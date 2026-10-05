// Exercise real browser input and the manager's row-refresh path in an isolated fixture.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/manager-ui-ready.json','utf8'));
 const out=process.argv.includes('--baseline')?'test-output/hover-help-before':'test-output/hover-help-fixed';
 fs.mkdirSync(out,{recursive:true});const checks=[],errors=[];
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 const page=await browser.newPage({viewport:{width:1600,height:1000}});page.on('pageerror',e=>errors.push(e.message));
 const visible=()=>page.locator('#controlHelp').isVisible();
 const delay=()=>page.waitForTimeout(500);
 const record=name=>checks.push(name);
 try{
  await page.goto(ready.url+'&lang=en');await page.waitForFunction(()=>queueData&&state.snapshot);
  await page.evaluate(async()=>{
   let q=await api('tournament-queue');
   if(!q.total){await api('tournament-queue',{action:'add',all_ready:true});q=await api('tournament-queue')}
   if(q.execution_mode!=='parallel')await api('tournament-queue',{action:'configure',revision:q.revision,execution_mode:'parallel',resources:{cpu_budget:4,memory_budget_mb:4096,concurrency:4,gpu_limits:{gpu0:1}}});
   await showQueue();
  });
  const heading=await page.locator('#pageTitle').boundingBox(),blank={x:heading.x+5,y:heading.y+5};
  const first=page.locator('[data-manager-select]').first();await first.click();
  await page.mouse.move(blank.x,blank.y);await delay();
  await page.evaluate(()=>{
   // The same renderer is invoked by live polling. A browser-only changed cell
   // forces node replacement without editing any tournament's saved results.
   window.checkedManagerId=document.activeElement.dataset.managerSelect;
   renderManagerRows({...queueData,items:queueData.items.map((item,i)=>i?item:{...item,official_games:item.official_games+1})});
  });
  await delay();await page.screenshot({path:out+'/stationary-pointer.png'});
  assert.equal(await page.evaluate(()=>document.activeElement.dataset.managerSelect===checkedManagerId),true,'Refresh keeps keyboard focus');
  assert.equal(await visible(),false,'Automatic focus restoration must not show help away from the pointer');record('Stationary pointer during manager refresh');
  await page.waitForTimeout(2400);assert.equal(await visible(),false);record('Repeated automatic polling');
  await page.locator('#managerSearch').focus();await delay();assert.equal(await visible(),false);record('Programmatic focus is silent');
  await page.keyboard.press('Tab');await delay();assert.equal(await visible(),true);record('Real keyboard navigation shows help');
  await page.keyboard.press('Escape');await delay();assert.equal(await visible(),false);record('Escape dismisses keyboard help');
  await page.locator('#managerConfigure').hover();await delay();assert.equal(await visible(),true);record('Real pointer hover shows help');
  await page.mouse.move(blank.x,blank.y);await delay();assert.equal(await visible(),false);record('Pointer leaving dismisses help');
  await page.locator('#managerConfigure').hover();await delay();await page.locator('#managerConfigure').click();
  await delay();assert.equal(await visible(),false);record('Opening dialog stays clear of hover help');
  await page.keyboard.press('Escape');await page.mouse.move(blank.x,blank.y);
  // Mount isolated controls inside the test page, using the production help code.
  await page.evaluate(()=>{
   const box=document.createElement('div');box.id='hoverTestControls';box.style.cssText='position:fixed;left:270px;top:180px;z-index:99;padding:20px;background:var(--panel)';
   box.innerHTML='<span id="helpOriginal" hidden>Original description</span><button id="helpA" aria-describedby="helpOriginal" data-help="First help">Hover A</button><button id="helpB" data-help="Second help">Hover B</button>';
   document.body.append(box);
  });
  await page.locator('#helpA').hover();await delay();assert.equal(await visible(),true);
  assert.equal(await page.locator('#helpA').getAttribute('aria-describedby'),'helpOriginal controlHelp');
  await page.mouse.move(blank.x,blank.y);assert.equal(await page.locator('#helpA').getAttribute('aria-describedby'),'helpOriginal');record('Accessible description restored');
  await page.locator('#helpA').hover();await page.waitForTimeout(100);await page.mouse.move(blank.x,blank.y);await delay();assert.equal(await visible(),false);record('Leaving before delay cancels help');
  await page.locator('#helpA').hover();await delay();await page.evaluate(()=>document.querySelector('#helpA').replaceWith(document.querySelector('#helpA').cloneNode(true)));
  await delay();assert.equal(await visible(),false);record('Replacing hovered control does not rearm stationary pointer');
  await page.mouse.move(blank.x,blank.y);await page.locator('#helpA').hover();await delay();assert.equal(await visible(),true);
  await page.evaluate(()=>document.querySelector('#helpA').style.transform='translateY(100px)');await delay();assert.equal(await visible(),false);record('Moved control cannot leave stale help');
  await page.mouse.move(blank.x,blank.y);await page.locator('#helpB').hover();await delay();assert.equal(await visible(),true);
  await page.keyboard.press('Escape');await delay();assert.equal(await visible(),false);
  await page.evaluate(()=>document.querySelector('#helpB').dispatchEvent(new PointerEvent('pointerover',{bubbles:true,pointerType:'mouse'})));
  await delay();assert.equal(await visible(),false);record('Boundary events do not reopen dismissed help');
  await page.evaluate(()=>document.querySelector('#hoverTestControls').remove());
  await page.mouse.move(blank.x,blank.y);await page.keyboard.press('Tab');await delay();
  await page.evaluate(()=>window.dispatchEvent(new Event('blur')));assert.equal(await visible(),false);record('Window blur dismisses help');
  assert.deepEqual(errors,[]);
  fs.writeFileSync(out+'/result.json',JSON.stringify({passed:true,packaged:!!ready.packaged,checks,errors},null,2));
  console.log(checks.length+' hover-help checks passed.');
 }catch(e){fs.writeFileSync(out+'/result.json',JSON.stringify({passed:false,checks,errors,failure:String(e)},null,2));throw e}
 finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
