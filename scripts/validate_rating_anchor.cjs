// Run against scripts/preview_rating_anchor.py, never against the live worker.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/anchor-ready.json','utf8'));
 const out='test-output/rating-anchor-ui';fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,channel:'msedge'}),page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[],checks=[];
 page.on('pageerror',e=>errors.push(e.message));
 const count=async text=>{await page.waitForFunction(text=>document.querySelector('#rcAnchorPage')?.textContent===text,text)};
 const selection=async name=>{assert.match(await page.locator('#rcAnchorEntry option:checked').textContent(),name);assert.equal(await page.locator('#rcAnchorValue').inputValue(),'3700')};
 try{
  await page.goto(ready.url);await page.waitForFunction(()=>typeof showRatingCenter==='function');await page.locator('[data-view=ratingCenter]').click();
  await page.waitForFunction(()=>RatingDesk.data?.total===64);
  const expected=await page.evaluate(async()=>Object.fromEntries((await api('rating-center?'+rcQuery({export:'json'}))).items.map(x=>[x.id,x.rank])));
  const checkRanks=async()=>{
   const displayed=await page.locator('#rcRows tr').evaluateAll(rows=>rows.map(r=>[r.querySelector('[data-rc-entry]').dataset.rcEntry,Number(r.querySelector('.rc-rank').textContent)]));
   for(const [id,rank] of displayed)assert.equal(rank,expected[id]);
   assert.equal(await page.locator('#rcHeads th').count(),await page.locator('#rcRows tr').first().locator('td').count());
  };
  await checkRanks();await page.screenshot({path:out+'/ranked-list.png'});
  await page.locator('#rcNext').click();await page.waitForFunction(()=>RatingDesk.data?.offset===50);await checkRanks();assert.equal(await page.locator('#rcNext').isDisabled(),true);
  await page.locator('[data-rc-sort=name]').click();await page.waitForFunction(()=>RatingDesk.data?.offset===0&&RatingDesk.data.sort==='name');await checkRanks();
  await page.locator('#rcSearch').fill('Stockfish');await page.waitForFunction(()=>RatingDesk.data?.total===1);await checkRanks();
  await page.locator('#rcSearch').fill('');await page.waitForFunction(()=>RatingDesk.data?.total===64);
  await page.locator('[data-rc-sort=rank]').click();await page.waitForFunction(()=>RatingDesk.data.sort==='rank'&&RatingDesk.data.direction==='asc');await checkRanks();
  const csv=await page.evaluate(()=>fetch('/api/rating-center?'+rcQuery({export:'csv'}),{headers:{'X-Arena-Token':token}}).then(r=>r.text()));assert.match(csv,/^Rank,Engine,/);
  const text=await page.evaluate(()=>rcFetchText());assert.match(text,/Rank\s+Engine/);fs.writeFileSync(out+'/ranked-export.txt',text);
  await page.locator('#rcCategory').selectOption('all');await page.waitForFunction(()=>RatingDesk.data?.category==='all');assert.equal(await page.locator('[data-rc-sort=rank]').count(),0);assert.match(await page.locator('#rcRows tr').first().textContent(),/Rank:/);
  await page.screenshot({path:out+'/category-ranks.png'});await page.locator('#rcCategory').selectOption('blitz');await page.waitForFunction(()=>RatingDesk.data?.category==='blitz');
  checks.push('Rank column and exports match API; ranks persist on page 2, search and sort; each time category has independent ranks');
  await page.locator('#rcAnchor').click();await count('1–50 / 64');
  await selection(/Stockfish dev · 1 thread/);assert.equal(await page.locator('#rcAnchorEntry').inputValue(),ready.anchor);
  assert.equal(await page.locator('#rcAnchorEntry option').count(),52);assert.equal(await page.locator('#rcAnchorPrev').isDisabled(),true);
  checks.push('Anchor beyond first 50 entries opens selected with its full name and 3700');
  await page.screenshot({path:out+'/anchor-first-page.png'});
  await page.locator('#rcAnchorNext').click();await count('51–64 / 64');await selection(/Stockfish/);
  assert.equal(await page.locator('#rcAnchorNext').isDisabled(),true);assert.equal(await page.locator('#rcAnchorEntry option').count(),15);
  // Select another engine, then page and search without losing the pending choice.
  const other=await page.locator('#rcAnchorEntry option').filter({hasText:'Engine 63'}).getAttribute('value');
  await page.locator('#rcAnchorEntry').selectOption(other);await page.locator('#rcAnchorPrev').click();await count('1–50 / 64');await selection(/Engine 63/);
  await page.locator('#rcAnchorSearch').fill('no such engine');await count('0–0 / 0');await selection(/Engine 63/);
  await page.locator('#rcAnchorSearch').fill('Stockfish');await count('1–1 / 1');await selection(/Engine 63/);
  await page.locator('#rcAnchorEntry').selectOption(ready.anchor);await page.locator('#rcAnchorSearch').fill('');await count('1–50 / 64');await selection(/Stockfish/);
  checks.push('Every page reachable, no duplicate pinned entry, choice retained through search including zero matches');
  let release,started;
  const held=new Promise(resolve=>{release=resolve}),requested=new Promise(resolve=>{started=resolve});
  await page.route('**/api/rating-center?**',async route=>{
   if(new URL(route.request().url()).searchParams.get('q')==='Engine 02'){
    const response=await route.fetch();started();await held;await route.fulfill({response});
   }else await route.continue();
  });
  await page.locator('#rcAnchorSearch').fill('Engine 02');await requested;
  await page.locator('#rcAnchorSearch').fill('Stockfish');await count('1–1 / 1');
  const finished=page.waitForResponse(r=>r.url().includes('q=Engine+02'));release();await (await finished).finished();
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  assert.equal(await page.locator('#rcAnchorEntry option').filter({hasText:'Engine 02'}).count(),0);await selection(/Stockfish/);
  await page.unroute('**/api/rating-center?**');checks.push('Out-of-order search responses cannot overwrite newer results or selection');
  await page.locator('#rcAnchorSave').click();await page.waitForFunction(()=>!document.querySelector('#modal').open&&RatingDesk.data?.anchor?.rating===3700);
  assert.equal(await page.evaluate(()=>RatingDesk.data.anchor.entry),ready.anchor);
  await page.locator('#rcAnchor').click();await count('1–50 / 64');await selection(/Stockfish/);
  await page.locator('#rcAnchorEntry').selectOption('');await page.locator('#rcAnchorSearch').fill('Stockfish');await count('1–1 / 1');assert.equal(await page.locator('#rcAnchorEntry').inputValue(),'');
  await page.keyboard.press('Escape');checks.push('Save/reopen keeps the exact anchor; searching does not silently restore a cleared selection');
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await page.goto(ready.url+'&lang='+lang);await page.waitForFunction(()=>typeof showRatingCenter==='function');await page.locator('[data-view=ratingCenter]').click();await page.waitForFunction(()=>RatingDesk.data?.total===64);await page.locator('#rcAnchor').click();await count('1–50 / 64');await selection(/Stockfish/);
   if(lang!=='en')assert.ok(!(await page.locator('#modal').textContent()).includes('Search by name or browse all pages.'));
   await page.setViewportSize({width:1050,height:760});await page.screenshot({path:`${out}/anchor-${lang}.png`});assert.ok(await page.evaluate(()=>document.querySelector('#modal').scrollWidth<=document.querySelector('#modal').clientWidth+2));
  }
  checks.push('Eight translated catalogs, desktop minimum viewport without modal overflow');
  assert.deepEqual(errors,[]);fs.writeFileSync(out+'/acceptance.json',JSON.stringify({checks,errors},null,2));console.log(JSON.stringify({checks,errors}));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
