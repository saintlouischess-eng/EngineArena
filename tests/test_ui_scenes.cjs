const test=require('node:test'),assert=require('node:assert/strict'),S=require('../ui/board3d-model.js');
test('Scene defaults remain demand-rendered and preferences are bounded',()=>{
 const p=S.settings({});assert.equal(p.mode,'testing');assert.equal(p.environment,'club');assert.equal(p.highlight,.38);
 assert.equal(p.trays,false);assert.equal(S.settings({fps:500,brightness:50,highlight:0}).fps,30);assert.equal(S.settings({brightness:50}).brightness,1.4);assert.equal(S.settings({highlight:0}).highlight,.2);
 assert.equal(p.board,'classic');assert.equal(p.coordinates,true);
 assert.equal(S.settings({board:'unknown'}).board,'classic');
 for(const board of ['classic','drueke','jaques'])assert.equal(S.settings({board,coordinates:false}).board,board);
 assert.equal(S.settings({coordinates:false}).coordinates,false);
 // Old saved numeric/string choices must use the new ceiling without losing
 // the room, quality or movement preferences on reload or a workspace switch.
 for(const fps of [60,'60']){
  const saved={environment:'live-club',quality:'high',live:true,people:true,motion:'smooth',fps};
  const restored=S.settings(JSON.parse(JSON.stringify(saved)));
  assert.deepEqual(restored,S.settings({...saved,fps:30}));assert.equal(restored.fps,30);
  assert.deepEqual(S.settings(restored),restored);
 }
 for(const fps of [15,30,'15','30'])assert.equal(S.settings({fps}).fps,Number(fps));
});
test('Cinematic path covers varied views and stays continuous through every segment and wrap',()=>{
 const base={angle:47,orbit:173,zoom:1.03,lift:.05,tilt:12},wrap=n=>(n+540)%360-180;
 assert.deepEqual(S.tourCamera(0,base),base);
 const poses=[];let maxStep=0;
 for(let time=0;time<400;time+=.05){const p=S.tourCamera(time,base);assert(p.angle>=12&&p.angle<=78);assert(p.zoom>=.6&&p.zoom<=2.4);assert(p.orbit>=-180&&p.orbit<=180);if(poses.length)maxStep=Math.max(maxStep,Math.abs(wrap(p.orbit-poses.at(-1).orbit)));poses.push(p)}
 assert(maxStep<.2,'No orientation jumps');assert(Math.max(...poses.map(p=>p.angle))-Math.min(...poses.map(p=>p.angle))>35);assert(Math.max(...poses.map(p=>p.zoom))-Math.min(...poses.map(p=>p.zoom))>.15);
 for(const t of [24,48,72,96,120,144,168,192,216,384]){const a=S.tourCamera(t-.01,base),b=S.tourCamera(t,base),c=S.tourCamera(t+.01,base);for(const k of ['angle','zoom','lift','orbit']){const d1=k==='orbit'?wrap(b[k]-a[k]):b[k]-a[k],d2=k==='orbit'?wrap(c[k]-b[k]):c[k]-b[k];assert(Math.abs(d2-d1)<.0001,k+' velocity continuity at '+t)}}
 assert.equal(S.settings({}).tour,'cinematic');assert.equal(S.settings({tourSpeed:20}).tourSpeed,1.5);
});
test('Normal moves, captures, en passant, castling and promotion have coherent display transitions',()=>{
 const cases=[
 ['8/8/8/8/8/8/4P3/4K2k w - - 0 1','8/8/8/8/4P3/8/8/4K2k b - - 0 1','e2e4',1,[]],
 ['7k/8/8/3pP3/8/8/8/7K w - d6 0 1','7k/8/3P4/8/8/8/8/7K b - - 0 1','e5d6',1,['d5']],
 ['4k3/8/8/8/8/8/8/4K2R w K - 0 1','4k3/8/8/8/8/8/8/5RK1 b - - 1 1','e1g1',2,[]],
 ['4k3/8/8/8/8/8/8/4K2R w H - 0 1','4k3/8/8/8/8/8/8/5RK1 b - - 1 1','e1h1',2,[]],
 ['1r5k/P7/8/8/8/8/8/7K w - - 0 1','1Q5k/8/8/8/8/8/8/7K b - - 0 1','a7b8q',1,['b8']],
 ];
 for(const [a,b,uci,n,removed] of cases){const p=S.transition(a,b,uci);assert(p,uci);assert.equal(p.moves.length,n);assert.deepEqual(p.removed,removed)}
 assert(S.transition(...cases[4].slice(0,3)).moves[0].promotion);
 assert.equal(S.transition(cases[0][0],cases[0][1].replace('0 1','0 4'),'e2e4'),null);
 assert.equal(S.transition(cases[0][1],cases[0][0],'e2e4'),null);
});

test('Live scenery defaults are opt-in and its independent controls survive normalization',()=>{
 const d=S.settings();assert.equal(d.live,false);assert.equal(d.ambience,false);
 const p=S.settings({live:true,activity:'busy',people:false,backgroundGames:false,atmosphere:false,ambience:true,ambienceVolume:92});
 assert.equal(p.live,true);assert.equal(p.activity,'busy');assert.equal(p.people,false);assert.equal(p.backgroundGames,false);assert.equal(p.atmosphere,false);assert.equal(p.ambience,true);assert.equal(p.ambienceVolume,50);
 assert.deepEqual(S.settings(p),p);assert.equal(S.settings({activity:'unknown',ambienceVolume:'oops'}).activity,'social');assert.equal(S.settings({ambienceVolume:'oops'}).ambienceVolume,15);
});
test('Room animation can override Windows without changing its preference or game settings',()=>{
 for(const reduced of [false,true]){
  assert.equal(S.roomMotionEnabled({},reduced),!reduced);
  assert.equal(S.roomMotionEnabled({roomMotion:'system'},reduced),!reduced);
  assert.equal(S.roomMotionEnabled({roomMotion:'animate'},reduced),true);
  assert.equal(S.roomMotionEnabled({roomMotion:'still'},reduced),false);
 }
 assert.equal(S.settings({roomMotion:'unknown'}).roomMotion,'system');
 for(const roomMotion of ['system','animate','still']){
  const saved=S.settings({roomMotion,fps:60,live:true});
  assert.deepEqual(S.settings(JSON.parse(JSON.stringify(saved))),saved);
 }
});
