// Shipped UI and API, on a copy of the long synthetic fixture only.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const ready=JSON.parse(fs.readFileSync(process.env.ARENA_MOVES_READY,'utf8')),out='test-output/scoresheet-package-ui';
assert(ready.long&&ready.folder.includes('test-output'));fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'}),errors=[],proof={passed:false,languages:[]};
 try{
  const page=await browser.newPage({viewport:{width:1200,height:900}});page.on('pageerror',e=>errors.push(e.stack));
  const settled=()=>page.waitForFunction(()=>!moveSheet.busy&&!moveSheet.pending&&!moveSheet.scrollLock&&moveSheet.rows.length&&moveSheet.data?.after===moveSheet.after&&moveSheet.data?.span===moveSheet.span);
  const select=async()=>{await page.waitForFunction(()=>state.snapshot);await page.evaluate(async r=>{state.tid=r.tid;await refreshTournament();await showFinalGame(r.gid);displayPrefs.panels.moves={visible:true,floating:true,bounds:{left:275,top:100,width:850,height:700}};applyDisplay()},ready);await settled()};
  await page.goto(ready.url);await select();
  const scroll=page.locator('.scoresheet-scroll'),finalFen=await page.evaluate(()=>selectedFocusGame().fen);
  const latest=await page.evaluate(()=>moveSheet.latest);assert(latest>600&&latest<=1000);
  await page.locator('#movesBeginning').click();await settled();
  assert.equal(await page.locator('.scoresheet tbody tr:first-child button span').textContent(),'1.');assert.equal(await scroll.evaluate(e=>e.scrollTop),0);
  await page.locator('[data-move="-3"]').click();assert.notEqual(await page.evaluate(()=>gameMovesView(selectedFocusGame()).fen),finalFen);
  assert.equal(await page.locator('.focus-last-move').textContent(),'Opening · 1. e4');
  await page.screenshot({path:out+'/beginning.png'});
  const seen=new Set();
  const windows=[[0,200],[0,400]];for(let after=200;after+200<latest;after+=200)windows.push([after,400]);
  for(const [after,span] of windows){
   await page.waitForFunction(({after,span})=>moveSheet.after===after&&moveSheet.span===span,{after,span});await settled();
   const rows=await page.locator('.scoresheet tbody tr').evaluateAll(rs=>rs.map(r=>Number(r.dataset.ply)));
   assert(rows.length<=404);assert.deepEqual([...new Set(rows)].sort((a,b)=>a-b),rows);rows.forEach(n=>seen.add(n));
   if(after!==windows.at(-1)[0]||span!==windows.at(-1)[1])await scroll.evaluate(e=>{e.scrollTop=e.scrollHeight});
  }
  for(let ply=-3;ply<=latest;ply++)assert(seen.has(ply),'Missing half-move '+ply);proof.allRecordedHalfMovesReachable=latest+4;
  assert.equal(await page.evaluate(()=>selectedFocusGame().fen),finalFen);
  await scroll.focus();await page.keyboard.press('End');await settled();
  assert.equal(await page.evaluate(()=>gameMovesView(selectedFocusGame()).fen),finalFen);assert(await scroll.evaluate(e=>e.scrollHeight-e.scrollTop-e.clientHeight<2));
  // A one-row final page has no scrollbar. The wheel must still load older
  // moves from that edge, just as it does when a taller page reaches the top.
  for(let after=Math.floor((latest-1)/200)*200-200;after>=0;after-=200){await scroll.evaluate(e=>{e.scrollTop=0});await scroll.hover();await page.mouse.wheel(0,-450);await page.waitForFunction(n=>moveSheet.after===n,after);await settled()}
  await scroll.focus();await page.keyboard.press('Home');await settled();assert.equal(await scroll.evaluate(e=>e.scrollTop),0);proof.forwardBackwardAndKeyboard=true;
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await page.setViewportSize({width:1050,height:800});await page.goto(ready.url+'&lang='+lang);await select();
   await page.evaluate(()=>{displayPrefs.fontSize=18;displayPrefs.moveFont=24;displayPrefs.moveDetails=true;displayPrefs.theme=ArenaI18n.locale==='de'?'light':'dark';displayPrefs.panels.moves={visible:true,floating:true,bounds:{left:250,top:85,width:770,height:650}};applyDisplay();paintMoveSheet()});
   await page.locator('#movesBeginning').click();await settled();
   await page.locator('[data-move="-3"]').click();
   assert.equal(await page.locator('.focus-last-move').textContent(),await page.evaluate(()=>ArenaI18n.t('Opening')+' · 1. e4'));
   assert(await page.locator('#movesBeginning').isVisible());assert.equal(await page.locator('.moves-toolbar').evaluate(e=>e.scrollWidth>e.clientWidth+1),false);
   const label=await page.locator('#movesBeginning').textContent();if(lang!=='en')assert.notEqual(label,'Beginning');
   proof.languages.push({language:lang,label});await page.screenshot({path:out+'/'+lang+'.png'});
  }
  assert.deepEqual(errors,[]);proof.passed=true;
 }finally{await browser.close();fs.writeFileSync(out+'/result.json',JSON.stringify({...proof,errors},null,2))}
 console.log('Packaged full history, replay, bounded scrolling and eight language layouts passed.');
})().catch(e=>{console.error(e);process.exitCode=1});
