// Real input, durable preferences and accessibility regression checks in isolated data.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/workflow-ready.json','utf8'));assert(ready.folder.includes('test-output'));
 const out='test-output/display-visibility';fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--enable-unsafe-swiftshader']}),errors=[],checks=[];
 try{
  const page=await browser.newPage({viewport:{width:1500,height:1000}});page.on('pageerror',e=>errors.push(e.stack));await page.goto(ready.url);await page.waitForFunction(()=>state.snapshot&&moveSheet.rows.length);
  const help=page.locator('#controlHelp'),delay=()=>page.waitForTimeout(450);
  await page.evaluate(()=>{displayPrefs.hoverHelp=true;displayPrefs.board3dControls=true;displayPrefs.focus3d=true;displayPrefs.panels.focus={visible:true,maximized:true};applyDisplay()});
  await page.waitForFunction(()=>document.querySelector('.board-3d')?.dataset.frames>0);
  // Use the real Display dialog and save button, then verify a fresh load.
  await page.evaluate(()=>displayDialog());assert(await page.locator('#displayHoverHelp').isChecked());await page.locator('#displayHoverHelp').uncheck();await page.locator('#applyDisplay').click();await page.waitForFunction(()=>!document.querySelector('#modal').open);
  await page.locator('#toggleBoard3dControls').hover();await delay();assert.equal(await help.isVisible(),false);
  await page.locator('#toggleBoard3dControls').focus();await page.keyboard.press('Shift+Tab');await delay();assert.equal(await help.isVisible(),false);checks.push('Disabled mouse and keyboard help');
  await page.reload();await page.waitForFunction(()=>document.querySelector('.board-3d')?.dataset.frames>0&&displayPrefs.hoverHelp===false);
  await page.evaluate(()=>{
   const el=document.createElement('button');el.id='nativeHelpFixture';el.title='Native description';el.textContent='Test';el.style='position:fixed;left:300px;top:200px;z-index:100000';el.setAttribute('aria-describedby','existingDescription');document.body.append(el);
  });await page.waitForFunction(()=>!document.querySelector('#nativeHelpFixture').hasAttribute('title'));
  assert.equal(await page.locator('#nativeHelpFixture').getAttribute('aria-description'),'Native description');
  await page.evaluate(()=>document.querySelector('#nativeHelpFixture').title='Updated description');await page.waitForFunction(()=>document.querySelector('#nativeHelpFixture').getAttribute('aria-description')==='Updated description');
  assert.equal(await page.locator('#nativeHelpFixture').getAttribute('title'),null);checks.push('Native titles disabled on inserted and updated controls; accessible description retained');
  await page.evaluate(()=>{displayPrefs.hoverHelp=true;applyDisplay()});assert.equal(await page.locator('#nativeHelpFixture').getAttribute('title'),'Updated description');assert.equal(await page.locator('#nativeHelpFixture').getAttribute('aria-description'),null);
  await page.locator('#nativeHelpFixture').hover();await delay();assert(await help.isVisible());
  await page.evaluate(()=>{displayPrefs.hoverHelp=false;ArenaHelp.refresh()});assert.equal(await help.isVisible(),false);assert.equal(await page.locator('#nativeHelpFixture').getAttribute('aria-describedby'),'existingDescription');
  // Disabling during the delay must also cancel a pending pop-up.
  await page.evaluate(()=>{displayPrefs.hoverHelp=true;ArenaHelp.refresh()});await page.mouse.move(100,100);await page.locator('#nativeHelpFixture').hover();await page.evaluate(()=>{displayPrefs.hoverHelp=false;ArenaHelp.refresh()});await delay();assert.equal(await help.isVisible(),false);checks.push('Existing and pending help cancelled immediately; descriptions restored');
  await page.evaluate(()=>document.querySelector('#nativeHelpFixture').remove());
  await page.locator('[data-zoom=in]').click();await page.locator('[data-lift=up]').click();
  const camera=await page.evaluate(()=>structuredClone(displayPrefs.camera3d));
  await page.locator('#toggleBoard3dControls').click();assert.equal(await page.locator('.board-3d-controls').isVisible(),false);assert.equal(await page.locator('#toggleBoard3dControls').textContent(),'Show 3D controls');assert.deepEqual(await page.evaluate(()=>displayPrefs.camera3d),camera);
  await page.evaluate(()=>persistDisplay());await page.reload();await page.waitForFunction(()=>document.querySelector('.board-3d')?.dataset.frames>0&&displayPrefs.board3dControls===false);
  assert.equal(await page.locator('.board-3d-controls').isVisible(),false);assert.deepEqual(await page.evaluate(()=>displayPrefs.camera3d),camera);
  await page.screenshot({path:out+'/unobstructed-board.png'});checks.push('Hidden 3D controls and camera survive reload');
  await page.locator('#toggleBoard3dControls').click();assert(await page.locator('.board-3d-controls').isVisible());assert.deepEqual(await page.evaluate(()=>displayPrefs.camera3d),camera);
  await page.evaluate(()=>boardViewDialog());await page.locator('#showBoard3dControls').uncheck();await page.locator('#applyBoardView').click();await page.waitForFunction(()=>document.querySelector('.board-3d')?.dataset.frames>0);assert.equal(await page.locator('.board-3d-controls').isVisible(),false);
  await page.locator('#toggleBoard3dControls').click();assert(await page.locator('.board-3d-controls').isVisible());checks.push('Header toggle and 2D / 3D dialog agree');
  await page.evaluate(()=>{displayPrefs.hoverHelp=true;displayPrefs.focus3d=false;applyDisplay()});assert.equal(await page.locator('#toggleBoard3dControls').isVisible(),false);
  await page.evaluate(()=>displayDialog());await page.locator('#displayHoverHelp').check();await page.locator('#applyDisplay').click();await page.waitForFunction(()=>!document.querySelector('#modal').open);
  await page.evaluate(()=>persistDisplay());await page.reload();await page.waitForFunction(()=>state.snapshot&&displayPrefs.hoverHelp===true);
  await page.locator('#focusPicker').hover();await delay();assert(await help.isVisible());checks.push('Help re-enabled durably; 3D toggle absent in 2D');
  assert.deepEqual(errors,[]);fs.writeFileSync(out+'/result.json',JSON.stringify({passed:true,checks,errors},null,2));console.log(checks.length+' display visibility checks passed.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
