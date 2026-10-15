const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/tournament-edit-ready.json','utf8')),browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const page=await browser.newPage({viewport:{width:1350,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(ready.url+'&lang=en');await page.waitForFunction(()=>state.snapshot&&queueData);
  await page.evaluate(async()=>{for(const id of ['2','3']){const p=(await api('profiles?limit=5')).items.find(p=>p.id===id);delete p.advertised;await api('profiles',{...p,discover:false})}state.selected=new Set(['2','3']);view('engines')});
  await page.locator('#bulkEngine').click();await page.waitForSelector('#bulkDiscover');
  let release;const gate=new Promise(r=>release=r);let calls=0;
  await page.route('**/api/profiles/inspect-options',async route=>{calls++;const response=await route.fetch();await gate;await route.fulfill({response})});
  await page.locator('#bulkDiscover').click();await page.waitForFunction(()=>document.querySelector('#bulkStopDiscovery').hidden===false);
  await page.locator('#bulkStopDiscovery').click();release();await page.waitForFunction(()=>document.querySelector('#bulkDiscoveryStatus').textContent.includes('1 still need discovery'));
  assert.equal(calls,1);await page.unroute('**/api/profiles/inspect-options');
  await page.locator('#bulkDiscover').click();await page.waitForFunction(()=>document.querySelector('#bulkDiscoveryStatus').textContent.includes('0 still need discovery'));
  await page.locator('#bulkUseThreads').check();await page.locator('#bulkThreads').fill('2');await page.locator('#bulkReview').click();await page.waitForSelector('#bulkRows tr');assert.match(await page.locator('#bulkSummary').textContent(),/2 profiles will change; 0/);
  await page.locator('#applyBulk').click();await page.waitForFunction(()=>!document.querySelector('#modal').open);
  const result=await page.evaluate(async()=>(await api('profiles?limit=5')).items.filter(p=>['2','3'].includes(p.id)));assert.equal(result.length,2);assert(result.every(p=>p.threads===2&&p.options.Threads===2));
  assert.deepEqual(errors,[]);fs.writeFileSync('test-output/setup-workflow-ui/discovery.json',JSON.stringify({passed:true,stopAfterOne:true,resumeMissing:true,bulkAfterImport:true,errors},null,2));console.log('Imported-profile discovery, stop/resume and bulk edit passed');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
