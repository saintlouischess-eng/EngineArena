const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/events-ready.json','utf8')),browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
 const page=await browser.newPage({viewport:{width:1500,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto(ready.url);await page.waitForFunction(()=>state.snapshot&&typeof renderSprt==='function');
 await page.evaluate(ids=>state.selected=new Set(ids.slice(0,2)),ready.profiles);await page.locator('#newTournament').click();await page.locator('#tformat').selectOption('sprt');
 await page.waitForFunction(()=>document.querySelector('#sprtCandidate').textContent.includes('Engine 2'));
 await page.locator('#sprtCandidate').selectOption('1');await page.locator('#tcycles').fill('2');await page.locator('#telo0').fill('-5');await page.locator('#telo1').fill('5');await page.locator('#sprtAlpha').fill('2.5');await page.locator('#sprtBeta').fill('10');await page.locator('#tmaxplies').fill('4');await page.locator('#tconcurrency').fill('2');
 await page.evaluate(()=>{$('#tcontrol').innerHTML=tcEditor('ttc',{kind:'nodes',nodes:77});wireTc('ttc')});
 await page.locator('#sprtSetup').scrollIntoViewIfNeeded();await page.screenshot({path:'test-output/sprt-setup.png'});
 await page.waitForFunction(()=>!document.querySelector('#createTournament').disabled);await page.locator('#createTournament').click();await page.waitForFunction(()=>!$('#modal').open&&state.snapshot?.settings.format==='sprt');
 assert.equal(await page.evaluate(()=>state.snapshot.settings.sprt_candidate),1);assert.equal(await page.evaluate(()=>state.snapshot.settings.sprt.alpha),.025);
 await page.locator('#start').click();await page.waitForFunction(()=>state.snapshot?.state==='completed',{},{timeout:30000});
 assert.equal(await page.evaluate(()=>state.snapshot.sprt_status.status),'inconclusive');assert.ok((await page.locator('#sprtPanel').innerText()).includes('Engine 2'));
 await page.locator('#sprtPanel').scrollIntoViewIfNeeded();await page.screenshot({path:'test-output/sprt-inconclusive.png'});
 const tid=await page.evaluate(()=>state.tid);const report=await page.evaluate(async tid=>{const response=await fetch(`/api/tournaments/${tid}/report?token=event-review`);return {status:response.status,text:await response.text()}},tid);
 assert.equal(report.status,200);assert.ok(JSON.parse(report.text).html.includes('Inconclusive — game limit reached'));
 const snapshot=await page.evaluate(()=>state.snapshot);
 assert.equal(snapshot.sprt.samples,2);assert.deepEqual(errors,[]);
 await page.evaluate(async ids=>{const t=await api('tournaments',{name:'SPRT H0 stop',profiles:ids.slice(0,2),settings:{format:'sprt',cycles:100,concurrency:2,max_plies:4,time_control:{kind:'nodes',nodes:77},sprt:{elo0:0,elo1:200,alpha:.05,beta:.05}}});state.tid=t.id;await loadTournaments();await refreshTournament()},ready.profiles);
 await page.locator('#start').click();await page.waitForFunction(()=>state.snapshot?.state==='paused'&&state.snapshot.sprt?.frozen,{},{timeout:30000});await page.evaluate(()=>updateRunControls());assert.equal(await page.locator('#start').isDisabled(),true);assert.equal(await page.evaluate(()=>state.snapshot.sprt.decision),'H0');
 await page.locator('#sprtPanel').scrollIntoViewIfNeeded();await page.screenshot({path:'test-output/sprt-stopped.png'});assert.deepEqual(errors,[]);
 fs.writeFileSync('test-output/sprt-ui.json',JSON.stringify({errors,games:snapshot.official_games,samples:snapshot.sprt.samples,candidate:snapshot.sprt_status.candidate,alpha:snapshot.settings.sprt.alpha,beta:snapshot.settings.sprt.beta,decision:snapshot.sprt_status.status,reportEndpoint:report.status},null,2));
 console.log('SPRT setup, candidate, risk targets, live status and inconclusive finish passed.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
