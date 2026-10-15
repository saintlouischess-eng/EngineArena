import * as T from '/ui/three.module.js';
import {mergeGeometries} from '/ui/three-geometry-utils.js';
import {clubTime} from '/ui/board3d-club-motion.js';

// An architectural study, not a photographic room with props layered over it.
// One unit = 5.5 cm. Every surface, opening and furnishing has real scene depth.
// The separate cast manager adds four individually modeled visitors. Keeping
// them separate also permits the owner's approved unpopulated architecture view.
export function buildClub(scene, assets, own, keep, texture) {
 const root=new T.Group();root.name='Standalone chess club';scene.add(root);
 const floor=-13.5,top=47,half=62,back=-96,front=57,animations=[],geometries=new Map();
 const geo=(key,fn)=>{if(!geometries.has(key))geometries.set(key,own(fn()));return geometries.get(key)};
 const material=(color,roughness=.65,metalness=0)=>keep(new T.MeshStandardMaterial({color,roughness,metalness}));
 const maps=(source,repeat=[1,1])=>Object.fromEntries(['color','normal','rough'].map((name,i)=>{const map=source[name].clone();map.wrapS=map.wrapT=T.RepeatWrapping;map.repeat.set(...repeat);map.anisotropy=8;if(!i)map.colorSpace=T.SRGBColorSpace;texture(map);return [['map','normalMap','roughnessMap'][i],map]}));
 const woodMaps=maps(assets.wood),leatherMaps=maps(assets.leather,[2,2]);
 const walnut=keep(new T.MeshPhysicalMaterial({...woodMaps,color:0x6c4930,roughness:.55,normalScale:new T.Vector2(.08,.08),clearcoat:.13,clearcoatRoughness:.42}));
 const oak=keep(new T.MeshPhysicalMaterial({...woodMaps,color:0xb69d72,roughness:.73,normalScale:new T.Vector2(.06,.06),clearcoat:.06}));
 const darkWood=keep(new T.MeshStandardMaterial({...woodMaps,color:0x3a2920,roughness:.6,normalScale:new T.Vector2(.08,.08)}));
 // Calibrate scanned albedo in linear space. Multiplying already dark wood by
 // another brown turns joinery black; use the scan to vary a species palette.
 function timber(m,name,low,high){m.color.set(0xffffff);m.onBeforeCompile=shader=>{shader.uniforms.timberLow={value:new T.Color(low)};shader.uniforms.timberHigh={value:new T.Color(high)};shader.fragmentShader='uniform vec3 timberLow; uniform vec3 timberHigh;\n'+shader.fragmentShader;shader.fragmentShader=shader.fragmentShader.replace('#include <map_fragment>',`#ifdef USE_MAP
 vec4 grain=texture2D(map,vMapUv);float lum=dot(grain.rgb,vec3(.2126,.7152,.0722));
 float figure=clamp((sqrt(max(lum,0.0))-.08)*3.0,0.0,1.0);
 diffuseColor.rgb*=mix(timberLow,timberHigh,figure);
 #endif`);shader.fragmentShader=shader.fragmentShader.replace('#include <roughnessmap_fragment>','#include <roughnessmap_fragment>\nroughnessFactor=.57+.24*roughnessFactor;')};m.customProgramCacheKey=()=>name;}
 timber(walnut,'walnut',0x4f3828,0x957047);timber(oak,'oak',0x786145,0xc9ad7b);timber(darkWood,'dark',0x30241a,0x6c5036);

 const leather=keep(new T.MeshPhysicalMaterial({...leatherMaps,color:0x23453c,roughness:.7,normalScale:new T.Vector2(.28,.28),clearcoat:.08}));
 timber(leather,'leather',0x1c392f,0x526c52);
 const gold=material(0xac8c53,.4,.67),iron=material(0x252a29,.4,.65),cream=material(0xd2c6ab,.9);
 function canvasTexture(w,h,draw){const c=document.createElement('canvas');c.width=w;c.height=h;draw(c.getContext('2d'),w,h);const t=new T.CanvasTexture(c);t.colorSpace=T.SRGBColorSpace;t.anisotropy=8;texture(t);return t}
 let seed=12458;const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296};
 const plasterMap=canvasTexture(256,256,(c,w,h)=>{const data=c.createImageData(w,h);for(let i=0;i<data.data.length;i+=4){const v=190+random()*20;data.data.set([v,v,v,255],i)}c.putImageData(data,0,0)});plasterMap.wrapS=plasterMap.wrapT=T.RepeatWrapping;plasterMap.repeat.set(7,5);
 const plaster=keep(new T.MeshStandardMaterial({color:0x45665b,map:plasterMap,bumpMap:plasterMap,bumpScale:.035,roughness:.98}));
 const ceiling=keep(new T.MeshStandardMaterial({color:0xe3dcc8,bumpMap:plasterMap,bumpScale:.015,roughness:.98}));
 const glow=keep(new T.MeshStandardMaterial({color:0xffe2a7,emissive:0xffbf64,emissiveIntensity:1.6,roughness:.7}));
 const unit=geo('box',()=>new T.BoxGeometry(1,1,1));
 function mesh(parent,g,m,x=0,y=0,z=0){const o=new T.Mesh(g,m);o.position.set(x,y,z);o.castShadow=o.receiveShadow=true;parent.add(o);return o}
 function box(p,m,x,y,z,w,h,d){const o=mesh(p,unit,m,x,y,z);o.scale.set(w,h,d);return o}
 function rod(p,m,a,b,r=.1){const av=new T.Vector3(...a),bv=new T.Vector3(...b),v=bv.clone().sub(av),o=mesh(p,geo('rod',()=>new T.CylinderGeometry(1,1,1,20)),m);o.position.copy(av.add(bv).multiplyScalar(.5));o.quaternion.setFromUnitVectors(new T.Vector3(0,1,0),v.clone().normalize());o.scale.set(r,v.length(),r);return o}
 function sphere(p,m,x,y,z,sx,sy,sz){const o=mesh(p,geo('sphere',()=>new T.SphereGeometry(1,24,16)),m,x,y,z);o.scale.set(sx,sy,sz);return o}
 function rounded(p,w,d,h,r,m,x=0,y=0,z=0){
  const key=[w,d,h,r].join(':');const g=geo(key,()=>{const s=new T.Shape(),a=w/2,b=d/2;s.moveTo(-a+r,-b);s.lineTo(a-r,-b);s.quadraticCurveTo(a,-b,a,-b+r);s.lineTo(a,b-r);s.quadraticCurveTo(a,b,a-r,b);s.lineTo(-a+r,b);s.quadraticCurveTo(-a,b,-a,b-r);s.lineTo(-a,-b+r);s.quadraticCurveTo(-a,-b,-a+r,-b);const g=new T.ExtrudeGeometry(s,{depth:h,bevelEnabled:true,bevelSize:.07,bevelThickness:.07,bevelSegments:3,curveSegments:10,steps:1});g.rotateX(-Math.PI/2);const pos=g.attributes.position,uv=g.attributes.uv;for(let i=0;i<pos.count;i++)uv.setXY(i,pos.getX(i)/w+.5,pos.getZ(i)/d+.5);return g});return mesh(p,g,m,x,y,z);
 }
 function molding(p,m,x,y,z,w,h){
  for(const a of [-1,1]){box(p,m,x+a*w/2,y,z,.17,h,.19);box(p,m,x,y+a*h/2,z,w,.17,.19)}
 }
 function label(text,sub,w=1024,h=256){return canvasTexture(w,h,(c,W,H)=>{c.fillStyle='#153f32';c.fillRect(0,0,W,H);c.strokeStyle='#ad925b';c.lineWidth=3;c.strokeRect(15,15,W-30,H-30);c.textAlign='center';c.fillStyle='#e2c998';c.font='54px Georgia';c.fillText(text,W/2,sub?115:H*.64);if(sub){c.font='19px Georgia';c.fillStyle='#c3c5b3';c.fillText(sub,W/2,174)}})}
 function sign(p,text,sub,x,y,z,w,h){box(p,gold,x,y,z,w+.22,h+.22,.24);const m=keep(new T.MeshStandardMaterial({map:label(text,sub),roughness:.8}));box(p,m,x,y,z+.14,w,h,.035)}
 function lathe(p,key,points,m,x,y,z){return mesh(p,geo(key,()=>new T.LatheGeometry(points.map(v=>new T.Vector2(...v)),32)),m,x,y,z)}

 // Parquet is made from individual sawn blocks; material and grain are shared,
 // but each block gets a small deterministic tone variation through instancing.
 box(root,darkWood,0,floor-.18,(back+front)/2,half*2,.36,front-back);
 const planks=[];for(let r=0;r<15;r++)for(let col=0;col<12;col++)for(let i=0;i<5;i++){
  const flip=(r+col)%2,centerX=-55+col*10,centerZ=-89+r*10;
  planks.push({x:centerX+(flip?0:i*2-4),z:centerZ+(flip?i*2-4:0),a:flip?Math.PI/2:0});
 }
 const block=geo('parquet',()=>new T.BoxGeometry(1.985,.13,9.985)),instance=new T.InstancedMesh(block,oak,planks.length),dummy=new T.Object3D();
 planks.forEach((p,i)=>{dummy.position.set(p.x,floor+.04,p.z);dummy.rotation.y=p.a;dummy.updateMatrix();instance.setMatrixAt(i,dummy.matrix);instance.setColorAt(i,new T.Color().setRGB(.77+random()*.15,.77+random()*.15,.77+random()*.15))});instance.receiveShadow=true;root.add(instance);
 for(const x of [-60.6,60.6])box(root,walnut,x,floor+.11,-19.5,1,.16,152);for(const z of [-94.8,55.8])box(root,walnut,0,floor+.11,z,120,.16,1.0);

 // Fully enclosed shell with real window openings in the west wall.
 // A genuine doorway through the shell, with a short illuminated vestibule.
 // The leaf opens away from the players and the aisle stays clear of furniture.
 for(const [a,b] of [[-half,13.5],[30.5,half]])box(root,plaster,(a+b)/2,(floor+top)/2,back,b-a,top-floor,1);
 box(root,plaster,22,(floor+38+top)/2,back,17,top-floor-38,1);
 box(root,plaster,half,(floor+top)/2,-19.5,1,top-floor,153);
 box(root,plaster,0,(floor+top)/2,front,half*2,top-floor,1);
 for(const [a,b] of [[back,-75],[-39,-19],[17,front]])box(root,plaster,-half,(floor+top)/2,(a+b)/2,1,top-floor,b-a);
 for(const z of [-57,-1]){box(root,plaster,-half,floor+13.25,z,1,26.5,36);box(root,plaster,-half,44,z,1,6,36)}
 box(root,ceiling,0,top,-19.5,half*2,1,153);
 // Walnut paneling, raised panels, skirting and soft rounded chair rails.
 function paneledWall(width){const g=new T.Group();box(g,walnut,0,floor+7.8,0,width,15.6,.65);box(g,darkWood,0,floor+1,0,width,2,.85);box(g,gold,0,floor+15.72,.14,width,.09,.68);box(g,walnut,0,floor+15.85,.0,width,.35,.95);const n=Math.floor(width/10);for(let i=0;i<n;i++){const x=(i-(n-1)/2)*(width/n);box(g,darkWood,x,floor+8,.36,width/n-1.2,10.4,.04);molding(g,oak,x,floor+8,.48,width/n-1.2,10.4);molding(g,walnut,x,floor+8,.54,width/n-1.65,9.9)}return g}
 for(const [a,b] of [[-half,13.5],[30.5,half]]){const rear=paneledWall(b-a);rear.position.set((a+b)/2,0,back+.7);root.add(rear)}const east=paneledWall(153);east.rotation.y=-Math.PI/2;east.position.set(half-.7,0,-19.5);root.add(east);const west=paneledWall(153);west.rotation.y=Math.PI/2;west.position.set(-half+.7,0,-19.5);root.add(west);const south=paneledWall(124);south.rotation.y=Math.PI;south.position.z=front-.7;root.add(south);
 // End the vestibule at the rear face of the wall. Its pale front caps used
 // to share the green wall's front plane, flashing white as the camera panned.
 box(root,oak,22,floor-.1,-107.5,19,.25,22);box(root,cream,12.8,floor+20,-107.5,1,40,22);box(root,cream,31.2,floor+20,-107.5,1,40,22);box(root,plaster,22,floor+20,-119,19,40,1);box(root,ceiling,22,floor+40,-107.5,19,.5,22);
 for(const x of [13.2,30.8]){box(root,walnut,x,floor+19,back+.5,.8,39,2);box(root,gold,x,floor+19,back+1.55,.10,38,.06)}box(root,walnut,22,floor+38.7,back+.5,19,1.0,2);
 const doorLeaf=new T.Group();doorLeaf.name='Opening club entrance';doorLeaf.userData.dynamic=true;doorLeaf.position.set(13.65,floor+.14,back+.35);root.add(doorLeaf);
 box(doorLeaf,walnut,8.3,18.9,0,16.6,37.7,.6);
 for(const y of [8.6,25.7])for(const face of [-1,1]){box(doorLeaf,darkWood,8.3,y,face*.32,13.1,14,.03);molding(doorLeaf,oak,8.3,y,face*.39,13.2,14.1)}
 for(const face of [-1,1]){rod(doorLeaf,gold,[14.2,17,face*.7],[14.2,20,face*.7],.12);rod(doorLeaf,gold,[14.2,17,face*.3],[14.2,17,face*.8],.10);rod(doorLeaf,gold,[14.2,20,face*.3],[14.2,20,face*.8],.10)}
 for(const y of [4,19,34])rod(doorLeaf,gold,[0,y-.65,0],[0,y+.65,0],.20);
 sign(root,'WELCOME','CHESS CLUB',22,29,back+.8,16,4.5);
 // A diffused ceiling fixture stays above the visitor route. The former point
 // source sat at head height; visitors passed through it and their hair flashed
 // almost white from the inverse-square intensity spike.
 const entryLight=new T.RectAreaLight(0xffdda8,.85,6,4);entryLight.name='Vestibule ceiling diffuser';entryLight.position.set(22,25.6,-107);entryLight.lookAt(22,floor,-107);root.add(entryLight);
 box(root,iron,22,25.95,-107,6.4,.35,4.4);box(root,glow,22,25.72,-107,6,.10,4);
 const door={group:doorLeaf,update(amount){doorLeaf.rotation.y=1.38*T.MathUtils.clamp(amount,0,1)}};
 // Recessed coffers and plaster crown moldings.
 for(const x of [-61,-30,0,30,61]){box(root,cream,x,top-1.1,-19.5,1.25,2.0,153);box(root,cream,x,top-2.15,-19.5,1.5,.25,153)}
 for(const z of [-95,-57,-19,19,56]){box(root,cream,0,top-1.1,z,124,2.0,1.25);box(root,cream,0,top-2.15,z,124,.25,1.5)}
 for(const x of [-61,61]){box(root,cream,x,top-2.8,-19.5,1.25,.5,153);box(root,cream,x,top-3.5,-19.5,.85,.35,153)}
 for(const z of [back+1,front-1]){box(root,cream,0,top-2.8,z,124,.5,1.25);box(root,cream,0,top-3.5,z,124,.35,.85)}

 // Tall sash windows, deep reveals and linen curtains with subtle motion.
 const linenMap=canvasTexture(128,128,(c,W,H)=>{c.fillStyle='#aeb1a4';c.fillRect(0,0,W,H);for(let i=0;i<128;i++){c.fillStyle=i%3?'#ffffff10':'#20211628';c.fillRect(i,0,1,H);c.fillRect(0,i,W,1)}});linenMap.wrapS=linenMap.wrapT=T.RepeatWrapping;linenMap.repeat.set(6,10);
 const linen=keep(new T.MeshStandardMaterial({color:0xd3ceb9,map:linenMap,bumpMap:linenMap,bumpScale:.025,roughness:1,side:T.DoubleSide}));
 const sky=keep(new T.MeshBasicMaterial({color:0xb2c8c7}));
 for(const z of [-57,-1]){
  const g=new T.Group();g.position.set(-half+.75,0,z);g.rotation.y=Math.PI/2;root.add(g);
  const daylight=box(g,sky,0,27,-2.5,36,28,.1);daylight.castShadow=daylight.receiveShadow=false;daylight.userData.dynamic=true;
  for(const x of [-18,18])box(g,cream,x,27,0,1.4,28,2.4);for(const y of [13,41])box(g,cream,0,y,0,38,1.2,2.6);
  for(const x of [-8.4,0,8.4])box(g,cream,x,27,.22,.35,26,1.0);box(g,cream,0,27,.22,36,.50,1.1);
  rounded(g,40,3,.6,.15,cream,0,12.65,.7);
  rod(g,gold,[-23,42.3,1.6],[23,42.3,1.6],.13);
  for(const side of [-1,1]){
   const width=9.0,height=41.8-floor-1.6,geoCurtain=own(new T.PlaneGeometry(width,height,28,45)),p=geoCurtain.attributes.position;
   for(let i=0;i<p.count;i++){const u=p.getX(i)/width+.5,v=p.getY(i)/height+.5;p.setZ(i,Math.sin(u*Math.PI*10)*.47+.08*Math.cos(v*6));p.setX(i,p.getX(i)+Math.sin(v*Math.PI)*side*.65)}
   geoCurtain.computeVertexNormals();const curtain=mesh(g,geoCurtain,linen,side*20,(41.8+floor+1.6)/2,1.6);curtain.userData.dynamic=true;const rest=Float32Array.from(p.array);
   animations.push(t=>{for(let i=0;i<p.count;i++){const v=(rest[i*3+1]/height+.5);p.setZ(i,rest[i*3+2]+Math.sin(t*.37+rest[i*3]*.4+v*2)*.20*(1-v))}p.needsUpdate=true;geoCurtain.computeVertexNormals()});
   for(let i=0;i<8;i++){const ring=mesh(g,geo('curtain ring',()=>new T.TorusGeometry(.23,.055,8,16)),gold,side*20+(i-3.5)*1.03,42.0,1.6);ring.rotation.y=Math.PI/2}
  }
 }

 // A woven rug under the main board; a warm visual anchor, not a flat floor overlay.
 const rugMap=canvasTexture(1536,1792,(c,W,H)=>{
  c.fillStyle='#6a3a30';c.fillRect(0,0,W,H);c.strokeStyle='#b19060';c.lineWidth=28;c.strokeRect(65,65,W-130,H-130);c.strokeStyle='#243d35';c.lineWidth=55;c.strokeRect(115,115,W-230,H-230);c.strokeStyle='#ba9561';c.lineWidth=8;c.strokeRect(165,165,W-330,H-330);
  function diamond(x,y,r,color){c.fillStyle=color;c.beginPath();c.moveTo(x,y-r);c.lineTo(x+r*.62,y);c.lineTo(x,y+r);c.lineTo(x-r*.62,y);c.closePath();c.fill()}
  for(let y=210;y<H-200;y+=120)for(let x=220;x<W-200;x+=112){diamond(x,y,25,'#b79865');diamond(x,y,15,'#4a614c');for(const d of [-1,1]){c.strokeStyle='#b79865';c.lineWidth=3;c.beginPath();c.moveTo(x,y+27);c.quadraticCurveTo(x+d*35,y+50,x+d*12,y+65);c.stroke()}}
  for(let y=150;y<H-130;y+=73){diamond(115,y,17,'#cfb880');diamond(W-115,y,17,'#cfb880')}
  for(let x=145;x<W-130;x+=72){diamond(x,115,18,'#cfb880');diamond(x,H-115,18,'#cfb880')}
  diamond(W/2,H/2,265,'#c09c68');diamond(W/2,H/2,235,'#233d32');diamond(W/2,H/2,185,'#b78c5b');diamond(W/2,H/2,158,'#703e32');diamond(W/2,H/2,71,'#c8a576');
  for(let y=0;y<H;y+=2){c.fillStyle=y%4?'#00000013':'#ffffff0b';c.fillRect(0,y,W,1)}for(let i=0;i<200000;i++){c.fillStyle=random()>.5?'#ffffff0a':'#00000014';c.fillRect(random()*W,random()*H,1,2)}
 });
 const rug=keep(new T.MeshStandardMaterial({map:rugMap,roughness:1,bumpMap:rugMap,bumpScale:.012}));box(root,material(0x34281f),0,floor+.14,0,37.5,.10,42.5);const rugFace=mesh(root,geo('rug',()=>new T.PlaneGeometry(37.4,42.4)),rug,0,floor+.20,0);rugFace.rotation.x=-Math.PI/2;

 function chair(parent,x,z,rotation=0){
  const g=new T.Group();g.position.set(x,floor,z);g.rotation.y=rotation;parent.add(g);
  // Continuous curved back, tailored seat, piping and real joinery.
  rounded(g,7.6,6.9,.4,.75,walnut,0,7.45,0);rounded(g,7.2,6.55,.62,.86,leather,0,7.87,.07);
  const backGeo=geo('chair back',()=>{const shape=new T.Shape();shape.moveTo(-3.6,0);shape.lineTo(-3.6,6);shape.bezierCurveTo(-3.6,8.4,3.6,8.4,3.6,6);shape.lineTo(3.6,0);shape.closePath();const geo=new T.ExtrudeGeometry(shape,{depth:.55,bevelEnabled:true,bevelSize:.2,bevelThickness:.18,bevelSegments:4,curveSegments:16});const p=geo.attributes.position;for(let i=0;i<p.count;i++)p.setZ(i,p.getZ(i)+Math.pow(p.getX(i)/3.6,2)*.7);geo.computeVertexNormals();return geo});
  const b=mesh(g,backGeo,walnut,0,8,-3);b.rotation.x=-.08;
  const cushionGeo=geo('chair cushion',()=>{const geo=new T.PlaneGeometry(6.2,6.3,28,28),p=geo.attributes.position;for(let i=0;i<p.count;i++){const x=p.getX(i),v=(p.getY(i)+3.15)/6.3;const edge=Math.max(0,1-(x/3.1)**2);p.setY(i,p.getY(i)+Math.sqrt(edge)*.64*v**8);p.setZ(i,(x/3.1)**2*.62+Math.sqrt(edge)*Math.sin(v*Math.PI)*.48)}geo.computeVertexNormals();return geo});const cushion=mesh(g,cushionGeo,leather,0,11.6,-1.65);cushion.rotation.x=-.08;
  for(const x of [-2.93,2.93])for(const z of [-2.5,2.5]){rod(g,walnut,[x,7.3,z],[x*1.13,.3,z*1.13],.28);sphere(g,gold,x*1.13,.28,z*1.13,.30,.20,.30)}
  for(const x of [-2.94,2.94])rod(g,walnut,[x,3.2,-2.5],[x,3.2,2.5],.18);
  for(let i=0;i<11;i++)sphere(g,gold,-2.8+i*.56,7.55,3.4,.055,.055,.055);
  return g;
 }
 function table(x,z,angle=0,main=false){
  const g=new T.Group();g.position.set(x,0,z);g.rotation.y=angle;root.add(g);const w=main?22:20,d=main?17:15;
  rounded(g,w,d,.50,.65,darkWood,0,-1.05,0);rounded(g,w-.14,d-.14,.055,.60,gold,0,-.56,0);rounded(g,w-.28,d-.28,.10,.54,walnut,0,-.49,0);
  for(const z of [-1,1])box(g,walnut,0,-1.5,z*(d/2-1),w-2,1.7,.55);for(const x of [-1,1])box(g,walnut,x*(w/2-1),-1.5,0,.55,1.7,d-2);
  for(const a of [-1,1])for(const b of [-1,1])lathe(g,'turned leg',[[.31,0],[.36,.2],[.27,.6],[.23,1.4],[.31,3.4],[.44,4.7],[.40,5.2],[.29,5.7],[.29,8.0],[.45,8.5],[.45,10.9],[.5,11.5],[.5,12.2]],walnut,a*(w/2-1.55),floor,b*(d/2-1.5));
  chair(g,0,-d/2-(main?4.8:3.3),0);chair(g,0,d/2+(main?4.8:3.3),Math.PI);
  return g;
 }
 const mainTable=table(0,0,0,true),leftTable=table(-29,-42,.10),rightTable=table(29,-47,-.10);

 function scoresheet(parent,x,z,angle){const map=canvasTexture(512,768,(c,w,h)=>{c.fillStyle='#e4dfca';c.fillRect(0,0,w,h);c.fillStyle='#364d3f';c.font='25px Georgia';c.fillText('ENGINE ARENA',30,45);c.font='16px Georgia';c.fillText('CHESS CLUB     •     SCORESHEET',30,80);c.strokeStyle='#9b9c8a';c.lineWidth=1;for(let y=110;y<h-20;y+=35){c.beginPath();c.moveTo(22,y);c.lineTo(w-22,y);c.stroke()}c.font='italic 18px Georgia';['e4     e5','Nf3    Nc6','Bb5    a6','Ba4    Nf6','O-O    Be7','Re1    b5','Bb3    d6'].forEach((s,i)=>c.fillText(`${i+1}.   ${s}`,40,140+i*35))});const g=new T.Group();g.position.set(x,-.075,z);g.rotation.y=angle;parent.add(g);const paper=keep(new T.MeshStandardMaterial({map,roughness:1}));const face=mesh(g,geo('sheet',()=>new T.PlaneGeometry(2.8,4.1)),paper);face.rotation.x=-Math.PI/2;rod(g,iron,[1.9,.06,-1.6],[1.9,.06,1.7],.065);rod(g,gold,[1.9,.06,1.5],[1.9,.06,1.85],.073)}
 function cup(parent,x,z){lathe(parent,'teacup',[[.27,0],[.36,.04],[.47,.6],[.47,.72],[.42,.72],[.4,.2],[.27,.1]],cream,x,-.06,z);lathe(parent,'saucer',[[0,0],[.78,0],[.78,.055],[.62,.09],[.3,.06],[0,.05]],cream,x,-.08,z);const tea=mesh(parent,geo('tea',()=>new T.CircleGeometry(.414,32)),material(0x442317,.18),x,.59,z);tea.rotation.x=-Math.PI/2;const handle=mesh(parent,geo('cup handle',()=>new T.TorusGeometry(.24,.065,10,24)),cream,x+.48,.33,z);handle.scale.x=.7}
 const clocks=[];
 function gameClock(parent,index){
  // Beside the h-file, outside even the captured-piece tray. Local +X is
  // White's half after turning the face toward the board; neither player's
  // reach crosses the other half. Rubber feet rest on the table at y=-.32.
  const g=new T.Group();g.name=index?'Illustrative side clock':'Live game side clock';g.userData.dynamic=true;parent.add(g);g.position.set(8.15,-.28,0);g.rotation.y=-Math.PI/2;
  for(const x of [-1.65,1.65])for(const z of [-.38,.38])box(g,iron,x,0,z,.24,.08,.24);
  // A sloping display fascia, like a real two-button digital clock. Its face
  // stays above the housing, so the LCD is readable from either player's seat.
  const profile=new T.Shape();profile.moveTo(-.68,.08);profile.lineTo(.70,.08);profile.lineTo(.70,.34);profile.lineTo(.12,.98);profile.lineTo(-.68,.98);profile.closePath();
  const housing=own(new T.ExtrudeGeometry(profile,{depth:4.2,bevelEnabled:true,bevelSize:.065,bevelThickness:.065,bevelSegments:3,steps:1}));housing.rotateY(-Math.PI/2);housing.translate(2.1,0,0);mesh(g,housing,walnut);
  const fascia=new T.Group();fascia.position.set(0,.68,.47);fascia.rotation.x=-.74;g.add(fascia);
  box(fascia,iron,0,0,0,3.91,.81,.045);
  const map=canvasTexture(1024,224,()=>{}),m=keep(new T.MeshStandardMaterial({map,roughness:.72,metalness:0}));box(fascia,m,0,0,.035,3.62,.67,.02);
  const buttons=[-1,1].map(x=>{const b=rounded(g,1.30,.48,.11,.09,iron,x,1.07,-.35);b.userData.dynamic=true;return b});
  let previous='';const set=data=>{const values=[data?.black,data?.white],signature=JSON.stringify(values);if(signature===previous)return;previous=signature;
   const c=map.image.getContext('2d');c.fillStyle='#a9b99b';c.fillRect(0,0,1024,224);c.fillStyle='#324b38';c.fillRect(507,10,10,204);c.textAlign='center';c.textBaseline='middle';
   values.forEach((v,i)=>{const x=256+i*512;c.fillStyle='#233c2b';c.font='24px sans-serif';c.fillText(i?'WHITE':'BLACK',x,30);const s=v?.text||'—';let n=104;c.font=`600 ${n}px monospace`;while(c.measureText(s).width>472&&n>36)c.font=`600 ${n-=2}px monospace`;c.fillText(s,x,116);c.font='23px sans-serif';c.fillText(v?.stale?'WAIT':v?.mode||(v?.active?'RUNNING':''),x,191);buttons[i].position.y=v?.active?1.14:values.some(x=>x?.active)?1.04:1.09});map.needsUpdate=true;
  };set(null);clocks.push({group:g,set});
 }
 [mainTable,leftTable,rightTable].forEach((t,i)=>{gameClock(t,i);if(i)scoresheet(t,-7.7,.7,-.06);cup(t,-7.9,-4.6)});

 // Bookshelves with shelves, shelf pins, separately bound spines and cornices.
 const bookColors=[0x6a3230,0x32483d,0x354453,0x8c7048,0x5e5146,0x382e29];const bindings=bookColors.map(c=>material(c,.9)),readingBooks=[];
 // Three real shelf volumes can be taken down. Keep them out of the static
 // room batch: their original shelf spaces remain empty while they are held.
 const pageMap=canvasTexture(512,768,(c,W,H)=>{c.fillStyle='#e5d9b8';c.fillRect(0,0,W,H);c.fillStyle='#4c4436';c.font='26px Georgia';c.fillText('CHESS STUDIES',40,62);for(let r=0;r<8;r++)for(let f=0;f<8;f++){c.fillStyle=(r+f)%2?'#697161':'#d0c7aa';c.fillRect(112+f*36,106+r*36,36,36)}c.fillStyle='#39392e';c.font='32px "Segoe UI Symbol"';c.fillText('♚',186,140);c.fillText('♔',222,356);c.fillText('♟',258,285);for(let line=0;line<15;line++){c.fillStyle='#756955';c.fillRect(42,445+line*17,line%5===4?255:420,2)}});
 const paper=keep(new T.MeshStandardMaterial({map:pageMap,roughness:.97,side:T.DoubleSide}));
 function readableBook(parent,w,h,m,index){
  const b=new T.Group();b.name='Reading volume '+index;b.userData.dynamic=true;parent.add(b);
  const left=new T.Group(),right=new T.Group();b.add(left,right);left.position.x=-w/2;right.position.x=w/2;
  for(const [pivot,sign] of [[left,-1],[right,1]]){box(pivot,m,0,0,-1.3,.09,h,2.6);box(pivot,cream,-sign*w*.23,0,-1.3,w*.42,h-.24,2.36);const face=mesh(pivot,geo('reading page',()=>new T.PlaneGeometry(2.3,h-.26)),paper,-sign*w*.46,0,-1.30);face.rotation.y=-sign*Math.PI/2;}
  box(b,m,0,0,.02,w+.12,h,.13);for(const y of [-h*.40,-h*.34,h*.34,h*.40])box(b,gold,0,y,.095,w,.03,.012);
  const spine=label(['ENDGAMES','STRATEGY','MASTERS'][index],'',512,128),title=mesh(b,geo('reading spine',()=>new T.PlaneGeometry(1.8,.30)),keep(new T.MeshStandardMaterial({map:spine,roughness:.8})),0,.1,.10);title.rotation.z=Math.PI/2;
  const turn=new T.Group();b.add(turn);const leaf=mesh(turn,geo('turning page',()=>new T.PlaneGeometry(2.32,h-.27)),paper,0,0,-1.22);leaf.rotation.y=-Math.PI/2;turn.visible=false;
  const entry={root:b,left,right,turn,width:w,height:h};readingBooks.push(entry);return entry;
 }
 function bookshelf(x){const g=new T.Group();g.position.set(x,0,back+4.2);root.add(g);box(g,darkWood,0,8,-2,25,42,.55);for(const a of [-12.7,12.7]){box(g,walnut,a,8,0,.8,43,5.4);molding(g,oak,a,8,2.9,.50,40)}for(const y of [floor+.3,-4.5,4,12.5,21,29.5]){box(g,walnut,0,y,0,26,.55,5.8);box(g,gold,0,y+.10,3,26,.07,.07)}rounded(g,27,6.5,.5,.15,walnut,0,30,0);box(g,walnut,0,-11,1.9,25,4,1.2);
  for(const [row,y] of [-4.2,4.3,12.8,21.3].entries()){let pos=-11.7;let index=0;while(pos<11){const w=.60+random()*.8,h=5.9+random()*1.8;const b=new T.Group();b.position.set(pos+w/2,y,1.3);b.rotation.z=(index%11===8?-.045:0);g.add(b);const m=bindings[Math.floor(random()*bindings.length)];if(x<0&&row===1&&pos>6&&readingBooks.length<3){const entry=readableBook(b,w,h,m,readingBooks.length);entry.root.position.set(0,h/2,1.3)}else{box(b,m,0,h/2,0,w,h,2.6);box(b,cream,0,h-.13,0,w-.14,.06,2.35);for(const a of [.47,.75,h-.75,h-.47])box(b,gold,0,a,1.31,w*.9,.025,.025);if(index%3===0){const tex=label(['CHESS','ENDGAMES','STRATEGY','MASTERS'][(row+index)%4],'',256,64);const face=mesh(b,geo('book type',()=>new T.PlaneGeometry(1,.25)),keep(new T.MeshStandardMaterial({map:tex,roughness:.8})),0,h*.6,1.324);face.rotation.z=Math.PI/2;face.scale.x=1.8}}pos+=w+.10;index++}}
 }
 bookshelf(-46);bookshelf(46);
 root.updateWorldMatrix(true,true);
 for(const book of readingBooks){root.attach(book.root);book.home=book.root.position.clone();book.rotation=book.root.quaternion.clone();}
 const library={books:readingBooks,reset(){for(const b of readingBooks){b.root.position.copy(b.home);b.root.quaternion.copy(b.rotation);b.left.rotation.y=b.right.rotation.y=0;b.turn.visible=false;b.root.updateWorldMatrix(true,true)}},pose(index,position,quaternion,open,page){const b=readingBooks[index];b.root.position.copy(root.worldToLocal(position.clone()));b.root.quaternion.copy(root.getWorldQuaternion(new T.Quaternion()).invert().multiply(quaternion));b.left.rotation.y=open*1.30;b.right.rotation.y=-open*1.30;b.turn.visible=page>0&&page<1;b.turn.rotation.y=(-1.30+page*2.60)*open;b.root.updateWorldMatrix(true,true);return b;}};
 sign(root,'ENGINE ARENA','THE CHESS CLUB',-5,31,back+.9,29,7.6);
 // An analysis board with an actual opening position, not decorative gibberish.
 const diagram=canvasTexture(1024,1024,(c,W,H)=>{c.fillStyle='#ccbc96';c.fillRect(0,0,W,H);const s=104,off=96,rows=['r.bqkbnr','pppp.ppp','..n.....','.B..p...','....P...','.....N..','PPPP.PPP','RNBQK..R'],glyph={r:'♜',n:'♞',b:'♝',q:'♛',k:'♚',p:'♟'};c.textAlign='center';c.textBaseline='middle';for(let r=0;r<8;r++)for(let f=0;f<8;f++){c.fillStyle=(r+f)%2?'#446354':'#d4d2ae';c.fillRect(off+f*s,off+r*s,s,s);const p=rows[r][f];if(p!=='.'){c.font='86px "Segoe UI Symbol"';c.fillStyle=p===p.toUpperCase()?'#fcf4d7':'#172d26';c.strokeStyle='#1a3028';c.lineWidth=1.5;c.strokeText(glyph[p.toLowerCase()],off+(f+.5)*s,off+(r+.54)*s);c.fillText(glyph[p.toLowerCase()],off+(f+.5)*s,off+(r+.54)*s)}}c.fillStyle='#344537';c.font='24px Georgia';for(let i=0;i<8;i++){c.fillText('abcdefgh'[i],off+(i+.5)*s,953);c.fillText(String(8-i),53,off+(i+.5)*s)}});
 box(root,walnut,0,12,back+1.4,23,23,.7);box(root,gold,0,12,back+1.83,22.5,22.5,.1);box(root,keep(new T.MeshStandardMaterial({map:diagram,roughness:.96})),0,12,back+1.9,21.9,21.9,.08);
 // Pendulum clock adds a small, plausible movement independent of camera motion.
 const clock=new T.Group();clock.position.set(half-1,16,-46);clock.rotation.y=-Math.PI/2;root.add(clock);box(clock,walnut,0,0,0,9,23,2.6);molding(clock,gold,0,0,1.4,8,22);
 const faceMap=canvasTexture(512,512,(c,W,H)=>{c.fillStyle='#d6cbb3';c.fillRect(0,0,W,H);c.strokeStyle='#6b5840';c.lineWidth=5;c.beginPath();c.arc(256,256,232,0,Math.PI*2);c.stroke();c.textAlign='center';c.textBaseline='middle';c.fillStyle='#2e3930';c.font='27px Georgia';for(let i=1;i<=12;i++){const a=i*Math.PI/6;c.fillText(String(i),256+Math.sin(a)*196,256-Math.cos(a)*196)}});const face=mesh(clock,geo('clock face',()=>new T.CircleGeometry(3.6,64)),keep(new T.MeshStandardMaterial({map:faceMap,roughness:.8})),0,5.8,1.5);face.castShadow=false;
 const hands=new T.Group();hands.position.set(0,5.8,1.58);clock.add(hands);
 const minute=new T.Group(),hour=new T.Group(),second=new T.Group();for(const h of [minute,hour,second]){h.userData.dynamic=true;hands.add(h)}
 box(minute,iron,0,1.35,0,.12,2.8,.08);box(hour,iron,0,.85,.08,.20,1.8,.08);box(second,material(0x9b493e,.5),0,1.25,.17,.048,3.3,.05);sphere(hands,gold,0,0,.24,.19,.19,.12);
 function setTime(date,automatic=true,manual='tournament'){
  const time=clubTime(date);minute.rotation.z=time.minute;hour.rotation.z=time.hour;second.rotation.z=time.second;
  const day=automatic?time.day:manual==='evening'?.12:1;
  sky.color.set(0x0b152b).lerp(new T.Color(0xb2c8c7),day);if(automatic)sky.color.lerp(new T.Color(0xd4a587),time.twilight*.38);
  glow.emissiveIntensity=1.6+(1-day)*1.4;return time;
 }
 setTime(new Date());
 box(clock,material(0x152820),0,-5.2,1.36,6.6,10.3,.02);const swing=new T.Group();swing.position.set(0,-1,1.65);swing.userData.dynamic=true;clock.add(swing);rod(swing,gold,[0,0,0],[0,-7.7,0],.10);sphere(swing,gold,0,-7.7,0,1.35,1.35,.22);animations.push(t=>{swing.rotation.z=Math.sin(t*2.2)*.10});

 function pendant(x,z,y=32){const g=new T.Group();g.position.set(x,y,z);root.add(g);rod(g,iron,[0,0,0],[0,top-y,0],.11);lathe(g,'lamp shade',[[0,3.8],[.8,3.8],[1.1,3.2],[2.6,1.5],[5.2,.1],[5.2,0],[4.9,-.13],[1.1,3.1],[0,3.1]],material(0x315b4d,.48,.3),0,0,0);const disk=mesh(g,geo('lamp glow',()=>new T.CircleGeometry(4.8,48)),glow,0,-.11,0);disk.rotation.x=Math.PI/2;sphere(g,glow,0,1.3,0,.8,.8,.8);lathe(g,'shade rim',[[4.9,0],[5.2,0],[5.2,.13],[4.9,.13]],gold,0,-.04,0);}
 pendant(0,0,32);pendant(-29,-42,33);pendant(29,-47,33);

 // Potted palms: custom curved leaves, not colored balls for foliage.
 const leafMaterials=[0x274337,0x385b3d,0x4e6a41].map(c=>keep(new T.MeshStandardMaterial({color:c,roughness:.87,side:T.DoubleSide})));
 function palm(x,z,index){const g=new T.Group();g.position.set(x,floor,z);root.add(g);lathe(g,'pot',[[0,0],[2.2,0],[2.3,.3],[3.1,5.6],[3.25,5.8],[3.25,6.1],[2.95,6.1],[2.85,5.7],[2.6,5.3]],material(0x8d7256,.95),0,0,0);const soil=mesh(g,geo('soil',()=>new T.CircleGeometry(2.83,24)),material(0x282820),0,5.6,0);soil.rotation.x=-Math.PI/2;
  for(let i=0;i<16;i++){const a=i*2.4+index,length=8+random()*7,height=8+random()*6,curve=new T.QuadraticBezierCurve3(new T.Vector3(0,5.5,0),new T.Vector3(Math.cos(a)*length*.28,height+6,Math.sin(a)*length*.28),new T.Vector3(Math.cos(a)*length,height,Math.sin(a)*length));mesh(g,own(new T.TubeGeometry(curve,12,.037,4,false)),leafMaterials[0]);const leaf=new T.Group();leaf.userData.dynamic=true;g.add(leaf);
   for(let j=2;j<12;j++){const t=j/12,p=curve.getPoint(t),w=Math.sin(t*Math.PI)*2.1;for(const side of [-1,1]){const shape=new T.Shape();shape.moveTo(0,0);shape.quadraticCurveTo(w*.32,.40,w,0);shape.quadraticCurveTo(w*.36,-.20,0,0);const l=mesh(leaf,own(new T.ShapeGeometry(shape,5)),leafMaterials[(i+j)%3],p.x,p.y,p.z);l.rotation.set(-Math.PI/2+.25,a+side*Math.PI/2,.12*side);l.scale.x=side}}
   batch(leaf);animations.push(t=>{leaf.rotation.z=Math.sin(t*.3+i*.9)*.004;leaf.rotation.x=Math.cos(t*.27+i)*.006});
  }
 }
 palm(-49,-27,0);palm(47,25,1);

 // Club memorabilia and useful everyday details. Keep the center aisle and
 // visitor routes clear; décor is attached to the walls and entrance corners.
 function wallGroup(z){const g=new T.Group();g.position.set(60.6,0,z);g.rotation.y=-Math.PI/2;root.add(g);return g}
 const display=wallGroup(-10);
 box(display,darkWood,0,7,0,27,26,4);box(display,walnut,0,-6,2.4,28,1.1,7);
 for(const x of [-13.8,13.8])box(display,walnut,x,7,2.8,.7,27,6);
 box(display,walnut,0,20.5,2.8,28.3,.7,6);box(display,gold,0,19.9,5.7,27,.10,.09);
 for(const y of [-5.3,7.6]){box(display,walnut,0,y,2.8,27,.6,5.8);box(display,gold,0,y+.32,5.7,27,.08,.08)}
 const bronze=material(0xb58651,.3,.8),silver=material(0xb5b9b4,.26,.88);
 for(const [i,x] of [-8.5,0,8.5].entries()){
  const y=8,metal=[silver,gold,bronze][i],h=[7.2,9.2,6.5][i];
  rounded(display,4.2,3.4,.5,.15,darkWood,x,y,3.1);
  lathe(display,'trophy '+i,[[1.55,0],[1.65,.3],[.8,.65],[.38,1.4],[.35,h*.5],[.75,h*.54],[1.3,h*.65],[1.8,h*.86],[1.9,h],[1.7,h],[1.6,h*.86],[1.15,h*.69],[.4,h*.60]],metal,x,y+.5,3.1);
  for(const s of [-1,1]){const curve=new T.CubicBezierCurve3(new T.Vector3(x+s*1.65,y+h*.85,3.1),new T.Vector3(x+s*3.1,y+h,3.1),new T.Vector3(x+s*3.1,y+h*.42,3.1),new T.Vector3(x+s*.8,y+h*.48,3.1));mesh(display,own(new T.TubeGeometry(curve,24,.13,8,false)),metal)}
  sign(display,['RAPID','CLUB CUP','BLITZ'][i],'',x,y+.25,4.86,3.1,.62);
 }
 // Lower shelf: bound tournament records and a retired mechanical clock.
 for(let i=0;i<5;i++)box(display,bindings[i],-10+i*1.2,-1.8,3,1,6.4,3.6);
 rounded(display,8,3.4,4.2,.35,walnut,5,-5,3.1);
 for(const x of [3,7]){const dial=canvasTexture(256,256,(c,w,h)=>{c.fillStyle='#e4d9bd';c.fillRect(0,0,w,h);c.fillStyle='#283b31';c.textAlign='center';c.font='22px Georgia';for(let n=1;n<=12;n++){const a=n*Math.PI/6;c.fillText(n,w/2+Math.sin(a)*98,h/2-Math.cos(a)*98+8)}c.strokeStyle='#273c32';c.lineWidth=5;c.beginPath();c.moveTo(128,54);c.lineTo(128,128);c.lineTo(183,152);c.stroke()});mesh(display,geo('heritage dial',()=>new T.CircleGeometry(1.55,40)),keep(new T.MeshStandardMaterial({map:dial,roughness:.65})),x,-2.9,4.93)}
 sign(display,'CLUB HONOURS','',0,23,1,26,3);
 const notices=wallGroup(-74);box(notices,walnut,0,13,.5,24,21,.5);
 const cork=canvasTexture(1024,896,(c,w,h)=>{c.fillStyle='#aa8962';c.fillRect(0,0,w,h);for(let i=0;i<13000;i++){c.fillStyle=i%2?'#4d361c20':'#e6cfaa40';c.fillRect(random()*w,random()*h,2,2)}
  for(const [x,y,W,H,title,lines] of [[45,40,530,350,'FRIDAY NIGHT CHESS',['Friendly games · 7 pm','All playing strengths welcome','Bring a friend. Find a game.']],[610,85,365,480,'CLUB LADDER',['Challenge a player','Record your result','Play again next week']],[100,445,470,390,'ANALYSIS CORNER',['A game worth sharing?','Bring your scoresheet','Saturday · 10 am']]]){c.save();c.translate(x+W/2,y+H/2);c.rotate(x>600?.035:-.025);c.shadowColor='#241b1740';c.shadowBlur=9;c.fillStyle=x>600?'#d7e3cd':'#f0e6ce';c.fillRect(-W/2,-H/2,W,H);c.shadowBlur=0;c.fillStyle='#26453c';c.textAlign='center';c.font=`bold ${x>600?28:35}px Georgia`;c.fillText(title,0,-H/2+65);c.font='23px Georgia';lines.forEach((s,i)=>c.fillText(s,0,-H/2+130+i*49));c.fillStyle='#9a473a';c.beginPath();c.arc(0,-H/2+15,7,0,Math.PI*2);c.fill();c.restore()}});
 box(notices,keep(new T.MeshStandardMaterial({map:cork,roughness:1})),0,13,.79,22.8,19.8,.03);sign(notices,'AT THE CLUB','',0,25,.5,24,3);
 function art(parent,x,y,z,title,variant){const tex=canvasTexture(768,960,(c,w,h)=>{c.fillStyle=variant?'#ebe0bf':'#e0dacb';c.fillRect(0,0,w,h);c.fillStyle='#315749';c.fillRect(70,65,w-140,h-195);c.strokeStyle='#c7ad72';c.lineWidth=4;for(let i=0;i<6;i++){c.beginPath();c.arc(w/2,h*.43,85+i*39,0,Math.PI*2);c.stroke()}c.fillStyle='#e8d1a1';c.textAlign='center';c.textBaseline='middle';c.font='440px "Segoe UI Symbol"';c.fillText(variant?'♞':'♜',w/2,h*.43);c.fillStyle='#27463b';c.font='31px Georgia';c.fillText(title,w/2,h-67)});box(parent,walnut,x,y,z,14,17.5,.5);box(parent,gold,x,y,z+.29,13.3,16.8,.08);box(parent,keep(new T.MeshStandardMaterial({map:tex,roughness:.92})),x,y,z+.35,12.8,16.3,.03)}
 const artEast=wallGroup(23);art(artEast,0,17,.4,'THE BEAUTY OF THE GAME',1);
 const artWest=new T.Group();artWest.position.set(-60.7,0,-29);artWest.rotation.y=Math.PI/2;root.add(artWest);art(artWest,0,24,0,'THINK. EXPLORE. PLAY.',0);
 // The opposite wall used to be an uninterrupted green plane. A club gallery,
 // reading bench and low cabinet give the reverse camera view a destination.
 const gallery=new T.Group();gallery.name='Club gallery wall';gallery.position.set(0,0,front-.8);gallery.rotation.y=Math.PI;root.add(gallery);
 const mural=canvasTexture(2048,1024,(c,w,h)=>{
  c.fillStyle='#e4d8b9';c.fillRect(0,0,w,h);c.strokeStyle='#9a7b47';c.lineWidth=3;c.strokeRect(35,35,w-70,h-70);
  const grad=c.createLinearGradient(0,0,w,h);grad.addColorStop(0,'#25473c');grad.addColorStop(1,'#132c27');c.fillStyle=grad;c.fillRect(75,75,w-150,h-220);
  c.save();c.beginPath();c.rect(75,75,w-150,h-220);c.clip();c.globalAlpha=.15;
  for(let r=0;r<8;r++)for(let f=0;f<16;f++){c.fillStyle=(r+f)%2?'#ad9868':'#647864';c.fillRect(f*148-100,r*130-80,148,130)}c.restore();
  c.strokeStyle='#bba36a';c.lineWidth=2;for(const x of [500,1024,1548]){c.beginPath();c.arc(x,435,230,0,Math.PI*2);c.stroke()}
  c.textAlign='center';c.textBaseline='middle';c.font='470px "Segoe UI Symbol"';c.fillStyle='#e5d0a1';['♜','♞','♚'].forEach((p,i)=>c.fillText(p,500+i*524,430));
  c.fillStyle='#284739';c.font='51px Georgia';c.fillText('A PLACE TO THINK. A PLACE TO PLAY.',w/2,930);
 });
 box(gallery,darkWood,0,22,.4,47,24.2,.65);molding(gallery,gold,0,22,.78,46.4,23.6);
 box(gallery,keep(new T.MeshStandardMaterial({map:mural,roughness:.88})),0,22,.80,45.5,22.75,.05);
 // Four small matted prints, with different chess subjects, balance the wall.
 for(const [i,x,y] of [[0,-39,28],[1,-39,8],[2,39,28],[3,39,8]]){
  const captions=['THE OPENING','THE MIDDLE GAME','THE ENDGAME','YOUR NEXT MOVE'];
  const print=canvasTexture(768,768,(c,w,h)=>{c.fillStyle='#e9e0ca';c.fillRect(0,0,w,h);c.fillStyle=['#4b675b','#5e5549','#4c5e6b','#705649'][i];c.fillRect(68,60,632,545);c.fillStyle='#ddc99d';c.textAlign='center';c.textBaseline='middle';c.font='385px "Segoe UI Symbol"';c.fillText(['♟','♝','♛','♘'][i],384,327);c.fillStyle='#344b3d';c.font='30px Georgia';c.fillText(captions[i],384,686)});
  box(gallery,walnut,x,y,.4,15.4,15.4,.55);molding(gallery,gold,x,y,.75,14.8,14.8);box(gallery,keep(new T.MeshStandardMaterial({map:print,roughness:.95})),x,y,.78,14.2,14.2,.04);
 }
 // Paneled record cabinet, inset doors, brass pulls and a reading bench.
 box(gallery,darkWood,0,-6.4,4.1,43,11.3,6.9);rounded(gallery,45,8,.55,.18,walnut,0,-.7,4.1);
 for(const x of [-14,0,14]){box(gallery,walnut,x,-6.3,7.65,13.5,10.5,.55);molding(gallery,oak,x,-6.3,7.97,11.7,8.7);rod(gallery,gold,[x-1,-2.8,8.3],[x+1,-2.8,8.3],.10);for(const dx of [-1,1])rod(gallery,gold,[x+dx,-2.8,7.93],[x+dx,-2.8,8.3],.085)}
 for(const x of [-19,19])for(const z of [1.5,6.5])box(gallery,walnut,x,-12.45,z,1.1,2,1.1);
 for(let i=0;i<4;i++){const book=box(gallery,bindings[i],-12+i*.1,.1+i*.55,4.5,7-i*.3,.45,4.3);book.rotation.y=(i-2)*.06;box(gallery,cream,-12+i*.1,.18+i*.55,6.64,6.5-i*.3,.25,.05)}
 const invitation=label('CHESS FOR EVERYONE','Take a seat. Find your next game.',768,256);box(gallery,walnut,9,1.8,4.8,13,4.4,.4);box(gallery,keep(new T.MeshStandardMaterial({map:invitation,roughness:.85})),9,1.8,5.04,12.5,4.0,.06);
 const bench=new T.Group();bench.position.set(-39,0,6);gallery.add(bench);rounded(bench,22,8,1.3,.7,leather,0,-6,0);box(bench,walnut,0,-7.2,0,23,.7,8.5);
 for(const x of [-9,9])for(const z of [-2.8,2.8])rod(bench,walnut,[x,floor+.1,z],[x,-7.4,z],.34);
 for(const x of [-9,9])rod(bench,walnut,[x,-7, -3.2],[x,1,-3.2],.32);rounded(bench,21,1,5.3,.35,leather,0,-4.4,-3.2);
 // A slim entrance console, coat hooks and umbrella stand, outside all paths.
 const entry=wallGroup(43);rounded(entry,21,6,.7,.3,walnut,0,-.8,3.5);
 for(const x of [-8.8,8.8])for(const z of [1.2,5.4])rod(entry,walnut,[x,floor,z],[x,-1,z],.25);
 box(entry,walnut,0,17,1,21,2,.45);for(const x of [-8,-4,0,4,8]){rod(entry,gold,[x,17,1.3],[x,16.3,2.2],.11);sphere(entry,gold,x,16.3,2.2,.22,.22,.22)}
 lathe(entry,'umbrella pot',[[1.5,0],[1.8,.25],[1.9,6.8],[1.65,6.8],[1.45,.5]],iron,14,floor,3);
 for(let i=0;i<3;i++){rod(entry,iron,[13.2+i*.8,floor+.2,3],[12.6+i*1.1,floor+13+i*.6,3],.13);const hook=mesh(entry,geo('umbrella handle',()=>new T.TorusGeometry(.55,.13,8,20,Math.PI)),walnut,13.1+i*1.1,floor+13+i*.6,3);hook.rotation.z=.12}
 const registerMap=label('VISITORS BOOK','Welcome to the club',512,384);const register=mesh(entry,geo('guest book',()=>new T.BoxGeometry(5,.32,3.9)),keep(new T.MeshStandardMaterial({map:registerMap,roughness:.9})),1,.10,3.3);register.rotation.y=-.09;
 // Static surfaces are merged by material. Animation nodes retain transforms.
 function batch(group){group.updateWorldMatrix(true,true);const buckets=new Map(),inverse=group.matrixWorld.clone().invert();function visit(o){if(o.userData.dynamic||o.isInstancedMesh)return;if(o.isMesh&&!Array.isArray(o.material)){const clone=o.geometry.clone();const g=clone.index?clone.toNonIndexed():clone;if(g!==clone)clone.dispose();g.applyMatrix4(inverse.clone().multiply(o.matrixWorld));const key=o.material;if(!buckets.has(key))buckets.set(key,[]);buckets.get(key).push({o,g})}for(const c of o.children)visit(c)}for(const child of [...group.children])visit(child);for(const [m,items] of buckets){const merged=mergeGeometries(items.map(v=>v.g));if(merged){const o=new T.Mesh(own(merged),m);o.castShadow=o.receiveShadow=true;group.add(o);for(const v of items)v.o.removeFromParent()}for(const v of items)v.g.dispose()}}
 // Tables remain separate groups to receive the detailed real app chess sets.
 batch(root);
 return {root,tables:[mainTable,leftTable,rightTable],clocks,door,library,setTime,floor,update(t){animations.forEach(fn=>fn(t))},animationCount:animations.length,materials:{walnut,gold,cream},geometryCount:geometries.size};
}
