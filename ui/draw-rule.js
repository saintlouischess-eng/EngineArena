'use strict';
const ArenaDrawRule=(()=>{
 function progress(fen,claims=true){
  const fields=String(fen||'').trim().split(/\s+/),plies=Number(fields[4]);
  if(fields.length!==6||!Number.isInteger(plies)||plies<0)return null;
  const limit=claims?100:150;
  return {plies,limit,remaining:Math.max(0,limit-plies),claims,reached:plies>=limit};
 }
 return {progress};
})();
if(typeof module!=='undefined')module.exports=ArenaDrawRule;
function paintDrawRule(root,g){
 let el=root.querySelector('.focus-draw-rule');
 if(!el){el=document.createElement('span');el.className='focus-draw-rule';root.querySelector('.focus-toolbar').insertBefore(el,root.querySelector('.focus-toolbar .spacer'))}
 const p=ArenaDrawRule.progress(g.fen,g.claim_draws??state.snapshot?.settings?.claim_draws??true);
 el.hidden=displayPrefs.showDrawRule===false||!p;
 if(!p)return;
 el.textContent=ArenaI18n.t(p.claims?'50-move rule: {0} / 100 plies · {1} remaining':'75-move rule: {0} / 150 plies · {1} remaining',p.plies,p.remaining);
 el.dataset.help=ArenaI18n.t('Half-moves since the last pawn move or capture; either resets the counter. Two plies equal one full move. This is not a time estimate. Checkmate and other game endings take precedence.')+(p.claims?'':' '+ArenaI18n.t('Fifty-move claims are disabled; showing the automatic seventy-five-move limit.'));
 el.title=el.dataset.help;el.classList.toggle('near-limit',p.remaining<=20);
}
