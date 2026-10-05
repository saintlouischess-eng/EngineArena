const fs=require('node:fs'),assert=require('node:assert/strict'),path=require('node:path');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1060}}),errors=[],evidence=[];
  page.on('pageerror',e=>errors.push(e.message));await page.goto(JSON.parse(fs.readFileSync('test-output/design-ready.json')).url);
  await page.waitForFunction(()=>state.snapshot);await page.waitForTimeout(600);
  await page.evaluate(async()=>{displayPrefs.graphs=[{id:'graph-de',kind:'score',slot:0,game:0,ci:'normal'}];displayPrefs.panels['graph-de']={column:'right',height:540};applyDisplay();await refreshGraphs()});
  await page.waitForSelector('.graph-plot svg');
  for(const theme of ['dark','light'])for(const width of [1050,1600,2560])for(const font of [14,24]){
   await page.setViewportSize({width,height:1060});
   await page.evaluate(async({theme,font})=>{displayPrefs.theme=theme;displayPrefs.fontSize=font;applyDisplay();await refreshGraphs()},{theme,font});
   await page.waitForTimeout(200);await page.evaluate(()=>refreshGraphs());
   const r=await page.locator('.graph-plot svg').evaluate(svg=>{const text=svg.querySelector('text'),matrix=text.getScreenCTM(),box=svg.getBoundingClientRect();return {font:Number(text.getAttribute('font-size')),scale:matrix.a,actualFont:Number(text.getAttribute('font-size'))*matrix.a,width:box.width,viewWidth:svg.viewBox.baseVal.width,height:box.height}});
   evidence.push({theme,width,font,...r});assert(r.actualFont>=10.5,JSON.stringify(r));
   if(width===1600&&font===14){await page.locator('.graph-panel').scrollIntoViewIfNeeded();await page.screenshot({path:'test-output/design-graph-'+theme+'.png'})}
  }
  await page.evaluate(()=>{const graph=graphData.get('graph-de');let exported='';const original=download;try{download=(name,text)=>exported=text;panels['graph-de'].querySelector('[data-graph-svg]').click()}finally{download=original}if(!exported.includes('viewBox="0 0 800 390"')||!exported.includes(graph.title)||!exported.includes(seriesLabel(graph.series[0])))throw Error('Export dimensions/title/legend missing')});
  assert.deepEqual(errors,[]);fs.writeFileSync('test-output/design-graph-validation.json',JSON.stringify({evidence,exportPreserved:true,errors},null,2));
  console.log('12 responsive graph/theme/font combinations preserve readable labels; standalone SVG export remains 800 x 390.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
