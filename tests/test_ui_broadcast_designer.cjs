const test=require('node:test'),assert=require('node:assert/strict'),M=require('../ui/broadcast-model.js');
test('large field completes every selected page before changing category',()=>{
 const data={summary:{standings:Array.from({length:400},(_,i)=>({rank:i+1}))},ratings:Array.from({length:40},(_,i)=>({id:String(i),rank:i+1})),field_rating_ids:['0','2']};
 const c={show_ratings:true,standings_limit:20,ratings_limit:30,rows:10},p={type:'rotation'};
 assert.deepEqual(M.pages(c,data,p).map(p=>[p.type,p.rows[0].rank]),[['standings',1],['standings',11],['ratings',1],['ratings',11],['ratings',21]]);
 c.standings_limit=0;assert.equal(M.pages(c,data,p).length,43);c.rating_scope='field';assert.equal(M.pages(c,data,p).at(-1).rows.length,2);
});
test('presets adapt small pools, have distinct looks and safe geometry',()=>{
 const themes=new Set();for(const key of Object.keys(M.presetInfo)){const s=M.preset(key,8);themes.add(s.appearance.theme);for(const p of s.panels){assert.ok(p.x>=0&&p.x+p.w<=100&&p.y+p.h<=100);assert.equal(p.limit,0);assert.equal(p.rows,8)}}assert.ok(themes.size>=6);
 const d=M.preset('match',2);assert.equal(d.panels.find(p=>p.type==='scoreboard').rows,2);
});
test('scene appearance inherits, nested overrides merge and history restores moves',()=>{
 const s=M.preset('club'),c={scene3d:{brightness:1.2},ticker_style:{outcome_color:'#ffffff'},design:{active:s.id,scenes:[s]}};
 assert.equal(M.effective(c).scene3d.brightness,1.2);assert.equal(M.effective(c).scene3d.environment,'live-club');
 const h=new M.History(),p={x:5,y:6,w:30,h:40};h.push(p);const moved=M.geometry(p,100,-100);assert.deepEqual(moved,{x:70,y:0,w:30,h:40});assert.deepEqual(h.undo(moved),p);assert.deepEqual(h.redo(p),moved);
});
