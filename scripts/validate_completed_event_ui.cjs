// Real UI scripts against read-only exported fixtures. No worker, engines or account.
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const folder=process.argv[2]||'test-output/completed-custom-season-20261014';
const read=f=>fs.readFileSync(f,'utf8'),json=f=>JSON.parse(read(path.join(folder,f+'.json')));
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--disable-gpu']});
 const errors=[],checks=[],p=await browser.newPage({viewport:{width:1500,height:1050}});
 p.on('pageerror',e=>errors.push(e.message));
 try{
  await p.setContent('<nav><button data-view="engines">Engines</button></nav><main></main><dialog id="modal"><div id="modalContent"></div></dialog>');
  await p.evaluate(f=>window.fixture=f,{e:json('event-fixed'),d:json('insights-fixed'),pages:json('insight-pages-fixed'),careers:json('careers-fixed'),details:json('career-details-fixed')});
  await p.addScriptTag({content:`
   const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
   const ArenaI18n={locale:'en',t:v=>window.messages?.[v]||v,message:v=>window.messages?.[v]||v,h:(v,...args)=>typeof v==='string'?v:v.reduce((a,s,i)=>a+s+(args[i]??''),'')};
   const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
   const tcText=t=>t.seconds+'s + '+t.increment+'s',safely=fn=>fn,state={view:'events'};
   const scheduleOrderLabel=v=>v;
   ${read('ui/app.js').split('\n').find(l=>l.startsWith('function modal('))}
   async function api(route,body){if(body)throw Error('Mutation prohibited in audit fixture');const url=new URL(route,'http://fixture/');const q=url.searchParams;
    if(q.get('view')==='insights')return structuredClone(q.has('export')?fixture.d:fixture.pages[Math.floor(Number(q.get('offset')||0)/8)]);
    if(q.get('view')==='careers'){if(q.has('identity'))return structuredClone(fixture.details[q.get('identity')]);let c=structuredClone(fixture.careers);c.items=c.items.filter(p=>p.name.toLowerCase().includes((q.get('search')||'').toLowerCase()));c.total=c.items.length;return c}
    return structuredClone(fixture.e)}
   window.setInterval=()=>0;
   ${read('ui/app.js').split('\n').find(l=>l.startsWith('function stableHtml('))}
  `});
  for(const file of ['text-format.js','events.js','season-insights.js','circuits.js'])await p.addScriptTag({content:read('ui/'+file)});
  for(const file of ['style.css','studio.css','events.css','season-insights.css','circuits.css'])await p.addStyleTag({content:read('ui/'+file)});
  await p.evaluate(()=>showEvent(fixture.e.id));
  await p.evaluate(async()=>{for(let i=0;i<100;i++)await refreshEventDetail();await loadInsights()});
  assert.equal(await p.locator('.cx-desk').count(),1);assert.equal(await p.locator('.si-hero').count(),1);
  assert.equal(await p.locator('.si-division').count(),4);assert.equal(await p.locator('.si-playoffs').count(),1);
  assert.equal(await p.locator('.si-final tbody tr').count(),6);
  assert.match(await p.locator('.si-match').innerText(),/2.5 — 1.5/);
  assert.match(await p.locator('.si-final tbody tr').first().innerText(),/Champion.*Triumviratus/);
  checks.push('100 refreshes: single plan, hero and playoff history; bracket order and actual 2.5–1.5 final');
  await p.locator('.cx-desk summary').click();await p.locator('#cxSaveTemplate').focus();
  await p.evaluate(async()=>{for(let i=0;i<20;i++)await refreshEventDetail();await loadInsights()});
  assert.equal(await p.locator('.cx-desk details').evaluate(el=>el.open),true);
  assert.equal(await p.locator('#cxSaveTemplate').evaluate(el=>el===document.activeElement),true);
  await p.locator('.cx-desk summary').click();
  for(let i=1;i<3;i++){await p.locator('#siNext').click();await p.waitForFunction(i=>SeasonDesk.offset===8*i&&document.querySelector('.si-playoffs'),i);await p.evaluate(()=>loadInsights());assert.equal(await p.locator('.cx-desk').count(),1);assert.equal(await p.locator('.si-playoffs').count(),1)}
  assert.equal(await p.locator('#siNext').isDisabled(),true);
  await p.evaluate(async()=>{SeasonDesk.offset=0;await loadInsights()});
  checks.push('all 21 stage records accessible across three pages');
  await p.locator('#siTab-careers').click();await p.waitForSelector('#siCareerRows');
  assert.equal(await p.locator('#siCareerRows tr').count(),24);
  await p.locator('#siCareerRows [data-career]').first().click();await p.waitForSelector('#siCareerBack');
  assert.match(await p.locator('#siPanel-careers').innerText(),/Champion/);
  await p.locator('#siPanel-careers').screenshot({path:path.join(folder,'career-fixed.png')});
  await p.locator('#siCareerBack').click();await p.waitForSelector('#siCareerRows');
  await p.locator('#siSearch').fill('Stockfish');await p.waitForFunction(()=>document.querySelectorAll('#siCareerRows tr').length===1);
  await p.locator('#siSearch').fill('');await p.waitForFunction(()=>document.querySelectorAll('#siCareerRows tr').length===24);
  checks.push('24 careers, search, career detail, version history and rivals');
  await p.locator('#siTab-summary').click();await p.waitForSelector('#siSummaryPreview');
  const brief=await p.locator('#siSummaryPreview').inputValue();fs.writeFileSync(path.join(folder,'season-summary-brief-fixed.txt'),brief);
  assert.match(brief,/2.5 — 1.5/);assert.match(brief,/Stage leaders/);assert.doesNotMatch(brief,/Division leaders|Live places are provisional/);
  assert.equal((brief.match(/Balanced_GM_8move/g)||[]).length,1);
  await p.locator('#siSummaryDetail').selectOption('full');
  const full=await p.locator('#siSummaryPreview').inputValue();fs.writeFileSync(path.join(folder,'season-summary-full-fixed.txt'),full);
  for(const s of json('insights-fixed').stages)assert.ok(full.includes(s.label),s.label);
  checks.push('brief/full reports: shared book once in recap, all 21 tables in full report, correct final');
  await p.locator('#siTab-stages').click();assert.match(await p.locator('#eventSummary').innerText(),/Season 1 · Champion/);assert.doesNotMatch(await p.locator('#eventSummary').innerText(),/Season 3/);
  const labels=await p.locator('#eventChildren tr td:first-child').allTextContents();assert.equal(new Set(labels).size,21);
  const eventText=await p.evaluate(()=>eventReport(eventDetailData));fs.writeFileSync(path.join(folder,'event-report-fixed.txt'),eventText);
  checks.push('records: Season 1 champion, 21 unique labels; complete event text export');
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   const catalog=JSON.parse(read('locales/'+lang+'.json')).messages;
   await p.evaluate(({lang,catalog})=>{ArenaI18n.locale=lang;window.messages=catalog;stableHtml('#siPanel-summary','')}, {lang,catalog});
   for(const width of [1050,1500])for(const theme of ['dark','light']){
    await p.setViewportSize({width,height:1050});await p.evaluate(t=>document.body.classList.toggle('light',t==='light'),theme);
    for(const tab of ['overview','careers','summary','stages']){
     await p.locator('#siTab-'+tab).click();await p.evaluate(()=>loadInsights());
     assert.equal(await p.locator('#siStatus').innerText(),'','Caught error in '+lang+' '+tab);
     if(tab==='summary')assert.match(await p.locator('#siSummaryPreview').inputValue(),/2.5 — 1.5/);
     assert.equal(await p.locator('#modal').evaluate(el=>el.scrollWidth>el.clientWidth+2),false,lang+' '+theme+' '+width+' '+tab);
     if(lang==='en'&&width===1500&&theme==='dark')await p.screenshot({path:path.join(folder,tab+'-fixed.png')});
    }
   }
  }
  checks.push('all four tabs: eight languages, two widths, dark/light; no dialog overflow');
  assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(folder,'ui-validation.json'),JSON.stringify({passed:true,checks,errors},null,2));console.log(JSON.stringify({passed:true,checks}));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
