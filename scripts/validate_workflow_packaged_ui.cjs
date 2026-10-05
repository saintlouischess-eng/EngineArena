const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/workflow-native-ui-ready.json')),out='test-output/workflow-packaged-ui';fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--enable-unsafe-swiftshader']}),errors=[],views=[];
 try{
  const page=await browser.newPage();page.on('pageerror',e=>errors.push(e.stack));
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await page.setViewportSize({width:lang==='en'?1600:1050,height:900});await page.goto(ready.url+'&lang='+lang);await page.waitForFunction(()=>state.snapshot);
   await page.evaluate(async r=>{state.tid=r.tid;await refreshTournament();await showFinalGame(r.gid);displayPrefs.focus3d=true;displayPrefs.theme=ArenaI18n.locale==='de'?'light':'dark';displayPrefs.panels={focus:{maximized:true,visible:true},moves:{visible:true},standings:{visible:false},games:{visible:false},search:{visible:false},live:{visible:false}};applyDisplay()},ready);
   await page.waitForFunction(()=>document.querySelector('.board-3d')?.dataset.frames>0&&moveSheet.data?.attempt?.ended);
   await page.locator('[data-zoom=reset]').click();await page.locator('[data-zoom=in]').click();assert.equal(await page.locator('[data-zoom=reset]').textContent(),'110%');
   await page.locator('[data-zoom=out]').click();assert.equal(await page.locator('[data-zoom=reset]').textContent(),'100%');
   await page.locator('[data-lift=reset]').click();await page.locator('[data-lift=up]').click();assert.equal(await page.locator('#board3dLift').inputValue(),'5');await page.locator('[data-lift=down]').click();assert.equal(await page.locator('#board3dLift').inputValue(),'0');
   const camera=await page.evaluate(()=>structuredClone(displayPrefs.camera3d));await page.locator('#toggleBoard3dControls').click();assert.equal(await page.locator('.board-3d-controls').isVisible(),false);await page.locator('#toggleBoard3dControls').click();assert(await page.locator('.board-3d-controls').isVisible());assert.deepEqual(await page.evaluate(()=>displayPrefs.camera3d),camera);
   await page.evaluate(()=>displayDialog());await page.locator('#displayHoverHelp').uncheck();assert.equal(await page.locator('#modal .modal-foot').evaluate(el=>el.scrollWidth>el.clientWidth+1),false);await page.locator('#applyDisplay').click();await page.waitForFunction(()=>!document.querySelector('#modal').open);assert.equal(await page.evaluate(()=>displayPrefs.hoverHelp),false);
   await page.locator('#toggleBoard3dControls').hover();await page.waitForTimeout(400);assert.equal(await page.locator('#controlHelp').isVisible(),false);
   await page.evaluate(()=>displayDialog());await page.locator('#displayHoverHelp').check();await page.locator('#applyDisplay').click();await page.waitForFunction(()=>!document.querySelector('#modal').open);
   assert(await page.locator('.board-3d-controls').evaluate(el=>{const a=el.getBoundingClientRect(),b=el.parentElement.getBoundingClientRect();return a.left>=b.left&&a.right<=b.right&&el.scrollWidth<=el.clientWidth}),'Zoom controls must fit inside the board');
   assert.equal(await page.locator('.board-3d-labels').count(),0);assert.equal(await page.locator('.board-3d').getAttribute('data-coordinate-count'),'16');assert.equal(await page.evaluate(()=>document.querySelector('.focus-last-move').textContent.includes(moveSheet.data.items.at(-1).san)),true);
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);assert.equal(overflow,false);
   await page.screenshot({path:out+'/'+lang+'-3d.png'});
   await page.evaluate(()=>{displayPrefs.panels.focus={visible:false};displayPrefs.panels.moves={visible:true,maximized:true};applyDisplay()});
   await page.waitForFunction(()=>moveSheet.rows.length>0);assert.equal(await page.locator('.scoresheet tbody tr').count(),44);await page.screenshot({path:out+'/'+lang+'-moves.png'});
   await page.evaluate(()=>quickMatch());await page.waitForFunction(()=>document.querySelector('#quickEngine1')?.options.length>=2);await page.locator('#quickReview').click();await page.waitForSelector('#createTournament');
   const dialogOverflow=await page.locator('#modal .modal-body').evaluate(el=>el.scrollWidth>el.clientWidth+1);assert.equal(dialogOverflow,false);await page.screenshot({path:out+'/'+lang+'-quick.png'});await page.locator('#modal [data-close]').first().click();
   views.push({language:lang,width:lang==='en'?1600:1050,overflow,dialogOverflow,recordedMoves:44,coordinates:16,zoomButtons:true,verticalFraming:true,controlsToggle:true,hoverHelpToggle:true});
  }
  assert.deepEqual(errors,[]);fs.writeFileSync(out+'/result.json',JSON.stringify({passed:true,packaged:true,errors,views},null,2));console.log('Packaged 3D, scoresheet and Quick match checked in all eight languages.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
