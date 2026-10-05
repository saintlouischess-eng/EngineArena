// Visual/layout acceptance against scripts/preview_design.py, never a user workspace.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/design-ready.json')),browser=await chromium.launch({headless:true,channel:'msedge'});
 const evidence=[],failures=[],errors=[];
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1060}});
  page.on('pageerror',e=>errors.push(e.message));
  // Changing a format can temporarily invalidate the draft (e.g. 8 engines to
  // two-engine SPRT). Those two preview endpoints deliberately return 400.
  page.on('response',r=>{if(r.status()>=400&&!(r.status()===400&&/\/api\/(schedule-preview|opening-preview)$/.test(r.url())))errors.push(`${r.status()} ${r.url()}`)});
  async function check(name,shot=false){
   const result=await page.evaluate(()=>{
    const visible=e=>e.getClientRects().length>0;
    const targets=[$('.view:not([hidden])'),...$$('#modal[open] .modal-head,#modal[open] .modal-body,#modal[open] .modal-foot')].filter(Boolean);
    return {overflow:targets.filter(e=>visible(e)&&e.scrollWidth>e.clientWidth+2).map(e=>e.id||e.className),documentOverflow:document.documentElement.scrollWidth>innerWidth+2,
      modal:$('#modal').open,bodyHeight:$('#modal').open?$('.modal-body').clientHeight:null,
      badImages:[...document.images].filter(e=>visible(e)&&e.complete&&!e.naturalWidth).map(e=>e.src)};
   });
   evidence.push({name,...result});if(result.overflow.length||result.documentOverflow||result.badImages.length||(result.modal&&result.bodyHeight<80))failures.push({name,...result});
   if(shot)await page.screenshot({path:`test-output/design-${name}.png`});
  }
  async function close(){await page.evaluate(()=>$('#modal').close())}
  async function openDialog(kind){
   await page.evaluate(async kind=>{
    const profiles=(await api('profiles')).items;state.selected=new Set(profiles.map(p=>p.id));
    switch(kind){case 'setup':await newTournament();break;case 'engine':editEngine(profiles[0]);break;
     case 'appearance':await displayDialog();break;case 'hardware':await hardwareDialog();break;
     case 'pgn':await pgnDialog();break;case 'ratings':await poolRatingsDialog();break;
     case 'event':await newEvent();break;case 'benchmark':newExperiment('benchmark');break;
     case 'suite':newExperiment('suite');break;case 'graph':await graphDialog();break;
     case 'clocks':$('#focusLayoutButton').click();break;case 'language':$('#languageButton').click();break;}
   },kind);
   await page.waitForSelector('#modal[open]');
  }
  for(const theme of ['dark','light'])for(const width of [1600,1050,2560]){
   const font=width===1050?20:14;await page.setViewportSize({width,height:width===1050?800:1060});
   await page.goto(ready.url);await page.waitForFunction(()=>state.snapshot&&$('#standings tbody tr'));
   await page.evaluate(({theme,font})=>{displayPrefs.theme=theme;displayPrefs.fontSize=font;applyDisplay()},{theme,font});
   for(const view of ['overview','tournamentQueue','events','engines','presets','experiments','health']){
    await page.locator(`aside [data-view=${view}]`).click();await page.mouse.move(1,1);await page.waitForTimeout(65);
    await check(`${theme}-${width}-${view}`,width===1600);
   }
   if(width===1600){
    await page.locator('aside [data-view=overview]').click();
    for(const kind of ['setup','engine','appearance','hardware','pgn','ratings','event','benchmark','suite','graph','clocks','language']){
     await openDialog(kind);await check(`${theme}-${kind}`,true);await close();
    }
   }
  }
  // Worst supported text size in every shipped language; no untranslated new UI.
  await page.setViewportSize({width:1050,height:800});
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await page.goto(ready.url+'&lang='+lang);await page.waitForFunction(()=>state.snapshot);
   await page.evaluate(()=>{displayPrefs.fontSize=24;displayPrefs.theme='dark';applyDisplay()});
   for(const view of ['overview','tournamentQueue','events','engines','presets','experiments','health']){
    await page.locator(`aside [data-view=${view}]`).click();await page.waitForTimeout(35);await check(`${lang}-24-${view}`);
   }
   for(const kind of ['setup','engine','appearance','hardware','pgn','ratings','event','benchmark','suite','graph','clocks','language']){
    await openDialog(kind);await check(`${lang}-24-${kind}`,lang==='de'&&['setup','appearance','clocks'].includes(kind));await close();
   }
  }
  await page.setViewportSize({width:1600,height:1060});await page.goto(ready.url);await page.waitForFunction(()=>state.snapshot);await page.waitForTimeout(800);
  await page.evaluate(()=>{displayPrefs.fontSize=14;displayPrefs.theme='dark';applyDisplay()});
  for(const format of ['match','round_robin','gauntlet','self_play','swiss','knockout','double_elimination','ladder','sprt','custom']){
   await openDialog('setup');await page.locator('#tformat').selectOption(format);await check(`format-${format}`);await close();
  }
  const clockLayouts=[];
  for(const placement of ['above','below','left','right','split'])for(const arrangement of ['row','stack']){
   await page.evaluate(({placement,arrangement})=>{displayPrefs.panels.focus={...displayPrefs.panels.focus,height:720,clocks:{...ArenaFocusLayout.defaults,placement,arrangement}};applyDisplay()},{placement,arrangement});
   const r=await page.evaluate(()=>{const b=$('#focusContent .board').getBoundingClientRect();return {w:b.width,h:b.height,overflow:$('#focusContent').scrollWidth>$('#focusContent').clientWidth+2}});
   clockLayouts.push({placement,arrangement,...r});if(r.w<80||Math.abs(r.w-r.h)>2||r.overflow)failures.push({placement,arrangement,...r});
  }
  // Exact columns still determine board width independently of visible game count.
  for(const columns of [1,2,3,4]){
   await page.evaluate(columns=>{displayPrefs.panels.live={visible:true,column:'left',order:0,cardColumns:columns,height:680};displayPrefs.boardCount=128;applyDisplay()},columns);
   const r=await page.evaluate(()=>{const host=$('#liveBoards'),b=host.querySelector('.board').getBoundingClientRect();return {columns:getComputedStyle(host).gridTemplateColumns.split(' ').length,w:b.width,h:b.height,count:host.children.length,height:panels.live.getBoundingClientRect().height}});
   if(r.columns!==columns||Math.abs(r.w-r.h)>2||r.height>1044)failures.push({columns,...r});evidence.push({name:'live-columns-'+columns,...r});
  }
  await page.evaluate(()=>{displayPrefs.panels.live={visible:true};displayPrefs.panels.focus={visible:true,height:650};displayPrefs.fontSize=14;displayPrefs.theme='dark';displayPrefs.boardCount=4;applyDisplay();scrollTo(0,0)});
  await page.screenshot({path:'test-output/design-final-workspace.png'});
  await page.locator('[data-panel=focus]').scrollIntoViewIfNeeded();await page.screenshot({path:'test-output/design-final-boards.png'});
  fs.writeFileSync('test-output/design-validation.json',JSON.stringify({evidence,clockLayouts,failures,errors},null,2));
  assert.deepEqual(errors,[]);assert.deepEqual(failures,[]);
  console.log(`${evidence.length} workspace/dialog/layout checks and ${clockLayouts.length} clock layouts passed.`);
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
