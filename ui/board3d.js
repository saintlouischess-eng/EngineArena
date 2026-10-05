'use strict';
// Heavy models/materials load only when the focused 3D board is requested.
const ArenaBoard3D=(()=>{
 let studio=null,pending=null;
 const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
 const zoomRange=Object.freeze({min:.6,max:2.4,step:.1});
 const liftRange=Object.freeze({min:-.5,max:.5,step:.05});
 function settings(p={}){return {angle:clamp(Number(p.angle)||50,25,78),orbit:clamp(Number(p.orbit)||0,-180,180),zoom:clamp(Number(p.zoom)||1,zoomRange.min,zoomRange.max),lift:clamp(Number(p.lift)||0,liftRange.min,liftRange.max)}}
 function prepare(){return pending??=(async()=>{try{const m=await import('/assets/board3d-studio.js');await m.load();studio=m}catch(e){pending=null;throw e}})()}
 function create(canvas,onLost){if(!studio)throw Error('3D assets are not ready');return studio.create(canvas,onLost,settings)}
 return {settings,zoomRange,liftRange,prepare,create,isReady:()=>!!studio};
})();
if(typeof module!=='undefined')module.exports=ArenaBoard3D;
