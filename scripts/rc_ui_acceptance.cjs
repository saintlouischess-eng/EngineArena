// Read-only workflow checks against an explicitly selected isolated workspace.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const file=process.argv[2],ready=JSON.parse(fs.readFileSync(file,'utf8'));
 const url=`http://127.0.0.1:${ready.port}/?token=${ready.token}`;
 const browser=await chromium.launch({headless:true,channel:'msedge'}),checks=[],errors=[];
 try{
  const page=await browser.newPage({viewport:{width:1550,height:1080}});page.on('pageerror',e=>errors.push(e.message));
  for(const language of ['en','es','fr','de','pt','it','nl','pl']){
   await page.goto(url+'&lang='+language);await page.waitForFunction(()=>typeof state!=='undefined'&&state.snapshot);
   await page.evaluate(()=>{window.missingMessages=new Set();ArenaI18n.capture(key=>{if(ArenaI18n.locale!=='en'&&!Object.hasOwn(window.ARENA_MESSAGES,key))missingMessages.add(key)})});
   await page.locator('[data-view=health]').click();await page.locator('.storage-panel details summary').click();await page.waitForFunction(()=>document.querySelector('#storageForecastNote').textContent.length>0);
   for(const width of [1100,1550]){
    await page.setViewportSize({width,height:1000});
    await page.evaluate(()=>{displayPrefs.fontSize=24;applyDisplay()});
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);
    assert.equal(overflow,false,language+' storage overflow '+width);
   }
   await page.screenshot({path:`test-output/rc-storage-${language}.png`});
   await page.evaluate(()=>{displayPrefs.fontSize=16;applyDisplay();view('overview')});
   await page.evaluate(()=>pgnDialog());await page.waitForFunction(()=>document.querySelector('#pgnExample')?.value.startsWith('[Event '));
   for(const preset of ['clean','annotated','testing','archive']){
    await page.locator('#pgnPreset').selectOption(preset);
    await page.waitForFunction(()=>!document.querySelector('#pgnPreviewStatus').textContent.includes('…'));
    // The request is debounced; wait for the chosen header signature.
    if(preset==='clean')await page.waitForFunction(()=>!document.querySelector('#pgnExample').value.includes('[AttemptId ')&&!document.querySelector('#pgnExample').value.includes('{'));
    if(preset==='testing')await page.waitForFunction(()=>document.querySelector('#pgnExample').value.includes('[AttemptId '));
    if(preset==='archive')await page.waitForFunction(()=>document.querySelector('#pgnExample').value.includes('[WhiteSettings '));
   }
   assert.equal(await page.locator('#modal').evaluate(e=>e.scrollWidth>e.clientWidth+2),false);
   await page.locator('#modal [data-close]').first().click();
   await page.evaluate(()=>showTournamentReport({technical:true}));await page.waitForSelector('iframe.report-preview');
   const frame=page.frames().find(f=>f.parentFrame());await frame.waitForSelector('h1');
   assert.equal(await frame.locator('html').getAttribute('lang'),language);
   assert.ok(await frame.locator('table').count()>5);
   await page.locator('#tournamentReportText').click();await page.waitForSelector('#textExportPreview');
   const txt=await page.locator('#textExportPreview').inputValue();assert.ok(txt.length>1000);
   await page.locator('#modal [data-close]').first().click();
   const missing=await page.evaluate(()=>[...missingMessages]);assert.deepEqual(missing,[],language+' missing translations');
   checks.push({language,largeTextWidths:[1100,1550],pgnPresets:4,reportTextCharacters:txt.length,missing});
  }
  // A simulated low-space response tests the banner without consuming disk.
  await page.route('**/api/storage',async route=>{
   const response=await route.fetch(),body=await response.json();body.forecast.warning=true;
   await route.fulfill({response,json:body});
  });
  await page.evaluate(()=>{storageLastPoll=0;return refreshStorage()});
  assert.equal(await page.locator('#storageWarning').isVisible(),true);
  await page.unroute('**/api/storage');await page.evaluate(()=>{storageLastPoll=0;return refreshStorage()});
  assert.equal(await page.locator('#storageWarning').isVisible(),false);
  await page.evaluate(()=>{ArenaI18n.capture(null);return api('preferences',{language:'en',fontSize:16,confidence:99,boardCount:4})});
  assert.deepEqual(errors,[]);
  fs.writeFileSync('test-output/rc-ui.json',JSON.stringify({checks,errors,lowSpaceBanner:true,passed:true},null,2));
  console.log('All eight language, PGN, report and storage layouts passed.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
