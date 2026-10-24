(function(root){
 'use strict';
 class Director{
  constructor(){this.reset('')}
  reset(tid){this.tid=tid;this.finishKey='';this.until=0;this.skipKey=''}
  skip(){this.skipKey=this.finishKey;this.until=0}
  select({tid,live,recent,current,retained,profile='',auto=true,review=false,hold=3,now=0,connected=true}){
   if(this.tid!==tid)this.reset(tid);
   const games=live.filter(g=>g.tid===tid),playing=games.find(g=>g.game===current);
   const matches=g=>!profile||g.white?.id===profile||g.black?.id===profile;
   if(playing&&matches(playing))return {game:playing,holding:false,waiting:false};
   const saved=recent.find(g=>g.tid===tid&&g.game===current&&(!retained?.attempt||g.attempt===retained.attempt))||retained;
   if(saved?.ended&&saved.game===current){
    const key=saved.game+':'+saved.attempt;
    if(key!==this.finishKey){this.finishKey=key;this.until=now+Math.max(0,Math.min(60,Number(hold)||0))*1000}
    if(this.skipKey!==key&&now<this.until)return {game:saved,holding:true,waiting:false};
   }
   if(review||!connected||(!auto&&!profile))return {game:playing||saved,holding:false,waiting:!!profile};
   const candidates=games.filter(matches).sort((a,b)=>a.number-b.number||a.game.localeCompare(b.game));
   return {game:candidates[0]||saved,holding:false,waiting:!!profile&&!candidates.length};
  }
 }
 function arrow(game,enabled,connected=true){
  if(!enabled||!connected||!game||game.reviewing||!game.clock_active||game.ended)return null;
  const search=game.searches?.[game.clock_active],hint=search?.info?.intention;
  if(search?.complete||!hint||hint.from===hint.to||hint.fen!==game.fen||!['from','to'].every(k=>/^[a-h][1-8]$/.test(hint[k])))return null;
  return hint;
 }
 const api={Director,arrow};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ArenaFocusDirector=api;
})(typeof globalThis!=='undefined'?globalThis:this);
