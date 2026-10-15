const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(require.resolve('../ui/app.js'),'utf8');
const I18n=require('../ui/i18n.js');

function fixture(){
 const elements=new Map(),calls={hardware:[],disconnected:0,notices:[],tournaments:[],listWrites:0};
 const $=id=>{if(!elements.has(id))elements.set(id,{textContent:'',hidden:false,checked:true});return elements.get(id)};
 const s={tid:'deleted',snapshot:{id:'deleted'},live:[],gameOffset:100,standOffset:50,gameTotal:180,standTotal:64,historyGames:[{id:'old'}],gameSelected:new Set(['old']),h2hSlot:63};
 const status={live:[],active_games:28,logical_cpus:32,hardware:{stale:false,metrics:{cpu_percent:90}},error:''};
 const clock={now:123};
 const c=vm.createContext({state:s,$,ArenaI18n:I18n,performance:{now:()=>clock.now},sessionStorage:{getItem:()=>null,removeItem(){}},esc:v=>v,
  stableHtml:(id,html)=>{const el=$(id);if(el._renderedHtml!==html){el.innerHTML=html;el._renderedHtml=html;calls.listWrites++}},
  notify:(text,error)=>{calls.notices.push({text,error});$('#error').textContent=text},renderBoards(){},
  renderHardware:v=>calls.hardware.push(v),hardwareDisconnected:()=>calls.disconnected++,
  api:async path=>{if(path==='status')return status;if(path==='tournaments')return [{id:'template',name:'Template',state:'paused'},{id:'active',name:'Qualification',state:'running'}];throw Error(path)},
  refreshTournament:async()=>{calls.tournaments.push(s.tid);if(s.tid==='deleted')throw Object.assign(Error('Tournament not found'),{status:400,serverMessage:'Tournament not found'})}});
 vm.runInContext('let tournamentRefresh=0,gamesRefresh=0;'+source.slice(source.indexOf('async function loadTournaments(){'),source.indexOf("$('#tournamentPicker').onchange")),c);
 vm.runInContext(source.slice(source.indexOf('let refreshing=false,tick=0;'),source.indexOf('safely(async()=>{',source.indexOf('let refreshing=false,tick=0;'))),c);
 return {c,s,calls,$,status,clock};
}

test('external deletion selects the running tournament, clears stale selection, and preserves live hardware',async()=>{
 const {c,s,calls,$}=fixture();$('#error').textContent='Tournament not found';
 await c.refresh();
 assert.equal(s.tid,'active');assert.equal(s.snapshot,null);assert.equal(s.gameSelected.size,0);
 assert.equal(s.historyGames.length,0);assert.equal(s.gameOffset,0);assert.equal(s.standOffset,0);assert.equal(s.h2hSlot,undefined);
 assert.equal($('#selectGames').checked,false);assert.equal($('#h2h').hidden,true);
 assert.deepEqual(calls.tournaments,['deleted','active']);assert.equal(calls.disconnected,0);assert.equal(s.connected,true);
 assert.equal(calls.hardware[0].hardware.metrics.cpu_percent,90);assert.equal($('#error').textContent,'');
 assert.equal($('#sideStatus').textContent,'28 active games · 32 logical CPUs');
});

test('deleting the entire field yields a clean empty workspace without a disconnect or retry loop',async()=>{
 const {c,s,calls,$,status}=fixture();c.api=async path=>path==='status'?status:[];
 await c.refresh();await c.refresh();await c.refresh();
 assert.equal(s.tid,'');assert.equal(s.snapshot,null);assert.equal($('#empty').hidden,false);assert.equal($('#tournamentContent').hidden,true);
 assert.equal($('#deleteTournament').disabled,true);assert.equal(calls.disconnected,0);assert.deepEqual(calls.tournaments,['deleted']);
});

test('other tournament view failures stay visible without blanking hardware',async()=>{
 const {c,s,calls,$}=fixture();c.refreshTournament=async()=>{throw Error('Report calculation failed')};
 await c.refresh();assert.equal(s.connected,true);assert.equal(calls.disconnected,0);
 assert.equal($('#error').textContent,'Report calculation failed');assert.equal(calls.hardware.length,1);
});

test('a real status connection failure still marks hardware disconnected, and later status can recover',async()=>{
 const {c,s,calls,$,status}=fixture();c.api=async()=>{throw Error('Offline')};
 await c.refresh();assert.equal(s.connected,false);assert.equal(calls.disconnected,1);assert.equal(calls.hardware.length,0);
 assert.match($('#sideStatus').textContent,/Worker connection lost/);
 s.tid='';c.api=async()=>status;await c.refresh();assert.equal(s.connected,true);assert.equal(calls.hardware.length,1);
});

test('a selection changed while a deleted tournament request is pending is not replaced',async()=>{
 const {c,s,calls}=fixture();let fail;
 c.refreshTournament=()=>new Promise((_,reject)=>{fail=reject});
 const pending=c.refreshSelectedTournament();s.tid='user-choice';
 fail(Object.assign(Error('Tournament not found'),{serverMessage:'Tournament not found'}));await pending;
 assert.equal(s.tid,'user-choice');assert.equal(calls.notices.length,0);
});

