// Slow acknowledgements, repeat clicks, server rejection and successful save feedback.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync(process.argv.includes('--manager')?'test-output/manager-ui-ready.json':'test-output/tournament-edit-ready.json','utf8'));
 const browser=await chromium.launch({headless:true,channel:'msedge'}),out='test-output/setup-save-ui',errors=[];fs.mkdirSync(out,{recursive:true});
 try{
  const page=await browser.newPage({viewport:{width:1450,height:1000}});page.on('pageerror',e=>errors.push(e.message));
  await page.goto(ready.url+'&lang=en');await page.waitForFunction(()=>state.snapshot&&queueData);
  const before=await page.evaluate(async()=>{await loadEngines();state.selected=new Set(state.engines.slice(0,2).map(x=>x.id));document.querySelector('#allProfiles').checked=false;return (await api('tournaments')).length});
  await page.locator('#newTournament').click();await page.waitForFunction(()=>document.querySelector('#createTournament')&&!document.querySelector('#createTournament').disabled);
  await page.locator('#tname').fill('Clear save confirmation');
  let sent=0,release;const gate=new Promise(r=>release=r);
  await page.route('**/api/tournaments',async route=>{if(route.request().method()!=='POST')return route.continue();sent++;const response=await route.fetch();await gate;await route.fulfill({response})});
  await page.locator('#createTournament').click();await page.waitForFunction(()=>document.querySelector('.tournament-save-status')?.textContent==='Saving tournament…');
  assert.equal(await page.locator('#createTournament').textContent(),'Saving…');assert.equal(await page.locator('#tname').isDisabled(),true);
  assert.equal(await page.locator('#modal [data-close]').first().isDisabled(),true);
  await page.keyboard.press('Escape');assert.equal(await page.locator('#modal').evaluate(el=>el.open),true);
  await page.locator('#createTournament').evaluate(el=>{el.click();el.click()});await page.screenshot({path:out+'/saving.png'});
  release();await page.waitForFunction(()=>!document.querySelector('#modal').open&&state.snapshot?.name==='Clear save confirmation');assert.equal(sent,1);
  assert.match(await page.locator('#notice').textContent(),/Saved “Clear save confirmation” — .*Paused and ready to run/);
  assert.equal(await page.evaluate(()=>(state.snapshot.state)),'paused');assert.equal(await page.evaluate(async()=>(await api('tournaments')).length),before+1);
  await page.screenshot({path:out+'/saved.png'});await page.unroute('**/api/tournaments');
  await page.locator('#editTournament').click();await page.waitForFunction(()=>document.querySelector('#editParticipants')&&!document.querySelector('#createTournament').disabled);
  await page.locator('#tname').fill('Edited confirmation');await page.locator('#createTournament').click();await page.waitForFunction(()=>!document.querySelector('#modal').open&&state.snapshot?.name==='Edited confirmation');
  assert.match(await page.locator('#notice').textContent(),/Saved “Edited confirmation”/);
  await page.locator('#newTournament').click();await page.waitForFunction(()=>document.querySelector('#createTournament')&&!document.querySelector('#createTournament').disabled);
  await page.locator('#tname').fill('Keep my input');await page.route('**/api/tournaments',async route=>route.request().method()==='POST'?route.fulfill({status:400,contentType:'application/json',body:JSON.stringify({error:'Validation test rejection'})}):route.continue());
  await page.locator('#createTournament').click();await page.waitForFunction(()=>document.querySelector('#modal .dialog-error')?.textContent==='Validation test rejection');
  assert.equal(await page.locator('#tname').inputValue(),'Keep my input');assert.equal(await page.locator('#tname').isDisabled(),false);assert.equal(await page.locator('#createTournament').isDisabled(),false);
  assert.equal(await page.locator('.tournament-save-status').count(),0);assert.equal(await page.locator('#modal').evaluate(el=>el.open),true);assert.equal(await page.evaluate(async()=>(await api('tournaments')).length),before+1);
  await page.keyboard.press('Escape');assert.equal(await page.locator('#modal').evaluate(el=>el.open),false);
  await page.unroute('**/api/tournaments');
  await page.evaluate(()=>showQueue());await page.screenshot({path:out+'/manager.png'});
  if(ready.packaged){
   const tid=await page.evaluate(()=>state.tid);await page.locator('#queueAddSelected').click();await page.waitForFunction(id=>!queueMutating&&queueData.items.some(x=>x.tid===id),tid);
   await page.locator(`[data-manager-settings="${tid}"]`).click();assert.equal(await page.locator('#managerEditSetup').isEnabled(),true);
   await page.locator('#managerEditSetup').click();await page.waitForFunction(()=>document.querySelector('#createTournament')&&!document.querySelector('#createTournament').disabled);
   await page.locator('#tname').fill('Edited from manager options');await page.locator('#createTournament').click();await page.waitForFunction(()=>!document.querySelector('#modal').open&&state.snapshot?.name==='Edited from manager options');
   await page.locator('[data-view=tournamentQueue]').click();await page.locator(`[data-manager-settings="${tid}"]`).click();await page.locator('#managerRemoveEntry').click();await page.waitForFunction(()=>!document.querySelector('#modal').open&&!queueMutating);
   assert.equal(await page.evaluate(id=>queueData.items.some(x=>x.tid===id),tid),false);assert.equal(await page.evaluate(async id=>(await api(`tournaments/${id}`)).name,tid),'Edited from manager options');
  }
  assert.deepEqual(errors,[]);fs.writeFileSync(out+'/result.json',JSON.stringify({passed:true,packaged:!!ready.packaged,errors,duplicateClicks:sent,busyFeedback:true,escapeWhileSaving:true,createCloses:true,editCloses:true,confirmation:true,rejectedSavePreservesInput:true},null,2));
  console.log('Tournament save feedback, repeat-click protection, edit and validation recovery passed.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
