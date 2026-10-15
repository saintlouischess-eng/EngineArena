const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/tournament-edit-ready.json','utf8'));
 const browser=await chromium.launch({headless:true,channel:'msedge'}),errors=[],checks=[];
 const out='test-output/schedule-ui';fs.mkdirSync(out,{recursive:true});
 try{
  const page=await browser.newPage({viewport:{width:1500,height:1050}});page.on('pageerror',e=>errors.push(e.message));
  await page.goto(ready.url);await page.waitForFunction(()=>state.snapshot&&typeof schedulingSettings==='function');
  await page.evaluate(async()=>{state.selected=new Set(['0','1','2','3']);await newTournament()});
  assert.equal(await page.locator('#tScheduleOrder').inputValue(),'balanced');assert.equal(await page.locator('#tScheduleSeedField').isVisible(),false);
  await page.locator('#tformat').selectOption('round_robin');await page.locator('#tname').fill('Scheduling UI test');
  await page.locator('#tScheduleOrder').selectOption('shuffle');await page.locator('#tScheduleSeed').fill('2345');
  assert.equal(await page.locator('#tScheduleSeedField').isVisible(),true);
  await page.locator('#tScheduleSeed').fill('-1');assert.equal(await page.locator('#tScheduleSeed').evaluate(e=>e.checkValidity()),false);await page.locator('#tScheduleSeed').fill('2345');
  await page.locator('#createTournament').click();await page.waitForFunction(()=>!document.querySelector('#modal').open&&state.snapshot?.name==='Scheduling UI test');
  const tid=await page.evaluate(()=>state.tid);let t=await page.evaluate(id=>api('tournaments/'+id),tid);
  assert.equal(t.settings.schedule_order,'shuffle');assert.equal(t.settings.schedule_seed,2345);
  await page.locator('#editTournament').click();await page.waitForFunction(()=>document.querySelector('#tScheduleOrder')?.value==='shuffle'&&!document.querySelector('#createTournament').disabled);
  assert.equal(await page.locator('#tScheduleSeed').inputValue(),'2345');await page.locator('#tScheduleOrder').selectOption('balanced');
  await page.locator('#createTournament').click();await page.waitForFunction(()=>!document.querySelector('#modal').open);
  t=await page.evaluate(id=>api('tournaments/'+id),tid);assert.equal(t.settings.schedule_order,'balanced');
  await page.evaluate(async id=>newTournament(await api('tournaments/'+id+'/setup')),ready.rr);
  assert.equal(await page.locator('#tScheduleOrder').inputValue(),'legacy');await page.keyboard.press('Escape');
  await page.evaluate(()=>newEvent());await page.waitForFunction(()=>document.querySelector('#eventGroups')?.value);
  await page.locator('#eventScheduleOrder').selectOption('shuffle');await page.locator('#eventScheduleSeed').fill('99');
  await page.locator('#eventCalculate').click();await page.waitForFunction(()=>!document.querySelector('#eventSave').disabled);
  await page.locator('#eventSave').click();await page.waitForSelector('#eventSummary');
  const event=await page.evaluate(()=>eventDetailData);assert.equal(event.schedule_order,'shuffle');assert.equal(event.schedule_seed,99);
  assert.match(await page.evaluate(()=>eventReport(eventDetailData)),/Game scheduling[\s\S]*Seeded shuffle[\s\S]*Scheduling seed[\s\S]*99/);
  await page.keyboard.press('Escape');
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await page.goto(ready.url+'&lang='+lang);await page.waitForFunction(()=>state.snapshot&&typeof schedulingSettings==='function');
   await page.evaluate(async()=>{window.missingMessages=new Set();ArenaI18n.capture(k=>{if(ArenaI18n.locale!=='en'&&!Object.hasOwn(window.ARENA_MESSAGES,k))missingMessages.add(k)});state.selected=new Set(['0','1','2','3']);displayPrefs.fontSize=20;applyDisplay();await newTournament()});
   for(const format of ['round_robin','gauntlet','self_play','swiss','knockout','double_elimination','ladder','sprt','custom','match']){
    await page.locator('#tformat').selectOption(format);
    for(const order of ['balanced','matchup','shuffle'])await page.locator('#tScheduleOrder').selectOption(order);
   }
   await page.locator('#tformat').selectOption('round_robin');
   for(const width of [1050,1600])for(const theme of ['dark','light']){
    await page.setViewportSize({width,height:1050});await page.evaluate(t=>document.body.classList.toggle('light',t==='light'),theme);
    const check=await page.evaluate(()=>({missing:[...missingMessages],overflow:document.querySelector('#modal').scrollWidth>document.querySelector('#modal').clientWidth+2}));
    assert.deepEqual(check.missing,[]);assert.equal(check.overflow,false);checks.push({lang,width,theme});
   }
   await page.locator('#tScheduleOrder').scrollIntoViewIfNeeded();
   if(['en','de','pl'].includes(lang))await page.screenshot({path:out+'/scheduling-'+lang+'.png'});
   await page.keyboard.press('Escape');await page.evaluate(()=>newEvent());
   await page.locator('#eventScheduleOrder').selectOption('shuffle');await page.locator('#eventScheduleSeed').scrollIntoViewIfNeeded();
   assert.deepEqual(await page.evaluate(()=>[...missingMessages]),[]);await page.keyboard.press('Escape');
  }
  assert.deepEqual(errors,[]);fs.writeFileSync(out+'/acceptance.json',JSON.stringify({passed:true,errors,checks,formats:10,choices:3,create:true,edit:true,legacy:true,eventOverride:true,eventReport:true},null,2));
  console.log('Scheduling UI passed: create/edit, old settings, event override/report, 10 formats, three choices and 32 language/layout checks.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
