'use strict';
const focusDirector=new ArenaFocusDirector.Director();
let focusStatus={holding:false,waiting:false},focusFinalPending='',focusArrowState={key:'',since:0};
const focusWatching=document.createElement('div');focusWatching.className='focus-watching';
focusWatching.innerHTML=ArenaI18n.h`<button id="followEngine">Follow engine…</button><button id="stopFollowEngine" hidden>Stop following</button><label>Finish hold <input id="focusFinishHold" type="number" min="0" max="60" step="1" aria-label="Final position hold in seconds"> s</label><button id="focusNextGame" hidden>Next game</button><label><input id="focusPvArrow" type="checkbox"> Best-move arrow</label><label>Delay <input id="focusArrowDelay" type="number" min="0" max="10" step="0.1" aria-label="Best-move arrow delay in seconds"> s</label><span id="followEngineStatus" role="status"></span>`;
panels.focus.querySelector('.panel-tools').after(focusWatching);
function clearEngineFollow(){displayPrefs.followEngine=null;focusDirector.reset(state.tid);saveDisplay();paintFollowControls()}
function followedProfile(){return displayPrefs.followEngine?.tid===state.tid?displayPrefs.followEngine.profile:''}
function focusDirectorSelect(games){
 const recent=state.recentFinished||[],live=games.find(g=>g.game===focusId),saved=recent.find(g=>g.game===focusId&&(!retainedFocus?.attempt||g.attempt===retainedFocus.attempt));
 if(!live&&!saved&&retainedFocus&&!retainedFocus.ended&&state.connected!==false){
  if(focusFinalPending!==retainedFocus.game){
   const old=retainedFocus;focusFinalPending=old.game;
   api(`games/${old.game}/moves?after=last&limit=1${old.attempt?'&attempt='+encodeURIComponent(old.attempt):''}`).then(d=>{
    if(d.attempt?.ended){const m=d.items.at(-1),a=d.attempt;
     const final={...old,...(m?{fen:m.fen,last_move:m.uci,san:m.san,ply:m.ply,crown_squares:m.crown_squares,knight_facings:m.knight_facings,captured:m.captured}:{fen:d.opening.fen}),attempt:a.id,ended:a.ended,result:a.result,reason:a.reason,detail:a.detail,official:a.official,clocks:a.clocks,clock_active:null,searches:{},status:a.result+' · '+a.reason.replaceAll('_',' ')};
     state.recentFinished=[...(state.recentFinished||[]).filter(x=>x.attempt!==a.id),final].slice(-64);
    }
   }).catch(e=>{if(focusId===old.game)$('#followEngineStatus').textContent=ArenaI18n.t('Final result unavailable')+': '+e.message}).finally(()=>{focusFinalPending='';});
  }
  return {...retainedFocus,clock_active:null,status:ArenaI18n.t('Waiting for committed result…')};
 }
 focusStatus=focusDirector.select({tid:state.tid,live:games,recent,current:focusId,retained:retainedFocus,profile:followedProfile(),auto:displayPrefs.followNextGame!==false,review:typeof browsingRecordedMoves==='function'&&browsingRecordedMoves(),hold:displayPrefs.finishHold??3,now:performance.now(),connected:state.connected!==false});
 paintFollowControls();return focusStatus.game;
}
function paintFollowControls(){
 const followed=followedProfile(),label=followed?displayPrefs.followEngine.name:'';
 $('#stopFollowEngine').hidden=!followed;$('#focusNextGame').hidden=!focusStatus.holding;
 $('#followEngineStatus').textContent=focusStatus.holding?ArenaI18n.t('Final result · viewing hold'):followed?(focusStatus.waiting?ArenaI18n.t('Waiting for '):ArenaI18n.t('Following '))+label:'';
 if(document.activeElement!==$('#focusFinishHold'))$('#focusFinishHold').value=displayPrefs.finishHold??3;$('#focusPvArrow').checked=!!displayPrefs.pvArrow;if(document.activeElement!==$('#focusArrowDelay'))$('#focusArrowDelay').value=displayPrefs.pvArrowDelay??1;
}
$('#stopFollowEngine').onclick=()=>{clearEngineFollow();renderFocus()};
$('#focusNextGame').onclick=()=>{focusDirector.skip();if(typeof sheetReset==='function')sheetReset('');renderFocus()};
for(const [id,key,min,max] of [['focusFinishHold','finishHold',0,60],['focusArrowDelay','pvArrowDelay',0,10]])$('#'+id).onchange=()=>{const el=$('#'+id);if(!el.reportValidity())return;displayPrefs[key]=Math.max(min,Math.min(max,Number(el.value)));saveDisplay();renderFocus()};
$('#focusPvArrow').onchange=()=>{displayPrefs.pvArrow=$('#focusPvArrow').checked;focusArrowState={key:'',since:0};saveDisplay();renderFocus()};
$('#followEngine').onclick=safely(async()=>{
 if(!state.tid)throw Error(ArenaI18n.t('Select a tournament first'));
 const tid=state.tid;let offset=0,gen=0;
 modal(ArenaI18n.t('Follow an engine'),ArenaI18n.h`<p>Follow this exact tournament profile. The current game stays selected while it plays. When idle, its last board stays visible until the next game starts. Choosing a game manually stops following.</p><label>Search tournament engines<input id="followSearch" type="search"></label><div id="followChoices"></div><div class="pager"><button id="followPrev">Previous</button><span id="followPage"></span><button id="followNext">Next</button></div>`);
 async function load(){const version=++gen,r=await api(`tournaments/${tid}/participants?q=${encodeURIComponent($('#followSearch').value)}&offset=${offset}`);if(version!==gen||!$('#followChoices'))return;
  $('#followChoices').innerHTML=r.items.map(p=>`<button class="follow-choice" data-follow-slot="${p.slot}" ${p.id?'':'disabled'}>${esc(p.name)} <small>${esc(p.id||ArenaI18n.t('No saved profile identity'))}</small></button>`).join('');
  $('#followPage').textContent=`${r.total?offset+1:0}–${Math.min(offset+50,r.total)} / ${r.total}`;$('#followPrev').disabled=!offset;$('#followNext').disabled=offset+50>=r.total;
  $$('[data-follow-slot]').forEach(b=>b.onclick=()=>{const p=r.items.find(x=>x.slot===Number(b.dataset.followSlot));displayPrefs.followEngine={tid,profile:p.id,name:p.name};focusId='';retainedFocus=null;focusDirector.reset(tid);saveDisplay();$('#modal').close();renderFocus()});
 }
 $('#followSearch').oninput=safely(()=>{offset=0;return load()});$('#followPrev').onclick=safely(()=>{offset=Math.max(0,offset-50);return load()});$('#followNext').onclick=safely(()=>{offset+=50;return load()});await load();
});
function focusedIntention(game){
 const hint=ArenaFocusDirector.arrow(game,displayPrefs.pvArrow,state.connected!==false),key=hint?[game.game,game.attempt,game.clock_active,hint.fen,hint.uci].join('|'):'';
 if(key!==focusArrowState.key)focusArrowState={key,since:performance.now()};
 return hint&&performance.now()-focusArrowState.since>=Math.max(0,Math.min(10,displayPrefs.pvArrowDelay??1))*1000?hint:null;
}
function paintIntention2d(game){
 const board=$('#focusContent .focus-board .board');if(!board)return;
 let svg=board.querySelector('.intention-arrow');const hint=focusedIntention(game);
 if(!hint){svg?.remove();return}
 if(!svg){svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('class','intention-arrow');svg.setAttribute('viewBox','0 0 800 800');svg.setAttribute('aria-label',ArenaI18n.t('Current engine principal-variation move'));board.append(svg)}
 const square=s=>{let x=s.charCodeAt(0)-97,y=8-Number(s[1]);if(state.flip){x=7-x;y=7-y}return [x*100+50,y*100+50]},a=square(hint.from),b=square(hint.to),dx=b[0]-a[0],dy=b[1]-a[1],len=Math.hypot(dx,dy)||1,ux=dx/len,uy=dy/len,base=[b[0]-ux*30,b[1]-uy*30];
 svg.innerHTML=`<path d="M${a} L${base}" fill="none" stroke="#35b9f3" stroke-width="14" stroke-linecap="round"/><path d="M${b} L${base[0]-uy*22},${base[1]+ux*22} L${base[0]+uy*22},${base[1]-ux*22} Z" fill="#35b9f3"/>`;
}
const focusBeforeFollowing=renderFocus;renderFocus=function(){focusBeforeFollowing();paintIntention2d(typeof gameMovesView==='function'?gameMovesView(retainedFocus):retainedFocus);paintFollowControls()};
const displayBeforeFollowing=applyDisplay;applyDisplay=function(){displayBeforeFollowing();paintFollowControls()};
const recentFinishHost=document.createElement('details');recentFinishHost.className='recent-finishes';recentFinishHost.innerHTML=ArenaI18n.h('<summary>Recent finishes</summary><div id="recentFinishItems"></div>');panels.live.append(recentFinishHost);
const boardsBeforeFinishes=renderBoards;renderBoards=function(){boardsBeforeFinishes();const finished=(state.recentFinished||[]).filter(g=>g.tid===state.tid).slice(-8).reverse();stableHtml('#recentFinishItems',finished.map(g=>`<button data-finished-game="${esc(g.game)}">${esc(g.white.name)} / ${esc(g.black.name)} · <strong>${esc(g.result)}</strong> · ${esc(g.reason.replaceAll('_',' '))}</button>`).join(''));recentFinishHost.hidden=!finished.length;recentFinishHost.querySelectorAll('button').forEach(b=>b.onclick=safely(()=>gameDetail(b.dataset.finishedGame)))};
paintFollowControls();
