const test=require('node:test'),assert=require('node:assert/strict');
const {Director,arrow}=require('../ui/focus-director.js');
const game=(id,n=1)=>({tid:'t',game:id,attempt:id+'a',number:n,white:{id:'wanted'},black:{id:'other'}});
test('follow exact profile, preserve finish hold and wait, manual skip',()=>{
 const d=new Director(),one=game('one'),two=game('two',2),end={...one,ended:100,result:'1-0'};
 const args={tid:'t',profile:'wanted',current:'one',retained:one,live:[one,two],recent:[],now:0,hold:3};
 assert.equal(d.select(args).game.game,'one');
 assert.equal(d.select({...args,live:[two],recent:[end]}).holding,true);
 assert.equal(d.select({...args,live:[two],recent:[end],now:2900}).game.result,'1-0');
 d.skip();assert.equal(d.select({...args,live:[two],recent:[end],now:2900}).game.game,'two');
 assert.equal(d.select({...args,live:[],recent:[end],now:4000}).waiting,true);
 assert.equal(d.select({...args,live:[{...two,white:{id:'different'}}],recent:[end],now:4000}).game.game,'one');
});
test('review and offline never switch boards; zero hold switches immediately',()=>{
 const d=new Director(),one=game('one'),end={...one,ended:100},two=game('two',2);
 const args={tid:'t',current:'one',retained:end,live:[two],recent:[end],now:1,hold:0};
 assert.equal(d.select({...args,review:true}).game.game,'one');
 assert.equal(d.select({...args,connected:false}).game.game,'one');
 assert.equal(d.select(args).game.game,'two');
});
test('PV arrow clears on stale position, ended search, move review and disabled',()=>{
 const hint={fen:'fen',from:'e2',to:'e4',uci:'e2e4'},g={fen:'fen',clock_active:'white',searches:{white:{info:{intention:hint}}}};
 assert.equal(arrow(g,true),hint);
 for(const v of [{...g,fen:'new'},{...g,ended:1},{...g,reviewing:true},{...g,clock_active:null},{...g,searches:{white:{complete:true,info:{intention:hint}}}}])assert.equal(arrow(v,true),null);
 assert.equal(arrow(g,false),null);assert.equal(arrow(g,true,false),null);
});
