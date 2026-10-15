// Read/write acceptance against an explicitly disposable fixture, software GPU only.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const ready=JSON.parse(fs.readFileSync(process.argv[2]||'test-output/tournament-edit-ready.json','utf8'));
assert(path.resolve(ready.folder).startsWith(path.resolve('test-output')+path.sep));
const out=process.argv[3]||'test-output/room-library-source';fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']}),proof={passed:false,errors:[]};let page;
 try{
  page=await browser.newPage({viewport:{width:1366,height:900}});page.setDefaultTimeout(90000);page.on('pageerror',e=>proof.errors.push(e.message));
  await page.goto(ready.url+'&lang=en');await page.waitForFunction(()=>state.snapshot&&queueData);
  const open=async()=>{await page.locator('#newTournament').click();await page.waitForSelector('#setupEngineRows tr');await page.waitForFunction(()=>$('#tname')?.dataset.setupLoading!=='true')};
  const saved=async()=>{await page.waitForFunction(()=>$('#setupDraftStatus')?.textContent==='Draft saved — safe to close')};
  const close=async()=>{await page.keyboard.press('Escape');await page.waitForFunction(()=>!$('#modal').open)};
  await page.evaluate(async()=>{state.selected=new Set(['0','1','2']);$('#allProfiles').checked=false;await newTournament(null,true)});
  await page.locator('#tformat').selectOption('gauntlet');await page.locator('[data-candidate="2"]').check();await page.locator('#tname').fill('Retain these conditions');await page.locator('#ttolerance').fill('1');await saved();await close();
  await page.reload();await page.waitForFunction(()=>state.snapshot&&queueData);await page.evaluate(()=>view('engines'));
  await page.locator('[data-engine="3"]').check();await page.locator('[data-engine="4"]').check();await open();
  assert.deepEqual(await page.evaluate(()=>[...state.selected]),['3','4']);assert.equal(await page.locator('#tname').inputValue(),'Retain these conditions');assert.equal(await page.locator('#ttolerance').inputValue(),'1');assert.equal(await page.locator('[data-candidate]:checked').count(),0);await saved();await close();
  await page.reload();await page.waitForFunction(()=>state.snapshot&&queueData);await open();assert.deepEqual(await page.evaluate(()=>[...state.selected]),['3','4']);proof.librarySelectionSurvivesDraftAndRestart=true;
  await page.locator('#setupLibrary').click();await page.locator('[data-engine="4"]').uncheck();await page.locator('[data-engine="2"]').check();await open();assert.deepEqual(await page.evaluate(()=>[...state.selected]),['3','2']);await saved();await close();
  await page.reload();await page.waitForFunction(()=>state.snapshot&&queueData);await page.evaluate(()=>view('engines'));await page.locator('#bulkClearSelection').click();await open();assert.equal(await page.evaluate(()=>state.selected.size),0);await saved();await close();proof.explicitClearOverridesDraft=true;
  await page.evaluate(()=>view('engines'));await page.locator('#allProfiles').check();await open();assert.equal(await page.evaluate(()=>tournamentParticipantCount()),5);await saved();await close();
  await page.reload();await page.waitForFunction(()=>state.snapshot&&queueData);await open();assert.equal(await page.evaluate(()=>tournamentParticipantCount()),5);await page.locator('#tformat').selectOption('round_robin');await page.locator('#tname').fill('Library handoff verification');await saved();await page.waitForFunction(()=>!$('#createTournament').disabled);await page.locator('#createTournament').click();await page.waitForFunction(()=>!$('#modal').open&&state.snapshot?.name==='Library handoff verification');
  assert.equal(await page.evaluate(()=>state.snapshot.participants),5);proof.allLibraryAndSavedTournament=true;
  // Keep recorded snapshots while deleting every matching disposable profile.
  const before=await page.evaluate(async()=>api('selected-participants',{recorded_participants:state.tid}));
  await page.evaluate(async()=>{const p=(await api('profiles?limit=1')).items[0];await api('profiles/import',{profiles:Array.from({length:121},(_,i)=>({...p,id:'review-'+String(i).padStart(3,'0'),name:'Review engine '+String(i).padStart(3,'0')}))});state.selected.clear();$('#allProfiles').checked=false;view('engines')});
  await page.locator('#engineSearch').fill('Review engine');await page.waitForFunction(()=>state.engineTotal===121);await page.locator('[data-engine="review-000"]').check();await page.locator('#engNext').click();await page.waitForFunction(()=>state.engOffset===50);await page.locator('[data-engine="review-050"]').check();
  assert.equal(await page.locator('#deleteEngines').innerText(),'Delete selected (2)…');await page.locator('#deleteEngines').click();await page.locator('#keepEngineProfiles').click();assert.equal(await page.evaluate(()=>state.engineTotal),121);assert.equal(await page.evaluate(()=>state.selected.size),2);
  await page.locator('#deleteEngines').click();await page.locator('#confirmDeleteEngines').click();await page.waitForFunction(()=>state.engineTotal===119);assert.equal(await page.evaluate(()=>state.engOffset),50);assert.equal(await page.locator('#engineSearch').inputValue(),'Review engine');assert.equal(await page.evaluate(()=>state.selected.size),0);proof.crossPageBulkAndCancel=true;
  await page.locator('#engNext').click();await page.waitForFunction(()=>state.engOffset===100&&$('#engineTable [data-engine]')?.dataset.engine==='review-102');await page.locator('[data-delete-engine="review-112"]').scrollIntoViewIfNeeded();
  const scroll=await page.evaluate(()=>window.scrollY);await page.locator('[data-delete-engine="review-112"]').click();await page.locator('#confirmDeleteEngines').click();await page.waitForFunction(()=>state.engineTotal===118);await page.waitForTimeout(150);
  assert.equal(await page.evaluate(()=>state.engOffset),100);assert(Math.abs((await page.evaluate(()=>window.scrollY))-scroll)<100);proof.singleDeletePreservesPageAndScroll=true;
  assert.equal(await page.locator('.engine-selection-bar').evaluate(e=>Math.round(e.getBoundingClientRect().top)),0);proof.bulkActionsRemainVisibleWhileScrolling=true;await page.screenshot({path:out+'/library-selection.png'});
  await page.evaluate(()=>{for(const e of $$('[data-engine]'))if(!e.checked){e.checked=true;e.dispatchEvent(new Event('change',{bubbles:true}))}});await page.locator('#deleteEngines').click();await page.locator('#confirmDeleteEngines').click();await page.waitForFunction(()=>state.engineTotal===100&&state.engOffset===50);proof.emptyLastPageClamps=true;
  await page.locator('#bulkSelectAll').click();await page.locator('#deleteEngines').click();await page.locator('#confirmDeleteEngines').click();await page.waitForFunction(()=>state.engineTotal===0&&state.engOffset===0);assert.equal(await page.locator('#engineSearch').inputValue(),'Review engine');
  await page.locator('#engineSearch').fill('');await page.waitForFunction(()=>state.engineTotal===5);await page.locator('#bulkSelectAll').click();await page.locator('#deleteEngines').click();await page.locator('#confirmDeleteEngines').click();await page.waitForFunction(()=>state.libraryTotal===0&&state.engOffset===0);
  assert.deepEqual(await page.evaluate(async()=>api('selected-participants',{recorded_participants:state.tid})),before);proof.emptyLibraryAndSnapshots=true;
  // Live room: real character elapsed time responds to independent motion choice.
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.evaluate(async()=>{displayPrefs.scene3d={environment:'live-club',live:true,people:true,backgroundGames:true,atmosphere:true,roomMotion:'system',quality:'low',fps:60};await paShow();PlayerDesk.board.setMode('3d')});
  await page.locator('#paBoard').scrollIntoViewIfNeeded();await page.waitForFunction(()=>Number(PlayerDesk.board?.canvas?.dataset.roomPeople)>=4);
  assert.equal(await page.evaluate(()=>PlayerDesk.board.args[9].fps),30);
  let t=await page.evaluate(()=>PlayerDesk.board.canvas.dataset.roomSeconds);let wall=await page.evaluate(()=>PlayerDesk.board.canvas.dataset.roomLocalTime);
  await page.waitForFunction(old=>PlayerDesk.board.canvas.dataset.roomLocalTime!==old,wall);assert.equal(await page.evaluate(()=>PlayerDesk.board.canvas.dataset.roomSeconds),t);assert.match(await page.locator('#paBoardPanel .room-motion-status').innerText(),/paused by Windows/);
  await page.evaluate(()=>boardViewDialog({player:true}));assert.deepEqual(await page.locator('#sceneFps option').evaluateAll(es=>es.map(e=>e.value)),['15','30']);await page.locator('#sceneRoomMotion').selectOption('animate');await page.locator('#applyBoardView').click();
  await page.waitForFunction(old=>Number(PlayerDesk.board.canvas.dataset.roomSeconds)>Number(old)+.15,t);assert.equal(await page.evaluate(()=>matchMedia('(prefers-reduced-motion: reduce)').matches),true);assert.equal(await page.locator('#paBoardPanel .room-motion-status').isVisible(),false);proof.overrideAnimatesActualRoom=true;
  await page.evaluate(()=>boardViewDialog({player:true}));await page.locator('#sceneRoomMotion').selectOption('still');await page.locator('#applyBoardView').click();await page.waitForTimeout(500);t=await page.evaluate(()=>PlayerDesk.board.canvas.dataset.roomSeconds);await page.waitForTimeout(1300);assert.equal(await page.evaluate(()=>PlayerDesk.board.canvas.dataset.roomSeconds),t);proof.explicitStill=true;
  await page.evaluate(()=>boardViewDialog({player:true}));await page.locator('#sceneRoomMotion').selectOption('system');await page.locator('#applyBoardView').click();await page.emulateMedia({reducedMotion:'no-preference'});await page.waitForFunction(old=>Number(PlayerDesk.board.canvas.dataset.roomSeconds)>Number(old)+.15,t);proof.windowsChangeResumes=true;
  await page.evaluate(async()=>{displayPrefs.scene3d.roomMotion='animate';await persistDisplay();view('engines')});await page.reload();await page.waitForFunction(()=>state.snapshot&&queueData);assert.equal(await page.evaluate(()=>displayPrefs.scene3d.roomMotion),'animate');proof.motionPreferencePersists=true;
  proof.languages=[];
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await page.goto(ready.url+'&lang='+lang);await page.waitForFunction(()=>state.snapshot&&queueData);await page.evaluate(()=>{window.missing=new Set();ArenaI18n.capture(k=>{if(ArenaI18n.locale!=='en'&&!Object.hasOwn(window.ARENA_MESSAGES,k))missing.add(k)});boardViewDialog()});
   assert.deepEqual(await page.locator('#sceneFps option').evaluateAll(es=>es.map(e=>e.value)),['15','30']);assert.deepEqual(await page.evaluate(()=>[...missing]),[]);assert.equal(await page.locator('#modal .modal-body').evaluate(e=>e.scrollWidth>e.clientWidth+1),false);proof.languages.push(lang);await close();
  }
  assert.deepEqual(proof.errors,[]);proof.passed=true;
 }finally{if(page&&!proof.passed)await page.screenshot({path:out+'/failure.png'}).catch(()=>{});await browser.close();fs.writeFileSync(out+'/result.json',JSON.stringify(proof,null,2))}
 console.log(JSON.stringify(proof,null,2));
})().catch(e=>{console.error(e);process.exitCode=1});
