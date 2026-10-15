const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/league-ready.json','utf8'));
 const out='test-output/insights-ui';fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,channel:'msedge'}),page=await browser.newPage({viewport:{width:1600,height:1100}}),errors=[],checks=[];
 page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(ready.url);await page.waitForFunction(()=>state.snapshot&&typeof seasonSummaryText==='function');
  await page.evaluate(id=>showEvent(id),ready.season);await page.waitForSelector('.si-hero');
  assert.equal(await page.locator('#siSeason').inputValue(),'latest');
  await page.screenshot({path:out+'/overview-dark.png'});
  await page.locator('#siSeason').selectOption('1');await page.waitForFunction(()=>document.querySelector('#siPanel-overview').textContent.includes('Qualification'));
  await page.locator('#siTab-careers').click();await page.waitForSelector('#siCareerRows');
  await page.locator('#siSearch').fill('0');await page.waitForFunction(()=>document.querySelectorAll('#siCareerRows tr').length===1);
  await page.locator('#siCareerRows [data-career]').click();await page.waitForSelector('#siCareerBack');
  assert.match(await page.locator('#siPanel-careers').textContent(),/1, 2/);
  await page.screenshot({path:out+'/career-dark.png'});
  await page.locator('#siRivalNext').isDisabled();await page.locator('#siCareerBack').click();await page.waitForSelector('#siSearch');
  await page.locator('#siTab-summary').click();await page.waitForSelector('#siSummaryPreview');
  const brief=await page.locator('#siSummaryPreview').inputValue();assert.match(brief,/Season champion/);
  await page.locator('#siSummaryDetail').selectOption('full');const full=await page.locator('#siSummaryPreview').inputValue();assert.match(full,/Clock tolerance/);assert.ok(full.length>brief.length);
  fs.writeFileSync(out+'/season-summary.txt',full);
  await page.locator('#siExportSummary').click();await page.waitForFunction(()=>!document.querySelector('#copyTextExport').disabled);
  await page.locator('#textCopyFormat').selectOption('forum');assert.match(await page.locator('#textExportPreview').inputValue(),/^\[code\]/);
  await page.keyboard.press('Escape');await page.evaluate(id=>showEvent(id),ready.completed);await page.locator('#siTab-overview').click();await page.waitForSelector('.si-final');
  await page.locator('#siTab-stages').click();assert.equal(await page.locator('#eventChildren').isVisible(),true);
  for(const lang of ['en','es','fr','de','pt','it','nl','pl']){
   await page.goto(ready.url+'&lang='+lang);await page.waitForFunction(()=>state.snapshot&&typeof seasonSummaryText==='function');
   await page.evaluate(()=>{window.missingMessages=new Set();ArenaI18n.capture(k=>{if(ArenaI18n.locale!=='en'&&!Object.hasOwn(window.ARENA_MESSAGES,k))missingMessages.add(k)});displayPrefs.fontSize=20;applyDisplay()});
   await page.evaluate(id=>showEvent(id),ready.season);await page.waitForSelector('.si-hero');
   for(const width of [1050,1600])for(const theme of ['dark','light']){
    await page.setViewportSize({width,height:1100});await page.evaluate(t=>document.body.classList.toggle('light',t==='light'),theme);
    for(const tab of ['overview','careers','summary','stages']){
     await page.locator('#siTab-'+tab).click();await page.waitForTimeout(120);
     const overflow=await page.locator('#modal').evaluate(el=>el.scrollWidth>el.clientWidth+2);assert.equal(overflow,false,lang+' '+tab+' '+width);
     if(tab==='summary'){await page.waitForSelector('#siSummaryDetail');await page.locator('#siSummaryDetail').selectOption('full')}
    }
    checks.push({lang,width,theme});
   }
   await page.locator('#siTab-careers').click();await page.waitForSelector('#siCareerRows');await page.locator('#siCareerRows [data-career]').first().click();await page.waitForSelector('#siCareerBack');
   assert.deepEqual(await page.evaluate(()=>[...missingMessages]),[],lang);
   if(lang==='en'){await page.locator('#siTab-overview').click();await page.waitForSelector('.si-hero');await page.screenshot({path:out+'/overview-light.png'})}
  }
  assert.deepEqual(errors,[]);fs.writeFileSync(out+'/acceptance.json',JSON.stringify({passed:true,checks,errors,legacy:true,careers:true,summary:true,forum:true},null,2));
  console.log('Season overview, careers, summary, legacy league, forum export and 32 language/theme/width layouts passed.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
