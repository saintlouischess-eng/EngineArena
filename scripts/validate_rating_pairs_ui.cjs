const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/rating-pair-ready.json','utf8'));
 const out='test-output/rating-pair-ui';fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--use-angle=swiftshader']});
 const page=await browser.newPage({viewport:{width:1500,height:1000}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 try{
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await page.goto(ready.url+'&lang='+lang);await page.waitForFunction(()=>typeof showRatingCenter==='function');
   await page.locator('[data-view=ratingCenter]').click();await page.waitForFunction(()=>RatingDesk.data?.sampling?.compatible_update_pairs===1);
   const text=await page.locator('#rcSampleNote').textContent();assert.match(text,/1/);if(lang!=='en')assert.ok(!text.includes('CPU opening pairs retained'));
   await page.locator('#rcCondition').selectOption(ready.conditions[0]);await page.waitForFunction(()=>RatingDesk.data?.sampling?.incomplete_pair_games===1);
   assert.equal(await page.locator('#rcSampleNote').isVisible(),true);
   await page.locator('#rcCondition').selectOption('');await page.waitForFunction(()=>RatingDesk.data?.counted_games===2);
   await page.locator('#rcCategory').selectOption('all');await page.waitForFunction(()=>RatingDesk.data?.category==='all');assert.equal(await page.locator('#rcSampleNote').isVisible(),false);
   await page.locator('#rcCategory').selectOption('blitz');await page.waitForFunction(()=>RatingDesk.data?.sampling?.compatible_update_pairs===1);
  }
  for(const width of [1500,1100])for(const light of [false,true]){
   await page.setViewportSize({width,height:1000});await page.evaluate(v=>document.body.classList.toggle('light',v),light);
   assert.ok(await page.evaluate(()=>document.body.scrollWidth<=innerWidth+2));
   await page.screenshot({path:`${out}/${width}-${light?'light':'dark'}.png`});
  }
  assert.deepEqual(errors,[]);const result={languages:8,exact_filters:true,category_switch:true,responsive:true,errors};fs.writeFileSync(out+'/result.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
