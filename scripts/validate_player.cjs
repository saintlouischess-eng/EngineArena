// Isolated, real mouse workflow. Never connect this harness to production data.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const ready=JSON.parse(fs.readFileSync(process.env.ARENA_PLAYER_READY||'test-output/workflow-ready.json'));
assert(ready.folder.includes('test-output')&&path.basename(ready.folder).startsWith('workflow-'));
const out=process.env.ARENA_PLAYER_OUT||'test-output/player-source';fs.mkdirSync(out,{recursive:true});
(async()=>{const browser=await chromium.launch({headless:true,channel:'msedge'}),proof={passed:false,errors:[]};let page;
 try{
  page=await browser.newPage({viewport:{width:1600,height:1050}});page.on('pageerror',e=>proof.errors.push(e.stack));
  await page.goto(ready.url);await page.waitForFunction(()=>typeof PlayerDesk!=='undefined');
  // Clear only our active fixture game when rerunning this acceptance harness.
  await page.evaluate(async()=>{const {game:g}=await api('player/state');if(g&&['playing','starting','paused'].includes(g.state))await api('player/action',{id:g.id,revision:g.revision,action:'abandon'})});
  await page.locator('[data-view=playerArena]').click();await page.waitForFunction(()=>PlayerDesk.board);
  await page.evaluate(async()=>{await api('player/settings',{sound:true,auto_queen:false});await paOverview()});
  if(await page.evaluate(()=>PlayerDesk.board.mode==='3d'))await page.locator('#paStyle').click();
  await page.locator('#paNew').click();
  await page.locator('[data-pa-engine]').first().check();await page.locator('#paCreate').click();await page.waitForSelector('#paSetupName',{state:'hidden'});
  await page.locator('#paResume').click();await page.waitForFunction(()=>PlayerDesk.game?.state==='playing');
  await page.locator('#paBoard [data-square=e2]').click();await page.locator('#paBoard [data-square=e4]').click();
  await page.waitForFunction(()=>PlayerDesk.game?.moves.length===2);assert.equal(await page.evaluate(()=>PlayerDesk.game.moves[0].uci),'e2e4');
  const center=async sq=>{const b=await page.locator(`#paBoard [data-square=${sq}]`).boundingBox();return {x:b.x+b.width/2,y:b.y+b.height/2}};
  const a=await center('d2'),b=await center('d4');await page.mouse.move(a.x,a.y);await page.mouse.down();await page.mouse.move(b.x,b.y,{steps:12});await page.mouse.up();
  await page.waitForFunction(()=>PlayerDesk.game?.moves.length===4);assert.equal(await page.evaluate(()=>PlayerDesk.game.moves[2].uci),'d2d4');
  await page.locator('#paFirst').click();assert.equal(await page.evaluate(()=>PlayerDesk.review),0);await page.locator('#paLive').click();
  await page.locator('#paAnalysis').check();await page.waitForFunction(()=>PlayerDesk.game?.analysis);await page.locator('#paPause').click();await page.waitForFunction(()=>PlayerDesk.game?.state==='paused');
  await page.screenshot({path:out+'/2d-player.png',fullPage:true});
  await page.locator('#paExport').click();await page.waitForFunction(()=>document.querySelector('#pgnExample')?.value.includes('1. e4'));
  await page.locator('#pgnPreset').selectOption('clean');await page.waitForFunction(()=>document.querySelector('#pgnExample')?.value.includes('1. e4')&&!document.querySelector('#pgnExample').value.includes('ScorePerspective'));
  await page.locator('#modal [data-close]').first().click();await page.locator('#paStyle').click();
  await page.waitForFunction(()=>PlayerDesk.board?.renderer);await page.evaluate(()=>PlayerDesk.board.renderer.ready());
  await page.screenshot({path:out+'/3d-player.png',fullPage:true});
  await page.locator('#paResume').click();await page.waitForFunction(()=>PlayerDesk.game?.state==='playing');
  // Locate square projection by querying the actual pick API over screen pixels.
  async function squarePoint(square){return page.evaluate(square=>{const b=PlayerDesk.board,r=b.canvas.getBoundingClientRect();for(let y=r.top+10;y<r.bottom-10;y+=3)for(let x=r.left+10;x<r.right-10;x+=3)if(b.renderer.pick(x,y,true)===square&&b.renderer.pick(x,y)===square)return {x,y};return null},square)}
  const from=await squarePoint('g1'),to=await squarePoint('f3');assert(from&&to);await page.mouse.click(from.x,from.y);await page.mouse.click(to.x,to.y);await page.waitForFunction(()=>PlayerDesk.game?.moves.length===6);
  assert.equal(await page.evaluate(()=>PlayerDesk.game.moves[4].uci),'g1f3');
  const dragFrom=await squarePoint('b1'),dragTo=await squarePoint('c3');assert(dragFrom&&dragTo);
  await page.mouse.move(dragFrom.x,dragFrom.y);await page.mouse.down();await page.mouse.move(dragTo.x,dragTo.y,{steps:12});await page.mouse.up();
  await page.waitForFunction(()=>PlayerDesk.game?.moves.length===8);assert.equal(await page.evaluate(()=>PlayerDesk.game.moves[6].uci),'b1c3');proof.drag3d=true;
  await page.locator('#paResign').click();await page.locator('#paConfirmAction').click();await page.waitForFunction(()=>PlayerDesk.game?.state==='completed');
  assert.equal(await page.evaluate(()=>PlayerDesk.game.result),'0-1');
  await page.locator('#paPhoto').click();await page.waitForFunction(()=>document.querySelector('#paPhotoPreview')?.src.startsWith('data:image/png'));
  assert(await page.locator('.photo-destination').isVisible());await page.locator('#modal [data-close]').first().click();
  // Decode the shipped, original audio rather than merely checking filenames.
  proof.sounds=await page.evaluate(async()=>{const c=new AudioContext(),result={};try{for(const kind of ['move','capture','castle','check','promotion','win','loss','draw','low']){const r=await fetch('/assets/player-'+kind+'.wav');if(!r.ok)throw Error(kind+' missing');const b=await c.decodeAudioData(await r.arrayBuffer());result[kind]={seconds:b.duration,channels:b.numberOfChannels};if(b.duration<=0||b.duration>3)throw Error(kind+' invalid')}}finally{await c.close()}return result});
  await page.locator('#paSound').click();await page.waitForFunction(()=>document.querySelector('#paSound').getAttribute('aria-pressed')==='false');
  await page.reload();await page.waitForFunction(()=>typeof PlayerDesk!=='undefined');await page.locator('[data-view=playerArena]').click();await page.waitForFunction(()=>PlayerDesk.overview);assert.equal(await page.locator('#paSound').getAttribute('aria-pressed'),'false');
  // Underpromotion through the actual choice dialog.
  await page.evaluate(async()=>{const p=(await api('profiles')).items[0];const r=await api('player/create',{engine:p.id,config:{fen:'7k/P7/6K1/8/8/8/8/8 w - - 0 1',hash:16}});PlayerDesk.viewing=null;paAccept(r)});
  if(await page.evaluate(()=>PlayerDesk.board.mode==='3d'))await page.locator('#paStyle').click();
  await page.locator('#paResume').click();await page.waitForFunction(()=>PlayerDesk.game?.state==='playing');await page.locator('#paBoard [data-square=a7]').click();await page.locator('#paBoard [data-square=a8]').click();
  await page.locator('[data-pa-promote=a7a8n]').click();await page.waitForFunction(()=>PlayerDesk.game?.state==='completed');assert.equal(await page.evaluate(()=>PlayerDesk.game.reason),'insufficient_material');proof.underpromotion=true;
  await page.locator('#paNew').click();await page.locator('#paMode').selectOption('series');await page.locator('[data-pa-engine]').nth(0).check();await page.locator('[data-pa-engine]').nth(1).check();
  assert((await page.locator('#paSchedule').textContent()).startsWith('4 '));await page.locator('#paCreate').click();await page.waitForSelector('#paSetupName',{state:'hidden'});
  await page.locator('.pa-series').first().locator('summary').click();
  const series=await page.evaluate(()=>PlayerDesk.overview.series[0].id);
  for(let round=0;round<4;round++){
   await page.locator(`[data-pa-next="${series}"]`).click();await page.waitForFunction(round=>PlayerDesk.game?.number===round+1,round);
   assert.equal(await page.evaluate(()=>PlayerDesk.game.config.color),round<2?'white':'black');
   await page.locator('#paResign').click();await page.locator('#paConfirmAction').click();await page.waitForFunction(()=>PlayerDesk.game?.state==='completed');
   await page.waitForFunction(round=>PlayerDesk.overview.series[0].played===round+1,round);
   if(round<3)await page.locator('.pa-series').first().locator('summary').click();
  }
  assert(await page.evaluate(()=>PlayerDesk.overview.series[0].complete));proof.series={games:4,alternatingColors:true};
  await page.setViewportSize({width:1200,height:800});await page.screenshot({path:out+'/laptop-player.png',fullPage:true});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.locator('#theme').click();await page.screenshot({path:out+'/light-player.png',fullPage:true});
  await page.locator('[data-view=engines]').click();assert(await page.evaluate(()=>!PlayerDesk.board));
  proof.passed=true;proof.moves=await page.evaluate(()=>PlayerDesk.game.moves.length);assert.deepEqual(proof.errors,[]);
 }catch(e){proof.failure=e.stack;if(page)proof.boardState=await page.evaluate(()=>({view:state.view,ready:ArenaBoard3D.isReady(),board:PlayerDesk.board?{mode:PlayerDesk.board.mode,loading:PlayerDesk.board.loading,onscreen:PlayerDesk.board.onscreen,disposed:PlayerDesk.board.disposed,rect:PlayerDesk.board.host.getBoundingClientRect().toJSON()}:null})).catch(()=>null);if(page)await page.screenshot({path:out+'/failure.png',fullPage:true}).catch(()=>{});throw e}
 finally{fs.writeFileSync(out+'/result.json',JSON.stringify(proof,null,2));await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});

