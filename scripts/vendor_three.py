"""Fetch pinned MIT Three.js sources; no package scripts are executed."""
from pathlib import Path
import base64,hashlib,io,json,tarfile,urllib.request
from three_lut_patch import patch_lut
ROOT=Path(__file__).resolve().parents[1]
VERSION='0.186.1'
INTEGRITY='blFeqb49wRCSGUGj7gtpfnSGHy2lwDk94RhUmS1c/hTby70kvChbWpkJ4Pm1390LqzzvTmzgXKHPEafJwCb8jA=='
url=f'https://registry.npmjs.org/three/-/three-{VERSION}.tgz'
cached=ROOT/'build'/f'three-{VERSION}.tgz'
data=cached.read_bytes() if cached.exists() else urllib.request.urlopen(url,timeout=60).read()
assert base64.b64encode(hashlib.sha512(data).digest()).decode()==INTEGRITY
files={'build/three.core.js':'three.core.js','build/three.module.js':'three.module.js',
       'examples/jsm/loaders/GLTFLoader.js':'three-gltf.js',
       'examples/jsm/loaders/HDRLoader.js':'three-hdr.js',
       'examples/jsm/objects/GroundedSkybox.js':'three-grounded.js',
       'examples/jsm/utils/BufferGeometryUtils.js':'three-geometry-utils.js',
       'examples/jsm/environments/RoomEnvironment.js':'three-room.js',
       'examples/jsm/utils/SkeletonUtils.js':'three-skeleton-utils.js'}
with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
 for source,target in files.items():
  text=archive.extractfile('package/'+source).read().decode()
  text=text.replace("from 'three'","from './three.module.js'").replace("from '../utils/BufferGeometryUtils.js'","from './three-geometry-utils.js'").replace("from '../utils/SkeletonUtils.js'","from './three-skeleton-utils.js'").replace('./three.core.min.js','./three.core.js')
  if target=='three.module.js':text=patch_lut(text)
  (ROOT/'ui'/target).write_text(text,encoding='utf-8')
 folder=ROOT/'vendor/Three';folder.mkdir(parents=True,exist_ok=True)
 (folder/'LICENSE.txt').write_bytes(archive.extractfile('package/LICENSE').read())
 (folder/'provenance.json').write_text(json.dumps({'package':'three','version':VERSION,'url':url,'integrity':'sha512-'+INTEGRITY,'files':files,'modifications':'Local import paths; renderer-owned DFG lighting LUT with explicit disposal (scripts/three_lut_patch.py) to prevent retired WebGL contexts being retained.'},indent=2)+'\n')
print('Verified Three.js',VERSION,'and wrote',len(files),'local modules.')
