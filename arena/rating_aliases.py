"""Compact profile provenance outside immutable rating identities."""
import json


def initialize(store):
    store.db.executescript('''CREATE TABLE IF NOT EXISTS rc_aliases(
      entry TEXT,profile_id TEXT,name TEXT,first_seen REAL,last_seen REAL,
      PRIMARY KEY(entry,profile_id,name));
      CREATE INDEX IF NOT EXISTS rc_alias_profile ON rc_aliases(profile_id);''')
    if store.one("SELECT 1 FROM preferences WHERE name='rating_aliases_backfilled_v1'"):return
    # Only join the exact recorded game/side. Retained compact records whose
    # original snapshots were deleted cannot safely be matched to today's library.
    with store.tx():
        for side in ('white','black'):
            store.db.execute(f'''INSERT OR IGNORE INTO rc_aliases
              SELECT r.{side},coalesce(json_extract(p.profile,'$.id'),''),json_extract(p.profile,'$.name'),min(r.ended),max(r.ended)
              FROM rc_games r JOIN games g ON g.id=r.gid JOIN participants p ON p.tid=g.tid AND p.slot=g.{side}
              WHERE json_extract(p.profile,'$.name') IS NOT NULL GROUP BY r.{side},p.profile''')
        store.db.execute("INSERT INTO preferences VALUES('rating_aliases_backfilled_v1','true')")


def record(db,entry,profile,stamp):
    db.execute('''INSERT INTO rc_aliases VALUES(?,?,?,?,?) ON CONFLICT(entry,profile_id,name)
      DO UPDATE SET first_seen=min(first_seen,excluded.first_seen),last_seen=max(last_seen,excluded.last_seen)''',
      (entry,str(profile.get('id') or ''),str(profile.get('name') or 'Unnamed profile'),stamp,stamp))


def renamed(db,profile):
    # Preserve former labels when a linked library profile is renamed, including
    # after its source tournament has been deleted. It remains a historical link.
    db.execute('''INSERT OR IGNORE INTO rc_aliases SELECT entry,profile_id,?,min(first_seen),max(last_seen)
      FROM rc_aliases WHERE profile_id=? GROUP BY entry,profile_id''',(profile['name'],profile['id']))


def read(db):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='rc_aliases'").fetchone():return {},{}
    aliases={}
    for row in db.execute('SELECT a.*,p.name current_name FROM rc_aliases a LEFT JOIN profiles p ON p.id=a.profile_id ORDER BY a.name,a.profile_id'):
        value=dict(row);aliases.setdefault(value.pop('entry'),[]).append(value)
    keys=[r[0] for r in db.execute('SELECT id FROM rc_entries ORDER BY id')];short={}
    for i,key in enumerate(keys):
        size=12
        for other in keys[max(0,i-1):i]+keys[i+1:i+2]:
            while size<len(key) and key[:size]==other[:size]:size+=1
        short[key]=key[:size]
    return aliases,short


def decorate(row,aliases,short):
    row['profiles']=aliases.get(row['id'],[])
    row['profile_names']=sorted({n for a in row['profiles'] for n in (a['name'],a['current_name']) if n},key=str.casefold)
    row['short_id']=short.get(row['id'],row['id'])
    row['provenance']='recorded profile association' if row['profiles'] else 'Profile association unavailable in retained evidence'
    return row
