// Actual WebGL, but software rendered in a disposable workspace. No physical reset.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const ready=JSON.parse(fs.readFileSync(process.env.ARENA_SCENE_READY||'test-output/workflow-ready.json'));
assert(path.resolve(ready.folder).startsWith(path.resolve('test-output')+path.sep));
const out=process.env.ARENA_STABILITY_OUT||'test-output/v187-stability';fs.mkdirSync(out,{recursive:true});
(async()=>{
 const b=await chromium.launch({headless:true,channel:'msedge',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']}),proof={passed:false,errors:[]};let p;
 try{
  p=await b.newPage({viewport:{width:3840,height:2160},deviceScaleFactor:2});p.setDefaultTimeout(180000);
  p.on('pageerror',e=>proof.errors.push(e.message));p.on('console',m=>{if(m.type()==='error'||/GL_INVALID/.test(m.text()))proof.errors.push(m.text())});
  await p.goto(ready.url);await p.waitForFunction(()=>state.snapshot);
  console.log('Checking fullscreen buffers');proof.buffers=await p.evaluate(async()=>{
   await ArenaBoard3D.prepare('tal1962');const c=document.createElement('canvas');c.id='stability';c.style='position:fixed;inset:0;width:100vw;height:100vh;z-index:9999';document.body.append(c);
   window.resizeWrites=0;for(const key of ['width','height']){const d=Object.getOwnPropertyDescriptor(HTMLCanvasElement.prototype,key);Object.defineProperty(c,key,{get(){return d.get.call(this)},set(v){resizeWrites++;d.set.call(this,v)}})}
   window.r=ArenaBoard3D.create(c,()=>{},undefined,'tal1962');window.args=['rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',false,{angle:24,orbit:14,zoom:1.05},false,'',[],'inward',{}, {key:'stability',white:'White',black:'Black'}, {environment:'live-club',live:true,people:true,quality:'high',fps:30,motion:'instant'}];
   r.render(...args);if(!await r.ready())throw Error('Assets failed');r.render(...args);await r.settled();
   return {...c.dataset,width:c.width,height:c.height,writes:resizeWrites};
  });assert(proof.buffers.width*proof.buffers.height<=2560*1440);assert.equal(proof.buffers.width,2560);assert.equal(proof.buffers.aoWidth,'1280');assert.equal(proof.buffers.aoHeight,'720');
  console.log('Checking GPU coalescing');proof.coalescing=await p.evaluate(async()=>{
   await r.settled();const c=document.querySelector('#stability'),before=Number(c.dataset.frames),writes=resizeWrites;
   for(let i=0;i<100;i++){args[2].orbit=i*.1;r.render(...args)}
   const submitted=Number(c.dataset.frames)-before;await r.settled();
   return {submitted,skipped:Number(c.dataset.gpuWaits),writes:resizeWrites-writes,finalFrames:Number(c.dataset.frames)-before};
  });assert.equal(proof.coalescing.submitted,1);assert(proof.coalescing.skipped>=99);assert.equal(proof.coalescing.writes,0);assert.equal(proof.coalescing.finalFrames,2);
  await p.setViewportSize({width:1920,height:1080});
  console.log('Checking warm sustained frames');proof.sustained=await p.evaluate(async()=>{
   args[9].quality='low';for(const orbit of [-30,-15,0,15]){args[2].orbit=orbit;r.render(...args);await r.settled()}const warm=r.metrics(),c=document.querySelector('#stability'),writes=resizeWrites,start=performance.now();
   for(let i=0;i<36;i++){args[2].orbit=-30+i*1.25;r.render(...args);await r.settled()}
   return {warm,after:r.metrics(),frames:36,seconds:(performance.now()-start)/1000,writes:resizeWrites-writes,glError:c.getContext('webgl2').getError()};
  });assert.deepEqual(proof.sustained.after,proof.sustained.warm);assert.equal(proof.sustained.writes,0);assert.equal(proof.sustained.glError,0);
  console.log('Checking 4K photo');await p.evaluate(async()=>{args[9].quality='high';r.render(...args);await r.settled();r.freezeEnvironment(true)});
  await p.screenshot({path:out+'/live-room.png'});
  const photo=await p.evaluate(()=>r.photo({width:3840,height:2160,blur:.4})),png=Buffer.from(photo.split(',')[1],'base64');assert.equal(png.readUInt32BE(16),3840);assert.equal(png.readUInt32BE(20),2160);fs.writeFileSync(out+'/photo-4K.png',png);proof.photo4K=true;
  const photos=await p.evaluate(()=>Promise.all([r.photo({width:960,height:540}),r.photo({width:800,height:450})]));for(let i=0;i<photos.length;i++){const bytes=Buffer.from(photos[i].split(',')[1],'base64');assert.equal(bytes.readUInt32BE(16),i?800:960)}proof.concurrentPhotosSerialized=true;
  await p.evaluate(async()=>{await r.settled();r.dispose();document.querySelector('#stability').remove()});
  console.log('Checking both workspace recoveries');await p.setViewportSize({width:1500,height:1000});
  await p.evaluate(async ready=>{state.tid=ready.tid;await refreshTournament();if(!state.live.length)await showFinalGame(ready.gid);displayPrefs.focus3d=true;displayPrefs.scene3d={environment:'live-club',live:true,people:false,quality:'low',fps:30};displayPrefs.panels.focus={visible:true,column:'left',height:740};applyDisplay();renderFocus()},ready);
  await p.locator('.focus-board').scrollIntoViewIfNeeded();await p.waitForFunction(()=>Number(board3dCanvas?.dataset.frames)>1);
  await p.evaluate(()=>board3dCanvas.getContext('webgl2').getExtension('WEBGL_lose_context').loseContext());
  await p.waitForFunction(()=>board3dRecovery.failed&&!board3dCanvas);await p.waitForTimeout(3600);
  assert(await p.evaluate(()=>board3dRecovery.failed&&!board3dRecovery.pending&&!board3dCanvas));
  assert(await p.locator('.focus-board .board').isVisible());await p.screenshot({path:out+'/focus-fallback.png'});
  await p.getByRole('button',{name:'Retry 3D',exact:true}).click();await p.waitForFunction(()=>board3dRecovery.phase==='ready'&&Number(board3dCanvas?.dataset.frames)>1);proof.focusManualRecovery=true;
  await p.evaluate(async()=>{await paShow();PlayerDesk.board.setMode('3d')});await p.locator('#paBoard').scrollIntoViewIfNeeded();await p.waitForFunction(()=>Number(PlayerDesk.board?.canvas?.dataset.frames)>1);
  await p.evaluate(()=>PlayerDesk.board.canvas.getContext('webgl2').getExtension('WEBGL_lose_context').loseContext());await p.waitForFunction(()=>PlayerDesk.board.recovery.failed);await p.waitForTimeout(3600);
  assert(await p.evaluate(()=>!PlayerDesk.board.canvas&&!PlayerDesk.board.recovery.pending));assert(await p.locator('#paBoard .board').isVisible());
  await p.evaluate(()=>view('engines'));await p.evaluate(()=>paShow());await p.waitForFunction(()=>PlayerDesk.board?.recovery.failed&&!PlayerDesk.board.canvas);proof.playerNavigationRemains2D=true;
  await p.getByRole('button',{name:'Retry 3D',exact:true}).click();await p.waitForFunction(()=>PlayerDesk.board.recovery.phase==='ready'&&Number(PlayerDesk.board.canvas?.dataset.frames)>1);proof.playerManualRecovery=true;
  proof.diagnostics=await p.evaluate(()=>JSON.parse(localStorage.getItem('arena.graphicsDiagnostics')));assert(proof.diagnostics.some(e=>e.workspace==='focus'&&e.reason==='live-context'));assert(proof.diagnostics.some(e=>e.workspace==='player'&&e.reason==='live-context'));
  const writes=await p.evaluate(()=>{for(let i=0;i<30;i++)Arena3DRecovery.record('test','bounded',null);return JSON.parse(localStorage.getItem('arena.graphicsDiagnostics')).length});assert.equal(writes,20);proof.boundedDiagnostics=true;
  assert.deepEqual(proof.errors,[]);proof.passed=true;
 }finally{if(p&&!proof.passed)await p.screenshot({path:out+'/failure.png'}).catch(()=>{});await b.close();fs.writeFileSync(out+'/result.json',JSON.stringify(proof,null,2))}
 console.log(JSON.stringify(proof,null,2));
})().catch(e=>{console.error(e);process.exitCode=1});
