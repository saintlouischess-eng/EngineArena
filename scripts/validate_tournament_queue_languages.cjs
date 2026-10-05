const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/tournament-queue-ready.json','utf8'));
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const page=await browser.newPage({viewport:{width:1400,height:1050}}),errors=[],evidence=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(ready.url);await page.waitForFunction(()=>state.snapshot);await page.evaluate(()=>api('tournament-queue',{action:'add',all_ready:true}));
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await page.goto(ready.url+'&lang='+lang);await page.waitForFunction(()=>typeof state!=='undefined'&&state.snapshot);
   await page.evaluate(async()=>{
    window.missingMessages=new Set();ArenaI18n.capture(key=>{if(ArenaI18n.locale!=='en'&&!Object.hasOwn(window.ARENA_MESSAGES,key))missingMessages.add(key)});
    displayPrefs.fontSize=20;applyDisplay();await showQueue();
   });
   await page.locator('#queueStartMode').selectOption('later');
   for(const width of [1400,1000]){
    await page.setViewportSize({width,height:1050});
    const result=await page.evaluate(()=>({language:ArenaI18n.locale,missing:[...missingMessages],
     overflow:document.documentElement.scrollWidth>document.documentElement.clientWidth+1,
     button:document.querySelector('#queueRun').textContent,rows:document.querySelectorAll('[data-queue-row]').length,
     dateVisible:!!document.querySelector('#queueDate').getClientRects().length}));
    assert.equal(result.language,lang);assert.deepEqual(result.missing,[]);assert.equal(result.overflow,false);assert.equal(result.rows,3);assert.equal(result.dateVisible,true);evidence.push({width,...result});
    if(width===1400&&(lang==='en'||lang==='de'))await page.screenshot({path:`test-output/tournament-queue-${lang}.png`});
   }
  }
  assert.deepEqual(errors,[]);fs.writeFileSync('test-output/tournament-queue-languages.json',JSON.stringify({errors,evidence},null,2));console.log('8 queue languages, 16 layouts passed at 20px');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
