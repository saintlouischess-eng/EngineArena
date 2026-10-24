"""Compact, transactional cross-tournament rating evidence. No moves or PGNs.

Called inside the official-result transaction; fitting is exclusively read-only
and outside the database actor. A rating entry describes a configuration, never
just a mutable profile name. Destructive commands have separate recovery receipts.
"""
from dataclasses import asdict
import hashlib
import json
import math
import time
import uuid

from .models import TimeControl

CATEGORIES = ('bullet', 'blitz', 'rapid', 'classical', 'nodes', 'depth', 'movetime', 'handicap')
RULES = {'bullet': 180, 'blitz': 600, 'classical': 3600}


def encode(v): return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
def digest(v): return hashlib.sha256(encode(v).encode()).hexdigest()


def initialize(store):
    store.db.executescript('''
      CREATE TABLE IF NOT EXISTS rc_pools(id TEXT PRIMARY KEY,name TEXT,automatic INTEGER,epoch REAL,revision INTEGER,rules TEXT);
      CREATE TABLE IF NOT EXISTS rc_sources(pool TEXT,tid TEXT,name TEXT,context TEXT,enabled INTEGER,explicit INTEGER,
        cursor INTEGER DEFAULT -1,retained INTEGER DEFAULT 0,PRIMARY KEY(pool,tid));
      CREATE TABLE IF NOT EXISTS rc_entries(id TEXT PRIMARY KEY,name TEXT,threads INTEGER,body TEXT,first_seen REAL);
      CREATE TABLE IF NOT EXISTS rc_conditions(id TEXT PRIMARY KEY,hardware TEXT,body TEXT);
      CREATE TABLE IF NOT EXISTS rc_games(pool TEXT,gid TEXT,aid TEXT,tid TEXT,pair_no INTEGER,leg INTEGER,paired INTEGER,
        white TEXT,black TEXT,category TEXT,result TEXT,reason TEXT,conditions TEXT,ended REAL,PRIMARY KEY(pool,gid));
      CREATE INDEX IF NOT EXISTS rc_games_category ON rc_games(pool,category,tid,pair_no);
      CREATE INDEX IF NOT EXISTS rc_games_source ON rc_games(tid,pool);
      CREATE INDEX IF NOT EXISTS rc_games_identity ON rc_games(gid);
      CREATE INDEX IF NOT EXISTS rc_games_conditions ON rc_games(pool,conditions);
      CREATE TABLE IF NOT EXISTS rc_anchors(pool TEXT,category TEXT,entry TEXT,rating REAL,PRIMARY KEY(pool,category));
      CREATE TABLE IF NOT EXISTS rc_refs(pool TEXT,category TEXT,entry TEXT,PRIMARY KEY(pool,category));
      CREATE TABLE IF NOT EXISTS rc_gates(pool TEXT,category TEXT,epoch REAL,PRIMARY KEY(pool,category));
      CREATE TABLE IF NOT EXISTS rc_imports(pool TEXT,tid TEXT,category TEXT,stamp REAL,PRIMARY KEY(pool,tid,category));
      CREATE TABLE IF NOT EXISTS rc_blocks(pool TEXT,entry TEXT,PRIMARY KEY(pool,entry));
      CREATE TABLE IF NOT EXISTS rc_links(pool TEXT,entry TEXT,predecessor TEXT,PRIMARY KEY(pool,entry));
      CREATE TABLE IF NOT EXISTS rc_families(pool TEXT,entry TEXT,family TEXT,PRIMARY KEY(pool,entry));
      CREATE TABLE IF NOT EXISTS rc_lineage(pool TEXT,family TEXT,configuration TEXT,entry TEXT,stamp REAL,PRIMARY KEY(pool,family,configuration));
      CREATE TABLE IF NOT EXISTS rc_receipts(seq INTEGER PRIMARY KEY);
      CREATE TRIGGER IF NOT EXISTS rc_stage_change AFTER UPDATE OF valid ON event_children
        WHEN old.valid<>new.valid BEGIN
        UPDATE rc_pools SET revision=revision+1 WHERE id IN (SELECT pool FROM rc_sources WHERE tid=new.tid);
      END;
    ''')
    store.db.execute('INSERT OR IGNORE INTO rc_pools VALUES(?,?,?,?,?,?)', ('main', 'Engine Arena ratings', 1, time.time(), 0, encode(RULES)))
    from .rating_aliases import initialize as initialize_aliases
    initialize_aliases(store)


