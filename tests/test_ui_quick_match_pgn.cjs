const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function harness(saved){
 const elements={'#exportPgn':{insertAdjacentHTML(){}},'#automaticPgn':{},'#newTournament':{}};
 const c={displayPrefs:{autoPgn:saved},calls:[],persisted:0,$:id=>elements[id]||null,ArenaI18n:{h:x=>x},safely:x=>x,newTournament:async()=>{},saveTournamentSetup:async(p,d)=>{c.calls.push({p,d});return {id:'saved'}},persistDisplay:async()=>c.persisted++};
 vm.createContext(c);vm.runInContext(fs.readFileSync('ui/pgn-output.js','utf8'),c);return {c,elements};
}
test('Quick match saves without full-form PGN controls or rewriting remembered preferences',async()=>{
 const {c}=harness(undefined);assert.equal((await c.saveTournamentSetup({name:'quick'},null)).id,'saved');assert.equal(c.calls[0].p.pgn_output.enabled,false);assert.equal(c.persisted,0);
});
test('Quick match continues a remembered PGN destination and preserves explicit output settings',async()=>{
 const saved={enabled:true,path:'C:/Chess/results.pgn',mode:'new',preset:'testing',remember:true};const {c}=harness(saved);
 await c.saveTournamentSetup({name:'quick'},null);assert.equal(c.calls[0].p.pgn_output.path,saved.path);assert.equal(c.calls[0].p.pgn_output.mode,'append');assert.equal(saved.mode,'new');assert.equal(c.persisted,0);
 const explicit={enabled:false};await c.saveTournamentSetup({name:'explicit',pgn_output:explicit},null);assert.equal(c.calls[1].p.pgn_output,explicit);
});
test('Full setup still uses visible PGN settings and persists the remember choice',async()=>{
 const {c,elements}=harness({remember:true,path:'old.pgn'});
 Object.assign(elements,{'#autoPgnEnabled':{checked:true},'#autoPgnPath':{value:'  new.pgn  '},'#autoPgnMode':{value:'new'},'#autoPgnPreset':{value:'clean'},'#autoPgnRemember':{checked:false}});
 await c.saveTournamentSetup({name:'full'},null);assert.equal(c.calls[0].p.pgn_output.path,'new.pgn');assert.equal(c.calls[0].p.pgn_output.mode,'new');assert.equal(c.persisted,1);assert.equal(c.displayPrefs.autoPgn.remember,false);
});
