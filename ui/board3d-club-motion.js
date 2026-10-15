// Deterministic choreography for decorative games only. Never reads/writes game APIs.
import * as T from './three.module.js';

export const clubMoves=['e2e4','e7e5','g1f3','b8c6','f1b5','a7a6','b5a4','g8f6','e1g1','f8e7','f1e1','b7b5','a4b3','d7d6','c2c3','e8g8'];
const smooth=x=>{x=T.MathUtils.clamp(x,0,1);return T.MathUtils.clamp(x*x*x*(10+x*(-15+6*x)),0,1)};
const ramp=(t,a,b)=>smooth((t-a)/(b-a));
const v=(x=0,y=0,z=0)=>new T.Vector3(x,y,z);
const square=s=>v(s.charCodeAt(0)-100.5,.008,4.5-Number(s[1]));
const blend=(a,b,t,arc=0)=>{const p=a.clone().lerp(b,smooth(t));p.y+=Math.sin(Math.PI*T.MathUtils.clamp(t,0,1))**2*arc;return p};
const world=o=>o.getWorldPosition(v());
export const clubCastNames=['arthur','mei','daniel','elena','jonas','nora','magnus','fabiano','hans','bobby','hikaru','levy'];

// Smooth, reproducible variation per person/hand. Never use frame-rate-dependent
// random walks: paused/reduced-motion rooms remain still, with no pose drift.
export function clubIdle(t,identity=0,hand=0){
 const hash=n=>{let x=Math.imul((n+1)^Math.imul(identity+3,19349663)^Math.imul(hand+5,83492791),73856093);x^=x>>>13;return (x>>>0)/4294967295};
 const noise=(period,salt)=>{const x=t/period+salt,k=Math.floor(x);return T.MathUtils.lerp(hash(k+salt*97),hash(k+1+salt*97),smooth(x-k))*2-1};
 const pulse=(1+Math.sin(t/(2.7+(identity%4)*.31)+identity*2.13+hand*1.7))*.5;
 return {x:noise(5.7,2)*.20,z:noise(7.9,7)*.28,lift:Math.max(0,noise(8.3,3))*.06,
  curl:.035+pulse*.10,spread:noise(4.8,5)*.028,arm:noise(9.1,1)*.055,head:noise(6.3,4)*.035};
}

// glTF BLEND materials disable depth writes. Changing only transparent=false
// leaves camera-near hair overwritten by the scalp in the opaque render pass.
export function prepareClubCharacter(g){
 g.traverse(o=>{if(o.isMesh){o.frustumCulled=false;for(const m of [o.material].flat())if(m?.name.startsWith('Hair')){
  const cutout=m.transparent||m.alphaTest>0;m.transparent=false;m.depthWrite=true;m.depthTest=true;
  m.alphaTest=cutout?.35:0;m.side=T.DoubleSide;m.needsUpdate=true;
 }}});
}

// A shuffled eight-person visitor roster, shared by both arrival routes. Adjacent
// arrivals always have different identities, including across cycle wraps.
export function clubGuestSchedule(seed=1){
 const order=Array.from({length:clubCastNames.length-4},(_,i)=>i);let state=seed>>>0;
 for(let i=order.length-1;i>0;i--){state=(Math.imul(state,1664525)+1013904223)>>>0;const j=state%(i+1);[order[i],order[j]]=[order[j],order[i]]}
 return t=>[0,1].map(slot=>{const cycle=Math.floor((Math.max(0,t)+(slot?180:0))/260),arrival=slot?cycle*2-1:cycle*2;return {slot,guest:order[((arrival%order.length)+order.length)%order.length]}});
}
export function clubGuests(models,floor,seed=Math.floor(Math.random()*0x100000000),library=null){
 const schedule=clubGuestSchedule(seed),controllers=models.map((g,i)=>[clubVisitor(g,0,floor,i,library),clubVisitor(g,1,floor,i,library)]);
 return {update(t,enabled=true){library?.reset();models.forEach(g=>g.visible=false);let door=0;const visitors=[];for(const {slot,guest} of schedule(t)){const d=controllers[guest][slot].update(t,enabled);door=Math.max(door,d.door);visitors.push({...d,guest:clubCastNames[guest+4]})}return {door,visitors}}};
}

// Absolute-time phases are reversible and deterministic for pause, screenshots
// and reduced motion. A visitor never leaves with a book or snaps it to a shelf.
export function clubReading(t,duration){
 const end=duration-8,take=ramp(t,4,7),put=ramp(t,end+2,end+5),held=take*(1-put);
 const open=ramp(t,7,9)*(1-ramp(t,end,end+2));
 const phase=t<2?'choose':t<4?'reach':t<7?'take':t<9?'open':t<end?'read':t<end+2?'close':t<end+5?'replace':'release';
 const turn=(t-11)/3.2,page=turn>0&&turn<1?smooth(turn):0;
 return {phase,held,open,page,stepL:ramp(t,4.2,6.2)*(1-ramp(t,end+2,end+4)),stepR:ramp(t,5.1,7.1)*(1-ramp(t,end+3,end+5)),right:ramp(t,2,4)*(1-ramp(t,end+5,end+7)),left:ramp(t,5,7)*(1-ramp(t,end+1,end+3))};
}

