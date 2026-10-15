"""Pinned CC0 MakeHuman data only; no application/plugin installation or execution."""
import concurrent.futures, hashlib, json, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'vendor/MakeHuman/club-cast';DEST.mkdir(parents=True,exist_ok=True)
ASSET='8cf9645b975a98eea056b140df11a1d278da0d10'
CORE='a8bc2d54ff0ac92e78ff71431b1023eda42bf482'
manifest=DEST/'provenance.json'
# A shipped source snapshot is reproducible from its URL manifest without the
# developer's temporary API catalog. Fresh additions use the pinned asset tree.
catalog_path=ROOT/'test-output/makehuman-tree.json'
catalog=json.loads(catalog_path.read_text())['tree'] if catalog_path.exists() else []
folders=['clothes/'+n for n in ['male_casualsuit01','male_casualsuit04','male_elegantsuit01','female_casualsuit01','female_casualsuit02','female_elegantsuit01','female_sportsuit01','shoes01','shoes02']]+['hair/'+n for n in ['short01','short02','short03','bob01','bob02','braid01','afro01','ponytail01']]
folders.append('hair/short04')
skinNames=['old_lightskinned_male_diffuse.png','middleage_lightskinned_male_diffuse.png','middleage_darkskinned_male_diffuse.png','young_lightskinned_female_diffuse.png','old_lightskinned_female_diffuse.png','middleage_darkskinned_female_diffuse.png']
files=[]
for item in catalog:
    p=item['path']
    if (any(p.startswith('base/'+f+'/') for f in folders) and p.endswith(('.mhclo','.mhmat','.obj','_diffuse.png','_normal.png'))) or (p.startswith('base/skins/textures/') and p.split('/')[-1] in skinNames):
        root='https://media.githubusercontent.com/media/' if p.endswith('.png') else 'https://raw.githubusercontent.com/'
        files.append((p,root+f's20220526/makehuman-assets/{ASSET}/{p}'))
if not catalog and manifest.exists():files=[(v['file'],v['url']) for v in json.loads(manifest.read_text()) if v['file'].startswith('base/')]
if not files:raise RuntimeError('Missing pinned graphical-data manifest')
targets=['macrodetails/caucasian-male-old','macrodetails/asian-female-young','macrodetails/african-male-young','macrodetails/caucasian-female-young','macrodetails/universal-male-old-averagemuscle-averageweight','macrodetails/universal-female-young-averagemuscle-averageweight','macrodetails/universal-male-young-averagemuscle-averageweight','head/head-rectangular','head/head-round','head/head-oval','chin/chin-width-incr','nose/nose-curve-convex','nose/nose-scale-horiz-incr','head/head-fat-incr']
targets+=['macrodetails/caucasian-female-old','macrodetails/african-female-young','macrodetails/caucasian-male-young','macrodetails/universal-female-old-averagemuscle-averageweight','macrodetails/universal-male-young-averagemuscle-maxweight','macrodetails/universal-female-young-averagemuscle-maxweight']
cameos=json.loads((ROOT/'scripts/club-cameos.json').read_text(encoding='utf-8'))
targets+=['macrodetails/asian-male-young']+[name for c in cameos for name,amount in c['face']]
for t in sorted(set(targets)):
    p='makehuman/data/targets/'+t+'.target';files.append(('targets/'+t+'.target',f'https://raw.githubusercontent.com/makehumancommunity/makehuman/{CORE}/{p}'))
for p in ['rigs/default.mhskel','rigs/default_weights.mhw','eyes/low-poly/low-poly.obj','eyes/low-poly/low-poly.mhclo','eyes/materials/brown_eye.png','eyes/materials/brown.mhmat']:
    files.append((p,f'https://raw.githubusercontent.com/makehumancommunity/makehuman/{CORE}/makehuman/data/{p}'))
def fetch(item):
    name,url=item;path=DEST/name
    if path.exists():data=path.read_bytes()
    else:
        data=urllib.request.urlopen(url,timeout=45).read();assert not data.startswith(b'version https://git-lfs'),name
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    return {'file':name,'url':url,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:records=list(executor.map(fetch,files))
(DEST/'provenance.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print(f'{len(records)} files, {sum(r["bytes"] for r in records)/1024**2:.1f} MB; provenance recorded.')
