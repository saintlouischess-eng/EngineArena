// Focus/activation regression for help popovers; use an isolated ready-file.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(`http://127.0.0.1:${ready.port}/?token=${ready.token}`);
  await page.waitForFunction(()=>state.snapshot);
  const menu=page.locator('.reports-menu summary');
  await menu.hover();await page.waitForTimeout(450);
  assert.equal(await page.locator('#controlHelp').isVisible(),true,'Hover help remains available');
  await menu.click();await page.waitForTimeout(450);
  assert.equal(await page.locator('.reports-menu').getAttribute('open'),'');
  assert.equal(await page.locator('#controlHelp').isVisible(),false,'Activated menu must not be covered by its own tooltip');
  await page.screenshot({path:'test-output/v1-final-review/report-menu.png'});
  await menu.press('Enter');await page.mouse.move(1,1);
  await menu.focus();await page.waitForTimeout(450);await menu.press('Enter');await page.waitForTimeout(450);
  assert.equal(await page.locator('#controlHelp').isVisible(),false,'Keyboard activation dismisses help too');
  await page.locator('#tournamentReport').click();await page.waitForSelector('.report-preview');
  await page.locator('#tournamentReportText').click();await page.waitForSelector('#textExportPreview');
  const report=await page.locator('#textExportPreview').inputValue();assert(report.includes('12')&&report.includes('Stockfish workflow'));
  await page.screenshot({path:'test-output/v1-final-review/report-text.png'});
  assert.deepEqual(errors,[]);
  fs.writeFileSync('test-output/v1-final-review/ui-polish.json',JSON.stringify({hoverHelp:true,pointerActivation:true,keyboardActivation:true,reportTextCharacters:report.length,errors,passed:true},null,2));
  console.log('Hover help, pointer/keyboard activation, report and text export passed.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