// Computer-local civil time, including the system's timezone/DST. This is a
// visual day/night cycle, not a geolocated sunrise or live-weather service.
export function clubTime(date=new Date()){
 const seconds=date.getSeconds(),minutes=date.getMinutes()+seconds/60,hours=date.getHours()+minutes/60;
 const day=ramp(hours,6,8)*(1-ramp(hours,18,20)),twilight=Math.sin(Math.PI*day);
 return {hours,day,twilight,second:-seconds*Math.PI/30,minute:-minutes*Math.PI/30,hour:-(hours%12)*Math.PI/6,local:date.toLocaleTimeString()};
}

// The two players play an opening and then go back through it as an analysis
// exercise. Every piece is returned by hand; the board never teleports/reset-jumps.
export function clubGame(all,index=0,clock=null){
 const map={},records=[],steps=[];let total=0;
 for(const p of all)map[p.square]=p;
 clubMoves.forEach((move,ply)=>{
  const transfers=[[move.slice(0,2),move.slice(2)]];
  if(move==='e1g1'||move==='e8g8')transfers.push(['h'+move[1],'f'+move[1]]);
  const actions=transfers.map(([a,b])=>{const p=map[a];delete map[a];map[b]=p;return {piece:p,from:square(a),to:square(b)}});
  records.push({actions,side:ply%2,ply});
 });
 const add=(r,review)=>{const think=(review?2.6:6.3)+((r.ply*13+index*7)%11)*.47;
  const actions=review?[...r.actions].reverse().map(a=>({...a,from:a.to,to:a.from})):r.actions;
  const duration=think+actions.length*3.2+3.7;
  steps.push({...r,actions,review,think,start:total,duration});total+=duration;
 };
 records.forEach(r=>add(r,false));[...records].reverse().forEach(r=>add(r,true));
 let last=-1,cycle=-1,current=null;
 const reset=()=>{for(const p of all)p.o.position.copy(square(p.square))};
 const offset=index?19.7:0;
 return {
  steps,total,
  update(seconds,playing=true){
   const raw=Math.max(0,seconds+offset),n=Math.floor(raw/total),t=raw%total;
   const k=steps.findIndex(s=>t<s.start+s.duration),s=steps[k],local=t-s.start;
   if(k!==last||cycle!==n){reset();for(let j=0;j<k;j++)for(const a of steps[j].actions)a.piece.o.position.copy(a.to);last=k;cycle=n}
   const side=s.side? -1:1,home=v(4.8,-.24,side*2.5),aTime=local-s.think;
   let hand=home.clone(),grip=0,stage='think',piece=null;
   const gripPoint=(a,p)=>p.clone().add(v(0,a.piece.height*.79,0));
   for(let j=0;j<s.actions.length;j++){
    const a=s.actions[j],u=aTime-j*3.2;
    a.piece.o.position.copy(u<1.15?a.from:u<2.6?blend(a.from,a.to,(u-1.15)/1.45,.8):a.to);
    if(u>=0&&u<3.2){
     const begin=j?gripPoint(s.actions[j-1],s.actions[j-1].to).add(v(0,.45,0)):home;
     const contact=gripPoint(a,a.piece.o.position);piece=a.piece.o;
     if(u<.9){stage='reach';hand=blend(begin,gripPoint(a,a.from),u/.9,.55)}
     else if(u<1.15){stage='grasp';hand=contact;grip=ramp(u,.9,1.15)}
     else if(u<2.6){stage='carry';hand=contact;grip=1}
     else if(u<2.85){stage='release';hand=contact;grip=1-ramp(u,2.6,2.85)}
     else {stage='clear';hand=contact.add(v(0,.45*ramp(u,2.85,3.2),0))}
    }
   }
   const end=s.actions.length*3.2,lastAction=s.actions.at(-1),placed=gripPoint(lastAction,lastAction.to).add(v(0,.45,0)),button=v(8.50,.87,side);
   if(aTime>=end){const u=aTime-end;
    if(s.review){stage='withdraw';hand=blend(placed,home,u/1.5,.55)}
    else if(u<1.15){stage='clock-reach';hand=blend(placed,button.clone().add(v(0,.35,0)),u/1.15,.25)}
    else if(u<1.6){stage='clock';hand=button.clone().add(v(0,.35*(1-Math.sin(Math.PI*(u-1.15)/.45)),0))}
    else {stage='withdraw';hand=blend(button.clone().add(v(0,.35,0)),home,(u-1.6)/1.5,.55)}
   }
   const engaged=ramp(local,s.think-1.6,s.think+.25)*(1-ramp(aTime,end+2,end+3.7));
   current={side:s.side,hand,home,grip,engaged,stage,piece,review:s.review,ply:s.ply,time:seconds};
   if(clock){const switched=aTime>=end+1.375,active=playing&&!s.review?(switched?1-s.side:s.side):null,data={};
    for(const [i,name] of ['white','black'].entries()){const used=Math.floor((s.ply+(i===0?1:0))/2)*12+(active===i?Math.max(0,local):0),left=Math.max(0,300-used);data[name]={text:Math.floor(left/60)+':'+String(Math.floor(left%60)).padStart(2,'0'),active:active===i,mode:s.review?'REVIEW':'DEMO'}}clock.set(data);
   }
   return current;
  },state:()=>current
 };
}

