// Isolated browser rehearsal. Every request is fulfilled with synthetic data or
// bundled UI files; no installed worker, tournament or OBS connection is used.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const root=process.cwd(),out=path.join(root,'test-output/broadcast-111');fs.mkdirSync(out,{recursive:true});
const config={tid:'fixture',title:'Broadcast appearance rehearsal',subtitle:'Synthetic data — not tournament results',preference:'any',follow:'',hold:15,move_seconds:.55,panel_seconds:24,ticker:true,ticker_mode:'scroll',ticker_seconds:150,ticker_size:26,results:true,upsets:true,leaders:true,milestones:true,show_ratings:true,category:'blitz',theme:'ocean',pieces:'classic',flip:false,sound:false,thinking_arrows:true,arrow_delay:1,board_light:'theme',board_dark:'theme',dark_lighten:0,eval_range:5};
const feed={config,connected:true,server_time:0,status:{active:28},ratings:[],headlines:[{text:'Alpha  1-0  Beta · checkmate'}],summary:{name:'Broadcast rehearsal',completed:36000,total:159600,active_participants:400,standings:Array.from({length:20},(_,i)=>({rank:i+1,name:'Test engine '+(i+1),points:150-i,games:200})),conditions:{time_control:{seconds:180,increment:2}}},game:{attempt:'same-game',fen:'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',phase:'Live',clock_active:'white',white:{name:'White engine',rating:3300},black:{name:'Black engine',rating:3280},info:{cp:100,depth:20},moves:[],clocks:{},revision:1}};
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--disable-gpu']});
 const errors=[];try{
  const ctx=await browser.newContext({viewport:{width:1920,height:1080}});
  ctx.on('page',p=>p.on('pageerror',e=>errors.push(e.message)));
  await ctx.route('**/*',async route=>{
   const u=new URL(route.request().url());assert.equal(u.hostname,'broadcast.test');
   if(u.pathname==='/feed')return route.fulfill({json:feed});
   if(u.pathname==='/config'){
    if(route.request().method()==='POST')Object.assign(config,route.request().postDataJSON());
    return route.fulfill({json:{config,viewer_url:'http://broadcast.test/view?key=fixture'}});
   }
   if(u.pathname==='/tournaments')return route.fulfill({json:[{id:'fixture',name:'Synthetic tournament',state:'running'}]});
   const name=u.pathname==='/control'?'broadcast-control.html':u.pathname==='/view'?'broadcast.html':u.pathname.replace('/assets/','');
   const file=path.resolve(root,'ui',name);assert.ok(file.startsWith(path.join(root,'ui')+path.sep));
   const type=name.endsWith('.js')?'text/javascript':name.endsWith('.css')?'text/css':name.endsWith('.png')?'image/png':name.endsWith('.svg')?'image/svg+xml':'text/html';
   return route.fulfill({body:fs.readFileSync(file),contentType:type});
  });
  const control=await ctx.newPage();await control.goto('http://broadcast.test/control?key=control');
  await control.waitForFunction(()=>document.querySelector('[name=tid]').value==='fixture');
  await control.locator('#warmTvPreset').click();assert.equal(config.theme,'ocean','Preset must not apply without saving');
  await control.locator('button[type=submit]').click();
  await control.waitForFunction(()=>document.querySelector('#message').textContent.startsWith('Applied'));
  for(const [k,v]of Object.entries({theme:'charcoal',pieces:'classic-bold',board_light:'ash',board_dark:'rosewood',dark_lighten:28,eval_range:4,ticker_seconds:150}))assert.equal(config[k],v,k);
  assert.equal(config.tid,'fixture');assert.equal(feed.game.attempt,'same-game');
  await control.reload();await control.waitForFunction(()=>document.querySelector('[name=dark_lighten]').value==='28');
  const page=await ctx.newPage();await page.goto('http://broadcast.test/view?key=fixture');
  await page.waitForFunction(()=>document.querySelector('#stage').className==='charcoal'&&document.querySelectorAll('#board .square').length===64);
  const appearance=await page.evaluate(()=>{
   const light=document.querySelector('.square:not(.dark)'),dark=document.querySelector('.square.dark');
   return {accent:getComputedStyle(document.querySelector('#stage')).getPropertyValue('--accent').trim(),light:getComputedStyle(light).backgroundImage,dark:getComputedStyle(dark).backgroundImage,piece:document.querySelector('#board img').getAttribute('src')};
  });
  assert.equal(appearance.accent,'#d6b98a');assert.ok(appearance.light.includes('ash.png'));assert.ok(appearance.dark.includes('rosewood.png')&&appearance.dark.includes('0.28'));
  assert.ok(appearance.piece.includes('/classic-bold/'));
  await page.waitForFunction(()=>Array.from(document.images).every(img=>img.complete&&img.naturalWidth>0));
  const labelState=()=>page.evaluate(()=>{
   const bar=document.querySelector('.eval-bar'),label=document.querySelector('#evalScore'),b=bar.getBoundingClientRect(),l=label.getBoundingClientRect();
   return {bottom:l.y+l.height/2>b.y+b.height/2,label:label.textContent,color:getComputedStyle(label).color,white:document.querySelector('#evalWhite').style.height};
  });
  assert.deepEqual(await labelState(),{bottom:true,label:'+1.00',color:'rgb(32, 38, 48)',white:'62.5%'});
  for(const [flip,cp,bottom] of [[false,-100,false],[true,-100,true],[true,100,false]]){
   config.flip=flip;feed.game.info.cp=cp;
   await page.waitForFunction(({flip,cp})=>document.querySelector('.eval-bar').classList.contains('flipped')===flip&&document.querySelector('#evalScore').textContent===(cp>0?'+1.00':'-1.00'),{flip,cp});
   assert.equal((await labelState()).bottom,bottom);
  }
  config.flip=false;feed.game.info={};await page.waitForFunction(()=>document.querySelector('.eval-bar').classList.contains('unavailable'));
  assert.equal(await page.locator('#evalScore').textContent(),'—');
  feed.game.info={cp:100,depth:20};await page.waitForFunction(()=>document.querySelector('#evalScore').textContent==='+1.00');
  const original=await page.locator('#ticker').textContent();
  feed.headlines=[{text:'Gamma  1/2-1/2  Delta · threefold repetition'},{text:'Epsilon  0-1  Zeta · checkmate'}];
  await page.waitForTimeout(1100);assert.equal(await page.locator('#ticker').textContent(),original,'Visible ticker must not change mid-pass');
  // Exercise a real CSS animation boundary without waiting 150 seconds.
  await page.evaluate(()=>{document.querySelector('#ticker').getAnimations()[0].currentTime=149900});
  await page.waitForFunction(()=>document.querySelector('#ticker').textContent.startsWith('Gamma'));
  assert.ok((await page.locator('#ticker').textContent()).includes('\u2003◆\u2003'));
  assert.deepEqual(await page.locator('#ticker .ticker-result').allTextContents(),['1/2-1/2','threefold repetition','0-1','checkmate']);
  assert.equal(await page.locator('#ticker .ticker-result').first().evaluate(e=>getComputedStyle(e).color),'rgb(214, 185, 138)');
  await page.evaluate(()=>{document.querySelector('#ticker').getAnimations()[0].currentTime=5000});
  await page.screenshot({path:path.join(out,'native-warm-tv.png')});
  await control.locator('details summary').click();
  await control.locator('[name=ticker_seconds]').fill('600');await control.locator('button[type=submit]').click();
  await page.waitForFunction(()=>document.querySelector('#ticker').style.animationDuration==='600s');
  assert.equal(config.ticker_seconds,600);assert.equal(feed.game.attempt,'same-game');
  assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(out,'browser-checks.json'),JSON.stringify({passed:true,appearance,checks:['preset staged then saved','appearance controls persist','native charcoal and grain','all piece images loaded','evaluation sign and flip','missing evaluation','ticker waits for real CSS boundary','accent scores and endings','diamond spacing','600-second slow ticker','featured game retained'],errors},null,2));
  console.log('Isolated broadcast UI checks passed.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
