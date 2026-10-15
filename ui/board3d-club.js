// Complete modeled room. No photographic backdrop or duplicated visitors.
import * as T from './three.module.js';
import {GLTFLoader} from './three-gltf.js';
import {clubGame,clubPlayer,clubGuests,clubCastNames,prepareClubCharacter} from './board3d-club-motion.js';
import {buildClub} from './board3d-club-room.js';
import {boardCollection} from './board3d-boards.js';
import {EffectComposer} from './three-club-EffectComposer.js';
import {RenderPass} from './three-club-RenderPass.js';
import {SSAOPass} from './three-club-SSAOPass.js';
import {OutputPass} from './three-club-OutputPass.js';
import {RectAreaLightUniformsLib} from './three-club-RectAreaLightUniformsLib.js';

export function liveClub(scene,camera,assets,templates,own,keep,textures,renderer,changed){
 const texture=t=>(textures.set(t,t),t),room=buildClub(scene,assets,own,keep,texture),lights=new T.Group();scene.add(lights);
 const hemi=new T.HemisphereLight(0xe0eeed,0xa2a599,.78);lights.add(hemi);
 const sun=new T.DirectionalLight(0xffecd0,2.25);sun.position.set(-110,42,15);sun.target.position.set(20,-13,-30);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-102,right:102,top:92,bottom:-92,near:1,far:290});sun.shadow.bias=-.00015;sun.shadow.normalBias=.09;lights.add(sun,sun.target);
 const broad=new T.DirectionalLight(0xedf4ff,.85);broad.position.set(30,35,12);lights.add(broad);
 const key=new T.DirectionalLight(0xffe0b2,.90);key.position.set(-8,18,6);key.castShadow=true;key.shadow.mapSize.set(2048,2048);Object.assign(key.shadow.camera,{left:-13,right:13,top:13,bottom:-13,near:.1,far:45});key.shadow.bias=-.00018;key.shadow.normalBias=.018;lights.add(key);
 const windows=[];RectAreaLightUniformsLib.init();for(const z of [-57,-1]){const l=new T.RectAreaLight(0xe2eeec,3.5,36,28);l.position.set(-60,27,z);l.lookAt(0,6,z);lights.add(l);windows.push(l)}
 const lamps=[];for(const [x,z] of [[0,0],[-29,-42],[29,-47]]){const l=new T.RectAreaLight(0xffdfb9,.8,9,9);l.position.set(x,30,z);l.lookAt(x,-13,z);lights.add(l);lamps.push(l)}
 // New lights need valid shadow textures before the reflection probe renders.
 // The shared renderer normally updates shadows only when a position changes.
 renderer.shadowMap.needsUpdate=true;
 const pmrem=new T.PMREMGenerator(renderer),probe=pmrem.fromScene(scene,.08,.3,400);pmrem.dispose();
 const composer=new EffectComposer(renderer,new T.WebGLRenderTarget(1,1,{type:T.HalfFloatType,samples:2})),ssao=new SSAOPass(scene,camera,1,1,16),output=new OutputPass();ssao.kernelRadius=1.4;ssao.minDistance=.00012;ssao.maxDistance=.025;composer.setPixelRatio(1);
 // AO needs less resolution than the color image; retain its aspect ratio.
 const resizeAO=ssao.setSize.bind(ssao);ssao.setSize=(w,h)=>{const scale=Math.min(.5,1280/w,1280/h);resizeAO(Math.max(1,Math.floor(w*scale)),Math.max(1,Math.floor(h*scale)))};
 composer.addPass(new RenderPass(scene,camera));composer.addPass(ssao);composer.addPass(output);
 const loader=new GLTFLoader(),games=[],visitors=[],mixers=[];let elapsed=0,previous=0,running=false,frozen=false,frozenTime=null,visible=true,disposed=false,waiting=Promise.resolve(true),castWaiting=null,clockRunning=false,sizeKey='',quality='',wallTimer=0,lastShadow=-Infinity;
 let guestDirector=null;
 const stopWall=()=>{clearTimeout(wallTimer);wallTimer=0};
 function adopt(model){model.scene.traverse(o=>{if(o.isMesh){own(o.geometry);for(const m of [o.material].flat()){keep(m);for(const v of Object.values(m))if(v?.isTexture)texture(v)}o.receiveShadow=true;o.castShadow=!/Hair[ _]*fine|Beard[ _]*fine/i.test(o.name)}})}
 function discard(model){model.scene.traverse(o=>{if(o.isMesh){o.geometry.dispose();for(const m of [o.material].flat()){for(const v of Object.values(m))if(v?.isTexture)v.dispose();m.dispose()}}})}
 function tableGame(parent,index,distant){
  const group=new T.Group();parent.add(group);const blank=new T.Group();group.add(blank);const collection=boardCollection(group,assets,own,keep,textures,renderer,blank);collection.update({board:'drueke'});
  const map={},all=[];for(const rank of [1,2,7,8])for(let f=0;f<8;f++){const type=rank===2||rank===7?'p':'rnbqkbnr'[f],white=rank<3,o=templates[white?type.toUpperCase():type].clone();o.geometry=distant[type];o.rotateY(type==='n'?(f===1?Math.PI:0):(white?0:Math.PI));const square='abcdefgh'[f]+rank;o.updateMatrix();const height=new T.Box3().setFromBufferAttribute(o.geometry.attributes.position).applyMatrix4(o.matrix).getSize(new T.Vector3()).y;all.push({o,square,height});group.add(o)}
  return clubGame(all,index,room.clocks[index+1]);
 }

 waiting=loader.loadAsync('/assets/club-staunton.glb').then(model=>{if(disposed){discard(model);return false}adopt(model);const distant={};model.scene.traverse(o=>{if(o.isMesh&&'pnbrqk'.includes(o.name)&&o.name.length===1)distant[o.name]=o.geometry});if(Object.keys(distant).length!==6)throw Error('Incomplete background set');room.tables.slice(1).forEach((table,i)=>games.push(tableGame(table,i,distant)));changed();return true}).catch(e=>{if(!disposed)changed(e);return false});
 function loadCast(){if(castWaiting)return;castWaiting=Promise.allSettled(clubCastNames.map(n=>loader.loadAsync('/assets/club-'+n+'.glb'))).then(results=>{
  if(disposed){for(const r of results)if(r.status==='fulfilled')discard(r.value);return false}
  if(results.some(r=>r.status==='rejected')){for(const r of results)if(r.status==='fulfilled')discard(r.value);changed(Error('Club visitors could not load'));return false}
  results.forEach((r,i)=>{const model=r.value;adopt(model);const g=model.scene,mixer=new T.AnimationMixer(g);if(model.animations[0]){mixer.clipAction(model.animations[0]).play();mixer.update(0)}mixers.push(mixer);const table=i<4?room.tables[1+Math.floor(i/2)]:room.root;table.add(g);g.position.set(0,room.floor,i%2?-10.5:10.5);g.rotation.y=i%2?0:Math.PI;g.traverse(o=>{if(o.isMesh){o.frustumCulled=false;}});prepareClubCharacter(g);visitors.push({g,actor:i<4?clubPlayer(g,table,i):null})});guestDirector=clubGuests(visitors.slice(4).map(v=>v.g),room.floor,undefined,room.library);changed();return true;
 });}
 return {
  update(p,context={},animate=true,now=performance.now()){
   visible=p.environment==='live-club';room.root.visible=lights.visible=visible;
   if(!visible){running=clockRunning=false;previous=0;stopWall();renderer.domElement.dataset.liveRoom='off';return}
   scene.environment=probe.texture;scene.environmentRotation.y=0;scene.environmentIntensity=.65;
   const palette={daylight:[0xf1f7ff,0xe4eeff,2.3],evening:[0xffd5a2,0xe5d8c5,2.05],tournament:[0xffecd0,0xe0eeed,2.25]}[p.lighting];sun.color.set(palette[0]);sun.color.lerp(new T.Color(p.warmth>0?0xffd6a4:0xc9ddff),Math.abs(p.warmth)*.35);hemi.color.set(palette[1]);sun.intensity=palette[2];
   const local=room.setTime(frozenTime||new Date(),p.localTime,p.lighting),day=p.localTime?local.day:1;
   hemi.intensity=.28+.50*day;sun.intensity*=day;windows.forEach(l=>l.intensity=.04+3.46*day);lamps.forEach(l=>l.intensity=.8+(1-day)*5.2);broad.intensity=.55+.30*day;key.intensity=.90+(1-day)*.28;key.color.set(p.localTime?0xffe0b2:palette[0]);
   if(p.localTime){sun.color.set(0xffecd0).lerp(new T.Color(0xffab65),local.twilight*.65);hemi.color.set(0x7185b1).lerp(new T.Color(0xe0eeed),day);sun.position.set(-110,8+34*Math.sin(Math.PI*T.MathUtils.clamp((local.hours-6)/14,0,1)),55-(local.hours-6)*7)}
   else sun.position.set(-110,42,15);
   if(p.people)loadCast();running=p.live&&(p.people||p.backgroundGames||p.atmosphere)&&!frozen&&animate;
   const delta=previous?Math.min(.15,Math.max(0,now-previous)/1000):0;previous=now;if(running)elapsed+=delta*({quiet:.55,social:.8,busy:1.05}[p.activity]);
   const t=elapsed;room.update(p.atmosphere?t:0);games.forEach((g,i)=>g.update(p.backgroundGames?t:18+i*20,p.backgroundGames&&running));
   let door=0;visitors.forEach(({g,actor},i)=>{if(i<4){g.visible=p.people&&(p.activity!=='quiet'||i<2);if(g.visible)actor.update(t,games[Math.floor(i/2)]?.state(),p.backgroundGames)}});room.door.update(guestDirector?.update(t,p.people&&p.activity!=='quiet').door||0,t);
   const clock=ArenaClocks.table(context.clock,now)||null;room.clocks[0].set(clock);clockRunning=!!clock&&!frozen&&!!(clock.white?.active||clock.black?.active);
   // An otherwise still room needs only one wall-clock repaint per second.
   // Visibility/pause/disposal cancels it; no permanent high-FPS idle loop.
   if(running||clockRunning||frozen)stopWall();else if(!wallTimer&&!document.hidden)wallTimer=setTimeout(()=>{wallTimer=0;if(!disposed&&visible&&!frozen&&!document.hidden)changed()},1000-Date.now()%1000+10);
   if(quality!==p.quality){quality=p.quality;const size=quality==='low'?1024:2048;sun.shadow.mapSize.set(size,size);sun.shadow.map?.dispose();sun.shadow.map=null;renderer.shadowMap.needsUpdate=true}
   // Room motion shadows update at most 15 times per second. Board moves
   // still request an immediate shadow update in the shared renderer.
   if(running&&now-lastShadow>=1000/15){lastShadow=now;renderer.shadowMap.needsUpdate=true}
   Object.assign(renderer.domElement.dataset,{liveRoom:'live-club',roomPeople:String(visitors.filter(v=>v.g.visible).length),roomTables:'2',roomSeconds:elapsed.toFixed(3),roomClock:JSON.stringify(clock),roomActivity:p.activity,roomLocalTime:local.local,roomDaylight:String(day)});
  },draw(linear=false){
   const size=renderer.getDrawingBufferSize(new T.Vector2()),key=[size.x,size.y].join(':');if(key!==sizeKey){sizeKey=key;composer.setSize(size.x,size.y)}
   Object.assign(renderer.domElement.dataset,{aoWidth:String(ssao.width),aoHeight:String(ssao.height)});
   ssao.enabled=quality!=='low';ssao.ssaoMaterial.uniforms.cameraProjectionMatrix.value.copy(camera.projectionMatrix);ssao.ssaoMaterial.uniforms.cameraInverseProjectionMatrix.value.copy(camera.projectionMatrixInverse);output.enabled=!linear;composer.renderToScreen=!linear;composer.render();return composer.readBuffer.texture;
  },ready:async()=>{const a=await waiting,b=castWaiting?await castWaiting:true;return a&&b},needsFrame:()=>visible&&(running||clockRunning),pause(){previous=0;stopWall()},freeze(value){frozen=value;frozenTime=value?new Date():null;previous=0;stopWall()},dispose(){disposed=true;stopWall();room.root.removeFromParent();lights.removeFromParent();mixers.forEach((m,i)=>{m.stopAllAction();m.uncacheRoot(visitors[i].g)});sun.shadow.dispose();key.shadow.dispose();probe.dispose();ssao.noiseTexture.dispose();ssao.ssaoMaterial.dispose();ssao.dispose();output.dispose();composer.dispose()}
 };
}
