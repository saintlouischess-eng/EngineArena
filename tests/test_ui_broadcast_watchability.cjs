const test=require('node:test'),assert=require('node:assert/strict');
const M=require('../ui/broadcast-model.js'),P=require('../ui/broadcast-progress.js');
test('final position survives the idle gap but never a different event or a new game',()=>{
 const f=new M.FinalPosition(),g={attempt:'done',reason:'checkmate',official:true,result:'1-0',fen:'final',clock_active:'white',thinking:{uci:'old'}};
 const d={connected:true,config:{tid:'one'},game:g};f.present(d);g.fen='mutated';
 const held=f.present({...d,game:null});assert.equal(held.game.fen,'final');assert.equal(held.game.clock_active,null);assert.equal(held.game.thinking,null);assert(held.game.waiting_next);
 assert.equal(f.present({...d,config:{tid:'two'},game:null}).game,null);
 f.present(d);const next={attempt:'new',phase:'Live'};assert.equal(f.present({...d,game:next}).game,next);assert.equal(f.present({...d,game:null}).game,null);
});
test('unofficial ended attempts never acquire an official result while waiting',()=>{
 const f=new M.FinalPosition(),d={connected:true,config:{tid:'one'},game:{reason:'interrupted',official:false,result:null}};
 f.present(d);assert.equal(f.present({...d,game:null}).game.result,null);
 assert.equal(M.gameContext(d.game),'Attempt ended');
});
test('shared configurations may be removed only when every displayed pool identity agrees',()=>{
 const rows=[{name:'Engine 1 · 1 thread'},{name:'Engine 2 · 1 thread'}];
 const c=M.commonConfiguration(rows);assert.equal(c,'1 thread');assert.equal(M.displayName(rows[0].name,c),'Engine 1');assert.equal(rows[0].name,'Engine 1 · 1 thread');
 rows.push({name:'Engine 1 · 32 threads'});assert.equal(M.commonConfiguration(rows),'');assert.equal(M.displayName(rows[0].name),'Engine 1 · 1 thread');
 assert.equal(M.displayName('Stockfish dev-20261024-dbe600b7'),'Stockfish dev-20261024-dbe600');
});
test('game context derives move and side from FEN; PV remains separate and bounded',()=>{
 const g={fen:'8/8/8/8/8/8/K7/7k b - - 0 34',phase:'Live',clock_active:'black'};
 assert.equal(M.gameContext(g),'Move 34 · Black to move');assert.equal(M.analysisSide(g),'black');
 assert.equal(M.analysisSide({moves:[{side:'white',info:{cp:14}}],info:{cp:14},phase:'Final result'}),'white');
 assert.equal(M.analysisSide({moves:[{side:'white',info:{cp:14}}],info:{cp:80},phase:'Final result'}),null);
 assert.equal(M.shortPV('34... Kf2 35. Ka3 Ke3 36. Kb3 Kd4 37. Kc2 Kc4',4),'34... Kf2 35. Ka3 Ke3 36. Kb3 …');
 assert.equal(M.shortPV(null),'');
});
const data=()=>({connected:true,server_time:10000,summary_at:10000,config:{tid:'one'},summary:{state:'running',total:10000,completed:1000,progress:{status:'estimated',games_per_hour:100,eta_seconds:324000}}});
test('ETA prefers a measured longer active segment over a volatile worker estimate',()=>{
 const d=data();d.observations=Array.from({length:13},(_,i)=>({tid:'one',state:'running',total:10000,time:6400+i*300,completed:800+200*i/12}));
 const v=P.progress(d);assert.equal(v.rate,200);assert.equal(v.windowMinutes,60);assert.match(v.detail,/60 min rolling pace/);
 d.observations[10].state='paused';assert.equal(P.progress(d).source,'worker');
});
test('five-minute ETA display hold never freezes counts or hides a pause or roster change',()=>{
 const stable=P.stableEstimate(),d=data();const a=stable(d);
 d.server_time+=30;d.summary_at=d.server_time;d.summary.completed+=2;d.summary.progress.games_per_hour=200;d.summary.progress.eta_seconds/=2;
 const b=stable(d);assert.equal(b.eta,a.eta);assert.equal(b.completed,1002);
 d.server_time+=300;d.summary_at=d.server_time;assert.notEqual(stable(d).eta,a.eta);
 d.summary.state='paused';assert.equal(stable(d).eta,'Paused');
 d.summary.state='running';assert.equal(stable(d).rate,200);
 d.summary.total=20000;d.summary.progress.games_per_hour=150;assert.equal(stable(d).rate,150);
 d.connected=false;assert.equal(stable(d).eta,'Reconnecting');
});
