// Local model/lighting review; never accesses tournament data.
const fs=require('fs'),path=require('path');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const out=process.argv[2]||'test-output/club-skin-arms';fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try{
  const p=await browser.newPage({viewport:{width:1400,height:1050}});p.on('pageerror',e=>{throw e});
  await p.goto('http://127.0.0.1:8772/prototypes/live-club/?cast');await p.waitForFunction(()=>window.clubPreview,{}, {timeout:180000});
  await p.evaluate(()=>document.querySelectorAll('header,nav,#status').forEach(e=>e.style.display='none'));
  for(const index of [1,3])for(const hour of [14,21]){
   const diagnostics=await p.evaluate(async({index,hour})=>{
    const T=await import('/ui/three.module.js'),r=clubPreview,g=r.actors[index].g,table=g.parent;
    r.setTime(`2026-10-12T${hour}:00:00`);r.freeze(0);
    const bones={};g.traverse(o=>{if(o.isBone)bones[o.name]=o});
    const head=bones.head.getWorldPosition(new T.Vector3());head.y+=1.9;
    r.target.copy(head);r.camera.position.copy(head).add(new T.Vector3(3,1.5,18).applyQuaternion(table.getWorldQuaternion(new T.Quaternion())));r.camera.fov=42;r.freeze(0);
    const joints={};for(const name of ['clavicleL','clavicleR','upperarm01L','upperarm02L','upperarm01R','upperarm02R','lowerarm01L','lowerarm01R','wristL','wristR'])if(bones[name])joints[name]=table.worldToLocal(bones[name].getWorldPosition(new T.Vector3())).toArray();
    return {joints,diagnostics:r.actors[index].actor.diagnostics};
   },{index,hour});
   fs.writeFileSync(path.join(out,`${index}-${hour}.json`),JSON.stringify(diagnostics,null,2));await p.screenshot({path:path.join(out,`${index}-${hour}.png`)});
  }
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
