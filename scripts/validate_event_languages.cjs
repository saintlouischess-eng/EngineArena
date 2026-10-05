const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/events-ready.json','utf8')),browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const page=await browser.newPage({viewport:{width:1400,height:1050}}),errors=[],evidence=[];page.on('pageerror',e=>errors.push(e.message));
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await page.goto(ready.url+'&lang='+lang);await page.waitForFunction(()=>state.snapshot&&typeof newEvent==='function');
   await page.evaluate(async ids=>{window.missingMessages=new Set();ArenaI18n.capture(key=>{if(ArenaI18n.locale!=='en'&&!Object.hasOwn(ARENA_MESSAGES,key))missingMessages.add(key)});displayPrefs.fontSize=20;applyDisplay();state.selected=new Set(ids);await newTournament()},ready.profiles);
   await page.locator('#tformat').selectOption('custom');await page.locator('#customPairs').fill('1 2 2\n3 4 1');await page.waitForFunction(()=>document.querySelector('#totalPreview').textContent==='6');
   await page.evaluate(()=>document.querySelector('#modal').close());await page.evaluate(()=>newEvent());await page.locator('#eventKind').selectOption('league');await page.locator('#eventCalculate').click();await page.waitForFunction(()=>!document.querySelector('#eventSave').disabled);
   for(const width of [1400,1100]){
    await page.setViewportSize({width,height:1050});const r=await page.evaluate(()=>({language:ArenaI18n.locale,missing:[...missingMessages],overflow:document.documentElement.scrollWidth>innerWidth,dialogOverflow:document.querySelector('.modal-body').scrollWidth>document.querySelector('.modal-body').clientWidth+1,save:document.querySelector('#eventSave').textContent}));
    assert.deepEqual(r.missing,[]);assert.equal(r.overflow,false);assert.equal(r.dialogOverflow,false);evidence.push({width,...r});
   }
   if(lang==='en'||lang==='de'){await page.evaluate(()=>document.querySelector('.modal-body').scrollTop=0);await page.screenshot({path:`test-output/events-${lang}-20px.png`})}
  }
  assert.deepEqual(errors,[]);fs.writeFileSync('test-output/events-languages.json',JSON.stringify({errors,evidence},null,2));console.log('Eight event languages and 16 layouts passed at 20px.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
