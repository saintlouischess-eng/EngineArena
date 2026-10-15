if(typeof module!=='undefined'&&!globalThis.ArenaI18n)require('./i18n.js');
/* Pure clock projection shared by the live boards, focus panel and history. */
const ArenaClocks=(()=>{
 function format(seconds){
  const tenths=Math.floor(Math.max(0,Number(seconds)||0)*10+1e-6),s=Math.floor(tenths/10),h=Math.floor(s/3600),m=Math.floor(s/60)%60;
  return (h?h+':'+String(m).padStart(2,'0'):String(m).padStart(2,'0'))+':'+String(s%60).padStart(2,'0')+'.'+tenths%10;
 }
 function project(game,side,age=0){
  const c=game.clocks?.[side],tc=c?.control||{},kind=tc.kind,active=game.clock_active===side;
  const stale=active&&age>2500,elapsed=active?Math.max(0,game.search_elapsed||0)+Math.min(2500,Math.max(0,age))/1000:(game.last_move_seconds?.[side]??c?.elapsed??0);
  let seconds,label,detail='';
  if(!c)return {text:'—',label:ArenaI18n.t('Waiting for clock'),detail:'',active:false,stale:false};
  if(kind==='nodes'||kind==='depth'){
   seconds=elapsed;label=active?ArenaI18n.t('Move elapsed'):ArenaI18n.t('Last move');detail=kind==='nodes'?Number(tc.nodes).toLocaleString(ArenaI18n.locale)+ArenaI18n.t(' nodes / move'):ArenaI18n.t('Depth ')+tc.depth;
   detail+=ArenaI18n.t(' · no chess clock');
  }else if(kind==='movetime'){
   seconds=Math.max(0,tc.seconds-(active?elapsed:0));label=ArenaI18n.t('Time per move');detail=format(tc.seconds)+' / move';
  }else{
   const delay=['delay','bronstein'].includes(kind)?Number(tc.delay)||0:0;
   seconds=c.remaining===null?null:Math.max(0,c.remaining-(active?Math.max(0,elapsed-delay):0));label=ArenaI18n.t('Time remaining');
   if(delay)detail=(kind==='bronstein'?ArenaI18n.t('Bronstein '):ArenaI18n.t('Delay '))+delay+'s'+(active?' · '+Math.max(0,delay-elapsed).toFixed(1)+ArenaI18n.t('s free'):'');
   else if(kind==='fischer')detail='+'+(tc.increment||0)+ArenaI18n.t('s / move');
   else if(kind==='staged')detail=ArenaI18n.t('Stage ')+((c.stage||0)+1)+(tc.repeat?ArenaI18n.t(' · repeating'):'');
  }
  if(stale)label=ArenaI18n.t('Waiting for update');
  return {text:seconds===null?'—':format(seconds),label,detail,active:active&&!stale,stale};
 }
 // Read-only projection for the physical clock in the modeled room. Unknown
 // clocks stay blank; node/depth searches are labeled elapsed, never a deadline.
 function table(data,now=0){
  if(!data)return null;
  if(data.kind==='focus')return Object.fromEntries(['white','black'].map(side=>{const value=project(data.game,side,Math.max(0,now-data.receivedAt));const kind=data.game.clocks?.[side]?.control?.kind;return [side,{...value,mode:['nodes','depth'].includes(kind)?'ELAPSED':''}]}));
  if(data.kind!=='player')return null;
  const g=data.game,review=data.review!==null,record=review?(data.review?g.moves[data.review-1]?.clocks:g.moves[0]?.before?.clocks):null;
  return Object.fromEntries(['white','black'].map(side=>{const c=(record||g.clocks)?.[side],tc=c?.control||{},active=!review&&g.state==='playing'&&g.turn===side&&!data.viewing;
   if(!c)return [side,{text:'—',active:false}];
   const elapsed=active?Math.max(0,g.turn_elapsed||0)+Math.max(0,now-data.receivedAt)/1000:0,delay=['delay','bronstein'].includes(tc.kind)?tc.delay||0:0;
   const fixed=['nodes','depth'].includes(tc.kind),seconds=fixed?elapsed:tc.kind==='movetime'?Math.max(0,tc.seconds-elapsed):c.remaining===null?null:Math.max(0,c.remaining-Math.max(0,elapsed-delay));
   return [side,{text:seconds===null?'∞':format(seconds),active,mode:fixed?'ELAPSED':seconds===null?'UNTIMED':''}];
  }));
 }
 return {format,project,table};
})();
if(typeof module!=='undefined')module.exports=ArenaClocks;
