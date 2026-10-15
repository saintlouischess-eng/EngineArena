"""Copy a bounded subset of the already-used Three version into this prototype."""
import base64, hashlib, io, json, re, tarfile, urllib.request
from pathlib import Path, PurePosixPath
ROOT=Path(__file__).resolve().parents[2]
provenance=json.loads((ROOT/'vendor/Three/provenance.json').read_text(encoding='utf-8'))
data=urllib.request.urlopen(provenance['url'],timeout=40).read()
assert 'sha512-'+base64.b64encode(hashlib.sha512(data).digest()).decode()==provenance['integrity']
target=Path(__file__).resolve().parent/'addons'
pending=['postprocessing/RenderPass.js','postprocessing/EffectComposer.js','postprocessing/SSAOPass.js','postprocessing/OutputPass.js','lights/RectAreaLightUniformsLib.js']
seen={}
with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
    while pending:
        name=pending.pop()
        if name in seen:continue
        content=archive.extractfile('package/examples/jsm/'+name).read()
        path=(target/name).resolve();assert path.is_relative_to(target)
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
        seen[name]=hashlib.sha256(content).hexdigest()
        for ref in re.findall(r"from\s+['\"]([^'\"]+)['\"]",content.decode()):
            if ref.startswith('.'):
                relative=(path.parent/ref).resolve();assert relative.is_relative_to(target)
                pending.append(relative.relative_to(target).as_posix())
(target/'LICENSE.txt').write_text((ROOT/'vendor/Three/LICENSE.txt').read_text(encoding='utf-8'),encoding='utf-8')
(target/'provenance.json').write_text(json.dumps({'version':provenance['version'],'source':provenance['url'],'integrity':provenance['integrity'],'files':seen},indent=2),encoding='utf-8')
print(f'Verified {len(seen)} MIT-licensed Three addon files for the isolated prototype.')
