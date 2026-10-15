// Run against a disposable workflow fixture, never a production worker.
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const root=path.resolve(__dirname,'..'),ready=JSON.parse(fs.readFileSync(path.join(root,'test-output/workflow-ready.json')));
const fen='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
async function snapshotCounts(session){
 let chunks=[];const receive=e=>chunks.push(e.chunk);session.on('HeapProfiler.addHeapSnapshotChunk',receive);
 await session.send('HeapProfiler.takeHeapSnapshot');session.off('HeapProfiler.addHeapSnapshotChunk',receive);
 const h=JSON.parse(chunks.join('')),m=h.snapshot.meta,n=h.nodes,str=h.strings,size=m.node_fields.length,types=m.node_types[0];
 const result={contexts:0,renderers:0};
 for(let i=0;i<n.length;i+=size){const type=types[n[i]],name=str[n[i+1]];if(type==='native'&&name==='WebGL2RenderingContext')result.contexts++;if(type==='object'&&name==='WebGLRenderer')result.renderers++;}
 return {...result,...await session.send('Runtime.getHeapUsage')};
}
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--enable-unsafe-swiftshader']});
 const proof={passed:false,checks:{}};
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1100}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  // --baseline loads only the old renderer, so the exact same exercise must fail.
  if(process.argv.includes('--baseline')){
   const upstream=execFileSync(path.join(root,'.venv/Scripts/python.exe'),['-c',"import tarfile,sys;sys.stdout.buffer.write(tarfile.open('build/three-0.186.1.tgz').extractfile('package/build/three.module.js').read())"],{cwd:root,maxBuffer:8*1024*1024}).toString().replaceAll('./three.core.min.js','./three.core.js');
   await page.route('**/assets/three.module.js',route=>route.fulfill({body:upstream,contentType:'text/javascript'}));
  }
  await page.goto(ready.url);await page.waitForFunction(()=>state.snapshot);
  await page.evaluate(async()=>{displayPrefs.focus3d=false;renderFocus();await ArenaBoard3D.prepare()});
  const session=await page.context().newCDPSession(page);await session.send('HeapProfiler.enable');
  let retirement=0;
  const cycle=()=>page.evaluate(({fen,boardDesign})=>{const canvas=document.createElement('canvas');canvas.style.cssText='position:fixed;top:0;left:0;width:320px;height:320px';document.body.append(canvas);const board=ArenaBoard3D.create(canvas,()=>{});board.render(fen,false,{},false,'',[],'inward',{}, {}, {board:boardDesign});board.dispose();canvas.remove()},{fen,boardDesign:['classic','drueke','jaques'][retirement++%3]});
  for(let i=0;i<5;i++)await cycle();await page.waitForTimeout(100);proof.warm=await snapshotCounts(session);
  for(let i=0;i<80;i++){await cycle();if(i%20===19)console.log('Retired boards:',i+1)}
  await page.waitForTimeout(300);proof.after=await snapshotCounts(session);
  assert.ok(proof.after.contexts<=proof.warm.contexts+2,JSON.stringify(proof));
  assert.ok(proof.after.renderers<=proof.warm.renderers+2,JSON.stringify(proof));
  proof.checks.retiredContextsBounded=true;
  // Multiple renderers must have independent LUT ownership. Disposing one must
  // leave the other's physical materials and lighting intact.
  await page.evaluate(fen=>{window.otherBoards=[];for(let i=0;i<2;i++){const canvas=document.createElement('canvas');canvas.style.cssText=`position:fixed;top:0;left:${i*330}px;width:320px;height:320px`;document.body.append(canvas);const board=ArenaBoard3D.create(canvas,()=>{});board.render(fen,false,{});otherBoards.push({canvas,board})}otherBoards[0].board.dispose();otherBoards[0].canvas.remove();otherBoards[1].board.render(fen,false,{orbit:30});if(otherBoards[1].canvas.getContext('webgl2').getError())throw Error('GL error after peer disposal');otherBoards[1].board.dispose();otherBoards[1].canvas.remove();otherBoards=null},fen);
  proof.checks.independentRenderers=true;
  await page.evaluate(({fen,gid})=>{window.refreshMovesBeforeTest=refreshGameMoves;refreshGameMoves=()=>{};displayPrefs.focus3d=true;displayPrefs.followNextGame=false;displayPrefs.panels.focus={visible:true,column:'left',height:740};applyDisplay();retainedTid=state.tid;retainedFocus={game:gid,tid:state.tid,number:0,white:{name:'First White'},black:{name:'First Black'},fen,status:'Saved game',searches:{}};focusId=gid;renderFocus()}, {fen,gid:ready.gid});
  await page.waitForFunction(()=>Number(board3dCanvas?.dataset.frames)>0);
  await page.evaluate(()=>{window.originalBoardCanvas=board3dCanvas;window.originalBoardInstance=board3dInstance;window.openedReplay='';gameDetail=async gid=>{openedReplay=gid};});
  for(let i=1;i<=200;i++)await page.evaluate(i=>{retainedFocus={...retainedFocus,game:'switch-'+i,white:{name:'White '+i},black:{name:'Black '+i},fen:i%2?'8/8/8/8/8/8/5K2/7k w - - 0 1':'8/8/8/8/8/5K2/8/7k b - - 0 1'};focusId=retainedFocus.game;renderFocus()},i);
  await page.waitForTimeout(300);
  assert.ok(await page.evaluate(()=>board3dCanvas===originalBoardCanvas&&board3dInstance===originalBoardInstance));
  assert.match(await page.locator('#focusContent [data-clock-side=white] .clock-name').textContent(),/White 200/);
  assert.match(await page.locator('#focusContent [data-clock-side=black] .clock-name').textContent(),/Black 200/);
  await page.locator('[data-focus-replay]').click();assert.equal(await page.evaluate(()=>openedReplay),'switch-200');
  const frame=await page.evaluate(()=>board3dCanvas.dataset.frames);await page.waitForTimeout(2300);assert.equal(await page.evaluate(()=>board3dCanvas.dataset.frames),frame);
  proof.checks.gameSwitchesReuseCanvasAndRenderer=200;proof.checks.namesAndReplayFollowGame=true;proof.checks.idleDoesNotRedraw=true;
  await page.screenshot({path:path.join(root,'test-output/board3d-lifetime.png')});
  for(let i=0;i<20;i++){await page.evaluate(()=>{displayPrefs.focus3d=false;renderFocus()});await page.evaluate(()=>{displayPrefs.focus3d=true;renderFocus()});await page.waitForFunction(()=>Number(board3dCanvas?.dataset.frames)>0)}
  await page.evaluate(()=>{displayPrefs.focus3d=false;renderFocus();originalBoardCanvas=null;originalBoardInstance=null});
  await page.waitForTimeout(200);proof.toggled=await snapshotCounts(session);assert.ok(proof.toggled.contexts<=proof.after.contexts+2);
  proof.checks.twentyStyleSwitchesBounded=true;assert.deepEqual(errors,[]);proof.passed=true;
 }finally{await browser.close();fs.writeFileSync(path.join(root,'test-output/board3d-lifetime'+(process.argv.includes('--baseline')?'-baseline':'')+'.json'),JSON.stringify(proof,null,2));}
 console.log(JSON.stringify(proof,null,2));
})().catch(e=>{console.error(e);process.exitCode=1});
