// Real local fixture only; never connects to the installed workspace.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/rating-ready.json','utf8'));
 const out='test-output/rating-defaults-ui';fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,channel:'msedge'}),page=await browser.newPage({viewport:{width:1200,height:900}}),errors=[],checks=[];
 page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(ready.url);await page.waitForFunction(()=>typeof showRatingCenter==='function');
  await page.locator('[data-view=ratingCenter]').click();await page.waitForFunction(()=>RatingDesk.data?.total===6);
  await page.locator('#rcSettings').click();assert.equal(await page.locator('#rcCollect').isChecked(),true);assert.equal(await page.locator('#rcNewCollect').isChecked(),true);
  await page.locator('#rcNewName').fill('Collect by default');await page.screenshot({path:out+'/new-list.png'});await page.locator('#rcCreateList').click();
  await page.waitForFunction(()=>RatingDesk.data?.pool.name==='Collect by default');assert.equal(await page.evaluate(()=>!!RatingDesk.data.pool.automatic),true);
  await page.locator('#rcSettings').click();await page.locator('#rcCollect').uncheck();await page.locator('#rcSaveSettings').click();
  await page.waitForFunction(()=>!document.querySelector('#modal').open);await page.locator('#rcSettings').click();assert.equal(await page.locator('#rcCollect').isChecked(),false);
  await page.locator('#rcNewName').fill('Manual collection');await page.locator('#rcNewCollect').uncheck();await page.locator('#rcCreateList').click();
  await page.waitForFunction(()=>RatingDesk.data?.pool.name==='Manual collection');assert.equal(await page.evaluate(()=>!!RatingDesk.data.pool.automatic),false);
  await page.locator('#rcSettings').click();assert.equal(await page.locator('#rcNewCollect').isChecked(),true);await page.keyboard.press('Escape');
  checks.push('Main/new lists collect by default; deliberate opt-out saves; each new list starts checked');
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await page.goto(ready.url+'&lang='+lang);await page.waitForFunction(()=>typeof deleteEventRecords==='function'&&typeof state==='object');
   await page.evaluate(tid=>{state.tid=tid;document.querySelector('#deleteTournament').click()},ready.source);
   await page.waitForSelector('#keepRatingEvidence');assert.equal(await page.locator('#keepRatingEvidence').isChecked(),true);
   if(lang!=='en')assert.ok(!(await page.locator('#modal').textContent()).includes('Kept by default:'));
   await page.screenshot({path:`${out}/tournament-${lang}.png`});await page.locator('#keepRatingEvidence').uncheck();await page.keyboard.press('Escape');
   await page.evaluate(()=>document.querySelector('#deleteTournament').click());await page.waitForSelector('#keepRatingEvidence');assert.equal(await page.locator('#keepRatingEvidence').isChecked(),true);await page.keyboard.press('Escape');
   await page.evaluate(eid=>deleteEventRecords([eid]),ready.event);await page.waitForSelector('#eventKeepRatings');assert.equal(await page.locator('#eventKeepRatings').isChecked(),true);
   if(lang!=='en')assert.ok(!(await page.locator('#modal').textContent()).includes('Kept by default:'));
   await page.screenshot({path:`${out}/event-${lang}.png`});assert.ok(await page.evaluate(()=>document.querySelector('#modal').scrollWidth<=document.querySelector('#modal').clientWidth+2));
   await page.locator('#eventKeepRatings').uncheck();await page.keyboard.press('Escape');
   await page.evaluate(eid=>deleteEventRecords([eid]),ready.event);await page.waitForSelector('#eventKeepRatings');assert.equal(await page.locator('#eventKeepRatings').isChecked(),true);await page.keyboard.press('Escape');
  }
  checks.push('Tournament and event deletion default to checked every time in all eight languages');
  assert.deepEqual(errors,[]);fs.writeFileSync(out+'/acceptance.json',JSON.stringify({checks,errors},null,2));console.log(JSON.stringify({checks,errors}));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
