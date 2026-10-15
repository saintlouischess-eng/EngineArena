'use strict';
// Heavy models/materials load only when the focused 3D board is requested.
const ArenaBoard3D=(()=>{
 let studio=null;const pending=new Map(),ready=new Set();
 const pieceSets=Object.freeze(['staunton1849','tal1962']);
 const pieceSet=value=>pieceSets.includes(value)?value:'staunton1849';
 const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
 const zoomRange=Object.freeze({min:.6,max:2.4,step:.1});
 const liftRange=Object.freeze({min:-.5,max:.5,step:.05});
 const tiltRange=Object.freeze({min:-30,max:70,step:2});
 const knightModes=Object.freeze(['inward','outward','forward','backward','left','right']);
 function knightMode(value){return knightModes.includes(value)?value:'inward'}
 function knightRotation(value,white,facing){
  const mode=knightMode(value),forward=white?-Math.PI/2:Math.PI/2;
  if(mode==='forward')return forward;
  if(mode==='backward')return -forward;
  if(mode==='left')return white?0:Math.PI;
  if(mode==='right')return white?Math.PI:0;
  // Unknown origins and promoted knights face forward. Their starting side
  // cannot be inferred reliably from a midgame square.
  if(facing!==1&&facing!==-1)return forward;
  return (mode==='outward'?-facing:facing)>0?Math.PI:0;
 }
 function settings(p={}){return {angle:clamp(Number(p.angle)||50,6,78),orbit:clamp(Number(p.orbit)||0,-180,180),zoom:clamp(Number(p.zoom)||1,zoomRange.min,zoomRange.max),lift:clamp(Number(p.lift)||0,liftRange.min,liftRange.max),tilt:clamp(Number(p.tilt)||0,tiltRange.min,tiltRange.max)}}
 function cameraGesture(e){return e.button===2||(e.button===0&&e.altKey)}
 function dragSettings(p,dx,dy,height,lift){
  if(lift)return settings({...p,lift:p.lift-dy/Math.max(1,height)});
  // Continue the same vertical gesture through the low viewing angle into an
  // upward look. Keep the camera above the table instead of orbiting underneath.
  let {angle,tilt}=settings(p),delta=dy*.25;
  if(delta<0){
   const unwind=Math.min(-delta,Math.max(0,-tilt));tilt+=unwind;delta+=unwind;
   const next=angle+delta;angle=Math.max(6,next);tilt+=Math.max(0,6-next);
  }else{
   const unwind=Math.min(delta,Math.max(0,tilt));tilt-=unwind;delta-=unwind;
   const next=angle+delta;angle=Math.min(78,next);tilt-=Math.max(0,next-78);
  }
  return settings({...p,orbit:p.orbit+dx*.4,angle,tilt:clamp(tilt,Math.max(tiltRange.min,angle-85),tiltRange.max)});
 }
 function wheelSettings(p,e,height){const pixels=e.deltaY*(e.deltaMode===1?16:e.deltaMode===2?height:1);return settings({...p,zoom:p.zoom*Math.exp(-clamp(pixels,-120,120)*.0015)})}
 function prepare(value){const set=pieceSet(value);if(!pending.has(set))pending.set(set,(async()=>{try{const m=await import('/assets/board3d-studio.js');await m.load(set);studio=m;ready.add(set)}catch(e){pending.delete(set);throw e}})());return pending.get(set)}
 function create(canvas,onLost,onReady,value){const set=pieceSet(value);if(!ready.has(set))throw Error('3D assets are not ready');return studio.create(canvas,onLost,settings,knightRotation,knightMode,onReady,set)}
 return {settings,zoomRange,liftRange,tiltRange,knightModes,knightMode,knightRotation,pieceSets,pieceSet,cameraGesture,dragSettings,wheelSettings,prepare,create,isReady:value=>ready.has(pieceSet(value))};
})();
if(typeof module!=='undefined')module.exports=ArenaBoard3D;
