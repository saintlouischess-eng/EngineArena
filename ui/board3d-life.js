import * as T from './three.module.js';
import {GLTFLoader} from './three-gltf.js';
import {mergeGeometries} from './three-geometry-utils.js';

let headPromise=null;
const loadHead=()=>headPromise??=new GLTFLoader().loadAsync('/assets/room-head.glb').then(g=>g.scene).catch(e=>{headPromise=null;throw e});

// Offline chess-room scenery. CC0 head attribution: vendor/MakeHuman. Its illustrative games never enter the
// tournament worker. Geometry/materials are pooled and constructed only on opt-in.
export function chessLife(scene,assets,own,mat,textures,renderer,changed){
 const root=new T.Group();root.name='Live chess environment';scene.add(root);
 const cache=new Map(),geos=new Map(),mats=new Map();let active=null,elapsed=0,previous=0,frozen=false,running=false,disposed=false,headModel=null;
 const waiting=loadHead().then(model=>{if(disposed)return false;headModel=model.clone(true);const copies=new Map();headModel.traverse(o=>{if(!o.isMesh)return;o.geometry=own(o.geometry.clone());o.material=mat(o.material.clone());if(o.material.map){const source=o.material.map;if(!copies.has(source)){const t=source.clone();textures.set(t,t);copies.set(source,t)}o.material.map=copies.get(source)}if(o.name==='hair'){o.material.transparent=false;o.material.alphaTest=.4;o.material.side=T.DoubleSide;o.material.roughness=.9}});changed();return true}).catch(e=>{if(!disposed){renderer.domElement.dataset.liveRoom='error';changed(e)}return false});
 // Batch static furniture by material; keep animation joints and pieces separate.
 function batch(group,deep=false){
  group.updateWorldMatrix(true,true);const buckets=new Map(),inverse=group.matrixWorld.clone().invert();
  function visit(o){if(o.userData.liveDynamic)return;if(o.isMesh&&!Array.isArray(o.material)){const g=o.geometry.clone();g.applyMatrix4(inverse.clone().multiply(o.matrixWorld));if(!buckets.has(o.material))buckets.set(o.material,[]);buckets.get(o.material).push({g,o})}if(deep)for(const child of o.children)visit(child)}
  for(const child of group.children)visit(child);
  for(const [m,items] of buckets){const g=mergeGeometries(items.map(x=>x.g));if(g){group.add(new T.Mesh(own(g),m));for(const item of items)item.o.removeFromParent()}for(const item of items)item.g.dispose()}
 }
 const floor=-13.48;
 const geo=(key,fn)=>{if(!geos.has(key))geos.set(key,own(fn()));return geos.get(key)};
 const material=(name,color,roughness=.75,metalness=0)=>{if(!mats.has(name))mats.set(name,mat(new T.MeshStandardMaterial({color,roughness,metalness})));return mats.get(name)};
 const woodColor=assets.wood.color.clone();woodColor.colorSpace=T.SRGBColorSpace;textures.set(woodColor,woodColor);
 const wood=mat(new T.MeshStandardMaterial({map:woodColor,normalMap:assets.wood.normal,roughnessMap:assets.wood.rough,color:0x75513a,roughness:.8,normalScale:new T.Vector2(.12,.12)}));
 const cream=material('ivory',0xdccb9a,.36),ebony=material('ebony',0x241d19,.34),brass=material('brass',0xb09152,.36,.65),iron=material('iron',0x242b2b,.55,.3),paper=material('paper',0xf0e6cd,.95);
 const unit=geo('box',()=>new T.BoxGeometry(1,1,1)),sphere=geo('sphere',()=>new T.SphereGeometry(1,20,16)),rod=geo('rod',()=>new T.CylinderGeometry(1,1,1,16));
 function mesh(parent,g,m,x=0,y=0,z=0,sx=1,sy=1,sz=1){const o=new T.Mesh(g,m);o.position.set(x,y,z);o.scale.set(sx,sy,sz);parent.add(o);return o}
 const box=(p,m,x,y,z,w,h,d)=>mesh(p,unit,m,x,y,z,w,h,d);
 const orb=(p,m,x,y,z,w,h,d)=>mesh(p,sphere,m,x,y,z,w,h,d);
 function link(p,a,b,r1,r2,m){const av=new T.Vector3(...a),bv=new T.Vector3(...b),v=bv.clone().sub(av),o=mesh(p,geo('link'+r1+':'+r2,()=>new T.CylinderGeometry(r2,r1,1,14)),m);o.position.copy(av.add(bv).multiplyScalar(.5));o.quaternion.setFromUnitVectors(new T.Vector3(0,1,0),v.clone().normalize());o.scale.y=v.length();return o}
 function canvasMap(key,w,h,draw){if(mats.has(key))return mats.get(key);const c=document.createElement('canvas');c.width=w;c.height=h;draw(c.getContext('2d'),w,h);const t=new T.CanvasTexture(c);t.colorSpace=T.SRGBColorSpace;t.anisotropy=4;textures.set(t,t);const m=mat(new T.MeshStandardMaterial({map:t,roughness:.85}));mats.set(key,m);return m}
 function sign(p,text,sub,x,y,z,w,h){
  const m=canvasMap('sign'+text,1024,256,(c,W,H)=>{c.fillStyle='#18332e';c.fillRect(0,0,W,H);c.strokeStyle='#b9a06d';c.lineWidth=3;c.strokeRect(12,12,W-24,H-24);c.textAlign='center';c.fillStyle='#eadcba';c.font='500 58px Georgia';c.fillText(text,W/2,116);c.font='23px sans-serif';c.fillStyle='#b2bfae';c.fillText(sub,W/2,183)});
  box(p,wood,x,y,z,w+.24,h+.24,.25);return box(p,m,x,y,z+.14,w,h,.015);
 }
 const score=canvasMap('scoresheet',256,384,(c,w,h)=>{c.fillStyle='#e7dfc9';c.fillRect(0,0,w,h);c.fillStyle='#313b32';c.font='bold 17px serif';c.fillText('ENGINE ARENA',21,29);c.font='11px serif';c.fillText('WHITE                     BLACK',21,55);c.strokeStyle='#8f9688';for(let y=73;y<h-10;y+=18){c.beginPath();c.moveTo(16,y);c.lineTo(w-16,y);c.stroke()}c.fillStyle='#354253';c.font='italic 11px serif';for(let i=0;i<12;i++)c.fillText(`${i+1}.   ${['e4','Nf3','Bb5','O-O'][i%4]}             ${['e5','Nc6','a6','Nf6'][i%4]}`,24,88+i*18)});
 // Procedural woven fabric: fine, irregular fibers instead of flat plastic.
 function fabric(name,color){if(mats.has(name))return mats.get(name);const c=document.createElement('canvas');c.width=c.height=128;const x=c.getContext('2d');x.fillStyle='#9e9e9e';x.fillRect(0,0,128,128);for(let y=0;y<128;y++)for(let z=0;z<128;z++){const n=135+((z*17+y*31)%39)+(z%3===0?22:0);x.fillStyle=`rgb(${n},${n},${n})`;x.fillRect(z,y,1,1)}const t=new T.CanvasTexture(c);t.wrapS=t.wrapT=T.RepeatWrapping;t.repeat.set(5,6);textures.set(t,t);const m=mat(new T.MeshStandardMaterial({color,roughness:.96,bumpMap:t,bumpScale:.025}));mats.set(name,m);return m}
 function lathe(key,points){return geo(key,()=>new T.LatheGeometry(points.map(([x,y])=>new T.Vector2(x,y)),20))}
 const profiles={p:[[0,0],[.34,0],[.37,.10],[.30,.19],[.19,.3],[.14,.62],[.22,.72],[.16,.78],[0,.78]],r:[[0,0],[.4,0],[.42,.12],[.29,.26],[.22,.4],[.24,1.1],[.4,1.2],[.4,1.43],[0,1.43]],b:[[0,0],[.4,0],[.43,.14],[.28,.3],[.17,.78],[.28,.97],[.26,1.08],[.14,1.18],[0,1.2]],n:[[0,0],[.4,0],[.41,.14],[.27,.3],[.22,.57],[0,.6]],q:[[0,0],[.44,0],[.46,.15],[.3,.3],[.18,.86],[.25,1.12],[.37,1.22],[.25,1.34],[.30,1.63],[0,1.65]],k:[[0,0],[.45,0],[.47,.16],[.31,.33],[.19,.94],[.28,1.2],[.4,1.3],[.24,1.4],[.31,1.63],[0,1.66]]};
 const pieceTemplates={};
 function piece(type,white){const key=type+(white?'w':'b');if(pieceTemplates[key])return pieceTemplates[key];const g=new T.Group(),m=white?cream:ebony;mesh(g,lathe('piece'+type,profiles[type]),m);
  if(type==='p')orb(g,m,0,.89,0,.23,.24,.23);
  if(type==='b'){const head=orb(g,m,0,1.36,0,.20,.32,.19);head.rotation.z=-.18;orb(g,m,0,1.72,0,.08,.08,.08)}
  if(type==='n'){const neck=orb(g,m,0,.99,0,.24,.54,.20);neck.rotation.x=-.26;const head=orb(g,m,0,1.43,.20,.23,.24,.40);head.rotation.x=-.15;for(const x of [-.13,.13]){const ear=mesh(g,geo('ear',()=>new T.ConeGeometry(.065,.24,8)),m,x,1.71,-.02);ear.rotation.x=-.2}orb(g,m,0,1.35,.46,.22,.14,.15)}
  if(type==='q'){for(let i=0;i<9;i++){const a=i*2*Math.PI/9;orb(g,m,.29*Math.cos(a),1.67,.29*Math.sin(a),.055,.10,.055)}orb(g,m,0,1.74,0,.13,.14,.13)}
  if(type==='k'){orb(g,m,0,1.73,0,.16,.14,.16);box(g,m,0,2,0,.10,.43,.10);box(g,m,0,2.04,0,.33,.10,.10)}
  if(type==='r')for(let i=0;i<6;i++){const a=i*Math.PI/3;const b=box(g,m,.32*Math.cos(a),1.5,.32*Math.sin(a),.20,.18,.20);b.rotation.y=-a}
  batch(g);pieceTemplates[key]=g;return g;
 }
 function shadow(parent,x,z,w,d,alpha=.23){const m=canvasMap('contact',128,128,(c,W,H)=>{const r=c.createRadialGradient(64,64,8,64,64,64);r.addColorStop(0,'rgba(0,0,0,.65)');r.addColorStop(1,'rgba(0,0,0,0)');c.fillStyle=r;c.fillRect(0,0,W,H)});if(!m.transparent){m.transparent=true;m.depthWrite=false;m.opacity=alpha}const o=mesh(parent,geo('plane',()=>new T.PlaneGeometry(1,1)),m,x,floor+.081,z,w,d,1);o.rotation.x=-Math.PI/2}
 function chair(parent,x,z,rotation){const g=new T.Group();g.position.set(x,floor,z);g.rotation.y=rotation;parent.add(g);const leather=material('chair leather',0x354039,.87);box(g,wood,0,7.6,0,6,.5,5.8);orb(g,leather,0,7.98,0,2.9,.35,2.8);for(const a of [-2.45,2.45])for(const b of [-2.3,2.3])box(g,wood,a,3.6,b,.34,7.2,.34);box(g,wood,0,11.2,-2.6,5.8,5.8,.42);orb(g,leather,0,11.2,-2.31,2.6,2.5,.28);shadow(parent,x,z,9,9);return g}
 const clockFace=canvasMap('clockface',512,160,(c,w,h)=>{c.fillStyle='#071713';c.fillRect(0,0,w,h);c.fillStyle='#c2dab3';c.font='60px monospace';c.fillText('05:32 05:17',12,89);c.font='18px sans-serif';c.fillText('BLITZ     + 3 SECONDS',102,135)});
 // A legal Ruy Lopez opening, looped only as clearly decorative background play.
 const line=['e2e4','e7e5','g1f3','b8c6','f1b5','a7a6','b5a4','g8f6','e1g1','f8e7','f1e1','b7b5','a4b3','d7d6','c2c3','e8g8','h2h3','c6b8','d2d4','b8d7'];
 function gameTable(parent,x,z,angle,index,kind){
  const g=new T.Group();g.position.set(x,0,z);g.rotation.y=angle;parent.add(g);const m=kind==='hall'?fabric('felt',0x275449):wood;
  const surface=box(g,m,0,-.6,0,14,.65,11);surface.receiveShadow=true;box(g,wood,0,-1.2,0,14.4,.35,11.4);
  for(const a of [-5.8,5.8])for(const b of [-4.2,4.2])box(g,wood,a,-7,b,.50,12,.50);
  const board=new T.Group();g.add(board);board.position.y=-.14;box(board,wood,0,0,0,7.4,.16,7.4);
  for(let r=0;r<8;r++)for(let f=0;f<8;f++){const s=.82;box(board,(f+r)%2?material('walnut squares',0x573a25):material('maple squares',0xd8c492),s*(f-3.5),.09,s*(r-3.5),s,.015,s)}
  const pieces=new T.Group();pieces.userData.liveDynamic=true;pieces.position.y=.115;board.add(pieces);const all=[],map={};
  for(const rank of [1,2,7,8])for(let f=0;f<8;f++){const type=rank===2||rank===7?'p':'rnbqkbnr'[f],p=piece(type,rank<3).clone();p.scale.setScalar(.59);p.rotation.y=rank<3?Math.PI:0;const sq='abcdefgh'[f]+rank;map[sq]=p;all.push({p,sq});pieces.add(p)}
  const coord=s=>new T.Vector3((s.charCodeAt(0)-100.5)*.82,0,(4.5-Number(s[1]))*.82);
  for(const {p,sq} of all)p.position.copy(coord(sq));
  const clock=new T.Group();g.add(clock);clock.position.set(0,.28,-4.05);box(clock,iron,0,0,0,3.7,.9,1.03);const face=box(clock,clockFace,0,.1,.524,3.4,.65,.025);for(const a of [-.9,.9])box(clock,brass,a,.52,0,.62,.12,.43);
  const sheet=box(g,score,5,-.245,0,2.0,.02,2.9);sheet.rotation.y=-.12;link(g,[4.2,-.19,1.7],[6,-.19,1.1],.035,.035,iron);
  const cup=mesh(g,geo('cup',()=>new T.CylinderGeometry(.39,.32,.62,20)),paper,-5,.14,-2.1);mesh(g,geo('tea',()=>new T.CircleGeometry(.34,20)),material('tea',0x372019),-5,.456,-2.1).rotation.x=-Math.PI/2;
  sign(g,String(index+1).padStart(2,'0'),'ENGINE ARENA',-5,.49,3.7,1.9,1.05);
  chair(g,0,-8.4,0);chair(g,0,8.4,Math.PI);shadow(g,0,0,21,18);
  let step=-1;function update(t,moving){const progress=((t+index*16)/10)%(line.length+5),next=Math.min(line.length,Math.floor(progress)),fraction=progress-Math.floor(progress);if(next!==step){step=next;for(const key of Object.keys(map))delete map[key];for(const {p,sq} of all){p.visible=true;p.position.copy(coord(sq));map[sq]=p}for(let i=0;i<next;i++){const u=line[i],a=u.slice(0,2),b=u.slice(2),p=map[a];if(map[b])map[b].visible=false;map[b]=p;delete map[a];p.position.copy(coord(b));if(u==='e1g1'||u==='e8g8'){const rank=u[1],r=map['h'+rank];delete map['h'+rank];map['f'+rank]=r;r.position.copy(coord('f'+rank))}}}
   if(moving&&next<line.length){const u=line[next],a=u.slice(0,2),b=u.slice(2),p=map[a],f=Math.min(1,Math.max(0,(fraction-.60)/.14)),ease=f*f*(3-2*f);p.position.lerpVectors(coord(a),coord(b),ease);p.position.y=Math.sin(f*Math.PI)*.45;if(f===1&&map[b])map[b].visible=false;if(u==='e1g1'||u==='e8g8'){const rank=u[1],rook=map['h'+rank];rook.position.lerpVectors(coord('h'+rank),coord('f'+rank),ease);rook.position.y=Math.sin(f*Math.PI)*.18}}
   return {side:next%2,phase:fraction,step:next};
  }
  return {g,update,index,players:[],scale:.82};
 }
 // Tailored background figures, with articulated shoulders/elbows, heads and
 // walking legs. Faces and cloth have volume; no photographic billboards.
 function person(parent,index,seated=true){
  const g=new T.Group();g.userData.liveDynamic=true;parent.add(g);const skins=[0xbf9680,0x92705b,0xd7b39a,0x655244,0xae8169],shirts=[0x394a57,0x947759,0x445c4e,0x776075,0xb9b3a0,0x48434d],skin=material('skin'+index%5,skins[index%5],.82),cloth=fabric('shirt'+index%6,shirts[index%6]),pants=fabric('trousers',0x303536),hair=material('hair'+index%3,[0x30261e,0x898176,0x4b3022][index%3],.97),shoe=material('shoes',0x262321,.62);
  const hip=seated?8.65:16.3,torso=new T.Group();torso.position.y=hip;g.add(torso);
  // Shaped torso taper, a seam and folded collar keep clothing from reading as capsules.
  const body=lathe('torso',[[0,0],[1.8,0],[2.03,.8],[2.16,3.3],[2.5,5.8],[2.1,7.1],[1.35,7.7],[0,7.7]]);mesh(torso,body,cloth,0,0,0,1,1,.59);
  link(torso,[0,1,1.16],[0,6.95,1.16],.022,.022,material('seam',0x868782));for(let i=0;i<4;i++)orb(torso,brass,0,2+i*1.1,1.21,.055,.055,.028);
  const neck=mesh(torso,rod,skin,0,7.8,0,.69,1.7,.63),head=new T.Group();head.position.set(0,9.5,.1);torso.add(head);
  const face=headModel.clone(true);face.scale.setScalar(.85);head.add(face);face.traverse(o=>{if(!o.isMesh)return;if(o.name==='head'){o.material=mat(o.material.clone());o.material.color.set([0xfff0e4,0xbba08b,0xfff3e5,0x8b7467,0xdebea6][index%5]);o.material.roughness=.83}if(o.name==='hair'||o.name==='scalp'){o.material=mat(o.material.clone());o.material.color.set([0x504232,0x9d9587,0x4b3026][index%3])}});
  for(const side of [-1,1]){const collar=box(torso,cloth,side*.67,7.21,.97,1,.22,1.1);collar.rotation.z=side*.32}
  if(index%3===1){const glasses=material('glasses',0x433c32,.4,.6);for(const s of [-1,1]){const ring=mesh(head,geo('glasses',()=>new T.TorusGeometry(.32,.027,6,24)),glasses,s*.51,.13,1.85);ring.scale.y=.7}link(head,[-.20,.13,1.86],[.20,.13,1.86],.024,.024,glasses)}
  const arms=[];
  for(const s of [-1,1]){
   const arm=new T.Group();arm.position.set(s*2.1,6.5,0);torso.add(arm);orb(arm,cloth,0,-.15,0,.67,.8,.62);link(arm,[0,0,0],[0,-4.25,0],.62,.52,cloth);
   const fore=new T.Group();fore.position.y=-4.25;arm.add(fore);orb(fore,cloth,0,0,0,.54,.6,.52);link(fore,[0,0,0],[0,-3.45,0],.47,.36,cloth);orb(fore,skin,0,-3.83,.08,.39,.70,.30);for(let j=0;j<4;j++)orb(fore,skin,-.23+j*.15,-4.32,.16,.075,.28,.075);arms.push({arm,fore});
   arm.rotation.x=seated?-.43:.08;arm.rotation.z=s*.08;fore.rotation.x=seated?-1.1:-.15;
  }
  const legs=[];
  for(const s of [-1,1]){const upper=new T.Group();upper.position.set(s*1.06,hip,0);g.add(upper);link(upper,[0,0,0],[0,-7.7,0],.97,.66,pants);const lower=new T.Group();lower.position.y=-7.7;upper.add(lower);link(lower,[0,0,0],[0,-7.5,0],.66,.45,pants);orb(lower,shoe,0,-7.62,.72,.62,.49,1.24);if(seated){upper.rotation.x=-1.48;lower.rotation.x=1.48}legs.push({upper,lower})}
  g.position.y=floor;const seed=index*1.93;
  function pose(t,action=null){const breath=Math.sin(t*.9+seed)*.023;torso.scale.y=1+breath*.28;torso.rotation.x=seated?.10+breath:.012*Math.sin(t*.38+seed);head.rotation.y=.07*Math.sin(t*.26+seed);head.rotation.x=seated?.21+.045*Math.sin(t*.41+seed):.03;
   const reach=action?Math.sin(Math.PI*Math.max(0,Math.min(1,(action.phase-.37)/.5))):0;
   arms[1].arm.rotation.x=seated?-.43-reach*.38:.04+Math.sin(t*2.4+seed)*.24;arms[1].fore.rotation.x=seated?-1.1-reach*.28:-.2;
   arms[0].arm.rotation.x=seated?-.43:.04-Math.sin(t*2.4+seed)*.24;
   if(!seated)for(let i=0;i<2;i++){legs[i].upper.rotation.x=Math.sin(t*2.4+seed+i*Math.PI)*.26;legs[i].lower.rotation.x=Math.max(0,-Math.sin(t*2.4+seed+i*Math.PI))*.35}
  }
  for(const joint of [head,...arms.flatMap(a=>[a.fore,a.arm]),torso,...legs.flatMap(a=>[a.lower,a.upper]),g])batch(joint);
  return {g,pose,head};
 }
 function analysisBoard(parent,x,z,angle){const g=new T.Group();g.position.set(x,0,z);g.rotation.y=angle;parent.add(g);const boardTexture=canvasMap('analysisboard',1024,1200,(c,w,h)=>{c.fillStyle='#203c32';c.fillRect(0,0,w,h);c.fillStyle='#dfd3ad';c.font='50px Georgia';c.textAlign='center';c.fillText('ANALYSIS CORNER',512,78);const map=ArenaScene3D.placement('r1bqk2r/1pppbppp/p1n2n2/4p3/B3P3/5N2/PPPP1PPP/RNBQ1RK1 w kq - 4 6');for(let r=0;r<8;r++)for(let f=0;f<8;f++){const X=72+f*110,Y=128+r*110;c.fillStyle=(r+f)%2?'#738c77':'#e2ddc5';c.fillRect(X,Y,110,110);const p=map['abcdefgh'[f]+(8-r)];if(p){c.font='82px "Segoe UI Symbol"';c.textBaseline='middle';c.fillStyle=p===p.toUpperCase()?'#fff4d6':'#171f1b';c.strokeStyle=p===p.toUpperCase()?'#354137':'#d2c9b0';c.lineWidth=2;const icon={p:'♟',n:'♞',b:'♝',r:'♜',q:'♛',k:'♚'}[p.toLowerCase()];c.strokeText(icon,X+55,Y+60);c.fillText(icon,X+55,Y+60)}}c.textBaseline='alphabetic';c.fillStyle='#e5d6b2';c.font='30px Georgia';c.fillText('Ruy López  ·  Open analysis',512,1080)});
  box(g,wood,0,7,0,13,15.2,.55);box(g,boardTexture,0,7,.29,12.5,14.65,.015);for(const a of [-4.5,4.5])link(g,[a,floor,0],[a,6,0],.13,.13,iron);link(g,[-5,floor+.4,0],[5,floor+.4,0],.2,.2,iron);shadow(g,0,0,15,7);
 }
 function bookshelf(parent,x,z,rotation){const g=new T.Group();g.position.set(x,0,z);g.rotation.y=rotation;parent.add(g);box(g,wood,0,-4,-1.4,12,19,.5);for(const y of [-13,-8,-3,2,7]){box(g,wood,0,y,0,12,.35,3.5);if(y<7)for(let i=0;i<11;i++){const book=box(g,material('book'+i,[0x424d3f,0x683d33,0x38495a,0x9b7c48][i%4]),-5+i, y+2.05,0,.68,3.6+(i%3)*.23,2.7);book.rotation.z=(i%5===0?.06:0);box(book,brass,0,-.23,.503,.75,.015,.012)}}for(const a of [-6,6])box(g,wood,a,-3,0,.4,20,3.5);shadow(g,0,0,18,7)}
 function build(kind){const group=new T.Group();root.add(group);const data={group,tables:[],people:[],lamps:[],leaves:[]};
  // A modeled floor grounds chairs/feet rather than projecting them onto furniture
  // in the panorama. The photographic room remains visible beyond the club area.
  const floorMap=assets.wood.color.clone();floorMap.colorSpace=T.SRGBColorSpace;floorMap.wrapS=floorMap.wrapT=T.RepeatWrapping;floorMap.repeat.set(11,14);textures.set(floorMap,floorMap);
  const floorMat=mat(new T.MeshStandardMaterial({map:floorMap,color:kind==='hall'?0x716655:kind==='studio'?0x67594e:0x887965,roughness:.98}));
  box(group,floorMat,0,floor+.02,-56,154,.10,185);
  const carpet=fabric('rug '+kind,{club:0x3d4c3d,hall:0x303e4a,study:0x70624e,studio:0x3b4547}[kind]);box(group,carpet,0,floor+.09,-6,42,.018,40);
  const layouts={club:[[-30,-40,.3],[32,-44,-.35],[-12,-72,.12]],hall:[[-31,-38,.1],[31,-38,-.1],[-29,-70,.05],[29,-70,-.05],[0,-97,0]],study:[[-32,-42,.28]],studio:[[-32,-43,.2],[34,-55,-.3]]};
  for(const [i,[x,z,a]] of layouts[kind].entries()){const table=gameTable(group,x,z,a,i,kind);data.tables.push(table);for(let side=0;side<2;side++){const actor=person(table.g,i*2+side+(kind==='study'?3:0));actor.g.position.z=side?8.3:-8.3;actor.g.rotation.y=side?Math.PI:0;table.players.push(actor);data.people.push(actor)}}
  if(kind==='club'){analysisBoard(group,27,-76,-.2);bookshelf(group,-48,-47,.5);sign(group,'ENGINE ARENA CHESS CLUB','PLAY  ·  ANALYZE  ·  DISCOVER',0,9,-91,23,5.75)}
  if(kind==='hall'){sign(group,'ENGINE ARENA CHAMPIONSHIP','ROUND IN PROGRESS',0,13,-120,34,8.5);analysisBoard(group,49,-54,-.5);for(const x of [-13,13])for(const z of [-26,-46]){mesh(group,rod,brass,x,-8,z,.17,11,.17);orb(group,brass,x,-2.4,z,.35,.35,.35);mesh(group,rod,iron,x,floor+.2,z,1.15,.4,1.15)}}
  if(kind==='study'){analysisBoard(group,29,-49,-.35);bookshelf(group,-49,-43,.6);sign(group,'THE ANALYSIS ROOM','IDEAS OVER THE BOARD',0,9,-78,23,5.75)}
  if(kind==='studio'){analysisBoard(group,0,-64,0);sign(group,'ENGINE ARENA LIVE','CHESS  ·  IDEAS  ·  ANALYSIS',0,19,-70,23,5.75)}
  // Spectator stays beyond the playing table and never crosses the user's view of pieces.
  const walker=person(group,8,false);walker.g.position.set(-35,floor,-35);data.people.push(walker);data.walker=walker;
  for(const side of [-1,1]){const g=new T.Group();group.add(g);g.position.set(side*43,floor,-30);mesh(g,geo('planter',()=>new T.CylinderGeometry(2.5,1.65,4,28)),material('planter',0x5c6558),0,2,0);const green=material('leaf',0x344f36,.89);for(let n=0;n<9;n++){const a=n*2.4,y=4+n*.75;link(g,[0,3,0],[Math.cos(a)*2,y,Math.sin(a)*2],.075,.035,green);const leaf=orb(g,green,Math.cos(a)*2.5,y,Math.sin(a)*2.5,.58,.09,1.5);leaf.rotation.set(.15,a,.3);leaf.userData.liveDynamic=true;data.leaves.push({leaf,base:leaf.rotation.z,phase:n+side})}
   const lamp=new T.Group();group.add(lamp);lamp.position.set(side*43,0,-63);mesh(lamp,rod,brass,0,-4,0,.16,19,.16);mesh(lamp,rod,iron,0,floor+.3,0,2.1,.6,2.1);const shade=mat(new T.MeshStandardMaterial({color:0xe4c692,emissive:0xdba960,emissiveIntensity:.15,roughness:.9,side:T.DoubleSide}));mesh(lamp,geo('shade',()=>new T.CylinderGeometry(1.5,2.9,3.4,32,1,true)),shade,0,6.7,0);data.lamps.push(shade);
  }
  batch(group,true);group.traverse(o=>{if(o.isMesh){o.castShadow=false;o.receiveShadow=false}});cache.set(kind,data);return data;
 }
 return {
  update(p,animate=true,now=performance.now()){
   root.visible=p.live&&!!headModel;root.rotation.y=p.roomRotation*Math.PI/180;running=p.live&&(p.people||p.backgroundGames||p.atmosphere)&&!frozen&&animate;
   if(!p.live||!headModel){running=false;previous=0;renderer.domElement.dataset.liveRoom=p.live?'loading':'off';renderer.domElement.dataset.roomPeople='0';return}
   const delta=previous?Math.min(.25,Math.max(0,now-previous)/1000):0;previous=now;if(running)elapsed+=delta;
   active=cache.get(p.environment)||build(p.environment);for(const d of cache.values())d.group.visible=d===active;
   const amount={quiet:1,social:2,busy:99}[p.activity],speed={quiet:.55,social:.8,busy:1.05}[p.activity],t=elapsed*speed;
   active.tables.forEach((table,i)=>{const playing=p.backgroundGames&&i<amount,turn=table.update(playing?t:20,playing);table.players.forEach((person,side)=>{person.g.visible=p.people&&i<amount;person.pose(p.people?t:0,playing&&turn.side===side?turn:null)})});
   const w=active.walker;w.g.visible=p.people&&p.activity==='busy';if(w.g.visible){const phase=t/42;w.g.position.set(Math.sin(phase+.7)*35,floor,-90+Math.cos(phase+.7)*6);w.g.rotation.y=Math.atan2(35*Math.cos(phase+.7),-6*Math.sin(phase+.7));w.pose(t)}
   active.leaves.forEach(({leaf,base,phase})=>leaf.rotation.z=base+(p.atmosphere?Math.sin(t*.37+phase)*.025:0));active.lamps.forEach((m,i)=>m.emissiveIntensity=.16+(p.atmosphere?Math.sin(t*.13+i)*.025:0));
   Object.assign(renderer.domElement.dataset,{liveRoom:p.environment,roomPeople:String(active.people.filter(x=>x.g.visible).length),roomTables:String(active.tables.length),roomSeconds:elapsed.toFixed(3),roomActivity:p.activity});
  },ready:()=>waiting,needsFrame:()=>running,pause(){previous=0},freeze(value){frozen=value;previous=0},dispose(){disposed=true;scene.remove(root);cache.clear()},
 };
}
