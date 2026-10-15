import * as T from '/ui/three.module.js';
import {GLTFLoader} from '/ui/three-gltf.js';
import {RoomEnvironment} from '/ui/three-room.js';
import {boardCollection} from '/ui/board3d-boards.js';
import {crownGeometry,crownTexture} from '/ui/board3d-crowns.js';
import {clubGame,clubPlayer,clubGuests,clubCastNames,prepareClubCharacter} from '/ui/board3d-club-motion.js';
import {buildClub} from './room.js';
import {EffectComposer} from './addons/postprocessing/EffectComposer.js';
import {SSAOPass} from './addons/postprocessing/SSAOPass.js';
import {RenderPass} from './addons/postprocessing/RenderPass.js';
import {OutputPass} from './addons/postprocessing/OutputPass.js';
import {RectAreaLightUniformsLib} from './addons/lights/RectAreaLightUniformsLib.js';

const canvas=document.querySelector('#view'),renderer=new T.WebGLRenderer({canvas,antialias:true,powerPreference:'low-power'});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.outputColorSpace=T.SRGBColorSpace;
renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.03;
renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFSoftShadowMap;renderer.shadowMap.autoUpdate=false;
const scene=new T.Scene();scene.background=new T.Color(0xa9bdba);const camera=new T.PerspectiveCamera(48,1,.1,500);
const geometries=new Set(),materials=new Set(),textures=new Set(),own=g=>(geometries.add(g),g),keep=m=>(materials.add(m),m),texture=t=>(textures.add(t),t);
const loader=new T.TextureLoader(),loadMap=async url=>texture(await loader.loadAsync(url));
async function scan(kind){return Object.fromEntries(await Promise.all(['color','normal','rough'].map(async n=>[n,await loadMap(`/ui/scene-assets/${kind}-${n}.jpg`)])))}
try {
const [model,distant,wood,leather]=await Promise.all([new GLTFLoader().loadAsync('/ui/staunton1849.glb'),new GLTFLoader().loadAsync('./distant-staunton.glb'),scan('wood'),scan('leather')]);
const distantMeshes={};distant.scene.traverse(o=>{if(o.isMesh&&o.name.length===1&&'pnbrqk'.includes(o.name))distantMeshes[o.name]=o.geometry});
const source={};model.scene.traverse(o=>{if(o.isMesh&&o.name.length===1&&'pnbrqk'.includes(o.name))source[o.name]=o});
const assets={wood,leather};
const hemi=new T.HemisphereLight(0xe0eeed,0xa2a599,.78);scene.add(hemi);
const sun=new T.DirectionalLight(0xffecd0,2.25);sun.position.set(-110,42,15);sun.target.position.set(20,-13,-30);sun.castShadow=true;sun.shadow.mapSize.set(4096,4096);Object.assign(sun.shadow.camera,{left:-102,right:102,top:92,bottom:-92,near:1,far:290});sun.shadow.bias=-.00015;sun.shadow.normalBias=.09;sun.shadow.radius=3;scene.add(sun,sun.target);
const broad=new T.DirectionalLight(0xedf4ff,.85);broad.position.set(30,35,12);scene.add(broad);
const key=new T.DirectionalLight(0xffe0b2,.90);key.position.set(-8,18,6);key.castShadow=true;key.shadow.mapSize.set(2048,2048);Object.assign(key.shadow.camera,{left:-13,right:13,top:13,bottom:-13,near:.1,far:45});key.shadow.bias=-.00018;key.shadow.normalBias=.018;scene.add(key);
const pmrem=new T.PMREMGenerator(renderer),neutral=new RoomEnvironment(),env=pmrem.fromScene(neutral,.12);scene.environment=env.texture;scene.environmentIntensity=.52;neutral.dispose();
RectAreaLightUniformsLib.init();
const windows=[];for(const z of [-57,-1]){const light=new T.RectAreaLight(0xe2eeec,3.5,36,28);light.position.set(-60,27,z);light.lookAt(0,6,z);scene.add(light);windows.push(light)}
const lamps=[];for(const [x,z] of [[0,0],[-29,-42],[29,-47]]){const l=new T.RectAreaLight(0xffdfb9,.8,9,9);l.position.set(x,30,z);l.lookAt(x,-13,z);scene.add(l);lamps.push(l)}
let timeOverride=null;
const room=buildClub(scene,assets,own,keep,texture);
// Render the room itself into the reflection probe: all pieces and furnishings
// reflect the same modeled surroundings. No panorama or photographic backdrop.
const roomProbe=pmrem.fromScene(scene,.08,.3,400);env.dispose();scene.environment=roomProbe.texture;scene.environmentIntensity=.65;pmrem.dispose();

const templates={};
for(const [type,s] of Object.entries(source))for(const white of [true,false]){
 const m=keep(s.material.clone());m.roughnessMap=null;m.color.set(white?0xffdfb0:0x171411);m.roughness=.28;m.specularIntensity=.85;m.clearcoat=white?.30:.26;m.clearcoatRoughness=.28;m.normalScale?.set(.35,.35);m.envMapIntensity=1.25;
 const obj=new T.Mesh(s.geometry,m);obj.rotation.copy(s.rotation);obj.scale.copy(s.scale);obj.castShadow=obj.receiveShadow=true;templates[white?type.toUpperCase():type]=obj;
}
const ink=texture(crownTexture()),stamp=keep(new T.MeshStandardMaterial({map:ink,roughness:.72,transparent:true,alphaTest:.05,depthWrite:false,polygonOffset:true,polygonOffsetFactor:-2,polygonOffsetUnits:-2}));
const crowns={r:own(crownGeometry(source.r,'r')),n:own(crownGeometry(source.n,'n'))};
function set(parent,index){
 const group=new T.Group();parent.add(group);const blank=new T.Group(),unused=new Map();group.add(blank);const collection=boardCollection(group,assets,own,keep,unused,renderer,blank);collection.update({board:'drueke'});for(const t of unused.values())texture(t);
 const map={},all=[];
 for(const rank of [1,2,7,8])for(let f=0;f<8;f++){
  const type=rank===2||rank===7?'p':'rnbqkbnr'[f],white=rank<3,o=templates[white?type.toUpperCase():type].clone();if(index)o.geometry=distantMeshes[type];
  o.position.set(f-3.5,.008,4.5-rank);o.rotateY(type==='n'?(f===1?Math.PI:0):(white?0:Math.PI));
  if((f===6&&type==='n')||(f===7&&type==='r'))o.add(new T.Mesh(crowns[type],stamp));
  const square='abcdefgh'[f]+rank;map[square]=o;o.updateMatrix();const height=new T.Box3().setFromBufferAttribute(o.geometry.attributes.position).applyMatrix4(o.matrix).getSize(new T.Vector3()).y;all.push({o,square,height});group.add(o);
 }
 return clubGame(all,Math.max(0,index-1),room.clocks[index]);
}
const games=room.tables.map(set);
function showClocks(t){const local=room.setTime(timeOverride||new Date());sun.intensity=2.25*local.day;hemi.intensity=.28+.5*local.day;hemi.color.set(0x7185b1).lerp(new T.Color(0xe0eeed),local.day);broad.intensity=.55+.3*local.day;key.intensity=.9+(1-local.day)*.28;windows.forEach(l=>l.intensity=.04+3.46*local.day);lamps.forEach(l=>l.intensity=.8+(1-local.day)*5.2);let door=0;visitors.forEach(({g,actor},i)=>{if(i<4)actor.update(t,games[1+Math.floor(i/2)].state())});room.door.update(guestDirector?.update(t).door||0,t)}

const visitors=[];let guestDirector=null;
if(new URLSearchParams(location.search).has('cast')){
 for(const [i,name] of clubCastNames.entries()){
  const model=await new GLTFLoader().loadAsync(`./cast/${name}.glb`),g=model.scene,mixer=new T.AnimationMixer(g);if(model.animations[0]){mixer.clipAction(model.animations[0]).play();mixer.update(0)}
  const table=i<4?room.tables[1+Math.floor(i/2)]:room.root;table.add(g);g.position.set(0,room.floor,i%2?-10.5:10.5);g.rotation.y=i%2?0:Math.PI;g.traverse(o=>{if(o.isMesh){o.castShadow=o.receiveShadow=true;o.frustumCulled=false;}});prepareClubCharacter(g);visitors.push({g,actor:i<4?clubPlayer(g,table,i):null});
 }
}
guestDirector=visitors.length?clubGuests(visitors.slice(4).map(v=>v.g),room.floor,421,room.library):null;
const renderTarget=new T.WebGLRenderTarget(1,1,{type:T.HalfFloatType,samples:4}),composer=new EffectComposer(renderer,renderTarget),ssao=new SSAOPass(scene,camera,800,600,24),output=new OutputPass();ssao.kernelRadius=2.3;ssao.minDistance=.00012;ssao.maxDistance=.025;composer.addPass(new RenderPass(scene,camera));composer.addPass(ssao);composer.addPass(output);
renderer.info.autoReset=false;let sizeKey='';
// Camera presets are actual scene positions. The room tour moves through room
// space instead of rotating a picture around a stationary table.
const views={entrance:{p:[-1,16,-44],target:[20,5,-94],fov:48},players:{p:[-9,9,-32],target:[-29,1,-42],fov:55},wallclock:{p:[41,18,-34],target:[60,21,-46],fov:40},clock:{p:[-3,7,12],target:[5,.3,0],fov:43},cast:{p:[-12,10,-26],target:[-29,5,-42],fov:50},board:{p:[13,10.5,19],target:[0,1,-3],fov:43},room:{p:[48,26,43],target:[-5,7,-34],fov:62},library:{p:[-2,17,-22],target:[0,12,-90],fov:67}};
let motion=!matchMedia('(prefers-reduced-motion: reduce)').matches,tour=false,seconds=0,lastTime=0,frames=0,activeView='board',transition=null,fps=30,disposed=false,timer=0,raf=0,drag=null;
const target=new T.Vector3(),orbit={azimuth:0,polar:0,distance:1};
function updateOrbit(){const d=camera.position.clone().sub(target);orbit.distance=d.length();orbit.azimuth=Math.atan2(d.x,d.z);orbit.polar=Math.acos(d.y/d.length())}
function choose(name,instant=false){activeView=name;tour=false;document.querySelector('#tour').setAttribute('aria-pressed','false');const v=views[name];if(instant){camera.position.set(...v.p);target.set(...v.target);camera.fov=v.fov;camera.updateProjectionMatrix();updateOrbit()}else transition={from:camera.position.clone(),to:new T.Vector3(...v.p),a:target.clone(),b:new T.Vector3(...v.target),f:camera.fov,g:v.fov,start:performance.now()};document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.view===name)));invalidate()}
function render(){const rect=canvas.getBoundingClientRect();if(sizeKey!==rect.width+':'+rect.height){sizeKey=rect.width+':'+rect.height;renderer.setSize(rect.width,rect.height,false);composer.setSize(rect.width,rect.height)}camera.aspect=rect.width/rect.height;camera.updateProjectionMatrix();camera.lookAt(target);ssao.kernelRadius=activeView==='board'?1.4:3.4;renderer.info.reset();ssao.ssaoMaterial.uniforms.cameraProjectionMatrix.value.copy(camera.projectionMatrix);ssao.ssaoMaterial.uniforms.cameraInverseProjectionMatrix.value.copy(camera.projectionMatrixInverse);composer.render();canvas.dataset.frames=String(++frames);canvas.dataset.seconds=seconds.toFixed(3);canvas.dataset.triangles=String(renderer.info.render.triangles);canvas.dataset.calls=String(renderer.info.render.calls)}
function invalidate(){if(disposed||document.hidden)return;clearTimeout(timer);timer=0;if(!raf)raf=requestAnimationFrame(frame)}
function frame(now){raf=0;if(disposed||document.hidden)return;const delta=lastTime?Math.min(.10,(now-lastTime)/1000):0;lastTime=now;if(motion){seconds+=delta;room.update(seconds);games.forEach(g=>g.update(seconds));showClocks(seconds);renderer.shadowMap.needsUpdate=true}
 if(transition){const t=Math.min(1,(now-transition.start)/1600),e=t*t*t*(10+t*(-15+6*t));camera.position.lerpVectors(transition.from,transition.to,e);target.lerpVectors(transition.a,transition.b,e);camera.fov=T.MathUtils.lerp(transition.f,transition.g,e);if(t===1){transition=null;updateOrbit()}}
 if(tour&&!transition){const phase=seconds/65*2*Math.PI;camera.position.set(Math.sin(phase)*32,18+Math.sin(phase*.5)*4,17+Math.cos(phase)*17);target.set(0,4,-23);camera.fov=57;updateOrbit()}
 render();if(motion||transition||tour)timer=setTimeout(()=>{timer=0;invalidate()},1000/fps)}
