// Original Blender sculptures, baked grain and physically based lighting. Offline.
import * as T from './three.module.js';
import {GLTFLoader} from './three-gltf.js';
import {RoomEnvironment} from './three-room.js';
import {crownGeometry,crownTexture} from './board3d-crowns.js';
import {liveClub} from './board3d-club.js';
import {surroundings} from './board3d-environments.js';
import {boardCollection} from './board3d-boards.js';
import {photograph} from './board3d-photo.js';
import {drawingBudget,resizeDrawingBuffer,GPUFrameGate} from './board3d-budget.js';
let assets=null,pending=null;const sets=new Map(),setLoads=new Map();
function loadBase(){return pending??=(async()=>{try{
 const loader=new T.TextureLoader();
 const scan=async kind=>Object.fromEntries(await Promise.all(['color','normal','rough'].map(async key=>[key,await loader.loadAsync(`/scene-assets/${kind}-${key}.jpg`)])));
 const [model,maple,walnut,logo,wood,leather]=await Promise.all([new GLTFLoader().loadAsync('/assets/staunton1849.glb'),loader.loadAsync('/textures/maple.png'),loader.loadAsync('/textures/walnut.png'),loader.loadAsync('/assets/engine-arena.svg'),scan('wood'),scan('leather')]);
 const pieces={};model.scene.traverse(o=>{if(o.isMesh&&'pnbrqk'.includes(o.name)&&o.name.length===1)pieces[o.name]=o});
 if(Object.keys(pieces).length!==6)throw Error('Incomplete Staunton set');
 const logoCanvas=document.createElement('canvas');logoCanvas.width=logoCanvas.height=512;logoCanvas.getContext('2d').drawImage(logo.image,0,0,512,512);logo.dispose();
 assets={pieces,maple,walnut,wood,leather,logo:new T.CanvasTexture(logoCanvas),stamps:{r:crownGeometry(pieces.r,'r'),n:crownGeometry(pieces.n,'n')}};
 sets.set('staunton1849',pieces);
 }catch(e){pending=null;throw e}})()}
