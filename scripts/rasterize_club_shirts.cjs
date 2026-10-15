// Original vector artwork -> deterministic transparent texture inputs for Blender.
const fs=require('fs'),path=require('path');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--disable-gpu']});
 try{
  const page=await browser.newPage();
  for(const name of ['levy-rook-shirt','hikaru-pineapple-shirt']){
   const file=path.join('prototypes/live-club/art',name),svg=fs.readFileSync(file+'.svg','utf8');
   const encoded=await page.evaluate(async svg=>{
    const image=new Image();image.src='data:image/svg+xml;base64,'+btoa(unescape(encodeURIComponent(svg)));await image.decode();
    const canvas=document.createElement('canvas');canvas.width=image.naturalWidth;canvas.height=image.naturalHeight;
    canvas.getContext('2d').drawImage(image,0,0);return canvas.toDataURL('image/png').split(',')[1];
   },svg);
   fs.writeFileSync(file+'.png',Buffer.from(encoded,'base64'));console.log(file+'.png');
  }
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
