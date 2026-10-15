// Render the actual app material on an isolated fixture, including unchanged surfaces.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const ready=JSON.parse(fs.readFileSync(process.env.ARENA_EBONY_READY||'test-output/workflow-ready.json','utf8'));
assert(ready.folder.includes('test-output')&&path.basename(ready.folder).startsWith('workflow-'));
const study=process.argv.includes('--study'),out=process.env.ARENA_EBONY_OUT||'test-output/ebony-'+(study?'study':'final');fs.mkdirSync(out,{recursive:true});
const views=[
 ['board','rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1',{angle:45,orbit:20},false],
 ['black','8/8/8/8/1rnbqk2/8/8/8 w - - 0 1',{angle:27,orbit:180,zoom:1.9},false],
 ['light','8/8/8/8/1rnbqk2/8/8/8 w - - 0 1',{angle:42,orbit:145,zoom:1.7},true],
 ['white','8/8/8/8/1RNBQK2/8/8/8 w - - 0 1',{angle:32,orbit:15,zoom:1.7},false],
 ['empty','8/8/8/8/8/8/8/8 w - - 0 1',{angle:50,orbit:0},false]
];
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--enable-unsafe-swiftshader']}),errors=[],proof={passed:false,views:[]};
 try{
  const original=study?fs.readFileSync('test-output/board3d-studio-before-v1511.js','utf8'):'';
  for(const variant of study?['before','satin-ebony','polished-ebony']:['after']){
   const page=await browser.newPage({viewport:{width:1600,height:1100}});page.on('pageerror',e=>errors.push(e.stack));
   if(study){
    const extra=variant==='satin-ebony'?'m.color.set(0x1d1916);m.roughness=.32;m.clearcoat=.22;m.clearcoatRoughness=.34;':variant==='polished-ebony'?'m.color.set(0x171411);m.roughness=.28;m.clearcoat=.26;m.clearcoatRoughness=.30;':'';
    const code=original.replace('const mesh=new T.Mesh(geometry,m);',`if(!white){${extra}}const mesh=new T.Mesh(geometry,m);`);
    await page.route('**/assets/board3d-studio.js',route=>route.fulfill({body:code,contentType:'text/javascript'}));
   }
   await page.goto(ready.url);await page.waitForFunction(()=>state.snapshot);
   await page.evaluate(async()=>{displayPrefs.focus3d=false;renderFocus();await ArenaBoard3D.prepare();const c=document.createElement('canvas');c.id='ebonyReview';c.style='position:fixed;inset:0;width:100vw;height:100vh;z-index:9999';document.body.append(c);window.ebonyBoard=ArenaBoard3D.create(c,()=>{});});
   for(const [name,fen,prefs,light] of views){
    await page.evaluate(({fen,prefs,light})=>ebonyBoard.render(fen,false,prefs,light,'',fen.startsWith('rnbqkbnr/')?['g1','h1','g8','h8']:[]),{fen,prefs,light});
    assert.equal(await page.locator('#ebonyReview').evaluate(c=>c.getContext('webgl2').getError()),0);
    assert.equal(await page.locator('#ebonyReview').getAttribute('data-coordinate-count'),'16');
    if(name==='board')assert.equal(await page.locator('#ebonyReview').getAttribute('data-crown-count'),'4');
    await page.screenshot({path:`${out}/${variant}-${name}.png`});proof.views.push(`${variant}-${name}`);
   }
   const frames=await page.locator('#ebonyReview').getAttribute('data-frames');await page.waitForTimeout(1200);assert.equal(await page.locator('#ebonyReview').getAttribute('data-frames'),frames);
   await page.evaluate(()=>ebonyBoard.dispose());await page.close();
  }
  assert.deepEqual(errors,[]);proof.passed=true;proof.idleNoRedraw=true;
 }finally{await browser.close();fs.writeFileSync(out+'/result.json',JSON.stringify({...proof,errors},null,2))}
 console.log('Ebony renders, coordinates, crown marks and idle rendering passed: '+out);
})().catch(e=>{console.error(e);process.exitCode=1});
