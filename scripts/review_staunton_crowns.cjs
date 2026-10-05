// Inspect the actual shipped crown projection on both wood colors.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const ready=JSON.parse(fs.readFileSync('test-output/workflow-ready.json','utf8'));assert(ready.folder.includes('test-output'));
 const browser=await chromium.launch({headless:true,channel:'msedge',args:['--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage({viewport:{width:2000,height:1100}}),errors=[];page.on('pageerror',e=>errors.push(e.stack));await page.goto(ready.url);
  const evidence=await page.evaluate(async()=>{
   const T=await import('/assets/three.module.js'),{GLTFLoader}=await import('/assets/three-gltf.js'),{RoomEnvironment}=await import('/assets/three-room.js'),{crownGeometry,crownTexture}=await import('/assets/board3d-crowns.js');
   const gltf=await new GLTFLoader().loadAsync('/assets/staunton1849.glb'),sources={};gltf.scene.traverse(o=>{if(o.isMesh)sources[o.name]=o});
   const canvas=document.createElement('canvas');canvas.style='position:fixed;inset:0;width:100%;height:100%;z-index:100000';document.body.append(canvas);
   const renderer=new T.WebGLRenderer({canvas,antialias:true});renderer.setSize(innerWidth,innerHeight);renderer.outputColorSpace=T.SRGBColorSpace;renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05;renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFShadowMap;
   const scene=new T.Scene();scene.background=new T.Color(0x202933);const pmrem=new T.PMREMGenerator(renderer),room=new RoomEnvironment(),env=pmrem.fromScene(room,.04,.1,100);scene.environment=env.texture;scene.environmentIntensity=.65;room.dispose();pmrem.dispose();
   scene.add(new T.HemisphereLight(0xe4eeff,0x806950,1.25));const key=new T.DirectionalLight(0xfff1dc,2.4);key.position.set(-4,9,5);key.castShadow=true;key.shadow.mapSize.set(2048,2048);Object.assign(key.shadow.camera,{left:-3,right:3,top:3,bottom:-3,near:.1,far:24});key.shadow.bias=-.00025;key.shadow.normalBias=.015;scene.add(key);const fill=new T.DirectionalLight(0xe0eaff,1.3);fill.position.set(5,5,-4);scene.add(fill);
   const ink=crownTexture(),stampMaterial=new T.MeshStandardMaterial({map:ink,roughness:.72,transparent:true,alphaTest:.05,depthWrite:false,polygonOffset:true,polygonOffsetFactor:-2,polygonOffsetUnits:-2});
   const stampShapes={n:crownGeometry(sources.n,'n'),r:crownGeometry(sources.r,'r')};const evidence={};
   for(const [k,g] of Object.entries(stampShapes)){g.computeBoundingBox();evidence[k]={min:g.boundingBox.min.toArray(),max:g.boundingBox.max.toArray(),triangles:g.index.count/3};}
   const pieces=[];['n','r','n','r'].forEach((type,i)=>{
    const source=sources[type],m=source.clone();m.material=source.material.clone();m.material.color.set(i<2?0xffdfb0:0x302b26);m.material.roughness=i<2?.98:.88;m.material.clearcoat=.18;m.material.clearcoatRoughness=.34;m.material.normalScale.set(.35,.35);m.material.envMapIntensity=1;
    m.add(new T.Mesh(stampShapes[type],stampMaterial));m.position.set((i-1.5)*.83,0,0);m.rotateY(type==='n'?Math.PI/2:0);m.castShadow=m.receiveShadow=true;scene.add(m);pieces.push(m);
   });
   const floor=new T.Mesh(new T.PlaneGeometry(200,200),new T.MeshStandardMaterial({color:0x29343e,roughness:.95}));floor.rotation.x=-Math.PI/2;floor.position.y=-.005;floor.receiveShadow=true;scene.add(floor);
   const h=2.1,w=h*innerWidth/innerHeight,camera=new T.OrthographicCamera(-w/2,w/2,h/2,-h/2,.1,40);camera.position.set(0,4.7,6);camera.lookAt(0,.60,0);renderer.render(scene,camera);
   window.crownStudy={renderer,scene,camera,pieces};return evidence;
  });
  await page.screenshot({path:'media/staunton1849/review/crowns-1.2.9.png'});
  await page.evaluate(()=>{const q=crownStudy;q.pieces[0].rotateY(-Math.PI/3);q.pieces[2].rotateY(-Math.PI/3);q.renderer.render(q.scene,q.camera)});
  await page.screenshot({path:'media/staunton1849/review/crowns-profile-1.2.9.png'});
  assert.deepEqual(errors,[]);console.log(JSON.stringify(evidence));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
