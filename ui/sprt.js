'use strict';
function sprtSettings(){return {sprt_candidate:Number($('#sprtCandidate')?.value??tournamentDraft?.settings.sprt_candidate??0)}}
function installSprtEditor(){
 const fields=$('#telo0').closest('.fields'),box=document.createElement('div');box.id='sprtSetup';
 box.innerHTML=ArenaI18n.h`<div class="section-label">Two-engine SPRT</div><div class="fields" id="sprtFields"><div class="field"><label for="sprtCandidate">Tested engine</label><select id="sprtCandidate"><option value="0">#1</option><option value="1">#2</option></select></div></div><p class="caption">Positive Elo favors the tested engine. H0 and H1 are test hypotheses, not confidence limits or probabilities of superiority.</p><p class="caption">The game count is a maximum. Reaching it without a boundary gives an inconclusive result. New tests admit results in scheduled order; paired tests wait for both games and prescribed retries.</p><p class="caption" id="sprtModel"></p>`;
 fields.after(box);const target=box.querySelector('.fields');for(const id of ['telo0','telo1'])target.append($('#'+id).closest('.field'));
 target.insertAdjacentHTML('beforeend',field('sprtAlpha',ArenaI18n.t('False positive target α (%)'),5,'number','min="0.001" max="99.999" step="any"')+field('sprtBeta',ArenaI18n.t('False negative target β (%)'),5,'number','min="0.001" max="99.999" step="any"'));
 $('#sprtAlpha').dataset.help=ArenaI18n.t('Target risk of selecting H1 when H0 holds. Alpha and beta must be positive and sum to less than 100%.');
 $('#sprtBeta').dataset.help=ArenaI18n.t('Target risk of selecting H0 when H1 holds. These are nominal error targets, not posterior probabilities.');
 $('#sprtCandidate').dataset.help=ArenaI18n.t('All SPRT scores, hypotheses and the likelihood graph use this engine relative to the other engine.');
 const refresh=async()=>{
  box.hidden=$('#tformat').value!=='sprt';if(box.hidden)return;
  const label=$('#tcycles').closest('.field').querySelector('label');label.textContent=$('#tpaired').checked?ArenaI18n.t('Maximum opening pairs'):ArenaI18n.t('Maximum games');
  $('#sprtModel').textContent=$('#tpaired').checked?ArenaI18n.t('Logistic Elo · pentanomial opening-pair model'):ArenaI18n.t('Logistic Elo · trinomial individual-game model');
  const payload=tournamentParticipantPayload(),rows=await api('selected-participants',{...payload,recorded_participants:payload.keep_participants?tournamentDraft.id:payload.recorded_participants});
  if(!box.isConnected)return;
  for(const option of $('#sprtCandidate').options){const row=rows.find(p=>p.slot===Number(option.value));option.textContent='#'+(Number(option.value)+1)+' · '+(row?.name||'—')}
 };
 $('#tformat').addEventListener('change',()=>{if($('#tformat').value!=='sprt')$('#tcycles').closest('.field').querySelector('label').textContent=ArenaI18n.t('Opening pairs per matchup');safely(refresh)()});
 $('#tpaired').addEventListener('change',safely(refresh));
 box.refresh=refresh;safely(refresh)();
}

function renderSprt(t){
 let panel=$('#sprtPanel');if(!panel){panel=document.createElement('section');panel.id='sprtPanel';panel.className='panel';$('#formatStatus').after(panel)}
 // Run-button state is owned by updateRunControls, including SPRT freezes.
 panel.hidden=!t.sprt_status;if(panel.hidden)return;
 const s=t.sprt_status,e=t.sprt,h=t.settings.sprt;
 const labels={H0:ArenaI18n.t('Lower hypothesis selected (H0)'),H1:ArenaI18n.t('Upper hypothesis selected (H1)'),invalidated:ArenaI18n.t('Sequential inference invalidated'),inconclusive:ArenaI18n.t('Inconclusive — game limit reached'),paused:ArenaI18n.t('Paused — no SPRT decision'),running:ArenaI18n.t('Test continuing'),draining:ArenaI18n.t('Draining — no SPRT decision')};
 const rows=[[ArenaI18n.t('Tested engine'),s.candidate],[ArenaI18n.t('Reference engine'),s.reference],[ArenaI18n.t('Hypotheses, Elo'),`H0: ${h.elo0} · H1: ${h.elo1}`],[ArenaI18n.t('False positive / false negative targets'),`α: ${fmt(100*h.alpha,3)}% · β: ${fmt(100*h.beta,3)}%`],[s.paired?ArenaI18n.t('Completed opening pairs'):ArenaI18n.t('Individual games'),fmt(s.samples,0)],[ArenaI18n.t('Log likelihood ratio'),fmt(e.llr,4)],[ArenaI18n.t('Lower / upper stopping boundaries'),`${fmt(e.lower,4)} / ${fmt(e.upper,4)}`],[ArenaI18n.t('Sample order'),s.order==='scheduled'?ArenaI18n.t('Scheduled order'):ArenaI18n.t('Legacy completion order')]];
 if(e.frozen)rows.push([ArenaI18n.t('Games outside frozen stopping evidence'),s.post_stop_games]);
 const expanded=panel.querySelector('details')?.open;
 stableHtml('#sprtPanel',`<div class="panel-title"><h2>${ArenaI18n.t('Two-engine SPRT')}</h2><strong role="status">${esc(labels[s.status]||s.status)}</strong></div><p>${ArenaI18n.t('Tested engine')}: <b>${esc(s.candidate)}</b> · ${ArenaI18n.t('Reference engine')}: ${esc(s.reference)}</p><p>LLR <b>${fmt(e.llr,4)}</b> · [${fmt(e.lower,4)}, ${fmt(e.upper,4)}] · ${fmt(s.samples,0)} ${s.paired?ArenaI18n.t('Completed opening pairs'):ArenaI18n.t('Individual games')}</p><details ${expanded?'open':''}><summary>${ArenaI18n.t('Test conditions')}</summary><div class="table-scroll"><table><tbody>${rows.map(([k,v])=>`<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join('')}</tbody></table></div></details><p class="caption">${esc(e.reason?ArenaI18n.message(e.reason):ArenaI18n.t('Positive Elo favors the tested engine. H0 and H1 are test hypotheses, not confidence limits or probabilities of superiority.'))}</p>`);
 if(t.progress?.status==='estimated')$('#etaMetric').textContent=ArenaI18n.t('ETA to game limit')+': '+ArenaResults.duration(t.progress.eta_seconds);
 $('#paceMetric').textContent=ArenaI18n.t('Progress and ETA refer to the game limit, not the SPRT stopping point.');
 if(e.frozen&&!s.can_diagnostic_start)$('#etaMetric').textContent=labels[s.status];
}
