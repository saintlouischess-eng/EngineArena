// Hold real script responses while a fast local worker serves saved results.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),out=process.argv[3];
 const browser=await chromium.launch({headless:true,channel:'msedge'}),checks=[];
 try{
  const scenarios=[{script:'results.js',lang:'en',baseline:true},
   ...['en','es','fr','de','pt','it','nl','pl'].map(lang=>({script:'results.js',lang})),
   {script:'review.js',lang:'en'},{script:'player-workspace.js',lang:'en'}];
  for(const scenario of scenarios){
   const page=await browser.newPage({viewport:{width:1500,height:950}}),errors=[];
   page.setDefaultTimeout(20000);page.on('pageerror',e=>errors.push(e.message));
   let releaseScript;const held=new Promise(resolve=>releaseScript=resolve);let requests=0;
   page.on('request',request=>{if(new URL(request.url()).pathname.startsWith('/api/'))requests++});
   await page.route('**/assets/'+scenario.script,async route=>{await held;await route.continue()});
   if(scenario.baseline)await page.route('**/assets/app.js',async route=>{
    const response=await route.fetch(),text=await response.text();assert.ok(text.includes('await interfaceReady;'));
    await route.fulfill({response,body:text.replace('await interfaceReady;','')});
   });
   try{
    await page.goto(ready.url+'&lang='+scenario.lang,{waitUntil:'commit'});
    await page.waitForFunction(()=>typeof refresh==='function'&&typeof displayPrefs!=='undefined');
    if(scenario.baseline){
     await page.waitForFunction(()=>document.querySelector('#error').textContent.includes('renderStandings is not defined'));
     checks.push({...scenario,reproduced:true,message:await page.locator('#error').textContent()});
     continue;
    }
    // The blocked final script also outlasts background polling timers.
    await page.waitForTimeout(2200);
    assert.equal(requests,0,scenario.script+' allowed a premature API request');
    assert.equal(await page.evaluate(()=>document.readyState),'loading');
    releaseScript();await page.waitForLoadState('domcontentloaded');
    await page.waitForFunction(()=>state.connected&&document.querySelectorAll('#standings tbody tr').length===2);
    await page.waitForFunction(()=>displayPrefs.fontSize===18);
    await page.evaluate(()=>refresh());
    await page.locator('[data-view=health]').click();
    await page.waitForFunction(()=>document.querySelector('#healthContent .backup-health'));
    await page.evaluate(()=>refreshStorage());
    assert.deepEqual(errors,[],JSON.stringify(scenario));
    const error=await page.locator('#error').textContent();assert.equal(error,'');
    if(scenario.lang==='en'&&scenario.script==='results.js')await page.screenshot({path:path.join(path.dirname(out),'startup-health.png')});
    checks.push({...scenario,heldRequests:0,standingsRows:2,preferencesRestored:true,backupVisible:true,browserErrors:errors});
   }finally{releaseScript();await page.close()}
  }
  fs.writeFileSync(out,JSON.stringify({passed:true,checks},null,2));
  console.log('Reproduced the original error; fixed startup passed all eight languages and three delayed script positions.');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
