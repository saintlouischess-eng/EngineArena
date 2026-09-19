const test=require('node:test'),assert=require('node:assert/strict');
const {project,settings}=require('../ui/evaluation.js');
test('linear centipawns and clipping retain actual score',()=>{
 assert.equal(project({info:{cp:100}},{range:5}).white,60);
 assert.equal(project({info:{cp:-100}},{range:5}).white,40);
 const clipped=project({info:{cp:1350}},{range:5});assert.equal(clipped.white,100);assert.equal(clipped.label,'+13.50');
 assert.equal(project({info:{cp:0}}).white,50);
});
test('compressed scale is monotone, symmetric and reaches chosen range',()=>{
 const p=cp=>project({info:{cp}},{range:5,scale:'compressed'}).white;
 assert.ok(p(100)>60);assert.equal(p(500),100);assert.equal(p(-500),0);assert.equal(p(100)+p(-100),100);
});
test('mate, no score, invalid values and board orientation',()=>{
 assert.equal(project({info:{mate:-3}}).label,'−M3');assert.equal(project({info:{mate:-3}}).white,0);
 assert.equal(project({info:{mate:4}}).white,100);assert.equal(project({info:{cp:NaN}}).available,false);
 assert.equal(project({info:{mate:0},info_side:'white'}).white,0);
 const g={info:{cp:200}};assert.equal(project(g,{},true).white,project(g).white);assert.equal(project(g,{},true).flip,true);
 assert.equal(settings({range:0,width:999}).range,5);assert.equal(settings({width:999}).width,64);
});
test('pin an engine without mistaking its older search for the current position',()=>{
 const g={clock_active:'black',info_side:'black',info:{},searches:{white:{info:{cp:42},move_number:9,complete:true}}};
 assert.equal(project(g).available,false);const p=project(g,{source:'white'});assert.equal(p.label,'+0.42');assert.match(p.description,/last completed search at move 9/);
 assert.match(project(g,{source:'white'},false,false).description,/Updates unavailable/);
});