// Preserve the sculpted split/twist bones. Rotate two anatomical joints, never
// stretch the mesh or pull a hand away from its arm to reach a chess piece.
function rigPose(g){
 const bones={},rest=[];g.traverse(o=>{if(o.isBone){bones[o.name]=o;rest.push({o,q:o.quaternion.clone(),p:o.position.clone()})}});
 function reset(){for(const r of rest){r.o.quaternion.copy(r.q);r.o.position.copy(r.p)}g.updateWorldMatrix(true,true)}
 function rotate(b,axis,angle){if(!b)return;const q=b.getWorldQuaternion(new T.Quaternion()).premultiply(new T.Quaternion().setFromAxisAngle(axis,angle));b.quaternion.copy(b.parent.getWorldQuaternion(new T.Quaternion()).invert().multiply(q));b.updateWorldMatrix(false,true)}
 function aim(b,end,target){const a=world(b),from=world(end).sub(a),to=target.clone().sub(a);if(from.lengthSq()<1e-9||to.lengthSq()<1e-9)return;const q=b.getWorldQuaternion(new T.Quaternion()).premultiply(new T.Quaternion().setFromUnitVectors(from.normalize(),to.normalize()));b.quaternion.copy(b.parent.getWorldQuaternion(new T.Quaternion()).invert().multiply(q));b.updateWorldMatrix(false,true)}
 function limb(upper,lower,tip,target,pole,hinged=false,minElbowY=-Infinity,bounds=[]){
  const a=world(upper),b=world(lower),c=world(tip),l1=a.distanceTo(b),l2=b.distanceTo(c),d=target.clone().sub(a),len=Math.min(l1+l2-.025,Math.max(Math.abs(l1-l2)+.025,d.length()));d.normalize();
  const bend=pole.clone().sub(a);bend.addScaledVector(d,-bend.dot(d)).normalize();
  const along=(len*len+l1*l1-l2*l2)/(2*len),height=Math.sqrt(Math.max(0,l1*l1-along*along));
  const center=a.clone().addScaledVector(d,along);
  const planes=Number.isFinite(minElbowY)?[...bounds,{normal:v(0,1,0),min:minElbowY}]:bounds;
  if(planes.length&&height>1e-6){
   // The valid elbow locations form a circle around the shoulder/wrist axis.
   // Choose its nearest anatomically valid point without changing bone length
   // or losing hand contact. A pole alone cannot keep a leaning player's elbow
   // out of the torso and in front of the back at the same time.
   const tangent=d.clone().cross(bend).normalize(),rules=planes.map(p=>({a:p.normal.dot(bend)*height,b:p.normal.dot(tangent)*height,c:p.min-p.normal.dot(center)}));
   const candidates=[0];for(const r of rules){const length=Math.hypot(r.a,r.b);if(length>1e-8&&Math.abs(r.c)<=length){const phase=Math.atan2(r.b,r.a),arc=Math.acos(T.MathUtils.clamp(r.c/length,-1,1));candidates.push(phase-arc,phase+arc)}}
   let best=0,bestCost=Infinity;
   for(const angle of candidates){const c=Math.cos(angle),s=Math.sin(angle),violation=rules.reduce((sum,r)=>sum+Math.max(0,r.c-r.a*c-r.b*s)**2,0),cost=violation*1e6+Math.abs(Math.atan2(s,c));if(cost<bestCost){bestCost=cost;best=angle}}
   bend.multiplyScalar(Math.cos(best)).addScaledVector(tangent,Math.sin(best));
  }
  const elbow=center.addScaledVector(bend,height);
  const end=a.clone().addScaledVector(d,len),normal=elbow.clone().sub(a).cross(end.clone().sub(elbow)).normalize();
  const hinge=(bone,next)=>{const along=world(next).sub(world(bone)).normalize(),x=v(1,0,0).applyQuaternion(bone.getWorldQuaternion(new T.Quaternion()));x.addScaledVector(along,-x.dot(along)).normalize();const n=normal.clone().addScaledVector(along,-normal.dot(along)).normalize();if(x.dot(n)<0)n.negate();rotate(bone,along,Math.atan2(along.dot(x.clone().cross(n)),x.dot(n)))};
  aim(upper,lower,elbow);if(hinged)hinge(upper,lower);
  aim(lower,tip,end);if(hinged)hinge(lower,tip);
  return {elbow,elbowError:world(lower).distanceTo(elbow)};
 }
 return {bones,reset,rotate,aim,limb};
}

