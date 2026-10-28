const test=require('node:test'),assert=require('node:assert/strict'),P=require('../ui/broadcast-progress.js');
const base=()=>({connected:true,server_time:20000,summary_at:19995,config:{tid:'one'},summary:{state:'running',completed:40000,total:160000,progress:{status:'estimated',eta_seconds:2160000,games_per_hour:200}}});
test('worker ETA uses official progress and formats marathon and short-match durations',()=>{
 const v=P.progress(base());assert.equal(v.percent,25);assert.equal(v.eta,'≈ 25d');assert.equal(v.source,'worker');
 assert.equal(P.duration(3599),'1h');assert.equal(P.duration(359),'6m');assert.equal(P.duration(25),'< 1m');assert.equal(P.duration(NaN),'—');
});
test('pauses, draining, disconnection, stale snapshots and finalizing never show a live estimate',()=>{
 for(const [state,expected] of [['paused','Paused'],['draining','Draining'],['completed','Ended early']]){const d=base();d.summary.state=state;assert.equal(P.progress(d).eta,expected)}
 const d=base();d.connected=false;assert.equal(P.progress(d).seconds,null);d.connected=true;d.summary_at=19000;assert.equal(P.progress(d).status,'stale');d.summary_at=20000;d.summary.completed=160000;assert.equal(P.progress(d).eta,'Finalizing');d.summary.progress.status='replays';assert.equal(P.progress(d).eta,'Replays in progress');d.summary.state='completed';assert.equal(P.progress(d).eta,'Complete');
});
test('fallback requires a fresh contiguous active-play segment from the selected tournament',()=>{
 const d=base();d.summary.progress={status:'collecting'};
 const point=(time,completed,extra={})=>({time,completed,total:160000,state:'running',tid:'one',...extra});
 d.observations=[point(19400,39950),point(19700,39975),point(20000,40000)];assert.equal(P.progress(d).rate,300);assert.equal(P.progress(d).source,'observed');
 for(const extra of [{state:'paused'},{total:100000},{tid:'other'}]){d.observations=[point(19400,39950,extra),point(20000,40000)];assert.equal(P.progress(d).seconds,null)}
 d.observations=[point(18000,39000),point(20000,40000)];assert.equal(P.progress(d).seconds,null);
 d.observations=[point(19400,40010),point(20000,40000)];assert.equal(P.progress(d).seconds,null);
 d.observations=[point(19000,39950),point(19400,39975)];assert.equal(P.progress(d).seconds,null);
 d.observations=[point(19400,39950),point(19700,39975,{state:'paused'}),point(20000,40000)];assert.equal(P.progress(d).seconds,null);
});
test('invalid, absent and zero totals remain bounded and non-misleading',()=>{
 const d=base();d.summary.total=0;assert.equal(P.progress(d).percent,0);assert.equal(P.progress(d).eta,'Waiting for games');
 d.summary.total=100;d.summary.completed=110;assert.equal(P.progress(d).percent,100);
 d.summary.completed=10;d.summary.progress.eta_seconds=Infinity;assert.equal(P.progress(d).seconds,null);
});
