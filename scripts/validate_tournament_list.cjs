// Isolated UI acceptance: externally created stages must appear without navigation.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync(process.env.ARENA_LIST_READY||'test-output/workflow-ready.json','utf8'));
 const out=process.env.ARENA_LIST_OUT||'test-output/tournament-list-ui';fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--disable-gpu']});const errors=[];
 try{
  const page=await browser.newPage({viewport:{width:1500,height:1000}});page.on('pageerror',e=>errors.push(e.message));
  const token=new URL(ready.url).searchParams.get('token'),base=new URL(ready.url).origin;
  const api=async(p,body)=>{const r=await page.request.fetch(base+'/api/'+p,{method:body===undefined?'GET':'POST',headers:{'X-Arena-Token':token},...(body===undefined?{}:{data:body})});assert(r.ok(),await r.text());return r.json()};
  let catalog=(await api('tournaments')).filter(t=>t.id===ready.completed),requests=0;
  await page.route('**/api/tournaments',route=>{if(route.request().method()!=='GET')return route.continue();requests++;return route.fulfill({json:catalog})});
  await page.goto(ready.url);await page.waitForFunction(id=>state.snapshot?.id===id,ready.completed);
  const selected=await page.locator('#tournamentPicker').inputValue();assert.equal(selected,ready.completed);
  const added=[];for(let i=0;i<3;i++)added.push(await api('tournaments',{name:'Automatic stage '+(i+2),profiles:ready.profiles.slice(0,2),settings:{format:'round_robin',cycles:1,concurrency:1,time_control:{kind:'nodes',nodes:1000}}}));
  catalog=await api('tournaments'); // APIRequestContext bypasses the page route.
  const initialRequests=requests,expectedOptions=catalog.length+1;
  await page.waitForFunction(n=>document.querySelector('#tournamentPicker').options.length===n,expectedOptions,{timeout:15000});
  assert.equal(await page.locator('#tournamentPicker').inputValue(),selected);assert.equal(await page.evaluate(()=>state.snapshot.id),selected);
  assert(requests-initialRequests<=3,'list polling is bounded');
  await page.locator('#tournamentPicker').selectOption(ready.tid);await page.waitForFunction(id=>state.snapshot?.id===id,ready.tid);
  await page.evaluate(()=>window.listOptionProbe=document.querySelector('#tournamentPicker').selectedOptions[0]);
  const sameRequests=requests;await page.waitForFunction(()=>performance.now()-tournamentListCheckedAt>10);while(requests===sameRequests)await page.waitForTimeout(150);
  assert.equal(await page.evaluate(()=>window.listOptionProbe===document.querySelector('#tournamentPicker').selectedOptions[0]),true);
  const renamed=catalog.find(x=>x.id===added[0].id);renamed.name='Renamed stage';renamed.state='completed';
  await page.waitForFunction(()=>[...document.querySelector('#tournamentPicker').options].some(o=>o.textContent==='Renamed stage · completed'),null,{timeout:15000});
  assert.equal(await page.locator('#tournamentPicker').inputValue(),ready.tid);
  await page.screenshot({path:out+'/stages-discovered.png'});
  // A second, initially empty workspace also learns about externally created stages.
  const empty=await browser.newPage({viewport:{width:1280,height:900}});empty.on('pageerror',e=>errors.push(e.message));let reveal=false;
  await empty.route('**/api/tournaments',route=>route.fulfill({json:reveal?catalog:[]}));await empty.goto(ready.url);
  await empty.waitForFunction(()=>document.querySelector('#tournamentPicker').options.length===1&&state.connected);reveal=true;
  await empty.waitForFunction(n=>!!state.tid&&document.querySelector('#tournamentPicker').options.length===n,expectedOptions,{timeout:15000});
  assert.equal(await empty.locator('#empty').isVisible(),false);assert.deepEqual(errors,[]);
  fs.writeFileSync(out+'/result.json',JSON.stringify({passed:true,externalCreation:true,selectionPreserved:true,stableOptionNodes:true,renamedAndCompleted:true,emptyWorkspace:true,pageErrors:errors,listRequests:requests},null,2));
  console.log('Tournament list UI: external stages, preserved selection, stable options, renames/states and empty workspace passed.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
