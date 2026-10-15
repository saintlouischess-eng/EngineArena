// Inspect the actual clothing textures and original runtime skinning, on software GPU.
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const out=process.argv[2]||'test-output/v188-shirts';fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const proof={passed:false,errors:[],views:[]};
 try{
  const p=await browser.newPage({viewport:{width:1400,height:1000}});p.on('pageerror',e=>proof.errors.push(e.message));
  p.on('console',m=>{if(m.type()==='error'||/GL_INVALID/.test(m.text()))proof.errors.push(m.text())});
  await p.route('**/favicon.ico',r=>r.fulfill({status:200,contentType:'image/x-icon',body:fs.readFileSync('ui/engine-arena.ico')}));
  await p.goto('http://127.0.0.1:8772/prototypes/live-club/portraits.html?names=levy,hikaru');
  await p.waitForFunction(()=>window.review?.ready,{},{timeout:120000});
  for(const [view,x,z] of [['front',0,36],['angle',16,32],['back',0,-36]]){
   await p.evaluate(({x,z})=>{
    document.querySelector('#view').style.gridTemplateColumns='repeat(2,1fr)';
    for(const m of review.models){m.renderer.setSize(700,900);m.camera.aspect=700/900;m.camera.fov=29;m.camera.updateProjectionMatrix();m.camera.position.set(x,26,z);m.camera.lookAt(0,24.3,0)}review.render();
   },{x,z});
   await p.locator('#view').screenshot({path:path.join(out,view+'.png')});proof.views.push(view);
  }
  for(const [pose,t] of [['walking',6],['watching',40]]){
   const state=await p.evaluate(async t=>{
    const T=await import('/ui/three.module.js'),{clubVisitor}=await import('/ui/board3d-club-motion.js');
    return review.models.map((m,i)=>{
     m.actor??=clubVisitor(m.g,0,0,i===0?7:6);const state=m.actor.update(t);m.g.updateWorldMatrix(true,true);
     const center=m.g.localToWorld(new T.Vector3(0,24.3,0));m.camera.position.copy(center).add(new T.Vector3(5,1.7,36).applyQuaternion(m.g.getWorldQuaternion(new T.Quaternion())));m.camera.lookAt(center);m.renderer.render(m.scene,m.camera);
     return {name:m.name,visible:m.g.visible,activity:state.activity,walking:state.walking};
    });
   },t);
   assert(state.every(s=>s.visible));await p.locator('#view').screenshot({path:path.join(out,pose+'.png')});proof.views.push({pose,state});
  }
  assert.deepEqual(proof.errors,[]);proof.passed=true;
 }finally{await browser.close();fs.writeFileSync(path.join(out,'review.json'),JSON.stringify(proof,null,2))}
 console.log(JSON.stringify(proof));
})().catch(e=>{console.error(e);process.exitCode=1});
