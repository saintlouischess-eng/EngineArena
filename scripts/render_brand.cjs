// Optional artwork regeneration: npm install playwright; node scripts/render_brand.cjs
// Uses installed Microsoft Edge. No image downloads, external fonts or paid assets.
const fs=require('node:fs'),path=require('node:path');
let chromium;try{({chromium}=require('playwright'))}catch{({chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright')))}
(async()=>{
 const root=path.resolve(__dirname,'..'),svg=fs.readFileSync(path.join(root,'ui/engine-arena.svg'),'utf8');
 const browser=await chromium.launch({channel:'msedge',headless:true}),frames=[];
 try{
  const page=await browser.newPage();
  for(const size of [16,24,32,48,64,128,256]){
   await page.setViewportSize({width:size,height:size});
   await page.setContent('<body style="margin:0;background:transparent">'+svg.replace('<svg ',`<svg width="${size}" height="${size}" `));
   frames.push({size,png:await page.screenshot({omitBackground:true})});
  }
  // ICO directory followed by PNG frames; supported by the Windows 11 target.
  const header=Buffer.alloc(6+frames.length*16);header.writeUInt16LE(1,2);header.writeUInt16LE(frames.length,4);
  let offset=header.length;
  frames.forEach(({size,png},i)=>{const entry=6+i*16;header[entry]=header[entry+1]=size===256?0:size;header.writeUInt16LE(1,entry+4);header.writeUInt16LE(32,entry+6);header.writeUInt32LE(png.length,entry+8);header.writeUInt32LE(offset,entry+12);offset+=png.length});
  fs.writeFileSync(path.join(root,'ui/engine-arena.ico'),Buffer.concat([header,...frames.map(f=>f.png)]));
  console.log('Rendered seven native SVG icon sizes (16–256 px).');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
