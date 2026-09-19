'use strict';
// Tournament policy controls and audited round review. Slots remain stable when
// standings or seeds change; the review labels them as participant numbers.
const tieLabels={wins:'Wins',black_wins:'Wins with Black',buchholz:'Buchholz',sonneborn_berger:'Sonneborn–Berger',seed:'Initial seed'};
function formatSettings(){
  return {seeding:$('#fseeding')?.value||'input',tiebreaks:$$('[data-tiebreak]').map(e=>e.value).filter(Boolean),
    bye_score:Number($('#fbye')?.value??1),swiss_rematches:$('#frematches')?.checked||false,
    knockout_tiebreak:$('#fknockout')?.value||'seed',playoff_limit:Number($('#fplayoffLimit')?.value??3),
    playoff_cycles:Number($('#fplayoffCycles')?.value??1),playoff_fallback:$('#ffallback')?.value||'seed',
    ladder_distance:Number($('#fdistance')?.value??1),ladder_swap:$('#fmovement')?.value||'adjacent'};
}
const baseTournamentEditor=newTournament;
newTournament=async function(){
  await baseTournamentEditor();
  const options=(values,selected)=>Object.entries(values).map(([v,label])=>`<option value="${v}" ${v===selected?'selected':''}>${label}</option>`).join('');
  $('.preview-total').insertAdjacentHTML('beforebegin',`<div class="section-label">PAIRING & RANKING POLICIES</div><div class="fields" id="formatFields">
    <label>Initial seeding<select id="fseeding"><option value="input">Engine selection order</option><option value="random">Shuffle using tournament seed</option></select></label>
    ${Array.from({length:5},(_,i)=>`<label>Standings tiebreak ${i+1}<select data-tiebreak>${options({'':'None',...tieLabels},i===0?'wins':i===1?'seed':'')}</select></label>`).join('')}
    <label data-format="swiss">Bye points per scheduled game<select id="fbye"><option value="1">1 point</option><option value="0.5">½ point</option><option value="0">0 points</option></select></label>
    <label data-format="swiss"><input type="checkbox" id="frematches"> Allow Swiss rematches automatically</label>
    <label data-format="knockout double_elimination">Tied knockout matchup<select id="fknockout">${options({...tieLabels,playoff:'Play additional games',manual:'Pause for manual winner'},'seed')}</select></label>
    <label data-format="knockout double_elimination">Maximum playoff stages<input id="fplayoffLimit" type="number" value="3" min="1" step="1"></label>
    <label data-format="knockout double_elimination">Opening cycles per playoff stage<input id="fplayoffCycles" type="number" value="1" min="1" step="1"></label>
    <label data-format="knockout double_elimination">If all playoff stages are tied<select id="ffallback"><option value="seed">Higher initial seed advances</option><option value="manual">Pause for manual winner</option></select></label>
    <label data-format="ladder">Challenge distance (ladder places)<input id="fdistance" type="number" value="1" min="1" step="1"></label>
    <label data-format="ladder">Successful lower-ranked challenger<select id="fmovement"><option value="adjacent">Swap the two ladder positions</option><option value="leap">Take opponent's place; shift others down</option></select></label>
    </div><p class="caption" id="formatExplanation"></p>`);
  let previewVersion=0;const previewNode=$('#totalPreview');
  $('.preview-total').insertAdjacentHTML('afterend','<p id="resourceAdvice" class="caption" role="status"></p><button id="useRecommended" type="button" hidden>Use recommended concurrency</button>');
  const update=async()=>{
    const version=++previewVersion,format=$('#tformat').value;
    $$('[data-format]').forEach(e=>e.hidden=!e.dataset.format.split(' ').includes(format));
    $('#formatExplanation').textContent=({swiss:'Engine Swiss pairs similar scores, balances colors and avoids rematches unless approved. Byes add tournament points but never rated games. Buchholz and Sonneborn–Berger use opponent points per played game; this is not a FIDE Dutch pairing implementation.',knockout:'Single elimination uses a seeded bracket. Playoffs preserve the selected opening and color-pair policy. Manual decisions are recorded in the tournament audit.',double_elimination:'Two-loss elimination keeps unbeaten and once-defeated groups separate, with byes as needed. A final reset is played when the finalist earns their first loss.',ladder:'Challenge starting positions rotate each round. Drawn challenges leave ladder positions unchanged. Standings follow ladder position.'})[format]||'Standings use game points followed by the selected tiebreaks. Initial seed is the final deterministic fallback.';
    $('#createTournament').disabled=true;$('#totalPreview').textContent='Calculating…';
    try{
      const n=$('#allProfiles').checked?state.libraryTotal:state.selected.size;
      const settings={...formatSettings(),format,cycles:Number($('#tcycles').value),paired:$('#tpaired').checked,rounds:Number($('#trounds').value),candidates:Number($('#tcandidates').value)};
      const r=await api('schedule-preview',{participants:n,settings});
      if(version!==previewVersion||$('#totalPreview')!==previewNode)return;
      $('#totalPreview').textContent=BigInt(r.scheduled_games).toLocaleString();
      $('#resourcePreview').textContent=`${n.toLocaleString()} participants · up to ${Number($('#tconcurrency').value)*2} engine processes.${r.conditional?' Up to '+BigInt(r.maximum_games).toLocaleString()+' games if all conditional finals and playoffs are needed.':''}`;
      $('#createTournament').disabled=false;
      const resources=await api('resource-preview',{profiles:[...state.selected],all_profiles:$('#allProfiles').checked,resource_preset:$('#tpreset').value!==''?state.presets[Number($('#tpreset').value)].settings:null,settings:{format,ponder:$('#tponder').checked,cpu_budget:Number($('#tcpu').value),memory_budget_mb:Number($('#tmemory').value),gpu_limits:Object.fromEntries($('#tgpu').value.split(',').filter(v=>v.trim()).map(v=>{const [name,count]=v.split(':');return [name.trim(),Number(count)];}))}});
      if(version!==previewVersion||$('#totalPreview')!==previewNode)return;
      $('#resourceAdvice').textContent=resources.recommended===null?resources.note:`Recommended: ${resources.recommended} concurrent games · limited by ${resources.limiting.join(', ')}. ${resources.logical_cpus} logical CPUs; ${Math.floor(resources.available_mb/1024)} GiB memory available. Estimated worst pairing: ${resources.worst_pair_threads} CPU threads and ${resources.worst_pair_memory_mb.toLocaleString()} MB. ${resources.note}${resources.recommended===0?' Increase the limiting budget or reduce the engine allocation before starting.':''}`;
      $('#useRecommended').hidden=!resources.recommended;$('#useRecommended').onclick=()=>{$('#tconcurrency').value=resources.recommended;update();};
    }catch(e){if(version===previewVersion&&$('#totalPreview')===previewNode){$('#totalPreview').textContent='Check settings';$('#resourcePreview').textContent=e.message;}}
  };
  ['tformat','tcycles','tpaired','trounds','tcandidates','tconcurrency','tcpu','tmemory','tgpu','tponder'].forEach(id=>{if($('#'+id)){$('#'+id).onchange=update;if($('#'+id).type==='number')$('#'+id).oninput=update;}});
  $$('#formatFields input, #formatFields select').forEach(e=>{e.onchange=update;if(e.type==='number')e.oninput=update;});
  const presetChanged=$('#tpreset').onchange;$('#tpreset').onchange=async()=>{presetChanged?.();await update();};
  await update();
};
$('#newTournament').onclick=safely(newTournament);
$('#exportPgn').insertAdjacentHTML('beforebegin','<button id="pairingReview">Pairings & tiebreaks</button>');
$('#pairingReview').onclick=safely(()=>{if(state.tid)return reviewPairings(state.tid);});
$('#tournamentNote').insertAdjacentHTML('afterend','<p id="formatStatus" class="caption"></p>');
function renderFormatStatus(t){
  const s=t.settings,extra=s.format==='swiss'?` · Bye points shown separately · ${s.swiss_rematches?'rematches allowed':'rematches require approval'}`:s.format==='self_play'?' · Self-play results use White perspective; no between-engine Elo inference':s.format==='ladder'?' · Ordered by ladder position':'';
  $('#formatStatus').textContent=`${s.format.replaceAll('_',' ')} · ${s.seeding==='random'?'Seeded shuffle':'Selection-order seeds'} · Tiebreaks: ${(s.tiebreaks||['wins','seed']).map(k=>tieLabels[k]).join(' → ')}${extra}`;
}
async function reviewPairings(tid,offset=0){
  const r=await api(`tournaments/${tid}/pairings?offset=${offset}`),dynamic=['swiss','knockout','double_elimination','ladder'].includes(r.format);
  const number=a=>Number(a)+1, names=new Map(r.participants.map(p=>[p.slot,p.name]));
  const label=a=>`#${number(a)}${names.has(a)?' '+names.get(a):''}`;
  const editable=r.format==='swiss'&&r.state==='paused'&&r.ready&&r.next_round!==null&&r.next_kind!=='completed';
  modal('Pairings & tiebreaks',`<p>${esc(r.format.replaceAll('_',' '))} · ${r.round<0?'No round scheduled':'Round '+(r.round+1)} · ${esc(r.state)}</p>
    ${r.attention?`<p class="pairing-attention">${esc(r.attention)}</p>`:''}
    <p class="caption">${dynamic?'Recorded pairings and decisions are retained with every attempt. Participant numbers below are stable, even when standings change.':'This format uses an incremental fixed schedule. Games and opening pairs are listed in the tournament history.'}</p>
    ${r.matches.length?`<div class="table-scroll"><table><thead><tr><th>FIRST COLOR</th><th>OPPONENT</th><th>PLAYOFF STAGES</th><th>MANUAL WINNER</th></tr></thead><tbody>${r.matches.map(m=>`<tr><td>#${number(m.a)} ${esc(m.a_name)}</td><td>#${number(m.b)} ${esc(m.b_name)}</td><td>${m.playoff_stages}</td><td>${m.manual_winner===null?'—':'#'+number(m.manual_winner)}</td></tr>`).join('')}</tbody></table></div>`:''}
    ${r.byes.length?`<p>${r.format==='ladder'?'Resting participants':'Byes'}: ${r.byes.map(a=>'#'+number(a)).join(', ')}</p>`:''}
    ${r.ladder_order?`<p>Ladder order: ${r.ladder_order.map(a=>'#'+number(a)).join(' → ')}</p>`:''}
    ${r.manual_tie_count?`<p class="caption">Manual tiebreaks ${offset<r.manual_tie_count?offset+1:0}–${Math.min(offset+50,r.manual_tie_count)} of ${r.manual_tie_count}. Use the page controls to review further decisions.</p>`:''}
    ${r.manual_ties.map(([a,b])=>`<div class="pairing-decision"><label>Winner of ${esc(label(a))} / ${esc(label(b))}<select id="winner-${a}-${b}"><option value="">Choose winner…</option><option value="${a}">${esc(label(a))}</option><option value="${b}">${esc(label(b))}</option></select></label><button data-winner="${a},${b}" ${r.state==='paused'?'':'disabled'}>Record decision</button></div>`).join('')}
    ${editable?`<div class="section-label">EDIT NEXT SWISS ROUND (${r.next_round+1})</div><p class="caption">One pair per line: White participant number, space, Black participant number. Include every participant exactly once, including the bye. Paired tests also play the reverse colors. Saved edits do not start games; use Start / resume.</p><label>Pairings<textarea id="manualPairs" rows="8" spellcheck="false">${esc((r.next_matches||[]).map(([a,b])=>`${number(a)} ${number(b)}`).join('\n'))}</textarea></label><label>Bye participant number (odd fields only)<input id="manualByes" value="${r.next_byes.map(number).join(', ')}"></label><label><input id="approveRematches" type="checkbox"> I approve any rematches in this edited round</label><button class="primary" id="saveManualRound">Save edited round</button>`:''}
    <div class="section-label">PARTICIPANT NUMBERS</div><div class="table-scroll"><table><thead><tr><th>NUMBER</th><th>INITIAL SEED</th><th>ENGINE PROFILE</th></tr></thead><tbody>${r.participants.map(p=>`<tr><td>#${number(p.slot)}</td><td>${p.seed}</td><td>${esc(p.name)}</td></tr>`).join('')}</tbody></table></div>
    <div class="pager"><button id="pairingPrev" ${offset?'':'disabled'}>←</button><span>${r.participant_count?offset+1:0}–${Math.min(offset+50,r.participant_count)} of ${r.participant_count.toLocaleString()} participants</span><button id="pairingNext" ${offset+50<Math.max(r.participant_count,r.match_count,r.manual_tie_count)?'':'disabled'}>→</button></div><p class="pairing-error" id="pairingError" role="alert"></p>`,`<button id="refreshPairings">Refresh review</button>`);
  const guarded=fn=>async()=>{try{await fn();}catch(e){$('#pairingError').textContent=e.message;}};
  $('#pairingPrev').onclick=safely(()=>reviewPairings(tid,Math.max(0,offset-50)));$('#pairingNext').onclick=safely(()=>reviewPairings(tid,offset+50));$('#refreshPairings').onclick=safely(()=>reviewPairings(tid,offset));
  $$('[data-winner]').forEach(e=>e.onclick=guarded(async()=>{const [a,b]=e.dataset.winner.split(',').map(Number),value=$(`#winner-${a}-${b}`).value;if(value==='')throw Error('Choose a winner before recording the decision.');await api(`tournaments/${tid}/pairings`,{action:'manual_winner',a,b,winner:Number(value)});await reviewPairings(tid,offset);await refreshTournament();}));
  if(editable)$('#saveManualRound').onclick=guarded(async()=>{
    const parse=v=>{if(!/^\d+$/.test(v)||Number(v)<1||!Number.isSafeInteger(Number(v)))throw Error('Use positive whole participant numbers.');return Number(v)-1;};
    const matches=$('#manualPairs').value.trim().split('\n').filter(v=>v.trim()).map(line=>{const pair=line.trim().split(/[\s,]+/);if(pair.length!==2)throw Error('Each pairing line must contain exactly two participant numbers.');return pair.map(parse);});
    const byes=$('#manualByes').value.trim().split(/[\s,]+/).filter(Boolean).map(parse);
    await api(`tournaments/${tid}/pairings`,{action:'manual_round',matches,byes,allow_rematches:$('#approveRematches').checked,signature:r.signature});await reviewPairings(tid,offset);await refreshTournament();
  });
}
