const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),out=process.argv[3];fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});const proof={passed:false,errors:[]};
 try{
  const p=await browser.newPage({viewport:{width:1600,height:1050}});p.on('pageerror',e=>proof.errors.push(e.message));
  await p.goto(ready.url+'&lang=en');await p.waitForFunction(()=>state.engines?.length&&queueData);
  await p.evaluate(()=>showRatingCenter());await p.waitForFunction(()=>RatingDesk.data?.total===5);
  const baseline=await p.evaluate(()=>RatingDesk.data);const older=baseline.items.find(r=>r.name.startsWith('Swift 1.0'));
  await p.evaluate(async row=>{await rcCommand({action:'anchor',category:'blitz',entry:row.id,rating:3000});await refreshRatings()},older);
  const all=await p.evaluate(()=>RatingDesk.data);await p.locator('#rcVersions').selectOption('best');await p.waitForFunction(()=>RatingDesk.data?.versions==='best'&&RatingDesk.data.total===4);
  const best=await p.evaluate(()=>RatingDesk.data);assert.deepEqual(best.items.filter(r=>r.family==='Swift').map(r=>r.threads).sort((a,b)=>a-b),[1,32]);
  for(const r of best.items){const old=all.items.find(v=>v.id===r.id);assert.equal(r.rating,old.rating);assert.deepEqual(r.ci,old.ci)}
  await p.locator('#rcAnchor').click();await p.waitForFunction(()=>$('#rcAnchorEntry')?.options.length>=6);assert(await p.locator(`#rcAnchorEntry option[value="${older.id}"]`).count());await p.keyboard.press('Escape');
  await p.locator('#ratingCenter').screenshot({path:path.join(out,'best-versions.png')});
  const text=await p.evaluate(()=>rcFetchText());assert(text.includes('Best version per family'));fs.writeFileSync(path.join(out,'ratings.txt'),text);
  const other=best.items.find(r=>r.family==='Other');await p.locator(`[data-rc-entry="${other.id}"]`).click();await p.locator('details').filter({has:p.locator('#rcFamilyName')}).locator('summary').click();await p.locator('#rcFamilyName').fill('Swift');await p.locator('#rcSaveFamily').click();await p.waitForFunction(()=>RatingDesk.data?.total===3);
  await p.evaluate(async id=>{await rcCommand({action:'family',entry:id,family:''});await refreshRatings()},other.id);await p.waitForFunction(()=>RatingDesk.data?.total===4);
  await p.reload();await p.waitForFunction(()=>state.engines?.length&&queueData);await p.evaluate(()=>showRatingCenter());await p.waitForFunction(()=>RatingDesk.data?.versions==='best'&&RatingDesk.data.total===4);
  await p.locator('#rcCategory').selectOption('all');await p.waitForFunction(()=>RatingDesk.data?.category==='all');assert.equal(await p.locator('#rcVersions').inputValue(),'all');assert.equal(await p.locator('#rcVersions option[value=best]').evaluate(el=>el.disabled),true,await p.locator('#rcFamilyNote').textContent());
  await p.locator('#rcCategory').selectOption('blitz');await p.waitForFunction(()=>RatingDesk.data?.category==='blitz');await p.locator('#rcVersions').selectOption('best');await p.waitForFunction(()=>RatingDesk.data?.versions==='best');
  for(const lang of ['es','fr','de','pt','it','nl','pl']){
   await p.goto(ready.url+'&lang='+lang);await p.waitForFunction(()=>state.engines?.length&&queueData);await p.evaluate(()=>showRatingCenter());await p.waitForFunction(()=>RatingDesk.data?.versions==='best');assert.notEqual(await p.locator('#rcVersions option[value=best]').textContent(),'Best version per engine family');
  }
  assert.deepEqual(proof.errors,[]);proof.passed=true;proof.visible_configurations=4;proof.thread_counts=[1,32];
 }finally{await browser.close();fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(proof,null,2))}
 console.log('Ratings families UI, anchors, exports, persistence and seven translations passed.');
})().catch(e=>{console.error(e);process.exitCode=1});