export function clubPlayer(g,table,index){
 const rig=rigPose(g),{bones:b,reset,rotate,limb,aim}=rig,side=index%2?-1:1,seed=index*2.37;
 const tableQ=()=>table.getWorldQuaternion(new T.Quaternion()),point=p=>table.localToWorld(p.clone()),axis=(x,y,z)=>v(x,y,z).applyQuaternion(tableQ());
 const hands={},seatedFeet={};g.updateWorldMatrix(true,true);
 for(const name of ['L','R']){
  const wrist=b['wrist'+name],forward=world(b['finger3-1'+name]).sub(world(wrist)).normalize(),q=wrist.getWorldQuaternion(new T.Quaternion()).invert();
  const across=world(b['finger2-1'+name]).sub(world(b['finger5-1'+name]));across.addScaledVector(forward,-across.dot(forward)).normalize();
  forward.applyQuaternion(q);across.applyQuaternion(q);
  hands[name]={rest:wrist.quaternion.clone(),shoulder:table.worldToLocal(world(b['upperarm01'+name])),frame:new T.Quaternion().setFromRotationMatrix(new T.Matrix4().makeBasis(across,forward.clone().cross(across),forward)).invert()};
  const hip=table.worldToLocal(world(b['upperleg01'+name]));
  seatedFeet[name]={hip,foot:v(hip.x+(name==='R'?side:-side)*.18,-11.8,side*(5.2+(index%2)*.25))};
 }
 const diagnostics={};
 function arm(name,contact,grip,weight,press=false,idle=null){
  const wrist=b['wrist'+name],upper=b['upperarm01'+name],lower=b['lowerarm01'+name];
  // Fingers rest together in a loose natural arc, rather than a spread fan.
  const middle=world(b['finger3-2'+name]).sub(world(b['finger3-1'+name])).normalize();
  for(const f of [2,4,5]){const base=b[`finger${f}-1${name}`],next=b[`finger${f}-2${name}`],dir=world(next).sub(world(base)).normalize().lerp(middle,.65).normalize();aim(base,next,world(base).add(dir))}
  for(let f=1;f<=5;f++)for(let joint=1;joint<=3;joint++){const bone=b[`finger${f}-${joint}${name}`];if(bone){bone.rotateX((f===1?.08:f===2?.23:.38)*grip+(idle?idle.curl*(1-weight)*(f===1?.15:.55+f*.1)*(joint===1?.45:1):0));if(joint===1&&idle)bone.rotateZ(idle.spread*(f-3)*(1-weight))}}
  wrist.updateWorldMatrix(true,true);
  // Broad, palm-down grasp, with the fingertips meeting the piece from above.
  const tilt=.02+weight*.32,desired=axis(0,-tilt,-side*Math.sqrt(1-tilt*tilt)),across=axis(name==='R'?-side:side,0,0);
  let q=new T.Quaternion().setFromRotationMatrix(new T.Matrix4().makeBasis(across,desired.clone().cross(across),desired)).multiply(hands[name].frame);
  wrist.quaternion.copy(wrist.parent.getWorldQuaternion(new T.Quaternion()).invert().multiply(q));wrist.updateWorldMatrix(false,true);
  if(grip>0){
   const thumb=world(b['finger1-3'+name]),indexTip=world(b['finger2-3'+name]),center=thumb.clone().lerp(indexTip,.5),apart=thumb.clone().sub(indexTip).normalize();
   for(const [f,sign,start] of [[1,1,thumb],[2,-1,indexTip]]){
    const end=center.clone().addScaledVector(apart,sign*.19),pole=world(b[`finger${f}-2${name}`]);
    limb(b[`finger${f}-1${name}`],b[`finger${f}-2${name}`],b[`finger${f}-3${name}`],start.lerp(end,grip),pole);
   }
  }
  const fingertip=()=>b['finger3-3'+name].localToWorld(v(0,.38,0));
  const anchor=()=>press?world(b['finger2-3'+name]):world(b['finger1-3'+name]).lerp(world(b['finger2-3'+name]),.5).lerp(fingertip(),1-weight);
  // Guide the elbow outward from its actual shoulder. A low fixed point near
  // the table edge can lie inside the shoulder-to-wrist line, folding an arm
  // through the torso or behind the back as the player leans.
  const shoulder=table.worldToLocal(world(upper)),outward=Math.sign(hands[name].shoulder.x);
  const pole=point(shoulder.clone().add(v(outward*2.6,-6,side*.4)));
  const shoulderWorld=world(upper),forwardLimit=axis(0,0,-side),lateralLimit=axis(outward,0,0);
  const limits=[{normal:forwardLimit,min:shoulderWorld.dot(forwardLimit)-2.0-weight*6},
   {normal:lateralLimit,min:shoulderWorld.dot(lateralLimit)-.25-weight*6},
   {normal:v(0,-1,0),min:-shoulderWorld.y+.45-weight*6}];
  // Solve contact and wrist direction together. Fixing every hand straight
  // toward the board made sideways reaches and resting wrists look fractured.
  // Fingers follow the forearm with modest flexion, instead of a right angle.
  let elbowSolution;for(let pass=0;pass<5;pass++){
   const offset=anchor().sub(world(wrist)),target=point(contact).sub(offset);
   elbowSolution=limb(upper,lower,wrist,target,pole,true,point(v(0,-4.0+weight*4.15,0)).y,limits);
   if(pass<4){const forward=world(wrist).sub(world(lower)).normalize(),up=axis(0,1,0);forward.addScaledVector(up,-.25).normalize().lerp(axis((name==='R'?-side:side)*.12,-.06,-side),1-weight).normalize();const cross=up.cross(forward).normalize().multiplyScalar(name==='R'?1:-1);q=new T.Quaternion().setFromRotationMatrix(new T.Matrix4().makeBasis(cross,forward.clone().cross(cross),forward)).multiply(hands[name].frame)}
   wrist.quaternion.copy(wrist.parent.getWorldQuaternion(new T.Quaternion()).invert().multiply(q));wrist.updateWorldMatrix(false,true);
  }
  // Spread forearm pronation over its two twist bones. A full palm-down turn
  // at the wrist alone collapses the skin and makes the joint look broken.
  const forearm=world(wrist).sub(world(lower)).normalize(),current=wrist.parent.getWorldQuaternion(new T.Quaternion()).multiply(hands[name].rest),delta=q.clone().multiply(current.invert());
  const projected=forearm.x*delta.x+forearm.y*delta.y+forearm.z*delta.z;
  let twist=2*Math.atan2(projected,delta.w);twist=Math.atan2(Math.sin(twist),Math.cos(twist));
  rotate(lower,forearm,twist*.50);rotate(b['lowerarm02'+name],forearm,twist*.45);
  // IK changes the wrist parent frame; keep the chosen hand orientation.
  wrist.quaternion.copy(wrist.parent.getWorldQuaternion(new T.Quaternion()).invert().multiply(q));wrist.updateWorldMatrix(false,true);
  const actual=press?world(b['finger2-3'+name]):world(b['finger1-3'+name]).lerp(world(b['finger2-3'+name]),.5).lerp(fingertip(),1-weight);
  const elbow=table.worldToLocal(world(lower)),wristPoint=table.worldToLocal(world(wrist));
  const fingers=world(b['finger3-1'+name]).sub(world(wrist)).normalize();
  diagnostics[name]={error:actual.distanceTo(point(contact)),elbowError:elbowSolution.elbowError,elbowGoal:table.worldToLocal(elbowSolution.elbow.clone()).toArray(),contact:contact.toArray(),actual:table.worldToLocal(actual).toArray(),shoulder:shoulder.toArray(),elbow:elbow.toArray(),wrist:wristPoint.toArray(),fingersTowardBoard:fingers.dot(axis(0,0,-side)),weight,lengths:[world(upper).distanceTo(world(lower)),world(lower).distanceTo(world(wrist))]};
 }
 return {diagnostics,update(t,state,play=true){
  reset();const acting=play&&state?.side===index%2,amount=acting?state.engaged:0;
  const breath=Math.sin(t*1.12+seed)*.007,shift=Math.sin(t*.23+seed)*.017;
  const clock=acting&&state.stage.startsWith('clock'),reach=acting?state.hand:null;
  // The lean follows reach distance and keeps hips and feet planted.
  const reachLean=reach?.42*ramp(10.5-side*reach.z,5.5,13.2):0;
  const lean=.12+amount*reachLean;
  rotate(b.spine05,axis(1,0,0),-side*(lean+breath));
  rotate(b.spine05,axis(0,0,1),amount*(reach?-T.MathUtils.clamp(reach.x*.030,-.18,.25):0));
  rotate(b.spine03,axis(1,0,0),-side*(.06+amount*.06));
  rotate(b.spine02,axis(0,1,0),shift+amount*(reach?T.MathUtils.clamp((reach.x-side*3)*.045,-.24,.24):0));
  rotate(b.neck01,axis(1,0,0),side*(lean*.48-.14));
  rotate(b.head,axis(0,1,0),Math.sin(t*.19+seed)*.045+amount*(reach?T.MathUtils.clamp(reach.x*.032,-.18,.18):0));
  rotate(b.head,axis(0,0,1),Math.sin(t*.17+seed)*.018);
  for(const name of ['L','R']){
   const use=acting&&name===(side===1?'R':'L');
   const idle=clubIdle(t,index,name==='R'?1:0),weight=use?amount:0;
   const resting=v((name==='R'?side:-side)*4.8,-.24,side*2.5);
   // Both resting hands follow the full shoulder travel. Half-following during
   // a deep lean put the wrist behind its shoulder and forced the elbow back.
   const travel=table.worldToLocal(world(b['upperarm01'+name])).sub(hands[name].shoulder);
   resting.x+=travel.x;resting.z+=travel.z;resting.y+=amount*.28;
   // Blend out of the same anatomical rest on either turn; do not jump to a
   // different fixed hand position merely because it became this player's move.
   if(use)resting.lerp(state.hand,weight);
   resting.add(v(idle.x,idle.lift,idle.z).multiplyScalar(1-weight));
   arm(name,resting,use?state.grip:0,weight,use&&clock,idle);
  }
  // Correct the seated rest's low ankles and retain full foot contact.
  diagnostics.legs={};
  for(const name of ['L','R']){const foot=b['foot'+name],q=foot.getWorldQuaternion(new T.Quaternion()),seat=seatedFeet[name];
   limb(b['upperleg01'+name],b['lowerleg01'+name],foot,point(seat.foot),point(v(seat.hip.x,-5.6,side*3.8)));
   foot.quaternion.copy(foot.parent.getWorldQuaternion(new T.Quaternion()).invert().multiply(q));foot.updateWorldMatrix(false,true);
   diagnostics.legs[name]={hip:table.worldToLocal(world(b['upperleg01'+name])).toArray(),knee:table.worldToLocal(world(b['lowerleg01'+name])).toArray(),foot:table.worldToLocal(world(foot)).toArray()};
  }
  diagnostics.stage=acting?state.stage:'watch';diagnostics.side=side;
 }};
}

