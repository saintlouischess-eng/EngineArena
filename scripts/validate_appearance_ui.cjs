const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const out='test-output/appearance-1105',ready=JSON.parse(fs.readFileSync(out+'/ready.json'));
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--disable-gpu']}),errors=[];
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1050}});page.on('pageerror',e=>{errors.push(e.message);console.error('PAGE ERROR:',e.message)});
  await page.goto(ready.url);await page.waitForFunction(()=>document.querySelector('#tournamentPicker')?.options.length>1);
  await page.selectOption('#tournamentPicker',ready.tid);await page.waitForFunction(()=>document.querySelectorAll('#standings tbody tr').length===4);
  const original=await page.evaluate(()=>({raw:structuredClone(state.snapshot.standings),query:statisticsQuery()}));
  const control=(scope,key)=>page.locator(`[data-rating-display="${scope}"] [data-rating-setting="${key}"]`);
  let fits=0;page.on('request',r=>{if(r.url().includes('/api/rating-center?'))fits++});
  for(const digits of ['0','1','2']){
   await control('standings','ratingDigits').selectOption(digits);await control('standings','ciDigits').selectOption(digits);
   for(const mode of ['bounds','error']){
    await control('standings','ciMode').selectOption(mode);
    const actual=await page.locator('#standings tbody tr').evaluateAll(rows=>rows.map(r=>[r.cells[10].textContent,r.cells[11].textContent]));
    const expected=await page.evaluate(({digits,mode})=>state.snapshot.standings.map(r=>[ArenaFormat.number(r.elo,Number(digits)),ArenaFormat.interval(r.ci,r.elo,mode,Number(digits))]),{digits,mode});
    assert.deepEqual(actual,expected);
   }
  }
  assert.equal(await page.evaluate(()=>statisticsQuery()),original.query);
  await page.selectOption('#confidenceMethod','conservative');
  await page.waitForFunction(()=>state.ciMethod==='conservative'&&document.querySelector('#standings tbody tr td:nth-child(12)').textContent===ArenaFormat.interval(state.snapshot.standings[0].ci_conservative,state.snapshot.standings[0].elo,'error',2));
  const conservative=await page.locator('#standings tbody tr').evaluateAll(rows=>rows.map(r=>r.cells[11].textContent));
  assert.deepEqual(conservative,await page.evaluate(()=>state.snapshot.standings.map(r=>ArenaFormat.interval(r.ci_conservative,r.elo,'error',2))));
  await page.selectOption('#confidenceMethod','normal');
  await page.locator('[data-view=ratingCenter]').click();await page.waitForFunction(()=>document.querySelectorAll('#rcRows .rc-rating').length===4);
  await page.locator('#rcAuto').uncheck();const baselineFits=fits;
  const rawBefore=await page.evaluate(()=>structuredClone(RatingDesk.data.items));
  for(const digits of ['0','1','2']){
   await control('center','ratingDigits').selectOption(digits);await control('center','ciDigits').selectOption(digits);
   for(const mode of ['bounds','error']){
    await control('center','ciMode').selectOption(mode);
    const actual=await page.locator('#rcRows tr').evaluateAll(rows=>rows.map(r=>[r.cells[2].textContent,r.cells[3].textContent]));
    const expected=await page.evaluate(({digits,mode})=>RatingDesk.data.items.map(r=>[ArenaFormat.number(r.rating,Number(digits)),ArenaFormat.interval(r.ci,r.rating,mode,Number(digits))]),{digits,mode});
    assert.deepEqual(actual,expected);
   }
  }
  assert.equal(fits,baselineFits,'Presentation changes must not request rating fits');
  assert.deepEqual(await page.evaluate(()=>RatingDesk.data.items),rawBefore);
  await control('center','ratingDigits').selectOption('0');await control('center','ciDigits').selectOption('1');
  assert.equal(await control('standings','ratingDigits').inputValue(),'2','Views keep independent preferences');
  const palettes=[];
  for(const theme of ['ocean','emerald','royal','burgundy','lagoon','lavender','peach','sky']){
   await page.locator('#theme').click();assert.equal(await page.locator('[data-theme-choice]').count(),15);
   await page.locator(`[data-theme-choice=${theme}]`).click();await page.locator('#applyTheme').click();
   await page.waitForFunction(theme=>document.body.dataset.arenaTheme===theme,theme);
   const colors=await page.evaluate(()=>{const s=getComputedStyle(document.body);return Object.fromEntries(['bg','panel','raised','text','muted','accent'].map(k=>[k,s.getPropertyValue('--'+k).trim()]))});
   const lum=h=>{const rgb=[1,3,5].map(i=>parseInt(h.slice(i,i+2),16)/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4);return rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722};
   const ratios=[];for(const fg of ['text','muted'])for(const bg of ['bg','panel','raised']){const [a,b]=[lum(colors[fg]),lum(colors[bg])].sort((a,b)=>a-b);const ratio=(b+.05)/(a+.05);assert(ratio>=4.5,`${theme} ${fg}/${bg}: ${ratio}`);ratios.push(ratio)}
   palettes.push({theme,colors,minimumTextContrast:Math.min(...ratios)});
   if(['ocean','lavender','peach'].includes(theme))await page.screenshot({path:out+`/${ready.mode}-${theme}.png`,animations:'disabled'});
  }
  await page.reload();await page.waitForFunction(()=>document.body.dataset.arenaTheme==='sky'&&document.querySelector('[data-rating-display=center] [data-rating-setting=ratingDigits]')?.value==='0');
  assert.equal(await control('center','ciDigits').inputValue(),'1');assert.equal(await control('center','ciMode').inputValue(),'error');assert.equal(await control('standings','ratingDigits').inputValue(),'2');
  await page.locator('[data-view=ratingCenter]').click();await page.waitForFunction(()=>document.querySelectorAll('#rcRows .rc-rating').length===4);
  await page.selectOption('#rcCategory','all');await page.waitForFunction(()=>document.querySelectorAll('#rcHeads th').length>10);
  await control('center','ratingDigits').selectOption('2');
  await page.selectOption('#rcCategory','blitz');await page.waitForFunction(()=>document.querySelectorAll('#rcRows .rc-rating').length===4);
  await page.selectOption('#rcRange','400');await page.waitForFunction(()=>document.querySelector('#rcHeads').textContent.includes('Filtered Elo'));
  const filtered=await page.locator('#rcRows tr').evaluateAll(rows=>rows.map(r=>[r.cells[2].textContent,r.cells[3].textContent,r.cells[4].childNodes[0].textContent]));
  assert.deepEqual(filtered,await page.evaluate(()=>RatingDesk.data.items.map(r=>[ArenaFormat.number(r.rating,2),ArenaFormat.interval(r.ci,r.rating,'error',1),ArenaFormat.number(r.full_rating,2)])));
  await page.selectOption('#rcRange','0');await page.waitForFunction(()=>!document.querySelector('#rcHeads').textContent.includes('Filtered Elo'));
  await page.setViewportSize({width:1100,height:850});await page.locator('.rc-display-controls').scrollIntoViewIfNeeded();await page.screenshot({path:out+`/${ready.mode}-narrow.png`,animations:'disabled'});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No page-wide overflow');
  assert.deepEqual(errors,[]);fs.writeFileSync(out+`/${ready.mode}-ui.json`,JSON.stringify({passed:true,palettes,allFormatsAndPrecisions:true,independentPersistence:true,noRefitForPresentation:true,rawRatingsUnchanged:true,errors},null,2));
  console.log('Passed: 8 colorful themes, contrast, both CI modes, all precisions, independent persistence, unchanged raw ratings, zero display-triggered fits, narrow layout.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
