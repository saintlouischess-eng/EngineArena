const {test}=require('node:test'),assert=require('node:assert/strict');
const layout=require('../ui/focus-layout.js');
test('clock preferences preserve valid choices and recover malformed sizes',()=>{
 assert.deepEqual(layout.normalize(null),layout.defaults);
 const p=layout.normalize({placement:'split',arrangement:'stack',order:'board',height:500,digits:NaN,width:-5,names:false,details:false,boardMax:360});
 assert.equal(p.placement,'split');assert.equal(p.order,'board');assert.equal(p.height,220);assert.equal(p.digits,28);assert.equal(p.width,140);assert.equal(p.names,false);assert.equal(p.boardMax,360);
 assert.equal(layout.normalize({placement:'arbitrary',digits:'60'}).digits,28);
});
