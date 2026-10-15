// Offline browser regression: real presentation scripts, recorded read-only data.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const folder=process.argv[2]||'test-output/custom-season-20261014';
const read=p=>fs.readFileSync(p,'utf8');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--disable-gpu']});
 const errors=[],report={passed:false};
 try{
  const p=await browser.newPage({viewport:{width:1400,height:1000}});p.on('pageerror',e=>errors.push(e.message));
  // No live worker or browser account is accessed by this fixture.
  await p.setContent('<button id="newEvent"></button><div id="siPanel-overview"></div><button id="eventRun"></button>');
  await p.addScriptTag({content:`
   const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
   const ArenaI18n={t:v=>v,message:v=>v,locale:'en'};
   const ArenaText={number:v=>String(v)};
   const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
   const tcText=t=>t.seconds+'s + '+t.increment+'s';
   const safely=fn=>fn;
   function renderEventDetail(){} function showEvent(){} function eventReport(){}
   let eventDetailData;
   ${read('ui/app.js').split('\n').find(l=>l.startsWith('function stableHtml('))}
  `});
  await p.addScriptTag({content:read('ui/season-insights.js')});
  await p.addScriptTag({content:read('ui/circuits.js')});
  const e=JSON.parse(read(path.join(folder,'event-latest.json'))),d=JSON.parse(read(path.join(folder,'insights-sample.json')));
  await p.evaluate(({e,d})=>{eventDetailData=e;window.sample=d;for(let i=0;i<50;i++)renderSeasonOverview(d)},{e,d});
  assert.equal(await p.locator('.cx-desk').count(),1);
  assert.equal(await p.locator('#cxSaveTemplate').count(),1);
  await p.locator('.cx-desk summary').click();await p.locator('#cxSaveTemplate').focus();
  await p.evaluate(()=>{for(let i=0;i<50;i++)renderSeasonOverview(sample)});
  assert.equal(await p.locator('.cx-desk details').evaluate(el=>el.open),true);
  assert.equal(await p.locator('#cxSaveTemplate').evaluate(el=>el===document.activeElement),true);
  await p.evaluate(()=>{eventDetailData.official_games=2;sample.official=2;sample.all_official=2;renderSeasonOverview(sample)});
  assert.equal(await p.locator('.cx-desk').count(),1);
  assert.match(await p.locator('.cx-desk').textContent(),/2 \/ 152 games/);
  assert.equal(await p.locator('.cx-desk details').evaluate(el=>el.open),true);
  assert.equal(await p.locator('#cxSaveTemplate').evaluate(el=>el===document.activeElement),true);
  await p.locator('.cx-desk summary').click();
  await p.evaluate(()=>{eventDetailData.official_games=4;renderSeasonOverview(sample)});
  assert.equal(await p.locator('.cx-desk details').evaluate(el=>el.open),false);
  await p.evaluate(()=>{delete eventDetailData.circuit_state;renderSeasonOverview(sample)});
  assert.equal(await p.locator('.cx-desk').count(),0);
  assert.equal(await p.locator('.si-hero').count(),1);
  // Prove that the former append-on-every-poll path reproduces the live defect.
  await p.evaluate(e=>{eventDetailData=e;for(let i=0;i<5;i++){circuitOverview(sample);$('#siPanel-overview').insertAdjacentHTML('afterbegin',circuitPath(e))}},e);
  report.former_path_duplicates=await p.locator('.cx-desk').count();assert.equal(report.former_path_duplicates,5);
  await p.evaluate(()=>renderSeasonOverview(sample));assert.equal(await p.locator('.cx-desk').count(),1);
  for(const file of ['style.css','events.css','season-insights.css','circuits.css'])await p.addStyleTag({content:read('ui/'+file)});
  await p.screenshot({path:path.join(folder,'circuit-refresh-fixed.png'),fullPage:true});
  assert.deepEqual(errors,[]);
  report.passed=true;report.checks=['100 unchanged refreshes remain singular','result changes update counters','expanded/collapsed plan preserved','focused button preserved','normal season has no circuit panel','old append path reproduced'];
 }finally{await browser.close();fs.writeFileSync(path.join(folder,'circuit-refresh-test.json'),JSON.stringify({...report,errors},null,2))}
 console.log(JSON.stringify(report));
})().catch(e=>{console.error(e);process.exitCode=1});
