const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),out=process.argv[3];fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try{
  const p=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];p.on('pageerror',e=>errors.push(e.message));
  await p.goto(ready.url+'&lang=en');await p.waitForFunction(()=>state.engines?.length&&queueData);
  await p.evaluate(id=>showEvent(id),ready.eid);await p.waitForSelector('#cxSaveTemplate');
  const text=await p.evaluate(()=>eventReport(eventDetailData));fs.writeFileSync(path.join(out,'competition.txt'),text);assert(text.includes('Season 2')&&text.includes('Champion')&&text.includes('Minimum played plies'));
  await p.locator('#siPanel-overview').screenshot({path:path.join(out,'completed.png')});
  // The same overview must remain bounded for a final with a large field.
  await p.evaluate(async id=>{const d=await api(`events/${id}?view=insights&export=1`);d.final.players=[...d.final.players,...d.final.players,...d.final.players,...d.final.players];renderSeasonOverview(d)},ready.eid);
  assert.equal(await p.locator('.si-final .si-score').count(),0);assert.equal(await p.locator('.si-final tbody tr').count(),8);
  await p.locator('.si-final').screenshot({path:path.join(out,'multi-entrant-final.png')});assert.deepEqual(errors,[]);
 }finally{await browser.close()}
 console.log('Completed competition text and multi-entrant final layout passed.');
})().catch(e=>{console.error(e);process.exitCode=1});
