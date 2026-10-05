const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/events-ready.json','utf8')),browser=await chromium.launch({headless:true,channel:'msedge'}),evidence=[],errors=[];
 try{
  const page=await browser.newPage({viewport:{width:1450,height:1000}});page.on('pageerror',e=>errors.push(e.message));
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await page.goto(ready.url+'&lang='+lang);await page.waitForFunction(()=>state.snapshot&&typeof newExperiment==='function');
   await page.evaluate(()=>{window.missingMessages=new Set();ArenaI18n.capture(key=>{if(ArenaI18n.locale!=='en'&&!Object.hasOwn(ARENA_MESSAGES,key))missingMessages.add(key)});displayPrefs.fontSize=20;applyDisplay()});
   for(const format of ['match','round_robin','gauntlet','self_play','swiss','knockout','double_elimination','ladder','sprt','custom']){
    await page.evaluate(async ({ids,format})=>{state.selected=new Set(ids.slice(0,['match','sprt'].includes(format)?2:5));await newTournament()}, {ids:ready.profiles,format});
    await page.locator('#tformat').selectOption(format);if(format==='custom')await page.locator('#customPairs').fill('1 2 2\n3 4 1');
    await page.waitForFunction(()=>!$('#createTournament').disabled&&$('#totalPreview').textContent!=='—');
    for(const width of [1450,1050]){await page.setViewportSize({width,height:1000});const check=await page.evaluate(()=>({pageOverflow:document.documentElement.scrollWidth>innerWidth,modalOverflow:$('.modal-body').scrollWidth>$('.modal-body').clientWidth+1,missing:[...missingMessages]}));assert.deepEqual(check,{pageOverflow:false,modalOverflow:false,missing:[]});evidence.push({lang,format,width})}
    await page.evaluate(()=>$('#modal').close());
   }
   for(const kind of ['suite','benchmark']){
    await page.evaluate(kind=>newExperiment(kind),kind);const opts=await page.locator('#extc [data-tc=kind] option').evaluateAll(es=>es.map(e=>e.value));assert.deepEqual(opts.sort(),['depth','movetime','nodes']);
    assert.equal(await page.locator('#exhang').inputValue(),'300');assert.deepEqual(await page.evaluate(()=>[...missingMessages]),[]);
    assert.equal(await page.evaluate(()=>$('.modal-body').scrollWidth>$('.modal-body').clientWidth+1),false);await page.evaluate(()=>$('#modal').close());
   }
  }
  await page.goto(ready.url+'&lang=en');await page.waitForFunction(()=>state.snapshot);await page.evaluate(ids=>{state.selected=new Set(ids.slice(0,2));newExperiment('benchmark')},ready.profiles);
  await page.locator('#exname').fill('GUI benchmark 52 cases');await page.locator('#exthreads').fill('1,2');await page.locator('#exrepeats').fill('13');await page.locator('#createExperiment').click();await page.waitForFunction(()=>!$('#modal').open);
  const id=await page.evaluate(async()=>{const j=(await api('experiments')).find(j=>j.name==='GUI benchmark 52 cases');await api(`experiments/${j.id}/action`,{action:'start'});await experimentResults(j.id);return j.id});
  await page.waitForFunction(()=>$('#experimentRows').children.length>=2);assert.equal(await page.locator('#experimentRows').innerText().then(s=>s.includes('running · archived')),false);
  await page.waitForFunction(()=>$('#experimentProgress').textContent.startsWith('52 / 52'),{},{timeout:60000});
  assert.equal(await page.locator('#experimentRows tr').count(),50);await page.locator('#experimentNext').click();await page.waitForFunction(()=>$('#experimentRows').children.length===2);
  await page.screenshot({path:'test-output/experiment-results-ui.png'});
  const downloadPromise=page.waitForEvent('download');await page.locator('#exportExperiment').click();const download=await downloadPromise;const exportPath='test-output/experiment-ui-export.json';await download.saveAs(exportPath);const exported=JSON.parse(fs.readFileSync(exportPath,'utf8'));assert.equal(exported.results.length,52);assert.equal(exported.benchmark_summary.length,4);assert.ok(exported.results[0].runtime.options.Threads);
  const text=await page.evaluate(job=>ArenaText.experiment(job),exported);assert.ok(text.includes('Benchmark averages')&&text.includes('repeat 13'));fs.writeFileSync('test-output/experiment-ui-export.txt',text);
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await page.goto(ready.url+'&lang='+lang);await page.waitForFunction(()=>state.snapshot);await page.evaluate(async id=>{window.missingMessages=new Set();ArenaI18n.capture(k=>{if(ArenaI18n.locale!=='en'&&!Object.hasOwn(ARENA_MESSAGES,k))missingMessages.add(k)});displayPrefs.fontSize=20;applyDisplay();await experimentResults(id)},id);
   await page.locator('#experimentSummary summary').click();assert.deepEqual(await page.evaluate(()=>[...missingMessages]),[]);assert.equal(await page.evaluate(()=>$('.modal-body').scrollWidth>$('.modal-body').clientWidth+1),false);
   if(['en','de'].includes(lang))await page.screenshot({path:`test-output/experiment-summary-${lang}.png`});
  }
  assert.deepEqual(errors,[]);fs.writeFileSync('test-output/format-experiment-ui.json',JSON.stringify({layouts:evidence,errors,experimentCases:52,fullExports:true},null,2));console.log('160 format layouts, eight-language suite/benchmark dialogs, live results, paging and full exports passed.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
