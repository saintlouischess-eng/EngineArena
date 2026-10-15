const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/league-ready.json','utf8')),browser=await chromium.launch({headless:true,channel:'msedge'}),errors=[],checks=[];
 const out='test-output/season-ui';fs.mkdirSync(out,{recursive:true});
 try{
  const page=await browser.newPage({viewport:{width:1500,height:1050}});page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.dismiss());
  await page.goto(ready.url);await page.waitForFunction(()=>state.snapshot&&typeof newSeason==='function');
  await page.locator('[data-view=events]').click();await page.locator('#newSeason').click();
  await page.locator('#snSource').selectOption(ready.source);await page.waitForFunction(()=>document.querySelector('#snCPU').value==='28');
  await page.locator('#snSizes').fill('8,8,8,8,8,8,8,8');await page.locator('#snSizes').dispatchEvent('change');
  for(const [preset,count] of [['qualify',1360],['divisions',912],['progressive',1136]]){
   await page.locator('#snPreset').selectOption(preset);await page.locator('#snCalculate').click();await page.waitForFunction(()=>!document.querySelector('#snSave').disabled);
   assert.match(await page.locator('#snPreview').textContent(),new RegExp(count.toLocaleString('en')));
  }
  await page.locator('#snStageConditions input[data-key="0"]').fill('3');await page.locator('#snNames').dispatchEvent('change');
  assert.equal(await page.locator('#snStageConditions input[data-key="0"]').inputValue(),'3');
  await page.locator('#snCycles').fill('1');await page.locator('#snCycles').dispatchEvent('change');
  await page.locator('#snPreset').selectOption('qualify');await page.locator('#snCalculate').click();await page.waitForFunction(()=>!document.querySelector('#snSave').disabled);
  await page.locator('.modal-body').evaluate(el=>el.scrollTop=0);await page.screenshot({path:out+'/builder-top.png'});
  await page.locator('#snSave').click();await page.waitForSelector('#seasonRoster');assert.equal(await page.locator('#eventRun').isDisabled(),true);
  const id=await page.evaluate(()=>eventDetailData.id);await page.locator('#seasonRoster').click();await page.waitForSelector('#rosterApprove');
  await page.locator('#rosterNext').click();assert.match(await page.locator('#rosterPage').textContent(),/51–64/);
  await page.locator('#rosterPrev').click();await page.screenshot({path:out+'/roster.png'});
  await page.locator('#rosterApprove').click();await page.waitForSelector('#eventRun');assert.equal(await page.locator('#eventRun').isDisabled(),false);
  const report=await page.evaluate(()=>eventReport(eventDetailData));assert.match(report,/scheduled/);
  await page.locator('#eventDelete').click();await page.locator('#eventDeleteConfirm').click();await page.waitForFunction(()=>document.querySelector('#eventDeleteConfirm').hidden);
  assert.match(await page.locator('#eventDeleteProgress').textContent(),/Cleanup complete/);await page.keyboard.press('Escape');
  await page.evaluate(id=>showEvent(id),ready.season);const completed=await page.evaluate(()=>eventReport(eventDetailData));
  assert.match(completed,/Championship final:/);assert.match(completed,/Division assignments/);fs.writeFileSync(out+'/completed-report.txt',completed);
  await page.locator('.season-decision').last().locator('summary').click();await page.screenshot({path:out+'/completed.png'});await page.keyboard.press('Escape');
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await page.goto(ready.url+'&lang='+lang);await page.waitForFunction(()=>state.snapshot&&typeof newSeason==='function');
   await page.evaluate(async()=>{window.missingMessages=new Set();ArenaI18n.capture(k=>{if(ArenaI18n.locale!=='en'&&!Object.hasOwn(window.ARENA_MESSAGES,k))missingMessages.add(k)});displayPrefs.fontSize=20;applyDisplay();await newSeason()});
   await page.locator('#snSource').selectOption(ready.source);await page.waitForFunction(()=>document.querySelector('#snCPU').value==='28');
   await page.locator('#snSizes').fill('8,8,8,8,8,8,8,8');await page.locator('#snSizes').dispatchEvent('change');
   for(const preset of ['qualify','divisions','progressive'])await page.locator('#snPreset').selectOption(preset);
   for(const width of [1050,1600])for(const theme of ['dark','light']){
    await page.setViewportSize({width,height:1050});await page.evaluate(t=>document.body.classList.toggle('light',t==='light'),theme);
    const check=await page.evaluate(()=>({missing:[...missingMessages],overflow:document.querySelector('#modal').scrollWidth>document.querySelector('#modal').clientWidth+2}));
    assert.deepEqual(check.missing,[],lang);assert.equal(check.overflow,false,lang);checks.push({lang,width,theme});
   }
   if(['en','de','pl'].includes(lang)){await page.locator('.modal-body').evaluate(el=>el.scrollTop=0);await page.screenshot({path:out+'/builder-'+lang+'.png'})}
   await page.keyboard.press('Escape');await page.evaluate(id=>showEvent(id),ready.season);
   await page.evaluate(()=>eventReport(eventDetailData));assert.deepEqual(await page.evaluate(()=>[...missingMessages]),[],lang);await page.keyboard.press('Escape');
  }
  assert.deepEqual(errors,[]);fs.writeFileSync(out+'/acceptance.json',JSON.stringify({passed:true,id,errors,checks,presets:3,create:true,roster:true,delete:true,report:true},null,2));
  console.log('Season UI passed: three presets, custom cycles, roster pagination/approval, deletion, complete report, eight languages / 32 layouts.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
