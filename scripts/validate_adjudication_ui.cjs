// Actual create/draft/edit workflow against an isolated dev or packaged worker.
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync(process.argv[2]||'test-output/tournament-edit-ready.json','utf8'));
 const out=process.argv[3]||'test-output/v189-ui';fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const report={passed:false,errors:[],languages:[],drafts:[],checkpoints:[]};
 try{
  const p=await browser.newPage({viewport:{width:1350,height:1000}});p.on('pageerror',e=>report.errors.push(e.message));
  p.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/api/setup-draft')){const d=r.postDataJSON();report.drafts.push({revision:d.revision,fields:d.value?.fields})}});
  const open=async()=>{await p.waitForFunction(()=>document.querySelector('#createTournament')&&!document.querySelector('#createTournament').disabled&&document.querySelector('#tresignPlies'))};
  const fields=['tresign','tresignPlies','tdraw','tdrawPlies','tdrawAfter'];
  const values=()=>p.evaluate(ids=>ids.map(id=>Number(document.getElementById(id).value)),fields);
  await p.goto(ready.url+'&lang=en');await p.waitForFunction(()=>state.engines?.length&&queueData);
  if(ready.rr){
   await p.evaluate(async tid=>newTournament(await api(`tournaments/${tid}/setup`)),ready.rr);await open();
   assert.deepEqual(await values(),[0,15,0,12,80]);await p.keyboard.press('Escape');report.legacy_settings_preserved=true;
  }
  await p.evaluate(async()=>{const d=await api('setup-draft');await api('setup-draft',{revision:d.revision,value:null});state.selected=new Set(state.engines.slice(0,2).map(e=>e.id));$('#allProfiles').checked=false;await newTournament(null,true)});await open();
  assert.deepEqual(await values(),[0,6,0,12,80]);
  for(const [id,value] of [['tdrawAfter',''],['tdrawPlies','2.5'],['tresignPlies','0']]){
   const old=await p.locator('#'+id).inputValue();await p.locator('#'+id).fill(value);assert.equal(await p.locator('#'+id).evaluate(e=>e.checkValidity()),false);
   await p.locator('#createTournament').click();assert.equal(await p.locator('#modal').evaluate(e=>e.open),true);await p.locator('#'+id).fill(old);
  }
  const custom=[650,9,15,17,101];for(let i=0;i<fields.length;i++)await p.locator('#'+fields[i]).fill(String(custom[i]));
  await p.locator('#tname').fill('Adjudication UI validation');
  // Poll the committed response explicitly. An async waitForFunction predicate
  // can treat its Promise as truthy before the response confirms the save.
  await p.evaluate(async({fields,custom})=>{
   const deadline=Date.now()+10000;
   while(Date.now()<deadline){
    const d=await api('setup-draft'),f=d.value?.fields;
    if(f?.tname==='Adjudication UI validation'&&fields.every((id,i)=>f[id]===String(custom[i])))return;
    await new Promise(resolve=>setTimeout(resolve,75));
   }
   throw Error('Custom adjudication draft was not committed before reload');
  },{fields,custom});
  report.checkpoints.push({stage:'before reload',values:await values()});
  await p.reload();await p.waitForFunction(()=>state.engines?.length&&queueData);await p.evaluate(()=>newTournament());await open();report.checkpoints.push({stage:'after reload',values:await values()});assert.deepEqual(await values(),custom);
  await p.locator('#createTournament').click();await p.waitForFunction(()=>!$('#modal').open&&state.snapshot?.name==='Adjudication UI validation');
  const tid=await p.evaluate(()=>state.tid);report.tid=tid;
  const settingValues=()=>p.evaluate(async tid=>{const s=(await api(`tournaments/${tid}`)).settings;return [s.resign_cp,s.resign_plies,s.draw_cp,s.draw_plies,s.draw_after]},tid);
  assert.deepEqual(await settingValues(),custom);
  await p.locator('#editTournament').click();await open();assert.deepEqual(await values(),custom);
  await p.locator('#tdrawAfter').fill('43');await p.locator('#tresignPlies').fill('7');await p.locator('#createTournament').click();await p.waitForFunction(()=>!$('#modal').open);
  assert.deepEqual(await settingValues(),[650,7,15,17,43]);
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await p.goto(ready.url+'&lang='+lang);await p.waitForFunction(()=>state.engines?.length&&queueData);
   await p.evaluate(async tid=>{state.tid=tid;await refreshTournament();await newTournament(await api(`tournaments/${tid}/setup`))},tid);await open();
   assert.deepEqual(await values(),[650,7,15,17,43]);
   const label=await p.locator('#tdrawAfter').evaluate(e=>e.closest('.field').querySelector('label').textContent);
   assert(label&& (lang==='en'||label!=='Minimum played plies before a draw'));
   await p.locator('#tresign').scrollIntoViewIfNeeded();const section=p.locator('#tresign').locator('xpath=ancestor::section[contains(@class,"editor-section")]');
   const layout=await section.evaluate(el=>({width:el.clientWidth,scroll:el.scrollWidth}));assert(layout.scroll<=layout.width+2,JSON.stringify({lang,layout}));
   if(['en','fr','de'].includes(lang))await section.screenshot({path:path.join(out,lang+'.png')});
   report.languages.push({lang,label});await p.keyboard.press('Escape');
  }
  assert.deepEqual(report.errors,[]);report.passed=true;report.default_values=[0,6,0,12,80];report.saved_values=[650,7,15,17,43];report.draft_reload=true;report.invalid_values_blocked=true;
 }finally{await browser.close();fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(report,null,2))}
 console.log(JSON.stringify(report));
})().catch(e=>{console.error(e);process.exitCode=1});
