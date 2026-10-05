const test=require('node:test'),assert=require('node:assert/strict');
const {numbered,score,seconds,nodes}=require('../ui/search.js');
test('number PVs from their searched move, including a Black start',()=>{
 assert.equal(numbered('e2e4 e7e5 g1f3 b8c6',1,'white'),'1. e2e4 e7e5 2. g1f3 b8c6');
 assert.equal(numbered('e7e5 g1f3 b8c6',8,'black'),'8… e7e5 9. g1f3 b8c6');
 assert.equal(numbered(['e1g1','a7a8q'],42,'white'),'42. e1g1 a7a8q');
 assert.equal(numbered('',3,'black'),'');assert.equal(numbered('g1f3',0),'1. g1f3');
});
test('scores distinguish missing values, mate, bounds and zero',()=>{
 assert.equal(score({cp:0}),'0.00');assert.equal(score({}),'—');assert.equal(score({mate:-2}),'M-2');
 assert.equal(score({cp:-23,score_bound:'upperbound'}),'≤ -0.23');
 assert.equal(score({cp:100,score_bound:'lowerbound'}),'≥ +1.00');
 assert.equal(seconds(0),'0.00 s');assert.equal(seconds(1234),'1.23 s');assert.equal(seconds(undefined),'—');
});
test('compact search counts retain zero and distinguish missing values at each unit',()=>{
 assert.equal(nodes(undefined),'—');assert.equal(nodes(NaN),'—');assert.equal(nodes(Infinity),'—');
 assert.equal(nodes(0),'0');assert.equal(nodes(999),'999');assert.equal(nodes(1000),'1.0k');
 assert.equal(nodes(1534200),'1.53M');assert.equal(nodes(1200000000),'1.20G');
});
