// Review the real local model under portrait and club lighting. Software GPU only.
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const out=process.argv[2]||'test-output/magnus-hair';fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const proof={passed:false,errors:[],views:[]};
 try{
  const p=await browser.newPage({viewport:{width:960,height:795}});p.on('pageerror',e=>proof.errors.push(e.message));
  // The repository preview server has no root icon route; use the app's icon.
  await p.route('http://127.0.0.1:8772/favicon.ico',r=>r.fulfill({status:200,contentType:'image/x-icon',body:fs.readFileSync('ui/engine-arena.ico')}));
  p.on('console',m=>{if(m.type()==='error'||/GL_INVALID/.test(m.text()))proof.errors.push(m.text())});
  await p.goto('http://127.0.0.1:8772/prototypes/live-club/portraits.html?names=magnus');
  await p.waitForFunction(()=>window.review?.ready,{},{timeout:120000});
  // One 640x530 render, without empty grid cells around it.
  const canvas=p.locator('canvas');
  for(const [view,x,z] of [['front',0,19],['side',17,7],['back',9,-17]]){
   await p.evaluate(({x,z})=>{const m=review.models[0],y=m.camera.position.y;m.camera.position.set(x,y,z);m.camera.lookAt(0,y-1,0);review.render()},{x,z});
   await canvas.screenshot({path:path.join(out,'magnus-'+view+'.png')});proof.views.push(view);
  }
  await p.setViewportSize({width:1280,height:960});
  await p.goto('http://127.0.0.1:8772/prototypes/live-club/?cast');
  await p.waitForFunction(()=>window.clubPreview,{},{timeout:180000});
  await p.evaluate(()=>document.querySelectorAll('header,nav,#status').forEach(e=>e.style.display='none'));
  for(const hour of [14,21]){
   const state=await p.evaluate(async hour=>{
    const T=await import('/ui/three.module.js'),r=clubPreview,t=630;
    r.freeze(t);r.setTime(`2026-10-13T${hour}:00:00`);r.freeze(t);
    const model=r.actors[6].g;if(!model.visible)throw Error('Magnus is not present at review time');
    model.updateWorldMatrix(true,true);let head;model.traverse(o=>{if(o.isBone&&o.name==='head')head=o.getWorldPosition(new T.Vector3())});head.y+=1.8;
    r.target.copy(head);r.camera.position.copy(head).add(new T.Vector3(1.5,1,17).applyQuaternion(model.getWorldQuaternion(new T.Quaternion())));r.camera.fov=30;r.freeze(t);
    return {hour,visible:model.visible,guest:r.guestDirector.update(t).visitors.map(v=>v.guest)};
   },hour);
   await p.locator('#view').screenshot({path:path.join(out,hour===14?'magnus-daylight.png':'magnus-evening.png')});proof.views.push(state);
  }
  assert.deepEqual(proof.errors,[]);proof.passed=true;
 }finally{await browser.close();fs.writeFileSync(path.join(out,'review.json'),JSON.stringify(proof,null,2))}
 console.log(JSON.stringify(proof));
})().catch(e=>{console.error(e);process.exitCode=1});
