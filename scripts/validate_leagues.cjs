const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/events-ready.json','utf8')),browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto(ready.url);await page.waitForFunction(()=>state.snapshot&&typeof newEvent==='function');
  await page.locator('[data-view=events]').click();await page.locator('#newEvent').click();await page.locator('#eventSource').selectOption(ready.source);await page.locator('#eventKind').selectOption('league');
  await page.locator('#eventGroupCount').fill('3');await page.locator('#eventDistribute').click();await page.locator('#leagueNames').fill('Premier\nChallengers\nQualifiers');await page.locator('#eventName').fill('Three-division league');
  await page.locator('#eventCalculate').click();await page.waitForFunction(()=>!document.querySelector('#eventSave').disabled);assert.equal(await page.locator('#eventPreview').textContent(),'18');
  await page.screenshot({path:'test-output/league-builder.png'});
  await page.locator('#eventSave').click();await page.waitForSelector('#eventRun');await page.locator('#eventRun').click();await page.waitForFunction(()=>eventDetailData?.state==='completed',{},{timeout:40000});
  assert.equal(await page.evaluate(()=>eventDetailData.official_games),18);assert.equal(await page.evaluate(()=>eventDetailData.decisions.length),3);
  await page.locator('#eventDecisions').evaluate(el=>el.closest('details').open=true);assert.ok((await page.locator('#eventDecisions').textContent()).includes('Promoted'));await page.screenshot({path:'test-output/league-completed.png'});
  await page.locator('#leagueExtend').click();await page.waitForFunction(()=>eventDetailData?.state==='paused'&&eventDetailData.definition.seasons===4);await page.locator('#eventRun').click();await page.waitForFunction(()=>eventDetailData?.state==='completed',{},{timeout:25000});
  assert.equal(await page.evaluate(()=>eventDetailData.official_games),24);assert.ok((await page.evaluate(()=>eventReport(eventDetailData))).includes('Premier'));
  for(const width of [1100,1550]){await page.setViewportSize({width,height:900});await page.evaluate(()=>document.documentElement.style.fontSize='20px');assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);}
  assert.deepEqual(errors,[]);fs.writeFileSync('test-output/leagues-ui.json',JSON.stringify({errors,divisions:3,seasons:4,officialGames:24,promotion:true,extension:true},null,2));console.log('League GUI workflows passed: 24 games, four seasons.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
