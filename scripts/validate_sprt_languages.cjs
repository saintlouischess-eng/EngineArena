const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/events-ready.json','utf8')),browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
 const page=await browser.newPage({viewport:{width:1400,height:1000}}),errors=[],evidence=[];page.on('pageerror',e=>errors.push(e.message));
 for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
  await page.goto(ready.url+'&lang='+lang);await page.waitForFunction(()=>state.snapshot&&typeof renderSprt==='function');
  await page.evaluate(async ids=>{window.missingMessages=new Set();ArenaI18n.capture(key=>{if(ArenaI18n.locale!=='en'&&!Object.hasOwn(ARENA_MESSAGES,key))missingMessages.add(key)});displayPrefs.fontSize=20;applyDisplay();state.selected=new Set(ids.slice(0,2));await newTournament()},ready.profiles);
  await page.locator('#tformat').selectOption('sprt');await page.waitForFunction(()=>$('#sprtCandidate').textContent.includes('Engine 2'));
  for(const paired of [true,false]){
   await page.locator('#tpaired').setChecked(paired);await page.locator('#sprtSetup').scrollIntoViewIfNeeded();
   for(const width of [1400,1050]){await page.setViewportSize({width,height:1000});const r=await page.evaluate(()=>({language:ArenaI18n.locale,missing:[...missingMessages],overflow:document.documentElement.scrollWidth>innerWidth,dialogOverflow:$('.modal-body').scrollWidth>$('.modal-body').clientWidth+1}));assert.deepEqual(r.missing,[]);assert.equal(r.overflow,false);assert.equal(r.dialogOverflow,false);evidence.push({paired,width,...r})}
  }
  if(lang==='en'||lang==='de')await page.screenshot({path:`test-output/sprt-${lang}-20px.png`});
  await page.evaluate(()=>$('#modal').close());await page.evaluate(()=>renderSprt(state.snapshot));assert.deepEqual(await page.evaluate(()=>[...missingMessages]),[]);
 }
 assert.deepEqual(errors,[]);fs.writeFileSync('test-output/sprt-languages.json',JSON.stringify({errors,evidence},null,2));console.log('Eight SPRT languages, paired/unpaired controls and 32 layouts passed.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
