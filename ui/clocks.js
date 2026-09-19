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
  if(!c)return {text:'—',label:'Waiting for clock',detail:'',active:false,stale:false};
  if(kind==='nodes'||kind==='depth'){
   seconds=elapsed;label=active?'Move elapsed':'Last move';detail=kind==='nodes'?Number(tc.nodes).toLocaleString()+' nodes / move':'Depth '+tc.depth;
   detail+=' · no chess clock';
  }else if(kind==='movetime'){
   seconds=Math.max(0,tc.seconds-(active?elapsed:0));label='Time per move';detail=format(tc.seconds)+' / move';
  }else{
   const delay=['delay','bronstein'].includes(kind)?Number(tc.delay)||0:0;
   seconds=c.remaining===null?null:Math.max(0,c.remaining-(active?Math.max(0,elapsed-delay):0));label='Time remaining';
   if(delay)detail=(kind==='bronstein'?'Bronstein ':'Delay ')+delay+'s'+(active?' · '+Math.max(0,delay-elapsed).toFixed(1)+'s free':'');
   else if(kind==='fischer')detail='+'+(tc.increment||0)+'s / move';
   else if(kind==='staged')detail='Stage '+((c.stage||0)+1)+(tc.repeat?' · repeating':'');
  }
  if(stale)label='Waiting for update';
  return {text:seconds===null?'—':format(seconds),label,detail,active:active&&!stale,stale};
 }
 return {format,project};
})();
if(typeof module!=='undefined')module.exports=ArenaClocks;
