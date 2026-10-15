"""Presentation-only family grouping. Never merges rating identities or evidence."""
import math
import re
import unicodedata
from .rating_center import encode
from .rating_compute import continuity


def automatic(version):
    name=unicodedata.normalize('NFKC',str(version)).strip()
    # Keep complete multi-word names; remove a separated version/build suffix.
    # Embedded digits (Lc0, Velvet2, etc.) remain part of the family name.
    parts=re.split(r'(?:[\s_]+(?=v?\d|dev(?:\b|[-_])|development\b|git[-_])|[-_](?=v?\d))',name,maxsplit=1,flags=re.I)
    return parts[0].strip(' _-') or name or 'Unnamed engine'


def read(db,pool):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='rc_families'").fetchone():return {}
    return {r['entry']:r['family'] for r in db.execute('SELECT entry,family FROM rc_families WHERE pool=?',(pool,))}


def describe(row,overrides):
    guessed=automatic(row['configuration'].get('version',row['name']))
    row.update(family=overrides.get(row['id'],guessed),family_override=overrides.get(row['id']),family_automatic=guessed)


def key(row):
    body=row['configuration'];compatible=continuity(body,row['threads'])
    if compatible is None or compatible['kind']=='cpu' and row['threads'] is None:
        return (row['family'].casefold(),row['id'])
    # Unequal fixed limits/clock handicaps must not silently compete for one row.
    return (row['family'].casefold(),encode(compatible),encode(body.get('limit')))


def select(rows):
    groups={}
    for row in rows:groups.setdefault(key(row),[]).append(row)
    result=[]
    for members in groups.values():
        def order(r):
            value=r.get('rating');rated=value is not None and math.isfinite(value) and r.get('samples',0)>0
            return (not rated,-round(value,9) if rated else 0,-r.get('samples',0),-r.get('games',0),r['name'].casefold(),r['id'])
        winner=min(members,key=order);winner['family_versions']=len(members);result.append(winner)
    return result
