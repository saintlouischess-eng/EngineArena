const test=require('node:test'),assert=require('node:assert/strict');
const T=require('../ui/text-format.js');
test('LOS bounds in sharing text do not imply certainty',()=>{
 assert.equal(T.los(100),'>99.9%');assert.equal(T.los(0),'<0.1%');
 assert.equal(T.los(null),'N/A');assert.equal(T.los(50),'50.00%');
 assert.equal(T.pct(100),'100.00%');
});

test('aligned text preserves long names, accents and wide characters without truncation',()=>{
 const name='Engine with a very long configuration name / 駒 / café';
 const out=T.table(['Name','Score'],[[name,'50.00%'],['Other','0.00%']],{limits:[18,8],right:[1]});
 assert.ok(out.includes('configuration'));assert.ok(out.includes('café'));assert.ok(!out.includes('...'));
 assert.equal(T.width('駒'),2);assert.equal(T.width('café'),4);assert.equal(T.clean('a\tb\nc\u0000'),'a b c');
 const lines=out.split('\n');assert.equal(T.width(lines.find(l=>l.includes('50.00%'))),T.width(lines.find(l=>l.includes('0.00%')&&!l.includes('50.00%'))));
});
test('text statistics preserve zeros, unbounded intervals and selected confidence method',()=>{
 assert.equal(T.number(null),'N/A');assert.equal(T.number(0),'0.0');assert.equal(T.pct(0),'0.00%');
 assert.equal(T.interval(['-infinity','+infinity']),'-inf to +inf');
 const r={name:'Sample',rank:1,games:3,wins:1,draws:2,losses:0,points:2,score_pct:66.666666,draw_pct:66.666666,elo:null,ci:null,ci_conservative:['-infinity',123.4],los:null,pairs:1};
 const out=T.statsTable([r],99.9,'conservative');assert.ok(out.includes('99.9%'));assert.ok(out.includes('-inf to 123.4'));assert.ok(out.includes('66.67%'));assert.ok(out.includes('N/A'));
 assert.ok(!T.statsTable([r],99.9,'normal').includes('123.4'));
});
test('profile report uses effective UCI resources and hides personal paths by default',()=>{
 const p={name:'Alpha',threads:1,hash:16,path:'C:\\private\\engine.exe',args:['--personal'],options:{Threads:8,Hash:512,EvalFile:'C:\\private\\network.nnue'},time_control:{kind:'nodes',nodes:10000}};
 const out=T.profiles([p]);assert.ok(out.includes('10,000 nodes per move; no chess clock'));assert.ok(/^Threads\s+8$/m.test(out));assert.ok(/^Hash \(MB\)\s+512$/m.test(out));assert.ok(!out.includes('C:\\private'));assert.ok(!out.includes('--personal'));
 assert.ok(T.profiles([p],true).includes('C:\\private\\engine.exe'));assert.ok(T.profiles([p],true).includes('network.nnue'));
});
test('graph report identifies UTC timestamps, gaps, units and display sampling',()=>{
 const out=T.graph({title:'Nodes',unit:'nodes',timeAxis:true,note:'Latest 600 observations',series:[{name:'A',points:[{x:0,y:0},{x:2,y:100}]},{name:'B',points:[{x:1,y:50}]}]});
 assert.ok(out.includes('1970-01-01T00:00:00.000Z'));assert.ok(out.includes('0.0000'));assert.ok(out.includes('N/A'));assert.ok(out.includes('Displayed graph samples'));assert.ok(out.includes('Latest 600 observations'));
});
test('neural engine profile does not report unsupported transposition hash',()=>{
 const out=T.profiles([{name:'Lc0',hash:1024,threads:1,advertised:{Threads:{},NNCacheSize:{}},options:{NNCacheSize:20000000}}]);
 assert.ok(/^Hash \(MB\)\s+N\/A \(unsupported\)$/m.test(out));assert.ok(out.includes('20000000'));
});
test('forum and Markdown wrappers preserve aligned text and cannot end Markdown early',()=>{
 const value='Name    Points\nExample ``` code   0\n';assert.equal(T.codeBlock(value,'plain'),value);assert.equal(T.codeBlock('A\n','forum'),'[code]\nA\n[/code]');assert.ok(T.codeBlock(value,'markdown').startsWith('````text\n'));assert.ok(T.codeBlock(value,'markdown').endsWith('````'));
});
test('large participant exports avoid argument-stack limits and include the final row',()=>{
 const rows=Array.from({length:150000},(_,i)=>['Engine '+i,i]);const out=T.table(['Engine','Games'],rows);assert.ok(out.includes('Engine 149999'));
});
test('experiment text retains archived attempts and does not score missing accuracy as incorrect',()=>{
 const out=T.experiment({name:'Suite',kind:'suite',state:'paused',completed:1,total:1,accuracy_pct:0,results:[{profile:'A',case:{id:'position 1'},correct:null,official:false,reason:'interrupted'},{profile:'A',case:{id:'position 1'},correct:false,official:true,reason:'completed',elapsed_seconds:0,measured_nps:0}]});
 assert.ok(out.includes('Archived / interrupted'));assert.ok(out.includes('Official / completed'));assert.equal((out.match(/Incorrect/g)||[]).length,1);assert.ok(out.includes('0.00%'));assert.ok(out.includes('0.0000'));
});

test('benchmark text identifies active attempts, configured threads and NPS coverage',()=>{
 const out=T.experiment({name:'Speed',kind:'benchmark',state:'running',completed:2,total:3,failures:0,settings:{time_control:{kind:'nodes',nodes:100}},results:[{profile:'Engine',case:{id:'next'},official:false,ended:null}],benchmark_summary:[{profile:'Engine',threads:2,samples:2,nps_samples:1,mean_nps:100,min_nps:100,max_nps:100}]});
 assert.ok(out.includes('Running / running'));assert.ok(!out.includes('Archived / running'));
 assert.ok(out.includes('Benchmark averages')&&out.includes('1 / 2'));assert.ok(!out.includes('Solve s'));
});

test('Swiss sharing tables disclose awarded bye points without counting them as games',()=>{
 const r={name:'Bye engine',games:2,wins:0,draws:2,losses:0,points:3,bye_points:2,score_pct:50,draw_pct:100,pairs:1};
 const out=T.statsTable([r]);assert.ok(out.includes('Bye points'));
 assert.ok(/Bye engine\s+2\s+0\s+2\s+0\s+3\.0/.test(out));
 assert.ok(!T.statsTable([r].map(x=>({...x,bye_points:0}))).includes('Bye points'));
});
