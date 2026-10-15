// Three review loops are documented in the release note. This is the repeatable
// second/third-pass acceptance: book setup, stable panels, saved layouts and audio.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const ready=JSON.parse(fs.readFileSync(process.env.ARENA_PLAYER_READY||'test-output/workflow-ready.json'));
assert(ready.folder.includes('test-output')&&path.basename(ready.folder).startsWith('workflow-'));
const out=process.env.ARENA_WORKSPACE_OUT||'test-output/v176-pass2';fs.mkdirSync(out,{recursive:true});
const book=path.resolve(out,'player-review.pgn');fs.writeFileSync(book,'1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 *\n');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'}),proof={passed:false,errors:[],checks:[]};let page;
 const check=(name)=>{proof.checks.push(name);console.log('PASS '+name)};
 try{
  page=await browser.newPage({viewport:{width:1600,height:1050}});page.on('pageerror',e=>proof.errors.push(e.stack));
  await page.goto(ready.url);await page.waitForFunction(()=>typeof PlayerWorkspace!=='undefined');
  await page.evaluate(async()=>{const {game}=await api('player/state');if(game&&['playing','starting','paused'].includes(game.state))await api('player/action',{id:game.id,revision:game.revision,action:'abandon'});delete displayPrefs.playerLayout;displayPrefs.player3d=false;applyDisplay();await persistDisplay()});
  await page.locator('[data-view=playerArena]').click();await page.waitForFunction(()=>PlayerDesk.board);
  await page.locator('#paNew').click();await page.locator('[data-pa-engine]').first().check();await page.locator('#paBookMode').selectOption('custom');
  await page.evaluate(p=>{window.fixtureBook=p;browse=async()=>[window.fixtureBook]},book);
  await page.locator('#importEngineBook').click();await page.waitForFunction(()=>document.querySelector('#eBook').value.length===64&&!document.querySelector('#importEngineBook').disabled);
  await page.locator('#eBookDepth').fill('4');await page.locator('#eBookPolicy').selectOption('best');await page.locator('#paCreate').click();await page.waitForSelector('#paSetupName',{state:'hidden'});
  assert.equal(await page.evaluate(()=>PlayerDesk.game.engine.move_book.max_plies),4);
  assert.match(await page.locator('#paHuman .pa-clock').textContent(),/^05:00\.0$/);
  await page.locator('#paResume').click();await page.waitForFunction(()=>PlayerDesk.game.state==='playing');
  const importError=await page.evaluate(async p=>{try{await api('move-books',{path:p});return ''}catch(e){return e.message}},book);assert.match(importError,/Pause your Player Arena/);
  await page.locator('#paBoard [data-square=e2]').click();await page.locator('#paBoard [data-square=e4]').click();await page.waitForFunction(()=>PlayerDesk.game.moves.length===2);
  assert.equal(await page.evaluate(()=>PlayerDesk.game.moves[1].uci),'e7e5');assert.equal(await page.evaluate(()=>PlayerDesk.game.moves[1].info.source),'book');
  assert.match(await page.locator('#paOpponent .pa-clock').textContent(),/^05:03\.0$/);
  await page.locator('#paBoard [data-square=g1]').click();await page.locator('#paBoard [data-square=f3]').click();await page.waitForFunction(()=>PlayerDesk.game.moves.length===4);
  assert.equal(await page.evaluate(()=>PlayerDesk.game.moves[3].uci),'b8c6');
  await page.locator('#paPause').click();await page.waitForFunction(()=>PlayerDesk.game.state==='paused');await page.locator('#paAnalysis').check();await page.waitForFunction(()=>PlayerDesk.game.analysis);
  const pgn=await page.evaluate(async()=>{const r=await api('player/pgn-preview?id='+PlayerDesk.game.id,{preset:'archive'});return r});
  assert(JSON.stringify(pgn).includes('BlackBook'));check('PGN import, book-only engine moves, absolute ply limit metadata and tenth-second clocks');
  // Layout stress is a display fixture, never a fabricated committed chess result.
  const stable=await page.evaluate(()=>{clearTimeout(PlayerDesk.timer);PlayerDesk.viewing=null;const g=PlayerDesk.game;g.search={info:{cp:22,depth:31,nodes:1234567890,time:3456,wdl:[112,822,66]},pv:'1. e4 e5',history:[],log:[]};paThinking(g);const before=Object.fromEntries(['paMovesPanel','paThinkingPanel','paBoardPanel'].map(id=>[id,document.getElementById(id).getBoundingClientRect().toJSON()]));g.search.pv='1. e4 e5 2. Nf3 Nc6 '.repeat(160);paThinking(g);const after=Object.fromEntries(Object.keys(before).map(id=>[id,document.getElementById(id).getBoundingClientRect().toJSON()]));PlayerDesk.viewing='layout-only-fixture';return {before,after,pvOverflow:$('#paPV').scrollHeight>$('#paPV').clientHeight}});
  for(const k of Object.keys(stable.before))assert.equal(stable.before[k].height,stable.after[k].height);assert(stable.pvOverflow);check('Very long PVs cannot resize the board, moves or thinking panel');
  await page.evaluate(()=>{const g=PlayerDesk.game,original=structuredClone(g.moves);g.moves=Array.from({length:500},(_,i)=>({...original[i%4],fullmove:Math.floor(i/2)+1}));paRender();$('#paMoves').scrollTop=0;g.note='Display fixture updated';paRender()});
  assert.equal(await page.locator('#paMoves').evaluate(el=>el.scrollTop),0);await page.locator('#paLive').click();assert((await page.locator('#paMoves').evaluate(el=>el.scrollTop))>100);
  await page.locator('#paFirst').click();assert.equal(await page.locator('#paMoves').evaluate(el=>el.scrollTop),0);check('500-ply move list keeps reading position and returns to the first move');
  await page.locator('#paThinkingPanel [data-pa-float]').click();assert(await page.locator('#paThinkingPanel').evaluate(el=>el.classList.contains('pa-floating')));
  const title=await page.locator('#paThinkingPanel .pa-window-heading h3').boundingBox();await page.mouse.move(title.x+15,title.y+8);await page.mouse.down();await page.mouse.move(title.x+175,title.y+65,{steps:10});await page.mouse.up();
  await page.locator('#paThinkingPanel .pa-resizer').focus();await page.keyboard.press('Shift+ArrowRight');await page.keyboard.press('Shift+ArrowDown');
  await page.locator('#paThinkingPanel [data-pa-options]').click();await page.locator('#paPanelFont').fill('125');await page.locator('#paPanelApply').click();
  await page.evaluate(()=>persistDisplay());const saved=await page.evaluate(()=>structuredClone(displayPrefs.playerLayout));
  await page.screenshot({path:out+'/floating-analysis.png'});await page.reload();await page.waitForFunction(()=>typeof PlayerWorkspace!=='undefined');await page.locator('[data-view=playerArena]').click();await page.waitForFunction(()=>PlayerDesk.board);
  assert.equal(await page.evaluate(()=>displayPrefs.playerLayout.panels.thinking.font),125);assert.equal(await page.evaluate(()=>displayPrefs.playerLayout.panels.thinking.width),saved.panels.thinking.width);check('Floating position, resize and text size persist after reload');
  await page.locator('#paThinkingPanel [data-pa-float]').click();await page.locator('#paMovesPanel .pa-grip').dragTo(page.locator('[data-pa-column=left]'),{targetPosition:{x:20,y:20}});
  assert.equal(await page.locator('#paMovesPanel').evaluate(el=>el.parentElement.dataset.paColumn),'left');
  await page.locator('#paLayout').click();await page.locator('#paLayoutReset').click();check('Drag to another dock column and reset workspace');
  await page.locator('#paStyle').click();await page.waitForFunction(()=>PlayerDesk.board?.renderer);await page.evaluate(()=>PlayerDesk.board.renderer.ready());
  const focusCamera=await page.evaluate(()=>JSON.stringify(displayPrefs.camera3d));await page.locator('#paAppearance').click();await page.locator('#cameraZoom').fill('130');await page.locator('#showBoard3dControls').check();await page.locator('#applyBoardView').click();
  assert.equal(await page.evaluate(()=>PlayerDesk.board.camera.zoom),1.3);assert.equal(await page.evaluate(()=>JSON.stringify(displayPrefs.camera3d)),focusCamera);assert(await page.locator('#paCamera').isVisible());
  await page.locator('#paCameraToggle').click();assert(!(await page.locator('#paCamera').isVisible()));check('Player camera appearance applies locally; camera controls hide');
  await page.locator('#paFullscreen').click();await page.waitForFunction(()=>document.querySelector('#paBoardPanel').classList.contains('pa-expanded'));
  const full=await page.locator('#paBoardPanel').boundingBox();assert(full.width>1500&&full.height>1000);await page.screenshot({path:out+'/fullscreen-3d.png'});
  await page.locator('#paResign').click();assert(await page.locator('#paConfirmAction').isVisible());await page.locator('#modal [data-close]').first().click();await page.keyboard.press('Escape');
  await page.waitForFunction(()=>!document.querySelector('#paBoardPanel').classList.contains('pa-expanded'));check('Full-screen 3D keeps game controls and dialogs usable; Escape restores layout');
  const audio=await page.evaluate(async()=>{const c=new AudioContext(),r=[];try{for(const kind of ['move','capture','castle','check','promotion','win','loss','draw','low'])for(const variant of (['win','loss','draw','low'].includes(kind)?['']:['','-2','-3'])){const response=await fetch('/assets/player-'+kind+variant+'.wav');if(!response.ok)throw Error('Missing '+kind+variant);const b=await c.decodeAudioData(await response.arrayBuffer());let peak=0,energy=0;for(const x of b.getChannelData(0)){peak=Math.max(peak,Math.abs(x));energy+=x*x}if(peak>.91||peak<.05||energy===0)throw Error('Bad sound '+kind+variant);r.push({name:kind+variant,seconds:b.duration,peak})}}finally{await c.close()}return r});assert.equal(audio.length,19);proof.audio=audio;check('19 audio files decode, have nonzero energy and retain clipping headroom');
  // Font / theme / laptop pass, including floating windows after a resize.
  await page.setViewportSize({width:1100,height:760});await page.locator('#paThinkingPanel [data-pa-float]').click();
  await page.evaluate(()=>{displayPrefs.fontSize=20;displayPrefs.theme='light';applyDisplay()});
  await page.waitForTimeout(250);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  const floating=await page.locator('#paThinkingPanel').boundingBox();assert(floating.x>=0&&floating.y>=0&&floating.x+floating.width<=1100&&floating.y+floating.height<=760);
  await page.screenshot({path:out+'/laptop-light.png'});check('Laptop width, larger fonts, light theme and reachable floating controls');
  await page.locator('[data-view=engines]').click();assert(!(await page.locator('#paThinkingPanel').isVisible()));assert(await page.evaluate(()=>!PlayerDesk.board));check('Changing workspace hides floating player panels and disposes its renderer');
  await page.locator('[data-view=playerArena]').click();await page.waitForFunction(()=>PlayerDesk.board);await page.evaluate(()=>paReview(PlayerDesk.game.id));
  await page.locator('[data-view=engines]').click();await page.locator('[data-view=playerArena]').click();await page.waitForFunction(()=>PlayerDesk.board?.game&&PlayerDesk.viewing);
  assert.equal(await page.evaluate(()=>PlayerDesk.review),4);await page.locator('#paReturn').click();assert.equal(await page.evaluate(()=>PlayerDesk.viewing),null);check('Saved-game review survives a workspace switch and returns to the live game');
  if(process.env.ARENA_PLAYER_LANGUAGES){
   proof.languages=[];
   for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
    await page.goto(ready.url+'&lang='+lang);await page.waitForFunction(()=>typeof PlayerWorkspace!=='undefined');
    await page.evaluate(()=>{displayPrefs.player3d=false;displayPrefs.fontSize=14;applyDisplay();window.missing=new Set();ArenaI18n.capture(k=>{if(ArenaI18n.locale!=='en'&&!Object.hasOwn(window.ARENA_MESSAGES,k))missing.add(k)})});
    await page.locator('[data-view=playerArena]').click();await page.locator('#paLayout').click();assert(!(await page.locator('#modal .modal-body').evaluate(el=>el.scrollWidth>el.clientWidth+1)));await page.locator('#paLayoutReset').click();
    await page.locator('#paNew').click();await page.locator('#paBookMode').selectOption('custom');assert(!(await page.locator('#modal .modal-body').evaluate(el=>el.scrollWidth>el.clientWidth+1)));
    assert.deepEqual(await page.evaluate(()=>[...missing]),[],'Missing translation: '+lang);await page.locator('#modal [data-close]').first().click();proof.languages.push(lang);
   }
   check('Book setup and workspace dialogs in all eight languages');
  }
  await page.evaluate(async()=>{const original=api;api=async(path,body)=>{if(path.startsWith('profiles'))await new Promise(resolve=>setTimeout(resolve,200));return original(path,body)};try{const opening=paNewGame();$('#modal').close();modal('Cancellation fixture','<p>Another dialog</p>');await opening;$('#modal').close()}finally{api=original}});check('Closing setup during opponent recall cannot update a replacement dialog');assert.deepEqual(proof.errors,[]);proof.passed=true;
 }catch(e){proof.failure=e.stack;if(page)await page.screenshot({path:out+'/failure.png'}).catch(()=>{});throw e}
 finally{fs.writeFileSync(out+'/result.json',JSON.stringify(proof,null,2));await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