def control(value):
    tc = TimeControl.parse(value)
    keys = {'nodes': ('nodes',), 'depth': ('depth',), 'movetime': ('seconds',),
            'sudden_death': ('seconds',), 'fischer': ('seconds', 'increment'),
            'delay': ('seconds', 'delay'), 'bronstein': ('seconds', 'delay'), 'staged': ('stages', 'repeat')}[tc.kind]
    return {'kind': tc.kind, **{k: getattr(tc, k) for k in keys}}


def nominal(value):
    """Nominal 60-move allocation, not a prediction of actual game duration."""
    tc = TimeControl.parse(value)
    if tc.kind in ('nodes', 'depth', 'movetime'): return None
    if tc.kind != 'staged':
        return tc.seconds + 60 * (tc.increment if tc.kind == 'fischer' else tc.delay if tc.kind in ('delay', 'bronstein') else 0)
    left, total, index = 60, 0, 0
    while left:
        stage = tc.stages[index]; moves = min(left, stage.get('moves') or left)
        total += stage['seconds'] + moves * stage.get('increment', 0); left -= moves
        if index + 1 < len(tc.stages): index += 1
        elif not tc.repeat:
            total += left * stage.get('increment', 0); break
    return total


def category(white, black, rules):
    w, b = control(white), control(black)
    # Unequal fixed node/depth budgets remain in their own testing category;
    # those budgets are also part of each entry's immutable configuration.
    if w['kind'] == b['kind'] and w['kind'] in ('nodes', 'depth', 'movetime'): return w['kind']
    if w != b: return 'handicap'
    seconds = nominal(w)
    return 'bullet' if seconds < rules['bullet'] else 'blitz' if seconds <= rules['blitz'] else 'rapid' if seconds < rules['classical'] else 'classical'


def entry(profile, evidence, settings, tc, handicap=False, hardware=None, scope=None):
    from .engine_options import find_name
    options = {str(k).casefold(): o.get('default') for k, o in profile.get('advertised', {}).items() if o.get('type') != 'button'}
    options.update({str(k).casefold(): v for k, v in profile.get('options', {}).items()})
    runtime = evidence.get('options')
    if runtime is not None: options.update({str(k).casefold(): v for k, v in runtime.items()})
    if runtime is None:
        for resource,default in (('Threads',1),('Hash',1024)):
            actual=find_name(profile.get('advertised',{}),resource)
            if actual and not find_name(profile.get('options',{}),resource):options[actual.casefold()]=profile.get(resource.lower(),default)
    thread_key = find_name(options, 'Threads')
    count = options.get(thread_key) if thread_key else None
    if count is None and runtime is None and find_name(profile.get('advertised', {}), 'Threads'): count = profile.get('threads', 1)
    try: threads = int(count) if count is not None and int(count) > 0 else None
    except (TypeError, ValueError): threads = None
    if thread_key: options.pop(thread_key, None)
    options['threads'] = threads
    hash_key = find_name(options, 'Hash')
    if hash_key: options['hash'] = options.pop(hash_key)
    elif find_name(profile.get('advertised', {}), 'Hash'): options['hash'] = profile.get('hash', 1024)
    options.update(ponder=bool(settings.get('ponder')),uci_chess960=bool(settings.get('chess960')))
    fingerprints = profile.get('fingerprints', {})
    sha = fingerprints.get('executable', {}).get('sha256') or profile.get('sha256')
    identity = evidence.get('identity') or profile.get('identity') or {}
    version = identity.get('name') or profile.get('name', 'Unnamed engine')
    configuration = {'options': options, 'args': profile.get('args', []), 'affinity': profile.get('affinity'),
        'move_book': profile.get('move_book') if settings.get('use_engine_books') else None,
        'limit': control(tc) if tc['kind'] in ('nodes','depth','movetime') or handicap else None}
    body = {'version': version, 'sha256': sha, 'networks': sorted(n.get('sha256', '') for n in fingerprints.get('networks', [])),
        'observed_network': (evidence.get('network') or {}).get('sha256'), **configuration}
    if not sha: body['unverified_identity'] = profile.get('id') or profile.get('path') or profile.get('name')
    from .rating_compute import describe, label
    legacy_key = digest(body)
    compute = describe(body, profile, evidence, hardware or {}, scope)
    if compute:
        body.update(compute=compute, legacy_identity=legacy_key)
        configuration['compute'] = compute
    return digest(body), label(body, threads), threads, body, digest(configuration)


def bump(db, pool): db.execute('UPDATE rc_pools SET revision=revision+1 WHERE id=?', (pool,))


