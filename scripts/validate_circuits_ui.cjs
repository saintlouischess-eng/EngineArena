const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync(process.argv[2]||'test-output/tournament-edit-ready.json','utf8')),out=process.argv[3]||'test-output/circuit-ui';fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});const report={passed:false,errors:[],cases:[]};
 try{
  const p=await browser.newPage({viewport:{width:1440,height:1000}});p.on('pageerror',e=>report.errors.push(e.message));
  await p.goto(ready.url+'&lang=en');await p.waitForFunction(()=>state.engines?.length&&queueData&&typeof editCircuit==='function');
  await p.evaluate(async id=>{state.tid=id;await editCircuit()},ready.rr);
  const card=p.locator('.cx-stage').first();await card.locator('[data-cx="advance"]').fill('99');await p.locator('#cxCalculate').click();await p.waitForFunction(()=>$('#modal .dialog-error')?.textContent.includes('exceeds'));assert.equal(await p.locator('#cxSave').isDisabled(),true);
  await card.locator('[data-cx="advance"]').fill('2');await card.locator('summary').click();await card.locator('[data-adjudication]').check();
  for(const [k,v] of Object.entries({resign_cp:600,resign_plies:9,draw_cp:15,draw_plies:17,draw_after:101}))await card.locator(`[data-adj="${k}"]`).fill(String(v));
  await card.locator('[data-clock]').check();await p.evaluate(()=>{const box=$('#cxTC0');box.innerHTML=tcEditor('temporary',{kind:'nodes',nodes:5432});});
  // Keep the actual editor identifiers intact when selecting the node control.
  await p.evaluate(()=>{const box=$('#cxTC0');box.outerHTML=tcEditor('cxTC0',{kind:'nodes',nodes:5432});wireTc('cxTC0')});
  await p.locator('#cxName').fill('UI custom season');await p.locator('#cxSeasons').fill('2');await p.locator('#cxCalculate').click();await p.waitForFunction(()=>!$('#cxSave').disabled);
  await p.locator('#cxPreview').screenshot({path:path.join(out,'preview.png')});await p.locator('#cxSave').click();await p.waitForFunction(()=>eventDetailData?.name==='UI custom season'&&$('#cxApprove'));
  const eid=await p.evaluate(()=>eventDetailData.id);report.eid=eid;
  const e=await p.evaluate(id=>api('events/'+id),eid);assert.equal(e.definition.stages[0].adjudication.draw_after,101);assert.equal(e.preview[0].draw_plies,17);assert.equal(e.preview[0].time_control.nodes,5432);
  await p.locator('#siPanel-overview').screenshot({path:path.join(out,'dashboard.png')});assert.equal(await p.locator('#eventRun').isDisabled(),true);
  await p.locator('#cxApprove').click();await p.waitForFunction(()=>!$('#eventRun').disabled);
  await p.locator('#cxEditFuture').click();await p.waitForSelector('#cxStages');await p.locator('.cx-stage').last().locator('[data-cx="pairs"]').fill('3');await p.locator('#cxCalculate').click();await p.waitForFunction(()=>!$('#cxSave').disabled);await p.locator('#cxSave').click();await p.waitForFunction(()=>!!$('#cxApprove'));
  report.cases.push('validation, save, per-stage nodes/adjudication, approve and edit');
  const template=await p.evaluate(id=>api('events',{action:'template',template:{action:'save',event_id:id,name:'UI reusable competition'}}),eid);
  await p.evaluate(()=>editCircuit());await p.locator('#cxTemplate').selectOption(template.id);await p.waitForFunction(()=>$('.cx-stage [data-adj="draw_after"]')?.value==='101');
  await p.locator('#cxCalculate').click();await p.waitForFunction(()=>!$('#cxSave').disabled);await p.keyboard.press('Escape');report.cases.push('template restores conditions');
  for(const width of [1440,900])for(const theme of ['dark','light']){
   await p.setViewportSize({width,height:900});await p.evaluate(async({eid,theme})=>{document.body.classList.toggle('light',theme==='light');await editCircuit(await api('events/'+eid))},{eid,theme});
   const size=await p.locator('.modal-body').evaluate(el=>({width:el.clientWidth,scroll:el.scrollWidth}));assert(size.scroll<=size.width+2,JSON.stringify({width,theme,size}));
   await p.locator('.cx-stage').first().screenshot({path:path.join(out,`editor-${width}-${theme}.png`)});await p.keyboard.press('Escape');
  }
  await p.setViewportSize({width:1440,height:1000});
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await p.goto(ready.url+'&lang='+lang);await p.waitForFunction(()=>state.engines?.length&&queueData);
   await p.evaluate(async id=>editCircuit(await api('events/'+id)),eid);await p.locator('#cxCalculate').click();await p.waitForFunction(()=>!$('#cxSave').disabled);assert.equal(await p.locator('.cx-stage').count(),2);await p.keyboard.press('Escape');
   report.cases.push('language '+lang);
  }
  assert.deepEqual(report.errors,[]);report.passed=true;
 }finally{await browser.close();fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(report,null,2))}
 console.log(JSON.stringify(report));
})().catch(e=>{console.error(e);process.exitCode=1});
