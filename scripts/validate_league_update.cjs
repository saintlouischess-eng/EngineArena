const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/league-ready.json','utf8')),browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(ready.url);await page.waitForFunction(()=>state.snapshot&&typeof newEvent==='function');
  await page.locator('[data-view=events]').click();await page.locator('#newEvent').click();await page.waitForSelector('#eventSource');
  await page.locator('#eventSource').selectOption(ready.source);await page.waitForFunction(()=>document.querySelector('#eventCPU').value==='28');
  await page.locator('#eventKind').selectOption('league');await page.locator('#eventGroupCount').fill('8');await page.locator('#eventDistribute').click();
  assert.equal(await page.locator('#eventGroups').inputValue(),Array.from({length:8},(_,i)=>Array.from({length:8},(_,j)=>i*8+j+1).join(' ')).join('\n'));
  await page.locator('#eventName').fill('64 engines · two seasons and championship');await page.locator('#eventCalculate').click();
  await page.waitForFunction(()=>!document.querySelector('#eventSave').disabled);assert.equal(await page.locator('#eventPreview').textContent(),'912');
  assert.match(await page.locator('#eventPreviewDetail').textContent(),/896.*16/);
  assert.match(await page.locator('#eventPreviewDetail').textContent(),/positions will repeat/);
  await page.locator('#leagueTieMode').selectOption('sequence');await page.locator('#leagueShorter').click();assert.equal(await page.locator('#leagueTieStages .tc-editor').count(),3);
  await page.locator('#leagueOptions').scrollIntoViewIfNeeded();await page.screenshot({path:'test-output/league-update-builder.png'});
  await page.locator('#leagueFinalGames').fill('3');await page.locator('#eventCalculate').click();await page.waitForTimeout(300);assert.equal(await page.locator('#eventSave').isDisabled(),true);
  await page.locator('#leagueFinalGames').fill('8');await page.locator('#eventCalculate').click();await page.waitForFunction(()=>!document.querySelector('#eventSave').disabled);
  await page.locator('#eventSave').click();await page.waitForSelector('#eventRun');assert.equal(await page.evaluate(()=>eventDetailData.state),'paused');
  assert.equal(await page.evaluate(()=>eventDetailData.definition.championship.controls.length),3);
  assert.equal(await page.evaluate(()=>eventDetailData.children.length),0);
  await page.locator('#eventResources').click();try{await page.locator('#erGames').waitFor({timeout:3000})}catch(error){console.log('Resource dialog:',await page.locator('#modalContent').innerText(),errors);throw error}await page.locator('#erGames').fill('14');await page.locator('#erSave').click();await page.waitForSelector('#eventRun');
  assert.equal(await page.evaluate(()=>eventDetailData.resources.concurrency),14);
  await page.evaluate(id=>showEvent(id),ready.completed);await page.waitForFunction(()=>eventDetailData.state==='completed');
  assert.match(await page.locator('#eventDecisions').textContent(),/Regular-season winner.*0.*Championship final.*Champion.*1/s);
  const report=await page.evaluate(()=>eventReport(eventDetailData));assert.match(report,/Regular-season winner/);assert.match(report,/Tiebreak 2/);assert.match(report,/30s \+ 0.5s/);
  fs.writeFileSync('test-output/league-update-report.txt',report);await page.screenshot({path:'test-output/league-update-completed.png'});
  for(const width of [1050,1440,1920]){await page.setViewportSize({width,height:900});await page.evaluate(()=>document.documentElement.style.fontSize='20px');assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false)}
  for(const lang of ['es','fr','de','pt','it','nl','pl']){
   await page.goto(ready.url+'&lang='+lang);await page.waitForFunction(()=>state.snapshot&&typeof showEvent==='function');await page.evaluate(id=>showEvent(id),ready.completed);
   assert.ok((await page.locator('#eventDecisions').textContent()).length>100);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  }
  assert.deepEqual(errors,[]);fs.writeFileSync('test-output/league-update-ui.json',JSON.stringify({passed:true,errors,preview:912,regular:896,finals:16,seededDivisions:true,controls:3,completedReport:true},null,2));
  console.log('League update UI passed.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
