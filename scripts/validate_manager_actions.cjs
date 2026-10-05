// Reuse only the explicit disposable manager fixture after its main UI check.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/manager-ui-ready.json','utf8'));
 const browser=await chromium.launch({headless:true,channel:'msedge'}),responses=[];
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1000}});
  page.on('response',r=>{if(r.url().endsWith('/api/tournament-queue')&&r.request().method()==='POST')responses.push(r.status())});
  await page.goto(ready.url+'&lang=en');await page.waitForFunction(()=>queueData?.execution_mode==='parallel');
  await page.locator('[data-view=tournamentQueue]').click();await page.waitForFunction(()=>queueData.items&&!queueLoading);
  const tid=await page.evaluate(()=>queueData.items.find(x=>!x.finished&&x.state==='paused').tid);
  await page.evaluate(()=>{queueData.revision=-1});
  await page.locator(`[data-queue-row="${tid}"] [data-manager-action=resume_selected]`).click();
  await page.waitForFunction(id=>!queueMutating&&state.live.some(g=>g.tid===id),tid);
  assert.deepEqual(responses.slice(0,2),[400,200]);
  assert.equal(await page.locator('#error').isVisible(),false);
  await page.locator('#queuePause').click();await page.waitForFunction(()=>!queueMutating&&!state.live.length&&queueData.running===0);
  const result=JSON.parse(fs.readFileSync('test-output/manager-ui/acceptance.json','utf8'));
  assert.ok(result.passed&&result.packaged);result.stale_revision_retry=true;
  fs.writeFileSync('test-output/manager-ui/acceptance.json',JSON.stringify(result,null,2));
  console.log('Stale-revision recovery and global pause passed in the packaged manager.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
