// Original Blender sculptures, baked grain and physically based lighting. Offline.
import * as T from './three.module.js';
import {GLTFLoader} from './three-gltf.js';
import {RoomEnvironment} from './three-room.js';
import {crownGeometry,crownTexture} from './board3d-crowns.js';
let assets=null,pending=null;
export function load(){return pending??=(async()=>{try{
 const loader=new T.TextureLoader();
 const [model,maple,walnut]=await Promise.all([new GLTFLoader().loadAsync('/assets/staunton1849.glb'),loader.loadAsync('/textures/maple.png'),loader.loadAsync('/textures/walnut.png')]);
 const pieces={};model.scene.traverse(o=>{if(o.isMesh&&'pnbrqk'.includes(o.name)&&o.name.length===1)pieces[o.name]=o});
 if(Object.keys(pieces).length!==6)throw Error('Incomplete Staunton set');
 assets={pieces,maple,walnut,stamps:{n:crownGeometry(pieces.n,'n'),r:crownGeometry(pieces.r,'r')}};
 }catch(e){pending=null;throw e}})()}
export function create(canvas,onLost,settings){
 if(!assets)throw Error('Staunton set is not loaded');
 const renderer=new T.WebGLRenderer({canvas,antialias:true,alpha:false,powerPreference:'low-power'});
 renderer.setPixelRatio(Math.min(devicePixelRatio||1,2));renderer.outputColorSpace=T.SRGBColorSpace;renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05;
 renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFShadowMap;renderer.shadowMap.autoUpdate=false;
 const scene=new T.Scene(),camera=new T.PerspectiveCamera(43,1,.1,80),owned=new Set(),materials=new Set(),textures=new Map();
 const own=g=>(owned.add(g),g),mat=m=>(materials.add(m),m);
 const texture=t=>{if(!textures.has(t)){const c=t.clone();c.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());c.needsUpdate=true;textures.set(t,c)}return textures.get(t)};
 const pmrem=new T.PMREMGenerator(renderer),room=new RoomEnvironment(),env=pmrem.fromScene(room,.04,.1,100);scene.environment=env.texture;scene.environmentIntensity=.65;room.dispose();pmrem.dispose();
 const hemi=new T.HemisphereLight(0xe4eeff,0x806950,1.25);scene.add(hemi);
 const key=new T.DirectionalLight(0xfff1dc,2.4);key.position.set(-4,9,5);key.castShadow=true;key.shadow.mapSize.set(2048,2048);Object.assign(key.shadow.camera,{left:-6,right:6,top:6,bottom:-6,near:.1,far:24});key.shadow.bias=-.00025;key.shadow.normalBias=.015;key.shadow.radius=2;scene.add(key);
 const fill=new T.DirectionalLight(0xe0eaff,1.3);fill.position.set(5,5,-4);scene.add(fill);
 const gold=mat(new T.MeshStandardMaterial({color:0xb49256,metalness:.45,roughness:.32}));
 const boardMaterial=(source,color)=>{const map=texture(source);map.colorSpace=T.SRGBColorSpace;return mat(new T.MeshPhysicalMaterial({map,color,roughness:.36,clearcoat:.18,clearcoatRoughness:.3}))};
 const pale=boardMaterial(assets.maple,0xe8d6b3),dark=boardMaterial(assets.walnut,0x8e7259),frameMat=boardMaterial(assets.walnut,0x453426);
 function block(w,h,d,m,y){const mesh=new T.Mesh(own(new T.BoxGeometry(w,h,d)),m);mesh.position.y=y;mesh.receiveShadow=true;scene.add(mesh);return mesh}
 const shape=new T.Shape(),s=4.55,r=.10;shape.moveTo(-s+r,-s);shape.lineTo(s-r,-s);shape.quadraticCurveTo(s,-s,s,-s+r);shape.lineTo(s,s-r);shape.quadraticCurveTo(s,s,s-r,s);shape.lineTo(-s+r,s);shape.quadraticCurveTo(-s,s,-s,s-r);shape.lineTo(-s,-s+r);shape.quadraticCurveTo(-s,-s,-s+r,-s);
 const frame=new T.Mesh(own(new T.ExtrudeGeometry(shape,{depth:.20,bevelEnabled:true,bevelThickness:.05,bevelSize:.04,bevelSegments:3,steps:1,curveSegments:12})),frameMat);frame.rotation.x=-Math.PI/2;frame.position.y=-.27;frame.receiveShadow=true;frame.castShadow=true;scene.add(frame);
 block(8.18,.02,8.18,gold,-.042);block(8.09,.022,8.09,frameMat,-.025);
 const squareGeo=own(new T.PlaneGeometry(1,1));
 for(let rank=0;rank<8;rank++)for(let file=0;file<8;file++){const mesh=new T.Mesh(squareGeo,(rank+file)%2?dark:pale);mesh.rotation.x=-Math.PI/2;mesh.position.set(file-3.5,0,rank-3.5);mesh.receiveShadow=true;scene.add(mesh)}
 // One atlas and one draw call for lettering on the frame. Scene depth must
 // hide the ink behind pieces; a screen overlay cannot respect that depth.
 const letters=document.createElement('canvas');letters.width=1024;letters.height=256;
 const inkContext=letters.getContext('2d');inkContext.font='bold 96px Georgia, serif';inkContext.textAlign='center';inkContext.textBaseline='middle';inkContext.fillStyle='#f4dfb9';
 for(let i=0;i<16;i++)inkContext.fillText('abcdefgh87654321'[i],(i%8+.5)*128,(Math.floor(i/8)+.5)*128+3);
 const letterTexture=new T.CanvasTexture(letters);letterTexture.colorSpace=T.SRGBColorSpace;letterTexture.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());textures.set(letterTexture,letterTexture);
 const letterGeo=own(new T.BufferGeometry()),letterPositions=new Float32Array(16*12),letterUVs=[],letterIndices=[];
 for(let i=0;i<16;i++){const u=i%8/8,v=1-Math.floor(i/8)/2;letterUVs.push(u,v-.5,u+.125,v-.5,u+.125,v,u,v);const j=i*4;letterIndices.push(j,j+1,j+2,j,j+2,j+3)}
 letterGeo.setAttribute('position',new T.BufferAttribute(letterPositions,3));letterGeo.setAttribute('uv',new T.Float32BufferAttribute(letterUVs,2));letterGeo.setIndex(letterIndices);
 const lettering=new T.Mesh(letterGeo,mat(new T.MeshBasicMaterial({map:letterTexture,transparent:true,alphaTest:.02,depthTest:true,depthWrite:false,toneMapped:false})));
 lettering.name='Board coordinates';lettering.frustumCulled=false;scene.add(lettering);canvas.dataset.coordinateCount='16';let letterView='';
 function placeLetters(){
  const front=camera.position.z>=0?1:-1,side=camera.position.x<=0?-1:1,orbit=Math.atan2(camera.position.x,camera.position.z),key=front+','+side+','+orbit;
  if(key===letterView)return;letterView=key;
  // Keep every glyph readable from the camera, including ranks on side rails.
  // Rotation remains within the board plane, so lettering still respects depth.
  const right=[Math.cos(orbit),-Math.sin(orbit)],up=[-Math.sin(orbit),-Math.cos(orbit)];
  for(let i=0;i<16;i++){
   const file=i<8,x=file?i-3.5:side*4.3,z=file?front*4.3:i-8-3.5;
   [[-1,-1],[1,-1],[1,1],[-1,1]].forEach(([u,v],corner)=>{const at=i*12+corner*3;letterPositions[at]=x+.175*(u*right[0]+v*up[0]);letterPositions[at+1]=-.018;letterPositions[at+2]=z+.175*(u*right[1]+v*up[1])});
  }
  letterGeo.attributes.position.needsUpdate=true;
 }
 const highlight=mat(new T.MeshBasicMaterial({color:0xc6b96e,opacity:.26,transparent:true,depthWrite:false})),marks=[0,1].map(()=>{const m=new T.Mesh(squareGeo,highlight);m.rotation.x=-Math.PI/2;m.position.y=.003;scene.add(m);return m});
 const groundMat=mat(new T.MeshStandardMaterial({color:0x29343e,roughness:.95})),ground=new T.Mesh(own(new T.PlaneGeometry(200,200)),groundMat);ground.rotation.x=-Math.PI/2;ground.position.y=-.34;ground.receiveShadow=true;scene.add(ground);
 const templates={};
 for(const type of 'pnbrqk'){
  const source=assets.pieces[type],geometry=own(source.geometry.clone());
  for(const white of [true,false]){
   const m=mat(source.material.clone());for(const name of ['map','normalMap','roughnessMap','metalnessMap','aoMap','clearcoatMap','clearcoatNormalMap','clearcoatRoughnessMap'])if(m[name])m[name]=texture(m[name]);
   m.color.set(white?0xffdfb0:0x302b26);m.roughness=white?.98:.88;m.clearcoat=.18;m.clearcoatRoughness=.34;m.normalScale.set(.35,.35);m.envMapIntensity=1;
   const mesh=new T.Mesh(geometry,m);mesh.rotation.copy(source.rotation);mesh.scale.copy(source.scale);mesh.castShadow=true;mesh.receiveShadow=true;templates[white?type.toUpperCase():type]=mesh;
  }
 }
 const ink=crownTexture();textures.set(ink,ink);
 const stampMaterial=mat(new T.MeshStandardMaterial({map:ink,roughness:.72,transparent:true,alphaTest:.05,depthWrite:false,polygonOffset:true,polygonOffsetFactor:-2,polygonOffsetUnits:-2}));
 const stamps=Object.fromEntries(Object.entries(assets.stamps).map(([type,g])=>[type,own(g.clone())]));
 const active=new T.Group();scene.add(active);let position='',disposed=false,lost=false,frames=0;
 const lostHandler=e=>{e.preventDefault();if(!disposed){lost=true;onLost()}};canvas.addEventListener('webglcontextlost',lostHandler);
 function render(fen,flip,prefs,light=false,last='',crownSquares=[]){
  if(disposed||lost)return;const rect=canvas.getBoundingClientRect();if(rect.width<2||rect.height<2)return;
  renderer.setSize(Math.round(rect.width),Math.round(rect.height),false);camera.aspect=rect.width/rect.height;camera.updateProjectionMatrix();
  const p=settings(prefs),a=p.angle*Math.PI/180,o=(p.orbit+(flip?180:0))*Math.PI/180,d=14.3/p.zoom*Math.max(1,1/camera.aspect);camera.position.set(Math.sin(o)*Math.cos(a)*d,Math.sin(a)*d,Math.cos(o)*Math.cos(a)*d);camera.lookAt(0,.25,0);camera.setViewOffset(rect.width,rect.height,0,p.lift*rect.height,rect.width,rect.height);camera.updateMatrixWorld();
  const placement=fen.split(' ')[0],marked=new Set(crownSquares),identity=placement+'|'+[...marked].sort().join(',');if(position!==identity){active.clear();let rank=0,file=0,count=0;for(const c of placement){if(c==='/'){rank++;file=0}else if(/[1-8]/.test(c))file+=Number(c);else{if(templates[c]){const m=templates[c].clone();m.position.set(file-3.5,.008,rank-3.5);if(c===c.toLowerCase())m.rotateY(Math.PI);const type=c.toLowerCase();if(stamps[type]&&marked.has('abcdefgh'[file]+(8-rank))){const stamp=new T.Mesh(stamps[type],stampMaterial);stamp.name='Kingside crown';m.add(stamp);count++}active.add(m)}file++}}position=identity;canvas.dataset.crownCount=String(count);renderer.shadowMap.needsUpdate=true}
  marks.forEach((m,i)=>{const sq=last.slice(i*2,i*2+2);m.visible=/^[a-h][1-8]$/.test(sq);if(m.visible){m.position.x=sq.charCodeAt(0)-97-3.5;m.position.z=8-Number(sq[1])-3.5}});
  placeLetters();scene.background=new T.Color(light?0xe0e2e0:0x202933);groundMat.color.set(light?0xc2c1bc:0x29343e);renderer.render(scene,camera);canvas.dataset.frames=String(++frames);
  const label=(text,x,z)=>{const v=new T.Vector3(x,-.018,z).project(camera);return {text,x:(v.x+1)*rect.width/2,y:(1-v.y)*rect.height/2}};
  return [...Array.from({length:8},(_,i)=>label('abcdefgh'[i],i-3.5,camera.position.z>=0?4.3:-4.3)),...Array.from({length:8},(_,i)=>label(String(8-i),camera.position.x<=0?-4.3:4.3,i-3.5))];
 }
 return {render,dispose(){if(disposed)return;disposed=true;canvas.removeEventListener('webglcontextlost',lostHandler);for(const g of owned)g.dispose();for(const m of materials)m.dispose();for(const t of textures.values())t.dispose();key.shadow.dispose();env.dispose();renderer.dispose();renderer.forceContextLoss()}};
}
