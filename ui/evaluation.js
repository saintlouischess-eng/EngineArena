(function(root){
 'use strict';
 const defaults={focus:true,live:false,scale:'linear',range:5,width:30,source:'active'};
 function settings(value={}){
  const range=Number(value.range),width=Number(value.width);
  return {...defaults,...value,scale:['linear','compressed'].includes(value.scale)?value.scale:'linear',source:['active','white','black'].includes(value.source)?value.source:'active',range:Number.isFinite(range)&&range>0?range:5,width:Number.isFinite(width)?Math.max(18,Math.min(64,width)):30};
 }
 function project(game,value={},flip=false,connected=true){
  const s=settings(value),side=s.source==='active'?(game.clock_active||game.info_side||'white'):s.source;
  const search=game.searches?.[side],info=s.source==='active'?(game.info||{}):(search?.info||{});
  const mate=Number.isFinite(info.mate),cp=Number.isFinite(info.cp);
  if(!mate&&!cp)return {available:false,label:'—',white:50,flip,description:'Evaluation unavailable; this engine has not reported a score for the displayed search.'};
  const pawns=cp?info.cp/100:0,direction=mate?(Math.sign(info.mate)||(side==='white'?-1:1)):Math.sign(pawns);
  const limited=Math.max(-s.range,Math.min(s.range,pawns));
  const normalized=mate?direction:s.scale==='compressed'?Math.asinh(limited)/Math.asinh(s.range):limited/s.range;
  const label=mate?(direction<0?'−M':'M')+Math.abs(info.mate):(pawns>0?'+':'')+pawns.toFixed(2);
  const status=!connected?'Updates unavailable':search?.complete?'last completed search':game.clock_active===side?'current search':'last reported search';
  return {available:true,label,white:50+50*normalized,flip,direction,
   description:`${side==='white'?'White':'Black'} engine, ${status}${search?.move_number?' at move '+search.move_number:''}: ${label}${mate?'':' pawns'}, White perspective. Display range ±${s.range} pawns, ${s.scale} scale. Engine estimate, not a win probability.`};
 }
 const api={defaults,settings,project};if(typeof module==='object'&&module.exports)module.exports=api;else root.ArenaEval=api;
})(typeof globalThis==='object'?globalThis:this);
