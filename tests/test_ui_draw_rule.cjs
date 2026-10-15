const assert=require('node:assert/strict'),{test}=require('node:test');
const {progress}=require('../ui/draw-rule.js');
const fen=n=>`8/8/8/8/8/8/4k3/R3K3 w - - ${n} 80`;
test('FEN counter counts plies, not game length or wall time',()=>{
 assert.deepEqual(progress(fen(84)),{plies:84,limit:100,remaining:16,claims:true,reached:false});
 assert.equal(progress(fen(99)).remaining,1);assert.equal(progress(fen(100)).remaining,0);
 assert.equal(progress(fen(0)).remaining,100);assert.equal(progress(fen(149),false).remaining,1);
 assert.equal(progress(fen(150),false).reached,true);assert.equal(progress(fen(151),false).remaining,0);
 for(const f of ['',fen(-1),fen('oops'),fen(1.5)])assert.equal(progress(f),null);
});
