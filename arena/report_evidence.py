"""Read-only report evidence. Legacy logs are sampled explicitly, never re-fingerprinted."""
import json
from pathlib import PureWindowsPath
import time
from .runtime_evidence import observe_line

FAILURES=('timeout','crash','hang','illegal_move','startup_timeout','readiness_timeout','protocol_error')


def filename(value):return PureWindowsPath(str(value)).name


def configured_option(profile,name,default=None):
    options=profile.get('options',{});advertised=profile.get('advertised')
    from .engine_options import find_name
    actual=find_name(options,name)
    if advertised is not None and not find_name(advertised,name):return 'N/A (unsupported)'
    if actual:return options[actual]
    if name.casefold() in profile:return profile[name.casefold()]
    if advertised is not None:
        actual=advertised.get(find_name(advertised,name),{})
        return actual.get('default',default)
    return default if default is not None else 'Not recorded'


def peak_events(events):
    current={};peak={}
    for r in events:
        k=r['kind'];current[k]=current.get(k,0)+r['delta'];peak[k]=max(peak.get(k,0),current[k])
    return peak


def collect(view,tid,settings,displayed):
    tables={r['name'] for r in view.rows("SELECT name FROM sqlite_master WHERE type='table'")}
    clock=time.time()
    timing=view.one('''SELECT min(a.started) first_start,max(a.ended) last_end,sum(a.ended IS NULL) running,
        count(*) attempts FROM attempts a JOIN games g ON g.id=a.gid WHERE g.tid=?''',(tid,))
    events=view.db.execute('''SELECT a.started t,1 delta,'Games' kind FROM attempts a JOIN games g ON g.id=a.gid WHERE g.tid=?
        UNION ALL SELECT coalesce(a.ended,?),-1,'Games' FROM attempts a JOIN games g ON g.id=a.gid WHERE g.tid=? ORDER BY t,delta''',(tid,clock,tid))
    peaks=peak_events(events)
    group_rows=view.rows("SELECT DISTINCT json_extract(profile,'$.gpu_group') name FROM participants WHERE tid=? AND coalesce(json_extract(profile,'$.gpu_group'),'')<>''",(tid,))
    gpu_limits={g['name']:settings.get('gpu_limits',{}).get(g['name'],2) for g in group_rows}
    if group_rows:
        peaks.update(peak_events(view.db.execute('''WITH reservations AS (
            SELECT a.started,coalesce(a.ended,?) ended,json_extract(p.profile,'$.gpu_group') kind
            FROM games g JOIN attempts a ON a.gid=g.id JOIN participants p ON p.tid=g.tid AND p.slot IN (g.white,g.black)
            WHERE g.tid=? AND coalesce(json_extract(p.profile,'$.gpu_group'),'')<>'')
            SELECT started t,1 delta,kind FROM reservations UNION ALL SELECT ended,-1,kind FROM reservations ORDER BY t,delta''',(clock,tid))))
    # One self-play profile can start two GPU engines; count both reservations.
    if settings['format']=='self_play':
        for group in gpu_limits:peaks[group]=2*peaks.get(group,0)
    source='FROM games g JOIN attempts a ON a.id=g.official WHERE g.tid=? AND g.invalid=0'
    openings=view.one('''SELECT count(DISTINCT json_extract(g.opening,'$.fen')) used,
        sum(json_extract(g.opening,'$.ko_opening_progression')='shared_pairs_v1') advancing_shared,
        sum(json_extract(g.opening,'$.competition_stage')='playoff') playoffs '''+source,(tid,))
    failure_matches=view.rows('''SELECT g.round,min(g.a,g.b) a,max(g.a,g.b) b,count(*) games,
        sum(CASE a.result WHEN '1/2-1/2' THEN .5 WHEN '1-0' THEN g.white=min(g.a,g.b) WHEN '0-1' THEN g.black=min(g.a,g.b) ELSE 0 END) score
        FROM games g JOIN attempts a ON a.id=g.official WHERE g.tid=? AND g.invalid=0
        AND a.reason IN ('''+','.join('?' for _ in FAILURES)+') GROUP BY g.round,min(g.a,g.b),max(g.a,g.b)',(tid,*FAILURES))
    phase_rows=view.rows('''SELECT p.value slot,coalesce(json_extract(g.opening,'$.competition_stage'),'regular') stage,count(*) games,
        sum(a.result='1/2-1/2') draws,
        sum((a.result='1-0' AND g.white=p.value) OR (a.result='0-1' AND g.black=p.value)) wins,
        sum((a.result='0-1' AND g.white=p.value) OR (a.result='1-0' AND g.black=p.value)) losses
        FROM games g JOIN attempts a ON a.id=g.official JOIN json_each(?) p ON p.value IN (g.white,g.black)
        WHERE g.tid=? AND g.invalid=0 GROUP BY p.value,stage''',(json.dumps([x['rank']['slot'] for x in displayed]),tid)) if settings['format'] in ('knockout','double_elimination') else []
    failures=view.rows('''SELECT g.id,g.number,g.round,g.white,g.black,a.id aid,a.result,a.reason,a.detail,
        json_extract(g.opening,'$.playoff_stage') stage,
        json_extract(w.profile,'$.name') white_name,json_extract(b.profile,'$.name') black_name
        FROM games g JOIN attempts a ON a.id=g.official
        JOIN participants w ON w.tid=g.tid AND w.slot=g.white JOIN participants b ON b.tid=g.tid AND b.slot=g.black
        WHERE g.tid=? AND g.invalid=0 AND a.reason IN ('''+','.join('?' for _ in FAILURES)+') ORDER BY g.number LIMIT 200',(tid,*FAILURES))
    for f in failures:
        from .log_storage import read
        lines=read(view.db,f['aid'],96)
        f['errors']=list(dict.fromkeys(r['line'].removeprefix('stderr ') for r in reversed(lines)
            if r['line'].startswith('stderr ') and any(word in r['line'].lower() for word in ('error','exception','failed'))))[-3:]
    sessions=view.rows('SELECT * FROM run_sessions WHERE tid=? ORDER BY started',(tid,)) if 'run_sessions' in tables else []
    for session in sessions:session['body']=json.loads(session['body'])
    process_peaks={}
    if 'attempt_engines' in tables:
        process_peaks=peak_events(view.db.execute('''WITH processes AS (
            SELECT x.started,coalesce(x.ended,a.ended,?) ended,coalesce(nullif(json_extract(p.profile,'$.gpu_group'),''),'ungrouped engine processes') kind
            FROM games g JOIN attempts a ON a.gid=g.id JOIN attempt_engines x ON x.aid=a.id
            JOIN participants p ON p.tid=g.tid AND p.slot=CASE x.side WHEN 'white' THEN g.white ELSE g.black END
            WHERE g.tid=? AND x.started IS NOT NULL)
            SELECT started t,1 delta,kind FROM processes UNION ALL SELECT ended,-1,kind FROM processes ORDER BY t,delta''',(clock,tid)))
    engines={}
    for item in displayed:
        slot=item['rank']['slot'];profile=item['profile'];records=[]
        if 'attempt_engines' in tables:
            records=view.rows('''SELECT e.body,count(*) observations FROM games g JOIN attempts a ON a.id=g.official
                JOIN attempt_engines x ON x.aid=a.id AND ((x.side='white' AND g.white=?) OR (x.side='black' AND g.black=?))
                JOIN engine_evidence e ON e.id=x.evidence WHERE g.tid=? AND g.invalid=0 GROUP BY e.id LIMIT 33''',(slot,slot,tid))
            records=[json.loads(r['body'])|{'observations':r['observations']} for r in records]
        entry={'observed':records[:32],'truncated':len(records)>32,'legacy':False}
        if not records:
            first=view.one('''SELECT g.white,g.black,g.official FROM games g WHERE g.tid=? AND g.invalid=0 AND g.official IS NOT NULL
                AND (g.white=? OR g.black=?) ORDER BY g.number LIMIT 1''',(tid,slot,slot))
            if first:
                # Legacy logs contain both engines. Only attribute network announcements
                # when just one of the two profiles advertises a weights-file option.
                peers=view.rows('SELECT slot,profile FROM participants WHERE tid=? AND slot IN (?,?)',(tid,first['white'],first['black']))
                weights=[p['slot'] for p in peers if any(k.casefold()=='weightsfile' for k in json.loads(p['profile']).get('advertised',{}))]
                if weights==[slot] and first['white']!=first['black']:
                    body={}
                    from .log_storage import read
                    for r in read(view.db,first['official'],512,False):observe_line(body,r['line'])
                    if body:entry.update(observed=[body],legacy=True)
        engines[slot]=entry
    changes=view.rows("SELECT created,body FROM audit WHERE tid=? AND action='concurrency_changed' ORDER BY id",(tid,))
    for change in changes:change['body']=json.loads(change['body'])
    return {'concurrency_changes':changes,'timing':timing,'peaks':peaks,'process_peaks':process_peaks,'openings':openings,'failures':failures,'failure_matches':failure_matches,'phase_rows':phase_rows,'sessions':sessions,'engines':engines,
        'gpu_limits':gpu_limits,'implicit_gpu_groups':[g for g in gpu_limits if g not in settings.get('gpu_limits',{})]}


