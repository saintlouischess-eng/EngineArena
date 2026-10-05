const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/events-ready.json','utf8')),browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const page=await browser.newPage({viewport:{width:1550,height:1050}}),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto(ready.url);
  await page.waitForFunction(()=>state.snapshot&&typeof newEvent==='function');
  await page.evaluate(ids=>{state.selected=new Set(ids)},ready.profiles);
  await page.locator('#newTournament').click();await page.locator('#tformat').selectOption('custom');
  await page.locator('#customPairs').fill('1 2 3\n2 3 2');await page.waitForFunction(()=>document.querySelector('#totalPreview').textContent==='10'&&!document.querySelector('#createTournament').disabled);
  await page.screenshot({path:'test-output/custom-matchups-ui.png'});
  await page.locator('#tname').fill('UI custom matchups');await page.locator('#createTournament').click();await page.waitForFunction(()=>!document.querySelector('#modal').open&&state.snapshot?.settings.format==='custom');
  assert.equal(await page.evaluate(()=>state.snapshot.total),10);
  await page.locator('[data-view=events]').click();await page.locator('#newEvent').click();await page.locator('#eventSource').selectOption(ready.source);
  await page.waitForFunction(()=>document.querySelector('#eventGroups').value.split('\n').length===2);
  await page.locator('#eventFinal').selectOption('round_robin');await page.locator('#eventAdvance').fill('2');await page.locator('#eventCalculate').click();
  await page.waitForFunction(()=>!document.querySelector('#eventSave').disabled);
  assert.equal(await page.locator('#eventPreview').textContent(),'24');await page.screenshot({path:'test-output/multistage-builder.png'});
  await page.locator('#eventSave').click();await page.waitForSelector('#eventRun');await page.locator('#eventRun').click();
  await page.waitForFunction(()=>eventDetailData?.state==='completed',{},{timeout:40000});
  assert.equal(await page.evaluate(()=>eventDetailData.official_games),24);assert.equal(await page.locator('#eventChildren tr').count(),3);
  await page.screenshot({path:'test-output/multistage-completed.png'});
  const text=await page.evaluate(()=>eventReport(eventDetailData));assert.ok(text.includes('Qualified'));assert.ok(text.includes('Engine 1'));
  await page.locator('[data-stage]').first().click();await page.waitForFunction(()=>state.snapshot?.event&&document.querySelector('#eventContext').textContent.includes('Engine championship'));
  assert.equal(await page.locator('#start').isDisabled(),true);
  assert.deepEqual(errors,[]);fs.writeFileSync('test-output/events-ui.json',JSON.stringify({errors,customGames:10,eventGames:24,stageCount:3,qualified:true},null,2));console.log('Custom and multi-stage GUI workflows passed.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
