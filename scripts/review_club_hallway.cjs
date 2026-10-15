// Inspect actual visitor routes beneath the vestibule fixture, without game APIs.
const fs=require('fs'),path=require('path');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const out=process.argv[2]||'test-output/club-hallway';fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage({viewport:{width:1400,height:1050}});page.on('pageerror',e=>{throw e});
  await page.goto('http://127.0.0.1:8772/prototypes/live-club/?cast');await page.waitForFunction(()=>window.clubPreview,{}, {timeout:180000});
  await page.evaluate(()=>document.querySelectorAll('header,nav,#status').forEach(e=>e.style.display='none'));
  const records=[];
  const times=(process.argv[3]||'2,126').split(',').map(Number);
  for(const hour of [14,21])for(const t of times)for(const old of [true,false]){
   const record=await page.evaluate(async({hour,t,old})=>{
    const T=await import('/ui/three.module.js'),r=clubPreview,fixture=r.scene.getObjectByName('Vestibule ceiling diffuser');
    if(!fixture)throw Error('Missing new ceiling fixture');
    let prior=r.scene.getObjectByName('Review former point source');if(!prior){prior=new T.PointLight(0xffdda8,34,33,2);prior.name='Review former point source';prior.position.set(22,17,-103);r.scene.add(prior)}
    fixture.visible=!old;prior.visible=old;r.setTime(`2026-10-12T${hour}:00:00`);r.freeze(t);
    const visitor=r.guestDirector.update(t).visitors[0];
    const g=r.actors.find(a=>a.g.visible&&Math.abs(a.g.position.z-visitor.position[2])<.1&&a.g.position.x>15).g;
    g.updateWorldMatrix(true,true);let head;g.traverse(o=>{if(o.isBone&&o.name==='head')head=o.getWorldPosition(new T.Vector3())});head.y+=2;
    r.target.copy(head);r.camera.position.copy(head).add(new T.Vector3(-7,2,15));r.camera.fov=38;r.freeze(t);
    return {hour,t,old,visitor,head:head.toArray(),light:fixture.position.toArray(),distance:head.distanceTo(fixture.position)};
   },{hour,t,old});records.push(record);
   await page.screenshot({path:path.join(out,`${hour}-${t}-${old?'before':'after'}.png`)});
  }
  fs.writeFileSync(path.join(out,'review.json'),JSON.stringify(records,null,2));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
