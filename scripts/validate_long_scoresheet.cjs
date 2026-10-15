// Long navigation/replay acceptance on a disposable fixture, never production.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const ready=JSON.parse(fs.readFileSync('test-output/workflow-ready.json','utf8')),out='test-output/long-scoresheet';
assert(ready.long&&ready.folder.includes('test-output'));fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'}),errors=[],requests=[],proof={passed:false};
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1000}});page.on('pageerror',e=>errors.push(e.stack));
  page.on('request',r=>{if(r.url().includes('/moves?'))requests.push(new URL(r.url()).search)});
  await page.goto(ready.url);await page.waitForFunction(()=>moveSheet.latest>=622&&moveSheet.rows.length&&!moveSheet.busy);
  await page.evaluate(()=>{displayPrefs.panels.moves={visible:true,column:'right',height:570};displayPrefs.panels.focus={visible:true,column:'left',height:680};applyDisplay()});
  const scroll=page.locator('.scoresheet-scroll');
  const settled=()=>page.waitForFunction(()=>!moveSheet.busy&&!moveSheet.pending&&!moveSheet.scrollLock&&moveSheet.data?.after===moveSheet.after&&moveSheet.data?.span===moveSheet.span);
  const inspect=async()=>{
   await settled();const data=await page.evaluate(()=>({after:moveSheet.after,span:moveSheet.span,latest:moveSheet.latest,rows:[...document.querySelectorAll('.scoresheet tbody tr')].map(r=>Number(r.dataset.ply))}));
   assert(data.rows.length<=404);assert.deepEqual([...new Set(data.rows)].sort((a,b)=>a-b),data.rows);return data;
  };
  assert.equal((await inspect()).after,600);
  await page.locator('#movesBeginning').click();await page.waitForFunction(()=>moveSheet.after===0&&moveSheet.rows[0]?.ply===-3);await settled();
  assert.equal(await page.locator('.scoresheet tbody tr:first-child button span').textContent(),'1.');assert.equal(await scroll.evaluate(e=>e.scrollTop),0);
  assert(await page.locator('#movesEarlier').isDisabled());proof.beginningIncludesBook=true;
  await page.screenshot({path:out+'/beginning.png'});
  await page.locator('[data-move="-3"]').click();const review=await page.evaluate(()=>({fen:gameMovesView(selectedFocusGame()).fen,latest:moveSheet.latest}));
  await page.request.post(new URL('/fixture/step',ready.url).href);await page.waitForFunction(n=>moveSheet.latest>n,review.latest);
  assert.equal(await page.evaluate(()=>gameMovesView(selectedFocusGame()).fen),review.fen);assert.equal(await scroll.evaluate(e=>e.scrollTop),0);proof.liveUpdatesKeepHistory=true;
  await page.locator('#movesLatest').click();await page.waitForFunction(()=>moveSheet.follow&&!moveSheet.review&&moveSheet.after===600);await settled();
  assert(await scroll.evaluate(e=>e.scrollHeight-e.scrollTop-e.clientHeight<2));
  // Upward scrolling traverses boundaries automatically and retains the row at
  // the viewport edge while prepending older moves and dropping distant rows.
  const seen=new Set((await inspect()).rows);
  for(const expected of [400,200,0]){
   await scroll.evaluate(e=>{e.scrollTop=0});await page.waitForFunction(n=>moveSheet.after===n,expected);await settled();
   const data=await inspect();data.rows.forEach(n=>seen.add(n));assert(await scroll.evaluate(e=>e.scrollTop>0),'Earlier moves must be inserted above the current reading position');
  }
  await scroll.focus();await page.keyboard.press('Home');await settled();assert.equal(await scroll.evaluate(e=>e.scrollTop),0);assert.equal((await inspect()).after,0);
  // Downward scrolling can get all the way back, with at most 400 searched rows.
  for(const expected of [0,200,400]){
   const oldSpan=await page.evaluate(()=>moveSheet.span);await scroll.evaluate(e=>{e.scrollTop=e.scrollHeight});
   await page.waitForFunction(({expected,oldSpan})=>moveSheet.after===expected&&(expected!==0||moveSheet.span>oldSpan),{expected,oldSpan});await settled();
   (await inspect()).rows.forEach(n=>seen.add(n));
  }
  for(let ply=-3;ply<=623;ply++)assert(seen.has(ply),'Missing half-move '+ply);proof.continuousScrollBothDirections=true;proof.maximumRows=404;
  await page.screenshot({path:out+'/later-history.png'});
  // A navigation click during an in-flight read must not be lost or overwritten
  // by the older response.
  await page.locator('#movesLatest').click();await settled();
  let release,held=false;const gate=new Promise(resolve=>{release=resolve});
  await page.route('**/api/games/*/moves?*',async route=>{const response=await route.fetch();if(!held){held=true;await gate}await route.fulfill({response})});
  await page.locator('#movesEarlier').click();await page.waitForFunction(()=>moveSheet.busy);
  await page.locator('#movesBeginning').click();release();await page.waitForFunction(()=>moveSheet.after===0&&moveSheet.rows[0]?.ply===-3&&!moveSheet.busy);await settled();
  await page.unroute('**/api/games/*/moves?*');assert.equal(await scroll.evaluate(e=>e.scrollTop),0);proof.pendingReadNavigation=true;
  // Returning live resumes scrolling and updates the latest board.
  await page.locator('#movesLatest').click();await settled();
  await page.request.post(new URL('/fixture/step',ready.url).href);await page.waitForFunction(()=>moveSheet.latest===624);await settled();
  assert(await scroll.evaluate(e=>e.scrollHeight-e.scrollTop-e.clientHeight<2));
  await page.request.post(new URL('/fixture/step?count=177',ready.url).href);await page.waitForFunction(()=>moveSheet.latest===801&&moveSheet.rows.at(-1)?.ply===801);await settled();
  assert(await page.evaluate(()=>moveSheet.follow));assert(await scroll.evaluate(e=>e.scrollHeight-e.scrollTop-e.clientHeight<2));proof.followAcrossPageBoundary=true;
  const finalFen=await page.evaluate(()=>state.live[0].fen);await page.locator('#movesBeginning').click();await settled();
  await page.request.post(new URL('/fixture/finish',ready.url).href);await page.waitForFunction(()=>!state.live.length&&moveSheet.data?.attempt?.ended);await settled();
  assert.equal(await page.evaluate(()=>selectedFocusGame().fen),finalFen,'Browsing an earlier page must not overwrite the saved final board');proof.completedBoardPreserved=true;
  const kept=await page.evaluate(()=>{displayPrefs.followNextGame=true;const g=selectedFocusGame();state.live=[{...g,game:'another-live-game'}];renderFocus();const stayed=focusId===g.game;state.live=[];return stayed});assert(kept);proof.historyPinsFinishedGame=true;
  await page.locator('[data-move="-3"]').click();await page.locator('#movesLatest').click();await settled();
  await page.waitForFunction(fen=>gameMovesView(selectedFocusGame()).fen===fen,finalFen);proof.finalPositionRestored=true;
  await page.setViewportSize({width:1050,height:800});await page.evaluate(()=>{displayPrefs.fontSize=18;displayPrefs.panels.moves={visible:true,column:'right',height:420};applyDisplay()});
  await page.screenshot({path:out+'/narrow-large-text.png'});
  assert.equal(await page.locator('.moves-toolbar').evaluate(e=>e.scrollWidth>e.clientWidth+1),false);
  assert(requests.every(s=>Number(new URLSearchParams(s).get('limit'))<=400));assert.deepEqual(errors,[]);proof.passed=true;proof.requests=requests.length;
 }finally{await browser.close();fs.writeFileSync(out+'/result.json',JSON.stringify({...proof,errors},null,2))}
 console.log('Long scoresheet beginning, continuous scrolling, live/replay, request races and bounded rendering passed.');
})().catch(e=>{console.error(e);process.exitCode=1});
