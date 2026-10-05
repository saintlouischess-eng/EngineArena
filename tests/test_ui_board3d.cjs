const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const B=require('../ui/board3d.js');
test('Six offline Staunton sculptures have valid geometry, normals and embedded wood maps',()=>{
 const bytes=fs.readFileSync(path.join(__dirname,'../ui/staunton1849.glb'));
 assert.equal(bytes.readUInt32LE(0),0x46546c67);assert.equal(bytes.readUInt32LE(4),2);assert.equal(bytes.readUInt32LE(8),bytes.length);
 const length=bytes.readUInt32LE(12),g=JSON.parse(bytes.subarray(20,20+length)),bin=bytes.subarray(28+length);
 assert.deepEqual(g.nodes.filter(n=>n.mesh!==undefined).map(n=>n.name).sort(),[...'bknpqr']);
 assert.equal(g.buffers.length,1);assert(!g.buffers[0].uri);assert(g.images.length>=3);assert(g.images.every(i=>i.bufferView!==undefined&&!i.uri));
 const knight=g.meshes[g.nodes.find(n=>n.name==='n').mesh];
 assert(knight.primitives.reduce((sum,p)=>sum+g.accessors[p.indices].count/3,0)<=130000,'Knight must stay within the interactive geometry budget');
 assert(g.meshes.reduce((sum,m)=>sum+m.primitives.reduce((n,p)=>n+g.accessors[p.indices].count/3,0),0)<=350000,'Set geometry budget');
 assert(g.materials[0].normalTexture);assert(g.materials[0].pbrMetallicRoughness.metallicRoughnessTexture);
 for(const mesh of g.meshes)for(const p of mesh.primitives){
  assert(p.attributes.TEXCOORD_0!==undefined);assert.equal(g.accessors[p.indices].count%3,0);
  for(const name of ['POSITION','NORMAL']){
   const a=g.accessors[p.attributes[name]],v=g.bufferViews[a.bufferView];assert.equal(a.componentType,5126);assert.equal(a.type,'VEC3');
   for(let i=0;i<a.count;i++){const at=(v.byteOffset||0)+(a.byteOffset||0)+i*(v.byteStride||12),xyz=[0,4,8].map(k=>bin.readFloatLE(at+k));assert(xyz.every(Number.isFinite));if(name==='NORMAL')assert(Math.abs(Math.hypot(...xyz)-1)<.001)}
  }
 }
});
test('Saved camera settings stay within usable limits',()=>{
 assert.deepEqual(B.settings({}),{angle:50,orbit:0,zoom:1,lift:0});
 assert.deepEqual(B.settings({angle:2,orbit:999,zoom:3}),{angle:25,orbit:180,zoom:2.4,lift:0});
 assert.equal(B.settings({zoom:.1}).zoom,.6);
 assert.equal(B.settings({zoom:1.85}).zoom,1.85);
 assert.equal(B.settings({lift:9}).lift,.5);assert.equal(B.settings({lift:-9}).lift,-.5);assert.equal(B.settings({lift:NaN}).lift,0);
});
test('Studio dependencies resolve locally and keep the MIT notice',()=>{
 for(const file of fs.readdirSync(path.join(__dirname,'../ui')).filter(n=>n.startsWith('three')&&n.endsWith('.js'))){
  const source=fs.readFileSync(path.join(__dirname,'../ui',file),'utf8').replace(/\/\*[\s\S]*?\*\//g,'');
  for(const m of source.matchAll(/^(?:import|export)\s+[^;]+?\sfrom\s+['"]([^'"]+)['"]/gm))assert(fs.existsSync(path.join(__dirname,'../ui',m[1])),`${file}: ${m[1]}`);
 }
 assert.match(fs.readFileSync(path.join(__dirname,'../vendor/Three/LICENSE.txt'),'utf8'),/MIT License/);
 assert.equal(B.isReady(),false);
});
