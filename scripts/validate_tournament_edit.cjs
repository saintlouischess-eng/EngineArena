const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/tournament-edit-ready.json','utf8'));
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const page=await browser.newPage({viewport:{width:1450,height:1050}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));await page.goto(ready.url);
  await page.waitForFunction(()=>typeof state!=='undefined'&&state.snapshot&&typeof renderTournamentEdit==='function');
  const select=async id=>{await page.locator('#tournamentPicker').selectOption(id);await page.waitForFunction(id=>state.snapshot?.id===id,id)};
  const read=async id=>page.evaluate(id=>api(`tournaments/${id}`),id);
  const open=async()=>{await page.locator('#editTournament').click();await page.waitForFunction(()=>document.querySelector('#modal').open&&document.querySelector('#editParticipants')&&!document.querySelector('#editTournament').hasAttribute('aria-busy')&&!document.querySelector('#createTournament').disabled)};
  const save=async()=>{await page.locator('#createTournament').click();try{await page.waitForFunction(()=>!document.querySelector('#modal').open,{},{timeout:8000})}catch(e){console.log(await page.evaluate(()=>({error:document.querySelector('#modal .dialog-error')?.textContent,invalid:[...document.querySelectorAll('#modal input,#modal select')].filter(e=>!e.checkValidity()).map(e=>({id:e.id,value:e.value,visible:e.getClientRects().length,message:e.validationMessage}))})));throw e}};
  await select(ready.rr);const before=await read(ready.rr);await open();
  assert.equal(await page.locator('#tname').inputValue(),'Saved RR');assert.equal(await page.locator('#tformat').inputValue(),'round_robin');
  assert.equal(await page.locator('#tseed').inputValue(),'348');assert.equal(await page.locator('#tconcurrency').inputValue(),'2');
  assert.equal(await page.locator('#topeningSource').inputValue(),'recorded');assert.equal(await page.locator('#totalPreview').textContent(),'36');
  assert.equal(await page.locator('#tannotations').isChecked(),false);
  assert.deepEqual(await page.evaluate(()=>readTc('ttc')),before.settings.time_control);
  await page.locator('#tname').fill('Cancelled edit');await page.locator('#modal [data-close]').first().click();
  assert.equal((await read(ready.rr)).name,'Saved RR');
  await open();await page.locator('#tname').fill('Renamed RR');await save();let after=await read(ready.rr);
  assert.equal(after.name,'Renamed RR');assert.equal(after.created,before.created);assert.equal(after.setup_revision,1);
  // UI must preserve every recorded control, seed, opening and hidden advanced setting.
  for(const [key,value] of Object.entries(before.settings))assert.deepEqual(after.settings[key],value,key);
  await open();await page.locator('#tcycles').fill('5');await page.locator('#tcycles').dispatchEvent('change');
  await page.waitForFunction(()=>document.querySelector('#totalPreview').textContent==='60'&&!document.querySelector('#createTournament').disabled);
  await page.screenshot({path:'test-output/tournament-edit.png'});await save();assert.equal((await read(ready.rr)).total,60);
  // Replacement profiles use the current selection, without modifying that selection on cancel/save.
  await page.evaluate(()=>{state.selected=new Set(['0','1','2']);document.querySelector('#allProfiles').checked=false});
  await open();await page.locator('#editParticipants').selectOption('library');await page.waitForFunction(()=>document.querySelector('#totalPreview').textContent==='30');
  await page.locator('#topeningSource').evaluate(e=>e.closest('details')?.setAttribute('open',''));
  await page.locator('#topeningSource').selectOption('initial');await save();after=await read(ready.rr);
  assert.equal(after.participants,3);assert.equal(after.total,30);assert.equal(after.settings.chess960,false);assert.equal(after.settings.openings.length,1);assert.equal(after.settings.opening_source,undefined);
  // Per-round KO match lengths and multiple tiebreak controls round-trip.
  await select(ready.ko);const ko=await read(ready.ko);await open();
  assert.deepEqual(await page.locator('[data-ko-round]').evaluateAll(rows=>rows.map(e=>Number(e.value))),[6,10]);
  assert.equal(await page.locator('#koPlayoffGames').inputValue(),'4');assert.equal(await page.locator('#koControlMode').inputValue(),'sequence');
  assert.deepEqual(await page.evaluate(()=>knockoutSettings().playoff_controls),ko.settings.playoff_controls);
  await page.locator('#tname').fill('Renamed KO');await save();after=await read(ready.ko);
  for(const [key,value] of Object.entries(ko.settings))assert.deepEqual(after.settings[key],value,'KO '+key);
  // Adding participants regenerates the logarithmic round table.
  await page.evaluate(()=>state.selected=new Set(['0','1','2','3','4']));await open();await page.locator('#editParticipants').selectOption('library');
  await page.waitForFunction(()=>document.querySelectorAll('[data-ko-round]').length===3&&!document.querySelector('#createTournament').disabled);
  await save();assert.equal((await read(ready.ko)).participants,5);
  await select(ready.legacy);const legacy=await read(ready.legacy);await open();
  assert.equal(await page.locator('#koTiePolicy').inputValue(),'seed');await save();assert.equal((await read(ready.legacy)).settings.knockout_tiebreak,'seed');
  // A separate caller starting the tournament while its editor is open cannot be overwritten.
  await select(ready.rr);await open();await page.evaluate(async id=>{await api(`tournaments/${id}/action`,{action:'start'});await api(`tournaments/${id}/action`,{action:'pause'})},ready.rr);
  await page.locator('#createTournament').click();await page.waitForFunction(()=>document.querySelector('#modal .dialog-error')?.textContent.includes('never started'));
  await page.locator('#modal [data-close]').first().click();await page.evaluate(()=>refreshTournament());assert.equal(await page.locator('#editTournament').isDisabled(),true);
  // Creating a new tournament still uses the library selection and fresh defaults.
  await page.locator('#newTournament').click();await page.waitForFunction(()=>document.querySelector('#modal').open&&document.querySelector('#koConfig')&&!document.querySelector('#newTournament').hasAttribute('aria-busy'));
  await page.locator('#tformat').selectOption('round_robin');await page.locator('#tname').fill('New tournament regression');await save();
  await page.waitForFunction(()=>state.snapshot.name==='New tournament regression');assert.equal(await page.evaluate(()=>state.snapshot.participants),5);
  fs.writeFileSync('test-output/tournament-edit-ui.json',JSON.stringify({errors,cancel:true,preservedSettings:true,openingReplacement:true,participantReplacement:true,koRoundControls:true,startRaceProtected:true,newTournament:true},null,2));
  assert.deepEqual(errors,[]);console.log('Tournament edit workflows passed');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
