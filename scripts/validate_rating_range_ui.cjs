// Real API/DOM workflow against an isolated source or packaged worker.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),out=process.argv[3];fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,channel:'msedge'}),checks=[];
 try{
  const page=await browser.newPage({viewport:{width:1500,height:1000}}),errors=[];
  await page.addInitScript(()=>localStorage.setItem('arena-rating-versions','all'));
  page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(30000);
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await page.goto(ready.url+'&lang='+lang);await page.locator('[data-view=ratingCenter]').click();
   await page.waitForFunction(()=>RatingDesk.data?.total===61);await page.locator('#rcAuto').uncheck();
   assert.equal(await page.locator('#rcRange').inputValue(),'0');
   await page.locator('#rcRange').selectOption('400');
   await page.waitForFunction(()=>RatingDesk.data?.opponent_range?.elo===400);
   await page.locator('#rcRange').selectOption('custom');await page.locator('#rcRangeValue').fill('250');
   await page.locator('#rcRangeForm button').click();
   await page.waitForFunction(()=>RatingDesk.data?.opponent_range?.elo===250);
   assert.equal(await page.locator('#rcRows tr').count(),50);assert.equal(await page.locator('#rcRangeNote').isVisible(),true);
   if(lang!=='en')assert.notEqual(await page.locator('#rcRangeHelp').textContent(),'Compare ratings using nearby opponents. Matchups are selected from the all-opponent ratings; saved results stay unchanged.');
   await page.locator('#rcNext').click();await page.waitForFunction(()=>RatingDesk.data?.offset===50);
   assert.equal(await page.locator('#rcRows tr').count(),11);
   await page.locator('#rcSearch').fill(ready.disconnected);
   await page.waitForFunction(()=>RatingDesk.data?.total===1);
   const row=await page.evaluate(()=>RatingDesk.data.items[0]);assert.equal(row.rating,null);assert.ok(Number.isFinite(row.full_rating));
   await page.locator('#rcSearch').fill('');await page.waitForFunction(()=>RatingDesk.data?.total===61);
   await page.locator('[data-rc-sort=full_rating]').click();await page.waitForFunction(()=>RatingDesk.data?.sort==='full_rating');
   await page.locator('#rcVersions').selectOption('best');await page.waitForFunction(()=>RatingDesk.data?.versions==='best');
   assert.equal(await page.evaluate(()=>RatingDesk.data.opponent_range.elo),250);
   await page.locator('#rcCategory').selectOption('all');await page.waitForFunction(()=>RatingDesk.data?.category==='all');
   assert.equal(await page.locator('#rcRange').isDisabled(),true);assert.equal(await page.locator('#rcRangeNote').isVisible(),false);
   await page.locator('#rcCategory').selectOption('blitz');await page.waitForFunction(()=>RatingDesk.data?.category==='blitz');
   assert.equal(await page.locator('#rcRange').inputValue(),'0');
   checks.push({lang,range:true,pagination:true,unavailableFullVisible:true,sort:true,bestVersions:true,categoryReset:true});console.log('Passed language',lang);
  }
  await page.goto(ready.url+'&lang=en');await page.locator('[data-view=ratingCenter]').click();await page.waitForFunction(()=>RatingDesk.data?.total===61);
  await page.locator('#rcRange').selectOption('custom');await page.locator('#rcRangeValue').fill('250');await page.locator('#rcRangeForm button').click();
  await page.waitForFunction(()=>RatingDesk.data?.opponent_range?.elo===250);
  const txt=await page.evaluate(()=>rcFetchText());assert.match(txt,/Opponent range: \+\/-250 Elo/);assert.match(txt,/Full Elo/);
  await page.locator('#rcRows [data-rc-entry]').first().click();await page.waitForFunction(()=>document.querySelector('#rcHistory table'));
  assert.match(await page.locator('#modal').textContent(),/Full Elo/);await page.evaluate(()=>document.querySelector('#modal').close());
  for(const [width,light] of [[1500,false],[1100,false],[1500,true]]){
   await page.setViewportSize({width,height:1000});await page.evaluate(v=>document.body.classList.toggle('light',v),light);
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);assert.equal(overflow,false);
   await page.screenshot({path:path.join(out,`ratings-${width}-${light?'light':'dark'}.png`)});
  }
  assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,'validation.json'),JSON.stringify({passed:true,checks,textExport:true,entryDetails:true,errors},null,2));
  console.log('Opponent-range UI: eight languages, filters, pages, full/filtered ratings, text export, details and responsive layout passed.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
