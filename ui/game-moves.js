'use strict';
// One bounded scoresheet page. Move polling is independent of search telemetry.
const moveSheet={game:'',attempt:'',after:0,latest:0,rows:[],data:null,review:null,busy:false,key:'',generation:0,follow:true};
function reviewingRecordedMove(){return !!moveSheet.review&&moveSheet.game===focusId}
const movesRoot=$('#gameMovesContent');
movesRoot.innerHTML=ArenaI18n.h('<div class="moves-toolbar"><button id="movesEarlier" aria-label="Earlier moves">←</button><button id="movesLater" aria-label="Later moves">→</button><button id="movesLatest" class="primary">Return to live</button><span class="spacer"></span><label>Text <input id="movesFont" aria-label="Move text size" type="number" min="12" max="24" step="1"></label><label><input id="movesDetails" type="checkbox"> More stats</label></div><p id="movesContext" class="caption" role="status"></p><div class="scoresheet-scroll" tabindex="0" role="region" aria-label="Recorded game moves"><table class="scoresheet"><thead></thead><tbody></tbody></table></div><p class="moves-note">Eval: White’s perspective before the move. Time: measured move elapsed. Book moves have no search statistics.</p>');
function sheetReset(game){Object.assign(moveSheet,{game,attempt:'',after:0,latest:0,rows:[],data:null,review:null,key:'',follow:true});moveSheet.generation++;paintMoveSheet()}
function gameMovesView(g){
 if(!g)return g;
 if(g.game!==moveSheet.game)return g;
 const row=moveSheet.review;
 if(!row)return g;
 // Clock DOM loses its live binding while reviewing. The search panel stays live.
 return {...g,fen:row.fen,last_move:row.uci,san:row.san,ply:row.ply,crown_squares:row.crown_squares||[],clocks:row.clocks,clock_active:null,searches:{},info:row.info,info_side:row.side,reviewing:true,status:ArenaI18n.t('Reviewing recorded move')+' '+row.label+' '+row.san};
}
async function refreshGameMoves(g,force=false){
 if(!g){if(moveSheet.game)sheetReset('');return}
 if(moveSheet.game!==g.game){sheetReset(g.game);if((g.ply||0)>200)moveSheet.after=Math.floor((g.ply-1)/200)*200}
 const live=state.live.find(x=>x.game===g.game);
 if(moveSheet.busy||document.hidden||state.view!=='overview'||panels.moves.hidden&&!force&&!moveSheet.review&&(panels.focus.hidden||live))return;
 const key=[g.game,live?.attempt||g.attempt,g.ply,!!live,moveSheet.after].join(':');
 if(!force&&key===moveSheet.key&&(!moveSheet.data?.attempt||live||moveSheet.data.attempt.ended))return;
 const generation=moveSheet.generation,game=g.game,after=moveSheet.after;
 moveSheet.busy=true;
 try{
  const old=moveSheet.data,since=old?.after===after&&(!live||live.attempt===old.attempt?.id)?Math.max(after,...moveSheet.rows.map(m=>m.ply)):after;
  const readAfter=since<after+200?since:after;
  const data=await api(`games/${game}/moves?after=${readAfter}&limit=${200-(readAfter-after)}`);
  if(generation!==moveSheet.generation||game!==focusId||g.tid!==state.tid||after!==moveSheet.after)return;
  if(moveSheet.attempt&&moveSheet.attempt!==data.attempt?.id){sheetReset(game);return}
  if(readAfter>after){data.items=[...old.items,...data.items];data.opening_moves=old.opening_moves;data.after=after}
  const scroll=movesRoot.querySelector('.scoresheet-scroll'),atBottom=scroll.scrollHeight-scroll.scrollTop-scroll.clientHeight<50;
  Object.assign(moveSheet,{data,attempt:data.attempt?.id||'',rows:[...data.opening_moves,...data.items],latest:data.latest_ply,key});
  if(moveSheet.follow&&data.latest_ply>after+200){moveSheet.after=Math.floor((data.latest_ply-1)/200)*200;moveSheet.key='';return}
  if(!live&&retainedFocus?.game===game){
   const last=data.items.at(-1);
   retainedFocus={...retainedFocus,crown_squares:last?.crown_squares||data.opening_crown_squares||[],clocks:data.attempt?.clocks||last?.clocks,clock_active:null,status:[data.attempt?.result,data.attempt?.reason].filter(Boolean).join(' · ')||ArenaI18n.t('Saved game'),...(last?{fen:last.fen,last_move:last.uci,san:last.san,ply:last.ply,info:last.info,info_side:last.side}:{}),searches:{}};
  }
  paintMoveSheet();if(moveSheet.follow&&atBottom)scroll.scrollTop=scroll.scrollHeight;
 }catch(e){if(generation===moveSheet.generation)$('#movesContext').textContent=e.message}
 finally{moveSheet.busy=false}
}
function paintMoveSheet(){
 const d=moveSheet.data,details=!!displayPrefs.moveDetails,font=Math.max(12,Math.min(24,Number(displayPrefs.moveFont)||14));
 movesRoot.style.setProperty('--moves-font',font+'px');$('#movesFont').value=font;$('#movesDetails').checked=details;
 $('#movesContext').textContent=d?`${d.white.name} / ${d.black.name} · ${ArenaI18n.t('Attempt')} ${d.attempt?.seq||'—'} · ${ArenaI18n.message(d.attempt?.mode||'')} ${d.attempt?.official?'· '+ArenaI18n.t('OFFICIAL'):''} · ${d.attempt?.result||ArenaI18n.t('In progress')}`:ArenaI18n.t('Recorded moves follow the focused game.');
 $('#movesContext').title=d?.warning||'';
 $('#movesEarlier').disabled=!moveSheet.after;$('#movesLater').disabled=moveSheet.after+200>=moveSheet.latest;
 $('#movesLatest').textContent=state.live.some(g=>g.game===moveSheet.game)?ArenaI18n.t('Return to live'):ArenaI18n.t('Final position');
 stableHtml('#gameMovesContent thead',ArenaI18n.h`<tr><th>Move</th><th>Eval</th><th>D / SD</th><th data-help="Measured elapsed seconds for this move, separate from engine-reported search time.">Time (s)</th>${details?ArenaI18n.h('<th>Nodes</th><th>Nodes / s</th><th>Clock</th>'):''}</tr>`);
 const existing=new Map([...movesRoot.querySelectorAll('tbody tr')].map(e=>[Number(e.dataset.ply),e])),body=movesRoot.querySelector('tbody');
 for(const m of moveSheet.rows){
  const book=['book','opening'].includes(m.info.source),selected=moveSheet.review?.ply===m.ply;
  const html=ArenaI18n.h`<td><button data-move="${m.ply}" title="${esc(m.uci)}" aria-pressed="${selected}"><span>${m.label}</span> <b>${esc(m.san)}</b>${book?'<i>'+ArenaI18n.t('Book')+'</i>':''}</button></td><td>${book?'—':esc(ArenaSearch.score(m.info))}</td><td>${book?'—':esc(m.info.depth??'—')+' / '+esc(m.info.seldepth??'—')}</td><td>${Number.isFinite(m.elapsed)?m.elapsed.toFixed(3):'—'}</td>${details?`<td title="${esc(m.info.nodes??'')}">${ArenaSearch.nodes(m.info.nodes)}</td><td>${ArenaSearch.nodes(m.info.nps)}</td><td>${m.clocks?.[m.side]?.remaining==null?'—':ArenaClocks.format(m.clocks[m.side].remaining)}</td>`:''}`;
  let row=existing.get(m.ply);if(!row){row=document.createElement('tr');row.dataset.ply=m.ply;body.append(row)}
  if(row._html!==html){row.innerHTML=html;row._html=html;row.querySelector('button').onclick=()=>{moveSheet.review=m;moveSheet.follow=false;paintMoveSheet();renderFocus()}}
  row.classList.toggle('selected-move',selected);existing.delete(m.ply);
 }
 for(const row of existing.values())row.remove();
}
function sheetPage(after){moveSheet.after=Math.max(0,after);moveSheet.key='';moveSheet.generation++;refreshGameMoves(selectedFocusGame(),true)}
$('#movesEarlier').onclick=()=>{moveSheet.follow=false;sheetPage(moveSheet.after-200)};
$('#movesLater').onclick=()=>{moveSheet.follow=false;sheetPage(moveSheet.after+200)};
$('#movesLatest').onclick=()=>{moveSheet.review=null;moveSheet.follow=true;sheetPage(Math.floor(Math.max(0,moveSheet.latest-1)/200)*200);renderFocus();const s=movesRoot.querySelector('.scoresheet-scroll');s.scrollTop=s.scrollHeight};
$('#movesFont').onchange=()=>{if(!$('#movesFont').reportValidity())return;displayPrefs.moveFont=Number($('#movesFont').value);paintMoveSheet();saveDisplay()};
$('#movesDetails').onchange=()=>{displayPrefs.moveDetails=$('#movesDetails').checked;paintMoveSheet();saveDisplay()};
movesRoot.querySelector('.scoresheet-scroll').addEventListener('scroll',e=>{const s=e.target;if(s.scrollHeight-s.scrollTop-s.clientHeight>50)moveSheet.follow=false});
const moveButton=document.createElement('button');moveButton.className='subtle';moveButton.textContent=ArenaI18n.t('Game moves');moveButton.onclick=()=>{revealFocusPanel('moves');refreshGameMoves(selectedFocusGame(),true)};panels.focus.querySelector('.panel-heading').append(moveButton);
const followNextLabel=document.createElement('label');followNextLabel.className='follow-next-game';followNextLabel.innerHTML=ArenaI18n.h('<input id="focusFollowNext" type="checkbox" checked> Follow next game');followNextLabel.dataset.help=ArenaI18n.t('Switch to another running game when this one finishes. Reviewing a recorded move pauses automatic switching. The last finished game stays visible when no games are running.');panels.focus.querySelector('.panel-tools').append(followNextLabel);
$('#focusFollowNext').onchange=()=>{displayPrefs.followNextGame=$('#focusFollowNext').checked;saveDisplay()};
const displayBeforeFollow=applyDisplay;applyDisplay=function(){displayBeforeFollow();$('#focusFollowNext').checked=displayPrefs.followNextGame!==false};
paintMoveSheet();renderFocus();
