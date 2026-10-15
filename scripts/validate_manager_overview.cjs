const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/manager-overview-ready.json','utf8'));
 const browser=await chromium.launch({headless:true,channel:'msedge'}),errors=[],checks=[];
 const out='test-output/manager-overview-ui';fs.mkdirSync(out,{recursive:true});
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1050}});page.on('pageerror',e=>errors.push(e.message));
  await page.goto(ready.url);await page.waitForFunction(()=>queueData);
  await page.locator('[data-view=tournamentQueue]').click();
  await page.waitForFunction(()=>queueData?.overview&&queueData.items.filter(x=>x.event_id).length===8);
  assert.equal(await page.locator('#queueRows tr').count(),10);
  assert.equal(await page.locator('#queueRows [data-manager-event]').count(),8);
  assert.equal(await page.locator('#queueRows [data-manager-select]').count(),1);
  assert.equal(await page.locator('#queueRun').isDisabled(),true);assert.equal(await page.locator('#queuePause').isDisabled(),true);
  assert.match(await page.locator('#managerEvent').textContent(),/Eight-division league/);
  assert.equal(await page.locator('#tournamentQueue .queue-controls').isVisible(),false);
  assert.match(await page.locator('#queueStatus').textContent(),/Independent queue/);
  await page.waitForFunction(()=>document.querySelector('#managerResources').textContent.includes('/ 2'));
  await page.locator('#managerSelectPage').check();assert.equal(await page.locator('#managerResume').isDisabled(),true);
  assert.equal(await page.locator('#managerPause').isDisabled(),true);await page.locator('#managerSelectPage').uncheck();
  await page.locator('#managerScope').selectOption('events');await page.waitForFunction(()=>queueData.scope==='events'&&!queueLoading);
  assert.equal(await page.locator('#queueRows tr').count(),8);assert.equal(await page.locator('#managerSelectPage').isDisabled(),true);
  await page.locator('[data-manager-sort=progress]').click();await page.waitForFunction(()=>queueData.sort==='progress'&&!queueLoading);
  await page.locator('[data-manager-sort=progress]').click();await page.waitForFunction(()=>queueData.direction==='desc'&&!queueLoading);
  let values=await page.evaluate(()=>queueData.items.map(x=>x.official_games/x.total));assert.ok(values.every((v,i)=>!i||values[i-1]>=v));
  await page.locator('#managerSearch').fill('Division 2');await page.waitForFunction(()=>queueData.filtered_total===1&&!queueLoading);
  await page.locator('#managerSearch').fill('');await page.waitForFunction(()=>queueData.filtered_total===8&&!queueLoading);
  await page.locator('#managerEventResources').click();await page.waitForSelector('#erCPU');
  assert.equal(await page.locator('#erCPU').inputValue(),'2');assert.equal(await page.locator('#erMemory').inputValue(),'1024');await page.keyboard.press('Escape');
  const initial=await page.evaluate(()=>queueData.items.reduce((sum,x)=>sum+x.official_games,0));
  await page.waitForFunction(n=>queueData.items.reduce((sum,x)=>sum+x.official_games,0)>n,initial,{timeout:45000});
  const eventRow=await page.locator('#queueRows [data-manager-event]').first().getAttribute('data-manager-event');assert.equal(eventRow,ready.event);
  await page.locator('#queueRows [data-manager-event]').first().click();await page.waitForSelector('#eventSummary');await page.keyboard.press('Escape');
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await page.goto(ready.url+'&lang='+lang);await page.waitForFunction(()=>queueData);
   await page.evaluate(async()=>{window.missingMessages=new Set();ArenaI18n.capture(k=>{if(ArenaI18n.locale!=='en'&&!Object.hasOwn(window.ARENA_MESSAGES,k))missingMessages.add(k)});displayPrefs.fontSize=20;applyDisplay();await showQueue()});
   await page.locator('#managerScope').selectOption('events');await page.waitForFunction(()=>!queueLoading&&queueData.scope==='events');
   for(const width of [1050,1600])for(const theme of ['dark','light']){
    await page.setViewportSize({width,height:1050});await page.evaluate(t=>document.body.classList.toggle('light',t==='light'),theme);
    const check=await page.evaluate(()=>({missing:[...missingMessages],overflow:document.documentElement.scrollWidth>innerWidth+1}));
    assert.deepEqual(check.missing,[]);assert.equal(check.overflow,false);checks.push({lang,width,theme});
   }
   if(['en','de','pl'].includes(lang))await page.screenshot({path:out+'/manager-'+lang+'.png',fullPage:true});
  }
  await page.goto(ready.url);await page.waitForFunction(()=>queueData);await page.evaluate(async()=>showQueue());
  await page.locator('#managerScope').selectOption('events');await page.waitForFunction(()=>queueData.scope==='events'&&!queueLoading);
  await page.screenshot({path:out+'/manager-running.png',fullPage:true});
  await page.locator('#queueRows [data-qview]').first().click();await page.waitForFunction(()=>state.view==='overview'&&state.snapshot?.event);
  assert.ok(await page.locator('#openParentEvent').isVisible());
  assert.deepEqual(errors,[]);
  fs.writeFileSync(out+'/acceptance.json',JSON.stringify({passed:true,errors,checks,rows:10,liveProgress:true,eventOwnership:true,resources:true,sort:true,search:true,navigation:true},null,2));
  console.log('Manager overview passed: live progress, league/queue separation, correct event budget, sorting, filtering, navigation and 32 language/layout checks.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
