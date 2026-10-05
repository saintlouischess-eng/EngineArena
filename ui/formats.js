'use strict';
// Tournament policy controls and audited round review. Slots remain stable when
// standings or seeds change; the review labels them as participant numbers.
const tieLabels={wins:ArenaI18n.t('Wins'),black_wins:ArenaI18n.t('Wins with Black'),buchholz:ArenaI18n.t('Buchholz'),sonneborn_berger:'Sonneborn–Berger',seed:ArenaI18n.t('Initial seed')};
function formatSettings(){
  return {...customMatchupSettings(),...sprtSettings(),seeding:$('#fseeding')?.value||'input',tiebreaks:$$('[data-tiebreak]').map(e=>e.value).filter(Boolean),
    bye_score:Number($('#fbye')?.value??1),swiss_rematches:$('#frematches')?.checked||false,
    knockout_tiebreak:$('#fknockout')?.value||tournamentDraft?.settings.knockout_tiebreak||'continuous',playoff_limit:Number($('#fplayoffLimit')?.value??tournamentDraft?.settings.playoff_limit??3),
    playoff_cycles:Number($('#fplayoffCycles')?.value??tournamentDraft?.settings.playoff_cycles??1),playoff_fallback:$('#ffallback')?.value||tournamentDraft?.settings.playoff_fallback||'seed',
    ladder_distance:Number($('#fdistance')?.value??1),ladder_swap:$('#fmovement')?.value||'adjacent',...knockoutSettings()};
}
const baseTournamentEditor=newTournament;
newTournament=async function(draft=null){
  await baseTournamentEditor(draft);
  const options=(values,selected)=>Object.entries(values).map(([v,label])=>ArenaI18n.h`<option value="${v}" ${v===selected?'selected':''}>${label}</option>`).join('');
  $('.preview-total').insertAdjacentHTML('beforebegin',ArenaI18n.h`<div class="section-label">PAIRING & RANKING POLICIES</div><div class="fields" id="formatFields">
    <label>Initial seeding<select id="fseeding"><option value="input">Engine selection order</option><option value="random">Shuffle using tournament seed</option></select></label>
    ${Array.from({length:5},(_,i)=>ArenaI18n.h`<label>Standings tiebreak ${i+1}<select data-tiebreak>${options({'':ArenaI18n.t('None'),...tieLabels},i===0?'wins':i===1?'seed':'')}</select></label>`).join('')}
    <label data-format="swiss">Bye points per scheduled game<select id="fbye"><option value="1">1 point</option><option value="0.5">½ point</option><option value="0">0 points</option></select></label>
    <label data-format="swiss"><input type="checkbox" id="frematches"> Allow Swiss rematches automatically</label>
    <label data-format="ladder">Challenge distance (ladder places)<input id="fdistance" type="number" value="1" min="1" step="1"></label>
    <label data-format="ladder">Successful lower-ranked challenger<select id="fmovement"><option value="adjacent">Swap the two ladder positions</option><option value="leap">Take opponent's place; shift others down</option></select></label>
    </div><p class="caption" id="formatExplanation"></p>`);
  installCustomMatchups();
  installSprtEditor();
  let previewVersion=0,previewKey='';const previewNode=$('#totalPreview');
  $('.preview-total').insertAdjacentHTML('afterend',ArenaI18n.h('<p id="resourceAdvice" class="caption" role="status"></p><button id="useRecommended" type="button" hidden>Use recommended concurrency</button>'));
  const update=async()=>{
    const format=$('#tformat').value;
    syncKnockout();
    // Input and blur both fire for numeric fields. Do not disable Save again
    // when a click merely blurs an already-previewed value.
    let key;
    try{key=JSON.stringify([$('#tname').dataset.setupLoading,tournamentParticipantCount(),tournamentParticipantPayload(),formatSettings(),...['tformat','tcycles','tpaired','trounds','tcandidates','tconcurrency','tcpu','tmemory','tgpu','tponder','tpreset'].map(id=>[$('#'+id).value,$('#'+id).checked])])}catch(e){key=String(e)}
    if(key===previewKey)return;previewKey=key;
    const version=++previewVersion;
    $$('[data-format]').forEach(e=>e.hidden=!e.dataset.format.split(' ').includes(format));
    $('#formatExplanation').textContent=({swiss:ArenaI18n.t('Engine Swiss pairs similar scores, balances colors and avoids rematches unless approved. Byes add tournament points but never rated games. Buchholz and Sonneborn–Berger use opponent points per played game; this is not a FIDE Dutch pairing implementation.'),knockout:ArenaI18n.t('KO uses a seeded bracket and the game count chosen for each round. Tied matches keep playing; standings tiebreaks only order the results table and never select a KO match winner.'),double_elimination:ArenaI18n.t('Two-loss elimination keeps unbeaten and once-defeated groups separate, with byes as needed. A final reset is played when the finalist earns their first loss.'),ladder:ArenaI18n.t('Challenge starting positions rotate each round. Drawn challenges leave ladder positions unchanged. Standings follow ladder position.')})[format]||ArenaI18n.t('Standings use game points followed by the selected tiebreaks. Initial seed is the final deterministic fallback.');
    $('#createTournament').disabled=true;$('#totalPreview').textContent=ArenaI18n.t('Calculating…');
    try{
      const n=tournamentParticipantCount();
      const settings={...formatSettings(),format,cycles:Number($('#tcycles').value),paired:$('#tpaired').checked,rounds:Number($('#trounds').value),candidates:Number($('#tcandidates').value)};
      const r=await api('schedule-preview',{participants:n,settings});
      if(version!==previewVersion||$('#totalPreview')!==previewNode)return;
      $('#totalPreview').textContent=BigInt(r.scheduled_games).toLocaleString(ArenaI18n.locale);
      $('#resourcePreview').textContent=ArenaI18n.m`${n.toLocaleString(ArenaI18n.locale)} participants · up to ${Number($('#tconcurrency').value)*2} engine processes.${r.unbounded?ArenaI18n.t(' Regular games shown; tiebreaks continue until a winner, with no fixed maximum.'):r.conditional?ArenaI18n.t(' Up to ')+BigInt(r.maximum_games).toLocaleString(ArenaI18n.locale)+ArenaI18n.t(' games if all conditional finals and playoffs are needed.'):''}`;
      $('#createTournament').disabled=$('#tname').dataset.setupLoading==='true';
      const resources=await api('resource-preview',{...tournamentParticipantPayload(),resource_preset:$('#tpreset').value!==''?state.presets[Number($('#tpreset').value)].settings:null,settings:{format,ponder:$('#tponder').checked,cpu_budget:Number($('#tcpu').value),memory_budget_mb:Number($('#tmemory').value),gpu_limits:Object.fromEntries($('#tgpu').value.split(',').filter(v=>v.trim()).map(v=>{const [name,count]=v.split(':');return [name.trim(),Number(count)];}))}});
      if(version!==previewVersion||$('#totalPreview')!==previewNode)return;
      $('#resourceAdvice').textContent=resources.recommended===null?resources.note:ArenaI18n.m`Recommended: ${resources.recommended} concurrent games · limited by ${resources.limiting.join(', ')}. ${resources.logical_cpus} logical CPUs; ${Math.floor(resources.available_mb/1024)} GiB memory available. Estimated worst pairing: ${resources.worst_pair_threads} CPU threads and ${resources.worst_pair_memory_mb.toLocaleString(ArenaI18n.locale)} MB. ${resources.note}${resources.recommended===0?ArenaI18n.t(' Increase the limiting budget or reduce the engine allocation before starting.'):''}`;
      $('#useRecommended').hidden=!resources.recommended;$('#useRecommended').onclick=()=>{$('#tconcurrency').value=resources.recommended;update();};
    }catch(e){if(version===previewVersion&&$('#totalPreview')===previewNode){previewKey='';$('#totalPreview').textContent=ArenaI18n.t('Check settings');$('#resourcePreview').textContent=e.message;}}
  };
  const syncKnockout=installKnockoutEditor(update);
  ['tformat','tcycles','tpaired','trounds','tcandidates','tconcurrency','tcpu','tmemory','tgpu','tponder'].forEach(id=>{if($('#'+id)){$('#'+id).onchange=update;if($('#'+id).type==='number')$('#'+id).oninput=update;}});
  $$('#formatFields input, #formatFields select').forEach(e=>{e.onchange=update;if(e.type==='number')e.oninput=update;});
  const presetChanged=$('#tpreset').onchange;$('#tpreset').onchange=async()=>{presetChanged?.();await update();};
  $('#tname').refreshSetup=update;
  await update();
};
$('#newTournament').onclick=safely(newTournament);
$('#exportPgn').insertAdjacentHTML('beforebegin',ArenaI18n.h('<button id="pairingReview">Pairings & tiebreaks</button>'));
$('#pairingReview').onclick=safely(()=>{if(state.tid)return reviewPairings(state.tid);});
$('#tournamentNote').insertAdjacentHTML('afterend',ArenaI18n.h('<p id="formatStatus" class="caption"></p>'));
function renderFormatStatus(t){
  const s=t.settings,extra=s.format==='swiss'?ArenaI18n.m` · Bye points shown separately · ${s.swiss_rematches?ArenaI18n.t('rematches allowed'):ArenaI18n.t('rematches require approval')}`:s.format==='self_play'?ArenaI18n.t(' · Self-play results use White perspective; no between-engine Elo inference'):s.format==='ladder'?ArenaI18n.t(' · Ordered by ladder position'):'';
  $('#formatStatus').textContent=ArenaI18n.m`${tournamentFormatName(s.format)} · ${s.seeding==='random'?ArenaI18n.t('Seeded shuffle'):ArenaI18n.t('Selection-order seeds')} · Tiebreaks: ${(s.tiebreaks||['wins','seed']).map(k=>tieLabels[k]).join(' → ')}${extra}`;
  if(t.knockout)$('#formatStatus').textContent=ArenaI18n.m`${tournamentFormatName(s.format)} · ${s.seeding==='random'?ArenaI18n.t('Seeded shuffle'):ArenaI18n.t('Selection-order seeds')} · ${s.knockout_tiebreak==='continuous'?ArenaI18n.t('Tied matches keep playing until a winner'):ArenaI18n.t('Recorded match tiebreak: ')+(s.knockout_tiebreak||'seed')} · Game statistics include regular matches and tiebreaks.`;
}
async function reviewPairings(tid,offset=0){
  const r=await api(`tournaments/${tid}/pairings?offset=${offset}`),dynamic=['swiss','knockout','double_elimination','ladder'].includes(r.format);
  const number=a=>Number(a)+1, names=new Map(r.participants.map(p=>[p.slot,p.name]));
  const label=a=>`#${number(a)}${names.has(a)?' '+names.get(a):''}`;
  const editable=r.format==='swiss'&&r.state==='paused'&&r.ready&&r.next_round!==null&&r.next_kind!=='completed';
  // Fixed schedules can run rounds concurrently; their dynamic round counter
  // stays at zero and is not a meaningful progress indicator.
  const roundLabel=dynamic?' · '+(r.round<0?ArenaI18n.t('No round scheduled'):ArenaI18n.t('Round ')+(r.round+1)):'';
  modal(ArenaI18n.t('Pairings & tiebreaks'),ArenaI18n.h`<p>${esc(tournamentFormatName(r.format))}${roundLabel} · ${esc(ArenaI18n.message(r.state))}</p>
    ${r.attention?ArenaI18n.h`<p class="pairing-attention">${esc(r.attention)}</p>`:''}
    <p class="caption">${dynamic?ArenaI18n.t('Recorded pairings and decisions are retained with every attempt. Participant numbers below are stable, even when standings change.'):ArenaI18n.t('This format uses an incremental fixed schedule. Games and opening pairs are listed in the tournament history.')}</p>
    ${r.matches.length?ArenaI18n.h`<div class="table-scroll"><table><thead><tr><th>FIRST COLOR</th><th>OPPONENT</th><th>PLAYOFF STAGES</th><th>MANUAL WINNER</th></tr></thead><tbody>${r.matches.map(m=>ArenaI18n.h`<tr><td>#${number(m.a)} ${esc(m.a_name)}</td><td>#${number(m.b)} ${esc(m.b_name)}</td><td>${m.playoff_stages}</td><td>${m.manual_winner===null?'—':'#'+number(m.manual_winner)}</td></tr>`).join('')}</tbody></table></div>`:''}
    ${r.byes.length?ArenaI18n.h`<p>${r.format==='ladder'?ArenaI18n.t('Resting participants'):ArenaI18n.t('Byes')}: ${r.byes.map(a=>'#'+number(a)).join(', ')}</p>`:''}
    ${r.ladder_order?ArenaI18n.h`<p>Ladder order: ${r.ladder_order.map(a=>'#'+number(a)).join(' → ')}</p>`:''}
    ${r.manual_tie_count?ArenaI18n.h`<p class="caption">Manual tiebreaks ${offset<r.manual_tie_count?offset+1:0}–${Math.min(offset+50,r.manual_tie_count)} of ${r.manual_tie_count}. Use the page controls to review further decisions.</p>`:''}
    ${r.manual_ties.map(([a,b])=>ArenaI18n.h`<div class="pairing-decision"><label>Winner of ${esc(label(a))} / ${esc(label(b))}<select id="winner-${a}-${b}"><option value="">Choose winner…</option><option value="${a}">${esc(label(a))}</option><option value="${b}">${esc(label(b))}</option></select></label><button data-winner="${a},${b}" ${r.state==='paused'?'':'disabled'}>Record decision</button></div>`).join('')}
    ${editable?ArenaI18n.h`<div class="section-label">EDIT NEXT SWISS ROUND (${r.next_round+1})</div><p class="caption">One pair per line: White participant number, space, Black participant number. Include every participant exactly once, including the bye. Paired tests also play the reverse colors. Saved edits do not start games; use Start / resume.</p><label>Pairings<textarea id="manualPairs" rows="8" spellcheck="false">${esc((r.next_matches||[]).map(([a,b])=>`${number(a)} ${number(b)}`).join('\n'))}</textarea></label><label>Bye participant number (odd fields only)<input id="manualByes" value="${r.next_byes.map(number).join(', ')}"></label><label><input id="approveRematches" type="checkbox"> I approve any rematches in this edited round</label><button class="primary" id="saveManualRound">Save edited round</button>`:''}
    <div class="section-label">PARTICIPANT NUMBERS</div><div class="table-scroll"><table><thead><tr><th>NUMBER</th><th>INITIAL SEED</th><th>ENGINE PROFILE</th></tr></thead><tbody>${r.participants.map(p=>ArenaI18n.h`<tr><td>#${number(p.slot)}</td><td>${p.seed}</td><td>${esc(p.name)}</td></tr>`).join('')}</tbody></table></div>
    <div class="pager"><button id="pairingPrev" ${offset?'':'disabled'}>←</button><span>${r.participant_count?offset+1:0}–${Math.min(offset+50,r.participant_count)} of ${r.participant_count.toLocaleString(ArenaI18n.locale)} participants</span><button id="pairingNext" ${offset+50<Math.max(r.participant_count,r.match_count,r.manual_tie_count)?'':'disabled'}>→</button></div><p class="pairing-error" id="pairingError" role="alert"></p>`,ArenaI18n.h`<button id="pairingsText">Current review · Text…</button><button id="refreshPairings">Refresh review</button>`);
  $('#pairingsText').onclick=()=>{const content=htmlReportText($('#modalContent').innerHTML),name=state.snapshot?.name||tid;return textExport(ArenaI18n.t('Pairings and tiebreaks'),()=>ArenaText.report(name+ArenaI18n.t(' — Pairings and tiebreaks'),[ArenaI18n.m`Scope: current review page, participants ${r.participant_count?offset+1:0}–${Math.min(offset+50,r.participant_count)} of ${r.participant_count}. Unsaved edits and controls are excluded.`,content]))};
  const guarded=fn=>async()=>{try{await fn();}catch(e){$('#pairingError').textContent=e.message;}};
  $('#pairingPrev').onclick=safely(()=>reviewPairings(tid,Math.max(0,offset-50)));$('#pairingNext').onclick=safely(()=>reviewPairings(tid,offset+50));$('#refreshPairings').onclick=safely(()=>reviewPairings(tid,offset));
  $$('[data-winner]').forEach(e=>e.onclick=guarded(async()=>{const [a,b]=e.dataset.winner.split(',').map(Number),value=$(`#winner-${a}-${b}`).value;if(value==='')throw Error(ArenaI18n.t('Choose a winner before recording the decision.'));await api(`tournaments/${tid}/pairings`,{action:'manual_winner',a,b,winner:Number(value)});await reviewPairings(tid,offset);await refreshTournament();}));
  if(editable)$('#saveManualRound').onclick=guarded(async()=>{
    const parse=v=>{if(!/^\d+$/.test(v)||Number(v)<1||!Number.isSafeInteger(Number(v)))throw Error(ArenaI18n.t('Use positive whole participant numbers.'));return Number(v)-1;};
    const matches=$('#manualPairs').value.trim().split('\n').filter(v=>v.trim()).map(line=>{const pair=line.trim().split(/[\s,]+/);if(pair.length!==2)throw Error(ArenaI18n.t('Each pairing line must contain exactly two participant numbers.'));return pair.map(parse);});
    const byes=$('#manualByes').value.trim().split(/[\s,]+/).filter(Boolean).map(parse);
    await api(`tournaments/${tid}/pairings`,{action:'manual_round',matches,byes,allow_rematches:$('#approveRematches').checked,signature:r.signature});await reviewPairings(tid,offset);await refreshTournament();
  });
}
