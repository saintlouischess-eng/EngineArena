from __future__ import annotations
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sqlite3
import threading
import time
import uuid
import chess
import chess.pgn
from .models import FAILURES, TimeControl, scheduled_pairs, static_pair
from .stats import summarize, sprt_llr

def encode(v): return json.dumps(v,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def uid(): return uuid.uuid4().hex
def now(): return time.time()

DEFAULTS={'format':'match','cycles':10,'paired':True,'rounds':5,'candidates':1,'concurrency':28,'seed':7970,
 'time_control':{'kind':'fischer','seconds':180,'increment':2},'startup_timeout':30,'readiness_timeout':30,
 'hang_timeout':300,'stop_timeout':3,'tolerance':.05,'overhead':0,'retry_limit':0,'retry_reasons':list(FAILURES),
 'max_plies':0,'claim_draws':True,'annotations':True,'chess960':False,'opening_order':'sequential','opening_policy':'legacy',
 'resign_cp':0,'resign_plies':6,'draw_cp':0,'draw_plies':12,'draw_after':80,'ponder':False,
 'syzygy_path':'','sprt':{'elo0':0,'elo1':5,'alpha':.05,'beta':.05}}
DEFAULTS.update(cpu_budget=0,memory_budget_mb=0,gpu_limits={})
DEFAULTS.update(seeding='input',tiebreaks=['wins','seed'],bye_score=1,knockout_tiebreak='seed',playoff_limit=3,playoff_cycles=1,playoff_fallback='seed',swiss_rematches=False,ladder_swap='adjacent',ladder_distance=1)

class SavingError(RuntimeError): pass

class Store:
    """Single writer, FULL WAL durability. Every public mutation is transactional.

    Scheduling stores a cursor plus only a small ready window. Tournament profiles
    are immutable snapshots; editing the registry never changes a running test.
    """
    def __init__(self,folder):
        self.folder=Path(folder).resolve();self.folder.mkdir(parents=True,exist_ok=True)
        self.path=self.folder/'arena.sqlite3';self.warning='';self.failure='';self.revision=0;self.backup_lock=threading.Lock()
        self.backup_revision=-1;self.backup_file=None;self.backup_signature=None
        self.backup_state={'phase':'waiting','percent':None,'completed_at':None,'duration_seconds':None}
        self.progress_callback=None
        self.lock=open(self.folder/'writer.lock','a+b')
        try:
            if os.name=='nt':
                import msvcrt
                self.lock.seek(0);self.lock.write(b'0');self.lock.flush();self.lock.seek(0)
                msvcrt.locking(self.lock.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.lock.close();raise RuntimeError('This data folder is already open by another worker')
        self.db=sqlite3.connect(self.path,isolation_level=None,timeout=30)
        self.db.row_factory=sqlite3.Row
        try:
            if self.db.execute('PRAGMA quick_check').fetchone()[0]!='ok': raise sqlite3.DatabaseError('Integrity check failed')
        except sqlite3.DatabaseError:
            self.db.close(); self._restore()
            self.db=sqlite3.connect(self.path,isolation_level=None,timeout=30);self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('PRAGMA foreign_keys=ON');self.db.execute('PRAGMA busy_timeout=30000')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS profiles(id TEXT PRIMARY KEY,name TEXT NOT NULL,body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS presets(name TEXT PRIMARY KEY,body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS positions(name TEXT PRIMARY KEY,body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS report_revisions(tid TEXT PRIMARY KEY,revision INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS rating_anchors(tid TEXT PRIMARY KEY,slot INTEGER NOT NULL,rating REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS preferences(name TEXT PRIMARY KEY,body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS tournaments(id TEXT PRIMARY KEY,name TEXT NOT NULL,settings TEXT NOT NULL,
          state TEXT NOT NULL DEFAULT 'paused',created REAL,total INTEGER NOT NULL,cursor INTEGER NOT NULL DEFAULT 0,
          round INTEGER NOT NULL DEFAULT 0,dependency TEXT NOT NULL DEFAULT '',note TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS participants(tid TEXT,slot INTEGER,profile TEXT NOT NULL,PRIMARY KEY(tid,slot));
        CREATE TABLE IF NOT EXISTS games(id TEXT PRIMARY KEY,tid TEXT NOT NULL,number INTEGER NOT NULL,pair_no INTEGER NOT NULL,
          leg INTEGER NOT NULL,a INTEGER NOT NULL,b INTEGER NOT NULL,white INTEGER NOT NULL,black INTEGER NOT NULL,
          round INTEGER NOT NULL DEFAULT 0,opening TEXT NOT NULL,state TEXT NOT NULL DEFAULT 'pending',
          mode TEXT NOT NULL DEFAULT 'original',official TEXT,invalid INTEGER NOT NULL DEFAULT 0,
          UNIQUE(tid,number));
        CREATE INDEX IF NOT EXISTS games_queue ON games(tid,state,invalid,number);
        CREATE INDEX IF NOT EXISTS games_pair ON games(tid,pair_no,invalid);
        CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY,gid TEXT NOT NULL,seq INTEGER NOT NULL,mode TEXT NOT NULL,
          started REAL NOT NULL,ended REAL,result TEXT,reason TEXT,detail TEXT,clocks TEXT,identity TEXT,
          UNIQUE(gid,seq));
        CREATE INDEX IF NOT EXISTS attempts_game ON attempts(gid,seq);
        CREATE TABLE IF NOT EXISTS moves(aid TEXT,ply INTEGER,uci TEXT,san TEXT,fen TEXT,elapsed REAL,clocks TEXT,info TEXT,
          PRIMARY KEY(aid,ply));
        CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY,aid TEXT,line TEXT,created REAL);
        CREATE INDEX IF NOT EXISTS logs_attempt ON logs(aid,id);
        CREATE TABLE IF NOT EXISTS aggregates(tid TEXT,a INTEGER,b INTEGER,w INTEGER DEFAULT 0,d INTEGER DEFAULT 0,l INTEGER DEFAULT 0,
          p0 INTEGER DEFAULT 0,p1 INTEGER DEFAULT 0,p2 INTEGER DEFAULT 0,p3 INTEGER DEFAULT 0,p4 INTEGER DEFAULT 0,PRIMARY KEY(tid,a,b));
        CREATE TABLE IF NOT EXISTS outbox(id INTEGER PRIMARY KEY AUTOINCREMENT,aid TEXT UNIQUE,stream TEXT,pgn TEXT);
        CREATE INDEX IF NOT EXISTS outbox_stream_cursor ON outbox(stream,id);
        CREATE TABLE IF NOT EXISTS exports(stream TEXT PRIMARY KEY,last_id INTEGER NOT NULL DEFAULT 0,offset INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS pgn_rebuild(stream TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,tid TEXT,created REAL,action TEXT,body TEXT);
        CREATE TABLE IF NOT EXISTS round_state(tid TEXT,round INTEGER,body TEXT,PRIMARY KEY(tid,round));
        ''')
        from .history import initialize as initialize_history
        initialize_history(self)
        from .experiments import initialize
        initialize(self)
        from .sequential import initialize as initialize_sequential
        initialize_sequential(self)
        from .rankings import initialize as initialize_rankings
        initialize_rankings(self)
        with self.tx():
            self.db.execute('INSERT OR IGNORE INTO presets VALUES(?,?)',('3m + 2s · 1 thread · 1 GB · paired',encode({'time_control':DEFAULTS['time_control'],'threads':1,'hash':1024,'ponder':False,'paired':True})))
        from .deletion import apply_pending
        try:apply_pending(self)
        except SavingError:return
        self.recover()

    @contextlib.contextmanager
    def tx(self):
        try:
            self.db.execute('BEGIN IMMEDIATE');before=self.db.total_changes
            yield
            self.db.execute('COMMIT')
            if self.db.total_changes!=before:self.revision+=1
        except (sqlite3.Error,OSError) as e:
            if self.db.in_transaction:self.db.rollback()
            self.failure=f'Saving failed: {e}. Scheduling is stopped; free disk space or repair storage, then retry.'
            raise SavingError(self.failure) from e
        except BaseException:
            if self.db.in_transaction:self.db.rollback()
            raise

    def rows(self,sql,args=()): return [dict(r) for r in self.db.execute(sql,args)]
    def one(self,sql,args=()):
        row=self.db.execute(sql,args).fetchone()
        return dict(row) if row else None

    def execute(self,sql,args=()):
        with self.tx():self.db.execute(sql,args)

    def experiment_create(self,*args,**kwargs):
        from .experiments import create
        return create(self,*args,**kwargs)

    def experiment_get(self,eid):
        from .experiments import get
        return get(self,eid)

    def experiment_state(self,eid,state):
        from .experiments import state as set_state
        return set_state(self,eid,state)

    def experiment_claim(self,eid):
        from .experiments import claim
        return claim(self,eid)

    def experiment_finish(self,*args):
        from .experiments import finish
        return finish(self,*args)

    def game_detail(self,gid):
        g=self.one('SELECT * FROM games WHERE id=?',(gid,))
        if not g:raise ValueError('Game not found')
        g['opening']=json.loads(g['opening'])
        g['attempts']=self.rows('SELECT * FROM attempts WHERE gid=? ORDER BY seq',(gid,))
        for a in g['attempts']:
            a['moves']=self.rows('SELECT * FROM moves WHERE aid=? ORDER BY ply',(a['id'],))
            a['logs']=self.rows('SELECT line,created FROM logs WHERE aid=? ORDER BY id DESC LIMIT 300',(a['id'],))
        return g

    def set_state(self,tid,state):
        t=self.tournament(tid)
        if state=='running' and (t['dependency'] or self.failure):raise ValueError(t['dependency'] or self.failure)
        if state=='running' and t['settings']['format']=='sprt':
            from .sequential import get
            decision=get(self,tid)
            if decision and decision.get('frozen'):raise ValueError('SPRT has reached its recorded stopping boundary. Create a new test to collect further sequential evidence.')
        if state not in ('running','paused','draining'):raise ValueError('Invalid tournament state')
        with self.tx():
            self.db.execute('UPDATE tournaments SET state=? WHERE id=?',(state,tid));self.audit(tid,'state',{'state':state})

    def retry_saving(self,backup=True):
        from .deletion import apply_pending
        apply_pending(self)
        self.export_pending()
        if backup:self.backup()
        with self.tx():self.audit(None,'saving_rechecked',{})
        self.recover()
        from .experiments import initialize
        initialize(self)
        self.failure=''

    def deletion_preview(self,tid):
        from .deletion import preview
        return preview(self,tid)

    def delete_tournament(self,tid,name):
        from .deletion import delete
        return delete(self,tid,name)

    def audit(self,tid,action,body): self.db.execute('INSERT INTO audit(tid,created,action,body) VALUES(?,?,?,?)',(tid,now(),action,encode(body)))

    def save_profile(self,profile):
        profile=dict(profile);profile.setdefault('id',uid());profile.setdefault('name',Path(profile.get('path','Engine')).stem)
        if not profile.get('path'):raise ValueError('Executable path required')
        for key,default in (('threads',1),('hash',1024)):
            if not isinstance(profile.get(key,default),int) or profile.get(key,default)<1:raise ValueError(key+' must be a positive integer')
        if profile.get('time_control'):TimeControl.parse(profile['time_control'])
        with self.tx():self.db.execute('INSERT OR REPLACE INTO profiles VALUES(?,?,?)',(profile['id'],profile['name'],encode(profile)))
        return profile

    def profiles(self,search='',offset=0,limit=100):
        return {'total':self.db.execute('SELECT count(*) FROM profiles WHERE name LIKE ?',('%'+search+'%',)).fetchone()[0],
          'library_total':self.db.execute('SELECT count(*) FROM profiles').fetchone()[0],
          'items':[json.loads(r[0]) for r in self.db.execute('SELECT body FROM profiles WHERE name LIKE ? ORDER BY name,id LIMIT ? OFFSET ?',('%'+search+'%',limit,offset))]}

    def delete_profiles(self,ids):
        if not isinstance(ids,list) or not ids or any(not isinstance(pid,str) for pid in ids):raise ValueError('Select engine profiles to delete')
        ids=list(dict.fromkeys(ids))
        with self.tx():
            for pid in ids:
                if not self.one('SELECT id FROM profiles WHERE id=?',(pid,)):raise ValueError('An engine profile no longer exists; refresh the library')
            self.db.executemany('DELETE FROM profiles WHERE id=?',((pid,) for pid in ids))
            self.audit(None,'delete_profiles',{'ids':ids})
        return {'deleted':ids,'count':len(ids)}

    def profile_deletion_preview(self,ids):
        if not isinstance(ids,list) or not ids or any(not isinstance(pid,str) for pid in ids):raise ValueError('Select engine profiles to delete')
        ids=list(dict.fromkeys(ids));args=(encode(ids),)
        clause='FROM profiles WHERE id IN (SELECT value FROM json_each(?))'
        count=self.one('SELECT count(*) n '+clause,args)['n']
        if count!=len(ids):raise ValueError('An engine profile no longer exists; refresh the library')
        return {'count':count,'names':[r['name'] for r in self.rows('SELECT name '+clause+' ORDER BY name,id LIMIT 20',args)]}

    def save_preset(self,*args):
        from .conditions import save_preset
        return save_preset(self,*args)

    def save_position(self,*args):
        from .conditions import save_position
        return save_position(self,*args)

    def create_tournament(self,name,profiles,settings,openings=None,backup=True):
        s=DEFAULTS|settings;TimeControl.parse(s['time_control'])
        for k in ('cycles','rounds','concurrency'):
            if not isinstance(s[k],int) or s[k]<1:raise ValueError(k+' must be a positive integer')
        for k in ('startup_timeout','readiness_timeout','hang_timeout','stop_timeout'):
            if not isinstance(s[k],(int,float)) or not math.isfinite(s[k]) or s[k]<=0:raise ValueError(k+' must be finite and positive')
        if s['retry_limit']<0 or s['tolerance']<0 or s['overhead']<0:raise ValueError('Retry/tolerance/overhead cannot be negative')
        for k in ('max_plies','retry_limit','cpu_budget','memory_budget_mb'):
            if not isinstance(s[k],int) or s[k]<0:raise ValueError(k+' must be a non-negative integer')
        if any(not isinstance(v,int) or v<1 for v in s['gpu_limits'].values()):raise ValueError('GPU limits must be positive integer engine-process counts')
        for k in ('resign_plies','draw_plies'):
            if not isinstance(s[k],int) or s[k]<1:raise ValueError(k+' must be a positive integer')
        from .rankings import TIEBREAKS
        if not isinstance(s['tiebreaks'],list) or any(k not in TIEBREAKS for k in s['tiebreaks']):raise ValueError('Unknown standings tiebreak')
        if s['seeding'] not in ('input','random'):raise ValueError('Unknown seeding policy')
        if s['bye_score'] not in (0,.5,1):raise ValueError('Bye score must be 0, 0.5 or 1 per scheduled game')
        if s['knockout_tiebreak'] not in (*TIEBREAKS,'playoff','manual'):raise ValueError('Unknown knockout tiebreak')
        if s['playoff_fallback'] not in ('seed','manual'):raise ValueError('Unknown playoff fallback')
        if s['ladder_swap'] not in ('adjacent','leap'):raise ValueError('Unknown ladder movement policy')
        for k in ('playoff_limit','playoff_cycles'):
            if not isinstance(s[k],int) or isinstance(s[k],bool) or s[k]<1:raise ValueError(k+' must be a positive integer')
        if not isinstance(s['ladder_distance'],int) or s['ladder_distance']<1 or (s['format']=='ladder' and s['ladder_distance']>=len(profiles)):raise ValueError('Ladder distance must be positive and smaller than the field')
        if s['format']=='sprt':sprt_llr([0]*5,**s['sprt'])
        for p in profiles:
            if p.get('time_control'):TimeControl.parse(p['time_control'])
        total=scheduled_pairs(len(profiles),s['format'],s['cycles'],s['candidates'],s['rounds'],s['ladder_distance'])*(2 if s['paired'] else 1)
        if total>9223372036854775807:raise ValueError('Schedule exceeds SQLite 64-bit game numbering capacity')
        from .opening_policy import prepare
        tid=uid();s['openings']=prepare(s,openings or [{'fen':chess.STARTING_FEN,'name':'Initial position'}])
        for o in s['openings']:
            board=chess.Board(o['fen'],chess960=s['chess960'])
            if not board.is_valid():raise ValueError('Invalid opening FEN: '+o['fen'])
        with self.tx():
            self.db.execute('INSERT INTO tournaments(id,name,settings,created,total) VALUES(?,?,?,?,?)',(tid,name,encode(s),now(),total))
            self.db.executemany('INSERT INTO participants VALUES(?,?,?)',((tid,i,encode(p)) for i,p in enumerate(profiles)))
            from .rankings import create as create_rankings
            create_rankings(self,tid,s)
            for i in range(len(profiles)):self.db.execute('INSERT INTO aggregates(tid,a,b) VALUES(?,?,-1)',(tid,i))
            self.audit(tid,'created',{'participants':len(profiles),'total':total})
        if backup:self.backup()
        return self.tournament(tid)

    def tournament(self,tid):
        t=self.one('SELECT * FROM tournaments WHERE id=?',(tid,))
        if not t:raise ValueError('Tournament not found')
        t['settings']=json.loads(t['settings']);t['participants']=self.db.execute('SELECT count(*) FROM participants WHERE tid=?',(tid,)).fetchone()[0]
        return t

    def participant(self,tid,slot):return json.loads(self.db.execute('SELECT profile FROM participants WHERE tid=? AND slot=?',(tid,slot)).fetchone()[0])

    def _opening(self,s,pair_no,round_no=0,cycle=0):
        from .opening_policy import select
        return encode(select(s,pair_no,round_no,cycle))

    def _insert_pair(self,tid,pair_no,a,b,round_no,s,fixed_colors=False,stage='regular',cycle=0):
        legs=2 if s['paired'] else 1
        opening=encode(json.loads(self._opening(s,pair_no,round_no,cycle))|{'competition_stage':stage})
        for leg in range(legs):
            w,bk=(a,b) if (leg if legs==2 else 0 if fixed_colors else pair_no%2)==0 else (b,a)
            self.db.execute('INSERT INTO games(id,tid,number,pair_no,leg,a,b,white,black,round,opening) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                (uid(),tid,pair_no*legs+leg,pair_no,leg,a,b,w,bk,round_no,opening))

    def fill_queue(self,tid,window,defer_pairing=False):
        t=self.tournament(tid);s=t['settings']
        if t['dependency'] or t['state']!='running':return
        if s['format'] in ('swiss','knockout','double_elimination','ladder'):
            from .rounds import advance_round
            return advance_round(self,t,window,defer_pairing)
        queued=self.db.execute("SELECT count(*) FROM games WHERE tid=? AND state IN ('pending','running') AND invalid=0",(tid,)).fetchone()[0]
        count=max(0,window-queued);legs=2 if s['paired'] else 1
        end=min(t['total']//legs,t['cursor']+(count+legs-1)//legs)
        if end<=t['cursor']:return
        with self.tx():
            for k in range(t['cursor'],end):
                from .opening_policy import round_pair
                decoder=round_pair if s.get('opening_policy')=='round' else static_pair
                a,b,rep=decoder(k,t['participants'],s['format'],s['cycles'],s['candidates'])
                self._insert_pair(tid,k,a,b,rep,s)
            self.db.execute('UPDATE tournaments SET cursor=? WHERE id=?',(end,tid))

    def claim(self,tid):
        with self.tx():
            if self.one('SELECT state FROM tournaments WHERE id=?',(tid,))['state']!='running':return None
            g=self.one("SELECT * FROM games WHERE tid=? AND state='pending' AND invalid=0 ORDER BY number LIMIT 1",(tid,))
            if not g:return None
            aid=uid();seq=self.db.execute('SELECT coalesce(max(seq),0)+1 FROM attempts WHERE gid=?',(g['id'],)).fetchone()[0]
            self.db.execute('INSERT INTO attempts(id,gid,seq,mode,started) VALUES(?,?,?,?,?)',(aid,g['id'],seq,g['mode'],now()))
            self.db.execute("UPDATE games SET state='running' WHERE id=?",(g['id'],))
        return g|{'aid':aid,'seq':seq,'opening':json.loads(g['opening'])}

    def apply_round_plan(self,plan):
        from .rounds import apply_plan
        return apply_plan(self,plan)

    def pairing_context(self,tid):
        from .rounds import context
        return context(self,self.tournament(tid),True)

    def manual_pairings(self,*args):
        from .rounds import manual_round
        return manual_round(self,*args)

    def manual_tiebreak(self,*args):
        from .rounds import manual_winner
        return manual_winner(self,*args)

    def move(self,aid,ply,uci,san,fen,elapsed,clocks,info):
        with self.tx():
            self.db.execute('INSERT INTO moves VALUES(?,?,?,?,?,?,?,?)',(aid,ply,uci,san,fen,elapsed,encode(clocks),encode(info)))
            self.db.execute('UPDATE attempts SET clocks=? WHERE id=?',(encode(clocks),aid))

    def move_batch(self,items):
        # Group concurrent games into a single durable fsync. Every caller waits
        # for the batch commit before its next engine search is allowed to begin.
        with self.tx():
            for aid,ply,uci,san,fen,elapsed,clocks,info,lines in items:
                self.db.execute('INSERT INTO moves VALUES(?,?,?,?,?,?,?,?)',(aid,ply,uci,san,fen,elapsed,encode(clocks),encode(info)))
                self.db.execute('UPDATE attempts SET clocks=? WHERE id=?',(encode(clocks),aid))
                self.db.executemany('INSERT INTO logs(aid,line,created) VALUES(?,?,?)',((aid,l[:4096],now()) for l in lines))

    def log(self,aid,lines):
        if not lines:return
        with self.tx():
            self.db.executemany('INSERT INTO logs(aid,line,created) VALUES(?,?,?)',((aid,l[:4096],now()) for l in lines))

    def _pair_bucket(self,tid,pair_no):
        rows=self.rows('SELECT g.*,a.result FROM games g LEFT JOIN attempts a ON a.id=g.official WHERE g.tid=? AND g.pair_no=? AND g.invalid=0 ORDER BY leg',(tid,pair_no))
        if len(rows)!=2 or any(r['result'] not in ('1-0','0-1','1/2-1/2') for r in rows):return None
        g=rows[0];score=0
        for r in rows:
            white={'1-0':1,'0-1':0,'1/2-1/2':.5}[r['result']]
            score+=white if r['white']==r['a'] else 1-white
        return g['a'],g['b'],round(score*2)

    def _pair_delta(self,tid,pair_no,delta):
        bucket=self._pair_bucket(tid,pair_no)
        if not bucket:return
        a,b,k=bucket
        for x,y,j in (((a,b,k),) if a==b else ((a,b,k),(b,a,4-k))):
            for opponent in (y,-1):
                self.db.execute('INSERT OR IGNORE INTO aggregates(tid,a,b) VALUES(?,?,?)',(tid,x,opponent))
                self.db.execute(f'UPDATE aggregates SET p{j}=p{j}+? WHERE tid=? AND a=? AND b=?',(delta,tid,x,opponent))

    def _result_delta(self,g,result,delta):
        if result not in ('1-0','0-1','1/2-1/2'):return
        from .rankings import result_delta
        result_delta(self,g,result,delta)
        sides=((g['white'],g['black'],'1-0'),) if g['white']==g['black'] else ((g['white'],g['black'],'1-0'),(g['black'],g['white'],'0-1'))
        for a,b,win in sides:
            column='d' if result=='1/2-1/2' else 'w' if result==win else 'l'
            for opponent in (b,-1):
                self.db.execute('INSERT OR IGNORE INTO aggregates(tid,a,b) VALUES(?,?,?)',(g['tid'],a,opponent))
                self.db.execute(f'UPDATE aggregates SET {column}={column}+? WHERE tid=? AND a=? AND b=?',(delta,g['tid'],a,opponent))

    def _set_official(self,g,aid):
        self.db.execute('INSERT INTO report_revisions VALUES(?,1) ON CONFLICT(tid) DO UPDATE SET revision=revision+1',(g['tid'],))
        self._pair_delta(g['tid'],g['pair_no'],-1)
        if g['official']:
            old=self.one('SELECT result FROM attempts WHERE id=?',(g['official'],));self._result_delta(g,old['result'],-1)
        self.db.execute('UPDATE games SET official=? WHERE id=?',(aid,g['id']))
        if aid:
            result=self.db.execute('SELECT result FROM attempts WHERE id=?',(aid,)).fetchone()[0];self._result_delta(g,result,1)
        self._pair_delta(g['tid'],g['pair_no'],1)

    def finish(self,aid,result,reason,detail='',identity=None):
        attempt=self.one('SELECT * FROM attempts WHERE id=?',(aid,))
        if not attempt or attempt['ended'] is not None:return
        g=self.one('SELECT * FROM games WHERE id=?',(attempt['gid'],));t=self.tournament(g['tid']);s=t['settings']
        if result not in ('1-0','0-1','1/2-1/2','*'):raise ValueError('Invalid result')
        with self.tx():
            self.db.execute('UPDATE attempts SET ended=?,result=?,reason=?,detail=?,identity=? WHERE id=?',(now(),result,reason,detail,encode(identity or {}),aid))
            if attempt['mode']!='diagnostic' and result!='*' and not g['invalid']:self._set_official(g,aid)
            self.db.execute("UPDATE games SET state='completed' WHERE id=?",(g['id'],))
            if reason=='interrupted' and not g['invalid']:self.db.execute("UPDATE games SET state='pending' WHERE id=?",(g['id'],))
            if reason in s['retry_reasons'] and reason!='interrupted' and attempt['mode']!='diagnostic' and not g['invalid']:
                retry_count=self.db.execute("SELECT count(*) FROM attempts WHERE gid=? AND mode='automatic'",(g['id'],)).fetchone()[0]
                if retry_count<s['retry_limit']:self.db.execute("UPDATE games SET state='pending',mode='automatic' WHERE id=?",(g['id'],))
            if attempt['mode']!='diagnostic' and not g['invalid']:
                from .sequential import observe
                observe(self,t,g)
            self.audit(g['tid'],'attempt_finished',{'game':g['id'],'attempt':aid,'result':result,'reason':reason,'mode':attempt['mode']})
            self.db.execute('INSERT INTO outbox(aid,stream,pgn) VALUES(?,?,?)',(aid,'interrupted' if result=='*' else 'games',self.pgn(aid)))

    def pgn(self,aid):
        from .pgn_format import render_attempt
        return render_attempt(self.db,aid)

    def export_pending(self):
        """Crash-safe append: truncate to committed offset, fsync bytes, commit cursor.

        A crash after fsync but before cursor commit is safely replayed. Outbox
        and cursor live in the same database as results, never guessed from PGN.
        """
        try:
            from .deletion import rebuild_pgn
            rebuild_pgn(self)
            for stream in ('games','interrupted'):
                e=self.one('SELECT * FROM exports WHERE stream=?',(stream,)) or {'last_id':0,'offset':0}
                path=self.folder/(stream+'.pgn')
                if not path.exists() or path.stat().st_size<e['offset']:
                    e={'last_id':0,'offset':0}
                rows=self.rows('SELECT * FROM outbox WHERE stream=? AND id>? ORDER BY id LIMIT 64',(stream,e['last_id']))
                if not rows and path.exists() and path.stat().st_size==e['offset']:continue
                with open(path,'r+b' if path.exists() else 'w+b') as f:
                    f.truncate(e['offset']);f.seek(e['offset'])
                    for row in rows:f.write(row['pgn'].encode('utf-8'))
                    f.flush();os.fsync(f.fileno());offset=f.tell()
                with self.tx():self.db.execute('INSERT OR REPLACE INTO exports VALUES(?,?,?)',(stream,rows[-1]['id'] if rows else e['last_id'],offset))
        except (OSError,sqlite3.Error) as exc:
            self.failure=f'PGN saving failed: {exc}. Results remain committed in the database. Scheduling stopped.'
            raise SavingError(self.failure) from exc

    def export_official(self,tid,style='compact',perspective='engine',annotations=None):
        # Compatibility helper for small callers. Downloads use a separate,
        # bounded WAL-snapshot reader, without work on the game writer thread.
        from .pgn_export import OfficialPgnReader
        reader=OfficialPgnReader(self.path,tid,style,perspective,annotations)
        try:
            parts=[]
            while chunk:=reader.chunk():parts.append(chunk.decode('utf-8'))
            return ''.join(parts)
        finally:reader.close()

    def recover(self):
        running=self.rows('SELECT a.id FROM attempts a JOIN games g ON a.gid=g.id WHERE a.ended IS NULL')
        for a in running:self.finish(a['id'],'*','interrupted','Worker/application terminated; restart from the recorded opening')
        with self.tx():
            self.db.execute("UPDATE tournaments SET state='paused',note='Recovered after restart. Completed results retained; unfinished attempts archived. Resume when ready.' WHERE state IN ('running','draining')")
        self.export_pending()

    def requeue(self,tid,ids=None,reason=None,mode='diagnostic',invalidate=False):
        if mode not in ('diagnostic','replacement'):raise ValueError('Select diagnostic or replacement replay')
        t=self.tournament(tid)
        if t['state'] in ('running','draining'):raise ValueError('Pause and drain this tournament before changing attempts')
        sql='SELECT g.* FROM games g LEFT JOIN attempts a ON a.id=g.official WHERE g.tid=? AND g.invalid=0';args=[tid]
        if ids:
            # Temporary selection table avoids SQLite host-parameter limits for bulk operations.
            self.db.execute('CREATE TEMP TABLE IF NOT EXISTS selected_games(id TEXT PRIMARY KEY)');self.db.execute('DELETE FROM selected_games')
            self.db.executemany('INSERT OR IGNORE INTO selected_games VALUES(?)',((i,) for i in ids));sql+=' AND g.id IN (SELECT id FROM selected_games)'
        elif reason:
            if reason=='failed':sql+=' AND (a.reason IN ('+','.join('?' for _ in FAILURES)+") OR EXISTS(SELECT 1 FROM attempts x WHERE x.gid=g.id AND x.reason='interrupted'))";args.extend(FAILURES)
            elif reason=='interrupted':sql+=" AND EXISTS(SELECT 1 FROM attempts x WHERE x.gid=g.id AND x.reason='interrupted')"
            else:sql+=' AND a.reason=?';args.append(reason)
        else:raise ValueError('Select games or a failure filter')
        games=self.rows(sql,args)
        if not games:return {'queued':0}
        first_round=min(g['round'] for g in games)
        from .dependencies import effects,invalidate_playoffs,update_total
        effect=effects(self,tid,games) if t['settings']['format'] in ('swiss','knockout','double_elimination','ladder') and mode=='replacement' else None
        dependent=effect is not None and bool(effect['later_rounds'] or effect['playoffs'])
        if dependent and not invalidate:
            return {'queued':0,'dependency':True,'effects':effect,'message':f'Replacement affects {len(effect["later_rounds"])} later round(s) and {len(effect["playoffs"])} playoff sequence(s). Explicitly invalidate these dependencies before replaying. Every previous attempt and pairing decision remains archived.'}
        with self.tx():
            if dependent:
                for g in self.rows('SELECT * FROM games WHERE tid=? AND round>? AND invalid=0',(tid,first_round)):
                    if g['official']:self._set_official(g,None)
                    self.db.execute("UPDATE games SET invalid=1,state='invalidated' WHERE id=?",(g['id'],))
                from .rankings import reverse_round_byes
                reverse_round_byes(self,tid,first_round,t['settings'])
                self.db.execute('DELETE FROM round_state WHERE tid=? AND round>?',(tid,first_round))
                self.db.execute("UPDATE tournaments SET round=?,dependency='',note='Later rounds invalidated explicitly; replay results will regenerate pairings.' WHERE id=?",(first_round,tid))
            if effect:
                invalidate_playoffs(self,tid,effect)
                update_total(self,tid)
            if mode=='replacement' and t['settings']['format']=='sprt':
                from .sequential import invalidate
                invalidate(self,tid)
                self.db.execute('UPDATE tournaments SET note=? WHERE id=?',('SPRT inference invalidated by manual replacement. Standings remain current; use a new test for sequential inference.',tid))
            queued=0
            for g in games:
                if self.one('SELECT invalid FROM games WHERE id=?',(g['id'],))['invalid']:continue
                self.db.execute("UPDATE games SET state='pending',mode=? WHERE id=?",(mode,g['id']))
                queued+=1
            self.db.execute("UPDATE tournaments SET state='paused' WHERE id=?",(tid,))
            self.audit(tid,'requeue',{'count':queued,'mode':mode,'invalidated_dependencies':effect if dependent else None})
        return {'queued':queued}

    def save_rating_anchor(self,tid,slot,rating):
        if not isinstance(slot,int) or isinstance(slot,bool) or not self.one('SELECT slot FROM participants WHERE tid=? AND slot=?',(tid,slot)):
            raise ValueError('Select a tournament participant as the reference')
        if not isinstance(rating,(int,float)) or isinstance(rating,bool) or not math.isfinite(rating):raise ValueError('Reference rating must be finite')
        with self.tx():
            self.db.execute('INSERT OR REPLACE INTO rating_anchors VALUES(?,?,?)',(tid,slot,rating))
            self.audit(tid,'rating_anchor',{'slot':slot,'rating':rating})
        return {'slot':slot,'rating':rating}

    def snapshot(self,tid,offset=0,limit=100,sort='rank',direction='asc',confidence=95,method='normal'):
        t=self.tournament(tid);paired=t['settings']['paired']
        from .standings import page
        t['standings']=page(self,tid,t['settings'],offset,limit,sort,direction,confidence,method)
        t['standings_sort']={'key':sort,'direction':direction};t['confidence']=float(confidence)
        t['counts']={r['state']:r['n'] for r in self.rows('SELECT state,sum(n) n FROM game_counts WHERE tid=? AND invalid=0 GROUP BY state HAVING sum(n)>0',(tid,))}
        t['official_games']=self.db.execute('SELECT coalesce(sum(n),0) FROM game_counts WHERE tid=? AND invalid=0 AND has_official=1',(tid,)).fetchone()[0]
        t['complete_pairs']=self.db.execute('SELECT coalesce(sum(p0+p1+p2+p3+p4),0) FROM aggregates WHERE tid=? AND b=-1',(tid,)).fetchone()[0]//(1 if t['settings']['format']=='self_play' else 2) if paired else 0
        t['revision']=self.revision;t['saving_error']=self.failure;t['warning']=self.warning
        if t['settings']['format']=='sprt':
            from .sequential import get
            r=self.one('SELECT * FROM aggregates WHERE tid=? AND a=0 AND b=1',(tid,))
            bins=[r[f'p{i}'] for i in range(5)] if r and paired else [r['l'],r['d'],r['w']] if r else [0]*5
            t['sprt']=get(self,tid) or sprt_llr([0]*(5 if paired else 3),**t['settings']['sprt'])
            t['sprt_descriptive']=sprt_llr(bins,**t['settings']['sprt'])
        return t

    def h2h(self,tid,slot):
        paired=self.tournament(tid)['settings']['paired']
        results=[{'opponent':r['b'],'name':self.participant(tid,r['b'])['name'],**summarize(r['w'],r['d'],r['l'],[r[f'p{i}'] for i in range(5)] if paired else None)} for r in self.rows('SELECT * FROM aggregates WHERE tid=? AND a=? AND b>=0',(tid,slot))]
        for r in results:
            if r['opponent']==slot:r.update(elo=None,ci95=None,ci95_conservative=None,los=None,model='Self-play, White perspective; no between-engine inference')
        return results

    def h2h_page(self,tid,slot,offset=0,search='',confidence=95):
        if offset<0:raise ValueError('Invalid head-to-head page')
        paired=self.tournament(tid)['settings']['paired']
        clause="FROM aggregates a JOIN participants p ON p.tid=a.tid AND p.slot=a.b WHERE a.tid=? AND a.a=? AND a.b>=0 AND a.w+a.d+a.l>0 AND json_extract(p.profile,'$.name') LIKE ?"
        args=(tid,slot,'%'+search+'%');total=self.one('SELECT count(*) n '+clause,args)['n']
        records=self.rows("SELECT a.*,json_extract(p.profile,'$.name') name "+clause+' ORDER BY a.b LIMIT 50 OFFSET ?',(*args,offset));items=[]
        for r in records:
            values=summarize(r['w'],r['d'],r['l'],[r[f'p{i}'] for i in range(5)] if paired else None,confidence)
            if r['b']==slot:values.update(elo=None,ci=None,ci_conservative=None,ci95=None,ci95_conservative=None,los=None,model='Self-play, White perspective; no between-engine inference')
            items.append({'opponent':r['b'],'name':r['name'],**values})
        return {'total':total,'items':items,'offset':offset}

    def games(self,tid,reason='',offset=0,limit=100):
        from .history import game_page
        return game_page(self.db,tid,reason,offset,limit)

    def backup(self,force=True):
        # This method owns its connections and can run outside the writer actor.
        # A pinned WAL snapshot keeps the copy consistent while moves commit.
        with self.backup_lock:
            if not force and self.backup_revision==self.revision and self.backup_file:
                try:
                    st=self.backup_file.stat()
                    if (st.st_size,st.st_mtime_ns)==self.backup_signature:
                        self._backup_progress(phase='ready',percent=None,unchanged=True)
                        return False
                except OSError:pass
            self._backup_snapshot()
            return True

    def _backup_progress(self,**values):
        self.backup_state=self.backup_state|values
        if self.progress_callback:
            try:self.progress_callback(dict(self.backup_state))
            except (OSError,ValueError):pass  # Progress output never controls durability.

    def _backup_snapshot(self):
        started=time.monotonic();revision=self.revision
        self._backup_progress(phase='copying',percent=0,unchanged=False,started_at=now())
        try:
            directory=self.folder/'backups';directory.mkdir(exist_ok=True)
            choices=[directory/f'recovery-{i}.sqlite3' for i in range(5)]
            target=min(choices,key=lambda p:p.stat().st_mtime_ns if p.exists() else 0);temporary=directory/'backup.tmp'
            # A killed process may leave a partial SQLite image here. It is not
            # a verified backup; start a fresh copy without touching the ring.
            temporary.unlink(missing_ok=True)
            source=sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True,timeout=30)
            try:
                source.execute('BEGIN');source.execute('SELECT count(*) FROM sqlite_master').fetchone()
                dest=sqlite3.connect(temporary)
                try:
                    last_progress=0.
                    def progress(status,remaining,total):
                        nonlocal last_progress
                        current=time.monotonic()
                        if current-last_progress>=.25 or remaining==0:
                            self._backup_progress(phase='copying',percent=round(100*(total-remaining)/total,1) if total else 100)
                            last_progress=current
                    source.backup(dest,pages=256,progress=progress)
                    self._backup_progress(phase='verifying',percent=None)
                    if dest.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise OSError('Backup integrity check failed')
                finally:dest.close()
            finally:source.close()
            self._backup_progress(phase='flushing',percent=None)
            with open(temporary,'r+b') as f:f.flush();os.fsync(f.fileno())
            os.replace(temporary,target)
            stat=target.stat();self.backup_file=target;self.backup_signature=(stat.st_size,stat.st_mtime_ns)
            self.backup_revision=revision
            files=[p.stat().st_size for p in choices if p.exists()]
            self._backup_progress(phase='ready',percent=None,completed_at=now(),duration_seconds=time.monotonic()-started,
                                  size_bytes=stat.st_size,backup_count=len(files),total_bytes=sum(files))
        except (OSError,sqlite3.Error) as e:
            self._backup_progress(phase='error',percent=None,error=str(e))
            self.failure=f'Backup saving failed: {e}. Scheduling stopped.';raise SavingError(self.failure) from e

    def _restore(self):
        candidates=sorted((self.folder/'backups').glob('recovery-*.sqlite3'),key=lambda p:p.stat().st_mtime,reverse=True)
        for candidate in candidates:
            try:
                with contextlib.closing(sqlite3.connect(candidate)) as check:
                    if check.execute('PRAGMA integrity_check').fetchone()[0]!='ok':continue
                stamp=str(time.time_ns())
                for suffix in ('','-wal','-shm'):
                    path=Path(str(self.path)+suffix)
                    if path.exists():os.replace(path,self.folder/(path.name+'.damaged-'+stamp))
                shutil.copy2(candidate,self.path)
                self.warning=f'Restored verified backup {candidate.name} from {time.ctime(candidate.stat().st_mtime)} after database corruption. Damaged files retained. Results newer than this backup may be unavailable; inspect before resuming.'
                return
            except (OSError,sqlite3.Error):continue
        raise SavingError('Database damaged and no verified backup available. Original files preserved; recovery requires repair, not tournament reset.')

    def close(self):
        self.db.close()
        if os.name=='nt':
            import msvcrt
            self.lock.seek(0);msvcrt.locking(self.lock.fileno(),msvcrt.LK_UNLCK,1)
        self.lock.close()