def option_rows(profile):
    options=profile.get('options',{})
    overhead=[f'{k}: {v} ms' for k,v in options.items() if 'overhead' in k.casefold()]
    syzygy=next((v for k,v in options.items() if k.casefold()=='syzygypath'),'')
    affinity=profile.get('affinity',[])
    rows=[('Reported engine',profile.get('identity',{}).get('name',profile['name'])),
        ('Search threads',configured_option(profile,'Threads')),('Hash (MB)',configured_option(profile,'Hash')),
        ('CPU affinity','Logical processor IDs: '+', '.join(map(str,affinity)) if affinity else 'Unrestricted (OS scheduling)'),
        ('GPU group',profile.get('gpu_group') or 'None'),('Move overhead','; '.join(overhead) or 'Not explicitly recorded'),
        ('Engine tablebases','Syzygy path configured; usage not inferred' if syzygy else 'No Syzygy path configured')]
    for key in ('NNCacheSize','WeightsFile','Backend','BackendOptions','MinibatchSize','MaxConcurrentSearchers','RamLimitMb','MultiPV','Contempt','UCI_LimitStrength','UCI_Elo','Skill Level','EvalFile'):
        actual=next((k for k in options if k.casefold()==key.casefold()),None)
        if actual:
            value=options[actual]
            if key in ('WeightsFile','EvalFile') and not str(value).startswith('<'):value=filename(value)
            if key=='UCI_Elo' and str(configured_option(profile,'UCI_LimitStrength')).casefold() in ('false','0'):
                value=str(value)+' (inactive; UCI_LimitStrength is off)'
            rows.append((key+' (positions)' if key=='NNCacheSize' else key,value if value!='' else 'Engine default / empty'))
    return rows


