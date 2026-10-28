(function(root){
 'use strict';
 const winningDefaults={enabled:false,pawns:2,confirm:5,stay:'finish',minimum:30,fade:15};
 function winningSettings(raw={}){
  const p={...winningDefaults,enabled:raw.enabled===true,stay:raw.stay==='fade'?'fade':'finish'};
  for(const [k,min,max] of [['pawns',.5,20],['confirm',0,30],['minimum',5,300],['fade',5,120]])if(Number.isFinite(raw[k]))p[k]=Math.max(min,Math.min(max,raw[k]));
  return p;
 }
 function winningEstimate(g){
  if(!g||g.ended||g.reviewing)return null;
  const exact=i=>i&&!['lowerbound','upperbound'].includes(i.score_bound)&&(Number.isFinite(i.mate)||Number.isFinite(i.cp));
  // Worker scores are already White-relative. Only the current or just-completed
  // search is usable; do not follow a score left behind several moves earlier.
  let info=exact(g.info)?g.info:null,side=g.info_side||g.clock_active;
  if(!info&&Number.isInteger(g.ply)){
   const fresh=Object.entries(g.searches||{}).filter(([,s])=>Number.isInteger(s.ply)&&s.ply>=g.ply&&s.ply<=g.ply+1&&exact(s.info)).sort((a,b)=>b[1].ply-a[1].ply);
   if(fresh.length){[side]=fresh[0];info=fresh[0][1].info}
  }
  if(!info)return null;
  const mate=Number.isFinite(info.mate),sign=mate?(Math.sign(info.mate)||(side==='white'?-1:1)):Math.sign(info.cp);
  return {side:sign<0?'black':'white',cp:mate?null:info.cp,mate:mate?info.mate:null,strength:mate?100000-Math.min(99999,Math.abs(info.mate)):Math.abs(info.cp)};
 }
 const gameKey=g=>g?g.game+':'+(g.attempt||''):'';
 class WinningWatch{
  constructor(){this.reset()}
  reset(){this.tracked=new Map();this.skipped=new Set();this.chosen='';this.chosenAt=0;this.fadedAt=null;this.advance=false}
  next(g){if(g)this.skipped.add(gameKey(g));this.advance=true}
  observe(games,p,now){
   const keys=new Set(games.map(gameKey));for(const key of this.tracked.keys())if(!keys.has(key))this.tracked.delete(key);
   for(const key of this.skipped)if(!keys.has(key))this.skipped.delete(key);
   return games.filter(g=>!g.ended).map(g=>{
    const key=gameKey(g),estimate=winningEstimate(g),qualifies=estimate&&estimate.strength>=p.pawns*100;
    let track=this.tracked.get(key);
    if(!qualifies){this.tracked.delete(key);return {g,key,estimate,ready:false,qualifies:false}}
    if(!track||track.side!==estimate.side){track={since:now,side:estimate.side};this.tracked.set(key,track)}
    return {g,key,estimate,qualifies:true,ready:now-track.since>=p.confirm*1000};
   });
  }
  select(rows,fallback,p,now){
   const held=rows.find(r=>r.key===this.chosen);
   if(held&&!this.advance){
    if(held.qualifies)this.fadedAt=null;else if(this.fadedAt===null)this.fadedAt=now;
    if(p.stay==='finish'||held.qualifies||now-this.chosenAt<p.minimum*1000||now-this.fadedAt<p.fade*1000)
     return {game:held.g,estimate:held.estimate,holding:false,waiting:false,winning:true};
   }
   let candidates=rows.filter(r=>(this.advance?r.qualifies:r.ready)&&!this.skipped.has(r.key)&&r.key!==held?.key);
   // Manual Next cycles through alternatives. Never bounce back automatically.
   if(!candidates.length&&this.advance){const current=gameKey(fallback);this.skipped=new Set(current?[current]:[]);candidates=rows.filter(r=>r.qualifies&&r.key!==current)}
   candidates.sort((a,b)=>b.estimate.strength-a.estimate.strength||a.g.number-b.g.number||a.key.localeCompare(b.key));
   const chosen=candidates[0];
   if(chosen){this.chosen=chosen.key;this.chosenAt=now;this.fadedAt=null;this.advance=false;return {game:chosen.g,estimate:chosen.estimate,holding:false,waiting:false,winning:true}}
   return {game:held?.g||fallback,estimate:held?.estimate,holding:false,waiting:true,winning:true};
  }
 }
 class Director{
  constructor(){this.reset('')}
  reset(tid){this.tid=tid;this.finishKey='';this.until=0;this.skipKey='';this.winning=new WinningWatch()}
  skip(){this.skipKey=this.finishKey;this.until=0}
  nextWinning(g){this.skip();this.winning.next(g)}
  select({tid,live,recent,current,retained,profile='',auto=true,review=false,hold=3,now=0,connected=true,winning={}}){
   if(this.tid!==tid)this.reset(tid);
   const games=live.filter(g=>g.tid===tid),playing=games.find(g=>g.game===current);
   const p=winningSettings(winning),watching=p.enabled&&!profile;
   const rows=watching&&connected&&!review?this.winning.observe(games,p,now):[];
   const matches=g=>!profile||g.white?.id===profile||g.black?.id===profile;
   if(!watching&&playing&&matches(playing))return {game:playing,holding:false,waiting:false};
   const saved=recent.find(g=>g.tid===tid&&g.game===current&&(!retained?.attempt||g.attempt===retained.attempt))||retained;
   if(saved?.ended&&saved.game===current){
    const key=saved.game+':'+saved.attempt;
    if(key!==this.finishKey){this.finishKey=key;this.until=now+Math.max(0,Math.min(60,Number(hold)||0))*1000}
    if(this.skipKey!==key&&now<this.until)return {game:saved,holding:true,waiting:false};
   }
   if(review||!connected||(!auto&&!profile&&!watching))return {game:playing||saved,holding:false,waiting:!!profile};
   if(watching)return this.winning.select(rows,playing||saved,p,now);
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
 const api={Director,arrow,winningSettings,winningEstimate};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ArenaFocusDirector=api;
})(typeof globalThis!=='undefined'?globalThis:this);
