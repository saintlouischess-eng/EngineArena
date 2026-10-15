const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/tournament-edit-ready.json','utf8')),browser=await chromium.launch({headless:true,channel:'msedge'}),results=[];
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1050}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(ready.url+'&lang=en');await page.waitForFunction(()=>state.snapshot&&queueData);
  await page.evaluate(async()=>{const p=(await api('profiles?limit=1')).items[0];await api('profiles/import',{profiles:Array.from({length:505},(_,i)=>({...p,id:'large-'+i,name:'Z library '+String(i).padStart(3,'0')}))});const d=await api('setup-draft');await api('setup-draft',{revision:d.revision,value:null});state.selected=new Set(['0','1']);view('engines')});
  await page.locator('#engineSearch').fill('Z library');await page.locator('#bulkSelectAll').click();await page.waitForFunction(()=>state.selected.size===505);
  await page.locator('#bulkEngine').click();await page.locator('#bulkUseThreads').check();await page.locator('#bulkThreads').fill('2');await page.locator('#bulkReview').click();await page.waitForSelector('#bulkRows tr');
  assert.equal(await page.locator('#bulkRows tr').count(),50);await page.locator('#bulkNext').click();await page.waitForFunction(()=>document.querySelector('#bulkPage').textContent.startsWith('51'));
  await page.keyboard.press('Escape');await page.locator('#engineSearch').fill('');
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await page.goto(ready.url+'&lang='+lang);await page.waitForFunction(()=>state.snapshot&&queueData);
   await page.evaluate(async()=>{window.missingMessages=new Set();ArenaI18n.capture(k=>{if(ArenaI18n.locale!=='en'&&!Object.hasOwn(window.ARENA_MESSAGES,k))missingMessages.add(k)});state.selected=new Set(['0','1']);displayPrefs.fontSize=18;applyDisplay();await newTournament(null,true)});
   await page.waitForSelector('#setupEngineRows tr');await page.locator('#tformat').selectOption('gauntlet');await page.locator('[data-candidate="0"]').check();
   assert.equal(await page.locator('#tcandidates').isVisible(),false);assert.equal(await page.locator('#setupAll').isVisible(),true);
   await page.locator('#setupAll').click();await page.waitForFunction(()=>tournamentParticipantCount()===510);assert.equal(await page.locator('#setupEngineRows tr').count(),50);await page.locator('[data-pick="1"]').uncheck();await page.waitForFunction(()=>tournamentParticipantCount()===509);await page.locator('#setupAll').click();await page.waitForFunction(()=>tournamentParticipantCount()===510);
   await page.locator('#setupNext').click();await page.waitForFunction(()=>document.querySelector('#setupPage').textContent.startsWith('51'));
   await page.locator('#setupSearch').fill('Z library 504');await page.waitForFunction(()=>document.querySelectorAll('#setupEngineRows tr').length===1);await page.locator('[data-candidate="large-504"]').check();
   for(const width of [1440,1000])for(const theme of ['dark','light']){
    await page.setViewportSize({width,height:1050});await page.evaluate(t=>document.body.classList.toggle('light',t==='light'),theme);
    const r=await page.evaluate(()=>({missing:[...missingMessages],overflow:$('#modal').scrollWidth>$('#modal').clientWidth+1}));assert.equal(r.overflow,false);assert.deepEqual(r.missing,[]);results.push({lang,width,theme,...r});
   }
   if(lang==='en'){await page.locator('#setupEngineRows').scrollIntoViewIfNeeded();await page.screenshot({path:'test-output/setup-workflow-ui/library.png'})}
   await page.keyboard.press('Escape');
   await page.evaluate(()=>{state.selected=new Set(['0','1']);view('engines')});await page.locator('#bulkEngine').click();await page.waitForSelector('#bulkEditor');
   const bulk=await page.evaluate(()=>({missing:[...missingMessages],overflow:$('#modal').scrollWidth>$('#modal').clientWidth+1}));assert.deepEqual(bulk.missing,[]);assert.equal(bulk.overflow,false);await page.keyboard.press('Escape');
  }
  assert.deepEqual(errors,[]);fs.writeFileSync('test-output/setup-workflow-ui/library-languages.json',JSON.stringify({passed:true,profiles:510,bulkSelected:505,results,errors},null,2));console.log('Large library and 32 language/theme/width checks passed');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
