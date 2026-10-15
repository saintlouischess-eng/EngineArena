import * as T from './three.module.js';

// Photo-matched at the listings' 2.5-inch square size. One scene unit = one
// square. Cross-sections not specified by the maker are inferred from photos.
export const boardSpecs={
 classic:{half:4.59,letter:4.3,inkY:-.018,letterSize:.35},
 drueke:{half:4.8,letter:4.38,inkY:-.04956,letterSize:.32,slope:-.115/.73},
 jaques:{half:4.4,letter:4.27,inkY:.174,letterSize:.18}
};

export function boardCollection(scene,assets,own,mat,textures,renderer,original){
 const groups=new Map([['classic',original]]),materials=new Map();let current='';
 function tex(source,color=false){const t=source.clone();t.wrapS=t.wrapT=T.RepeatWrapping;t.anisotropy=Math.min(16,renderer.capabilities.getMaxAnisotropy());if(color)t.colorSpace=T.SRGBColorSpace;t.needsUpdate=true;textures.set(t,t);return t}
 // The same CC0 photographed grain drives color, microscopic relief and satin
 // roughness. Species palettes operate in linear light, without painted glare.
 const maps={map:tex(assets.wood.color,true),normalMap:tex(assets.wood.normal),roughnessMap:tex(assets.wood.rough)};
 function wood(kind){
  if(materials.has(kind))return materials.get(kind);
  const palettes={walnut:[0x36271d,0x805c40],maple:[0xc8ad7d,0xeddbb2],purpleheart:[0x3a1726,0x793146]},colors=palettes[kind].map(c=>new T.Color(c));
  const m=mat(new T.MeshPhysicalMaterial({...maps,vertexColors:true,roughness:.72,normalScale:new T.Vector2(kind==='maple'?.035:.065,kind==='maple'?.035:.065),specularIntensity:.5,clearcoat:.14,clearcoatRoughness:.42,envMapIntensity:.8}));
  m.onBeforeCompile=s=>{
   s.uniforms.woodLow={value:colors[0]};s.uniforms.woodHigh={value:colors[1]};
   s.fragmentShader='uniform vec3 woodLow; uniform vec3 woodHigh;\n'+s.fragmentShader;
   s.fragmentShader=s.fragmentShader.replace('#include <map_fragment>',`#ifdef USE_MAP
    vec4 grain = texture2D(map, vMapUv);
    float lum = dot(grain.rgb, vec3(.2126,.7152,.0722));
    float figure = clamp((sqrt(max(lum,0.0))-.08)*3.0,0.0,1.0);
    diffuseColor.rgb *= mix(woodLow,woodHigh,figure);
   #endif`);
   s.fragmentShader=s.fragmentShader.replace('#include <roughnessmap_fragment>','#include <roughnessmap_fragment>\nroughnessFactor = .38 + .20 * roughnessFactor;');
  };
  m.customProgramCacheKey=()=> 'board-wood-'+kind;materials.set(kind,m);return m;
 }
 function geometry(positions,uvs,colors,indices){const g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(positions,3));g.setAttribute('uv',new T.Float32BufferAttribute(uvs,2));g.setAttribute('color',new T.Float32BufferAttribute(colors,3));g.setIndex(indices);g.computeVertexNormals();return own(g)}
 function mesh(group,geo,material){const m=new T.Mesh(geo,material);m.castShadow=m.receiveShadow=true;group.add(m);return m}
 function patch(group,xs,zs,height,material,uv,variation=1){
  const p=[],u=[],c=[],ix=[];
  for(const z of zs)for(const x of xs){p.push(x,height(x,z),z);u.push(...uv(x,z));const value=typeof variation==='function'?variation(x,z):variation;c.push(value,value,value)}
  for(let r=0;r<zs.length-1;r++)for(let f=0;f<xs.length-1;f++){const a=r*xs.length+f,b=a+1,d=a+xs.length,e=d+1;ix.push(a,d,b,b,d,e)}
  return mesh(group,geometry(p,u,c,ix),material);
 }
 function field(group,dark){
  const buffers=[0,1].map(()=>({p:[],u:[],c:[],ix:[]}));
  for(let rank=0;rank<8;rank++)for(let file=0;file<8;file++){
   const b=buffers[(rank+file)%2],n=b.p.length/3,id=rank*8+file;
   // Different sawn sections, parallel grain, slight natural board-to-board tone.
   const ox=((id*37)%101)/101*.72,oy=((id*61+13)%103)/103*.72,v=.94+((id*17)%19)/190;
   for(const [dx,dz] of [[0,0],[0,1],[1,1],[1,0]]){b.p.push(file-4+dx,0,rank-4+dz);b.u.push(ox+dx*.265,oy+dz*.265);b.c.push(v,v,v)}
   b.ix.push(n,n+1,n+2,n,n+2,n+3);
  }
  buffers.forEach((b,i)=>mesh(group,geometry(b.p,b.u,b.c,b.ix),wood(i?dark:'maple')));
 }
 function body(group,half,upper){
  // Solid underside and vertical faces, with continuous rail-oriented grain.
  const box=own(new T.BoxGeometry(half*2-.004,upper+.324,half*2-.004));
  const p=box.attributes.position,u=box.attributes.uv,c=[];
  for(let i=0;i<p.count;i++){const x=p.getX(i),y=p.getY(i),z=p.getZ(i);u.setXY(i,(Math.abs(x)>half-.01?z:x)*.105+.41,y*.45+.3);c.push(.83,.83,.83)}box.setAttribute('color',new T.Float32BufferAttribute(c,3));
  const b=mesh(group,box,wood('walnut'));b.position.y=(upper-.324)/2;
 }
 function drueke(group){
  const outer=4.8,groove=4.019,halfGroove=.019;
  const edge=r=>r<4.04?0:r<4.77?-.115*(r-4.04)/.73:-.115-(r-4.77)*.8;
  const cut=(along,across)=>{
   const d=Math.abs(Math.abs(across)-groove),end=Math.max(0,Math.min(1,(4.66-Math.abs(along))/.055));
   return d<halfGroove?.060*(1-d/halfGroove)*end:0;
  };
  const cavity=(x,z)=>Math.max(cut(x,z),cut(z,x));
  const height=(x,z)=>edge(Math.max(Math.abs(x),Math.abs(z)))-cavity(x,z);
  const tone=(x,z)=>1-.88*cavity(x,z)/.060;
  const stops=[0,4,4.001,groove,4.038,4.055,4.4,4.605,4.66,4.77,4.79,outer];
  const xs=[...stops.slice(1).map(n=>-n).reverse(),...stops];
  const radial=stops.filter(n=>n>=4);
  body(group,outer,-.139);
  // Full-width end rails; side rails butt into them, as in the reference.
  for(const sign of [-1,1]){
   const zs=radial.map(n=>n*sign).sort((a,b)=>a-b);
   patch(group,xs,zs,height,wood('walnut'),(x,z)=>[(z-sign*4)*.44+(sign>0?.14:.57),x*.104+.51],(x,z)=>tone(x,z)*(sign>0?1:.95));
   patch(group,zs,[-4,...xs.filter(n=>n>-4&&n<4),4],height,wood('walnut'),(x,z)=>[(x-sign*4)*.44+(sign>0?.62:.28),z*.105+.31],(x,z)=>tone(x,z)*(sign>0?.96:1.03));
  }
  field(group,'walnut');
 }
 function jaques(group){
  // Narrow mitered walnut surround, a rolled inner lip and genuine recessed
  // playing surface. Many short profile segments give the molding a soft roll.
  const profile=[[4,0],[4.009,.004],[4.021,.014],[4.036,.03],[4.05,.052],[4.063,.08],[4.078,.112],[4.094,.135],[4.113,.151],[4.133,.161],[4.155,.166],[4.18,.168],[4.32,.164],[4.35,.16],[4.374,.151],[4.39,.136],[4.399,.116],[4.4,.092],[4.4,-.307],[4.39,-.322]];
  body(group,4.398,-.02);
  for(let side=0;side<4;side++){
   const p=[],u=[],c=[],ix=[];
   for(const [r,y] of profile)for(const x of [-r,r]){
    const a=side*Math.PI/2;p.push(x*Math.cos(a)-r*Math.sin(a),y,x*Math.sin(a)+r*Math.cos(a));
    u.push((r-4)*.7+.10+side*.19,x*.108+.51+side*.117);c.push(1,1,1);
   }
   for(let j=0;j<profile.length-1;j++){const a=j*2;ix.push(a,a+2,a+1,a+1,a+2,a+3)}
   mesh(group,geometry(p,u,c,ix),wood('walnut'));
  }
  field(group,'purpleheart');
 }
 return {
  update(p){const name=Object.hasOwn(boardSpecs,p.board)?p.board:'classic';
   if(name!==current){if(!groups.has(name)){const g=new T.Group();g.name=name==='drueke'?'Walnut and maple — Drueke':'Purpleheart and maple — Jaques';scene.add(g);groups.set(name,g);(name==='drueke'?drueke:jaques)(g)}for(const [key,g] of groups)g.visible=key===name;current=name;renderer.shadowMap.needsUpdate=true}
   renderer.domElement.dataset.boardDesign=name;return boardSpecs[name];
  }
 };
}
