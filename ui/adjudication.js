'use strict';
async function adjudicateGame(id){
 const summary=(state.historyGames||[]).find(g=>g.id===id),g=await api('games/'+id),attempt=g.attempts.at(-1);
 if(g.state!=='running'||g.invalid||!attempt||attempt.ended)throw Error(ArenaI18n.t('This game is no longer running. Refresh the game list.'));
 const diagnostic=attempt.mode==='diagnostic';
 modal(ArenaI18n.m`Adjudicate live game ${g.number+1}`,ArenaI18n.h`<p>End attempt ${attempt.seq} of opening pair ${g.pair_no+1} with a result you choose.</p><p class="caption">${diagnostic?ArenaI18n.t('This is a diagnostic replay. The decision is saved in its attempt history and PGN; the official result stays unchanged.'):ArenaI18n.t('This result will count in official standings and ratings. Opening-pair statistics update when both games finish. Later rounds use this result.')} Moves, clocks and the reason are preserved. A move may finish while the engines stop.</p><div class="fields"><div class="field full"><label for="manualResult">Result</label><select id="manualResult" required><option value="">Choose a result…</option><option value="1-0">White wins · 1–0</option><option value="1/2-1/2">Draw · ½–½</option><option value="0-1">Black wins · 0–1</option></select></div><div class="field full"><label for="manualReason">Reason for adjudication</label><input id="manualReason" required maxlength="1000" placeholder="Why are you ending this game?"></div></div><p id="manualGameNames" class="caption"></p>`,ArenaI18n.h`<button class="primary" id="confirmAdjudication">Adjudicate & end game</button>`);
 $('#manualGameNames').textContent=ArenaI18n.m`White: ${summary?.white_name||'#'+(g.white+1)} · Black: ${summary?.black_name||'#'+(g.black+1)}`;
 if(!diagnostic&&state.snapshot?.settings.format==='sprt'&&!state.snapshot.sprt?.frozen)$('#manualGameNames').insertAdjacentHTML('afterend',ArenaI18n.h('<p class="caption">Manual adjudication invalidates SPRT inference. Use diagnostic replay to investigate without changing the test.</p>'));
 const error=document.createElement('p');error.id='adjudicationError';error.setAttribute('role','alert');error.hidden=true;$('#manualGameNames').after(error);
 $('#manualResult').dataset.help=ArenaI18n.t('Choose the result from White’s perspective. The selected attempt must still be running.');
 $('#manualReason').dataset.help=ArenaI18n.t('Required explanation saved in the attempt, audit trail and PGN termination details.');
 $('#confirmAdjudication').dataset.help=ArenaI18n.t('Stop this attempt and commit the selected result. Other live games continue.');
 $('#confirmAdjudication').onclick=safely(async()=>{
  if(!$('#manualResult').reportValidity()||!$('#manualReason').reportValidity())return;
  error.hidden=true;
  try{await api(`tournaments/${g.tid}/games/${g.id}/adjudicate`,{attempt:attempt.id,result:$('#manualResult').value,note:$('#manualReason').value,confirmed:true});}
  catch(e){error.textContent=e.message;error.hidden=false;return;}
  $('#modal').close();await refreshTournament();notify(diagnostic?ArenaI18n.t('Diagnostic adjudication saved. Official result unchanged.'):ArenaI18n.t('Manual adjudication saved; official results updated.'));
 });
}

function wireAdjudication(){
 for(const g of state.historyGames||[]){
  if(g.state!=='running'||g.invalid)continue;
  const row=$(`#games [data-game="${g.id}"]`);if(!row||row.querySelector('[data-adjudicate]'))continue;
  const button=document.createElement('button');button.className='subtle';button.dataset.adjudicate=g.id;button.textContent=ArenaI18n.t('Adjudicate…');button.setAttribute('aria-label',ArenaI18n.m`Adjudicate game ${g.number+1}`);button.dataset.help=ArenaI18n.t('End this live attempt as a White win, draw or Black win, with a recorded reason.');
  button.onclick=safely(event=>{event.stopPropagation();return adjudicateGame(g.id)});row.children[5].append(button);
 }
}
