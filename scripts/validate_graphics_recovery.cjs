// Simulate WebGL loss in a software-rendered, disposable browser, never the owner's GPU.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const ready=JSON.parse(fs.readFileSync(process.env.ARENA_GRAPHICS_READY||'test-output/workflow-ready.json'));
assert(path.resolve(ready.folder).startsWith(path.resolve('test-output')+path.sep));
const out=process.env.ARENA_GRAPHICS_OUT||'test-output/graphics-recovery';fs.mkdirSync(out,{recursive:true});
const fen='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']}),proof={passed:false,checks:[],errors:[]};
 try{
  const page=await browser.newPage({viewport:{width:1500,height:1000}});page.on('pageerror',e=>proof.errors.push(e.message));
  await page.goto(ready.url);await page.waitForFunction(()=>state.snapshot);
  await page.evaluate(({fen,gid})=>{refreshGameMoves=()=>{};displayPrefs.pieces3d='staunton1849';displayPrefs.focus3d=true;displayPrefs.camera3d={angle:48,orbit:12,zoom:1.1,lift:.1};displayPrefs.scene3d={environment:'studio',live:false,mode:'testing',motion:'instant',quality:'low'};displayPrefs.followNextGame=false;retainedTid=state.tid;retainedFocus={game:gid,tid:state.tid,number:0,white:{name:'White'},black:{name:'Black'},fen,status:'Saved game',searches:{}};focusId=gid;applyDisplay();renderFocus()}, {fen,gid:ready.gid});
  await page.locator('.focus-board').scrollIntoViewIfNeeded();
  const focusedReady=()=>page.waitForFunction(()=>board3dRecovery.phase==='ready'&&Number(board3dCanvas?.dataset.frames)>0);
  await focusedReady();
  const before=await page.evaluate(()=>JSON.stringify([displayPrefs.camera3d,displayPrefs.scene3d]));
  const loss=()=>page.evaluate(()=>{window.lostCanvas=board3dCanvas;const gl=board3dCanvas.getContext('webgl2');gl.getExtension('WEBGL_lose_context').loseContext()});
  await loss();await page.waitForFunction(()=>board3dRecovery.failed&&!board3dCanvas);
  assert(await page.locator('.focus-board .board').isVisible());
  await focusedReady();assert(await page.evaluate(()=>board3dCanvas!==lostCanvas));
  assert.equal(await page.evaluate(()=>JSON.stringify([displayPrefs.camera3d,displayPrefs.scene3d])),before);
  assert(await page.locator('#focusContent').evaluate(el=>el.previousElementSibling.hidden));
  proof.checks.push('Focus automatic recovery, fresh renderer, camera/room preserved, warning cleared');
  await loss();await page.waitForFunction(()=>board3dRecovery.failed);await page.waitForTimeout(3500);
  assert(await page.evaluate(()=>board3dRecovery.failed&&!board3dCanvas));
  await page.evaluate(()=>notify('Unrelated saving diagnostic retained',true));
  await page.locator('#focusContent').evaluate(el=>el.previousElementSibling.querySelector('button').click());await focusedReady();
  assert.equal(await page.locator('#error').textContent(),'Unrelated saving diagnostic retained');
  proof.checks.push('Repeated loss stays in usable 2D; manual retry works without clearing worker errors');
  // Creation fails once, then the visible recovery button succeeds. No retry loop.
  await page.evaluate(()=>{window.realCreate=ArenaBoard3D.create;ArenaBoard3D.create=()=>{throw Error('Simulated unavailable GPU')};releaseBoard3d();renderFocus()});
  await page.waitForFunction(()=>board3dRecovery.failed);await page.screenshot({path:out+'/focus-fallback.png'});
  await page.evaluate(()=>{ArenaBoard3D.create=realCreate});
  await page.getByRole('button',{name:'Retry 3D',exact:true}).click();await focusedReady();
  await page.screenshot({path:out+'/focus-restored.png'});
  proof.checks.push('Unavailable graphics is caught; 2D fallback and explicit retry');
  await page.evaluate(()=>board3dRecovery.reset());await loss();await page.waitForFunction(()=>board3dRecovery.failed);
  await page.evaluate(()=>view('engines'));await page.waitForTimeout(3500);
  assert(await page.evaluate(()=>board3dRecovery.failed&&!board3dCanvas));
  await page.evaluate(()=>view('overview'));await page.locator('.focus-board').scrollIntoViewIfNeeded();await focusedReady();
  proof.checks.push('Hidden Focused Game defers recovery until visible');
  // Opting into 2D cancels the scheduled recovery.
  await page.evaluate(()=>board3dRecovery.reset());await loss();await page.waitForFunction(()=>board3dRecovery.failed);
  await page.evaluate(()=>{displayPrefs.focus3d=false;renderFocus()});await page.waitForTimeout(3500);
  assert(await page.evaluate(()=>!board3dCanvas&&board3dRecovery.phase==='ready'));
  proof.checks.push('Selecting 2D cancels pending recovery');
  await page.locator('[data-view=playerArena]').click();await page.waitForFunction(()=>PlayerDesk.board);
  await page.evaluate(async()=>{const {game:g}=await api('player/state');if(g&&['playing','starting','paused'].includes(g.state))await api('player/action',{id:g.id,revision:g.revision,action:'abandon'});await paPoll()});
  await page.locator('#paNew').click();await page.locator('[data-pa-engine="'+ready.profiles[0]+'"]').check();await page.locator('#paCreate').click();
  await page.waitForSelector('#paSetupName',{state:'hidden'});await page.locator('#paResume').click();await page.waitForFunction(()=>PlayerDesk.game?.state==='playing');
  await page.evaluate(()=>{paBoard().setMode('3d');paRender()});
  const playerReady=()=>page.waitForFunction(()=>PlayerDesk.board?.recovery.phase==='ready'&&Number(PlayerDesk.board?.canvas?.dataset.frames)>0);
  await playerReady();
  const playerLoss=()=>page.evaluate(()=>PlayerDesk.board.canvas.getContext('webgl2').getExtension('WEBGL_lose_context').loseContext());
  await playerLoss();await page.waitForFunction(()=>PlayerDesk.board.recovery.failed);await playerReady();
  assert(await page.evaluate(()=>displayPrefs.player3d));
  await playerLoss();await page.waitForFunction(()=>PlayerDesk.board.recovery.failed);await page.waitForTimeout(3500);
  assert(await page.locator('#paPhoto').isDisabled());assert(await page.locator('#paCameraToggle').isHidden());
  await page.locator('#paBoard [data-square=e2]').click();await page.locator('#paBoard [data-square=e4]').click();
  await page.waitForFunction(()=>PlayerDesk.game?.moves.length===2);assert.equal(await page.evaluate(()=>PlayerDesk.game.moves[0].uci),'e2e4');
  await page.screenshot({path:out+'/player-fallback.png'});
  await page.getByRole('button',{name:'Retry 3D',exact:true}).click();await playerReady();
  assert(await page.locator('#paPhoto').isEnabled());
  proof.checks.push('Player automatic and manual recovery; preference retained; legal human move in 2D fallback');
  // Dispose a player board with recovery pending; it must not resurrect a canvas.
  await page.evaluate(()=>PlayerDesk.board.recovery.reset());await playerLoss();await page.waitForFunction(()=>PlayerDesk.board.recovery.failed);
  await page.locator('[data-view=engines]').click();await page.waitForTimeout(3500);
  assert(await page.evaluate(()=>!PlayerDesk.board&&!document.querySelector('#paBoard canvas')));
  proof.checks.push('Leaving Player Arena cancels recovery and releases resources');
  await page.evaluate(async()=>{const {game:g}=await api('player/state');if(g&&['playing','starting','paused'].includes(g.state))await api('player/action',{id:g.id,revision:g.revision,action:'abandon'})});
  assert.deepEqual(proof.errors,[]);proof.passed=true;
 }finally{await browser.close();fs.writeFileSync(out+'/result.json',JSON.stringify(proof,null,2));}
 console.log(JSON.stringify(proof,null,2));
})().catch(e=>{console.error(e);process.exitCode=1});
