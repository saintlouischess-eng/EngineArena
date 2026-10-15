"""User-selected, incremental official PGNs. All file work runs off the game actor.

The adjacent SQLite file is a durable export index, not the tournament database.
Commit intended bytes there first, fsync the PGN, then acknowledge its fingerprint.
Ordinary games append; replacements rebuild through an atomic sibling rename.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

import chess.pgn
from .pgn_format import render_attempt, PgnContext
from .pgn_options import normalize, PRESETS

BATCH = 32


class ImportGame(chess.pgn.GameBuilder):
    def begin_game(self):
        super().begin_game();self.game.explicit_result=False

    def visit_result(self,result):
        self.game.explicit_result=True
        return super().visit_result(result)


def initialize(store):
    store.db.executescript('''
      CREATE TABLE IF NOT EXISTS pgn_targets(path TEXT PRIMARY KEY,preset TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS pgn_links(tid TEXT PRIMARY KEY,path TEXT NOT NULL);
      CREATE INDEX IF NOT EXISTS pgn_links_path ON pgn_links(path);
      CREATE TABLE IF NOT EXISTS pgn_changes(seq INTEGER PRIMARY KEY AUTOINCREMENT,
        gid TEXT UNIQUE NOT NULL,tid TEXT NOT NULL);
      CREATE INDEX IF NOT EXISTS pgn_changes_tid ON pgn_changes(tid,seq);
      CREATE TRIGGER IF NOT EXISTS pgn_official_changed AFTER UPDATE OF official,invalid ON games
      WHEN (OLD.official IS NOT NEW.official OR OLD.invalid<>NEW.invalid)
        AND EXISTS(SELECT 1 FROM pgn_links WHERE tid=NEW.tid)
      BEGIN
        INSERT OR REPLACE INTO pgn_changes(gid,tid) VALUES(NEW.id,NEW.tid);
      END;
    ''')


def bind(store, tid, output):
    """Inside the caller's tournament transaction; output was prepared off-thread."""
    if output is None:return
    store.db.execute('DELETE FROM pgn_links WHERE tid=?', (tid,))
    if output.get('enabled'):
        path, preset = output['path'], output['preset']
        old = store.one('SELECT preset FROM pgn_targets WHERE path=?', (path,))
        if old and old['preset'] != preset and store.one('SELECT 1 FROM pgn_links WHERE path=?',(path,)):
            raise ValueError('This PGN file already uses another preset. Select its existing preset or a new file.')
        store.db.execute('INSERT INTO pgn_targets VALUES(?,?) ON CONFLICT(path) DO UPDATE SET preset=excluded.preset', (path,preset))
        store.db.execute('INSERT INTO pgn_links VALUES(?,?)', (tid,path))


def configure(store, tid, output):
    store.tournament(tid)
    with store.tx():
        bind(store,tid,output)
        store.audit(tid,'automatic_pgn',output)
    return output


def read_db(path):
    db=sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True,timeout=5)
    db.row_factory=sqlite3.Row
    return db


def file_hash(path, limit=None):
    digest=hashlib.sha256()
    with open(path,'rb') as f:
        left=limit
        while left is None or left>0:
            chunk=f.read(1024*1024 if left is None else min(left,1024*1024))
            if not chunk:break
            digest.update(chunk)
            if left is not None:left-=len(chunk)
        if left:raise ValueError('The PGN file is shorter than its saved export index.')
    return digest.hexdigest()