function stop(){clearTimeout(timer);timer=0;cancelAnimationFrame(raf);raf=0;lastTime=0}
document.addEventListener('visibilitychange',()=>{stop();if(!document.hidden)invalidate()});
addEventListener('resize',invalidate);
canvas.addEventListener('pointerdown',e=>{canvas.setPointerCapture(e.pointerId);tour=false;transition=null;document.querySelector('#tour').setAttribute('aria-pressed','false');updateOrbit();drag={x:e.clientX,y:e.clientY,a:orbit.azimuth,p:orbit.polar}});
canvas.addEventListener('pointermove',e=>{if(!drag)return;orbit.azimuth=drag.a-(e.clientX-drag.x)*.004;orbit.polar=Math.max(.13,Math.min(1.62,drag.p-(e.clientY-drag.y)*.004));camera.position.setFromSphericalCoords(orbit.distance,orbit.polar,orbit.azimuth).add(target);invalidate()});canvas.addEventListener('pointerup',()=>drag=null);canvas.addEventListener('pointercancel',()=>drag=null);
canvas.addEventListener('wheel',e=>{e.preventDefault();tour=false;transition=null;document.querySelector('#tour').setAttribute('aria-pressed','false');updateOrbit();orbit.distance=Math.max(7,Math.min(95,orbit.distance*Math.exp(e.deltaY*.001)));camera.position.setFromSphericalCoords(orbit.distance,orbit.polar,orbit.azimuth).add(target);invalidate()},{passive:false});
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>choose(b.dataset.view));
document.querySelector('#motion').setAttribute('aria-pressed',String(motion));document.querySelector('#motion').onclick=()=>{motion=!motion;document.querySelector('#motion').setAttribute('aria-pressed',String(motion));lastTime=0;invalidate()};
document.querySelector('#tour').onclick=()=>{tour=!tour;transition=null;motion=true;document.querySelector('#tour').setAttribute('aria-pressed',String(tour));document.querySelector('#motion').setAttribute('aria-pressed','true');invalidate()};
function photo(){const oldSize=renderer.getSize(new T.Vector2()),ratio=renderer.getPixelRatio(),aspect=camera.aspect;renderer.setPixelRatio(1);renderer.setSize(3840,2160,false);composer.setPixelRatio(1);composer.setSize(3840,2160);camera.aspect=3840/2160;camera.updateProjectionMatrix();composer.render();const image=canvas.toDataURL('image/png');renderer.setPixelRatio(ratio);renderer.setSize(oldSize.x,oldSize.y,false);composer.setPixelRatio(ratio);composer.setSize(oldSize.x,oldSize.y);camera.aspect=aspect;camera.updateProjectionMatrix();render();return image}
document.querySelector('#capture').onclick=()=>{const a=document.createElement('a');a.download='Engine-Arena-live-club-study-4K.png';a.href=photo();a.click()};
addEventListener('keydown',e=>{if(e.key.toLowerCase()==='h')for(const node of document.querySelectorAll('header,nav,#status'))node.classList.toggle('hidden')});
window.clubPreview={room,guestDirector,setTime(date){timeOverride=date?new Date(date):null;showClocks(seconds);renderer.shadowMap.needsUpdate=true;render()},actors:visitors,games,scene,camera,target,choose:(name)=>choose(name,true),freeze(t=0){motion=false;tour=false;transition=null;seconds=t;stop();room.update(t);games.forEach(g=>g.update(t));showClocks(t);renderer.shadowMap.needsUpdate=true;render()},photo,metrics:()=>({frames,seconds,triangles:renderer.info.render.triangles,calls:renderer.info.render.calls,memory:{...renderer.info.memory},people:visitors.length,panoramas:0,animationChannels:room.animationCount}),dispose(){disposed=true;stop();for(const g of geometries)g.dispose();for(const m of materials)m.dispose();for(const t of textures)t.dispose();roomProbe.dispose();ssao.dispose();output.dispose();composer.dispose();renderer.dispose()}};
room.update(0);games.forEach(g=>g.update(0));showClocks(0);renderer.shadowMap.needsUpdate=true;choose('room',true);document.querySelector('#loading').hidden=true;canvas.dataset.ready='true';
}catch(error){console.error(error);document.querySelector('#loading').textContent='The preview could not load: '+error.message;canvas.dataset.error=error.message}