// Two independent, curved walking routes. Stops are deliberate: watching a
// board or studying the wall diagram, with arrival/exit concealed by the vestibule.
export function clubVisitor(g,index,floor,style=0,library=null){
 const rig=rigPose(g),{bones:b,reset,rotate,limb,aim}=rig;
 const paths=index===0?[
  {points:[[22,-113],[22,-100],[21,-85],[10,-70],[11,-49]],seconds:17},
  {at:[11,-49],look:[29,-47],seconds:37,activity:'watch'},
  {points:[[11,-49],[7,-41],[1,-34],[-12,-34]],seconds:8},
  {at:[-12,-34],look:[-29,-42],seconds:31,activity:'watch'},
  {points:[[-12,-34],[-7,-52],[1,-70],[8,-80]],seconds:11},
  {at:[8,-80],look:[0,-95],seconds:19,activity:'study'},
  {points:[[8,-80],[18,-86],[22,-99],[22,-113]],seconds:10}
 ]:[
  {points:[[22,-113],[22,-100],[20,-86],[0,-78],[-13,-57]],seconds:18},
  {at:[-13,-57],look:[-29,-42],seconds:46,activity:'watch'},
  {points:[[-13,-57],[-17,-69],[-30,-79],[-38,-83]],seconds:9},
  {at:[-38,-83],look:[-38,-91],seconds:28,activity:'browse'},
  {points:[[-38,-83],[-20,-80],[-5,-83],[18,-88],[22,-100],[22,-113]],seconds:17}
 ];
 // A stroll needs an ordinary cadence. The old very slow translation combined
 // with a long stride looked like a rigid slow-motion march.
 for(const [i,p] of paths.entries())if(p.points){const saved=p.seconds*.44;p.seconds-=saved;if(paths[i+1])paths[i+1].seconds+=saved;p.curve=new T.CatmullRomCurve3(p.points.map(([x,z])=>v(x,0,z)),false,'centripetal');p.length=p.curve.getLength()}
 const total=paths.reduce((a,p)=>a+p.seconds,0),period=260,offset=index?180:0;
 const feet={},hands={};g.updateWorldMatrix(true,true);for(const name of ['L','R']){
  const foot=b['foot'+name],position=g.worldToLocal(world(foot));position.x=(name==='L'?1:-1)*1.10;
  feet[name]={p:position,q:foot.getWorldQuaternion(new T.Quaternion()).premultiply(g.getWorldQuaternion(new T.Quaternion()).invert())};
  const wrist=b['wrist'+name],forward=world(b['finger3-1'+name]).sub(world(wrist)).normalize(),across=world(b['finger2-1'+name]).sub(world(b['finger5-1'+name]));across.addScaledVector(forward,-across.dot(forward)).normalize();const inverse=wrist.getWorldQuaternion(new T.Quaternion()).invert();forward.applyQuaternion(inverse);across.applyQuaternion(inverse);
  hands[name]={rest:wrist.quaternion.clone(),frame:new T.Quaternion().setFromRotationMatrix(new T.Matrix4().makeBasis(across,forward.clone().cross(across),forward)).invert()};
 }
 function relaxHand(name,front,idle){
  const middle=world(b['finger3-2'+name]).sub(world(b['finger3-1'+name])).normalize();
  for(const f of [2,4,5]){const base=b[`finger${f}-1${name}`],next=b[`finger${f}-2${name}`],direction=world(next).sub(world(base)).normalize().lerp(middle,.78).normalize();aim(base,next,world(base).add(direction))}
  for(let f=1;f<=5;f++)for(let j=1;j<=3;j++){const finger=b[`finger${f}-${j}${name}`];if(!finger)continue;finger.rotateX((f===1?.015:j===1?.12:.27)+idle.curl*(f===1?.20:.35+f*.12));if(j===1)finger.rotateZ(idle.spread*(f-3))}
  const wrist=b['wrist'+name],lower=b['lowerarm01'+name],forward=world(wrist).sub(world(lower)).normalize(),across=front.clone().addScaledVector(forward,-front.dot(forward)).normalize();
  const q=new T.Quaternion().setFromRotationMatrix(new T.Matrix4().makeBasis(across,forward.clone().cross(across),forward)).multiply(hands[name].frame);
  const natural=wrist.parent.getWorldQuaternion(new T.Quaternion()).multiply(hands[name].rest),delta=q.clone().multiply(natural.invert());
  let twist=2*Math.atan2(forward.x*delta.x+forward.y*delta.y+forward.z*delta.z,delta.w);twist=Math.atan2(Math.sin(twist),Math.cos(twist));
  rotate(lower,forward,twist*.45);rotate(b['lowerarm02'+name],forward,twist*.45);
  wrist.quaternion.copy(wrist.parent.getWorldQuaternion(new T.Quaternion()).invert().multiply(q));wrist.updateWorldMatrix(false,true);
 }
 let diagnostics={};
 // Constant walking speed between a gentle start and stop, not a repeated
 // stop/start at every waypoint. Distance also drives the planted-foot gait.
 function distance(u){const a=.10;if(u<a)return u*u/(2*a*(1-a));if(u>1-a)return 1-(1-u)**2/(2*a*(1-a));return (u-a/2)/(1-a)}
 return {diagnostics,update(t,enabled=true){
  const time=(t+offset)%period;g.visible=enabled&&time<total;if(!g.visible)return Object.assign(diagnostics,{visible:false,door:0});
  let local=time,j=0;while(local>=paths[j].seconds){local-=paths[j].seconds;j++}
  const p=paths[j],u=local/p.seconds,walking=!!p.curve,progress=walking?distance(u):0,pos=walking?p.curve.getPointAt(progress):v(p.at[0],0,p.at[1]);
  const tangent=walking?p.curve.getTangentAt(progress):v(p.look[0]-pos.x,0,p.look[1]-pos.z).normalize();
  // Turn toward the game after stopping and toward the aisle before departing.
  let angle=Math.atan2(tangent.x,tangent.z);
  if(!walking){const prev=paths[j-1].curve.getTangentAt(1),next=paths[j+1].curve.getTangentAt(0),a0=Math.atan2(prev.x,prev.z),a1=Math.atan2(next.x,next.z),turn=(a,b,f)=>a+Math.atan2(Math.sin(b-a),Math.cos(b-a))*f;angle=turn(a0,angle,ramp(local,0,1.5));angle=turn(angle,a1,ramp(local,p.seconds-1.5,p.seconds))}
  const readState=!walking&&p.activity==='browse'&&library?clubReading(local,p.seconds):null,stepMean=readState?(readState.stepL+readState.stepR)*.5:0;
  g.position.set(pos.x-Math.sin(angle)*1.35*stepMean,floor,pos.z-Math.cos(angle)*1.35*stepMean);g.rotation.y=angle;reset();
  const worldQ=g.getWorldQuaternion(new T.Quaternion()),ax=v(1,0,0).applyQuaternion(worldQ),az=v(0,0,1).applyQuaternion(worldQ),ay=v(0,1,0).applyQuaternion(worldQ);
  const stride=(index?10.1:11.0)+(style%3)*.35,travelled=walking?progress*p.length:0,cycleAngle=travelled/stride*Math.PI*2,gait=Math.sin(cycleAngle),pace=walking?ramp(u,0,.12)*(1-ramp(u,.88,1)):0;
  // Move the pelvis over the supporting leg, soften the knees and transfer
  // weight twice per stride. Foot targets below remain in room coordinates.
  const sway=(walking?.27*gait*pace:.13*Math.sin(t*.47+index));
  const bob=-.12+pace*(-.62-.08*Math.cos(cycleAngle*2));
  const shift=ax.clone().multiplyScalar(sway).add(v(0,bob,0));
  b.root.position.add(shift.applyQuaternion(b.root.parent.getWorldQuaternion(new T.Quaternion()).invert()));b.root.updateWorldMatrix(false,true);
  rotate(b.root,ay,gait*.055*pace);rotate(b.root,az,-gait*.021*pace);
  const personal=clubIdle(t,style+4,index),gaze=walking?.035: .13;
  rotate(b.spine05,az,walking?gait*.039*pace:.012*Math.sin(t*.6+index));
  rotate(b.spine03,ay,-gait*.095*pace);rotate(b.spine03,ax,walking?.05*pace:.055);rotate(b.head,ay,Math.sin(t*.23+index*4)*gaze);rotate(b.neck01,ax,walking?.025:p.activity==='watch'?.19:.03);
  if(readState){const reach=readState.right*(1-readState.held);rotate(b.spine05,ax,.22*reach);rotate(b.spine03,ax,.10*reach);rotate(b.neck01,ax,-.08*reach)}
  const footStats={};
  for(const [name,sign] of [['L',1],['R',-1]]){
   rotate(b['upperarm01'+name],ax,-Math.sin(cycleAngle+.16)*sign*.31*pace);rotate(b['upperarm01'+name],az,-sign*.035*pace);
   rotate(b['lowerarm01'+name],ax,-.13-Math.max(0,gait*sign)*.22*pace+personal.arm*(1-pace));rotate(b['wrist'+name],ax,.035*Math.sin(cycleAngle+.4)*sign*pace);
   const neutral=g.localToWorld(feet[name].p.clone()),foot=b['foot'+name];let target=neutral.clone();
   if(readState){const step=readState['step'+name];target.addScaledVector(az,-1.35*(step-stepMean));target.y+=Math.sin(Math.PI*step)**2*.48}
   let roll=0,phase=0;
   if(walking){
    const shift=name==='L'?0:.5,cycle=travelled/stride+shift,k=Math.floor(cycle);phase=cycle-k;
    const sample=d=>{const f=T.MathUtils.clamp(d/p.length,0,1),c=p.curve.getPointAt(f),dir=p.curve.getTangentAt(f);c.add(v(dir.z,0,-dir.x).multiplyScalar(feet[name].p.x));c.y=floor+feet[name].p.y;return c};
    // Stance is a fixed room-space anchor; only the swing foot lifts/advances.
    const anchor=(k-shift)*stride+stride*.25;
    if(phase<.6){target=sample(anchor);const heel=1-ramp(phase,0,.12),toe=ramp(phase,.40,.60);roll=(-.15*heel+.27*toe)*pace;target.y+=(.10*heel+.55*toe)*pace}
    else {const swing=(phase-.6)/.4;target=blend(sample(anchor),sample(anchor+stride),swing,1.15);roll=(.27*(1-ramp(swing,0,.28))-.15*ramp(swing,.68,1))*pace;target.y+=(.55*(1-ramp(swing,0,.28))+.10*ramp(swing,.68,1))*pace}
    target.lerp(neutral,1-pace);
   }
   const pole=g.localToWorld(v(feet[name].p.x,8,6));limb(b['upperleg01'+name],b['lowerleg01'+name],foot,target,pole);
   const footQ=worldQ.clone().multiply(feet[name].q).premultiply(new T.Quaternion().setFromAxisAngle(ax,roll));foot.quaternion.copy(foot.parent.getWorldQuaternion(new T.Quaternion()).invert().multiply(footQ));foot.updateWorldMatrix(false,true);
   footStats[name]={phase,roll,error:world(foot).distanceTo(target),target:target.toArray()};
  }
  if(!walking&&p.activity!=='browse'){
   // Distinct relaxed watching habits, eased in/out. Keep hands outside the
   // clothing silhouette; small weight shifts do not slide the planted feet.
   const hold=ramp(local,1.2,3)*(1-ramp(local,p.seconds-3,p.seconds-1)),left=(style+index)%2===1,name=left?'L':'R',wrist=b['wrist'+name],sign=left?1:-1;
   const rest=world(wrist),target=g.localToWorld(v(sign*(2.9+personal.x),14.0+(style%3)*.6+personal.lift,2.2+(style%4)*.32+personal.z));
   limb(b['upperarm01'+name],b['lowerarm01'+name],wrist,rest.lerp(target,hold),g.localToWorld(v(sign*5.3,18,1.0)),true);
   rotate(b.head,ax,Math.sin(t*.51+index)*.018);
  }
  // Door moves before the visitor crosses the threshold; the closer brings
  // it gently back when the person has cleared the opening.
  const door=ramp(pos.z,-111,-103)*(1-ramp(pos.z,-91,-83));
  if(walking&&pos.z< -91&&pos.z> -104){const reach=Math.sin(Math.PI*T.MathUtils.clamp((pos.z+104)/13,0,1))*.35;rotate(b.upperarm01R,ax,-reach);rotate(b.lowerarm01R,ax,-reach*.5)}
  const handStats={};for(const name of ['L','R']){
   relaxHand(name,az,clubIdle(t,style+4,name==='R'?1:0));
   const fingers=world(b['finger3-1'+name]).sub(world(b['wrist'+name])).normalize(),thumbSide=world(b['finger2-1'+name]).sub(world(b['finger5-1'+name])).normalize();
   const palm=fingers.clone().cross(thumbSide).normalize().multiplyScalar(name==='R'?-1:1);
   handStats[name]={thumbForward:thumbSide.dot(az),palmTowardLeg:palm.dot(ax.clone().multiplyScalar(name==='R'?1:-1))};
  }
  let reading=null;
  if(!walking&&p.activity==='browse'&&library?.books.length){
   const state=readState,cycle=Math.floor((t+offset)/period),choice=((Math.imul((cycle+1)^Math.imul(style+5,19349663),73856093))>>>0)%library.books.length,book=library.books[choice];
   const home=g.parent.localToWorld(book.home.clone()),held=g.localToWorld(v(personal.x*.25,21.2+personal.lift,4.0));
   const lead=g.worldToLocal(home.clone()).x>=0?'L':'R';
   const normal=az.clone().multiplyScalar(.60).addScaledVector(ay,-.80).normalize(),right=ax.clone(),up=normal.clone().cross(right).normalize();
   const readQ=new T.Quaternion().setFromRotationMatrix(new T.Matrix4().makeBasis(right,up,normal)),shelfQ=g.parent.getWorldQuaternion(new T.Quaternion()).multiply(book.rotation);
   const pos=blend(home,held,state.held,.30),orientation=shelfQ.clone().slerp(readQ,smooth(state.held));
   library.pose(choice,pos,orientation,state.open,state.page);
   rotate(b.neck01,ax,.35*state.held);rotate(b.head,ax,.18*state.held);rotate(b.head,ay,Math.sin(local*.72)*.035*state.open);
   const contacts={};
   for(const name of ['L','R']){
    const weight=name===lead?state.right:state.left,wrist=b['wrist'+name],upper=b['upperarm01'+name],lower=b['lowerarm01'+name];
    if(weight===0)continue;
    const sign=name==='L'?1:-1;
    const handPoint=v(sign*(book.width/2+Math.sin(state.open*1.30)*1.78),-.75,-Math.cos(state.open*1.30)*1.78*state.open+.12);
    if(name==='R'&&state.page>0){const a=-1.30+state.page*2.60,tip=v(-Math.sin(a)*2.32,.1,-Math.cos(a)*2.32);handPoint.lerp(tip,Math.sin(Math.PI*state.page)**2)}
    const contact=book.root.localToWorld(handPoint);
    // Fingers wrap the cover. Palm and wrist follow the book's orientation,
    // while elbow and upper arm retain their real, unscaled bone lengths.
    const forward=v(0,1,0).applyQuaternion(orientation),across=v(name==='R'?1:-1,0,0).applyQuaternion(orientation);
    const q=new T.Quaternion().setFromRotationMatrix(new T.Matrix4().makeBasis(across,forward.clone().cross(across),forward)).multiply(hands[name].frame);
    const restQ=wrist.getWorldQuaternion(new T.Quaternion()),desired=restQ.clone().slerp(q,weight);
    const anchor=()=>world(b['finger2-2'+name]).lerp(world(b['finger5-2'+name]),.5),destination=anchor().lerp(contact,weight);
    for(let pass=0;pass<5;pass++){
     wrist.quaternion.copy(wrist.parent.getWorldQuaternion(new T.Quaternion()).invert().multiply(desired));wrist.updateWorldMatrix(false,true);
     const offset=anchor().sub(world(wrist));limb(upper,lower,wrist,destination.clone().sub(offset),g.localToWorld(v(name==='L'?4.7:-4.7,15,2)),true);
    }
    wrist.quaternion.copy(wrist.parent.getWorldQuaternion(new T.Quaternion()).invert().multiply(desired));wrist.updateWorldMatrix(false,true);
    contacts[name]={weight,error:anchor().distanceTo(contact)};
   }
   reading={...state,choice,contacts,position:pos.toArray(),home:home.toArray()};
  }
  return Object.assign(diagnostics,{visible:true,door,activity:walking?'walk':p.activity,position:g.position.toArray(),phase:u,pace,feet:footStats,hands:handStats,reading,stepWidth:Math.abs(feet.L.p.x-feet.R.p.x),pelvisSway:sway});
 }};
}
