const test=require('node:test'),assert=require('node:assert/strict');
const Board=require('../ui/board3d.js');
const vm=require('node:vm'),fs=require('node:fs');
test('3D camera reserves left drag for chess and supports right / Alt-left drag',()=>{
 assert(!Board.cameraGesture({button:0,altKey:false}));assert(Board.cameraGesture({button:2}));assert(Board.cameraGesture({button:0,altKey:true}));assert(!Board.cameraGesture({button:1,altKey:true}));
});
test('Shared camera movement preserves unrelated axes and honors wheel units',()=>{
 const p=Board.settings({angle:45,orbit:20,zoom:1.2,lift:.1,tilt:0});
 assert.deepEqual(Board.dragSettings(p,30,20,400,false),{angle:50,orbit:32,zoom:1.2,lift:.1,tilt:0});
 assert.deepEqual(Board.dragSettings(p,30,20,400,true),{...p,lift:.05});
 assert.equal(Board.wheelSettings(p,{deltaY:3,deltaMode:1},500).zoom,Board.wheelSettings(p,{deltaY:48,deltaMode:0},500).zoom);
 assert.equal(Board.wheelSettings(p,{deltaY:.096,deltaMode:2},500).zoom,Board.wheelSettings(p,{deltaY:48,deltaMode:0},500).zoom);
 assert.equal(Board.dragSettings(p,0,10000,0,true).lift,-.5);
});
test('Ordinary mouse drag continues above the board and reverses smoothly',()=>{
 const p=Board.settings({angle:16,orbit:20,zoom:1.2,lift:.1});
 const up=Board.dragSettings(p,0,-80,400,false);
 assert.deepEqual(up,{...p,angle:6,tilt:10});
 const higher=Board.dragSettings(up,0,-40,400,false);
 assert.deepEqual(higher,{...p,angle:6,tilt:20});
 assert.deepEqual(Board.dragSettings(higher,0,120,400,false),p);
 assert.deepEqual(Board.dragSettings(up,40,0,400,false),{...up,orbit:36});
 assert(Math.abs(Board.dragSettings(up,0,-20,400,true).lift-.15)<1e-10);
 const top=Board.dragSettings(p,0,-10000,0,false),bottom=Board.dragSettings(p,0,10000,0,false);
 assert.equal(top.angle,6);assert.equal(top.tilt,70);
 assert.equal(bottom.angle,78);assert.equal(bottom.tilt,-7);
 // Every pixel moves continuously through the horizon; no forced jump or flip.
 let previous=p.angle-p.tilt;
 for(let dy=0;dy>=-400;dy--){const c=Board.dragSettings(p,0,dy,400,false),look=c.angle-c.tilt;assert(look<=previous);assert(previous-look<=.250001);previous=look;assert(c.angle>=6)}
});
test('Player camera keys support tilt and preserve browser shortcuts',()=>{
 const context={ArenaBoard3D:Board};vm.createContext(context);vm.runInContext(fs.readFileSync(require.resolve('../ui/player-board.js'),'utf8')+';globalThis.PB=PlayerBoard',context);
 const b=Object.create(context.PB.prototype);b.camera=Board.settings({});b.host={clientHeight:400};b.paint=()=>{};b.saveCamera=()=>{};let prevented=0;
 for(const modifier of ['ctrlKey','metaKey','altKey']){const before={...b.camera};assert.equal(b.cameraKey({key:'+',preventDefault:()=>prevented++,[modifier]:true}),false);assert.deepEqual(b.camera,before)}
 assert.equal(prevented,0);assert.equal(b.cameraKey({key:'ArrowRight',preventDefault:()=>prevented++}),true);assert.equal(b.camera.orbit,5);assert.equal(prevented,1);
 b.camera=Board.settings({angle:6});const before={...b.camera};assert.equal(b.cameraKey({key:'ArrowUp',preventDefault:()=>prevented++}),true);assert.deepEqual(b.camera,{...before,tilt:3});
 assert.equal(b.cameraKey({key:'ArrowDown',preventDefault:()=>prevented++}),true);assert.deepEqual(b.camera,before);
});
