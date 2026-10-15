// Real UI, audio decoding/playback and resize regression on a disposable worker.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const ready=JSON.parse(fs.readFileSync('test-output/workflow-ready.json','utf8'));
assert(ready.long&&ready.folder.includes('test-output'));
const packaged=process.argv.includes('--package-assets'),out=`test-output/focus-sound-${packaged?'package':'source'}`;
fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--use-angle=swiftshader']}),errors=[],proof={passed:false,packaged,checks:[]};
 try{
  const page=await browser.newPage({viewport:{width:1586,height:993}});page.on('pageerror',e=>errors.push(e.stack));
  if(packaged)await page.route('**/assets/**',async route=>{
   const relative=decodeURIComponent(new URL(route.request().url()).pathname.slice('/assets/'.length)),root=path.resolve('release/EngineArena/worker/_internal/ui'),file=path.resolve(root,relative);
   assert(file.startsWith(root+path.sep));await route.fulfill({path:file});
  });
  await page.addInitScript(()=>{
   window.audioStarts=0;const Native=window.AudioContext;
   window.AudioContext=class extends Native{createBufferSource(){const source=super.createBufferSource(),start=source.start.bind(source);source.start=(...args)=>{window.audioStarts++;return start(...args)};return source}};
  });
  await page.goto(ready.url);await page.waitForFunction(()=>moveSheet.rows.length&&!moveSheet.busy);
  await page.evaluate(()=>{
   displayPrefs.fontSize=20;displayPrefs.split=74;displayPrefs.focusSound=true;displayPrefs.focusSoundVolume=40;
   displayPrefs.panels.moves={visible:true,height:442};displayPrefs.panels.focus={visible:true,height:740,column:'left'};applyDisplay();sheetLatest();
  });
  const settle=async()=>{await page.waitForFunction(()=>!moveSheet.busy&&!moveSheet.scrollLock);await page.waitForTimeout(200)};
  const heard=()=>page.evaluate(()=>audioStarts);
  // Explicit user gesture unlocks real Web Audio, including WAV decode/source start.
  await page.locator('#focusSound').click();await page.locator('#focusSoundTest').click();await page.waitForFunction(()=>audioStarts>0);await page.locator('#modal [data-close]').first().click();
  const step=async(expectSound=true)=>{
   const before=await page.evaluate(()=>({ply:retainedFocus.ply,audio:audioStarts}));
   await page.request.post(new URL('/fixture/step',ready.url).href);await page.waitForFunction(p=>retainedFocus.ply>p,before.ply);await settle();
   if(expectSound)await page.waitForFunction(n=>audioStarts===n+1,before.audio);else assert.equal(await heard(),before.audio);
  };
  const followed=async()=>{await settle();assert.equal(await page.evaluate(()=>moveSheet.follow),true);assert(await page.locator('.scoresheet-scroll').evaluate(e=>e.scrollHeight-e.scrollTop-e.clientHeight<2))};
  const resize=async key=>{const grip=page.locator('[data-panel=focus] .focus-resizer');await grip.focus();await page.keyboard.press(key);await settle();await step();await followed()};
  await followed();await step();proof.checks.push('real WAV decoding and move audio');
  for(const mode of ['2d','3d']){
   await page.evaluate(mode=>{displayPrefs.focus3d=mode==='3d';renderFocus()},mode);
   if(mode==='3d')await page.waitForFunction(()=>board3dInstance);
   await resize('ArrowUp');await resize('ArrowDown');
   await page.locator('[data-panel=focus] [data-float]').click();await settle();
   // Real corner dragging, including pointer capture, must not mute future moves.
   const grip=await page.locator('[data-panel=focus] .focus-resizer').boundingBox();
   await page.mouse.move(grip.x+grip.width/2,grip.y+grip.height/2);await page.mouse.down();await page.mouse.move(grip.x-90,grip.y-90,{steps:12});await page.mouse.up();await settle();await step();await followed();
   await resize('ArrowRight');await resize('ArrowDown');
   for(const size of [{width:1100,height:800},{width:1800,height:1200},{width:1586,height:993}]){await page.setViewportSize(size);await settle();await step();await followed()}
   for(let i=0;i<2;i++){await page.locator('[data-panel=focus] [data-expand]').click();await settle();await step();await followed()}
   await page.locator('[data-panel=focus] [data-float]').click();await settle();await step();await followed();
   proof.checks.push(`${mode}: docked/floating resize, corner drag, app resize, expand/restore`);
  }
  await page.evaluate(()=>panels.moves.style.height='300px');await settle();await step();await followed();
  await page.evaluate(()=>panels.moves.style.height='900px');await settle();await step();await followed();
  proof.checks.push('viewport growth does not become history browsing');
  await page.evaluate(()=>{displayPrefs.focus3d=false;renderFocus()});
  const scroll=page.locator('.scoresheet-scroll');await scroll.scrollIntoViewIfNeeded();await scroll.hover();await page.mouse.wheel(0,-250);await page.waitForFunction(()=>!moveSheet.follow);await step();
  assert.equal(await page.evaluate(()=>reviewingRecordedMove()),false);proof.checks.push('reading scoresheet leaves live-board audio enabled');
  const row=page.locator('.scoresheet tbody button').last();await row.click();await page.waitForFunction(()=>reviewingRecordedMove());const fen=await page.evaluate(()=>gameMovesView(retainedFocus).fen);await step(false);
  await page.setViewportSize({width:1450,height:1000});await settle();assert.equal(await page.evaluate(()=>gameMovesView(retainedFocus).fen),fen);assert.equal(await page.evaluate(()=>moveSheet.follow),false);
  await step(false);const quiet=await heard();await page.locator('#movesLatest').click();await settle();assert.equal(await heard(),quiet);await step();proof.checks.push('actual replay stays quiet and selected; Return to live resumes next move');
  await page.evaluate(()=>{panels.focus.hidden=true});await step(false);await page.evaluate(()=>{panels.focus.hidden=false;renderFocus()});await step();
  await page.evaluate(()=>{displayPrefs.focusSound=false});await step(false);await page.evaluate(()=>{displayPrefs.focusSound=true});await step();
  const count=await heard();await page.evaluate(()=>{for(let i=0;i<100;i++)renderFocus()});await settle();assert.equal(await heard(),count);proof.checks.push('hidden/muted boards quiet; repeated renders do not duplicate audio');
  await page.screenshot({path:out+'/verified.png'});assert.deepEqual(errors,[]);proof.audioStarts=await heard();proof.passed=true;
 }finally{await browser.close();fs.writeFileSync(out+'/result.json',JSON.stringify({...proof,errors},null,2)+'\n')}
 console.log(JSON.stringify(proof,null,2));
})().catch(e=>{console.error(e);process.exitCode=1});
