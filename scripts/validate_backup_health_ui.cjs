// Exercise the shipped interface with review.js deliberately held back.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),out=process.argv[3];
 const browser=await chromium.launch({headless:true,channel:'msedge'}),checks=[];
 try{
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   const page=await browser.newPage({viewport:{width:1500,height:950}}),errors=[];
   page.on('pageerror',e=>errors.push(e.message));
   let releaseReview;const held=new Promise(resolve=>{releaseReview=resolve});
   await page.route('**/assets/review.js',async route=>{await held;await route.continue()});
   try{
    await page.goto(ready.url+'&lang='+lang,{waitUntil:'commit'});
    await page.waitForFunction(()=>typeof renderWorkerHealth==='function'&&typeof state!=='undefined');
    // Bypass the startup gate only in this regression probe: the helper must
    // remain usable with its caller even before the rest of the UI has loaded.
    const early=await page.evaluate(async()=>{
     const response=await fetch('/api/status',{headers:{'X-Arena-Token':token}});
     const s=await response.json();renderWorkerHealth(s);
     return {reviewNotLoaded:typeof reviewLabels==='undefined',backupPresent:!!document.querySelector('#healthContent .backup-health'),error:document.querySelector('#error').textContent};
    });
    assert.equal(early.reviewNotLoaded,true);assert.equal(early.backupPresent,true);
    assert.doesNotMatch(early.error,/backupHealth|not defined/);
    releaseReview();await page.waitForLoadState('load');
    await page.locator('[data-view=health]').click();
    await page.waitForFunction(()=>document.querySelector('#healthContent .backup-health'));
    await page.evaluate(async()=>{await refresh();await refreshStorage()});
    assert.deepEqual(errors,[],lang+' browser errors');
    assert.doesNotMatch(await page.locator('#error').textContent(),/backupHealth|not defined/);
    if(lang==='en')await page.screenshot({path:path.join(path.dirname(out),'backup-health.png')});
    checks.push({language:lang,earlyStatusWithReviewBlocked:true,backupVisible:true,browserErrors:errors});
   }finally{releaseReview();await page.close()}
  }
  fs.writeFileSync(out,JSON.stringify({passed:true,checks},null,2));
  console.log('All eight languages passed delayed-script startup and backup display checks.');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
