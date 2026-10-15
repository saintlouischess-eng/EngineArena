// Actual offline renderer on a disposable fixture; no production data access.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const ready=JSON.parse(fs.readFileSync(process.env.ARENA_BOXWOOD_READY||'test-output/workflow-ready.json'));
assert(ready.folder.includes('test-output')&&path.basename(ready.folder).startsWith('workflow-'));
const study=process.argv.includes('--study'),out=process.env.ARENA_BOXWOOD_OUT||'test-output/boxwood-'+(study?'study':'source');fs.mkdirSync(out,{recursive:true});
const full='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',pieces='8/8/1prnbqk1/8/1PRNBQK1/8/8/8 w - - 0 1';
const variants={before:'',soft:'m.roughness=.34;m.clearcoat=.24;m.clearcoatRoughness=.34;',polished:'m.roughness=.28;m.clearcoat=.30;m.clearcoatRoughness=.28;',lustrous:'m.roughness=.25;m.clearcoat=.42;m.clearcoatRoughness=.25;'};
(async()=>{const browser=await chromium.launch({headless:true,channel:'msedge'}),proof={passed:false,errors:[],views:[]};
 try{
  for(const variant of study?Object.keys(variants):['final']){
   const p=await browser.newPage({viewport:{width:1700,height:1100}});
   p.on('pageerror',e=>proof.errors.push(e.stack));p.on('console',m=>{if(m.type()==='error'||/WebGL: INVALID|GL_INVALID/.test(m.text()))proof.errors.push(m.text())});
   if(study){const code=fs.readFileSync('test-output/board3d-studio-before-v163.js','utf8').replace('const mesh=new T.Mesh(geometry,m);',`if(white){${variants[variant]}}const mesh=new T.Mesh(geometry,m);`);await p.route('**/assets/board3d-studio.js',r=>r.fulfill({body:code,contentType:'text/javascript'}))}
   await p.goto(ready.url);await p.waitForFunction(()=>state.snapshot);
   await p.evaluate(async()=>{displayPrefs.focus3d=false;renderFocus();await ArenaBoard3D.prepare();const c=document.createElement('canvas');c.id='boxwoodReview';c.style='position:fixed;inset:0;width:100vw;height:100vh;z-index:9999';document.body.append(c);window.reviewBoard=ArenaBoard3D.create(c,()=>{})});
   const draw=async(fen,environment,lighting,board,camera)=>{
    await p.evaluate(({fen,environment,lighting,board,camera})=>reviewBoard.render(fen,false,camera,false,'',fen.startsWith('rnbq')?['g1','h1','g8','h8']:['c4','d4','c6','d6'],fen.startsWith('rnbq')?'inward':'right',{}, {key:'boxwood'}, {environment,lighting,board,quality:'high',coordinates:false,plates:false,plaque:false,trays:false,surface:'felt',motion:'instant'}),{fen,environment,lighting,board,camera});
    assert(await p.evaluate(()=>reviewBoard.ready()));assert.equal(await p.locator('#boxwoodReview').evaluate(c=>c.getContext('webgl2').getError()),0);
   };
   const rooms=study?['club','study']:['club','study','hall','studio'];
   for(const room of rooms)for(const light of study?['tournament']:['daylight','tournament','evening']){
    await draw(pieces,room,light,'jaques',{angle:29,orbit:10,zoom:1.65,lift:.03});
    const name=variant+'-'+room+'-'+light;await p.screenshot({path:out+'/'+name+'.png'});proof.views.push(name);
   }
   for(const board of study?['drueke']:['classic','drueke','jaques']){
    await draw(full,'club','tournament',board,{angle:38,orbit:25,zoom:.90});
    assert.equal(await p.locator('#boxwoodReview').getAttribute('data-crown-count'),'4');await p.screenshot({path:out+'/'+variant+'-'+board+'.png'});
   }
   if(!study){
    await draw(pieces,'club','tournament','jaques',{angle:27,orbit:14,zoom:1.40,lift:.025});
    const png=Buffer.from((await p.evaluate(()=>reviewBoard.photo({width:3840,height:2160,blur:.4}))).split(',')[1],'base64');assert.equal(png.readUInt32BE(16),3840);assert.equal(png.readUInt32BE(20),2160);fs.writeFileSync(out+'/boxwood-4K.png',png);proof.photoBytes=png.length;
    const frames=await p.locator('#boxwoodReview').getAttribute('data-frames');await p.waitForTimeout(1500);assert.equal(await p.locator('#boxwoodReview').getAttribute('data-frames'),frames);proof.idleNoRedraw=true;
   }
   await p.evaluate(()=>{reviewBoard.dispose();document.querySelector('#boxwoodReview').remove()});await p.close();
  }
  assert.deepEqual(proof.errors,[]);proof.passed=true;
 }finally{await browser.close();fs.writeFileSync(out+'/result.json',JSON.stringify(proof,null,2))}
 console.log('Boxwood material review passed: '+out);
})().catch(e=>{console.error(e);process.exitCode=1});
