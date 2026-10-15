const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync(process.env.ARENA_PAGES_READY||'test-output/event-pages-ready.json','utf8'));
 const out=process.env.ARENA_PAGES_OUT||'test-output/event-pages-ui';fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--disable-gpu']}),page=await browser.newPage({viewport:{width:1500,height:1050}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(ready.url);await page.waitForFunction(()=>state.connected&&typeof SeasonDesk!=='undefined');
  await page.evaluate(id=>showEvent(id),ready.qualifier);await page.waitForSelector('.si-division');
  const table=page.locator('.si-division').first();
  assert.equal(await table.locator('tbody tr').count(),50);
  assert.match(await table.locator('.si-entry-pager').innerText(),/1–50 \/ 64/);
  await table.locator('[data-entry-offset="50"]').click();
  await page.waitForFunction(()=>document.querySelector('.si-entry-table').dataset.offset==='50');
  assert.equal(await table.locator('tbody tr').count(),14);
  assert.equal(await table.locator('tbody tr').last().locator('td').first().innerText(),'64');
  assert.match(await table.locator('.si-entry-pager').innerText(),/51–64 \/ 64/);
  assert.equal(await table.locator('button[id^=siEntryNext]').isDisabled(),true);
  await page.evaluate(()=>loadInsights());assert.equal(await table.locator('tbody tr').count(),14);
  await table.locator('.si-entry-table').evaluate(el=>el.scrollTop=el.scrollHeight);
  assert.equal(await table.locator('.si-entry-table').evaluate(el=>el.querySelector('tbody tr:last-child').getBoundingClientRect().bottom<=el.getBoundingClientRect().bottom+1),true);
  await page.screenshot({path:out+'/qualification-last-page.png'});
  // A changed live snapshot must retain table scroll and keyboard focus.
  await table.locator('button[id^=siEntryPrev]').click();
  await page.waitForFunction(()=>document.querySelector('.si-entry-table').dataset.offset==='0');
  await table.locator('.si-entry-table').evaluate(el=>el.scrollTop=270);
  await table.locator('button[id^=siEntryNext]').focus();
  await page.route('**/api/events/*?view=insights*',async route=>{const response=await route.fetch(),d=await response.json();d.official+=1;await route.fulfill({json:d})});
  await page.evaluate(()=>loadInsights());
  assert.equal(await table.locator('.si-entry-table').evaluate(el=>el.scrollTop),270);
  assert.equal(await table.locator('button[id^=siEntryNext]').evaluate(el=>el===document.activeElement),true);
  await page.unroute('**/api/events/*?view=insights*');
  // Switching events resets pages; each 16-engine division includes the bottom places.
  await page.evaluate(id=>showEvent(id),ready.divisions);await page.waitForSelector('.si-division');
  assert.equal(await page.locator('.si-division').count(),4);
  for(const section of await page.locator('.si-division').all()){
   assert.equal(await section.locator('tbody tr').count(),16);
   assert.equal(await section.locator('tbody tr').last().locator('td').first().innerText(),'16');
   assert.match(await section.locator('.si-entry-pager').innerText(),/1–16 \/ 16/);
  }
  await page.screenshot({path:out+'/division-full-field.png'});
  const layouts=[];
  for(const width of [1050,1500])for(const theme of ['light','dark']){
   await page.setViewportSize({width,height:900});await page.evaluate(t=>{document.body.classList.toggle('light',t==='light');displayPrefs.fontSize=20;applyDisplay()},theme);
   assert.equal(await page.locator('#modal').evaluate(el=>el.scrollWidth>el.clientWidth+2),false);
   layouts.push({width,theme,fontSize:20});
  }
  // Export remains complete and independent of the currently viewed page.
  await page.evaluate(id=>showEvent(id),ready.qualifier);await page.locator('#siTab-summary').click();await page.waitForSelector('#siSummaryDetail');
  await page.locator('#siSummaryDetail').selectOption('full');
  assert.match(await page.locator('#siSummaryPreview').inputValue(),/64\s+63\s/);
  assert.deepEqual(errors,[]);
  fs.writeFileSync(out+'/result.json',JSON.stringify({passed:true,qualificationPlaces:64,divisionPlaces:[16,16,16,16],pagePreserved:true,scrollAndFocusPreserved:true,completeExport:true,layouts,errors},null,2));
  console.log('Event pages: all 64 places, all 16-engine divisions, refresh, scroll, focus, exports and layouts passed.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
