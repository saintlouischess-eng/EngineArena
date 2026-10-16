// Real retained results served by an isolated worker, never production mutations.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),out=process.argv[3];
 fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,channel:'msedge'}),checks=[];
 try{
  const page=await browser.newPage({viewport:{width:1500,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(25000);
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await page.goto(ready.url+'&lang='+lang);
   await page.locator('[data-view=ratingCenter]').click();
   await page.waitForFunction(()=>RatingDesk.data?.fit_summary?.finite_configurations===97);
   assert.equal(await page.locator('#rcHardware').inputValue(),'');
   assert.equal(await page.locator('#rcRows tr').count(),50);
   assert.equal(await page.locator('#rcFitNote').isVisible(),true);
   const note=await page.locator('#rcFitNote').textContent();assert.match(note,/97/);assert.match(note,/9/);
   if(lang!=='en')assert.ok(!note.includes('Ratings remain available'));
   await page.locator('#rcHardware').selectOption(ready.hardware);
   await page.waitForFunction(h=>RatingDesk.hardware===h&&RatingDesk.data?.fit_summary?.separated_configurations===0,ready.hardware);
   await page.locator('#rcHardware').selectOption('');
   await page.waitForFunction(()=>RatingDesk.data?.fit_summary?.separated_configurations===9);
   await page.locator('#rcVersions').selectOption('best');
   await page.waitForFunction(()=>RatingDesk.data?.versions==='best');
   assert.ok(await page.locator('#rcRows .rc-rating').count()>1);
   await page.locator('#rcCategory').selectOption('all');
   await page.waitForFunction(()=>RatingDesk.data?.category==='all');
   assert.equal(await page.locator('#rcFitNote').isVisible(),false);
   await page.locator('#rcCategory').selectOption('blitz');
   await page.waitForFunction(()=>RatingDesk.data?.fit_summary?.finite_configurations===97);
   checks.push({lang,ratingsVisible:true,hardwareReset:true,bestVersions:true,allCategories:true});
  }
  await page.goto(ready.url+'&lang=en');await page.locator('[data-view=ratingCenter]').click();
  await page.waitForFunction(()=>RatingDesk.data?.fit_summary?.finite_configurations===97);
  await page.locator('#rcVersions').selectOption('all');await page.waitForFunction(()=>RatingDesk.data?.versions==='all');
  await page.locator('#rcNext').click();await page.waitForFunction(()=>RatingDesk.data?.offset===50);
  assert.ok(await page.locator('#rcRows .rc-rating').count()>0);
  await page.locator('#rcSearch').fill(ready.separated);
  await page.waitForFunction(()=>RatingDesk.data?.total===1);
  assert.equal(await page.evaluate(()=>RatingDesk.data.items[0].status),'no_finite_fit');
  await page.locator('#rcSearch').fill('');await page.waitForFunction(()=>RatingDesk.data?.total===229);
  await page.locator('[data-rc-sort=rating]').click();
  await page.waitForFunction(()=>RatingDesk.data?.sort==='rating');
  for(const light of [false,true]){
   await page.evaluate(v=>document.body.classList.toggle('light',v),light);
   await page.screenshot({path:path.join(out,light?'ratings-light.png':'ratings-dark.png')});
  }
  assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,'validation.json'),JSON.stringify({passed:true,checks,pagination:true,separatedEntry:true,errors},null,2));
  console.log('Rating rows, hardware filters, best versions, categories and pagination passed in all eight languages.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
