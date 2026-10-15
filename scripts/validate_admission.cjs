const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync(process.env.ADMISSION_READY||'test-output/admission-ready.json','utf8'));
 const browser=await chromium.launch({headless:true,channel:'msedge'}),errors=[],checks=[];
 const out='test-output/admission-ui-review';fs.mkdirSync(out,{recursive:true});
 try{
  const page=await browser.newPage({viewport:{width:1450,height:1050}});page.on('pageerror',e=>errors.push(e.message));
  await page.goto(ready.url);await page.waitForFunction(()=>state.snapshot&&typeof newSeason==='function');
  await page.evaluate(()=>newSeason());await page.locator('#snSource').selectOption(ready.source);
  await page.waitForFunction(()=>document.querySelector('#snSourceInfo').textContent.includes('300'));
  await page.locator('#snSizes').fill('16,16,16,16');await page.locator('#snSizes').dispatchEvent('change');
  await page.locator('#snAdmission').selectOption('full');
  assert.equal(await page.locator('#snQualify').isChecked(),true);
  assert.equal(await page.locator('#snQualify').isDisabled(),true);
  await page.locator('#snCalculate').click();await page.waitForFunction(()=>!document.querySelector('#snSave').disabled);
  assert.match(await page.locator('#snPreview').textContent(),/6,136/);
  await page.locator('#snAdmission').selectOption('challenge');await page.locator('#snRisk').fill('8');
  await page.locator('#snCalculate').click();await page.waitForFunction(()=>!document.querySelector('#snSave').disabled);
  assert.match(await page.locator('#snPreview').textContent(),/5,744/);
  await page.locator('#snAdmission').scrollIntoViewIfNeeded();await page.screenshot({path:out+'/setup.png'});
  await page.locator('#snSave').click();await page.waitForSelector('#seasonRoster');
  const id=await page.evaluate(()=>eventDetailData.id);
  await page.locator('#seasonRoster').click();await page.locator('#rosterNext').click();
  assert.match(await page.locator('#rosterPage').textContent(),/51–100 \/ 300/);
  assert.equal(await page.locator('#rosterDivision').isVisible(),false);
  assert.match(await page.locator('#seasonRosterList').textContent(),/Must qualify/);
  await page.screenshot({path:out+'/roster.png'});
  // Preview an invalid undersized candidate pool: the API must reject atomically.
  const rejected=await page.evaluate(async id=>{const e=await api('events/'+id);try{await api('events/'+id,{action:'review',revision:e.revision,candidates:[0,1]});return false}catch{const after=await api('events/'+id);return e.revision===after.revision&&after.admission.candidate_count===300}},id);
  assert.equal(rejected,true);
  await page.locator('#rosterApprove').click();await page.waitForSelector('#eventRun');assert.equal(await page.locator('#eventRun').isDisabled(),false);
  await page.evaluate(id=>showEvent(id),ready.completed);
  const report=await page.evaluate(()=>eventReport(eventDetailData));
  assert.match(report,/Not qualified/);assert.match(report,/Main season field size/);assert.match(report,/Season 2 — Qualification/);
  fs.writeFileSync(out+'/completed-report.txt',report);
  await page.locator('#siTab-stages').click();
  await page.locator('.season-decision').first().locator('summary').first().click();await page.screenshot({path:out+'/completed.png'});
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await page.goto(ready.url+'&lang='+lang);await page.waitForFunction(()=>state.snapshot&&typeof newSeason==='function');
   await page.evaluate(async()=>{window.missingMessages=new Set();ArenaI18n.capture(k=>{if(ArenaI18n.locale!=='en'&&!Object.hasOwn(window.ARENA_MESSAGES,k))missingMessages.add(k)});await newSeason()});
   await page.locator('#snSource').selectOption(ready.source);await page.waitForFunction(()=>document.querySelector('#snSourceInfo').textContent.includes('300'));
   await page.locator('#snAdmission').selectOption('challenge');await page.locator('#snField').fill('64');await page.locator('#snField').dispatchEvent('change');
   for(const width of [1050,1600]){
    await page.setViewportSize({width,height:1000});
    assert.equal(await page.locator('#modal').evaluate(el=>el.scrollWidth>el.clientWidth+2),false);
    assert.deepEqual(await page.evaluate(()=>[...missingMessages]),[],lang);checks.push({lang,width});
   }
   await page.evaluate(id=>showEvent(id),ready.completed);await page.evaluate(()=>eventReport(eventDetailData));
   assert.deepEqual(await page.evaluate(()=>[...missingMessages]),[],lang);
  }
  assert.deepEqual(errors,[]);
  fs.writeFileSync(out+'/acceptance.json',JSON.stringify({passed:true,errors,checks,created:id,preview:true,roster:true,report:true,atomicRejection:true},null,2));
  console.log('Admission UI passed: 300 candidates, 64 places, both forecasts, paged roster, approval, reports, 8 languages / 16 layouts.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
