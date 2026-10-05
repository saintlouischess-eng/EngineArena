/* Original carved horse model, authored for Engine Arena. No downloaded assets.
 * Bake a smooth implicit sculpture once, rather than meshing it on the UI thread.
 * Signed int16 positions/normals are stored in a compact local JS asset.
 */
'use strict';
const fs=require('node:fs'),path=require('node:path');
const mix=(a,b,h)=>a*(1-h)+b*h;
function join(a,b,k=.06){const h=Math.max(0,Math.min(1,.5+.5*(b-a)/k));return mix(b,a,h)-k*h*(1-h)}
function ell(x,y,z,cx,cy,cz,rx,ry,rz,angle=0){
 const dx=x-cx,dy=y-cy,c=Math.cos(angle),s=Math.sin(angle);
 return (Math.hypot((dx*c+dy*s)/rx,(-dx*s+dy*c)/ry,(z-cz)/rz)-1)*Math.min(rx,ry,rz);
}
function field(x,y,z){
 let d=ell(x,y,z,.02,.53,0,.244,.19,.182);
 for(const p of [[.105,.73,0,.19,.27,.158,-.25],[.16,.98,0,.153,.31,.137,.05],
  [.04,1.25,0,.185,.173,.143,.18],[-.185,1.17,0,.24,.119,.112,.47],
  [-.371,1.071,0,.103,.092,.102,.42],[-.10,1.134,0,.134,.132,.136,.25]])d=join(d,ell(x,y,z,...p));
 // Paired tapered ears, and a raised mane following the nape.
 for(const side of [-1,1])d=join(d,ell(x,y,z,.062,1.425,side*.074,.047,.135,.039,-.25),.027);
 d=join(d,ell(x,y,z,.267,1.03,0,.074,.277,.065,.17),.025);
 // Recessed eyes and nostrils, and a lightly incised mouth.
 for(const side of [-1,1]){
  d=Math.max(d,-ell(x,y,z,-.100,1.279,side*.135,.027,.020,.019,-.3));
  d=Math.max(d,-ell(x,y,z,-.359,1.11,side*.091,.023,.016,.018,.5));
  d=Math.max(d,-ell(x,y,z,-.383,1.038,side*.095,.08,.011,.029,.16));
 }
 // A continuous raised mane reads cleanly even on a small docked board.
 return d;
}
const step=.019,min=[-.51,.355,-.235],max=[.40,1.60,.235],size=max.map((v,i)=>Math.ceil((v-min[i])/step)+1);
const idx=(x,y,z)=>(x*size[1]+y)*size[2]+z,grid=new Float64Array(size.reduce((a,b)=>a*b));
for(let x=0;x<size[0];x++)for(let y=0;y<size[1];y++)for(let z=0;z<size[2];z++)grid[idx(x,y,z)]=field(min[0]+x*step,min[1]+y*step,min[2]+z*step);
const corners=[[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]],
 tetra=[[0,5,1,6],[0,1,2,6],[0,2,3,6],[0,3,7,6],[0,7,4,6],[0,4,5,6]],out=[];
const sub=(a,b)=>a.map((v,i)=>v-b[i]),cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
function normal(p){const e=.0003,n=[0,1,2].map(i=>{const a=[...p],b=[...p];a[i]+=e;b[i]-=e;return field(...a)-field(...b)}),l=Math.hypot(...n);return n.map(v=>v/l)}
function tri(a,b,c){const n=[a,b,c].map(normal),f=cross(sub(b,a),sub(c,a));if(f.reduce((s,v,i)=>s+v*n[0][i],0)<0){[b,c]=[c,b];[n[1],n[2]]=[n[2],n[1]]}for(const [i,p] of [a,b,c].entries())out.push(...p.map(v=>Math.round(v*10000)),...n[i].map(v=>Math.round(v*32767)))}
for(let x=0;x<size[0]-1;x++)for(let y=0;y<size[1]-1;y++)for(let z=0;z<size[2]-1;z++){
 const val=corners.map(c=>grid[idx(x+c[0],y+c[1],z+c[2])]);if(val.every(v=>v<0)||val.every(v=>v>=0))continue;
 const p=corners.map(c=>[min[0]+(x+c[0])*step,min[1]+(y+c[1])*step,min[2]+(z+c[2])*step]);
 const edge=(a,b)=>{const t=val[a]/(val[a]-val[b]);return p[a].map((v,i)=>mix(v,p[b][i],t))};
 for(const t of tetra){const inside=t.filter(i=>val[i]<0),outside=t.filter(i=>val[i]>=0);
  if(inside.length===1){tri(...outside.map(i=>edge(inside[0],i)))}
  if(inside.length===3){tri(...inside.map(i=>edge(outside[0],i)))}
  if(inside.length===2){const [a,b]=inside,[c,d]=outside,ac=edge(a,c),ad=edge(a,d),bc=edge(b,c),bd=edge(b,d);tri(ac,ad,bc);tri(ad,bd,bc)}
 }
}
const bytes=Buffer.alloc(out.length*2);out.forEach((v,i)=>bytes.writeInt16LE(v,i*2));
const target=path.join(__dirname,'../ui/board3d-knight.js');
fs.writeFileSync(target,`'use strict';\n// Original Engine Arena sculpture. Regenerate with scripts/generate_board3d_knight.cjs.\nconst ArenaKnightMesh=(()=>{\n const raw=atob('${bytes.toString('base64')}'),data=new DataView(Uint8Array.from(raw,c=>c.charCodeAt(0)).buffer),out=new Float32Array(data.byteLength/12*7);\n for(let i=0;i<data.byteLength;i+=12){const n=[6,8,10].map(k=>data.getInt16(i+k,true)/32767),l=Math.hypot(...n);out.set([...\n [0,2,4].map(k=>data.getInt16(i+k,true)/10000),...n.map(v=>v/l),1],i/12*7)}\n return out;\n})();\nif(typeof module!=='undefined')module.exports=ArenaKnightMesh;\n`);
console.log(JSON.stringify({vertices:out.length/6,triangles:out.length/18,bytes:fs.statSync(target).size}));
