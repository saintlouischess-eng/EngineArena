const test=require('node:test'),assert=require('node:assert/strict');
const Recovery=require('../ui/board3d-recovery.js');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));

test('Reopening a failed live-room workspace retains 2D until explicit retry',async()=>{
 let calls=0;const options={workspace:'navigation-test',active:()=>true,rebuild:()=>calls++,delay:5};
 const first=new Recovery(options);first.fail('live-context');first.dispose();
 const reopened=new Recovery(options);assert(reopened.failed);reopened.resume();await sleep(20);assert.equal(calls,0);
 reopened.retry();assert.equal(calls,1);reopened.ready();reopened.dispose();
 const final=new Recovery(options);assert.equal(final.phase,'ready');final.dispose();
});

test('Live-room loss never automatically reloads the scene, even after stable use',async()=>{
 let calls=0,now=0;const r=new Recovery({active:()=>true,rebuild:()=>calls++,delay:5,stable:60,now:()=>now});
 r.ready();now=100;r.fail('live-context');assert(r.failed);assert(!r.pending);
 r.resume();await sleep(20);assert.equal(calls,0);r.retry();assert.equal(calls,1);r.ready();
 now=1000;r.fail('live-context');await sleep(20);assert.equal(calls,1);r.dispose();
});

test('One automatic attempt per interruption burst; healthy use rearms recovery',async()=>{
 let calls=0,now=0;const r=new Recovery({active:()=>true,rebuild:()=>calls++,delay:5,stable:60,now:()=>now});
 r.ready();r.fail('context');assert(r.failed);await sleep(15);assert.equal(calls,1);assert.equal(r.phase,'retrying');
 r.ready();assert.equal(r.phase,'ready');r.fail('context');await sleep(15);assert.equal(calls,1);
 r.retry();assert.equal(calls,2);r.ready();now=61;r.fail('context');await sleep(15);assert.equal(calls,3);r.dispose();
});
test('Hidden boards defer recovery; reset and disposal cancel pending attempts',async()=>{
 let visible=false,calls=0;const r=new Recovery({active:()=>visible,rebuild:()=>calls++,delay:5});
 r.fail('context');await sleep(15);assert.equal(calls,0);assert(r.pending);
 visible=true;r.resume();r.reset();await sleep(15);assert.equal(calls,0);
 r.fail('context');visible=false;await sleep(15);assert.equal(calls,0);assert(r.pending);
 visible=true;r.resume();await sleep(15);assert.equal(calls,1);
 r.reset();r.fail('context');r.dispose();await sleep(15);assert.equal(calls,1);r.retry();assert.equal(calls,1);
});
test('Unavailable graphics stays in 2D; retry errors do not create a retry loop',async()=>{
 let calls=0;const r=new Recovery({active:()=>true,rebuild:()=>{calls++;r.fail('unavailable')},delay:5});
 r.fail('unavailable');await sleep(15);assert.equal(calls,0);r.retry();assert.equal(calls,1);assert(r.failed);
 await sleep(15);assert.equal(calls,1);r.dispose();
});