def observation_rows(entry):
    rows=[]
    if not entry['observed']:return [('Runtime engine/network detection','Not recorded; configured settings shown above')]
    if entry['legacy']:rows.append(('Evidence scope','Legacy log sample: first official game only; filename/backend observed, no network fingerprint captured'))
    else:rows.append(('Evidence scope','Distinct saved observations from current official game attempts'))
    seen=set()
    for observation in entry['observed']:
        network=observation.get('network',{})
        values=[('Loaded network',filename(observation['network_file']) if observation.get('network_file') else 'Not identified'),
            ('Network SHA-256',network.get('sha256','Not recorded')),
            ('Network identification',network.get('status','Filename from engine log; file contents not verified' if observation.get('network_file') else 'Not recorded'))]
        for k,label in (('backend','Selected backend'),('gpu','Reported GPU'),('cuda_runtime','CUDA runtime'),('driver_cuda','Driver CUDA support')):
            if observation.get(k):values.append((label,observation[k]))
        effective=observation.get('options',{})
        if effective:
            for k,label in (('Threads','Observed search threads'),('Hash','Observed Hash (MB)'),('NNCacheSize','Observed NN cache (positions)')):
                from .engine_options import find_name
                actual=find_name(effective,k);value=effective.get(actual)
                if value is not None:values.append((label,str(value)+' ('+actual+')' if actual!=k else value))
        for label,value in values:
            signature=(label,str(value))
            if signature not in seen:rows.append((label,value));seen.add(signature)
    if entry['truncated']:rows.append(('Observation limit','First 32 distinct engine observations shown; full evidence remains in the database'))
    return rows
