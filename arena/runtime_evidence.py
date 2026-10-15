"""Durable run conditions and deduplicated engine observations, outside chess clocks."""
import asyncio
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import time
import uuid

import psutil


def initialize(store):
    store.db.executescript('''
      CREATE TABLE IF NOT EXISTS run_sessions(id TEXT PRIMARY KEY,tid TEXT NOT NULL,started REAL NOT NULL,
        last_seen REAL NOT NULL,ended REAL,state TEXT NOT NULL,body TEXT NOT NULL);
      CREATE INDEX IF NOT EXISTS run_sessions_tournament ON run_sessions(tid,started);
      CREATE TABLE IF NOT EXISTS run_attempts(aid TEXT PRIMARY KEY,sid TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS engine_evidence(id TEXT PRIMARY KEY,body TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS attempt_engines(aid TEXT,side TEXT,evidence TEXT NOT NULL,started REAL,ended REAL,
        PRIMARY KEY(aid,side));
    ''')


def system_snapshot():
    from . import __version__
    from .hardware import cpu_name,read_gpus
    gpus,note=read_gpus()
    return {'app_version':__version__,'os':platform.platform(),'cpu':cpu_name(),
        'physical_cores':psutil.cpu_count(logical=False),'logical_processors':psutil.cpu_count(),
        'ram_gib':psutil.virtual_memory().total/2**30,
        'gpus':[{'name':g['name'],'index':g['index'],'driver':g['driver'],'vram_gib':g['metrics'].get('gpu_memory_total')} for g in gpus],
        'gpu_note':note}


def write_engine(store,aid,side,body,started,ended,sid=None):
    encoded=json.dumps(body,sort_keys=True,separators=(',',':'),ensure_ascii=False)
    key=hashlib.sha256(encoded.encode()).hexdigest()
    with store.tx():
        if sid:store.db.execute('INSERT OR IGNORE INTO run_attempts VALUES(?,?)',(aid,sid))
        store.db.execute('INSERT OR IGNORE INTO engine_evidence VALUES(?,?)',(key,encoded))
        store.db.execute('INSERT OR REPLACE INTO attempt_engines VALUES(?,?,?,?,?)',(aid,side,key,started,ended))


def observe_line(body,line):
    """Parse only specific engine announcements; do not interpret arbitrary log text."""
    text=line.removeprefix('stderr ').removeprefix('< ').removeprefix('info string ').strip()
    changed=False
    if text.startswith('GPU:'):
        value=text[4:].strip()[:2048]
        models=body.setdefault('gpu_models',[])
        if value and value not in models:models.append(value);changed=True
        observation={'backend_instance':body.get('backend_instance',0),'model':value}
        observations=body.setdefault('gpu_observations',[])
        if value and observation not in observations:observations.append(observation);changed=True
    for prefix,key in (('Loading weights file from:','network_file'),('GPU:','gpu'),
                       ('CUDA Runtime version:','cuda_runtime'),('Latest version of CUDA supported by the driver:','driver_cuda')):
        if text.startswith(prefix):
            value=text[len(prefix):].strip()[:2048]
            if value and body.get(key)!=value:body[key]=value;changed=True
    if text.startswith('Switching to [') and ']...' in text:
        value=text.partition('[')[2].partition(']')[0]
        if body.get('backend')!=value:body['backend']=value;changed=True
    if text.startswith('Creating backend [') and ']' in text:
        value=text.partition('[')[2].partition(']')[0]
        body['backend_instance']=body.get('backend_instance',0)+1;changed=True
        if not body.get('root_backend'):body['root_backend']=value;changed=True
        if body.get('backend')!=value:body['backend']=value;changed=True
    return changed


def observed_fingerprint(profile,value):
    """Hash a reported weights file only inside approved engine/configured folders."""
    from .fingerprints import fingerprint
    roots=[Path(profile.get('cwd') or Path(profile['path']).parent).resolve(),Path(profile['path']).resolve().parent]
    for key,v in profile.get('options',{}).items():
        if key.casefold()=='weightsfile' and v and not str(v).startswith('<'):
            p=Path(str(v));roots.append((p if p.is_absolute() else roots[0]/p).resolve().parent)
    raw=Path(value);path=(raw if raw.is_absolute() else roots[0]/raw).resolve()
    if not any(path.is_relative_to(root) for root in roots):
        return {'name':path.name,'status':'Filename observed; outside configured engine/network folders; fingerprint unavailable'}
    if not path.name.lower().endswith(('.pb.gz','.pb','.nnue','.bin','.txt.gz','.weights','.gz')):
        return {'name':path.name,'status':'Filename observed; unrecognized network extension; fingerprint unavailable'}
    try:return {'name':path.name,'status':'File fingerprint captured after engine load announcement',**fingerprint(path)}
    except (OSError,ValueError) as e:return {'name':path.name,'status':'Filename observed; fingerprint unavailable: '+str(e)}


