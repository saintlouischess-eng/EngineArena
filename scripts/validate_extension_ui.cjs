const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),out=process.argv[3];fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--use-angle=swiftshader']});
 const page=await browser.newPage({viewport:{width:1500,height:1050}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await page.goto(ready.url+'&lang='+lang);await page.waitForFunction(()=>typeof renderFocus==='function'&&state.snapshot);
   await page.locator('#tournamentPicker').selectOption(ready.rr);await page.waitForFunction(tid=>state.snapshot?.id===tid,ready.rr);
   await page.locator('#extendTournament').click();await page.waitForFunction(()=>document.querySelector('[data-add-engine]'));
   assert.ok((await page.locator('#dialogTitle').textContent()).length>4);
   if(lang!=='en')assert.notEqual(await page.locator('#dialogTitle').textContent(),'Extend round robin');
   await page.locator('#modal [data-close]').first().click();
   // Render the real focused panel; input FENs exercise threshold/reset/history display.
   await page.evaluate(gid=>{
    window.savedMoveRefresh=refreshGameMoves;refreshGameMoves=()=>{};
    displayPrefs.followNextGame=false;displayPrefs.showDrawRule=true;focusId=gid;
    retainedTid=state.tid;retainedFocus={tid:state.tid,game:gid,number:0,fen:'1k6/8/8/8/8/8/8/R6K w - - 84 80',white:{name:'Counter test — White'},black:{name:'Counter test — Black'},status:'Reviewing',claim_draws:true};
    revealFocusPanel('focus');renderFocus();
   },ready.gid);
   assert.match(await page.locator('.focus-draw-rule').textContent(),/84 \/ 100.*16/);
   await page.evaluate(()=>{retainedFocus.fen=retainedFocus.fen.replace('84 80','99 80');renderFocus()});
   assert.match(await page.locator('.focus-draw-rule').textContent(),/99 \/ 100.*1/);
   await page.evaluate(()=>{retainedFocus.claim_draws=false;renderFocus()});
   assert.match(await page.locator('.focus-draw-rule').textContent(),/99 \/ 150.*51/);
   await page.evaluate(()=>{retainedFocus.fen=retainedFocus.fen.replace('99 80','0 81');renderFocus()});
   assert.match(await page.locator('.focus-draw-rule').textContent(),/0 \/ 150.*150/);
  }
  await page.goto(ready.url+'&lang=en');await page.waitForFunction(()=>state.snapshot?.state==='completed');
  await page.locator('#tournamentPicker').selectOption(ready.rr);await page.waitForFunction(tid=>state.snapshot?.id===tid,ready.rr);
  await page.locator('#extendTournament').click();await page.waitForFunction(()=>document.querySelector('[data-add-engine="old-a"]'));
  assert.equal(await page.locator('[data-add-engine="old-a"]').isDisabled(),true);
  await page.locator('#extendNext').click();await page.waitForFunction(()=>document.querySelector('[data-add-engine="new-079"]'));
  await page.locator('[data-add-engine="new-079"]').check();
  await page.locator('#extendSearch').fill('Candidate 080');await page.waitForFunction(()=>document.querySelectorAll('[data-add-engine]').length===1);
  await page.locator('[data-add-engine="new-080"]').check();
  assert.match(await page.locator('#extendSelected').textContent(),/^2 /);
  await page.locator('#extendCheck').click();await page.waitForFunction(()=>!document.querySelector('#extendSave').disabled);
  assert.match(await page.locator('#extendPreview').textContent(),/10 additional games · 12 total scheduled/);
  for(const width of [1500,1100])for(const light of [false,true]){
   await page.setViewportSize({width,height:1000});await page.evaluate(v=>document.body.classList.toggle('light',v),light);
   assert.ok(await page.locator('#modal').evaluate(el=>el.scrollWidth<=el.clientWidth+2));
   await page.screenshot({path:`${out}/preview-${width}-${light?'light':'dark'}.png`});
  }
  await page.locator('#extendSave').click();await page.waitForFunction(()=>!document.querySelector('#modal').open&&state.snapshot?.total===12);
  assert.equal(await page.evaluate(()=>state.snapshot.state),'paused');
  assert.equal(await page.evaluate(()=>state.snapshot.official_games),2);
  assert.equal(await page.locator('#extendTournament').isDisabled(),true);
  assert.match(await page.locator('#notice').textContent(),/saved paused/);
  await page.evaluate(gid=>{
   refreshGameMoves=()=>{};displayPrefs.followNextGame=false;focusId=gid;retainedTid=state.tid;
   retainedFocus={tid:state.tid,game:gid,number:0,fen:'1k6/8/8/8/8/8/8/R6K w - - 84 80',white:{name:'White'},black:{name:'Black'},status:'Reviewing',claim_draws:true};
   revealFocusPanel('focus');renderFocus();
  },ready.gid);
  await page.locator('#focusLayoutButton').click();assert.equal(await page.locator('#focusDrawRule').isChecked(),true);
  await page.locator('#focusDrawRule').uncheck();await page.locator('#saveFocusLayout').click();await page.waitForFunction(()=>!document.querySelector('#modal').open);
  assert.equal(await page.locator('.focus-draw-rule').isVisible(),false);
  const prefs=await page.evaluate(()=>api('preferences'));assert.equal(prefs.showDrawRule,false);
  await page.locator('#focusLayoutButton').click();await page.locator('#focusDrawRule').check();await page.locator('#saveFocusLayout').click();await page.waitForFunction(()=>!document.querySelector('#modal').open);
  assert.equal(await page.locator('.focus-draw-rule').isVisible(),true);
  await page.screenshot({path:`${out}/focus-counter.png`});
  assert.deepEqual(errors,[]);const result={passed:true,languages:8,pagination:true,search:true,selection_across_pages:true,preview:true,paused_save:true,draw_counter:true,persisted_toggle:true,errors};
  fs.writeFileSync(out+'/result.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