class Target:
    def __init__(self,path,workspace,preset,mode='append'):
        self.path=Path(path);self.index=Path(str(path)+'.arena-pgn.sqlite3')
        self.tmp=Path(str(path)+'.arena-pgn.tmp');self.workspace=workspace
        self.lock=None;self.db=None;self.verified=False;self.links=None;self.status={}
        # A per-output lock prevents two workspaces/processes from interleaving.
        try:
            self.lock=open(str(path)+'.arena-pgn.lock','a+b')
            if os.name=='nt':
                import msvcrt
                if not self.lock.seek(0,2):self.lock.write(b'0');self.lock.flush()
                self.lock.seek(0);msvcrt.locking(self.lock.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            if mode=='new' and (self.index.exists() or self.path.exists() and self.path.stat().st_size):
                raise ValueError('That PGN file already exists. Choose Append / continue or a new filename.')
            self.db=sqlite3.connect(self.index,timeout=5)
            self.db.row_factory=sqlite3.Row
            self.db.execute('PRAGMA synchronous=FULL')
            self.db.executescript('''
              CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS entries(seq INTEGER PRIMARY KEY AUTOINCREMENT,
                gid TEXT UNIQUE,tid TEXT,aid TEXT,body BLOB NOT NULL,active INTEGER NOT NULL DEFAULT 1);
              CREATE INDEX IF NOT EXISTS entries_tid ON entries(tid);
              CREATE TABLE IF NOT EXISTS pending(gid TEXT PRIMARY KEY,tid TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS append_bytes(seq INTEGER PRIMARY KEY,body BLOB NOT NULL);
            ''')
            owner=self.get('workspace')
            if owner and owner!=workspace:raise ValueError('This PGN file belongs to another Engine Arena data folder. Choose a different file.')
            if owner and self.get('preset')!=preset:raise ValueError('This PGN file already uses another preset. Select its existing preset or a new file.')
            if not owner:self.adopt(preset)
            self.preset=preset
            self.recover()
        except BaseException:
            self.close();raise

    def get(self,key,default=None):
        row=self.db.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone()
        return json.loads(row[0]) if row else default

    def put(self,key,value):
        self.db.execute('INSERT INTO meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key,json.dumps(value)))

    def adopt(self,preset):
        # Existing PGNs are read once. Preserve their exact bytes, including
        # comments. GameId lets older Engine Arena exports be reconciled too.
        if not self.path.exists():
            with self.path.open('xb') as f:f.flush();os.fsync(f.fileno())
        before=self.path.stat();digest=file_hash(self.path)
        with self.db:
            self.db.execute('DELETE FROM entries');self.db.execute('DELETE FROM pending')
            with self.path.open('r',encoding='utf-8-sig',newline='') as text, self.path.open('rb') as raw:
                while True:
                    start=text.tell();game=chess.pgn.read_game(text,Visitor=ImportGame);end=text.tell()
                    raw.seek(start);body=raw.read(end-start)
                    if game is None:
                        if body.strip():raise ValueError('The existing PGN has unrecognized or incomplete text. Use a new filename.')
                        if body:self.db.execute('INSERT INTO entries(gid,body) VALUES(?,?)',('external:'+uuid.uuid4().hex,body))
                        break
                    if game.errors or not game.explicit_result or game.headers.get('Result') not in ('1-0','0-1','1/2-1/2'):
                        raise ValueError('The existing PGN contains an incomplete or invalid game. Use a new filename.')
                    gid=game.headers.get('GameId') or 'external:'+uuid.uuid4().hex
                    if self.db.execute('SELECT 1 FROM entries WHERE gid=?',(gid,)).fetchone():
                        raise ValueError('The existing PGN has duplicate GameId records. Export current official results or use a new filename.')
                    self.db.execute('INSERT INTO entries(gid,tid,aid,body) VALUES(?,?,?,?)',
                        (gid,game.headers.get('TournamentId'),game.headers.get('AttemptId'),body))
            after=self.path.stat()
            if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns) or file_hash(self.path)!=digest:
                raise ValueError('The PGN file changed while it was being connected. Try again when its other writer is stopped.')
            self.put('workspace',self.workspace);self.put('preset',preset);self.put('cursor',0)
            self.put('size',after.st_size);self.put('mtime',after.st_mtime_ns);self.put('hash',digest)
            self.put('dirty',None)
            self.put('games',self.db.execute('SELECT count(*) FROM entries WHERE active=1 AND aid IS NOT NULL').fetchone()[0])

    def verify(self):
        st=self.path.stat()
        if st.st_size!=self.get('size') or st.st_mtime_ns!=self.get('mtime') or not self.verified:
            if st.st_size!=self.get('size') or file_hash(self.path)!=self.get('hash'):
                raise ValueError('The PGN file was changed outside Engine Arena. Saving is paused; choose a new file or restore the matching PGN and export index.')
            with self.db:self.put('mtime',st.st_mtime_ns)
        self.verified=True

    def checkpoint(self):
        st=self.path.stat()
        with self.db:
            self.put('size',st.st_size);self.put('mtime',st.st_mtime_ns)
            self.put('hash',self.get('desired_hash'));self.put('dirty',None)
            self.db.execute('DELETE FROM append_bytes')
        self.verified=True

    def write_file(self,recovery=False):
        dirty=self.get('dirty')
        if not dirty:return
        if dirty=='append':
            size=self.get('size')
            if recovery:
                # Accept only our old prefix followed by a partial/exact copy of
                # our planned tail. Never truncate unrelated external changes.
                if file_hash(self.path,size)!=self.get('hash'):raise ValueError('PGN recovery found an altered committed prefix.')
                with self.path.open('rb') as f:
                    f.seek(size)
                    for row in self.db.execute('SELECT body FROM append_bytes ORDER BY seq'):
                        body=row[0];actual=f.read(len(body))
                        if actual!=body[:len(actual)]:raise ValueError('PGN recovery found an unexpected file tail.')
                        if len(actual)<len(body):break
                    if f.read(1):raise ValueError('PGN recovery found extra external games. The file was left unchanged.')
            with self.path.open('r+b') as f:
                f.truncate(size);f.seek(size)
                for row in self.db.execute('SELECT body FROM append_bytes ORDER BY seq'):f.write(row[0])
                f.flush();os.fsync(f.fileno())
        else:
            if recovery and file_hash(self.path) not in (self.get('hash'),self.get('desired_hash')):
                raise ValueError('PGN recovery found an externally changed file. The file was left unchanged.')
            with self.tmp.open('wb') as f:
                for row in self.db.execute('SELECT body FROM entries WHERE active=1 ORDER BY seq'):f.write(row[0])
                f.flush();os.fsync(f.fileno())
            os.replace(self.tmp,self.path)
        self.checkpoint()

    def recover(self):
        if self.get('dirty'):
            self.write_file(recovery=True)
            if hasattr(self,'digest'):del self.digest
        self.verify()

    def enqueue(self,source,tids):
        links=tuple(sorted(tids))
        if links!=self.links:
            # Once per process/selection: metadata reconciliation also covers a
            # restored tournament backup whose change sequence moved backwards.
            head=source.execute('SELECT coalesce(max(seq),0) FROM pgn_changes').fetchone()[0]
            with self.db:
                self.db.execute('CREATE TEMP TABLE IF NOT EXISTS seen(gid TEXT PRIMARY KEY)')
                for tid in links:
                    self.db.execute('DELETE FROM seen')
                    cursor=source.execute('SELECT id,official FROM games WHERE tid=? AND official IS NOT NULL AND invalid=0',(tid,))
                    for rows in iter(lambda:cursor.fetchmany(256),[]):
                        self.db.executemany('INSERT INTO seen VALUES(?)',((r[0],) for r in rows))
                        for r in rows:
                            old=self.db.execute('SELECT aid,active FROM entries WHERE gid=?',(r['id'],)).fetchone()
                            if not old or old['aid']!=r['official'] or not old['active']:
                                self.db.execute('INSERT OR IGNORE INTO pending VALUES(?,?)',(r['id'],tid))
                    self.db.execute('INSERT OR IGNORE INTO pending SELECT gid,tid FROM entries WHERE tid=? AND active=1 AND gid NOT IN (SELECT gid FROM seen)',(tid,))
                self.put('cursor',head)
            self.links=links
        cursor=self.get('cursor',0)
        rows=source.execute('SELECT seq,gid,tid FROM pgn_changes WHERE seq>? ORDER BY seq LIMIT 256',(cursor,)).fetchall()
        with self.db:
            self.db.executemany('INSERT OR REPLACE INTO pending VALUES(?,?)',((r['gid'],r['tid']) for r in rows if r['tid'] in tids))
            if rows:self.put('cursor',rows[-1]['seq'])

    def sync(self,dbpath,tids):
        self.recover()
        with contextlib.closing(read_db(dbpath)) as source:
            source.execute('BEGIN');self.enqueue(source,set(tids));source.rollback()
            changes=[];contexts={};skipped=[]
            source.execute('BEGIN')
            for pending in self.db.execute('SELECT * FROM pending LIMIT ?',(BATCH,)).fetchall():
                gid,tid=pending['gid'],pending['tid']
                if tid not in tids:
                    skipped.append((gid,))
                    continue
                row=source.execute('SELECT official,invalid FROM games WHERE id=?',(gid,)).fetchone()
                if not row and not source.execute('SELECT 1 FROM tournaments WHERE id=?',(tid,)).fetchone():
                    skipped.append((gid,))
                    continue  # Deleted tournaments leave exported games intact.
                aid=row['official'] if row and not row['invalid'] else None
                old=self.db.execute('SELECT * FROM entries WHERE gid=?',(gid,)).fetchone()
                if aid and old and old['aid']==aid and old['active']:
                    skipped.append((gid,))
                    continue
                if not aid and (not old or not old['active']):
                    skipped.append((gid,))
                    continue
                body=b''
                if aid:
                    if tid not in contexts:contexts[tid]=PgnContext(source,tid)
                    choices=normalize({'preset':self.preset})
                    choices['headers']=list(dict.fromkeys(choices['headers']+['GameId','TournamentId','AttemptId']))
                    body=render_attempt(source,aid,context=contexts[tid],export_options=choices).encode('utf-8')
                changes.append((gid,tid,aid,body,old))
            more=bool(source.execute('SELECT 1 FROM pgn_changes WHERE seq>? LIMIT 1',(self.get('cursor',0),)).fetchone())
            source.rollback()
            if skipped:
                with self.db:self.db.executemany('DELETE FROM pending WHERE gid=?',skipped)
        if changes:
            rewrite=any(old is not None for *_,old in changes)
            self.verify()
            with self.db:
                self.db.execute('DELETE FROM append_bytes')
                count=self.get('games',0)
                for gid,tid,aid,body,old in changes:
                    count+=int(bool(aid))-int(bool(old and old['active'] and old['aid']))
                    self.db.execute('''INSERT INTO entries(gid,tid,aid,body,active) VALUES(?,?,?,?,?)
                      ON CONFLICT(gid) DO UPDATE SET tid=excluded.tid,aid=excluded.aid,body=excluded.body,active=excluded.active''', (gid,tid,aid,body,int(bool(aid))))
                    self.db.execute('DELETE FROM pending WHERE gid=?',(gid,))
                    if body and not rewrite:self.db.execute('INSERT INTO append_bytes(body) VALUES(?)',(body,))
                # Hash only new bytes during normal appends; the old SHA state is
                # rebuilt once on reopening, never by rereading all PGNs per game.
                if rewrite:
                    digest=hashlib.sha256()
                    for r in self.db.execute('SELECT body FROM entries WHERE active=1 ORDER BY seq'):digest.update(r[0])
                else:
                    if not hasattr(self,'digest'):
                        self.digest=hashlib.sha256()
                        with self.path.open('rb') as f:
                            for chunk in iter(lambda:f.read(1024*1024),b''):self.digest.update(chunk)
                    digest=self.digest.copy()
                    # Ensure separation even when an imported PGN omitted a final newline.
                    if self.get('size'):
                        with self.path.open('rb') as f:f.seek(-1,2);last=f.read(1)
                        if last!=b'\n':
                            first=self.db.execute('SELECT seq,body FROM append_bytes ORDER BY seq LIMIT 1').fetchone()
                            if first:
                                self.db.execute('UPDATE append_bytes SET body=? WHERE seq=?',(b'\n\n'+first['body'],first['seq']))
                                # Preserve this separator in later atomic rewrites.
                                gid=changes[0][0];self.db.execute('UPDATE entries SET body=CAST(?||body AS BLOB) WHERE gid=?',(b'\n\n',gid))
                    for r in self.db.execute('SELECT body FROM append_bytes ORDER BY seq'):digest.update(r[0])
                self.put('desired_hash',digest.hexdigest());self.put('dirty','rewrite' if rewrite else 'append')
                self.put('games',count)
            self.write_file();self.digest=digest
        count=self.get('games',0)
        pending=self.db.execute('SELECT count(*) FROM pending').fetchone()[0]
        self.status={'path':str(self.path),'preset':self.preset,'games':count,'pending':pending,
                     'state':'saving' if pending or more else 'saved','backlog':more,'updated':time.time(),'error':''}
        return self.status

    def close(self):
        if self.db:self.db.close();self.db=None
        if self.lock:self.lock.close();self.lock=None


class Outputs:
    def __init__(self,db):
        self.db=db;self.path=db.store.path;self.targets={};self.status={};self.task=None;self.closed=False
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='OfficialPgn')
        self.workspace=db.store.workspace_identity

    async def run(self,fn,*args):return await asyncio.get_running_loop().run_in_executor(self.executor,fn,*args)

    def prepare(self,body):
        if not body or not body.get('enabled'):return {'enabled':False}
        p=Path(str(body.get('path','')).strip()).expanduser()
        if not p.is_absolute() or p.suffix.lower()!='.pgn':raise ValueError('Choose an absolute path ending in .pgn.')
        p=p.resolve();folder=self.path.parent.resolve()
        if p.is_relative_to(folder):raise ValueError('Choose a PGN output folder outside Engine Arena’s managed data folder.')
        if not p.parent.is_dir():raise ValueError('The PGN output folder does not exist.')
        preset=body.get('preset','annotated');mode=body.get('mode','new')
        if preset not in PRESETS or mode not in ('new','append'):raise ValueError('Choose a PGN preset and file mode.')
        key=os.path.normcase(str(p))
        if key in self.targets:
            target=self.targets[key]
            if mode=='new':raise ValueError('That PGN file already exists. Choose Append / continue or a new filename.')
            if target.preset!=preset:raise ValueError('This PGN file already uses another preset. Select its existing preset or a new file.')
            target.recover()
        else:self.targets[key]=Target(key,self.workspace,preset,mode)
        self.targets[key].links=None
        self.status.pop(key,None)
        return {'enabled':True,'path':key,'preset':preset}

    def tick(self):
        try:
            with contextlib.closing(read_db(self.path)) as db:
                configs=db.execute('SELECT t.path,t.preset,l.tid FROM pgn_targets t JOIN pgn_links l ON l.path=t.path ORDER BY t.path,l.tid').fetchall()
        except (OSError,sqlite3.Error) as exc:
            self.status['']={'path':str(self.path),'state':'error','error':str(exc)}
            return
        self.status.pop('',None)
        grouped={}
        for r in configs:grouped.setdefault(r['path'],{'preset':r['preset'],'tids':[]})['tids'].append(r['tid'])
        for path,config in grouped.items():
            if self.status.get(path,{}).get('error'):continue
            try:
                if path not in self.targets:self.targets[path]=Target(path,self.workspace,config['preset'])
                self.status[path]=self.targets[path].sync(self.path,config['tids'])
            except Exception as exc:
                self.status[path]={'path':path,'preset':config['preset'],'state':'error','error':str(exc),'updated':time.time()}
        for path in set(self.status)-set(grouped):self.status.pop(path,None)
        for path in set(self.targets)-set(grouped):self.targets.pop(path).close()

    async def loop(self):
        while not self.closed:
            if not self.db.store.startup_pending:await self.run(self.tick)
            await asyncio.sleep(.05 if any(s.get('state')=='saving' for s in self.status.values()) else 1)

    def retry(self,path):
        self.status.pop(path,None)
        target=self.targets.pop(path,None)
        if target:target.close()
        self.tick()

    async def flush(self):
        # Used before deleting source records; never erase unsaved official PGNs.
        while True:
            await self.run(self.tick)
            errors=[s['error'] for s in self.status.values() if s.get('error')]
            if errors:raise ValueError('Automatic PGN saving needs attention before deleting records: '+errors[0])
            if not any(s.get('pending') or s.get('backlog') for s in self.status.values()):return

    async def close(self):
        self.closed=True
        if self.task:self.task.cancel();await asyncio.gather(self.task,return_exceptions=True)
        # The export queue/index survives an interrupted shutdown. Do not turn
        # closing a large tournament into a forced full export.
        await self.run(lambda:[t.close() for t in self.targets.values()])
        self.executor.shutdown(wait=False)
