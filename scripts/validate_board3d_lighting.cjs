// Visual lighting review against an isolated fixture or a packaged fixture copy.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const ready=JSON.parse(fs.readFileSync(process.env.ARENA_LIGHTING_READY||'test-output/workflow-ready.json','utf8'));
const baseline=process.argv.includes('--baseline'),out=process.env.ARENA_LIGHTING_OUT||'test-output/lighting-'+(baseline?'before':'after');
assert(ready.folder.includes('test-output')&&path.basename(ready.folder).startsWith('workflow-'));fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--enable-unsafe-swiftshader']}),errors=[],proof={passed:false,views:[]};
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1100}});page.on('pageerror',e=>errors.push(e.stack));
  if(baseline)await page.route('**/assets/board3d-studio.js',r=>r.fulfill({body:fs.readFileSync('test-output/board3d-studio-before-v158.js','utf8'),contentType:'text/javascript'}));
  await page.goto(ready.url);await page.waitForFunction(()=>state.snapshot);
  await page.evaluate(async()=>{displayPrefs.focus3d=false;renderFocus();await ArenaBoard3D.prepare();const canvas=document.createElement('canvas');canvas.id='lightingReview';canvas.style='position:fixed;inset:0;width:100vw;height:100vh;z-index:9999';document.body.append(canvas);window.lightingBoard=ArenaBoard3D.create(canvas,()=>{});});
  const full='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
  const views=[['default',full,{angle:50,orbit:0},false],['angled',full,{angle:42,orbit:22},false],['light',full,{angle:50,orbit:0},true],['reverse',full,{angle:38,orbit:180},false],['overhead',full,{angle:78,orbit:-80},false],['low',full,{angle:25,orbit:-45},false],['pieces','8/8/8/8/1rnbqk2/1RNBQK2/8/8 w - - 0 1',{angle:32,orbit:15,zoom:1.4},false],['empty','8/8/8/8/8/8/8/8 w - - 0 1',{angle:50,orbit:0},false]];
  for(const [name,fen,prefs,light] of views){
   await page.evaluate(({fen,prefs,light})=>lightingBoard.render(fen,false,prefs,light,'',fen.startsWith('rnbqkbnr/')?['g1','h1','g8','h8']:[]),{fen,prefs,light});
   assert.equal(await page.locator('#lightingReview').evaluate(c=>c.getContext('webgl2').getError()),0);
   assert.equal(await page.locator('#lightingReview').getAttribute('data-coordinate-count'),'16');
   if(fen===full)assert.equal(await page.locator('#lightingReview').getAttribute('data-crown-count'),'4');
   await page.screenshot({path:out+'/'+name+'.png'});proof.views.push(name);
  }
  const frames=await page.locator('#lightingReview').getAttribute('data-frames');await page.waitForTimeout(2200);assert.equal(await page.locator('#lightingReview').getAttribute('data-frames'),frames);proof.idleNoRedraw=true;
  await page.evaluate(()=>{lightingBoard.dispose();document.querySelector('#lightingReview').remove()});
  assert.deepEqual(errors,[]);proof.passed=true;
 }finally{await browser.close();fs.writeFileSync(out+'/result.json',JSON.stringify({...proof,errors},null,2))}
 console.log('Lighting views, stamps, coordinates and idle rendering passed: '+out);
})().catch(e=>{console.error(e);process.exitCode=1});
