// Bound live render targets and submit at most one unfinished GPU frame.
// Neither a fence poll nor resizing waits synchronously for the graphics driver.
export function drawingBudget(width,height,dpr,quality,live,maxSize=16384){
 width=Math.max(1,Math.round(width));height=Math.max(1,Math.round(height));
 const ratioLimit={low:1,balanced:1.5,high:2}[quality]||1;
 const pixels={low:1280*720,balanced:1920*1080,high:2560*1440}[quality]||1920*1080;
 const ratio=Math.min(Math.max(.1,dpr||1),ratioLimit,maxSize/width,maxSize/height,live?Math.sqrt(pixels/(width*height)):Infinity);
 return {width,height,ratio};
}
export function resizeDrawingBuffer(renderer,budget){
 const {width,height,ratio}=budget,current=renderer.getSize({set(x,y){this.x=x;this.y=y;return this}});
 if(current.x===width&&current.y===height&&renderer.getPixelRatio()===ratio)return false;
 // setPixelRatio followed by setSize would allocate the drawing buffer twice.
 renderer.setDrawingBufferSize(width,height,ratio);return true;
}
export class GPUFrameGate {
 constructor(gl){this.gl=gl;this.sync=null;this.disposed=false;this.skipped=0}
 available(){
  if(this.disposed||this.gl.isContextLost())return false;
  if(!this.sync)return true;
  const gl=this.gl,result=gl.clientWaitSync(this.sync,0,0);
  if(result===gl.TIMEOUT_EXPIRED){this.skipped++;return false}
  gl.deleteSync(this.sync);this.sync=null;
  if(result===gl.WAIT_FAILED)throw Error('Graphics frame completion check failed');
  return true;
 }
 submitted(){
  if(this.disposed||this.gl.isContextLost())return;
  if(this.sync)throw Error('Graphics frame submitted before its predecessor completed');
  this.sync=this.gl.fenceSync(this.gl.SYNC_GPU_COMMANDS_COMPLETE,0);
  if(!this.sync)throw Error('Graphics frame completion fence is unavailable');
  this.gl.flush();
 }
 async idle(){
  const deadline=performance.now()+30000;
  while(!this.available()){
   if(this.disposed||this.gl.isContextLost())throw Error('Graphics context is unavailable');
   if(performance.now()>deadline)throw Error('Graphics frame did not complete');
   await new Promise(resolve=>setTimeout(resolve,16));
  }
 }
 dispose(){if(this.sync&&!this.gl.isContextLost())this.gl.deleteSync(this.sync);this.sync=null;this.disposed=true}
}
