"""Editing a saved setup is allowed only before its first start or scheduling."""
import json
import random


def initialize(store):
    columns={r['name'] for r in store.db.execute('PRAGMA table_info(tournaments)')}
    if 'started_once' in columns:return
    # One migration, not an audit-log scan on every live snapshot. Include old
    # start/pause actions even if no game was dispatched between them.
    with store.tx():
        store.db.execute('ALTER TABLE tournaments ADD COLUMN started_once INTEGER NOT NULL DEFAULT 0')
        store.db.execute('ALTER TABLE tournaments ADD COLUMN setup_revision INTEGER NOT NULL DEFAULT 0')
        store.db.execute("""UPDATE tournaments SET started_once=1 WHERE state<>'paused'
          OR cursor<>0 OR round<>0 OR dependency<>'' OR id IN (SELECT tid FROM games)
          OR id IN (SELECT tid FROM round_state) OR id IN (SELECT tid FROM opening_suites)
          OR id IN (SELECT tid FROM audit WHERE action='state' AND json_extract(body,'$.state')='running')""")


def editable(store,t):
    return (t['state']=='paused' and not t['started_once'] and not t['cursor']
            and not t['round'] and not t['dependency']
            and not any(store.one(f'SELECT 1 FROM {table} WHERE tid=? LIMIT 1',(t['id'],))
                        for table in ('games','round_state','opening_suites')))


def require_editable(store,tid,revision=None):
    t=store.tournament(tid)
    if not t['can_edit']:raise ValueError('Only tournaments that have never started or scheduled games can be edited. Create a new tournament to change these conditions.')
    if revision is not None and (type(revision) is not int or revision!=t['setup_revision']):
        raise ValueError('This tournament setup changed while the editor was open. Reopen Edit setup to load the latest settings.')
    return t


def setup(store,tid):
    t=require_editable(store,tid)
    settings=dict(t['settings']);items=settings.pop('openings')
    return {**t,'settings':settings,'opening_count':len(items)}


def original_openings(settings):
    """Undo the recorded shuffle before applying a changed seed/order once."""
    items=settings['openings']
    if settings['opening_order']!='shuffle':return items
    order=list(range(len(items)));random.Random(settings['seed']).shuffle(order)
    original=[None]*len(items)
    for index,item in zip(order,items):original[index]=item
    return original


def edit(store,tid,name,settings,revision,profiles=None,openings=None,*,keep_openings=True,backup=True):
    from .store import encode
    from .rankings import create
    if type(revision) is not int:raise ValueError('Reopen Edit setup before saving this tournament.')
    old=require_editable(store,tid,revision)
    name=str(name).strip()
    if not name:raise ValueError('Enter a tournament name.')
    s={**old['settings'],**settings}
    if profiles is None:
        profiles=[json.loads(r['profile']) for r in store.rows('SELECT profile FROM participants WHERE tid=? ORDER BY slot',(tid,))]
    if keep_openings:
        if s['chess960']!=old['settings']['chess960']:
            raise ValueError('Choose a new opening source to change the chess variant.')
        openings=original_openings(old['settings'])
    else:
        # Metadata belongs to the newly selected source, never the previous book.
        for key in ('opening_inventory','opening_source'):
            if key not in settings:s.pop(key,None)
    profiles,s,total=store.prepare_tournament(profiles,s,openings)
    with store.tx():
        require_editable(store,tid,revision)
        for table in ('participants','aggregates','rankings','ranking_meta','rating_anchors'):
            store.db.execute(f'DELETE FROM {table} WHERE tid=?',(tid,))
        store.db.execute('UPDATE tournaments SET name=?,settings=?,total=?,setup_revision=setup_revision+1 WHERE id=?',(name,encode(s),total,tid))
        store.db.executemany('INSERT INTO participants VALUES(?,?,?)',((tid,i,encode(p)) for i,p in enumerate(profiles)))
        create(store,tid,s)
        store.db.executemany('INSERT INTO aggregates(tid,a,b) VALUES(?,?,-1)',((tid,i) for i in range(len(profiles))))
        store.db.execute('INSERT INTO report_revisions VALUES(?,1) ON CONFLICT(tid) DO UPDATE SET revision=revision+1',(tid,))
        store.audit(tid,'setup_edited',{'revision':revision+1,'previous_name':old['name'],'name':name,
            'previous_total':old['total'],'total':total,'participants':len(profiles),
            'changed_settings':[k for k in s if k!='openings' and s[k]!=old['settings'].get(k)],
            'opening_source_replaced':not keep_openings})
    if backup:store.backup()
    return store.tournament(tid)
