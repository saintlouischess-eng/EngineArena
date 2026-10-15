'use strict';
function renderTournamentEdit(t){
 const button=$('#editTournament');button.disabled=!t?.can_edit;
 button.title=t?.can_edit?ArenaI18n.t('Edit this saved tournament before starting it.'):ArenaI18n.t('Setup is locked after the first start or scheduled game.');
}
$('#tournamentPicker').addEventListener('change',()=>renderTournamentEdit(null));
$('#editTournament').onclick=safely(async()=>{
 if(!state.tid)return;
 const draft=await api(`tournaments/${state.tid}/setup`);
 await newTournament(draft);
});

const completeTournamentEditor=newTournament;
newTournament=async function(draft=null){
 await completeTournamentEditor(draft);
 if(!draft?.id||!$('#tname'))return;
 const s=draft.settings;
 $('#dialogTitle').textContent=ArenaI18n.t('Edit tournament setup');
 $('#createTournament').textContent=ArenaI18n.t('Save changes');
 $('#createTournament').disabled=true;
 const value=(id,v)=>{if($('#'+id)&&v!==undefined)$('#'+id).value=v};
 const checked=(id,v)=>{if($('#'+id)&&v!==undefined)$('#'+id).checked=v};
 value('tname',draft.name);
 for(const [id,key] of Object.entries({tformat:'format',tcycles:'cycles',trounds:'rounds',tcandidates:'candidates',tseed:'seed',torder:'opening_order',tconcurrency:'concurrency',tretries:'retry_limit',tcpu:'cpu_budget',tmemory:'memory_budget_mb',tstop:'stop_timeout',tstartup:'startup_timeout',tready:'readiness_timeout',thang:'hang_timeout',ttolerance:'tolerance',toverhead:'overhead',tmaxplies:'max_plies',tresign:'resign_cp',tresignPlies:'resign_plies',tdraw:'draw_cp',tdrawPlies:'draw_plies',tdrawAfter:'draw_after',tsyzygy:'syzygy_path',fseeding:'seeding',fbye:'bye_score',fdistance:'ladder_distance',fmovement:'ladder_swap'}))value(id,s[key]);
 for(const [id,key] of Object.entries({tpaired:'paired',tEngineBooks:'use_engine_books',tponder:'ponder',tannotations:'annotations',tclaim:'claim_draws',frematches:'swiss_rematches',tfile960:'chess960'}))checked(id,s[key]);
 value('tgpu',Object.entries(s.gpu_limits||{}).map(([group,count])=>`${group}:${count}`).join(', '));
 value('telo0',s.sprt.elo0);value('telo1',s.sprt.elo1);
 value('sprtCandidate',s.sprt_candidate??0);value('sprtAlpha',100*s.sprt.alpha);value('sprtBeta',100*s.sprt.beta);
 $$('[data-tiebreak]').forEach((e,i)=>e.value=s.tiebreaks[i]||'');
 $('#tcontrol').innerHTML=tcEditor('ttc',s.time_control);wireTc('ttc');
 if(s.opening_policy==='legacy')$('#openingPreset').add(new Option(ArenaI18n.t('Recorded legacy opening assignment'),'legacy'));
 value('openingPreset',s.opening_policy||'legacy');
 $('#topeningSource').add(new Option(ArenaI18n.t('Keep recorded opening positions'),'recorded'));
 value('topeningSource','recorded');value('tdepth',s.opening_source?.depth??16);
 $('#topeningSource').closest('label').insertAdjacentHTML('afterend',ArenaI18n.h`<p class="caption">${ArenaI18n.t('Recorded opening source')}: ${esc(s.opening_source?.name||ArenaI18n.t('Saved positions'))} · ${draft.opening_count.toLocaleString(ArenaI18n.locale)} ${ArenaI18n.t('positions')}. ${ArenaI18n.t('The saved positions remain available even if the original file has moved. Choose another source to replace them.')}</p>`);
 const participants=$('#tParticipantSummary').closest('.field');
 participants.innerHTML=ArenaI18n.h`<label for="editParticipants">Participants</label><select id="editParticipants" data-help="Keep the recorded engine profiles, or replace them with the profiles currently selected in Engine library. Applying a resource preset also updates their thread and hash allocations."><option value="saved">Keep saved engines and settings</option><option value="library">Use current Engine library selection</option></select><small id="editParticipantCount"></small><small>Select replacement engines in Engine library before opening this editor. Their current profiles will be copied when you save.</small>`;
 const describe=()=>$('#editParticipantCount').textContent=ArenaI18n.m`${tournamentParticipantCount().toLocaleString(ArenaI18n.locale)} participants`;
 $('#editParticipants').onchange=async()=>{describe();await $('#tname').refreshSetup();await $('#sprtSetup').refresh();$('#analyzeOpenings').click()};describe();
 $('#koConfig').loadSetup(s);
 $('#topeningSource').dispatchEvent(new Event('change',{bubbles:true}));
 $('#tformat').dispatchEvent(new Event('change',{bubbles:true}));
 $('#tname').dataset.setupLoading='false';
 await $('#tname').refreshSetup();
};
$('#newTournament').onclick=safely(newTournament);