export async function load(set='staunton1849'){
 await loadBase();if(sets.has(set))return;if(set!=='tal1962')throw Error('Unknown 3D piece set');
 if(!setLoads.has(set))setLoads.set(set,(async()=>{try{const model=await new GLTFLoader().loadAsync('/assets/tal1962.glb'),pieces={};model.scene.traverse(o=>{if(o.name.length===1&&'pnbrqk'.includes(o.name))pieces[o.name]=o});if(Object.keys(pieces).length!==6)throw Error('Incomplete Tal 1962 set');sets.set(set,pieces)}catch(error){setLoads.delete(set);throw error}})());
 await setLoads.get(set);
}
export function create(canvas,onLost,settings,knightRotation,knightMode,onReady,set='staunton1849'){
 if(!assets)throw Error('Staunton set is not loaded');
 const pieces=sets.get(set);if(!pieces)throw Error('Selected piece set is not loaded');canvas.dataset.pieceSet=set;
 const renderer=new T.WebGLRenderer({canvas,antialias:true,alpha:false,powerPreference:'low-power'});
 const frameGate=new GPUFrameGate(renderer.getContext()),maxBuffer=Math.min(renderer.capabilities.maxTextureSize,renderer.getContext().getParameter(renderer.getContext().MAX_RENDERBUFFER_SIZE));let deferred=false,photoBusy=false,photoQueue=Promise.resolve();
 renderer.outputColorSpace=T.SRGBColorSpace;renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=.98;
 renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFShadowMap;renderer.shadowMap.autoUpdate=false;
 renderer.info.autoReset=false;
 const scene=new T.Scene(),camera=new T.PerspectiveCamera(43,1,.1,400),owned=new Set(),materials=new Set(),textures=new Map();
 const own=g=>(owned.add(g),g),mat=m=>(materials.add(m),m);
 const texture=t=>{if(!textures.has(t)){const c=t.clone();c.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());c.needsUpdate=true;textures.set(t,c)}return textures.get(t)};
 // Broad, blurred environment reflections supply shape without bright pinpoints.
 // A restrained key/fill ratio leaves the carved contours legible on both colors.
 const pmrem=new T.PMREMGenerator(renderer),room=new RoomEnvironment(),env=pmrem.fromScene(room,.16,.1,100);scene.environment=env.texture;scene.environmentIntensity=.55;room.dispose();pmrem.dispose();
 const hemi=new T.HemisphereLight(0xe4eeff,0x806950,.82);scene.add(hemi);
 const key=new T.DirectionalLight(0xfff3e3,1.85);key.position.set(-4,9,5);key.castShadow=true;key.shadow.mapSize.set(2048,2048);Object.assign(key.shadow.camera,{left:-6,right:6,top:6,bottom:-6,near:.1,far:24});key.shadow.bias=-.00025;key.shadow.normalBias=.015;key.shadow.radius=3;scene.add(key);
 const fill=new T.DirectionalLight(0xe7eeff,.72);fill.position.set(5,5,-4);scene.add(fill);
 const gold=mat(new T.MeshStandardMaterial({color:0xb49256,metalness:.35,roughness:.55}));
 // Satin board finish: the grain and square contrast should survive grazing views.
 const boardMaterial=(source,color)=>{const map=texture(source);map.colorSpace=T.SRGBColorSpace;return mat(new T.MeshPhysicalMaterial({map,color,roughness:.78,specularIntensity:.32,clearcoat:0,envMapIntensity:.65}))};
 const pale=boardMaterial(assets.maple,0xe8d6b3),dark=boardMaterial(assets.walnut,0x8e7259),frameMat=boardMaterial(assets.walnut,0x604932);
 const originalBoard=new T.Group();scene.add(originalBoard);
 function block(w,h,d,m,y){const mesh=new T.Mesh(own(new T.BoxGeometry(w,h,d)),m);mesh.position.y=y;mesh.receiveShadow=true;originalBoard.add(mesh);return mesh}
 const shape=new T.Shape(),s=4.55,r=.10;shape.moveTo(-s+r,-s);shape.lineTo(s-r,-s);shape.quadraticCurveTo(s,-s,s,-s+r);shape.lineTo(s,s-r);shape.quadraticCurveTo(s,s,s-r,s);shape.lineTo(-s+r,s);shape.quadraticCurveTo(-s,s,-s,s-r);shape.lineTo(-s,-s+r);shape.quadraticCurveTo(-s,-s,-s+r,-s);
 const frame=new T.Mesh(own(new T.ExtrudeGeometry(shape,{depth:.20,bevelEnabled:true,bevelThickness:.05,bevelSize:.04,bevelSegments:3,steps:1,curveSegments:12})),frameMat);frame.rotation.x=-Math.PI/2;frame.position.y=-.27;frame.receiveShadow=true;frame.castShadow=true;originalBoard.add(frame);
 block(8.18,.02,8.18,gold,-.042);block(8.09,.022,8.09,frameMat,-.025);
 const squareGeo=own(new T.PlaneGeometry(1,1));
 for(let rank=0;rank<8;rank++)for(let file=0;file<8;file++){const mesh=new T.Mesh(squareGeo,(rank+file)%2?dark:pale);mesh.rotation.x=-Math.PI/2;mesh.position.set(file-3.5,0,rank-3.5);mesh.receiveShadow=true;originalBoard.add(mesh)}
 const boards=boardCollection(scene,assets,own,mat,textures,renderer,originalBoard);let boardSpec={letter:4.3,inkY:-.018,letterSize:.35};
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
  const front=camera.position.z>=0?1:-1,side=camera.position.x<=0?-1:1,orbit=Math.atan2(camera.position.x,camera.position.z),key=[front,side,orbit,boardSpec.letter,boardSpec.inkY].join(',');
  if(key===letterView)return;letterView=key;
  // Keep every glyph readable from the camera, including ranks on side rails.
  // Rotation remains within the board plane, so lettering still respects depth.
  const right=[Math.cos(orbit),-Math.sin(orbit)],up=[-Math.sin(orbit),-Math.cos(orbit)];
  for(let i=0;i<16;i++){
   const file=i<8,x=file?i-3.5:side*boardSpec.letter,z=file?front*boardSpec.letter:i-8-3.5;
   [[-1,-1],[1,-1],[1,1],[-1,1]].forEach(([u,v],corner)=>{const at=i*12+corner*3;letterPositions[at]=x+boardSpec.letterSize/2*(u*right[0]+v*up[0]);letterPositions[at+1]=boardSpec.inkY;letterPositions[at+2]=z+boardSpec.letterSize/2*(u*right[1]+v*up[1]);letterPositions[at+1]+=(boardSpec.slope||0)*(Math.max(Math.abs(letterPositions[at]),Math.abs(letterPositions[at+2]))-boardSpec.letter)});
  }
  letterGeo.attributes.position.needsUpdate=true;
 }
 const highlight=mat(new T.MeshBasicMaterial({color:0xf5d447,opacity:.38,transparent:true,depthWrite:false,toneMapped:false}));
 const outline=mat(new T.MeshBasicMaterial({color:0xf4cf40,opacity:.68,transparent:true,depthWrite:false,toneMapped:false}));
 const ring=new T.Shape();ring.moveTo(-.49,-.49);ring.lineTo(.49,-.49);ring.lineTo(.49,.49);ring.lineTo(-.49,.49);ring.closePath();const hole=new T.Path();hole.moveTo(-.471,-.471);hole.lineTo(-.471,.471);hole.lineTo(.471,.471);hole.lineTo(.471,-.471);hole.closePath();ring.holes.push(hole);
 const ringGeo=own(new T.ShapeGeometry(ring)),marks=[0,1].map(()=>{const m=new T.Mesh(squareGeo,highlight);m.rotation.x=-Math.PI/2;m.position.y=.006;const edge=new T.Mesh(ringGeo,outline);edge.position.z=.001;m.add(edge);scene.add(m);return m});
 const environment=surroundings(scene,assets,own,mat,textures,renderer,error=>{if(disposed)return;if(onReady)onReady(error);else if(!error&&lastArgs)render(...lastArgs)});
 const intentionMat=mat(new T.MeshBasicMaterial({color:0x35b9f3,transparent:true,opacity:.88,depthWrite:false,toneMapped:false}));
 const intentionShaft=new T.Mesh(own(new T.CylinderGeometry(.055,.055,1,8)),intentionMat),intentionTip=new T.Mesh(own(new T.ConeGeometry(.21,.4,12)),intentionMat);
 scene.add(intentionShaft,intentionTip);intentionShaft.visible=intentionTip.visible=false;
 let life=null;
 const pieceGeometry=new Map(),pieceMaterials=new Map(),sourceMaterials=new Map();
 for(const source of Object.values(pieces))source.traverse(o=>{if(o.isMesh)for(const m of Array.isArray(o.material)?o.material:[o.material])sourceMaterials.set(m.name,m)});
 function pieceMaterial(source,white,selected){
  if(selected==='tal1962'&&!white){const alternate={'Tal boxwood':'Tal ebony','Tal ebony':'Tal boxwood'}[source.name];if(alternate)source=sourceMaterials.get(alternate)}
  const id=source.uuid+':'+white;if(pieceMaterials.has(id))return pieceMaterials.get(id);
  const m=mat(source.clone());for(const name of ['map','normalMap','roughnessMap','metalnessMap','aoMap','clearcoatMap','clearcoatNormalMap','clearcoatRoughnessMap'])if(m[name])m[name]=texture(m[name]);
  if(selected==='staunton1849'){
   // Preserve the established polished Staunton finish.
   m.roughnessMap=null;m.color.set(white?0xffdfb0:0x171411);m.roughness=.28;m.specularIntensity=.85;m.clearcoat=white?.30:.26;m.clearcoatRoughness=white?.28:.30;m.normalScale.set(.35,.35);m.envMapIntensity=1.25;
  }else if(source.name!=='Dark green felt underside'){m.specularIntensity=.85;m.envMapIntensity=1.15}
  pieceMaterials.set(id,m);return m;
 }
 function makeTemplates(sources,selected){const result={};for(const type of 'pnbrqk'){
  const source=sources[type];
  for(const white of [true,false]){
   const mesh=source.clone(true);mesh.traverse(o=>{if(!o.isMesh)return;if(!pieceGeometry.has(o.geometry))pieceGeometry.set(o.geometry,own(o.geometry.clone()));o.geometry=pieceGeometry.get(o.geometry);o.material=Array.isArray(o.material)?o.material.map(m=>pieceMaterial(m,white,selected)):pieceMaterial(o.material,white,selected);o.castShadow=true;o.receiveShadow=true});result[white?type.toUpperCase():type]=mesh;
  }
 }return result}
 const templates=makeTemplates(pieces,set);let clubTemplates=null;
 const ink=crownTexture();textures.set(ink,ink);
 const stampMaterial=mat(new T.MeshStandardMaterial({map:ink,roughness:.72,transparent:true,alphaTest:.05,depthWrite:false,polygonOffset:true,polygonOffsetFactor:-2,polygonOffsetUnits:-2}));
 const stamps=set==='staunton1849'?Object.fromEntries(Object.entries(assets.stamps).map(([type,g])=>[type,own(g.clone())])):{};
 const active=new T.Group(),trayPieces=new T.Group(),trays=new T.Group();scene.add(active,trayPieces,trays);
 const trayMat=mat(new T.MeshStandardMaterial({color:0x263c34,roughness:.95}));
 for(const x of [-6.1,6.1]){const tray=new T.Mesh(own(new T.BoxGeometry(1.7,.12,6.5)),frameMat);tray.position.set(x,-.24,0);tray.receiveShadow=true;trays.add(tray);const inset=new T.Mesh(own(new T.BoxGeometry(1.52,.01,6.3)),trayMat);inset.position.set(x,-.171,0);trays.add(inset)}
 let position='',disposed=false,lost=false,frames=0,previousFen='',previousGame='',meshMap={},tweens=[],started=0,duration=0,lastCaptures='',quality='',lastArgs=null,shadowState='';
 const finishMotion=()=>{for(const t of tweens){if(t.ghost)active.remove(t.mesh);else{t.mesh.position.copy(t.target);t.mesh.scale.copy(t.scale)}if(t.reveal)t.reveal.visible=true}tweens=[]};
 function lighting(p){
  const palettes={daylight:[0xf2f7ff,0xdce8ff,0xd9e7ef,1.7,.82,.88],evening:[0xffd5a1,0xd7e5ff,0xf1d8b4,1.65,.7,.78],tournament:[0xfff3e3,0xe7eeff,0xe4eeff,1.85,.72,.82]},v=palettes[p.lighting];
  key.color.set(v[0]);fill.color.set(v[1]);hemi.color.set(v[2]);const warmth=new T.Color(p.warmth>0?0xffd6a4:0xc9ddff);key.color.lerp(warmth,Math.abs(p.warmth)*.35);key.intensity=v[3];fill.intensity=v[4];hemi.intensity=v[5];renderer.toneMappingExposure=.98*p.brightness;
  if(quality!==p.quality){quality=p.quality;const size=quality==='high'?2048:1024;key.shadow.mapSize.set(size,size);key.shadow.map?.dispose();key.shadow.map=null;renderer.shadowMap.needsUpdate=true}
 }
 function captures(values,p){
  trays.visible=trayPieces.visible=p.trays;const key=JSON.stringify(values);if(key===lastCaptures)return;lastCaptures=key;trayPieces.clear();const counts={white:0,black:0};
  for(const c of (values||[])){if(!templates[c])continue;const white=c===c.toUpperCase(),side=white?'white':'black',n=counts[side]++,total=values.filter(v=>(v===v.toUpperCase())===white).length,spacing=Math.min(.8,5.6/Math.max(1,Math.ceil(total/2)-1)),scale=Math.min(.68,spacing*.88);const mesh=templates[c].clone();mesh.scale.multiplyScalar(scale);mesh.position.set((white?-6.1:6.1)+(n%2? .39:-.39),-.16,-2.8+Math.floor(n/2)*spacing);trayPieces.add(mesh)}
  canvas.dataset.capturedCount=String(trayPieces.children.length);renderer.shadowMap.needsUpdate=true;
 }
 const lostHandler=e=>{e.preventDefault();if(!disposed){lost=true;onLost()}};canvas.addEventListener('webglcontextlost',lostHandler);
 function render(fen,flip,prefs,light=false,last='',crownSquares=[],knights='inward',knightFacings={},context={},scenePrefs={}){
  if(disposed||lost)return;lastArgs=[fen,flip,prefs,light,last,crownSquares,knights,knightFacings,context,scenePrefs];if(photoBusy||!frameGate.available()){deferred=true;canvas.dataset.gpuWaits=String(frameGate.skipped);return}deferred=false;const style=ArenaScene3D.settings(scenePrefs);canvas.dataset.environment=style.environment;if(style.motion==='instant')finishMotion();lighting(style);boardSpec=boards.update(style);lettering.visible=style.coordinates;canvas.dataset.coordinateCount=style.coordinates?'16':'0';environment.update(style,context);const club=style.environment==='live-club';hemi.visible=key.visible=fill.visible=!club;if(club&&!life)life=liveClub(scene,camera,assets,clubTemplates??=(set==='staunton1849'?templates:makeTemplates(assets.pieces,'staunton1849')),own,mat,textures,renderer,error=>{if(disposed)return;if(onReady)onReady(error);else if(!error&&lastArgs)render(...lastArgs)});life?.update(style,context,context.environmentMotion!==false);captures(context.captured,style);highlight.opacity=style.highlight;
  const shadowKey=[style.board,style.environment,style.surface,style.trays,style.plates,style.plaque].join(',');if(shadowKey!==shadowState){shadowState=shadowKey;renderer.shadowMap.needsUpdate=true}
  const rect=canvas.getBoundingClientRect();if(rect.width<2||rect.height<2)return;
  if(resizeDrawingBuffer(renderer,drawingBudget(rect.width,rect.height,devicePixelRatio,style.quality,club,maxBuffer)))canvas.dataset.bufferResizes=String(Number(canvas.dataset.bufferResizes||0)+1);canvas.dataset.renderWidth=String(canvas.width);canvas.dataset.renderHeight=String(canvas.height);camera.aspect=rect.width/rect.height;camera.updateProjectionMatrix();
  const p=settings(prefs),a=p.angle*Math.PI/180,o=(p.orbit+(flip?180:0))*Math.PI/180,d=14.3/p.zoom*Math.max(1,1/camera.aspect);camera.position.set(Math.sin(o)*Math.cos(a)*d,Math.sin(a)*d,Math.cos(o)*Math.cos(a)*d);camera.lookAt(0,.25,0);camera.rotateX(p.tilt*Math.PI/180);canvas.dataset.cameraTilt=String(p.tilt);camera.setViewOffset(rect.width,rect.height,0,p.lift*rect.height,rect.width,rect.height);camera.updateMatrixWorld();
  const placement=fen.split(' ')[0],marked=new Set(crownSquares),mode=knightMode(knights);
  const facings=placement==='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR'?{b1:1,g1:-1,b8:1,g8:-1}:knightFacings;
  const identity=JSON.stringify([placement,[...marked].sort(),mode,facings]);
  if(position!==identity||previousGame!==(context.key||'')){
   finishMotion();const plan=previousGame===(context.key||'')&&style.motion!=='instant'&&!context.reviewing?ArenaScene3D.transition(previousFen,fen,last):null,oldMap=meshMap;
   meshMap={};active.clear();let rank=0,file=0,count=0;const directions={};
   for(const c of placement){
    if(c==='/'){rank++;file=0}else if(/[1-8]/.test(c))file+=Number(c);else{
     if(templates[c]){
      const m=templates[c].clone(),type=c.toLowerCase(),white=c!==type,square='abcdefgh'[file]+(8-rank),ownerRotation=white?0:Math.PI;
      const rotation=type==='n'?knightRotation(mode,white,facings?.[square]):ownerRotation;
      m.position.set(file-3.5,.008,rank-3.5);m.rotateY(rotation);
      if(type==='n')directions[square]=Math.round(rotation*180/Math.PI);
      if(stamps[type]&&marked.has(square)){const stamp=new T.Mesh(stamps[type],stampMaterial);stamp.name='Kingside crown';m.add(stamp);count++}
      active.add(m);meshMap[square]=m;
     }
     file++;
    }
   }
   if(plan){
    duration=style.motion==='smooth'?550:220;started=performance.now();
    for(const change of plan.moves){const mesh=meshMap[change.to],old=oldMap[change.from];if(!mesh||!old)continue;const target=mesh.position.clone(),scale=mesh.scale.clone(),origin=old.position.clone();
     if(change.promotion){mesh.visible=false;active.add(old);tweens.push({mesh:old,origin,target,scale:old.scale.clone(),ghost:true,reveal:mesh,knight:false})}
     else tweens.push({mesh,origin,target,scale,knight:change.piece.toLowerCase()==='n'});
    }
    for(const square of plan.removed){const mesh=oldMap[square];if(mesh){active.add(mesh);tweens.push({mesh,origin:mesh.position.clone(),target:mesh.position.clone(),scale:mesh.scale.clone(),ghost:true})}}
   }
   previousFen=fen;previousGame=context.key||'';position=identity;canvas.dataset.knightMode=mode;canvas.dataset.knightRotations=JSON.stringify(directions);canvas.dataset.crownCount=String(count);renderer.shadowMap.needsUpdate=true;
  }
  marks.forEach((m,i)=>{const sq=last.slice(i*2,i*2+2);m.visible=/^[a-h][1-8]$/.test(sq);if(m.visible){m.position.x=sq.charCodeAt(0)-97-3.5;m.position.z=8-Number(sq[1])-3.5}});
  const hint=context.intention,hasHint=hint&&hint.fen===fen&&/^[a-h][1-8]$/.test(hint.from)&&/^[a-h][1-8]$/.test(hint.to)&&!context.reviewing;
  intentionMat.color.set(/^#[0-9a-f]{6}$/i.test(context.intentionColor||'')?context.intentionColor:0x35b9f3);
  intentionShaft.visible=intentionTip.visible=!!hasHint;
  if(hasHint){const point=s=>new T.Vector3(s.charCodeAt(0)-100.5,.055,4.5-Number(s[1])),start=point(hint.from),end=point(hint.to),dir=end.clone().sub(start),len=dir.length();dir.normalize();const q=new T.Quaternion().setFromUnitVectors(new T.Vector3(0,1,0),dir);intentionShaft.quaternion.copy(q);intentionTip.quaternion.copy(q);intentionShaft.scale.y=Math.max(.01,len-.3);intentionShaft.position.copy(start).addScaledVector(dir,(len-.3)/2);intentionTip.position.copy(end).addScaledVector(dir,-.2)}
  canvas.dataset.intention=hasHint?hint.from+hint.to:'';
  if(tweens.length){const t=Math.min(1,(performance.now()-started)/duration),ease=t*t*(3-2*t);for(const a of tweens){a.mesh.position.lerpVectors(a.origin,a.target,ease);a.mesh.position.y+=Math.sin(t*Math.PI)*(a.knight?.42:.055);if(a.ghost&&!a.reveal)a.mesh.scale.copy(a.scale).multiplyScalar(1-ease)}renderer.shadowMap.needsUpdate=true;if(t>=1)finishMotion()}
  canvas.dataset.animating=String(tweens.length>0);canvas.dataset.environment=style.environment;canvas.dataset.highlight=String(style.highlight);
  placeLetters();scene.background=new T.Color(light?0xc9c6bd:0x202b30);renderer.info.reset();if(club)life.draw();else renderer.render(scene,camera);frameGate.submitted();canvas.dataset.frames=String(++frames);canvas.dataset.drawCalls=String(renderer.info.render.calls);
  const label=(text,x,z)=>{const v=new T.Vector3(x,boardSpec.inkY,z).project(camera);return {text,x:(v.x+1)*rect.width/2,y:(1-v.y)*rect.height/2}};
  return !style.coordinates?[]:[...Array.from({length:8},(_,i)=>label('abcdefgh'[i],i-3.5,camera.position.z>=0?boardSpec.letter:-boardSpec.letter)),...Array.from({length:8},(_,i)=>label(String(8-i),camera.position.x<=0?-boardSpec.letter:boardSpec.letter,i-3.5))];
 }
 async function settled(){await frameGate.idle();if(deferred&&lastArgs){render(...lastArgs);await frameGate.idle()}}
 // Interactive boards share the same geometry and camera. Picking uses real
 // mesh intersections, then the board plane; decorations never intercept moves.
 const ray=new T.Raycaster(),plane=new T.Plane(new T.Vector3(0,1,0),0),hit=new T.Vector3();let dragPiece=null,interactionGroup=null;
 function cast(x,y){const rect=canvas.getBoundingClientRect();ray.setFromCamera(new T.Vector2((x-rect.left)/rect.width*2-1,1-(y-rect.top)/rect.height*2),camera)}
 function pick(x,y,ground=false){
  cast(x,y);if(!ground){scene.updateMatrixWorld(true);const objects=Object.entries(meshMap);const hits=ray.intersectObjects(objects.map(([,m])=>m),true);if(hits.length){let object=hits[0].object;while(object&&object.parent!==active)object=object.parent;return objects.find(([,m])=>m===object)?.[0]||null}}
  if(!ray.ray.intersectPlane(plane,hit))return null;const f=Math.floor(hit.x+4),r=Math.floor(hit.z+4);return f>=0&&f<8&&r>=0&&r<8?'abcdefgh'[f]+(8-r):null;
 }
 function drag(square,x,y){
  finishMotion();if(!square){if(dragPiece){dragPiece.mesh.position.copy(dragPiece.origin);dragPiece=null;renderer.shadowMap.needsUpdate=true}return}
  const mesh=meshMap[square];if(!mesh)return;
  if(!dragPiece)dragPiece={mesh,origin:mesh.position.clone()};cast(x,y);
  if(ray.ray.intersectPlane(plane,hit)){mesh.position.set(hit.x,.15,hit.z);renderer.shadowMap.needsUpdate=true}
 }
 function interaction(selected,targets=[],hint=[]){
  if(!interactionGroup){interactionGroup=new T.Group();scene.add(interactionGroup);const geo=own(new T.RingGeometry(.24,.31,32)),material=mat(new T.MeshBasicMaterial({color:0x65dfbb,transparent:true,opacity:.85,depthWrite:false}));for(let i=0;i<64;i++){const mesh=new T.Mesh(geo,material);mesh.rotation.x=-Math.PI/2;mesh.position.y=.015;mesh.visible=false;interactionGroup.add(mesh)}}
  const squares=[...new Set([selected,...targets,...hint].filter(s=>/^[a-h][1-8]$/.test(s||'')))];
  interactionGroup.children.forEach((m,i)=>{const sq=squares[i];m.visible=!!sq;if(sq){m.position.x=sq.charCodeAt(0)-97-3.5;m.position.z=8-Number(sq[1])-3.5}});
 }
 return {render,pick,drag,interaction,metrics:()=>({...renderer.info.memory}),ready:async()=>{await settled();const result=await Promise.all([environment.ready(),life?life.ready():true]);await settled();return result.every(Boolean)},needsFrame:()=>!photoBusy&&(deferred||tweens.length>0||!!life?.needsFrame()),settled,freezeEnvironment(value){life?.freeze(value)},pauseEnvironment(){life?.pause()},finishMotion,photo(options){const captured=lastArgs?[...lastArgs]:null;const job=photoQueue.then(async()=>{await settled();finishMotion();if(captured)render(...captured);await frameGate.idle();photoBusy=true;try{return photograph(renderer,scene,camera,canvas,options,captured?.[9]?.environment==='live-club'?linear=>life.draw(linear):null)}finally{photoBusy=false;frameGate.submitted()}});photoQueue=job.catch(()=>{});return job},dispose(){if(disposed)return;disposed=true;frameGate.dispose();life?.dispose();environment.dispose();canvas.removeEventListener('webglcontextlost',lostHandler);for(const g of owned)g.dispose();for(const m of materials)m.dispose();for(const t of textures.values())t.dispose();key.shadow.dispose();env.dispose();renderer.dispose();renderer.forceContextLoss()}};
}
