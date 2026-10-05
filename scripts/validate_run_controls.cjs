// Isolated live-refresh regression. Start with scripts/preview_design.py.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(JSON.parse(fs.readFileSync('test-output/design-ready.json')).url);
  await page.waitForFunction(()=>state.snapshot?.state==='running'&&$('#start').disabled&&$('#start').textContent.includes('Running'));
  const refresh=await page.evaluate(async()=>{
   const button=$('#start'),mutations=[];
   const observer=new MutationObserver(rs=>mutations.push(...rs.map(r=>({type:r.type,attribute:r.attributeName,disabled:button.disabled}))));
   observer.observe(button,{attributes:true,attributeFilter:['disabled'],childList:true});
   await new Promise(resolve=>setTimeout(resolve,4200));observer.disconnect();
   return {mutations,disabled:button.disabled,label:button.textContent};
  });
  assert.deepEqual(refresh.mutations,[]);assert.equal(refresh.disabled,true);
  const cases=await page.evaluate(async()=>{
   const original=state.snapshot,workerError=state.workerError,results=[];
   const checks=[['paused',{},false],['running',{},true],['draining',{},true],['completed',{},true],
    ['paused',{dependency:{round:1}},true],['paused',{sprt:{frozen:true},sprt_status:{can_diagnostic_start:false}},true],
    ['paused',{sprt:{frozen:true},sprt_status:{can_diagnostic_start:true}},false],
    ['paused',{queue:{finished:false}},true],['paused',{event:{can_diagnostic_start:false}},true],
    ['paused',{event:{can_diagnostic_start:true}},false],['running',{event:{can_diagnostic_start:true}},true]];
   try{
    state.workerError='';
    for(const [status,extra,expected] of checks){state.snapshot={...original,state:status,event:null,dependency:null,queue:null,sprt:null,sprt_status:null,...extra};updateRunControls();results.push({status,extra,expected,disabled:$('#start').disabled})}
    state.snapshot={...original,state:'paused'};state.workerError='fixture';updateRunControls();results.push({status:'worker error',expected:true,disabled:$('#start').disabled});
    state.workerError='';updateRunControls();
    await safely(async()=>{state.snapshot={...original,state:'running'};updateRunControls()})({currentTarget:$('#start')});
    results.push({status:'start action completes',expected:true,disabled:$('#start').disabled,busy:$('#start').hasAttribute('aria-busy')});
   }finally{state.snapshot=original;state.workerError=workerError;updateRunControls()}
   return results;
  });
  for(const c of cases){assert.equal(c.disabled,c.expected,JSON.stringify(c));if('busy'in c)assert.equal(c.busy,false)}
  assert.deepEqual(errors,[]);fs.writeFileSync('test-output/run-controls-stability.json',JSON.stringify({refresh,cases,errors},null,2));
  console.log('Steady Running button across live refreshes; 13 start-state/action cases passed.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
