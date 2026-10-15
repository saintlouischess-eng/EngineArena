import * as T from './three.module.js';
import {GroundedSkybox} from './three-grounded.js';
import {HDRLoader} from './three-hdr.js';

// Photographic CC0 rooms (vendor/PolyHaven) around an original, fully 3D table.
// Board units represent 5.5 cm: floor is 74 cm below the playing surface.
const rooms={
 club:{color:0xc4ad95,edge:0x59402b,rotation:1.4,height:27,radius:220,width:18,depth:16,round:.8},
 hall:{color:0xa58673,edge:0x422819,rotation:.92,height:29,radius:280,width:20,depth:17,round:4},
 study:{color:0xffefdb,edge:0xbca58b,rotation:2.2,height:27,radius:220,width:19,depth:16,round:.25},
 studio:{color:0xd3c6b7,edge:0x20262a,rotation:-1.2,height:29,radius:270,width:20,depth:16,round:.5}
};
export function surroundings(scene,assets,own,mat,textures,renderer,changed){
 const groups=new Map(),loader=new T.TextureLoader(),hdr=new HDRLoader(),pmrem=new T.PMREMGenerator(renderer);
 let active=null,requested='',serial=0,disposed=false,waiting=Promise.resolve(true),enabled=true;
 const material=(color,roughness=.65,metalness=0)=>mat(new T.MeshStandardMaterial({color,roughness,metalness}));
 const brass=material(0xaf8c52,.36,.72),iron=material(0x24292c,.48,.7);
 function tex(source,repeat=1,color=false){const t=source.clone();t.wrapS=t.wrapT=T.RepeatWrapping;t.repeat.set(repeat,repeat);if(color)t.colorSpace=T.SRGBColorSpace;t.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());t.needsUpdate=true;textures.set(t,t);return t}
 const woodMaps={map:tex(assets.wood.color,1,true),normalMap:tex(assets.wood.normal),roughnessMap:tex(assets.wood.rough)};
 const leatherMaps={map:tex(assets.leather.color,2,true),normalMap:tex(assets.leather.normal,2),roughnessMap:tex(assets.leather.rough,2)};
 const leather=mat(new T.MeshPhysicalMaterial({...leatherMaps,color:0x85736b,roughness:.86,normalScale:new T.Vector2(.38,.38),clearcoat:.08}));
 const canvas=document.createElement('canvas');canvas.width=canvas.height=512;const cx=canvas.getContext('2d');cx.fillStyle='#29483b';cx.fillRect(0,0,512,512);
 for(let i=0;i<512;i+=2){cx.fillStyle=i%4?'#335242':'#254333';cx.fillRect(i,0,1,512);cx.fillStyle='#ffffff06';cx.fillRect(0,i,512,1)}
 const cloth=new T.CanvasTexture(canvas);textures.set(cloth,cloth);const felt=mat(new T.MeshStandardMaterial({map:tex(cloth,7,true),roughness:1,color:0xb4c4b7}));
 function box(g,w,h,d,x,y,z,m){const o=new T.Mesh(own(new T.BoxGeometry(w,h,d)),m);o.position.set(x,y,z);o.castShadow=o.receiveShadow=true;g.add(o);return o}
 function top(g,w,d,y,m,r=.4,thickness=.15){
  const s=new T.Shape(),x=w/2,z=d/2;s.moveTo(-x+r,-z);s.lineTo(x-r,-z);s.quadraticCurveTo(x,-z,x,-z+r);s.lineTo(x,z-r);s.quadraticCurveTo(x,z,x-r,z);s.lineTo(-x+r,z);s.quadraticCurveTo(-x,z,-x,z-r);s.lineTo(-x,-z+r);s.quadraticCurveTo(-x,-z,-x+r,-z);
  const geo=own(new T.ExtrudeGeometry(s,{depth:thickness,bevelEnabled:true,bevelThickness:.045,bevelSize:.045,bevelSegments:4,steps:1,curveSegments:24}));
  const p=geo.attributes.position,u=geo.attributes.uv;for(let i=0;i<p.count;i++)u.setXY(i,p.getX(i)/w+.5,p.getY(i)/d+.5);
  const mesh=new T.Mesh(geo,m);mesh.rotation.x=-Math.PI/2;mesh.position.y=y-thickness;mesh.castShadow=mesh.receiveShadow=true;g.add(mesh);return mesh;
 }
 function turnedLeg(g,x,z,m){
  const points=[[.34,0],[.4,.15],[.32,.35],[.25,1],[.32,2.8],[.43,4.2],[.37,5],[.3,5.5],[.3,7.8],[.43,8.2],[.43,9.8],[.48,10.2],[.48,11.7]].map(([r,y])=>new T.Vector2(r,y));
  const mesh=new T.Mesh(own(new T.LatheGeometry(points,32)),m);mesh.position.set(x,-13.4,z);mesh.castShadow=true;g.add(mesh);
 }
 function build(kind){
  const v=rooms[kind],g=new T.Group();g.name='Table '+kind;scene.add(g);
  const wood=mat(new T.MeshPhysicalMaterial({...woodMaps,color:v.color,roughness:.78,normalScale:new T.Vector2(.10,.10),clearcoat:kind==='hall'?.18:.08,clearcoatRoughness:.5}));
  wood.onBeforeCompile=shader=>{shader.fragmentShader=shader.fragmentShader.replace('#include <roughnessmap_fragment>','#include <roughnessmap_fragment>\nroughnessFactor = .48 + .42 * roughnessFactor;')};wood.customProgramCacheKey=()=> 'satin-table';
  const edge=mat(new T.MeshStandardMaterial({...woodMaps,color:v.edge,roughness:.73,normalScale:new T.Vector2(.2,.2)}));
  // Rounded joinery, a fine brass reveal and an inset surface, rather than a box.
  top(g,v.width,v.depth,-.52,edge,v.round,.55);top(g,v.width-.12,v.depth-.12,-.48,brass,Math.max(.1,v.round-.06),.035);
  top(g,v.width-.2,v.depth-.2,-.43,wood,Math.max(.1,v.round-.1),.10);
  const inset=top(g,v.width-1.25,v.depth-1.25,-.375,wood,Math.max(.15,v.round-.625),.035);
  for(const z of [-1,1])box(g,v.width-2.2,1.5,.28,0,-1.6,z*(v.depth/2-1),edge);
  for(const x of [-1,1])box(g,.28,1.5,v.depth-2.2,x*(v.width/2-1),-1.6,0,edge);
  if(kind==='studio'){
   for(const x of [-7.8,7.8]){box(g,.3,11.8,.55,x,-7,0,iron);box(g,1,.5,12,x,-13.1,0,iron);box(g,.5,.3,12,x,-1.4,0,iron)}
   box(g,15.6,.25,.35,0,-10,0,iron);
  }else if(kind==='study'){
   for(const x of [-7.2,7.2])for(const z of [-5.7,5.7])box(g,.8,11.7,.8,x,-7.5,z,wood);
   for(const x of [-7.2,7.2])box(g,.5,.5,12,x,-10,0,wood);
  }else for(const x of [-1,1])for(const z of [-1,1])turnedLeg(g,x*(v.width/2-2),z*(v.depth/2-2),edge);
  groups.set(kind,{g,inset,wood});return groups.get(kind);
 }
 function label(text){const c=document.createElement('canvas');c.width=1536;c.height=192;const x=c.getContext('2d');x.fillStyle='#192322';x.fillRect(0,0,c.width,c.height);x.strokeStyle='#a68b59';x.lineWidth=3;x.strokeRect(14,14,c.width-28,c.height-28);x.fillStyle='#eddfc3';x.textAlign='center';x.textBaseline='middle';let size=82;x.font=`500 ${size}px Georgia`;while(x.measureText(text).width>c.width-90&&size>24){size-=2;x.font=`500 ${size}px Georgia`}x.fillText(text,c.width/2,c.height/2+3);return c}
 const plates=new T.Group(),plaque=new T.Group();scene.add(plates,plaque);const nameTextures=[];
 function nameplate(g,z,text,width){
  top(g,width+.1,.98,-.31,brass,.07,.10);const t=new T.CanvasTexture(label(text));t.colorSpace=T.SRGBColorSpace;t.anisotropy=8;textures.set(t,t);
  const face=new T.Mesh(own(new T.PlaneGeometry(width,.88)),mat(new T.MeshStandardMaterial({map:t,roughness:.72})));face.rotation.x=-Math.PI/2;face.position.y=-.258;g.add(face);g.position.z=z;if(z<0)g.rotation.y=Math.PI;return t;
 }
 for(const z of [5.75,-5.75]){const g=new T.Group();plates.add(g);nameTextures.push(nameplate(g,z,'ENGINE ARENA',7.2))}
 nameplate(plaque,4.94,'ENGINE ARENA',2.9);plaque.scale.z=.5;plaque.position.z=4.94;
 let lastNames='';
 function disposeRoom(r){if(!r)return;scene.remove(r.sky);r.sky.geometry.dispose();r.sky.material.dispose();r.pano.dispose();r.env.dispose()}
 function loadRoom(kind,quality){
  const max=renderer.capabilities.maxTextureSize,size=Math.min(max,{low:2048,balanced:4096,high:8192}[quality]),resolution=size>=8192?8192:size>=4096?4096:2048,key=kind+resolution;
  if(requested===key)return;requested=key;const revision=++serial;renderer.domElement.dataset.roomReady='loading';
  waiting=(async()=>{
   // All promises settle, so successful textures are also released if one fails.
   const loaded=await Promise.allSettled([loader.loadAsync(`/scene-assets/${kind}-${resolution}.jpg`),hdr.loadAsync(`/scene-assets/${kind}-light.hdr`)]);
   const failure=loaded.find(r=>r.status==='rejected');
   if(failure||disposed||revision!==serial){for(const r of loaded)if(r.status==='fulfilled')r.value.dispose();if(failure&&!disposed&&revision===serial){renderer.domElement.dataset.roomReady='error';changed(new Error('Room assets could not load.'));}return false}
   const [pano,light]=loaded.map(r=>r.value);let next=null,env=null;
   try{
    pano.colorSpace=T.SRGBColorSpace;pano.anisotropy=4;light.mapping=T.EquirectangularReflectionMapping;
    env=pmrem.fromEquirectangular(light);const v=rooms[kind],sky=new GroundedSkybox(pano,v.height,v.radius,96);
    sky.position.y=v.height-13.5;sky.rotation.y=v.rotation;sky.material.toneMapped=false;sky.name='Photographic room';
    next={sky,pano,env,kind};scene.add(sky);sky.visible=enabled;if(enabled){scene.environment=env.texture;scene.environmentRotation.y=v.rotation}disposeRoom(active);active=next;
    renderer.domElement.dataset.roomReady=key;renderer.domElement.dataset.roomTexture=String(resolution);renderer.shadowMap.needsUpdate=true;changed();return true;
   }catch(e){if(next)disposeRoom(next);else {pano.dispose();env?.dispose()}renderer.domElement.dataset.roomReady='error';changed(e);return false}finally{light.dispose()}
  })();
 }
 return {
  update(p,data){if(disposed)return;enabled=p.environment!=='live-club';if(enabled)loadRoom(p.environment,p.quality);if(active){active.sky.visible=enabled;if(enabled){active.sky.rotation.y=rooms[active.kind].rotation+p.roomRotation*Math.PI/180;scene.environmentRotation.y=active.sky.rotation.y;scene.environment=active.env.texture;scene.environmentIntensity=.55}}const selected=enabled?(groups.get(p.environment)||build(p.environment)):null;for(const {g} of groups.values())g.visible=enabled&&g===selected.g;if(selected)selected.inset.material=p.surface==='wood'?selected.wood:p.surface==='felt'?felt:leather;plates.visible=p.plates;plaque.visible=p.plaque;const margin=p.board==='drueke'?.32:0;plates.children.forEach((g,i)=>g.position.z=(i?-1:1)*(5.75+margin));plaque.position.z=4.94+margin;
   const names=[data.white||'ENGINE ARENA',data.black||'ENGINE ARENA'],key=JSON.stringify(names);if(lastNames!==key){lastNames=key;nameTextures.forEach((t,i)=>{const c=label(names[i]);t.image.getContext('2d').drawImage(c,0,0);t.needsUpdate=true});renderer.domElement.dataset.nameplates=key}
  },ready:()=>waiting,dispose(){disposed=true;serial++;disposeRoom(active);pmrem.dispose()},groups
 };
}
