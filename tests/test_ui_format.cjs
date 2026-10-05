const test=require('node:test');
const assert=require('node:assert/strict');
const f=require('../ui/format.js');
test('unbounded and unavailable estimates are distinct',()=>{
 assert.equal(f.number('+infinity'),'+∞');assert.equal(f.number('-infinity'),'−∞');
 assert.equal(f.number(null),'—');assert.equal(f.number(-.0001),'0.0');
 assert.equal(f.percent(null),'—');assert.equal(f.percent(1e-12),'<0.1%');
 assert.equal(f.percent(99.99999),'>99.9%');assert.equal(f.percent(100),'100.0%');
 assert.equal(f.bytes(524288),'512.00 KiB');assert.equal(f.bytes(2**30),'1.00 GiB');
 assert.equal(f.bytes(null),'—');
});
test('incomplete and degenerate paired estimates explain missing uncertainty',()=>{
 assert.match(f.uncertainty({pairs:0,games:1}),/completed opening pair/);
 assert.match(f.uncertainty({pairs:20,games:40,ci:null}),/Conservative/);
 assert.match(f.uncertainty({pairs:20,games:40,ci:null},'conservative'),/20 completed opening pairs/);
});
test('estimated LOS bounds never display false certainty while exact scores stay exact',()=>{
 assert.equal(f.los(0),'<0.1%');assert.equal(f.los(100),'>99.9%');
 assert.equal(f.los(99.96),'>99.9%');assert.equal(f.los(.001),'<0.1%');
 assert.equal(f.los(50),'50.0%');assert.equal(f.los(null),'—');
 assert.equal(f.percent(0),'0.0%');assert.equal(f.percent(100),'100.0%');
});
test('legacy search-thread aliases match resource precedence',()=>{
 for(const key of ['Threads','Number of Threads','MaxThreads','Max CPUs'])assert.equal(f.resourceOption({[key]:4},'threads'),key);
 assert.equal(f.resourceOption({'CPU Usage':100},'threads'),undefined);
 assert.equal(f.resourceOption({'Max CPUs':4,Threads:2},'threads'),'Threads');
});
