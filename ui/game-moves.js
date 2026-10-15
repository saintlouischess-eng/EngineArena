'use strict';
// Scroll through a bounded window; keep polling independent of search telemetry.
const movePageSize=200,moveWindowSize=400;
const moveSheet={game:'',attempt:'',after:0,span:movePageSize,latest:0,rows:[],data:null,review:null,busy:false,pending:false,key:'',generation:0,follow:true,scrollHint:null,scrollLock:false,scrollTop:0,scrollFrame:0};
function reviewingRecordedMove(){return !!moveSheet.review&&moveSheet.game===focusId}
function browsingRecordedMoves(){return moveSheet.game===focusId&&(!!moveSheet.review||!moveSheet.follow)}
const movesRoot=$('#gameMovesContent');
movesRoot.innerHTML=ArenaI18n.h('<div class="moves-toolbar"><button id="movesBeginning" data-help="Show the opening and earliest recorded moves. Home also returns to the beginning.">Beginning</button><button id="movesEarlier" aria-label="Earlier moves" data-help="Earlier moves">↑</button><button id="movesLater" aria-label="Later moves" data-help="Later moves">↓</button><button id="movesLatest" class="primary">Return to live</button><span class="spacer"></span><label>Text <input id="movesFont" aria-label="Move text size" type="number" min="12" max="24" step="1"></label><label><input id="movesDetails" type="checkbox"> More stats</label></div><p id="movesContext" class="caption" role="status"></p><p id="movesRange" class="moves-range" data-help="Scroll up for earlier moves and down for later moves. Your reading position stays in place while games continue."></p><div class="scoresheet-scroll" tabindex="0" role="region" aria-label="Recorded game moves"><table class="scoresheet"><thead></thead><tbody></tbody></table></div><p class="moves-note">Eval: White’s perspective before the move. Time: measured move elapsed. Book moves have no search statistics.</p>');
function sheetReset(game){Object.assign(moveSheet,{game,attempt:'',after:0,span:movePageSize,latest:0,rows:[],data:null,review:null,key:'',follow:true,scrollHint:{edge:'bottom'}});moveSheet.generation++;paintMoveSheet();restoreSheetScroll({edge:'bottom'})}
function gameMovesView(g){
 if(!g)return g;
 if(g.game!==moveSheet.game)return g;
 const row=moveSheet.review;
 if(!row)return g;
 // Clock DOM loses its live binding while reviewing. The search panel stays live.
 return {...g,fen:row.fen,last_move:row.uci,san:row.san,ply:row.ply,move_label:row.label,opening_move:row.info?.source==='opening',crown_squares:row.crown_squares||[],knight_facings:row.knight_facings||{},captured:row.captured||[],clocks:row.clocks,clock_active:null,searches:{},info:row.info,info_side:row.side,reviewing:true,status:ArenaI18n.t('Reviewing recorded move')+' '+row.label+' '+row.san};
}
async function refreshGameMoves(g,force=false){
 if(!g){if(moveSheet.game)sheetReset('');return}
 const changedGame=moveSheet.game!==g.game;
 if(changedGame){sheetReset(g.game);if((g.ply||0)>movePageSize)moveSheet.after=Math.floor((g.ply-1)/movePageSize)*movePageSize}
 const live=state.live.find(x=>x.game===g.game);
 if(moveSheet.busy){if(force||changedGame)moveSheet.pending=true;return}
 if(document.hidden||state.view!=='overview'||panels.moves.hidden&&!force&&!moveSheet.review&&(panels.focus.hidden||live))return;
 const key=[g.game,live?.attempt||g.attempt,g.ply,!!live,moveSheet.after,moveSheet.span].join(':');
 if(!force&&key===moveSheet.key&&(!moveSheet.data?.attempt||live||moveSheet.data.attempt.ended))return;
 const generation=moveSheet.generation,game=g.game,after=moveSheet.after,span=moveSheet.span;
 const old=moveSheet.data,sameWindow=old?.after===after&&old?.span===span&&(!live||live.attempt===old.attempt?.id);
 if(!force&&!moveSheet.follow&&sameWindow&&live&&old.items.length>=span){moveSheet.latest=Math.max(moveSheet.latest,g.ply||0);moveSheet.key=key;paintMoveNavigation();return}
 moveSheet.busy=true;
 try{
  const since=sameWindow?Math.max(after,...old.items.map(m=>m.ply)):after;
  const readAfter=since<after+span?since:after;
  const data=await api(`games/${game}/moves?after=${readAfter}&limit=${span-(readAfter-after)}`);
  if(generation!==moveSheet.generation||game!==focusId||g.tid!==state.tid||after!==moveSheet.after)return;
  if(moveSheet.attempt&&moveSheet.attempt!==data.attempt?.id){sheetReset(game);moveSheet.pending=true;return}
  if(readAfter>after){data.items=[...old.items,...data.items];data.opening_moves=old.opening_moves;data.after=after}
  data.span=span;
  const scroll=movesRoot.querySelector('.scoresheet-scroll'),hint=moveSheet.scrollHint?.edge?moveSheet.scrollHint:(moveSheet.follow?{edge:'bottom'}:sheetScrollAnchor());
  Object.assign(moveSheet,{data,attempt:data.attempt?.id||'',rows:[...data.opening_moves,...data.items],latest:data.latest_ply,key});
  if(moveSheet.follow&&data.latest_ply>after+span){sheetPage(Math.max(0,(Math.floor((data.latest_ply-1)/movePageSize)-1)*movePageSize),moveWindowSize,{edge:'bottom'});return}
  if(!live&&retainedFocus?.game===game&&data.items.at(-1)?.ply===data.latest_ply){
   const last=data.items.at(-1);
   retainedFocus={...retainedFocus,crown_squares:last?.crown_squares||data.opening_crown_squares||[],knight_facings:last?.knight_facings||data.opening_knight_facings||{},captured:last?.captured||data.opening_captured||[],clocks:data.attempt?.clocks||last?.clocks,clock_active:null,status:[data.attempt?.result,data.attempt?.reason].filter(Boolean).join(' · ')||ArenaI18n.t('Saved game'),...(last?{fen:last.fen,last_move:last.uci,san:last.san,ply:last.ply,info:last.info,info_side:last.side}:{}),searches:{}};
  }
  moveSheet.scrollHint=null;paintMoveSheet();restoreSheetScroll(hint);
 }catch(e){if(generation===moveSheet.generation)$('#movesContext').textContent=e.message}
 finally{moveSheet.busy=false;if(moveSheet.pending){moveSheet.pending=false;queueMicrotask(()=>refreshGameMoves(selectedFocusGame(),true))}}
}
function paintMoveNavigation(){
 $('#movesBeginning').disabled=!moveSheet.rows.length&&!moveSheet.after;
 $('#movesEarlier').disabled=!moveSheet.after;$('#movesLater').disabled=moveSheet.after+moveSheet.span>=moveSheet.latest;
 $('#movesLatest').textContent=state.live.some(g=>g.game===moveSheet.game)?ArenaI18n.t('Return to live'):ArenaI18n.t('Final position');
 const rows=moveSheet.rows;$('#movesRange').textContent=rows.length?ArenaI18n.t('Showing moves {0}–{1}',rows[0].label.replace(/[.…]+$/,''),rows.at(-1).label.replace(/[.…]+$/,''))+(moveSheet.follow?'':' · '+ArenaI18n.t('Browsing history')):'';
}
function paintMoveSheet(){
 const d=moveSheet.data,details=!!displayPrefs.moveDetails,font=Math.max(12,Math.min(24,Number(displayPrefs.moveFont)||14));
 movesRoot.style.setProperty('--moves-font',font+'px');$('#movesFont').value=font;$('#movesDetails').checked=details;
 $('#movesContext').textContent=d?`${d.white.name} / ${d.black.name} · ${ArenaI18n.t('Attempt')} ${d.attempt?.seq||'—'} · ${ArenaI18n.message(d.attempt?.mode||'')} ${d.attempt?.official?'· '+ArenaI18n.t('OFFICIAL'):''} · ${d.attempt?.result||ArenaI18n.t('In progress')}`:ArenaI18n.t('Recorded moves follow the focused game.');
 $('#movesContext').title=d?.warning||'';
 paintMoveNavigation();
 stableHtml('#gameMovesContent thead',ArenaI18n.h`<tr><th>Move</th><th>Eval</th><th>D / SD</th><th data-help="Measured elapsed seconds for this move, separate from engine-reported search time.">Time (s)</th>${details?ArenaI18n.h('<th>Nodes</th><th>Nodes / s</th><th>Clock</th>'):''}</tr>`);
 const existing=new Map([...movesRoot.querySelectorAll('tbody tr')].map(e=>[Number(e.dataset.ply),e])),body=movesRoot.querySelector('tbody');
 let cursor=body.firstChild;
 for(const m of moveSheet.rows){
  const book=['book','opening'].includes(m.info.source),selected=moveSheet.review?.ply===m.ply;
  const html=ArenaI18n.h`<td><button data-move="${m.ply}" title="${esc(m.uci)}" aria-pressed="${selected}"><span>${m.label}</span> <b>${esc(m.san)}</b>${book?'<i>'+ArenaI18n.t('Book')+'</i>':''}</button></td><td>${book?'—':esc(ArenaSearch.score(m.info))}</td><td>${book?'—':esc(m.info.depth??'—')+' / '+esc(m.info.seldepth??'—')}</td><td>${Number.isFinite(m.elapsed)?m.elapsed.toFixed(3):'—'}</td>${details?`<td title="${esc(m.info.nodes??'')}">${ArenaSearch.nodes(m.info.nodes)}</td><td>${ArenaSearch.nodes(m.info.nps)}</td><td>${m.clocks?.[m.side]?.remaining==null?'—':ArenaClocks.format(m.clocks[m.side].remaining)}</td>`:''}`;
  let row=existing.get(m.ply);if(!row){row=document.createElement('tr');row.dataset.ply=m.ply}
  if(row!==cursor)body.insertBefore(row,cursor);cursor=row.nextSibling;
  if(row._html!==html){row.innerHTML=html;row._html=html;row.querySelector('button').onclick=()=>{moveSheet.review=m;moveSheet.follow=false;paintMoveSheet();renderFocus()}}
  row.classList.toggle('selected-move',selected);existing.delete(m.ply);
 }
 for(const row of existing.values())row.remove();
}
function sheetScrollAnchor(){
 const scroll=movesRoot.querySelector('.scoresheet-scroll'),top=scroll.getBoundingClientRect().top,header=scroll.querySelector('thead').getBoundingClientRect().height;
 const row=[...scroll.querySelectorAll('tbody tr')].find(r=>r.getBoundingClientRect().bottom>top+header);
 return row?{ply:Number(row.dataset.ply),offset:row.getBoundingClientRect().top-top}:{edge:'top'};
}
function restoreSheetScroll(hint){
 const scroll=movesRoot.querySelector('.scoresheet-scroll');moveSheet.scrollLock=true;cancelAnimationFrame(moveSheet.scrollFrame);
 if(hint?.edge)scroll.scrollTop=hint.edge==='bottom'?scroll.scrollHeight:0;
 else if(hint){const row=scroll.querySelector(`tr[data-ply="${hint.ply}"]`);if(row)scroll.scrollTop+=row.getBoundingClientRect().top-scroll.getBoundingClientRect().top-hint.offset}
 moveSheet.scrollTop=scroll.scrollTop;moveSheet.scrollFrame=requestAnimationFrame(()=>{moveSheet.scrollTop=scroll.scrollTop;moveSheet.scrollLock=false});
}
function sheetPage(after,span=movePageSize,hint={edge:'top'}){moveSheet.after=Math.max(0,after);moveSheet.span=span;moveSheet.scrollHint=hint;moveSheet.key='';moveSheet.generation++;refreshGameMoves(selectedFocusGame(),true)}
function sheetBeginning(){moveSheet.follow=false;sheetPage(0)}
function sheetLatest(){moveSheet.review=null;moveSheet.follow=true;sheetPage(Math.floor(Math.max(0,moveSheet.latest-1)/movePageSize)*movePageSize,movePageSize,{edge:'bottom'});renderFocus()}
function sheetScrollPage(direction){
 if(moveSheet.busy||moveSheet.data?.after!==moveSheet.after||moveSheet.data?.span!==moveSheet.span)return;
 if(direction<0&&moveSheet.after>0){moveSheet.follow=false;sheetPage(moveSheet.after-movePageSize,Math.min(moveWindowSize,moveSheet.span+movePageSize),sheetScrollAnchor())}
 else if(direction>0&&moveSheet.after+moveSheet.span<moveSheet.latest){moveSheet.follow=false;sheetPage(moveSheet.span<moveWindowSize?moveSheet.after:moveSheet.after+movePageSize,Math.min(moveWindowSize,moveSheet.span+movePageSize),sheetScrollAnchor())}
}
$('#movesBeginning').onclick=sheetBeginning;
$('#movesEarlier').onclick=()=>{moveSheet.follow=false;sheetPage(moveSheet.after-movePageSize)};
$('#movesLater').onclick=()=>{moveSheet.follow=false;sheetPage(moveSheet.after+moveSheet.span)};
$('#movesLatest').onclick=sheetLatest;
$('#movesFont').onchange=()=>{if(!$('#movesFont').reportValidity())return;displayPrefs.moveFont=Number($('#movesFont').value);const hint=moveSheet.follow?{edge:'bottom'}:sheetScrollAnchor();paintMoveSheet();restoreSheetScroll(hint);saveDisplay()};
$('#movesDetails').onchange=()=>{displayPrefs.moveDetails=$('#movesDetails').checked;const hint=moveSheet.follow?{edge:'bottom'}:sheetScrollAnchor();paintMoveSheet();restoreSheetScroll(hint);saveDisplay()};
const sheetScroll=movesRoot.querySelector('.scoresheet-scroll');
let sheetViewport={width:sheetScroll.clientWidth,height:sheetScroll.clientHeight};
function syncSheetViewport(){
 const width=sheetScroll.clientWidth,height=sheetScroll.clientHeight;
 if(width===sheetViewport.width&&height===sheetViewport.height)return false;
 sheetViewport={width,height};
 // The browser clamps scrollTop when the viewport grows or controls reflow.
 // That is a layout change, not a request to stop following the live game.
 if(moveSheet.follow&&width&&height)restoreSheetScroll({edge:'bottom'});
 return true;
}
const sheetViewportObserver=new ResizeObserver(syncSheetViewport);sheetViewportObserver.observe(sheetScroll);
sheetScroll.addEventListener('scroll',()=>{
 const resized=syncSheetViewport(),direction=sheetScroll.scrollTop-moveSheet.scrollTop;moveSheet.scrollTop=sheetScroll.scrollTop;if(moveSheet.scrollLock||resized)return;
 if(direction<0||sheetScroll.scrollHeight-sheetScroll.scrollTop-sheetScroll.clientHeight>50){moveSheet.follow=false;paintMoveNavigation()}
 if(direction<0&&sheetScroll.scrollTop<48)sheetScrollPage(-1);
 else if(direction>0&&sheetScroll.scrollHeight-sheetScroll.scrollTop-sheetScroll.clientHeight<48)sheetScrollPage(1);
});
sheetScroll.addEventListener('wheel',e=>{if(e.deltaY<0&&sheetScroll.scrollTop<48)sheetScrollPage(-1);else if(e.deltaY>0&&sheetScroll.scrollHeight-sheetScroll.scrollTop-sheetScroll.clientHeight<48)sheetScrollPage(1)},{passive:true});
sheetScroll.addEventListener('keydown',e=>{if(e.ctrlKey||e.metaKey||e.altKey)return;if(e.key==='Home'){e.preventDefault();sheetBeginning()}else if(e.key==='End'){e.preventDefault();sheetLatest()}else if(['ArrowUp','PageUp'].includes(e.key)&&sheetScroll.scrollTop<48)sheetScrollPage(-1);else if(['ArrowDown','PageDown'].includes(e.key)&&sheetScroll.scrollHeight-sheetScroll.scrollTop-sheetScroll.clientHeight<48)sheetScrollPage(1)});
const moveButton=document.createElement('button');moveButton.className='subtle';moveButton.textContent=ArenaI18n.t('Game moves');moveButton.onclick=()=>{revealFocusPanel('moves');refreshGameMoves(selectedFocusGame(),true)};panels.focus.querySelector('.panel-heading').append(moveButton);
const followNextLabel=document.createElement('label');followNextLabel.className='follow-next-game';followNextLabel.innerHTML=ArenaI18n.h('<input id="focusFollowNext" type="checkbox" checked> Follow next game');followNextLabel.dataset.help=ArenaI18n.t('Switch to another running game when this one finishes. Reviewing a recorded move pauses automatic switching. The last finished game stays visible when no games are running.');panels.focus.querySelector('.panel-tools').append(followNextLabel);
$('#focusFollowNext').onchange=()=>{displayPrefs.followNextGame=$('#focusFollowNext').checked;saveDisplay()};
const displayBeforeFollow=applyDisplay;applyDisplay=function(){displayBeforeFollow();$('#focusFollowNext').checked=displayPrefs.followNextGame!==false};
paintMoveSheet();renderFocus();