def sync(store, g, aid, pool_id=None):
    """No commits here: the result and its compact contribution are atomic."""
    db = store.db
    pools = list(db.execute('SELECT * FROM rc_pools' + (' WHERE id=?' if pool_id else ''), (pool_id,) if pool_id else ()))
    if not pools: return
    tracked={r['pool'] for r in db.execute('SELECT pool FROM rc_games WHERE gid=?',(g['id'],))}
    for pool in pools:
        if db.execute('DELETE FROM rc_games WHERE pool=? AND gid=?', (pool['id'], g['id'])).rowcount: bump(db,pool['id'])
    if not aid:
        return
    a = store.one('SELECT * FROM attempts WHERE id=?', (aid,))
    if not a or a['result'] not in ('1-0', '0-1', '1/2-1/2') or a['mode'] == 'diagnostic' or g['invalid'] or min(g['white'],g['black']) < 0: return
    t = store.one('SELECT name,settings FROM tournaments WHERE id=?',(g['tid'],)); s = json.loads(t['settings']); context = s.get('event_context') or {}
    first = store.one('SELECT started FROM attempts WHERE gid=? ORDER BY seq LIMIT 1', (g['id'],))['started']
    recorded = store.one("SELECT min(ended) stamp FROM attempts WHERE gid=? AND result IN ('1-0','0-1','1/2-1/2') AND mode<>'diagnostic'",(g['id'],))['stamp']
    profiles = [json.loads(store.one('SELECT profile FROM participants WHERE tid=? AND slot=?', (g['tid'], slot))['profile']) for slot in (g['white'],g['black'])]
    from .knockout import game_control
    opening = json.loads(g['opening']) if isinstance(g['opening'], str) else g['opening']
    clocks = json.loads(a['clocks'] or '{}')
    controls = [control((clocks.get(side) or {}).get('control') or game_control(s, p, opening)) for side,p in zip(('white','black'),profiles)]
    evidence = {r['side']: json.loads(r['body']) for r in store.rows('SELECT ae.side,e.body FROM attempt_engines ae JOIN engine_evidence e ON e.id=ae.evidence WHERE ae.aid=?', (aid,))}
    session = store.one('SELECT s.body FROM run_attempts a JOIN run_sessions s ON s.id=a.sid WHERE a.aid=?', (aid,))
    hardware = json.loads(session['body']).get('hardware', {}) if session else {}
    hardware = {k:v for k,v in hardware.items() if k in ('cpu','physical_cores','logical_processors','ram_gib','os','gpus')}
    condition_body = {'hardware': hardware, 'controls': sorted(controls,key=encode), 'chess960': s.get('chess960',False),
        'opening_book': s.get('opening_file') or s.get('opening_inventory'), 'ponder': s.get('ponder',False),
        'adjudication': {k:s.get(k) for k in ('resign_cp','draw_cp','max_plies','claim_draws','syzygy_path','tolerance','overhead')},
        'adaptive': s.get('format') in ('sprt','knockout','double_elimination','swiss')}
    condition_key = digest(condition_body); hardware_key = digest(hardware)
    for pool in pools:
        pid = pool['id']; source = store.one('SELECT * FROM rc_sources WHERE pool=? AND tid=?', (pid,g['tid']))
        cat = category(*controls,json.loads(pool['rules']))
        gate = store.one('SELECT epoch FROM rc_gates WHERE pool=? AND category=?', (pid,cat))
        cutoff = max(pool['epoch'],gate['epoch'] if gate else 0)
        if source and not source['enabled']: continue
        imported=store.one('SELECT stamp FROM rc_imports WHERE pool=? AND tid=? AND category=?',(pid,g['tid'],cat)) if source and source['explicit'] else None
        if pid not in tracked and not (imported and imported['stamp']>=cutoff) and (not pool['automatic'] or first < cutoff): continue
        entries = [entry(p,evidence.get(side,{}),s,tc,cat=='handicap',hardware,g['tid']) for side,p,tc in zip(('white','black'),profiles,controls)]
        if entries[0][0] == entries[1][0]: continue # Same immutable configuration cannot compare with itself.
        if any(store.one('SELECT 1 FROM rc_blocks WHERE pool=? AND entry IN (?,?)',
                        (pid,e[0],e[3].get('legacy_identity',e[0]))) for e in entries): continue
        db.execute('INSERT OR IGNORE INTO rc_sources(pool,tid,name,context,enabled,explicit) VALUES(?,?,?,?,1,0)', (pid,g['tid'],t['name'],encode(context)))
        for slot,e in zip((g['white'],g['black']),entries):
            key,label,threads,body,config = e
            db.execute('INSERT OR IGNORE INTO rc_entries VALUES(?,?,?,?,?)',(key,label,threads,encode(body),first))
            from .rating_aliases import record
            record(db,key,profiles[0 if slot==g['white'] else 1],recorded)
            identities = context.get('identities') or []
            if slot < len(identities):
                family = str(context.get('id')) + ':' + str(identities[slot])
                old = store.one('SELECT * FROM rc_lineage WHERE pool=? AND family=? AND configuration=?', (pid,family,config))
                if old and old['entry'] != key and old['stamp'] < first:
                    db.execute('INSERT OR IGNORE INTO rc_links VALUES(?,?,?)',(pid,key,old['entry']))
                if not old or old['stamp'] < first:
                    db.execute('INSERT OR REPLACE INTO rc_lineage VALUES(?,?,?,?,?)',(pid,family,config,key,first))
        db.execute('INSERT OR IGNORE INTO rc_conditions VALUES(?,?,?)',(condition_key,hardware_key,encode(condition_body)))
        db.execute('INSERT OR IGNORE INTO rc_refs VALUES(?,?,?)',(pid,cat,min(e[0] for e in entries)))
        db.execute('INSERT OR REPLACE INTO rc_games VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (pid,g['id'],aid,g['tid'],g['pair_no'],g['leg'],int(s['paired']),entries[0][0],entries[1][0],cat,a['result'],a['reason'],condition_key,recorded))
        bump(db,pid)


def listing(store):
    return {'pools': [dict(r)|{'rules':json.loads(r['rules'])} for r in store.db.execute('SELECT * FROM rc_pools ORDER BY rowid')], 'categories': CATEGORIES}


def exclusions(store,pool,offset=0):
    if offset<0:raise ValueError('Invalid page')
    return {'items':store.rows('SELECT b.entry,e.name FROM rc_blocks b LEFT JOIN rc_entries e ON e.id=b.entry WHERE b.pool=? ORDER BY e.name,b.entry LIMIT 50 OFFSET ?',(pool,offset)),
            'total':store.one('SELECT count(*) n FROM rc_blocks WHERE pool=?',(pool,))['n'],'offset':offset}


def sources(store,pool,search='',offset=0):
    if offset<0: raise ValueError('Invalid page')
    params=('%'+search+'%',)
    # Union also shows compact retained sources whose tournament was deleted.
    sql='''WITH available AS (SELECT t.id tid,t.name,t.state FROM tournaments t UNION ALL
      SELECT tid,name,'retained' FROM rc_sources WHERE pool=? AND retained=1)
      SELECT a.*,s.enabled,s.explicit,s.cursor,s.retained,(SELECT count(*) FROM rc_games g WHERE g.pool=? AND g.tid=a.tid) games
      FROM available a LEFT JOIN rc_sources s ON s.pool=? AND s.tid=a.tid '''
    # Qualify the name because source and tournament labels share the same name.
    sql=sql+'WHERE a.name LIKE ?'
    rows=store.rows(sql+' ORDER BY a.name,a.tid LIMIT 50 OFFSET ?', (pool,pool,pool,*params,offset))
    total=store.one('SELECT count(*) n FROM ('+sql+')',(pool,pool,pool,*params))['n']
    return {'items':rows,'total':total,'offset':offset}


def import_batch(store,pool,tid,restart=False):
    store.tournament(tid)
    if not store.one('SELECT 1 FROM rc_pools WHERE id=?',(pool,)): raise ValueError('Rating list not found')
    with store.tx():
        if restart:
            t=store.tournament(tid)
            store.db.execute('INSERT OR REPLACE INTO rc_sources VALUES(?,?,?,?,1,1,-1,0)',(pool,tid,t['name'],encode(t['settings'].get('event_context',{}))))
            store.db.executemany('INSERT OR REPLACE INTO rc_imports VALUES(?,?,?,?)',[(pool,tid,c,time.time()) for c in CATEGORIES])
        source=store.one('SELECT * FROM rc_sources WHERE pool=? AND tid=?',(pool,tid))
        if not source or not source['explicit'] or not source['enabled']: raise ValueError('Start an explicit history import first')
        rows=store.rows('SELECT * FROM games WHERE tid=? AND number>? ORDER BY number LIMIT 200',(tid,source['cursor']))
        for g in rows:
            if g['official'] and not g['invalid']: sync(store,g,g['official'],pool)
        cursor=rows[-1]['number'] if rows else source['cursor']
        store.db.execute('UPDATE rc_sources SET cursor=? WHERE pool=? AND tid=?',(cursor,pool,tid))
        more=bool(store.one('SELECT 1 FROM games WHERE tid=? AND number>? LIMIT 1',(tid,cursor)))
    return {'cursor':cursor,'done':not more,'games':store.one('SELECT count(*) n FROM rc_games WHERE pool=? AND tid=?',(pool,tid))['n']}


def command(store,body):
    action=body.get('action');pool=body.get('pool','main')
    if action=='import': return import_batch(store,pool,body['tid'],bool(body.get('restart')))
    if action=='create':
        name=str(body.get('name','')).strip()
        if not name or len(name)>120: raise ValueError('Enter a rating-list name of 1–120 characters')
        pool=uuid.uuid4().hex
        with store.tx(): store.db.execute('INSERT INTO rc_pools VALUES(?,?,?,?,0,?)',(pool,name,int(bool(body.get('automatic',True))),time.time(),encode(RULES)))
        return {'id':pool}
    current=store.one('SELECT * FROM rc_pools WHERE id=?',(pool,))
    if not current: raise ValueError('Rating list not found')
    if action in ('reset','remove_source','remove_entry','delete_pool'):
        from .rating_cleanup import request
        return request(store,body|{'pool':pool})
    with store.tx():
        if action=='configure':
            rules=body.get('rules',json.loads(current['rules']))
            if set(rules)!=set(RULES) or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in rules.values()) or not 0<rules['bullet']<rules['blitz']<rules['classical']:
                raise ValueError('Category boundaries must be positive and increasing')
            if rules!=json.loads(current['rules']) and store.one('SELECT 1 FROM rc_games WHERE pool=? LIMIT 1',(pool,)):
                raise ValueError('Reset this rating list before changing category boundaries; then import the desired history')
            store.db.execute('UPDATE rc_pools SET automatic=?,rules=? WHERE id=?',(int(bool(body.get('automatic',current['automatic']))),encode(rules),pool))
        elif action=='anchor':
            cat=body.get('category');key=body.get('entry')
            if cat not in CATEGORIES: raise ValueError('Choose one time-control category')
            if key:
                rating=body.get('rating')
                if isinstance(rating,bool) or not isinstance(rating,(int,float)) or not math.isfinite(rating): raise ValueError('Enter a finite reference rating')
                if not store.one('SELECT 1 FROM rc_games WHERE pool=? AND category=? AND (white=? OR black=?) LIMIT 1',(pool,cat,key,key)): raise ValueError('The reference must have results in this category')
                store.db.execute('INSERT OR REPLACE INTO rc_anchors VALUES(?,?,?,?)',(pool,cat,key,rating))
            else: store.db.execute('DELETE FROM rc_anchors WHERE pool=? AND category=?',(pool,cat))
        elif action=='predecessor':
            key=body['entry'];previous=body.get('predecessor')
            if previous:
                from .rating_compute import continuity
                rows=store.rows('SELECT id,threads,body FROM rc_entries WHERE id IN (?,?)',(key,previous))
                byid={r['id']:r for r in rows}
                compatible = [continuity(json.loads(r['body']),r['threads']) for r in rows]
                if len(rows)!=2 or compatible[0] is None or compatible[0]!=compatible[1]:
                    raise ValueError('Choose a predecessor with matching CPU threads or verified GPU hardware and backend')
                seen={key};node=previous
                while node:
                    if node in seen: raise ValueError('Version links cannot form a cycle')
                    seen.add(node);link=store.one('SELECT predecessor FROM rc_links WHERE pool=? AND entry=?',(pool,node));node=link['predecessor'] if link else None
                store.db.execute('INSERT OR REPLACE INTO rc_links VALUES(?,?,?)',(pool,key,previous))
            else: store.db.execute('DELETE FROM rc_links WHERE pool=? AND entry=?',(pool,key))
        elif action=='family':
            key=body.get('entry');family=body.get('family','')
            if not store.one('SELECT 1 FROM rc_entries WHERE id=?',(key,)):raise ValueError('Rating entry not found')
            if not isinstance(family,str) or len(family)>120 or any(ord(c)<32 for c in family):raise ValueError('Enter a family name of at most 120 characters')
            family=family.strip()
            if family:store.db.execute('INSERT OR REPLACE INTO rc_families VALUES(?,?,?)',(pool,key,family))
            else:store.db.execute('DELETE FROM rc_families WHERE pool=? AND entry=?',(pool,key))
        elif action=='restore_entry': store.db.execute('DELETE FROM rc_blocks WHERE pool=? AND entry=?',(pool,body['entry']))
        else: raise ValueError('Unknown rating-center action')
        bump(store.db,pool)
    return {'ok':True}
