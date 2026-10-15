const test=require('node:test'),assert=require('node:assert/strict');
async function fixture(){const T=await import('../ui/three.module.js'),M=await import('../ui/board3d-club-motion.js');const pieces=[];for(const rank of [1,2,7,8])for(const file of 'abcdefgh')pieces.push({square:file+rank,height:2,o:new T.Object3D()});let clock;const game=M.clubGame(pieces,0,{set:v=>clock=v});return {T,M,pieces,game,clock:()=>clock}}
test('Reading takes a book, opens and turns a page, closes and replaces it before leaving',async()=>{
 const {M}=await fixture(),phases=new Set();let maxOpen=0,turned=false;
 for(const duration of [28,31.96,35]){
  for(let t=0;t<=duration;t+=.025){const a=M.clubReading(t,duration),b=M.clubReading(t+.00001,duration);phases.add(a.phase);maxOpen=Math.max(maxOpen,a.open);turned||=a.page>.9;
   for(const k of ['held','open','right','left']){assert(a[k]>=0&&a[k]<=1);assert(Math.abs(a[k]-b[k])<.0001)}
   if(a.open>0)assert.equal(a.held,1,'Only open a fully retrieved book');
   assert.deepEqual(a,M.clubReading(t,duration),'Freeze and seek must not drift');
  }
  for(const t of [0,duration]){const a=M.clubReading(t,duration);assert.equal(a.held,0);assert.equal(a.open,0);assert.equal(a.right,0);assert.equal(a.left,0)}
 }
 assert.equal(maxOpen,1);assert(turned);assert.deepEqual([...phases],['choose','reach','take','open','read','close','replace','release']);
});
test('Idle gestures differ by person and hand, remain smooth and freeze at fixed room time',async()=>{
 const {M}=await fixture(),poses=new Set();
 for(let id=0;id<12;id++)for(let hand=0;hand<2;hand++){
  let changed=false;
  for(let t=0;t<100;t+=.5){const a=M.clubIdle(t,id,hand),b=M.clubIdle(t+.0001,id,hand);assert.deepEqual(a,M.clubIdle(t,id,hand));for(const k in a){assert(Number.isFinite(a[k]));assert(Math.abs(a[k]-b[k])<.001)}assert(Math.abs(a.x)<=.20&&Math.abs(a.z)<=.28&&a.lift>=0&&a.lift<=.06);if(t>0&&a.curl!==M.clubIdle(0,id,hand).curl)changed=true}
  assert(changed);poses.add(JSON.stringify(M.clubIdle(12,id,hand)));
 }
 assert.equal(poses.size,24);
});
test('Imported hair cutouts occlude the scalp from either side and preparation is idempotent',async()=>{
 const {T,M}=await fixture(),g=new T.Group(),cutout=new T.MeshStandardMaterial({name:'Hair cards',transparent:true,depthWrite:false}),solid=new T.MeshStandardMaterial({name:'Hair curls'}),skin=new T.MeshStandardMaterial({name:'Skin'});
 g.add(new T.Mesh(new T.BoxGeometry(),[cutout,solid,skin]));
 for(let i=0;i<2;i++){M.prepareClubCharacter(g);assert.equal(cutout.transparent,false);assert.equal(cutout.depthWrite,true);assert.equal(cutout.depthTest,true);assert.equal(cutout.alphaTest,.35);assert.equal(cutout.side,T.DoubleSide);assert.equal(solid.alphaTest,0);assert.equal(skin.side,T.FrontSide)}
});
test('Decorative pieces are carried, placed and clocked; castling uses two separate transfers',async()=>{
 const {game,pieces,clock}=await fixture();for(const s of game.steps.filter(s=>!s.review)){
  for(let j=0;j<s.actions.length;j++){
   const a=s.actions[j],t=s.start+s.think+j*3.2;
   game.update(t+.8);assert(a.piece.o.position.distanceTo(a.from)<1e-9,'Piece stays on square before grasp');
   const holding=game.update(t+1.8);assert.equal(holding.stage,'carry');assert.equal(holding.grip,1);assert(a.piece.o.position.y>.4);
   assert.equal(holding.hand.x,a.piece.o.position.x);assert.equal(holding.hand.z,a.piece.o.position.z);
   game.update(t+2.7);assert(a.piece.o.position.distanceTo(a.to)<1e-9,'Put piece down before releasing');
  }
  const end=s.start+s.think+s.actions.length*3.2;
  game.update(end+1.2);assert(clock()[s.side?'black':'white'].active);
  game.update(end+1.5);assert(clock()[s.side?'white':'black'].active);
 }
 assert.equal(game.steps.filter(s=>!s.review&&s.actions.length===2).length,2);
 game.update(game.total-.001);const before=pieces.map(p=>p.o.position.clone());game.update(game.total+.001);pieces.forEach((p,i)=>assert(p.o.position.distanceTo(before[i])<1e-5,'No board reset teleport'));
});
test('Hand and piece trajectories stay continuous across action and move boundaries',async()=>{
 const {game}=await fixture();for(const s of game.steps){for(const a of [0,s.think,...s.actions.flatMap((_,j)=>[.9,1.15,2.6,2.85,3.2].map(x=>s.think+j*3.2+x)),s.duration-.001]){
  const t=s.start+a;if(t<=0)continue;const l=game.update(t-.00001),r=game.update(t+.00001);
  if(l.side===r.side)assert(l.hand.distanceTo(r.hand)<.002,`Hand discontinuity at ${t}: ${l.stage}/${r.stage}`);
 }}
});
test('Wall clock uses local civil time and day/night follows local hours',async()=>{
 const {M}=await fixture(),at=(h,m=0,s=0)=>M.clubTime(new Date(2026,9,11,h,m,s));
 assert(Math.abs(at(0).hour)<1e-10);assert(Math.abs(at(12).hour)<1e-10);assert.equal(at(12).day,1);assert.equal(at(23).day,0);
 assert(Math.abs(at(3,30).hour+7*Math.PI/12)<1e-10);assert(Math.abs(at(3,30).minute+Math.PI)<1e-10);assert(Math.abs(at(0,0,15).second+Math.PI/2)<1e-10);
 assert(at(7).day>0&&at(7).day<1);assert(at(19).day>0&&at(19).day<1);
 for(const hour of [6,8,18,20])assert(Math.abs(at(hour,0,1).day-at(hour,0,0).day)<.001);
});

test('Visitor rotation covers all eight identities without duplicates or visible swaps',async()=>{
 const {M}=await fixture();const orders=new Set();for(const seed of [1,421,927,0xffffffff]){
  const schedule=M.clubGuestSchedule(seed),seen=new Set();let arrivals=[];
  for(let k=0;k<21;k++){const a=schedule(k*260+25)[0],b=schedule(k*260+105)[1];seen.add(a.guest);seen.add(b.guest);arrivals.push(a.guest,b.guest);assert.notEqual(a.guest,b.guest);
   for(const t of [0,9,30,64,95,120])assert.equal(schedule(k*260+t)[0].guest,a.guest,'No identity change during a visit');
  }
  assert.equal(seen.size,8);for(let i=1;i<arrivals.length;i++)assert.notEqual(arrivals[i],arrivals[i-1]);orders.add(arrivals.slice(0,7).join(','));
 }
 assert(orders.size>1,'Launch seed changes the visitor order');
});
