// Disposable rendering fixture: board geometry/materials, UI and GPU lifetime.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const ready=JSON.parse(fs.readFileSync(process.env.ARENA_SCENE_READY||'test-output/workflow-ready.json')),
 out=process.env.ARENA_BOARD_OUT||'test-output/boards-source';assert(ready.folder.includes('test-output'));fs.mkdirSync(out,{recursive:true});
const start='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',empty='8/8/8/8/8/8/8/8 w - - 0 1';
(async()=>{const browser=await chromium.launch({headless:true,channel:'msedge'}),proof={passed:false,errors:[],boards:[]};
 try{
  const p=await browser.newPage({viewport:{width:1600,height:1200}});p.on('pageerror',e=>proof.errors.push(e.stack));p.on('console',m=>{if(m.type()==='error'||/WebGL: INVALID|GL_INVALID/.test(m.text()))proof.errors.push(m.text())});
  await p.goto(ready.url);await p.waitForFunction(()=>state.snapshot);
  await p.evaluate(async()=>{await ArenaBoard3D.prepare();const c=document.createElement('canvas');c.id='boardReview';c.style='position:fixed;inset:0;width:100vw;height:100vh;z-index:9999';document.body.append(c);window.reviewBoard=ArenaBoard3D.create(c,()=>{})});
  const draw=async(board,fen,camera={},coords=false,details=false)=>{
   await p.evaluate(({board,fen,camera,coords,details})=>reviewBoard.render(fen,false,{angle:54,orbit:24,zoom:.85,...camera},false,'',['g1','h1','g8','h8'],'inward',{}, {key:'boards',white:'Stockfish 19',black:'Reckless',captured:['P','p']}, {board,coordinates:coords,environment:'study',surface:'felt',lighting:'daylight',quality:'high',trays:details,plates:details,plaque:details,motion:'instant'}),{board,fen,camera,coords,details});
   assert(await p.evaluate(()=>reviewBoard.ready()));
   assert.equal(await p.locator('#boardReview').getAttribute('data-board-design'),board);
   assert.equal(await p.locator('#boardReview').getAttribute('data-coordinate-count'),coords?'16':'0');
   assert.equal(await p.locator('#boardReview').evaluate(c=>c.getContext('webgl2').getError()),0);
  };
  for(const board of ['classic','drueke','jaques']){
   await draw(board,empty);const clean=await p.screenshot({path:out+'/'+board+'-empty.png'});
   await draw(board,empty,{},false,true);await draw(board,empty);
   assert((await p.screenshot()).equals(clean),'Hiding table details must remove their cached shadows');
   await draw(board,empty,{angle:22,orbit:25,zoom:.86});await p.screenshot({path:out+'/'+board+'-edge.png'});
   await draw(board,start,{},true,true);await p.screenshot({path:out+'/'+board+'-playing.png'});
   await draw(board,start,{angle:40,orbit:30,zoom:.81});
   const photo=Buffer.from((await p.evaluate(()=>reviewBoard.photo({width:3840,height:2160,blur:.15}))).split(',')[1],'base64');
   assert.equal(photo.readUInt32BE(16),3840);assert.equal(photo.readUInt32BE(20),2160);fs.writeFileSync(out+'/'+board+'-4K.png',photo);
   proof.boards.push({board,memory:await p.evaluate(()=>reviewBoard.metrics()),photoBytes:photo.length});
  }
  const before=await p.evaluate(()=>reviewBoard.metrics());
  for(let i=0;i<18;i++)await draw(['classic','drueke','jaques'][i%3],i%2?start:empty,{angle:20+i*3,orbit:i*35-180},i%2===0);
  assert.deepEqual(await p.evaluate(()=>reviewBoard.metrics()),before);proof.repeatedSwitchesStable=true;proof.hiddenDetailsLeaveNoShadows=true;
  await p.evaluate(()=>{reviewBoard.dispose();document.querySelector('#boardReview').remove();boardViewDialog()});
  await p.locator('#sceneBoard').selectOption('jaques');await p.locator('#sceneCoordinates').uncheck();await p.locator('#applyBoardView').click();
  await p.evaluate(()=>persistDisplay());await p.reload();await p.waitForFunction(()=>state.snapshot);
  assert.equal(await p.evaluate(()=>displayPrefs.scene3d.board),'jaques');assert.equal(await p.evaluate(()=>displayPrefs.scene3d.coordinates),false);proof.preferencesRetained=true;
  await p.evaluate(()=>boardViewDialog());await p.locator('#sceneBoard').scrollIntoViewIfNeeded();await p.screenshot({path:out+'/board-selector.png'});
  assert.deepEqual(proof.errors,[]);proof.passed=true;
 }finally{await browser.close();fs.writeFileSync(out+'/result.json',JSON.stringify(proof,null,2))}
 console.log('Board acceptance passed: '+out);
})().catch(e=>{console.error(e);process.exitCode=1});
