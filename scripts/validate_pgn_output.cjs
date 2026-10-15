const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync(process.env.ARENA_PGN_READY||'test-output/pgn-output-ready.json','utf8'));
 const out=process.env.ARENA_PGN_OUT||'test-output/pgn-output-ui';fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const page=await browser.newPage({viewport:{width:1400,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  const waitGames=async count=>{for(let i=0;i<200;i++){const r=await page.evaluate(()=>api('pgn-output'));if(r.targets.some(t=>t.games>=count&&!t.pending))return;await new Promise(r=>setTimeout(r,100))}throw Error('PGN saving did not finish')};
  const openSettings=async()=>{if(!await page.locator('.reports-menu').evaluate(e=>e.open))await page.locator('.reports-menu>summary').click();await page.locator('#automaticPgn').click();await page.waitForFunction(()=>document.querySelector('#modal').open&&document.querySelector('#autoPgnApply'))};
  await page.goto(ready.url);await page.waitForFunction(()=>typeof state!=='undefined'&&state.snapshot);
  await page.evaluate(async tid=>{state.tid=tid;await refreshTournament()},ready.one);
  await openSettings();await page.locator('#autoPgnEnabled').check();
  await page.locator('#autoPgnPath').fill(ready.output);if(fs.existsSync(ready.output))await page.locator('#autoPgnMode').selectOption('append');await page.locator('#autoPgnRemember').check();
  await page.screenshot({path:path.join(out,'destination.png')});
  await page.locator('#autoPgnApply').click();await page.waitForFunction(()=>!document.querySelector('#modal').open);
  await waitGames(1);
  await page.evaluate(async tid=>{state.tid=tid;await refreshTournament()},ready.two);
  await openSettings();assert.equal(await page.locator('#autoPgnEnabled').isChecked(),true);
  assert.equal(await page.locator('#autoPgnMode').inputValue(),'append');
  await page.locator('#autoPgnApply').click();await page.waitForFunction(()=>!document.querySelector('#modal').open);
  await waitGames(2);
  assert.equal((fs.readFileSync(ready.output,'utf8').match(/^\[GameId /gm)||[]).length,2);
  await page.evaluate(async()=>{state.selected=new Set(await api('profiles/selection'));return newTournament(null,true)});
  assert.equal(await page.locator('#autoPgnEnabled').isChecked(),true);
  assert.equal((await page.locator('#autoPgnPath').inputValue()).toLowerCase(),ready.output.toLowerCase());
  await page.locator('#tname').fill('Remembered output setup');await page.locator('#createTournament').click();
  await page.waitForFunction(()=>!document.querySelector('#modal').open);
  const created=await page.evaluate(()=>state.tid);
  const info=await page.evaluate(()=>api('pgn-output'));assert.ok(info.links.some(l=>l.tid===created));
  await openSettings();await page.locator('#autoPgnEnabled').uncheck();await page.locator('#autoPgnApply').click();
  await page.waitForFunction(()=>!document.querySelector('#modal').open);
  const disabled=await page.evaluate(()=>api('pgn-output'));assert.ok(!disabled.links.some(l=>l.tid===created));
  const languages=[];
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await page.goto(ready.url+'&lang='+lang);await page.waitForFunction(()=>typeof state!=='undefined'&&state.snapshot);
   await page.evaluate(()=>{window.missing=new Set();ArenaI18n.capture(k=>{if(ArenaI18n.locale!=='en'&&!Object.hasOwn(window.ARENA_MESSAGES,k))missing.add(k)});document.documentElement.style.fontSize='20px';return automaticPgnDialog()});
   await page.setViewportSize({width:980,height:800});
   const r=await page.evaluate(()=>({lang:ArenaI18n.locale,missing:[...missing],overflow:$('#modal').scrollWidth>$('#modal').clientWidth}));
   assert.deepEqual(r.missing,[]);assert.equal(r.overflow,false);languages.push(r);
  }
  await page.screenshot({path:path.join(out,'large-text.png')});
  assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({errors,languages,combinedGames:2,rememberedSetup:true,disable:true},null,2));
  console.log('Automatic PGN UI passed: shared file, remembered setup, disable, 8 languages.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
