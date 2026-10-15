"""Copy reviewed original room artwork and pinned MIT addons into offline UI."""
from pathlib import Path
import shutil,re,json,hashlib
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'prototypes/live-club';UI=ROOT/'ui'
room=(SRC/'room.js').read_text(encoding='utf-8').replace("'/ui/","'./")
(UI/'board3d-club-room.js').write_text(room,encoding='utf-8')
names={p.name:'three-club-'+p.name for p in (SRC/'addons').rglob('*.js')}
for p in (SRC/'addons').rglob('*.js'):
    text=p.read_text(encoding='utf-8')
    text=re.sub(r"from ['\"]([^'\"]+)['\"]",lambda m:"from './"+('three.module.js' if m[1]=='three' else names[Path(m[1]).name])+"'",text)
    (UI/names[p.name]).write_text(text,encoding='utf-8')
shutil.copy2(SRC/'distant-staunton.glb',UI/'club-staunton.glb')
for p in (SRC/'cast').glob('*.glb'):shutil.copy2(p,UI/('club-'+p.name))
shutil.copy2(SRC/'cast/manifest.json',ROOT/'vendor/MakeHuman/club-cast/derived.json')
record={'version':'0.186.1','license':'MIT','adaptation':'Imports rewritten to the existing offline Three module and flat local filenames; implementation unchanged.','files':[]}
for p in (SRC/'addons').rglob('*.js'):
 record['files'].append({'original':str(p.relative_to(SRC)),'file':names[p.name],'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'sha256':hashlib.sha256((UI/names[p.name]).read_bytes()).hexdigest()})
(ROOT/'vendor/Three/club-addons.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('Synced room, distant set, cast and',len(names),'pinned Three modules')

