const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/tournament-edit-ready.json','utf8'));
 const browser=await chromium.launch({headless:true,channel:'msedge'}),out='test-output/setup-workflow-ui';fs.mkdirSync(out,{recursive:true});
 try{
  const page=await browser.newPage({viewport:{width:1450,height:1050}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(ready.url+'&lang=en');await page.waitForFunction(()=>state.snapshot&&queueData);
  await page.evaluate(async()=>{const d=await api('setup-draft');await api('setup-draft',{revision:d.revision,value:null});state.selected=new Set(['0','1','2']);document.querySelector('#allProfiles').checked=false});
  await page.locator('#newTournament').click();await page.waitForSelector('#setupEngineRows tr');
  await page.locator('#tformat').selectOption('gauntlet');await page.locator('[data-candidate="2"]').check();
  await page.locator('#tname').fill('Named candidate test');await page.locator('[data-tolerance="0.25"]').click();
  await page.locator('#tcycles').fill('3');await page.locator('#tcycles').dispatchEvent('change');
  await page.waitForFunction(()=>document.querySelector('#totalPreview').textContent==='12');
  await page.waitForFunction(()=>document.querySelector('#setupDraftStatus').textContent==='Draft saved — safe to close');
  await page.screenshot({path:out+'/gauntlet.png'});
  await page.locator('#setupLibrary').click();await page.locator('#newTournament').click();await page.waitForSelector('#setupEngineRows tr');
  assert.equal(await page.locator('#tname').inputValue(),'Named candidate test');assert.equal(await page.locator('[data-candidate="2"]').isChecked(),true);
  await page.reload();await page.waitForFunction(()=>state.snapshot&&queueData);await page.locator('#newTournament').click();await page.waitForSelector('#setupEngineRows tr');
  assert.equal(await page.locator('#ttolerance').inputValue(),'0.25');assert.equal(await page.locator('#tcycles').inputValue(),'3');
  await page.waitForFunction(()=>!document.querySelector('#createTournament').disabled);await page.locator('#createTournament').click();
  await page.waitForFunction(()=>!document.querySelector('#modal').open&&state.snapshot?.name==='Named candidate test');
  const created=await page.evaluate(async()=>({tid:state.tid,roles:await api('selected-participants',{recorded_participants:state.tid}),draft:await api('setup-draft')}));
  assert.deepEqual(created.roles.map(p=>p.id),['2','0','1']);assert.equal(created.draft.value,null);
  await page.locator('#editTournament').click();await page.waitForSelector('#setupEngineRows tr');assert.equal(await page.locator('[data-candidate="2"]').isChecked(),true);
  await page.keyboard.press('Escape');
  // Staged clock and KO dynamic rows survive closing, including a custom tie sequence.
  await page.locator('#newTournament').click();await page.waitForSelector('#setupEngineRows tr');
  await page.locator('#tformat').selectOption('knockout');await page.locator('#ttc [data-tc=kind]').selectOption('staged');
  await page.locator('#ttc .stage-row [data-stage=seconds]').first().fill('83');await page.locator('#ttc [data-tc=repeat]').check();
  await page.locator('#koControlMode').selectOption('sequence');await page.locator('#koShorterPreset').click();await page.locator('[data-ko-round="0"]').fill('6');
  await page.waitForFunction(()=>document.querySelector('#setupDraftStatus').textContent==='Draft saved — safe to close');await page.keyboard.press('Escape');
  await page.locator('#newTournament').click();await page.waitForSelector('#setupEngineRows tr');
  assert.equal(await page.locator('#ttc .stage-row [data-stage=seconds]').first().inputValue(),'83');assert.equal(await page.locator('[data-ko-round="0"]').inputValue(),'6');assert.equal(await page.locator('#koStages .tc-editor').count(),3);
  await page.locator('#setupFresh').click();await page.waitForFunction(()=>document.querySelector('#tformat')?.value==='match');await page.waitForSelector('#setupEngineRows tr');assert.equal(await page.locator('#tformat').inputValue(),'match');
  await page.keyboard.press('Escape');
  // Give two fixture profiles different advertised resource limits.
  await page.evaluate(async()=>{for(const [id,max] of [['0',64],['1',1]]){const p=(await api('profiles?limit=5')).items.find(p=>p.id===id);p.advertised={Threads:{name:'Threads',type:'spin',default:1,min:1,max,var:[]},SyzygyPath:{name:'SyzygyPath',type:'string',default:'',min:null,max:null,var:[]}};p.options={Threads:1};await api('profiles',{...p,discover:false})}state.selected=new Set(['0','1']);view('engines')});
  await page.locator('#bulkEngine').click();await page.waitForSelector('#bulkEditor');await page.locator('#bulkUseThreads').check();await page.locator('#bulkThreads').fill('4');await page.locator('#bulkUseTb').check();await page.locator('#bulkTb').fill('C:\\test tables');await page.locator('#bulkReview').click();await page.waitForSelector('#bulkRows tr');
  assert.match(await page.locator('#bulkSummary').textContent(),/2 profiles will change; 1/);await page.screenshot({path:out+'/bulk-preview.png'});
  await page.locator('#applyBulk').click();await page.waitForFunction(()=>!document.querySelector('#modal').open);
  const profiles=await page.evaluate(async()=>(await api('profiles?limit=5')).items);assert.equal(profiles.find(p=>p.id==='0').threads,4);assert.equal(profiles.find(p=>p.id==='1').threads,1);assert.equal(profiles.find(p=>p.id==='1').options.SyzygyPath,'C:\\test tables');
  assert.deepEqual(errors,[]);fs.writeFileSync(out+'/result.json',JSON.stringify({passed:true,created,errors,draftRestart:true,gauntletNames:true,stagedKoRestore:true,bulkRanges:true},null,2));console.log('Setup workflow browser checks passed');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