test('a still-present tournament is not retried endlessly or allowed to hide its error',async()=>{
 const {c,s,calls,$,status}=fixture();c.api=async path=>path==='status'?status:[{id:'deleted',name:'Present',state:'running'}];
 await c.refresh();assert.equal(s.tid,'deleted');assert.deepEqual(calls.tournaments,['deleted']);
 assert.equal($('#error').textContent,'Tournament not found');assert.equal(calls.disconnected,0);
});

test('missing selection recovery relies on untranslated error metadata',async()=>{
 const {c,s,calls}=fixture();c.refreshTournament=async()=>{if(s.tid==='deleted')throw Object.assign(Error('Tournoi introuvable'),{serverMessage:'Tournament not found'})};
 await c.refresh();assert.equal(s.tid,'active');assert.equal(calls.disconnected,0);
});

test('a failed list reload is reported but does not change healthy hardware status',async()=>{
 const {c,s,calls,$,status}=fixture();c.api=async path=>{if(path==='status')return status;throw Error('List reload failed')};
 await c.refresh();assert.equal(s.tid,'deleted');assert.equal(s.connected,true);assert.equal(calls.disconnected,0);
 assert.equal($('#error').textContent,'List reload failed');
});

test('the API preserves server error metadata alongside its translated presentation',async()=>{
 const c=vm.createContext({state:{},token:'test',ArenaI18n:{message:()=> 'Tournoi introuvable',t:v=>v},
  fetch:async()=>({ok:false,status:400,headers:{get:()=> 'application/json'},json:async()=>({error:'Tournament not found'})})});
 vm.runInContext(source.slice(source.indexOf('async function api('),source.indexOf('function safely(')),c);
 await assert.rejects(c.api('tournaments/missing'),e=>e.status===400&&e.serverMessage==='Tournament not found'&&e.message==='Tournoi introuvable');
});

test('new event divisions appear automatically while the completed qualification stays selected',async()=>{
 const {c,s,calls,$,status,clock}=fixture();s.tid='qualifier';s.snapshot={id:'qualifier'};
 const rows=[{id:'qualifier',name:'Qualification',state:'completed'}];let lists=0;
 c.api=async path=>{if(path==='status')return status;if(path==='tournaments'){lists++;return rows}throw Error(path)};
 c.refreshTournament=async()=>{};await c.loadTournaments();
 rows.unshift(...Array.from({length:4},(_,i)=>({id:'division'+i,name:'Division '+(i+1),state:'running'})));
 clock.now+=5000;await c.refresh();
 assert.equal(lists,2);assert.equal(s.tid,'qualifier');assert.equal(s.snapshot.id,'qualifier');assert.equal(s.gameOffset,100);
 assert.equal($('#tournamentPicker').value,'qualifier');assert.match($('#tournamentPicker').innerHTML,/Division 4/);
 assert.equal(s.gameSelected.has('old'),true);assert.equal(calls.disconnected,0);
 clock.now+=5000;await c.refresh();assert.equal(calls.listWrites,2,'unchanged options are not recreated');
});

test('an empty workspace discovers a tournament created externally and refreshes its results',async()=>{
 const {c,s,calls,$,status,clock}=fixture();s.tid='';s.snapshot=null;
 clock.now+=5000;await c.refresh();
 assert.equal(s.tid,'active');assert.equal($('#empty').hidden,true);assert.deepEqual(calls.tournaments,['active']);
});

test('polling discovers renames and state changes without following a different tournament',async()=>{
 const {c,s,$,clock}=fixture();s.tid='a';
 let rows=[{id:'a',name:'Old name',state:'running'}];c.api=async()=>rows;
 await c.loadTournaments();rows=[{id:'a',name:'New name',state:'completed'},{id:'b',name:'Next stage',state:'running'}];
 clock.now+=5000;await c.refreshTournamentList();
 assert.equal(s.tid,'a');assert.match($('#tournamentPicker').innerHTML,/New name · completed/);assert.match($('#tournamentPicker').innerHTML,/Next stage/);
});

test('a late list response cannot undo a newer list or a selection made while loading',async()=>{
 const {c,s,$}=fixture();const pending=[];c.api=()=>new Promise(resolve=>pending.push(resolve));
 const first=c.loadTournaments(),second=c.loadTournaments();s.tid='chosen';
 pending[1]([{id:'chosen',name:'Chosen division',state:'running'}]);await second;
 pending[0]([{id:'old',name:'Stale stage',state:'completed'}]);await first;
 assert.equal(s.tid,'chosen');assert.match($('#tournamentPicker').innerHTML,/Chosen division/);assert.doesNotMatch($('#tournamentPicker').innerHTML,/Stale stage/);
});

test('background list failures are rate limited and do not disconnect healthy hardware',async()=>{
 const {c,s,calls,$,status,clock}=fixture();s.tid='';let lists=0;
 c.api=async path=>{if(path==='status')return status;lists++;throw Error('List reload failed')};
 clock.now+=5000;await c.refresh();for(let i=0;i<6;i++){clock.now+=750;await c.refresh()}
 assert.equal(lists,1);assert.equal(s.connected,true);assert.equal(calls.disconnected,0);assert.equal($('#error').textContent,'List reload failed');
 clock.now+=750;await c.refresh();assert.equal(lists,2);
});
