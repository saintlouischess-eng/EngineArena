const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const out='test-output/rating-search-1106',ready=JSON.parse(fs.readFileSync(out+'/ready.json'));
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--disable-gpu']}),errors=[];
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1050}});page.on('pageerror',e=>errors.push(e.message));
  await page.goto(ready.url);await page.waitForFunction(()=>document.querySelector('#tournamentPicker')?.options.length>1);
  await page.selectOption('#tournamentPicker',ready.tid);await page.waitForFunction(tid=>state.snapshot?.id===tid,ready.tid);
  await page.locator('[data-view=ratingCenter]').click();await page.waitForFunction(()=>RatingDesk.data?.total===6);
  await page.locator('#rcAuto').uncheck();const baseline=await page.evaluate(()=>structuredClone(RatingDesk.data.items));
  const expected=baseline.filter(r=>r.name.startsWith('Rebel')||r.name.startsWith('Chess System Tal'));
  await page.locator('#rcSearch').fill('Rebel; Chess System Tal');await page.waitForFunction(()=>RatingDesk.data?.total===4);
  assert.deepEqual(await page.evaluate(()=>RatingDesk.data.items),expected);
  assert.equal(await page.locator('[data-rc-remove-search]').count(),2);
  const text=await page.evaluate(()=>rcFetchText());assert(text.includes('Rebel 14')&&text.includes('Chess System Tal Assassin')&&!text.includes('Stockfish 19'));
  await page.screenshot({path:out+`/${ready.mode}-search.png`,animations:'disabled'});
  await page.locator('#rcSearch').fill('Rebel, Chess System Tal; Stockfish');await page.waitForFunction(()=>RatingDesk.data?.total===5);
  await page.locator('[data-rc-remove-search="0"]').click();await page.waitForFunction(()=>RatingDesk.data?.total===3);
  assert.equal(await page.locator('#rcSearch').inputValue(),'Chess System Tal; Stockfish');
  await page.locator('#rcSearch').fill('Missing; No such engine');await page.waitForFunction(()=>RatingDesk.data?.total===0);
  assert.equal(await page.locator('#rcRows h3').textContent(),'No engines match this search');
  await page.locator('#rcEmptyClearSearch').click();await page.waitForFunction(()=>RatingDesk.data?.total===6);
  await page.locator('#rcSearch').fill('Rebel; Chess System Tal');await page.waitForFunction(()=>RatingDesk.data?.total===4);
  await page.selectOption('#rcVersions','best');await page.waitForFunction(()=>RatingDesk.data?.versions==='best');
  assert((await page.locator('#rcRows .rc-engine').allTextContents()).every(n=>n.startsWith('Rebel')||n.startsWith('Chess System Tal')));
  await page.selectOption('#rcCategory','all');await page.waitForFunction(()=>RatingDesk.data?.category==='all');
  assert.equal(await page.locator('#rcRows .rc-engine').count(),4);
  await page.setViewportSize({width:1050,height:900});await page.locator('#rcSearch').scrollIntoViewIfNeeded();
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:out+`/${ready.mode}-narrow.png`,animations:'disabled'});
  await page.locator('#rcClearSearch').click();await page.waitForFunction(()=>RatingDesk.data?.total===6);
  // Render a fixture FEN in the actual focused panel; no engines are launched.
  const setupFocus=async()=>page.evaluate(gid=>{
   view('overview');refreshGameMoves=()=>{};displayPrefs.focus3d=false;displayPrefs.followNextGame=false;
   focusId=gid;retainedTid=state.tid;
   retainedFocus={tid:state.tid,game:gid,number:0,fen:'1k6/8/8/8/8/8/8/R6K w - - 84 80',white:{name:'White'},black:{name:'Black'},status:'Reviewing',claim_draws:true,ended:1};
   revealFocusPanel('focus');renderFocus();
  },ready.gid);
  await setupFocus();const settings=await page.evaluate(()=>JSON.stringify(state.snapshot.settings));
  assert(await page.locator('#focusDrawRuleToggle').isChecked());assert(await page.locator('.focus-draw-rule').isVisible());
  await page.locator('#focusDrawRuleToggle').uncheck();await page.evaluate(()=>preferenceSave);
  assert(!(await page.locator('.focus-draw-rule').isVisible()));
  await page.locator('#focusLayoutButton').click();assert(!(await page.locator('#focusDrawRule').isChecked()));
  await page.locator('#focusDrawRule').check();await page.locator('#saveFocusLayout').click();await page.waitForFunction(()=>!document.querySelector('#modal').open);
  assert(await page.locator('#focusDrawRuleToggle').isChecked());assert(await page.locator('.focus-draw-rule').isVisible());
  await page.locator('#focusDrawRuleToggle').uncheck();await page.evaluate(()=>preferenceSave);
  await page.reload();await page.waitForFunction(()=>state.snapshot&&displayPrefs.showDrawRule===false);await setupFocus();
  assert(!(await page.locator('#focusDrawRuleToggle').isChecked()));assert(!(await page.locator('.focus-draw-rule').isVisible()));
  await page.locator('#focusDrawRuleToggle').check();await page.evaluate(()=>preferenceSave);
  assert.match(await page.locator('.focus-draw-rule').textContent(),/84 \/ 100.*16/);
  await page.evaluate(()=>{retainedFocus.claim_draws=false;renderFocus()});assert.match(await page.locator('.focus-draw-rule').textContent(),/84 \/ 150.*66/);
  assert.equal(await page.evaluate(()=>JSON.stringify(state.snapshot.settings)),settings);
  await page.locator('.focus-watching').scrollIntoViewIfNeeded();await page.screenshot({path:out+`/${ready.mode}-counter.png`,animations:'disabled'});
  await page.locator('#focusWinningOptions').click();assert.equal(await page.locator('#winningPawns').inputValue(),'2');
  assert(await page.locator('#winningMinimum').isDisabled());
  await page.selectOption('#winningStay','fade');assert(!(await page.locator('#winningMinimum').isDisabled()));
  await page.locator('#winningMinimum').fill('45');await page.locator('#winningFade').fill('20');
  await page.locator('#winningPawns').fill('3');await page.locator('#winningConfirm').fill('0');await page.locator('#winningEnabled').check();
  await page.screenshot({path:out+`/${ready.mode}-winning-options.png`,animations:'disabled'});
  await page.locator('#saveWinningWatch').click();await page.waitForFunction(()=>!document.querySelector('#modal').open);
  assert(await page.locator('#focusWinningWatch').isChecked());assert(await page.locator('#focusNextWinning').isVisible());
  assert.deepEqual(await page.evaluate(()=>displayPrefs.winningWatch),{enabled:true,pawns:3,confirm:0,stay:'fade',minimum:45,fade:20});
  // Drive the real button with two synthetic telemetry records in this isolated UI.
  const switched=await page.evaluate(()=>{
   focusDirector.reset(state.tid);focusId='';retainedFocus=null;
   state.live=[{tid:state.tid,game:'watch-a',attempt:'aa',number:1,fen:'1k6/8/8/8/8/8/8/R6K w - - 84 80',ply:20,info:{cp:400},info_side:'white',white:{name:'White'},black:{name:'Black'},searches:{},clock_active:'white'},
    {tid:state.tid,game:'watch-b',attempt:'bb',number:2,fen:'1k6/8/8/8/8/8/8/R6K w - - 84 80',ply:20,info:{cp:-500},info_side:'black',white:{name:'White'},black:{name:'Black'},searches:{},clock_active:'black'}];
   renderFocus();const first=focusId;$('#focusNextWinning').click();const second=focusId;
   state.live=[];retainedFocus=null;focusId='';return {first,second};
  });assert.deepEqual(switched,{first:'watch-b',second:'watch-a'});
  await page.reload();await page.waitForFunction(()=>state.snapshot&&displayPrefs.winningWatch?.pawns===3);
  await setupFocus();assert(await page.locator('#focusWinningWatch').isChecked());
  await page.locator('#focusWinningWatch').uncheck();await page.evaluate(()=>preferenceSave);
  assert.equal(await page.evaluate(()=>displayPrefs.winningWatch.enabled),false);
  assert.deepEqual(errors,[]);
  fs.writeFileSync(out+`/${ready.mode}-ui.json`,JSON.stringify({passed:true,multiSearch:true,removeAndClear:true,exports:true,unchangedRatingsAndRanks:true,bestAndAllCategories:true,narrowLayout:true,counterSyncAndPersistence:true,gameRulesUnchanged:true,winningWatchOptionsAndPersistence:true,nextWinningGame:true,errors},null,2));
  console.log('Passed: multi-engine search, exports, unchanged ratings/ranks, counter controls, winning-watch options/persistence and Next winning game; zero JS errors.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
