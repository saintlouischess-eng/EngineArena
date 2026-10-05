const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const file=process.argv[2],info=JSON.parse(fs.readFileSync(file,'utf8'));
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const page=await browser.newPage({viewport:{width:1920,height:1080}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(`http://127.0.0.1:${info.port}/?token=${info.token}`);
  await page.waitForFunction(()=>typeof state!=='undefined'&&state.snapshot);
  await page.locator('#tournamentPicker').selectOption(info.tid);
  await page.waitForFunction(tid=>state.snapshot?.id===tid,info.tid);
  assert.equal(await page.locator('.graph-panel:not([hidden])').count(),16);
  fs.writeFileSync(file.replace(/\.json$/,'.ready'),'ready');
  let maxBoards=0,frameWorst=0,elapsed=0;const began=Date.now();
  while(Date.now()-began<1200000){
   const s=await page.evaluate(()=>({completed:state.snapshot?.state==='completed',boards:document.querySelectorAll('#liveBoards .board-card').length,error:state.workerError}));
   maxBoards=Math.max(maxBoards,s.boards);if(s.completed)break;
   await page.waitForTimeout(400);
  }
  assert.ok(maxBoards>=28,`Only ${maxBoards} boards observed`);assert.deepEqual(errors,[]);
  await page.screenshot({path:file.replace(/\.json$/,'.png')});
  const metrics=await page.evaluate(()=>api('status'));
  fs.writeFileSync(file.replace(/\.json$/,'-ui-result.json'),JSON.stringify({maxBoards,errors,seconds:(Date.now()-began)/1000,metrics:metrics.ui_metrics},null,2));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