class EngineRecorder:
    def __init__(self,db,aid,side,engine,sid=None):
        self.db=db;self.aid=aid;self.side=side;self.engine=engine;self.task=None;self.dirty=False;self.hashed=None;self.network=None;self.error=None
        self.sid=sid

    def changed(self):
        self.dirty=True
        if self.task and self.task.done() and not self.task.cancelled() and self.task.exception():self.error=self.task.exception()
        if self.error:return
        if not self.task or self.task.done():
            self.task=asyncio.create_task(self.flush())
            self.task.add_done_callback(self.done)

    def done(self,task):
        if not task.cancelled() and task.exception():self.error=task.exception()

    async def flush(self):
        while self.dirty:
            # Coalesce the process-start, identity and option announcements. This
            # never delays UCI readiness, move delivery or the chess clock.
            await asyncio.sleep(.02)
            self.dirty=False;e=self.engine;body=copy.deepcopy(e.runtime)
            body['identity']=dict(e.identity)
            if self.network and self.hashed==body.get('network_file'):body['network']=self.network
            # Commit the observed filename before the potentially slow file read.
            await self.db.call('record_engine_evidence',self.aid,self.side,body,e.process_started,e.process_ended,self.sid)
            value=body.get('network_file')
            if value and value!=self.hashed:
                self.hashed=value
                try:self.network=await asyncio.to_thread(observed_fingerprint,e.profile,value)
                except (OSError,ValueError):self.network={'status':'Observed filename could not be fingerprinted'}
                self.dirty=True

    async def close(self):
        if self.error:raise self.error
        self.changed()
        if self.task:await self.task


def add_sample(body,snapshot):
    stamp=snapshot.get('sampled_at')
    if not stamp or snapshot.get('stale') or stamp<=body.get('last_sample',0):return False
    body['last_sample']=stamp;body.setdefault('first_sample',stamp)
    fields={k:v for k,v in snapshot.get('metrics',{}).items() if k in
        ('cpu_percent','cpu_temperature','cpu_fastest_clock','ram_used','ram_percent')}
    for gpu in snapshot.get('gpus',[]):
        for k,v in gpu.get('metrics',{}).items():
            if k in ('gpu_percent','gpu_memory','gpu_temperature','gpu_clock','gpu_power'):
                fields['GPU '+gpu['index']+' '+k]=v
    samples=body.setdefault('samples',{})
    for k,v in fields.items():
        if not isinstance(v,(float,int)) or isinstance(v,bool) or not math.isfinite(v):continue
        p=samples.setdefault(k,{'count':0,'sum':0.,'min':v,'max':v})
        p.update(count=p['count']+1,sum=p['sum']+v,min=min(p['min'],v),max=max(p['max'],v))
    return True


class RunRecorder:
    def __init__(self,db):self.db=db;self.sessions={};self.monitor=None;self.due=0

    async def shared_changed(self,tid,limits,priority):
        session=self.sessions.get(tid)
        if not session:return
        evidence={'limits':limits,'priority':priority}
        if session['body'].get('shared_scheduler')==evidence:return
        session['body']['shared_scheduler']=evidence
        session['body'].setdefault('shared_scheduler_history',[]).append({'at':time.time(),**evidence})
        await self.db.call('execute','UPDATE run_sessions SET body=? WHERE id=?',(json.dumps(session['body']),session['id']))

    async def begin(self,tid,settings,admission,shared=None,priority=2):
        shared_evidence={'limits':shared,'priority':priority} if shared else None
        if tid in self.sessions:
            if shared_evidence:await self.shared_changed(tid,shared,priority)
            return
        try:hardware=await asyncio.to_thread(system_snapshot)
        except Exception as e:hardware={'unavailable':'Hardware snapshot unavailable: '+str(e)}
        groups=await self.db.call('rows',"SELECT DISTINCT json_extract(profile,'$.gpu_group') name FROM participants WHERE tid=? AND coalesce(json_extract(profile,'$.gpu_group'),'')<>''",(tid,))
        sid=uuid.uuid4().hex;stamp=time.time()
        body={'hardware':hardware,'resources':{'cpu_threads':settings.get('cpu_budget') or os.cpu_count() or 1,
            'memory_mb':admission.get('memory_budget_mb'),'game_limit':settings['concurrency'],
            'gpu_limits':{g['name']:settings.get('gpu_limits',{}).get(g['name'],2) for g in groups},
            'implicit_gpu_groups':[g['name'] for g in groups if g['name'] not in settings.get('gpu_limits',{})]}}
        if shared_evidence:
            body['shared_scheduler']=shared_evidence
            body['shared_scheduler_history']=[{'at':stamp,**shared_evidence}]
        await self.db.call('execute','INSERT INTO run_sessions VALUES(?,?,?,?,?,?,?)',(sid,tid,stamp,stamp,None,'running',json.dumps(body)))
        self.sessions[tid]={'id':sid,'body':body,'started':stamp}

    async def update(self,running,active,force=False):
        due=time.monotonic()>=self.due or force
        if due and self.monitor:self.monitor.request()
        for tid,session in list(self.sessions.items()):
            finished=tid not in running and tid not in active
            if not due and not finished:continue
            if tid in active and self.monitor:
                sample=self.monitor.snapshot()
                if (sample.get('sampled_at') or 0)>=session['started']:add_sample(session['body'],sample)
            stamp=time.time()
            await self.db.call('execute','UPDATE run_sessions SET last_seen=?,ended=?,state=?,body=? WHERE id=?',
                (stamp,stamp if finished else None,'closed' if finished else 'running',json.dumps(session['body']),session['id']))
            if finished:del self.sessions[tid]
        if due:self.due=time.monotonic()+10

    async def close(self):await self.update(set(),set(),True)
