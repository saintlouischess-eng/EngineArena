'use strict';
// Pure display rules: never changes game state, clocks, or engine commands.
const ArenaScene3D=(()=>{
 const clamp=(n,a,b,f)=>Number.isFinite(Number(n))?Math.max(a,Math.min(b,Number(n))):f;
 const one=(v,all,f)=>all.includes(v)?v:f;
 function settings(p={}){return {
  board:one(p.board,['classic','drueke','jaques'],'classic'),coordinates:p.coordinates!==false,
  roomRotation:clamp(p.roomRotation,-180,180,0),environment:one(p.environment,['club','hall','study','studio','live-club'],'club'),surface:one(p.surface,['wood','felt','leather'],'wood'),
  lighting:one(p.lighting,['daylight','evening','tournament'],'tournament'),brightness:clamp(p.brightness,.6,1.4,1),warmth:clamp(p.warmth,-1,1,0),
  quality:one(p.quality,['low','balanced','high'],'balanced'),mode:one(p.mode,['testing','presentation'],'testing'),
  // Both workspaces normalize saved preferences here, including legacy 60 FPS.
  motion:one(p.motion,['instant','quick','smooth'],'quick'),tour:one(p.tour,['cinematic','orbit','views'],'cinematic'),tourSpeed:clamp(p.tourSpeed,.5,1.5,1),fps:one(Number(p.fps),[15,30],30),
  trays:p.trays===true,plates:p.plates!==false,plaque:p.plaque!==false,highlight:clamp(p.highlight,.2,.6,.38),
  localTime:p.localTime!==false,live:p.live===true,activity:one(p.activity,['quiet','social','busy'],'social'),people:p.people!==false,backgroundGames:p.backgroundGames!==false,atmosphere:p.atmosphere!==false,
  ambience:p.ambience===true,ambienceVolume:clamp(p.ambienceVolume,0,50,15),
  roomMotion:one(p.roomMotion,['system','animate','still'],'system'),
 }}
 function roomMotionEnabled(p={},reduced=false){const mode=settings(p).roomMotion;return mode==='animate'||(mode==='system'&&!reduced)}
 const views={low:{angle:8,orbit:25,zoom:1,lift:0,tilt:6},room:{angle:16,orbit:-30,zoom:.68,lift:-.1},detail:{angle:28,orbit:35,zoom:1.25,lift:0},white:{angle:40,orbit:0,zoom:.92,lift:0},black:{angle:40,orbit:180,zoom:.92,lift:0},overhead:{angle:78,orbit:0,zoom:.88,lift:0},broadcast:{angle:48,orbit:28,zoom:.88,lift:0}};
 // Continuous Catmull-Rom dolly/crane path: no holds or direction snaps at shots.
 // Orbit is unwrapped during interpolation and normalized only at the end.
 function tourCamera(seconds,base,mode='cinematic',saved=[]){
  const b={angle:50,orbit:0,zoom:1,lift:0,tilt:0,...base},wrap=n=>((n+180)%360+360)%360-180;
  if(mode==='orbit')return {...b,orbit:wrap(b.orbit+seconds*2)};
  const cinematic=[[38,0,.88,0],[18,42,.88,-.07],[45,91,.90,0],[68,143,.91,-.015],[38,186,.88,.02],[26,228,1.06,0],[51,281,.9,0],[65,326,.90,-.01]].map(([angle,orbit,zoom,lift])=>({angle,orbit,zoom,lift}));
  const points=mode==='views'&&saved.length>1?saved:cinematic,n=points.length,phase=Math.max(0,seconds)/24,i=Math.floor(phase),t=phase-i;
  const at=k=>points[(k%n+n)%n],cat=(a,b,c,d)=>.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t),out={};
  for(const key of ['angle','zoom','lift','tilt'])out[key]=cat(...[-1,0,1,2].map(d=>at(i+d)[key]||0));
  const center=at(i).orbit||0,a=center+wrap((at(i-1).orbit||0)-center),c=center+wrap((at(i+1).orbit||0)-center),d=c+wrap((at(i+2).orbit||0)-(at(i+1).orbit||0));
  out.orbit=cat(a,center,c,d)+(mode==='views'&&saved.length>1?0:b.orbit);
  const f=Math.min(1,seconds/7),ease=f*f*f*(10+f*(-15+6*f));
  for(const k of ['angle','zoom','lift','tilt'])out[k]=b[k]+(out[k]-b[k])*ease;
  out.orbit=wrap(b.orbit+wrap(out.orbit-b.orbit)*ease);
  out.tilt=clamp(out.tilt,-30,70,0);out.angle=clamp(out.angle,6,78,50);out.zoom=clamp(out.zoom,.6,2.4,1);out.lift=clamp(out.lift,-.5,.5,0);return out;
 }
 function placement(fen){const map={};let rank=8,file=0;for(const c of (fen||'').split(' ')[0]){if(c==='/'){rank--;file=0}else if(/[1-8]/.test(c))file+=Number(c);else{map['abcdefgh'[file]+rank]=c;file++}}return map}
 const xyz=s=>[s.charCodeAt(0)-100.5,8-Number(s[1])-3.5];
 function transition(before,after,uci){
  const a=placement(before),b=placement(after),from=uci?.slice(0,2),to=uci?.slice(2,4),moved=a[from];
  const old=(before||'').split(' '),next=(after||'').split(' ');
  if(!moved||old[1]===next[1]||Number(next[5])!==Number(old[5])+(old[1]==='b'?1:0))return null;
  const changed=[...new Set([...Object.keys(a),...Object.keys(b)])].filter(s=>a[s]!==b[s]);
  if(changed.length<2||changed.length>4)return null;
  const moves=[],removed=[];
  if(moved.toLowerCase()==='k'&&(Math.abs(xyz(from)[0]-xyz(to)[0])>1||a[to]?.toLowerCase()==='r')){
   const king=Object.keys(b).find(s=>b[s]===moved),rook=moved==='K'?'R':'r';
   const rf=changed.find(s=>a[s]===rook),rt=changed.find(s=>b[s]===rook);
   if(!king||!rf||!rt||changed.some(s=>![from,king,rf,rt].includes(s)))return null;
   moves.push({from,to:king,piece:moved},{from:rf,to:rt,piece:rook});
  }else{
   const expected=uci.length===5?(moved==='P'?uci[4].toUpperCase():uci[4]):moved;
   if(b[to]!==expected||b[from])return null;
   moves.push({from,to,piece:moved,promotion:expected!==moved});
   for(const sq of changed)if(sq!==from&&a[sq]){if((a[sq]===a[sq].toUpperCase())===(moved===moved.toUpperCase()))return null;removed.push(sq)}
   if(changed.some(s=>s!==from&&s!==to&&!removed.includes(s)))return null;
  }
  return {moves,removed};
 }
 return {settings,roomMotionEnabled,views,tourCamera,placement,xyz,transition};
})();
if(typeof module!=='undefined')module.exports=ArenaScene3D;
