const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const lib=import('data:text/javascript;base64,'+fs.readFileSync('ui/board3d-budget.js').toString('base64'));
test('Fullscreen, portrait and high-DPI render targets have bounded area and preserve aspect',async()=>{
 const {drawingBudget}=await lib;
 for(const [width,height] of [[3840,2160],[2160,3840],[7680,4320],[500,900],[1920,1080]])for(const dpr of [1,1.25,2,3])for(const [quality,area] of [['low',1280*720],['balanced',1920*1080],['high',2560*1440]]){
  const b=drawingBudget(width,height,dpr,quality,true,4096),w=Math.floor(b.width*b.ratio),h=Math.floor(b.height*b.ratio);
  assert(w*h<=area);assert(w<=4096&&h<=4096);assert(Math.abs(w/h-width/height)<.005);
 }
 assert.equal(drawingBudget(3840,2160,1,'high',false).ratio,1);
});
test('Unchanged canvas incurs zero resizes; one allocation per viewport or quality change',async()=>{
 const {drawingBudget,resizeDrawingBuffer}=await lib;let w=1,h=1,r=1,writes=0;
 const renderer={getSize:v=>v.set(w,h),getPixelRatio:()=>r,setDrawingBufferSize:(x,y,z)=>{w=x;h=y;r=z;writes++}};
 const b=drawingBudget(3840,2160,2,'high',true);assert(resizeDrawingBuffer(renderer,b));
 for(let i=0;i<1000;i++)assert(!resizeDrawingBuffer(renderer,b));assert.equal(writes,1);
 assert(resizeDrawingBuffer(renderer,drawingBudget(2160,3840,2,'high',true)));assert.equal(writes,2);
 assert(resizeDrawingBuffer(renderer,drawingBudget(2160,3840,2,'low',true)));assert.equal(writes,3);
});
test('GPU timeout coalesces frames, never blocks, and cleans fences on completion/disposal',async()=>{
 const {GPUFrameGate}=await lib;let result=1,deletes=0,fences=0,lost=false;
 const gl={TIMEOUT_EXPIRED:1,CONDITION_SATISFIED:2,ALREADY_SIGNALED:3,WAIT_FAILED:4,SYNC_GPU_COMMANDS_COMPLETE:5,
  isContextLost:()=>lost,clientWaitSync:(s,flags,time)=>{assert.equal(flags,0);assert.equal(time,0);return result},
  deleteSync:()=>deletes++,fenceSync:()=>{fences++;return {}},flush:()=>{}};
 const gate=new GPUFrameGate(gl);assert(gate.available());gate.submitted();
 for(let i=0;i<1000;i++)assert(!gate.available());assert.equal(fences,1);assert.equal(deletes,0);
 assert.throws(()=>gate.submitted(),/predecessor/);result=2;assert(gate.available());assert.equal(deletes,1);
 gate.submitted();result=4;assert.throws(()=>gate.available(),/completion check/);assert.equal(deletes,2);
 result=3;gate.submitted();await gate.idle();assert.equal(deletes,3);gate.submitted();gate.dispose();assert.equal(deletes,4);assert(!gate.available());
 const lostGate=new GPUFrameGate(gl);lost=true;assert(!lostGate.available());await assert.rejects(()=>lostGate.idle(),/unavailable/);lostGate.dispose();
});
