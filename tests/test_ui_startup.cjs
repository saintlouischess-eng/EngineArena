const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(require.resolve('../ui/app.js'),'utf8');
const gate=source.slice(source.indexOf('const interfaceReady='),source.indexOf('const token='));
const api=source.slice(source.indexOf('async function api('),source.indexOf('function safely('));

function fixture(readyState='loading'){
 const events=new EventTarget(),calls=[];
 const context=vm.createContext({Promise,state:{},token:'test',ArenaI18n:{locale:'en',t:v=>v},
  document:{readyState,addEventListener:events.addEventListener.bind(events)},
  fetch:async(url,options)=>{calls.push({url,options});return {ok:true,headers:{get:()=> 'application/json'},json:async()=>({ok:true})}}});
 vm.runInContext(gate+api,context);
 return {context,calls,ready:()=>events.dispatchEvent(new Event('DOMContentLoaded'))};
}

test('fast worker reads and preference writes wait for every interface script',async()=>{
 const {context,calls,ready}=fixture();
 const reads=context.api('tournaments/example'),writes=context.api('preferences',{fontSize:18});
 await Promise.resolve();await Promise.resolve();assert.equal(calls.length,0);
 ready();await Promise.all([reads,writes]);assert.equal(calls.length,2);
 assert.match(calls[0].url,/confidence=95/);
 assert.equal(calls[1].options.body,'{"fontSize":18}');
 ready();await Promise.resolve();assert.equal(calls.length,2,'readiness does not duplicate requests');
 await context.api('status');assert.equal(calls.length,3,'later polling needs no new readiness event');
});

for(const state of ['interactive','complete'])test(`already parsed document (${state}) starts immediately`,async()=>{
 const {context,calls}=fixture(state);await context.api('status');assert.equal(calls.length,1);
});
