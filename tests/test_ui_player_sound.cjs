const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
test('Focus sound follows new visible moves, not replay, switches or hidden boards',()=>{
 const c={window:{},matchMedia:()=>({matches:false}),performance:{now:()=>c.now},now:6000,calls:[],next:null,retainedFocus:null,document:{hidden:false,createElement:()=>({dataset:{}})},ArenaI18n:{t:x=>x},panels:{focus:{hidden:false,querySelector:()=>({append(){}})}},displayPrefs:{focusSound:true,focusSoundVolume:40},state:{view:'overview'},review:false};
 c.renderFocus=()=>{c.retainedFocus=c.next};c.reviewingRecordedMove=()=>c.review;
 vm.createContext(c);vm.runInContext(fs.readFileSync('ui/player-sound.js','utf8'),c);vm.runInContext('PlayerSound.play=(...args)=>calls.push(args)',c);
 const render=(game,ply,san='e4')=>{c.next={game,ply,san};c.renderFocus()};
 render('a',4);assert.equal(c.calls.length,0);render('a',5,'Nxe4');assert.equal(c.calls[0][0],'capture');assert.equal(c.calls[0][2],40);
 render('a',5);render('b',6);assert.equal(c.calls.length,1);
 c.review=true;render('b',7);c.review=false;c.panels.focus.hidden=true;render('b',8);c.panels.focus.hidden=false;
 c.state.view='playerArena';render('b',9);c.state.view='overview';c.document.hidden=true;render('b',10);c.document.hidden=false;
 c.displayPrefs.focusSound=false;render('b',11);c.displayPrefs.focusSound=true;
 assert.equal(c.calls.length,1);render('b',12,'O-O');assert.equal(c.calls.at(-1)[0],'castle');
 // Reading the independent scoresheet (or a resize-induced scroll) must not
 // silence the board when it is still displaying the live position.
 c.browsingRecordedMoves=()=>true;render('b',13,'Qh5+');assert.equal(c.calls.at(-1)[0],'check');
 const count=c.calls.length;for(let i=0;i<25;i++)render('b',13,'Qh5+');assert.equal(c.calls.length,count);
 c.review=true;render('b',14);c.review=false;render('b',14);assert.equal(c.calls.length,count);
 render('b',15,'e8=Q');assert.equal(c.calls.at(-1)[0],'promotion');
});

test('Ambient chess sounds are optional, quiet, visible-only and not replayed after enabling',()=>{
 const c={ArenaScene3D:require('../ui/board3d-model.js'),window:{},calls:[],now:6000,performance:{now:()=>c.now},matchMedia:()=>({matches:c.reduced||false}),document:{hidden:false,createElement:()=>({dataset:{}})},ArenaI18n:{t:x=>x},panels:{focus:{querySelector:()=>({append(){}})}},renderFocus(){}};
 vm.createContext(c);vm.runInContext(fs.readFileSync('ui/player-sound.js','utf8'),c);vm.runInContext('PlayerSound.play=(...args)=>calls.push(args)',c);
 const audio=c.window.ArenaRoomAudio,canvas={dataset:{roomSeconds:'0'}},p={environment:"live-club",live:true,ambience:false,backgroundGames:true,ambienceVolume:20,activity:'social'};
 audio.tick(canvas,p);canvas.dataset.roomSeconds='12';audio.tick(canvas,p);assert.equal(c.calls.length,0);
 p.ambience=true;audio.tick(canvas,p);assert.equal(c.calls.length,0);canvas.dataset.roomSeconds='24';audio.tick(canvas,p);assert.equal(c.calls.length,1);assert.equal(c.calls[0][2],9);
 audio.tick(canvas,p);assert.equal(c.calls.length,1);c.document.hidden=true;canvas.dataset.roomSeconds='36';audio.tick(canvas,p);assert.equal(c.calls.length,1);
 c.document.hidden=false;p.live=false;c.now+=6000;canvas.dataset.roomSeconds='48';audio.tick(canvas,p);assert.equal(c.calls.length,1);
 p.live=true;audio.tick(canvas,p);assert.equal(c.calls.length,1);p.backgroundGames=false;canvas.dataset.roomSeconds='60';audio.tick(canvas,p);assert.equal(c.calls.length,1);
 p.backgroundGames=true;c.reduced=true;audio.tick(canvas,p);assert.equal(c.calls.length,1);
 p.roomMotion='animate';audio.tick(canvas,p);canvas.dataset.roomSeconds='72';audio.tick(canvas,p);assert.equal(c.calls.length,2);
 p.roomMotion='still';canvas.dataset.roomSeconds='84';c.now+=6000;audio.tick(canvas,p);assert.equal(c.calls.length,2);
});
