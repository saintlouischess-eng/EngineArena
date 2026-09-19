const test=require('node:test'),assert=require('node:assert/strict');
const {format,project}=require('../ui/clocks.js');
const game=(control,remaining=60)=>({clock_active:'white',search_elapsed:3,clocks:{white:{control,remaining,stage:1}}});
test('clock format includes hours, tenths and nonnegative bounds',()=>{
 assert.equal(format(3661.29),'1:01:01.2');assert.equal(format(60),'01:00.0');assert.equal(format(-1),'00:00.0');
});
test('countdown projects between updates; committed snapshots do not double-charge',()=>{
 const g=game({kind:'fischer',increment:2});assert.equal(project(g,'white',500).text,'00:56.5');
 g.clock_active=null;g.clocks.white.remaining=59;assert.equal(project(g,'white',500).text,'00:59.0');
});
test('both delay controls preserve bank during the free interval',()=>{
 for(const kind of ['delay','bronstein']){const g=game({kind,delay:5});assert.equal(project(g,'white',500).text,'01:00.0');g.search_elapsed=7;assert.equal(project(g,'white',0).text,'00:58.0');}
});
test('pure nodes and depth count elapsed time without a chess-clock limit',()=>{
 for(const kind of ['nodes','depth']){const g=game({kind,nodes:1000,depth:12},null);assert.equal(project(g,'white',400).text,'00:03.4');assert.match(project(g,'white').detail,/no chess clock/);g.clock_active=null;g.clocks.white.elapsed=2.25;assert.equal(project(g,'white').text,'00:02.2');}
});
test('fixed time per move and stages are explicit',()=>{
 const g=game({kind:'movetime',seconds:10},null);assert.equal(project(g,'white',500).text,'00:06.5');g.clock_active=null;assert.equal(project(g,'white').text,'00:10.0');
 assert.equal(project(game({kind:'staged',repeat:true}),'white').detail,'Stage 2 · repeating');
});
test('lost updates freeze projected time and remove the thinking highlight',()=>{
 const g=game({kind:'sudden_death'}),p=project(g,'white',8000);assert.equal(p.text,'00:54.5');assert.equal(p.active,false);assert.equal(p.stale,true);assert.equal(p.label,'Waiting for update');
});
