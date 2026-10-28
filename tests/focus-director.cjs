const test=require('node:test'),assert=require('node:assert/strict');
const {Director,arrow,winningSettings,winningEstimate}=require('../ui/focus-director.js');
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

const winningGame=(id,cp,n=1)=>({...game(id,n),info:{cp},info_side:'white',clock_active:'white',ply:20});
const watchArgs=(live,extra={})=>({tid:'t',live,recent:[],current:'',retained:null,now:0,winning:{enabled:true},...extra});
test('winning watch requires a sustained advantage and never chases a higher score',()=>{
 const d=new Director(),a=winningGame('a',250),b=winningGame('b',100,2);
 let x=watchArgs([a,b]);assert.equal(d.select(x).waiting,true);
 assert.equal(d.select({...x,now:4999}).game,null);
 assert.equal(d.select({...x,now:5000}).game.game,'a');
 x={...x,current:'a',retained:a,now:15000,live:[a,winningGame('b',900,2)]};
 assert.equal(d.select(x).game.game,'a');
 // Default stay-until-finished also avoids jumping away after a reversal.
 assert.equal(d.select({...x,live:[winningGame('a',0),b],now:50000}).game.game,'a');
});
test('manual next switches immediately and cycles without automatic bouncing',()=>{
 const d=new Director(),a=winningGame('a',300),b=winningGame('b',400,2),c=winningGame('c',500,3);
 const winning={enabled:true,confirm:0};let x=watchArgs([a,b,c],{winning});
 assert.equal(d.select(x).game.game,'c');d.nextWinning(c);
 assert.equal(d.select({...x,current:'c',retained:c,now:10}).game.game,'b');d.nextWinning(b);
 assert.equal(d.select({...x,current:'b',retained:b,now:20}).game.game,'a');d.nextWinning(a);
 assert.equal(d.select({...x,current:'a',retained:a,now:30}).game.game,'c');
 const only=new Director();x=watchArgs([a],{winning});only.select(x);only.nextWinning(a);
 const waiting=only.select({...x,current:'a',retained:a,now:10});assert.equal(waiting.waiting,true);assert.equal(waiting.game.game,'a');
 assert.equal(only.select({...x,current:'a',retained:a,live:[a,b],now:11}).game.game,'b');
});
test('fade switching needs minimum viewing time and a sustained faded score',()=>{
 const d=new Director(),a=winningGame('a',400),b=winningGame('b',300,2),winning={enabled:true,confirm:0,stay:'fade',minimum:30,fade:15};
 let x=watchArgs([a,b],{winning});d.select(x);
 x={...x,current:'a',retained:a,live:[winningGame('a',20),b]};
 for(const now of [1000,20000,29999])assert.equal(d.select({...x,now}).game.game,'a');
 assert.equal(d.select({...x,now:30000}).game.game,'b');
});
test('winning watch preserves result hold, review, offline and exact-engine precedence',()=>{
 const d=new Director(),a=winningGame('a',400),b=winningGame('b',300,2),winning={enabled:true,confirm:0};
 let x=watchArgs([a,b],{winning});d.select(x);const end={...a,ended:100,result:'1-0'};
 x={...x,current:'a',retained:end,live:[b],recent:[end],now:100};
 assert.equal(d.select(x).holding,true);
 assert.equal(d.select({...x,now:3099}).game.result,'1-0');
 assert.equal(d.select({...x,now:3100,review:true}).game.game,'a');
 assert.equal(d.select({...x,now:3100,connected:false}).game.game,'a');
 assert.equal(d.select({...x,now:3100}).game.game,'b');
 assert.equal(new Director().select({...x,profile:'absent',hold:0,now:4000}).game.game,'a');
 const fresh=d.select({...x,tid:'other',live:[],recent:[],retained:null,current:'',now:4000});assert.equal(fresh.game,null);
});
test('winning scores use White perspective, mates and only fresh exact searches',()=>{
 assert.equal(winningEstimate(winningGame('b',-500)).side,'black');
 assert.equal(winningEstimate({...winningGame('b',0),info:{mate:-3}}).side,'black');
 for(const extra of [{ended:1},{reviewing:true},{info:{cp:900,score_bound:'lowerbound'}},{info:{wdl:[900,100,0]}}])assert.equal(winningEstimate({...winningGame('b',0),...extra}),null);
 const g={...winningGame('a',0),info:{},searches:{black:{ply:20,info:{cp:-400}}}};
 assert.equal(winningEstimate(g).side,'black');g.ply=23;assert.equal(winningEstimate(g),null);
 assert.deepEqual(winningSettings(),{enabled:false,pawns:2,confirm:5,stay:'finish',minimum:30,fade:15});
});
