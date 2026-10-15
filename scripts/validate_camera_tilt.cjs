/* Disposable browser acceptance. Software GPU only; never production data. */
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const ready=JSON.parse(fs.readFileSync(process.argv[2]||'test-output/tournament-edit-ready.json','utf8')),out=process.argv[3]||'test-output/camera-tilt-source';
assert(path.resolve(ready.folder).startsWith(path.resolve('test-output')+path.sep));fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']}),proof={passed:false,errors:[]};let p;
 try{
  p=await browser.newPage({viewport:{width:1500,height:1000}});p.setDefaultTimeout(90000);p.on('pageerror',e=>proof.errors.push(e.message));
  function sameCamera(actual,expected){for(const key of Object.keys(expected))assert(Math.abs(actual[key]-expected[key])<1e-8,key+': '+actual[key]+' vs '+expected[key])}
  async function mouseTilt(selector,readCamera,setCamera){
   const canvas=p.locator(selector);await canvas.scrollIntoViewIfNeeded();const box=await canvas.boundingBox();assert(box&&box.height>200);
   const x=box.x+box.width/2,y=box.y+Math.min(box.height/2,180),original=await p.evaluate(readCamera);
   const before={...original,angle:16,tilt:0};await p.evaluate(setCamera,before);
   async function drag(modifiers,button,dx,dy){
    await p.mouse.move(x,y);for(const key of modifiers)await p.keyboard.down(key);
    await p.mouse.down({button});await p.mouse.move(x+dx,y+dy,{steps:3});await p.mouse.up({button});
    for(const key of [...modifiers].reverse())await p.keyboard.up(key);
   }
   await drag([],'right',32,-80);sameCamera(await p.evaluate(readCamera),{...before,angle:6,tilt:10,orbit:before.orbit+12.8});
   await drag([],'right',-32,-40);sameCamera(await p.evaluate(readCamera),{...before,angle:6,tilt:20});
   await drag([],'right',0,120);sameCamera(await p.evaluate(readCamera),before);
   // The same upward look works with Alt-left on a trackpad.
   await drag(['Alt'],'left',0,-80);sameCamera(await p.evaluate(readCamera),{...before,angle:6,tilt:10});
   await drag(['Alt'],'left',0,80);sameCamera(await p.evaluate(readCamera),before);
   await canvas.focus();await p.keyboard.press('ArrowUp');sameCamera(await p.evaluate(readCamera),{...before,angle:13});
   await p.keyboard.press('ArrowDown');sameCamera(await p.evaluate(readCamera),before);
   await drag(['Shift'],'right',0,-20);const lifted=await p.evaluate(readCamera);assert(lifted.lift>before.lift);assert.equal(lifted.tilt,before.tilt);assert.equal(lifted.angle,before.angle);
   await drag(['Shift'],'right',0,20);assert(Math.abs((await p.evaluate(readCamera)).lift-before.lift)<1e-10);
   await drag([],'right',20,0);const orbited=await p.evaluate(readCamera);assert.equal(orbited.orbit,before.orbit+8);assert.equal(orbited.angle,before.angle);assert.equal(orbited.tilt,before.tilt);
   await p.evaluate(setCamera,original);
  }
  await p.goto(ready.url+'&lang=en');await p.waitForFunction(()=>state.snapshot&&queueData);
  await p.evaluate(async()=>{displayPrefs.scene3d={environment:'live-club',live:true,people:true,quality:'low',roomMotion:'still',localTime:false,lighting:'tournament'};await paShow();paBoard().camera=ArenaBoard3D.settings({});paBoard().setMode('3d')});
  await p.locator('#paBoard').scrollIntoViewIfNeeded();await p.waitForFunction(()=>Number(paBoard().canvas?.dataset.frames)>0);await p.evaluate(async()=>{const b=paBoard();b.photoOpen=true;b.stopFrames();try{await b.renderer.ready()}finally{b.photoOpen=false;b.paint()}});
  console.log('Player room loaded');await p.evaluate(()=>boardViewDialog({player:true}));await p.locator('[data-scene-view="low"]').click();assert.equal(await p.locator('#cameraAngle').inputValue(),'8');assert.equal(await p.locator('#cameraTilt').inputValue(),'6');
  await p.locator('#sceneSaveView').click();await p.locator('#cameraTilt').fill('20');await p.locator('#sceneLoadView').click();assert.equal(await p.locator('#cameraTilt').inputValue(),'6');await p.locator('#applyBoardView').click();
  await p.locator('#paBoard').scrollIntoViewIfNeeded();await p.waitForFunction(()=>paBoard().canvas?.dataset.cameraTilt==='6');proof.lowAngleAndSavedView=true;console.log("Saved camera view passed");
  await mouseTilt('#paBoard canvas',()=>({...paBoard().camera}),c=>{paBoard().camera=c;paBoard().paint();paBoard().saveCamera()});assert.equal(await p.evaluate(()=>displayPrefs.playerCamera.tilt),6);proof.playerMouseTiltAndControls=true;
  // Resize only the isolated test panel for legible low-angle/ceiling evidence.
  await p.evaluate(()=>{$('#paBoardPanel').style.width='1280px';$('#paBoardPanel').style.height='880px';paBoard().paint()});
  await p.locator('#paPhoto').click();await p.waitForFunction(()=>$('#paPhotoPreview')?.naturalWidth===960);
  let data=await p.locator('#paPhotoPreview').getAttribute('src');fs.writeFileSync(out+'/low-angle.png',Buffer.from(data.split(',')[1],'base64'));
  const camera=await p.evaluate(()=>({...paBoard().camera}));await p.locator('#paPhotoTilt').fill('60');await p.locator('#paPhotoTilt').dispatchEvent('change');await p.waitForFunction(old=>$('#paPhotoPreview')?.src!==old,data);
  data=await p.locator('#paPhotoPreview').getAttribute('src');fs.writeFileSync(out+'/ceiling.png',Buffer.from(data.split(',')[1],'base64'));
  const downloadPromise=p.waitForEvent('download');await p.locator('#paSavePhoto').click();const download=await downloadPromise;await download.saveAs(out+'/ceiling-4k.png');const bytes=fs.readFileSync(out+'/ceiling-4k.png');assert.equal(bytes.readUInt32BE(16),3840);assert.equal(bytes.readUInt32BE(20),2160);
  await p.keyboard.press('Escape');await p.waitForFunction(()=>!paBoard().photoOpen&&paBoard().canvas?.dataset.cameraTilt==='6');assert.deepEqual(await p.evaluate(()=>({...paBoard().camera})),camera);proof.playerFrozenPhotoTilt4kAndRestore=true;console.log("Player photos passed");
  await p.evaluate(()=>{$('#paCamera').hidden=false});await p.locator('#paTilt').fill('18');await p.locator('#paTilt').dispatchEvent('input');await p.waitForFunction(()=>paBoard().canvas.dataset.cameraTilt==='18');assert.equal(await p.evaluate(()=>paBoard().camera.angle),8);assert.equal(await p.evaluate(()=>paBoard().camera.zoom),1);
  await p.evaluate(()=>persistDisplay());await p.reload();await p.waitForFunction(()=>state.snapshot);assert.equal(await p.evaluate(()=>displayPrefs.playerCamera.tilt),18);proof.playerSliderAndRestart=true;console.log("Player restart passed");
  await p.evaluate(()=>{view('overview');refreshGameMoves=()=>{};displayPrefs.focus3d=true;displayPrefs.camera3d=ArenaBoard3D.settings({angle:8,orbit:25,zoom:1,tilt:6});displayPrefs.followNextGame=false;retainedTid=state.tid;retainedFocus={game:'camera-preview',tid:state.tid,number:0,white:{name:'White'},black:{name:'Black'},fen:'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',status:'Saved game',searches:{}};focusId='camera-preview';applyDisplay();renderFocus()});
  await p.locator('.focus-board').scrollIntoViewIfNeeded();await p.waitForFunction(()=>board3dCanvas?.dataset.cameraTilt==='6');await p.locator('#board3dTilt').fill('14');await p.locator('#board3dTilt').dispatchEvent('input');await p.waitForFunction(()=>board3dCanvas?.dataset.cameraTilt==='14');await p.locator('[data-tilt="reset"]').click();await p.waitForFunction(()=>board3dCanvas?.dataset.cameraTilt==='0');
  await mouseTilt('canvas.board-3d',()=>({...ArenaBoard3D.settings(displayPrefs.camera3d)}),c=>{displayPrefs.camera3d=c;board3dSignature='';renderFocus();saveDisplay()});assert.equal(await p.locator('#board3dTilt').inputValue(),'0');proof.focusMouseTiltAndControls=true;
  await p.locator('#boardPhoto').click();await p.waitForFunction(()=>$('#scenePhotoPreview')?.naturalWidth===960);await p.locator('#photoView').selectOption('low');await p.waitForFunction(()=>board3dCanvas?.dataset.cameraTilt==='6');await p.locator('#photoTilt').fill('35');await p.locator('#photoTilt').dispatchEvent('change');await p.waitForFunction(()=>board3dCanvas?.dataset.cameraTilt==='35');await p.keyboard.press('Escape');await p.waitForFunction(()=>!board3dPhotoOpen&&board3dCanvas?.dataset.cameraTilt==='0');proof.focusSliderPresetPhotoAndRestore=true;
  await p.locator('canvas.board-3d').focus();await p.keyboard.press('ArrowUp');await p.evaluate(()=>persistDisplay());await p.reload();await p.waitForFunction(()=>state.snapshot);assert.equal(await p.evaluate(()=>displayPrefs.camera3d.tilt),1);proof.focusTiltPersists=true;
  assert.deepEqual(proof.errors,[]);proof.passed=true;
 }finally{if(p&&!proof.passed)await p.screenshot({path:out+'/failure.png'}).catch(()=>{});await browser.close();fs.writeFileSync(out+'/result.json',JSON.stringify(proof,null,2))}
 console.log(JSON.stringify(proof,null,2));
})().catch(e=>{console.error(e);process.exitCode=1});
