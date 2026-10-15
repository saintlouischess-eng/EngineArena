// Disposable fixture only. Scene, animation, lifetime, photo and UI acceptance.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const ready=JSON.parse(fs.readFileSync(process.env.ARENA_SCENE_READY||'test-output/workflow-ready.json')),
 out=process.env.ARENA_SCENE_OUT||'test-output/scenes-source';assert(ready.folder.includes('test-output'));fs.mkdirSync(out,{recursive:true});
const start='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
(async()=>{const browser=await chromium.launch({headless:true,channel:'msedge',args:['--enable-unsafe-swiftshader']}),proof={passed:false,views:[],errors:[],renderer:'Headless Edge; graphics device recorded below. Functional validation, not a GPU benchmark'};
 try{
  const p=await browser.newPage({viewport:{width:1600,height:1100}});p.on('pageerror',e=>proof.errors.push(e.stack));
  p.on('console',m=>{if(m.type()==='error'||/WebGL: INVALID|GL_INVALID/.test(m.text()))proof.errors.push(m.text())});
  await p.goto(ready.url);await p.waitForFunction(()=>state.snapshot);
  await p.evaluate(async()=>{await ArenaBoard3D.prepare();const c=document.createElement('canvas');c.id='sceneReview';c.style='position:fixed;inset:0;width:100vw;height:100vh;z-index:9999';document.body.append(c);window.reviewBoard=ArenaBoard3D.create(c,()=>{})});
  proof.graphics=await p.evaluate(()=>{const gl=document.querySelector('#sceneReview').getContext('webgl2'),ext=gl.getExtension('WEBGL_debug_renderer_info');return ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER)});
  const context={key:'scene',white:'Stockfish 19',black:'Reckless 0.10',event:'Engine Arena Championship',score:'Head-to-head 12.5 – 11.5',captured:['P','p','n','B']};
  for(const environment of ['club','hall','study','studio']){
   await p.evaluate(({start,context,environment})=>reviewBoard.render(start,false,{angle:38,orbit:20,zoom:.82},false,'e2e4',['g1','h1','g8','h8'],'inward',{},context,{environment,trays:true,quality:'high'}),{start,context,environment});
   assert(await p.evaluate(()=>reviewBoard.ready()));assert.equal(await p.locator('#sceneReview').evaluate(c=>c.getContext('webgl2').getError()),0);await p.screenshot({path:out+'/'+environment+'.png'});proof.views.push(environment);const memory=await p.evaluate(()=>reviewBoard.metrics());(proof.roomMemory||=[]).push(memory);if(proof.roomMemory.length>1)assert.equal(memory.textures,proof.roomMemory[0].textures,'Room switches release old GPU textures');assert.deepEqual(JSON.parse(await p.locator('#sceneReview').getAttribute('data-nameplates')),[context.white,context.black]);
   await p.evaluate(({start,context,environment})=>reviewBoard.render(start,false,ArenaScene3D.views.room,false,'e2e4',['g1','h1','g8','h8'],'inward',{},context,{environment,quality:'high'}),{start,context,environment});await p.screenshot({path:out+'/'+environment+'-wide.png'});
  }
  // Older room loads cannot replace a more recent selection.
  await p.evaluate(({start,context})=>{reviewBoard.render(start,false,{},false,'',[],'inward',{},context,{environment:'study',quality:'low'});reviewBoard.render(start,false,{},false,'',[],'inward',{},context,{environment:'hall',quality:'balanced'})},{start,context});
  assert(await p.evaluate(()=>reviewBoard.ready()));await p.waitForTimeout(500);assert.equal(await p.locator('#sceneReview').getAttribute('data-room-ready'),'hall4096');proof.latestRoomWins=true;
  for(const [surface,lighting] of [['felt','evening'],['leather','daylight'],['wood','tournament']]){
   await p.evaluate(({start,context,surface,lighting})=>reviewBoard.render(start,false,{angle:50,orbit:-22,zoom:.92},false,'e2e4',[],'inward',{},context,{environment:'club',surface,lighting,trays:true}),{start,context,surface,lighting});assert(await p.evaluate(()=>reviewBoard.ready()));await p.screenshot({path:out+'/'+surface+'-'+lighting+'.png'});
  }
  assert.equal(await p.locator('#sceneReview').getAttribute('data-captured-count'),'4');
  // Actual 3840 x 2160 depth-aware photo, followed by continued rendering.
  assert(await p.evaluate(()=>reviewBoard.ready()));const photo=await p.evaluate(()=>reviewBoard.photo({width:3840,height:2160,blur:.6}));const png=Buffer.from(photo.split(',')[1],'base64');assert.equal(png.readUInt32BE(16),3840);assert.equal(png.readUInt32BE(20),2160);fs.writeFileSync(out+'/board-4K.png',png);proof.photoBytes=png.length;
  assert(await p.evaluate(()=>reviewBoard.ready()));assert.equal(await p.locator('#sceneReview').evaluate(c=>c.getContext('webgl2').getError()),0);
  // Real renderer animation path and final position, including a jumping knight.
  const before='7k/8/8/8/8/8/8/1N5K w - - 0 1',after='7k/8/8/8/8/2N5/8/7K b - - 1 1';
  await p.evaluate(({before,after})=>{window.animationArgs=[after,false,{},false,'b1c3',[],'inward',{}, {key:'animation'}, {motion:'smooth'}];reviewBoard.render(before,false,{},false,'',[],'inward',{}, {key:'animation'});reviewBoard.render(...animationArgs)},{before,after});
  assert(await p.evaluate(()=>reviewBoard.needsFrame()));await p.waitForTimeout(650);await p.evaluate(()=>reviewBoard.render(...animationArgs));assert.equal(await p.evaluate(()=>reviewBoard.needsFrame()),false);proof.animationSettles=true;
  await p.evaluate(()=>{reviewBoard.dispose();document.querySelector('#sceneReview').remove()});
  await p.evaluate(async r=>{state.tid=r.tid;await refreshTournament();if(!state.live.length)await showFinalGame(r.gid);displayPrefs.focus3d=true;displayPrefs.scene3d={environment:'club',motion:'instant'};displayPrefs.camera3d={angle:50.125,orbit:3.892400000095364,zoom:1,lift:0};displayPrefs.panels.focus={visible:true,column:'left',height:740};applyDisplay();renderFocus()},ready);
  await p.waitForFunction(()=>board3dCanvas?.dataset.frames>0);await p.waitForTimeout(2200);
  const frames=await p.locator('.board-3d').getAttribute('data-frames');await p.waitForTimeout(1300);assert.equal(await p.locator('.board-3d').getAttribute('data-frames'),frames);proof.testingIdle=true;
  await p.evaluate(()=>{boardViewDialog();document.querySelector('#sceneMode').value='presentation';document.querySelector('#sceneTrays').checked=true;document.querySelector('#sceneSaveView').click();if(![...document.querySelectorAll('#modal input[type=number]')].every(e=>e.checkValidity()))throw Error('Camera fields rejected a saved fractional view');document.querySelector('#applyBoardView').click()});
  await p.locator('.board-3d').scrollIntoViewIfNeeded();await p.waitForTimeout(300);const moving=Number(await p.locator('.board-3d').getAttribute('data-frames'));
  try{await p.waitForFunction(n=>Number(board3dCanvas?.dataset.frames)>n,moving,{timeout:10000})}catch(e){proof.tourFailure=await p.evaluate(()=>({visible:sceneVisible(),view:state.view,hidden:document.hidden,onscreen:board3dOnscreen,photo:board3dPhotoOpen,panel:panels.focus.hidden,mode:displayPrefs.scene3d.mode,pending:board3dPending,timer:board3dTimer,frames:board3dCanvas?.dataset.frames}));await p.screenshot({path:out+'/tour-failure.png'});throw e}
  await p.evaluate(()=>view('engines'));await p.waitForTimeout(200);const hidden=await p.locator('.board-3d').getAttribute('data-frames');await p.waitForTimeout(500);assert.equal(await p.locator('.board-3d').getAttribute('data-frames'),hidden);proof.hiddenStops=true;const frozenTour=await p.evaluate(()=>board3dTourElapsed);await p.waitForTimeout(1000);assert.equal(await p.evaluate(()=>board3dTourElapsed),frozenTour);proof.hiddenTourTimeStops=true;
  await p.evaluate(()=>view('overview'));await p.waitForTimeout(200);await p.locator('.board-3d').click({position:{x:60,y:80}});assert.equal(await p.evaluate(()=>displayPrefs.scene3d.mode),'testing');proof.interactionStopsTour=true;
  await p.evaluate(()=>boardPhotoDialog());await p.locator('#scenePhotoPreview').waitFor();await p.locator('#photoBlur').selectOption('0.6');await p.screenshot({path:out+'/photo-dialog.png'});
  const downloadReady=p.waitForEvent('download');await p.locator('#scenePhotoExport').click();const download=await downloadReady;await download.saveAs(out+'/photo-dialog-4K.png');
  const exported=fs.readFileSync(out+'/photo-dialog-4K.png');assert.equal(exported.readUInt32BE(16),3840);assert.equal(exported.readUInt32BE(20),2160);proof.photoButtonExports=true;await p.evaluate(()=>$('#modal').close());
  await p.evaluate(()=>persistDisplay());await p.reload();await p.waitForFunction(()=>state.snapshot);assert.equal(await p.evaluate(()=>displayPrefs.scene3d.trays),true);assert(await p.evaluate(()=>displayPrefs.savedCameras3d[0]));proof.preferencesRetained=true;
  await p.setViewportSize({width:1050,height:800});await p.evaluate(()=>{boardViewDialog();document.documentElement.style.fontSize='20px'});assert.equal(await p.locator('#modal .modal-body').evaluate(el=>el.scrollWidth>el.clientWidth+1),false);await p.screenshot({path:out+'/settings.png'});
  proof.languages=[];
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await p.goto(ready.url+'&lang='+lang);await p.waitForFunction(()=>state.snapshot);await p.evaluate(()=>{window.sceneMissing=new Set();ArenaI18n.capture(k=>{if(ArenaI18n.locale!=='en'&&!Object.hasOwn(window.ARENA_MESSAGES,k))sceneMissing.add(k)});boardViewDialog()});assert.deepEqual(await p.evaluate(()=>[...sceneMissing]),[]);assert.equal(await p.locator('#modal .modal-body').evaluate(el=>el.scrollWidth>el.clientWidth+1),false);
   const label=await p.locator('#sceneEnvironment option:checked').textContent();if(lang!=='en')assert.notEqual(label,'Chess club');proof.languages.push({language:lang,environment:label});
  }
  assert.deepEqual(proof.errors,[]);proof.passed=true;
 }finally{await browser.close();fs.writeFileSync(out+'/result.json',JSON.stringify(proof,null,2))}
 console.log('Scene and presentation acceptance passed: '+out);
})().catch(e=>{console.error(e);process.exitCode=1});
