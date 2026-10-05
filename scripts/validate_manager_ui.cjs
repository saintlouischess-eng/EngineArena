const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/manager-ui-ready.json','utf8'));
 const browser=await chromium.launch({headless:true,channel:'msedge'}),errors=[],evidence=[];
 const out='test-output/manager-ui';fs.mkdirSync(out,{recursive:true});
 fs.writeFileSync(out+'/acceptance.json',JSON.stringify({passed:false,workspace:ready.folder,packaged:!!ready.packaged}));
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1000}});page.on('pageerror',e=>errors.push(e.message));
  await page.goto(ready.url);await page.waitForFunction(()=>state.snapshot&&queueData);
  await page.locator('[data-view=tournamentQueue]').click();await page.locator('#queueAddAll').click();
  await page.waitForFunction(()=>queueData?.total===5&&!queueMutating);
  assert.equal(await page.locator('[data-execution-mode=sequential]').getAttribute('aria-pressed'),'true');
  await page.screenshot({path:out+'/sequential-dark.png'});
  await page.locator('[data-execution-mode=parallel]').click();assert.equal(await page.locator('#managerMode').inputValue(),'parallel');
  await page.locator('#managerCpu').fill('4');await page.locator('#managerMemory').fill('4096');await page.locator('#managerGames').fill('4');await page.locator('#managerGpu').fill('gpu0:1');
  await page.locator('#managerSave').click();await page.waitForFunction(()=>!document.querySelector('#modal').open&&queueData.execution_mode==='parallel');
  await page.locator('#managerSelectPage').check();await page.locator('#managerLimits').click();await page.locator('#managerPriority').selectOption('4');
  await page.locator('#managerLimit').fill('1');await page.locator('#managerApplyLimits').click();await page.waitForFunction(()=>!document.querySelector('#modal').open);
  assert.equal(await page.locator('#queueRows td:nth-child(6)').allTextContents().then(xs=>xs.every(x=>x==='High')),true);
  await page.locator('#managerSelectPage').uncheck();await page.locator('[data-manager-sort=name]').click();
  await page.waitForFunction(()=>queueData.sort==='name'&&!queueLoading);assert.match(await page.locator('[data-qview]').first().textContent(),/CPU reference/);
  await page.locator('#managerSearch').fill('GPU');await page.waitForFunction(()=>queueData.filtered_total===1&&!queueLoading);
  await page.locator('#managerSearch').fill('');await page.waitForFunction(()=>queueData.filtered_total===5&&!queueLoading);
  await page.locator('#queueRun').click();await page.waitForFunction(()=>new Set(state.live.map(g=>g.tid)).size>=3);
  await page.waitForFunction(()=>queueData.items.filter(x=>x.active_games>0).length>=3);
  assert.equal(await page.locator('[data-execution-mode=sequential]').isDisabled(),true);
  assert.equal(await page.locator('[data-execution-mode=parallel]').getAttribute('aria-pressed'),'true');
  const focusId=ready.ids[1];await page.locator(`[data-manager-settings="${focusId}"]`).focus();
  await page.waitForTimeout(2300);
  assert.equal(await page.evaluate(()=>document.activeElement?.dataset.managerSettings),focusId);
  await page.screenshot({path:out+'/running-dark.png'});
  const pauseRow=page.locator(`[data-queue-row="${ready.ids[0]}"]`);await pauseRow.locator('[data-manager-action=pause_selected]').click();
  await page.waitForFunction(id=>!queueMutating&&!state.live.some(g=>g.tid===id)&&queueData.items?.find(x=>x.tid===id)?.held&&queueData.items.find(x=>x.tid===id)?.state==='paused',ready.ids[0]);
  assert.equal(await page.evaluate(()=>queueData.mode),'running');assert.ok(await page.evaluate(()=>state.live.length)>0);
  await pauseRow.locator('[data-manager-action=resume_selected]').click();await page.waitForFunction(id=>state.live.some(g=>g.tid===id),ready.ids[0]);
  await page.locator('[data-view=overview]').click();await page.locator('#boardCount').selectOption('8');await page.locator('#liveTournamentScope').selectOption('all');
  await page.waitForFunction(()=>document.querySelectorAll('#liveBoards .tournament-label').length>=3);
  assert.ok(new Set(await page.locator('#liveBoards .tournament-label').allTextContents()).size>=3);
  await page.locator('[data-view=tournamentQueue]').click();await page.locator('#queuePause').click();
  await page.waitForFunction(()=>queueData.mode==='paused'&&!state.live.length&&queueData.running===0,null,{timeout:30000});
  await page.reload();await page.waitForFunction(()=>queueData?.execution_mode==='parallel');
  assert.equal(await page.locator('#liveTournamentScope').inputValue(),'all');
  await page.locator('[data-view=tournamentQueue]').click();
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await page.goto(ready.url+'&lang='+lang);await page.waitForFunction(()=>state.snapshot&&queueData);
   await page.evaluate(async()=>{window.missingMessages=new Set();ArenaI18n.capture(key=>{if(ArenaI18n.locale!=='en'&&!Object.hasOwn(window.ARENA_MESSAGES,key))missingMessages.add(key)});displayPrefs.fontSize=20;applyDisplay();await showQueue()});
   await page.locator('#managerConfigure').click();await page.locator('#managerMode').selectOption('parallel');
   for(const width of [1050,1600])for(const theme of ['dark','light']){
    await page.setViewportSize({width,height:1000});await page.evaluate(theme=>document.body.classList.toggle('light',theme==='light'),theme);
    const result=await page.evaluate(()=>({language:ArenaI18n.locale,missing:[...missingMessages],overflow:document.documentElement.scrollWidth>innerWidth+1,dialogOverflow:document.querySelector('#modal').scrollWidth>document.querySelector('#modal').clientWidth+2}));
    assert.deepEqual(result.missing,[]);assert.equal(result.overflow,false);assert.equal(result.dialogOverflow,false);evidence.push({width,theme,...result});
   }
   await page.keyboard.press('Escape');await page.locator('#managerFilter').selectOption('paused');await page.locator('#managerFilter').selectOption('');
   await page.waitForFunction(()=>!queueLoading);
   await page.locator('#managerSelectPage').check();await page.locator('#managerLimits').click();
   assert.deepEqual(await page.evaluate(()=>[...missingMessages]),[]);await page.keyboard.press('Escape');
   await page.locator('[data-manager-settings]').first().click();assert.deepEqual(await page.evaluate(()=>[...missingMessages]),[]);await page.keyboard.press('Escape');
   if(['en','de','pl'].includes(lang)){
    await page.setViewportSize({width:1050,height:1000});await page.screenshot({path:out+`/manager-${lang}-laptop.png`});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
   }
  }
  assert.deepEqual(errors,[]);fs.writeFileSync(out+'/acceptance.json',JSON.stringify({passed:true,workspace:ready.folder,packaged:!!ready.packaged,errors,views:evidence,bulkLimits:true,sort:true,search:true,individualPause:true,allBoards:true,pauseAll:true,reload:true,keyboardFocus:true},null,2));
  console.log('Manager workflow and 32 translated/theme/size dialog layouts passed.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
