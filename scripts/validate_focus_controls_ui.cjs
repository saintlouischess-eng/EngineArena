// Real UI geometry and preference checks against a disposable fixture only.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const out='test-output/focus-controls-1107',ready=JSON.parse(fs.readFileSync(out+'/ready.json'));
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']}),errors=[];
 const proof={passed:false,mode:ready.mode,checks:{}};
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1050}});page.on('pageerror',e=>errors.push(e.message));
  await page.goto(ready.url);await page.waitForFunction(()=>document.querySelector('#tournamentPicker')?.options.length>1);
  await page.selectOption('#tournamentPicker',ready.tid);await page.waitForFunction(tid=>state.snapshot?.id===tid,ready.tid);
  const setup=()=>page.evaluate(gid=>{
   view('overview');refreshGameMoves=()=>{};displayPrefs.focus3d=false;displayPrefs.followNextGame=false;
   focusId=gid;retainedTid=state.tid;
   retainedFocus={tid:state.tid,game:gid,number:0,fen:'1k6/8/8/8/8/8/8/R6K w - - 84 80',white:{name:'White engine'},black:{name:'Black engine'},status:'1-0 · Checkmate',result:'1-0',reason:'checkmate',claim_draws:true,ended:1};
   revealFocusPanel('focus');renderFocus();
  },ready.gid);
  await setup();
  await page.evaluate(()=>{displayPrefs.panels.focus={...panelSettings('focus'),height:720};applyDisplay()});
  const panel=page.locator('[data-panel=focus]'),toggle=page.locator('#focusControlsToggle');
  const watch=()=>page.evaluate(()=>JSON.stringify({game:focusId,winning:displayPrefs.winningWatch,follow:displayPrefs.followEngine,hold:displayPrefs.finishHold,arrow:displayPrefs.pvArrow,counter:displayPrefs.showDrawRule,camera:displayPrefs.camera3d,controls:displayPrefs.board3dControls}));
  const geometry=()=>page.evaluate(()=>{const r=s=>{const b=document.querySelector(s).getBoundingClientRect();return {width:b.width,height:b.height}};return {panel:r('[data-panel=focus]'),title:r('[data-panel=focus]>.panel-title'),board:r('#focusContent .focus-board>.board'),host:r('#focusContent .focus-board')}});
  async function collapse(label){
   const before=await geometry(),settings=await watch();
   assert.equal(await toggle.textContent(),'Hide controls');await toggle.click();
   await page.waitForFunction(()=>document.querySelector('[data-panel=focus]').classList.contains('focus-controls-hidden'));
   assert.equal(await toggle.getAttribute('aria-expanded'),'false');assert.equal(await toggle.textContent(),'Show controls');
   assert(!(await page.locator('#focusPicker').isVisible()));assert(!(await page.locator('#followEngine').isVisible()));
   assert(!(await page.locator('#focusLayoutButton').isVisible()));assert(!(await page.locator('[data-focus-flip]').isVisible()));
   assert(await page.locator('#focusContent .focus-clocks').isVisible());assert(await page.locator('.focus-game-state').isVisible());
   assert(await page.locator('.focus-draw-rule').isVisible());assert(await panel.locator('[data-expand]').isVisible());
   assert.equal(await watch(),settings);const after=await geometry();
   assert(after.title.height<before.title.height-20,JSON.stringify({before,after}));
   assert(after.host.height>before.host.height+20,JSON.stringify({before,after}));
   assert(after.board.height>=before.board.height);assert.equal(after.panel.height,before.panel.height);
   proof.checks[label]={before,after};
  }
  await panel.screenshot({path:out+`/${ready.mode}-before.png`});await collapse('docked');
  assert(proof.checks.docked.after.board.height>proof.checks.docked.before.board.height+20);
  await panel.screenshot({path:out+`/${ready.mode}-hidden.png`});
  // Keyboard restore is accessible and all previously configured options survive.
  await toggle.focus();await page.keyboard.press('Enter');assert(await page.locator('#followEngine').isVisible());
  await panel.locator('[data-float]').click();await collapse('floating');await toggle.click();
  await panel.locator('[data-expand]').click();await collapse('expanded');await toggle.click();await panel.locator('[data-expand]').click();
  await page.setViewportSize({width:1050,height:900});
  await page.evaluate(()=>{displayPrefs.fontSize=24;displayPrefs.panels.focus={...panelSettings('focus'),bounds:{left:8,top:8,width:530,height:810}};applyDisplay()});
  await collapse('narrow-large-text');
  const visibleRestore=await toggle.boundingBox();assert(visibleRestore.x>=0&&visibleRestore.y>=0&&visibleRestore.x+visibleRestore.width<=1050&&visibleRestore.y+visibleRestore.height<=900);
  await panel.screenshot({path:out+`/${ready.mode}-narrow.png`});
  await page.evaluate(()=>persistDisplay());await page.reload();await page.waitForFunction(()=>state.snapshot&&displayPrefs.panels.focus?.controlsHidden===true);await setup();
  assert.equal(await toggle.textContent(),'Show controls');assert(!(await page.locator('#focusPicker').isVisible()));proof.checks.reload=true;
  // Named layouts restore the collapsed state independently of later toggles.
  await page.evaluate(()=>{displayPrefs.fontSize=14;applyDisplay();return displayDialog()});
  await page.locator('#layoutName').fill('Quiet board');await page.locator('#saveLayout').click();
  await page.waitForFunction(()=>Array.from(document.querySelector('#layoutChoice')?.options||[]).some(o=>o.value==='Quiet board'));
  await page.evaluate(()=>document.querySelector('#modal').close());await toggle.click();
  await page.evaluate(()=>displayDialog());await page.selectOption('#layoutChoice','Quiet board');await page.locator('#loadLayout').click();
  assert.equal(await toggle.textContent(),'Show controls');proof.checks.namedLayout=true;
  // A live 3D canvas resizes in place: no renderer restart or camera reset.
  await page.setViewportSize({width:1600,height:1050});await toggle.click();
  await page.evaluate(()=>{
   displayPrefs.panels.focus={...panelSettings('focus'),bounds:{left:10,top:10,width:950,height:820}};
   displayPrefs.focus3d=true;displayPrefs.board3dControls=true;
   displayPrefs.scene3d={environment:'studio',mode:'testing',quality:'low',live:false};
   displayPrefs.camera3d={angle:40,orbit:25,zoom:1.1};applyDisplay();renderFocus();
  });
  await page.waitForFunction(()=>Number(board3dCanvas?.dataset.frames)>0,null,{timeout:60000});
  await page.evaluate(()=>{window.testCanvas=board3dCanvas;window.testRenderer=board3dInstance});
  assert(await page.locator('#board3dControls').isVisible());const camera=await watch();
  const frames=await page.evaluate(()=>Number(board3dCanvas.dataset.frames));await toggle.click();
  await page.waitForFunction(n=>Number(board3dCanvas?.dataset.frames)>n,frames);
  assert(!(await page.locator('#board3dControls').isVisible()));assert.equal(await watch(),camera);
  assert(await page.evaluate(()=>board3dCanvas===testCanvas&&board3dInstance===testRenderer&&!board3dCanvas.getContext('webgl2').isContextLost()));
  await panel.screenshot({path:out+`/${ready.mode}-3d.png`});await toggle.click();
  assert(await page.locator('#board3dControls').isVisible());
  // If camera controls were already hidden, restoring the setup must respect it.
  await page.locator('#toggleBoard3dControls').click();await toggle.click();await toggle.click();
  assert(!(await page.locator('#board3dControls').isVisible()));
  assert.equal(await page.evaluate(()=>displayPrefs.board3dControls),false);
  proof.checks.rendererReusedCameraPreserved=true;proof.checks.independentCameraControlPreference=true;
  assert.deepEqual(errors,[]);proof.passed=true;
 }finally{await browser.close();fs.writeFileSync(out+`/${ready.mode}-ui.json`,JSON.stringify({...proof,errors},null,2))}
 console.log(JSON.stringify(proof));
})().catch(e=>{console.error(e);process.exitCode=1});
