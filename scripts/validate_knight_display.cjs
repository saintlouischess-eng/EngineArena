// Display acceptance against a disposable workflow fixture only.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const out='test-output/knight-display',ready=JSON.parse(fs.readFileSync(process.env.ARENA_KNIGHT_READY||'test-output/workflow-ready.json','utf8'));
assert(ready.folder.includes('test-output')&&path.basename(ready.folder).startsWith('workflow-'));fs.mkdirSync(out,{recursive:true});
const start='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--enable-unsafe-swiftshader']}),errors=[],proof={passed:false};
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1100}});page.on('pageerror',e=>errors.push(e.stack));
  const selectGame=async()=>{await page.waitForFunction(()=>state.snapshot);await page.evaluate(async r=>{state.tid=r.tid;await refreshTournament();if(!state.live.length)await showFinalGame(r.gid)},ready);await page.waitForFunction(()=>moveSheet.rows.length)};
  await page.goto(ready.url);await selectGame();
  await page.evaluate(()=>{displayPrefs.focus3d=true;delete displayPrefs.knights3d;displayPrefs.camera3d={};displayPrefs.panels.focus={visible:true,column:'left',height:740};applyDisplay();renderFocus()});
  await page.waitForFunction(()=>board3dCanvas?.dataset.frames>0);
  assert.equal(await page.locator('.board-3d').getAttribute('data-knight-mode'),'inward');
  await page.evaluate(()=>{window.keptRenderer=board3dInstance;window.keptCanvas=board3dCanvas;boardViewDialog()});
  assert.equal(await page.locator('#knights3d').inputValue(),'inward');
  assert.equal(await page.locator('#knights3d option').count(),6);
  await page.screenshot({path:out+'/settings.png'});
  for(const mode of ['outward','forward','backward','left','right','inward']){
   if(!await page.locator('#knights3d').isVisible())await page.evaluate(()=>boardViewDialog());
   await page.locator('#knights3d').selectOption(mode);await page.locator('#applyBoardView').click();
   await page.waitForFunction(mode=>board3dCanvas?.dataset.knightMode===mode,mode);
   assert(await page.evaluate(()=>keptRenderer===board3dInstance&&keptCanvas===board3dCanvas));
   assert.equal(await page.evaluate(()=>board3dCanvas.getContext('webgl2').getError()),0);
  }
  await page.evaluate(()=>boardViewDialog());await page.locator('#knights3d').selectOption('right');await page.locator('#applyBoardView').click();
  await page.evaluate(()=>persistDisplay());await page.reload();await selectGame();await page.waitForFunction(()=>board3dCanvas?.dataset.frames>0);
  assert.equal(await page.locator('.board-3d').getAttribute('data-knight-mode'),'right');proof.savedChoicesAndRendererReuse=true;
  await page.evaluate(()=>boardViewDialog());await page.locator('#knights3d').selectOption('inward');await page.locator('#applyBoardView').click();
  // Inspect the actual source geometry and project texture-up through the same
  // piece rotations used by the shipped renderer. Only rooks face owner-up;
  // knights retain the original model-relative stamp UVs in all six directions.
  proof.stamps=await page.evaluate(async()=>{
   const T=await import('/assets/three.module.js'),{GLTFLoader}=await import('/assets/three-gltf.js'),{crownGeometry}=await import('/assets/board3d-crowns.js');
   const model=await new GLTFLoader().loadAsync('/assets/staunton1849.glb'),sources={};model.scene.traverse(o=>{if(o.isMesh)sources[o.name]=o});const result=[];
   for(const type of ['n','r'])for(const white of [true,false])for(const mode of ArenaBoard3D.knightModes){
    const yaw=type==='n'?ArenaBoard3D.knightRotation(mode,white,-1):(white?0:Math.PI),geometry=crownGeometry(sources[type],type),p=geometry.attributes.position,uv=geometry.attributes.uv;
    let originalKnightError=0;
    if(type==='n')for(let j=0;j<=12;j++)for(let i=0;i<=12;i++){
     const at=j*13+i,u=.15+.70*i/12,v=.17+.64*j/12;
     originalKnightError=Math.max(originalKnightError,Math.abs(uv.getX(at)-u),Math.abs(uv.getY(at)-v),Math.abs(p.getX(at)-(-.025+(v-.5)*.19)),Math.abs(p.getZ(at)-(u-.5)*.19));
    }
    const a=new T.Vector3().fromBufferAttribute(p,0),b=new T.Vector3().fromBufferAttribute(p,1).sub(a),c=new T.Vector3().fromBufferAttribute(p,13).sub(a);
    const bu=uv.getX(1)-uv.getX(0),bv=uv.getY(1)-uv.getY(0),cu=uv.getX(13)-uv.getX(0),cv=uv.getY(13)-uv.getY(0),det=bu*cv-bv*cu;
    const up=b.multiplyScalar(-cu/det).add(c.multiplyScalar(bu/det));up.y=0;up.normalize().applyAxisAngle(new T.Vector3(0,1,0),yaw);
    result.push({type,white,mode,yaw,originalKnightError,up:up.toArray(),minimumHeight:Math.min(...Array.from({length:p.count},(_,i)=>p.getY(i)))});geometry.dispose();
   }
   return result;
  });
  for(const stamp of proof.stamps){
   if(stamp.type==='r'){assert(Math.abs(stamp.up[0])<1e-5);assert(Math.abs(stamp.up[2]-(stamp.white?-1:1))<1e-5)}
   else{assert(stamp.originalKnightError<1e-6);assert(Math.abs(stamp.up[0]-Math.cos(stamp.yaw))<1e-5);assert(Math.abs(stamp.up[2]+Math.sin(stamp.yaw))<1e-5)}
   assert(stamp.minimumHeight>.9);
  }
  proof.originalKnightStampRestored=true;proof.onlyRookStampUpright=true;
  // Review real meshes and materials in a large board, including both sides.
  await page.evaluate(()=>{const canvas=document.createElement('canvas');canvas.id='knightReview';canvas.style='position:fixed;inset:0;width:100vw;height:100vh;z-index:9999';document.body.append(canvas);window.reviewBoard=ArenaBoard3D.create(canvas,()=>{})});
  proof.directions={};
  for(const mode of ['inward','outward','forward','backward','left','right']){
   await page.evaluate(({start,mode})=>reviewBoard.render(start,false,{angle:52,orbit:0,zoom:1.05},false,'',['g1','h1','g8','h8'],mode),{start,mode});
   proof.directions[mode]=JSON.parse(await page.locator('#knightReview').getAttribute('data-knight-rotations'));
   assert.equal(await page.locator('#knightReview').getAttribute('data-crown-count'),'4');
   await page.screenshot({path:out+'/'+mode+'.png'});
  }
  assert.deepEqual(proof.directions.inward,{b8:180,g8:0,b1:180,g1:0});
  assert.deepEqual(proof.directions.outward,{b8:0,g8:180,b1:0,g1:180});
  for(const [name,flip,orbit] of [['flipped',true,0],['orbit',false,55]]){
   await page.evaluate(({start,flip,orbit})=>reviewBoard.render(start,flip,{angle:58,orbit,zoom:1.03},false,'',['g1','h1','g8','h8'],'inward'),{start,flip,orbit});
   assert.deepEqual(JSON.parse(await page.locator('#knightReview').getAttribute('data-knight-rotations')),proof.directions.inward);
   await page.screenshot({path:out+'/'+name+'.png'});
  }
  await page.evaluate(()=>{reviewBoard.dispose();document.querySelector('#knightReview').remove()});
  const frame=await page.locator('.board-3d').getAttribute('data-frames');await page.waitForTimeout(2400);assert.equal(await page.locator('.board-3d').getAttribute('data-frames'),frame);proof.idleNoRedraw=true;
  // Saved-game and scoresheet viewing must pass the reconstructed identities.
  await page.evaluate(()=>{moveSheet.review=moveSheet.rows.find(m=>m.knight_facings&&Object.keys(m.knight_facings).length);renderFocus()});
  await page.waitForTimeout(150);const review=await page.evaluate(()=>({rotations:JSON.parse(board3dCanvas.dataset.knightRotations),facings:moveSheet.review.knight_facings}));
  for(const [square,facing] of Object.entries(review.facings))assert.equal(review.rotations[square],facing>0?180:0);proof.scoresheetIdentity=true;
  proof.languages=[];
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await page.setViewportSize({width:1050,height:800});await page.goto(ready.url+'&lang='+lang);await page.waitForFunction(()=>state.snapshot);
   await page.evaluate(()=>{if(ArenaI18n.locale==='de'){displayPrefs.theme='light';applyDisplay()}boardViewDialog()});
   assert.equal(await page.locator('#knights3d option').count(),6);
   assert.equal(await page.locator('#modal .modal-body').evaluate(el=>el.scrollWidth>el.clientWidth+1),false);
   assert(await page.locator('#applyBoardView').isVisible());
   const label=await page.locator('#knights3d option[value=inward]').textContent();if(lang!=='en')assert.notEqual(label,'Toward the king');
   proof.languages.push({language:lang,label});await page.screenshot({path:out+'/settings-'+lang+'.png'});
  }
  assert.deepEqual(errors,[]);proof.passed=true;
 }finally{await browser.close();fs.writeFileSync(out+'/result.json',JSON.stringify({...proof,errors},null,2))}
 console.log('Knight direction, crown orientation, saved preferences, replay and idle checks passed.');
})().catch(e=>{console.error(e);process.exitCode=1});
