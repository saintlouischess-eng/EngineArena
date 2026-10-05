// Close-up inspection of the actual GLB and the app's Three.js/material setup.
// Only the camera and arrangement differ from the focused board.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const r=JSON.parse(fs.readFileSync('test-output/workflow-ready.json','utf8'));assert(r.folder.includes('test-output'));
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage({viewport:{width:2200,height:1150}}),errors=[];page.on('pageerror',e=>errors.push(e.stack));await page.goto(r.url);
  await page.evaluate(async()=>{
   const T=await import('/assets/three.module.js'),{GLTFLoader}=await import('/assets/three-gltf.js'),{RoomEnvironment}=await import('/assets/three-room.js');
   const gltf=await new GLTFLoader().loadAsync('/assets/staunton1849.glb'),sources={};gltf.scene.traverse(o=>{if(o.isMesh)sources[o.name]=o});const source=sources.n;if(!source)throw Error('Missing knight');
   const canvas=document.createElement('canvas');canvas.style='position:fixed;inset:0;width:100%;height:100%;z-index:100000';document.body.append(canvas);
   const renderer=new T.WebGLRenderer({canvas,antialias:true});renderer.setSize(innerWidth,innerHeight);renderer.outputColorSpace=T.SRGBColorSpace;renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05;renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFShadowMap;
   const scene=new T.Scene();scene.background=new T.Color(0x202933);const pmrem=new T.PMREMGenerator(renderer),room=new RoomEnvironment(),env=pmrem.fromScene(room,.04,.1,100);scene.environment=env.texture;scene.environmentIntensity=.65;room.dispose();pmrem.dispose();
   scene.add(new T.HemisphereLight(0xe4eeff,0x806950,1.25));const key=new T.DirectionalLight(0xfff1dc,2.4);key.position.set(-4,9,5);key.castShadow=true;key.shadow.mapSize.set(2048,2048);Object.assign(key.shadow.camera,{left:-3,right:3,top:3,bottom:-3,near:.1,far:24});key.shadow.bias=-.00025;key.shadow.normalBias=.003;key.shadow.radius=2;scene.add(key);
   const fill=new T.DirectionalLight(0xe0eaff,1.3);fill.position.set(5,5,-4);scene.add(fill);
   const meshes=[];for(let i=0;i<3;i++){
    const m=source.clone();m.material=source.material.clone();const white=i<2;m.material.color.set(white?0xffdfb0:0x302b26);m.material.roughness=white?.98:.88;m.material.clearcoat=.18;m.material.clearcoatRoughness=.34;m.material.normalScale.set(.35,.35);m.material.envMapIntensity=1;m.rotation.copy(source.rotation);m.rotateY([0,Math.PI/4,-Math.PI/6][i]);m.position.set((i-1)*1.02,0,0);m.castShadow=m.receiveShadow=true;scene.add(m);meshes.push(m);
   }
   const floor=new T.Mesh(new T.PlaneGeometry(200,200),new T.MeshStandardMaterial({color:0x29343e,roughness:.95}));floor.rotation.x=-Math.PI/2;floor.position.y=-.005;floor.receiveShadow=true;scene.add(floor);
   const h=1.62,w=h*innerWidth/innerHeight,camera=new T.OrthographicCamera(-w/2,w/2,h/2,-h/2,.1,40);camera.position.set(0,1.48,6);camera.lookAt(0,.57,0);renderer.render(scene,camera);
   window.knightStudy={renderer,scene,camera,meshes,sources,T};
   window.arrangeStudy=(keys,angles,spacing,height,target,elevation)=>{
    const q=knightStudy;for(const m of q.meshes){q.scene.remove(m);m.material.dispose()}q.meshes=[];
    keys.forEach((name,i)=>{const source=q.sources[name],m=source.clone();m.material=source.material.clone();const white=i!==keys.length-1;m.material.color.set(white?0xffdfb0:0x302b26);m.material.roughness=white?.98:.88;m.material.clearcoat=.18;m.material.clearcoatRoughness=.34;m.material.normalScale.set(.35,.35);m.material.envMapIntensity=1;m.rotation.copy(source.rotation);m.rotateY(angles[i]);m.position.set((i-(keys.length-1)/2)*spacing,0,0);m.castShadow=m.receiveShadow=true;q.scene.add(m);q.meshes.push(m)});
    const w=height*innerWidth/innerHeight;q.camera.left=-w/2;q.camera.right=w/2;q.camera.top=height/2;q.camera.bottom=-height/2;q.camera.position.set(0,elevation,6);q.camera.lookAt(0,target,0);q.camera.updateProjectionMatrix();q.renderer.render(q.scene,q.camera);
   };
  });
  await page.screenshot({path:'media/staunton1849/review/knight-wood-study.png'});
  await page.evaluate(()=>{const q=knightStudy;for(const m of q.meshes){m.receiveShadow=false;m.material.needsUpdate=true}q.renderer.render(q.scene,q.camera)});
  await page.screenshot({path:'media/staunton1849/review/knight-wood-no-shadow.png'});
  await page.evaluate(()=>{const q=knightStudy;for(const m of q.meshes){m.receiveShadow=true;m.material.needsUpdate=true;m.material.normalMap=null;m.material.needsUpdate=true}q.renderer.render(q.scene,q.camera)});
  await page.screenshot({path:'media/staunton1849/review/knight-wood-no-normal.png'});
  await page.evaluate(()=>{const q=knightStudy;for(const m of q.meshes){m.material.map=null;m.material.roughnessMap=null;m.material.roughness=.5;m.material.clearcoat=0;m.material.color.set(0x808080);m.material.needsUpdate=true}q.renderer.render(q.scene,q.camera)});
  await page.screenshot({path:'media/staunton1849/review/knight-webgl-clay.png'});
  await page.evaluate(()=>arrangeStudy(['n','n','n'],[0,Math.PI/2,Math.PI/4],1.02,1.62,.57,1.48));
  await page.screenshot({path:'media/staunton1849/review/knight-refined-study.png'});
  await page.evaluate(()=>arrangeStudy(['k','q','b','n','r','p'],[0,0,0,Math.PI/4,0,0],.88,3.0,.84,3.0));
  await page.evaluate(()=>{const q=knightStudy;for(const m of q.meshes){m.material.color.set(0xffdfb0);m.material.roughness=.98}q.renderer.render(q.scene,q.camera)});
  await page.screenshot({path:'media/staunton1849/review/set-wood-study.png'});
  await page.evaluate(()=>{const q=knightStudy;for(const m of q.meshes){m.material.color.set(0x302b26);m.material.roughness=.88}q.renderer.render(q.scene,q.camera)});
  await page.screenshot({path:'media/staunton1849/review/set-ebony-study.png'});
  await page.evaluate(()=>arrangeStudy(['k','q','b'],[0,0,0],1.10,2.0,.88,1.6));
  await page.evaluate(()=>{const q=knightStudy;for(const m of q.meshes){m.material.color.set(0xffdfb0);m.material.roughness=.98}q.renderer.render(q.scene,q.camera)});
  await page.screenshot({path:'media/staunton1849/review/proportions-wood-study.png'});
  await page.evaluate(()=>arrangeStudy(['b','b'],[0,Math.PI/2],.8,.75,1.14,1.6));
  await page.screenshot({path:'media/staunton1849/review/bishop-wood-finial.png'});
  await page.evaluate(()=>arrangeStudy(['q','q'],[0,.33],.85,.95,1.15,4.2));
  await page.screenshot({path:'media/staunton1849/review/queen-wood-crown.png'});
  await page.evaluate(()=>arrangeStudy(['q','q'],[0,.33],.85,.85,1.25,1.25));
  await page.screenshot({path:'media/staunton1849/review/queen-wood-profile.png'});
  await page.evaluate(()=>{
   arrangeStudy(['q','q'],[0,0],.85,.80,1.30,6);
   const q=knightStudy;q.camera.position.set(0,6,.001);q.camera.lookAt(0,1.30,0);q.renderer.render(q.scene,q.camera);
  });
  await page.screenshot({path:'media/staunton1849/review/queen-wood-overhead.png'});
  assert.deepEqual(errors,[]);console.log('Rendered actual GLB close-ups with the application material settings.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
