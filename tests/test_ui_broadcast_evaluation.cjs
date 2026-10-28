const test=require('node:test'),assert=require('node:assert/strict');
const {broadcastEvaluation,paintBroadcastEvaluation}=require('../ui/broadcast.js');
const ArenaEval=require('../ui/evaluation.js');
test('broadcast scores agree with the regular bar for centipawns, mates, zero and missing scores',()=>{
 for(const info of [{cp:125},{cp:-87},{cp:0},{cp:10000},{cp:-10000},{mate:5},{mate:-2},{mate:0},{cp:25,mate:-3},{},{cp:null},{cp:NaN},{mate:Infinity}]){
  for(const side of ['white','black']){
   const game={info,clock_active:side},actual=broadcastEvaluation(game),expected=ArenaEval.project(game);
   for(const key of ['available','label','white'])assert.equal(actual[key],expected[key],JSON.stringify({info,side,key}));
   if(expected.available)assert.equal(actual.direction,expected.direction);
  }
 }
});
test('the rendered bar follows score changes and both board orientations',()=>{
 const classes=new Set(),attributes={};
 const bar={classList:{toggle(k,on){on?classes.add(k):classes.delete(k)}},setAttribute(k,v){attributes[k]=v}};
 const label={textContent:''},fill={style:{}};
 for(const flip of [false,true]){
  for(const cp of [100,-100,0]){
   paintBroadcastEvaluation(bar,label,fill,{info:{cp}},flip);
   assert.equal(classes.has('flipped'),flip);assert.equal(classes.has('white-favored'),cp>=0);
   assert.equal(classes.has('unavailable'),false);assert.equal(fill.style.height,50+cp/10+'%');
   assert.ok(attributes['aria-label'].includes('White perspective'));
  }
 }
 paintBroadcastEvaluation(bar,label,fill,null,false);
 assert.equal(label.textContent,'—');assert.equal(classes.has('unavailable'),true);
 assert.equal(attributes['aria-label'],'Evaluation unavailable');
 paintBroadcastEvaluation(bar,label,fill,{info:{mate:-2}},false);
 assert.equal(label.textContent,'−M2');assert.equal(classes.has('unavailable'),false);
 assert.equal(classes.has('white-favored'),false);assert.equal(fill.style.height,'0%');
});
test('configured evaluation range matches the focused-game scale without changing labels',()=>{
 for(const range of [.1,4,5,12])for(const cp of [-600,-75,0,75,600]){
  const game={info:{cp}},actual=broadcastEvaluation(game,range),expected=ArenaEval.project(game,{range});
  assert.equal(actual.label,expected.label);assert.ok(Math.abs(actual.white-expected.white)<1e-10);
 }
});
