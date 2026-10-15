"""Build offline CC0 room assets. Downloads are data only; verifies provider hashes."""
from pathlib import Path
import hashlib,json,urllib.request
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'build/room-assets';OUT=ROOT/'ui/scene-assets';OUT.mkdir(parents=True,exist_ok=True)
NOTICE=ROOT/'vendor/PolyHaven';NOTICE.mkdir(parents=True,exist_ok=True)
HEADERS={'User-Agent':'EngineArena asset build (local desktop; open-source)'}
records=[]
def fetch(url,path,md5=None):
    if not path.exists():
        with urllib.request.urlopen(urllib.request.Request(url,headers=HEADERS),timeout=90) as r:path.write_bytes(r.read())
    data=path.read_bytes()
    if md5 and hashlib.md5(data).hexdigest()!=md5:raise ValueError('Provider checksum mismatch: '+str(path))
    return data
def meta(asset):
    files=json.loads(fetch('https://api.polyhaven.com/files/'+asset,CACHE/(asset+'.json')))
    info=json.loads(fetch('https://api.polyhaven.com/info/'+asset,CACHE/(asset+'-info.json')))
    return files,info
def record(asset,info,source,path,changes):
    records.append(dict(file=path.name,asset=asset,authors=info['authors'],source='https://polyhaven.com/a/'+asset,download=source['url'],source_md5=source['md5'],license='CC0-1.0',changes=changes,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
for room,asset in [('club','lythwood_lounge'),('hall','ballroom'),('study','studio_country_hall'),('studio','photo_studio_loft_hall')]:
    files,info=meta(asset);source=files['tonemapped'];path=CACHE/(asset+'.jpg');fetch(source['url'],path,source['md5'])
    with Image.open(path) as im:
        for size,quality in [(2048,88),(4096,90),(8192,92)]:
            target=OUT/f'{room}-{size}.jpg';im.convert('RGB').resize((size,size//2),Image.Resampling.LANCZOS).save(target,quality=quality,optimize=True)
            record(asset,info,source,target,f'Tonemapped panorama resized to {size} x {size//2}; JPEG quality {quality}.')
    source=files['hdri']['1k']['hdr'];target=OUT/f'{room}-light.hdr';target.write_bytes(fetch(source['url'],CACHE/(asset+'-light.hdr'),source['md5']));record(asset,info,source,target,'Unmodified 1K HDR illumination.')
    print(room,flush=True)
for prefix,asset in [('wood','wood_table_001'),('leather','brown_leather')]:
    files,info=meta(asset)
    for name,key in [('color','Diffuse'),('normal','nor_gl'),('rough','Rough')]:
        source=files[key]['2k']['jpg'];target=OUT/f'{prefix}-{name}.jpg';target.write_bytes(fetch(source['url'],CACHE/f'{asset}-{name}.jpg',source['md5']));record(asset,info,source,target,'Unmodified 2K PBR texture.')
    print(prefix,flush=True)
(NOTICE/'provenance.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
(NOTICE/'LICENSE.txt').write_text('Poly Haven photographic environments and surface scans\n\nThese assets are free public-domain assets under CC0 1.0, not original Engine Arena artwork.\nLicense: https://creativecommons.org/publicdomain/zero/1.0/\nProvider license: https://polyhaven.com/license\nSee provenance.json for each author, original download, checksum and transformation.\n',encoding='utf-8')
print('Offline assets:',sum(r['bytes'] for r in records),'bytes')
