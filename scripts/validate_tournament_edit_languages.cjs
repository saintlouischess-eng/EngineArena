const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/tournament-edit-ready.json','utf8'));
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const page=await browser.newPage({viewport:{width:1100,height:850}}),errors=[],evidence=[];
  page.on('pageerror',e=>errors.push(e.message));
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await page.goto(ready.url+'&lang='+lang);await page.waitForFunction(()=>typeof state!=='undefined'&&state.snapshot);
   await page.evaluate(async id=>{
    state.tid=id;await refreshTournament();window.missingMessages=new Set();
    ArenaI18n.capture(key=>{if(ArenaI18n.locale!=='en'&&!Object.hasOwn(window.ARENA_MESSAGES,key))missingMessages.add(key)});
    displayPrefs.fontSize=20;applyDisplay();await newTournament(await api(`tournaments/${id}/setup`));
   },ready.legacy);
   await page.waitForFunction(()=>!document.querySelector('#createTournament').disabled);
   const result=await page.evaluate(()=>({language:ArenaI18n.locale,missing:[...missingMessages],
    overflow:document.querySelector('#modal').scrollWidth>document.querySelector('#modal').clientWidth+1,
    title:document.querySelector('#dialogTitle').textContent,save:document.querySelector('#createTournament').textContent}));
   assert.equal(result.language,lang);assert.deepEqual(result.missing,[]);assert.equal(result.overflow,false);evidence.push(result);
   if(lang==='en'||lang==='de')await page.screenshot({path:`test-output/tournament-edit-${lang}.png`});
  }
  assert.deepEqual(errors,[]);fs.writeFileSync('test-output/tournament-edit-languages.json',JSON.stringify({errors,evidence},null,2));console.log('All 8 edit-dialog languages passed at 20px');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
