'use strict';
// Setup-only work: no polling and no cost on the live game update path.
(() => {
 const selectionKey=()=>JSON.stringify([[...state.selected],$('#allProfiles').checked]);
 let active=null,queue=Promise.resolve(),lastSelection=selectionKey(),libraryTouched=false;
 document.addEventListener('change',e=>{if(e.target.matches('[data-engine],#allProfiles'))libraryTouched=true});
 document.addEventListener('click',e=>{if(e.target.closest('#bulkSelectAll,#bulkClearSelection'))libraryTouched=true},true);
 const originalModal=modal;
 modal=function(...args){if(active){active.save();active.dispose();active=null}return originalModal(...args)};
 const oldPayload=tournamentParticipantPayload;
 tournamentParticipantPayload=function(){const p=oldPayload();if(active&&$('#tformat')?.value==='gauntlet')p.candidate_ids=[...active.candidates];return p};
 const originalSave=saveTournamentSetup;
 saveTournamentSetup=async function(payload,draft){if(active&&!draft){await active.save();await queue}return originalSave(payload,draft)};
 document.addEventListener('arena-tournament-saved',()=>{
  if(!active||tournamentDraft)return;
  const session=active;session.dispose();active=null;
  queue=queue.catch(()=>{}).then(async()=>{await api('setup-draft',{revision:session.revision,value:null})}).catch(e=>notify(e.message,true));
 });
 const originalNew=newTournament;
 newTournament=async function(draft=null,fresh=false){
  if(active){await active.save().catch(()=>{});active.dispose();active=null}await queue.catch(()=>{});
  const saved=draft?.id?null:await api('setup-draft');
  if(fresh&&saved){const r=await api('setup-draft',{revision:saved.revision,value:null});saved.revision=r.revision;saved.value=null}
  const value=saved?.value;
  if(value){
   const libraryChanged=libraryTouched||lastSelection!==selectionKey();
   if(!libraryChanged){state.selected=new Set(value.selected||[]);$('#allProfiles').checked=!!value.all}
  }
  libraryTouched=false;
  const info=await api('profiles?limit=0');state.libraryTotal=info.library_total;
  await originalNew(draft);
  const root=$('#modal .modal-body'),name=$('#tname'),dialog=$('#modal');
  if(!name)return;
  const controller=new AbortController(),signal=controller.signal;
  const session={revision:saved?.revision,candidates:new Set((value?.candidates||[]).filter(id=>$('#allProfiles').checked||state.selected.has(id))),restoring:true,failed:false,dispose:()=>{clearTimeout(timer);clearTimeout(searchTimer);controller.abort()},save:()=>Promise.resolve()};active=session;
  root.insertAdjacentHTML('afterbegin',ArenaI18n.h`<div class="setup-draft-bar"><span id="setupDraftStatus" role="status">${draft?.id?ArenaI18n.t('Editing saved setup'):value?ArenaI18n.t('Unsaved setup restored'):ArenaI18n.t('Draft saves automatically')}</span><span class="spacer"></span>${!draft?.id?ArenaI18n.h('<button id="setupFresh">Start fresh</button><button id="setupLibrary">Engine library…</button>'):''}</div>`);
  const summary=$('#tParticipantSummary');if(summary)summary.parentElement.querySelector('small').textContent=ArenaI18n.t('Choose engines below without leaving tournament setup.');
  $('#tcandidates').closest('.field').classList.add('named-candidates-only');
  root.querySelector('.fields').insertAdjacentHTML('afterend',ArenaI18n.h`<details class="setup-engines" open><summary>Engine selection & gauntlet roles</summary><p class="caption">Choose participants, then mark candidates by name for a gauntlet. Candidates play the remaining opponents; candidates do not play each other.</p><div class="toolbar"><input id="setupSearch" placeholder="Search engine profiles…"><label><input id="setupSelected" type="checkbox"> Selected only</label><button id="setupAll">Use entire library</button><button id="setupClearEngines">Clear selection</button></div><p id="setupRoles" role="status"></p><div class="table-scroll setup-engine-table"><table><thead><tr><th>Play</th><th>Engine</th><th id="setupRoleHead">Candidate</th></tr></thead><tbody id="setupEngineRows"></tbody></table></div><div class="pager"><button id="setupPrev">←</button><span id="setupPage"></span><button id="setupNext">→</button></div></details>`);
  $('#ttolerance').closest('.field').insertAdjacentHTML('beforeend',ArenaI18n.h`<div class="tolerance-presets">${[0,.05,.25,.5,1].map(n=>`<button type="button" data-tolerance="${n}">${n} s</button>`).join('')}</div><small>Extra grace before a time forfeit, including fixed time per move. This is not engine Move Overhead. It does not add a clock to node-only games.</small>`);
  $('#tsyzygy').closest('.field').insertAdjacentHTML('beforeend',ArenaI18n.h`<p class="caption">GUI adjudication only: the referee can end covered positions. This does not configure engines or produce engine TB hits. Set each engine’s SyzygyPath in Engine library or Bulk settings for engine probing. Missing table files leave the game playing normally.</p>`);
  for(const b of $$('[data-tolerance]'))b.onclick=()=>{$('#ttolerance').value=b.dataset.tolerance;$('#ttolerance').dispatchEvent(new Event('input',{bubbles:true}))};
  const collect=()=>({version:1,selected:[...state.selected],all:$('#allProfiles').checked,candidates:[...session.candidates],
   fields:Object.fromEntries([...root.querySelectorAll('input[id],select[id],textarea[id]')].filter(e=>!e.id.startsWith('setup')).map(e=>[e.id,e.type==='checkbox'?e.checked:e.value])),
   preset:$('#tpreset').value!==''?state.presets[Number($('#tpreset').value)]:null,
   control:readTc('ttc'),ties:$$('[data-tiebreak]').map(e=>e.value),
   ko:{format:$('#tformat').value,knockout_tiebreak:'continuous',cycles:Number($('#tcycles').value),paired:$('#tpaired').checked,ko_round_games:$$('[data-ko-round]').map(e=>e.value),playoff_cycles:Number($('#koPlayoffGames').value)/($('#tpaired').checked?2:1),playoff_controls:$('#koControlMode').value==='sequence'?$$('#koStages .tc-editor').map(e=>readTc(e.id)):[],time_control:readTc('ttc')}});
  let timer,previous='',offset=0,request=0,searchTimer;
  session.save=()=>{
   if(draft?.id||session.restoring||session.failed||!name.isConnected)return queue;
   clearTimeout(timer);const value=collect(),key=JSON.stringify(value);lastSelection=selectionKey();if(previous===key)return queue;previous=key;
   const status=$('#setupDraftStatus');status.textContent=ArenaI18n.t('Saving draft…');
   queue=queue.catch(()=>{}).then(async()=>{
    if(session.failed)return;
    try{const r=await api('setup-draft',{revision:session.revision,value});session.revision=r.revision;if(status.isConnected)status.textContent=ArenaI18n.t('Draft saved — safe to close')}
    catch(e){session.failed=true;previous='';if(status.isConnected)status.textContent=ArenaI18n.t('Draft not saved: ')+e.message;throw e}
   });queue.catch(e=>notify(e.message,true));return queue;
  };
  const changed=()=>{if(!session.restoring){clearTimeout(timer);timer=setTimeout(()=>session.save(),300)}};
  const refresh=async()=>{
   const gauntlet=$('#tformat').value==='gauntlet';$('#tcandidates').value=gauntlet?session.candidates.size:Math.max(1,session.candidates.size);
   $('#setupRoleHead').hidden=!gauntlet;
   if(summary)summary.textContent=ArenaI18n.m`${tournamentParticipantCount()} participants`;
   $('#setupRoles').textContent=gauntlet?ArenaI18n.m`${session.candidates.size} candidates · ${Math.max(0,tournamentParticipantCount()-session.candidates.size)} opponents`:ArenaI18n.m`${tournamentParticipantCount()} participants`;
   $$('[data-role-cell]').forEach(e=>e.hidden=!gauntlet);
   await name.refreshSetup();if($('#sprtSetup')?.refresh)await $('#sprtSetup').refresh();changed();
  };
  const load=async()=>{
   const gen=++request,keep=oldPayload().keep_participants,selected=$('#setupSelected').checked||keep,q=$('#setupSearch').value;
   let rows,total;
   if(selected){
    // Selected pages use the same stable slot order as the schedule and custom pairs.
    const r=await api('participant-picker',{...oldPayload(),q,offset});rows=r.items;total=r.total;
   }else{const r=await api(`profiles?q=${encodeURIComponent(q)}&offset=${offset}&limit=50`);rows=r.items;total=r.total;state.libraryTotal=r.library_total}
   if(gen!==request||!name.isConnected)return;
   const all=$('#allProfiles').checked,gauntlet=$('#tformat').value==='gauntlet';
   $('#setupEngineRows').innerHTML=rows.map(p=>{const chosen=keep||all||state.selected.has(p.id);return `<tr><td><input type="checkbox" data-pick="${esc(p.id)}" aria-label="${esc(ArenaI18n.t('Play')+': '+p.name)}" ${chosen?'checked':''} ${keep?'disabled':''}></td><td>${esc(p.name)}</td><td data-role-cell ${gauntlet?'':'hidden'}><input type="checkbox" data-candidate="${esc(p.id)}" aria-label="${esc(ArenaI18n.t('Candidate')+': '+p.name)}" ${session.candidates.has(p.id)?'checked':''} ${chosen?'':'disabled'}></td></tr>`}).join('');
   $('#setupPage').textContent=`${total?offset+1:0}–${Math.min(offset+50,total)} / ${total}`;$('#setupPrev').disabled=!offset;$('#setupNext').disabled=offset+50>=total;
   $('#setupAll').disabled=keep;$('#setupClearEngines').disabled=keep;
   $$('[data-pick]').forEach(e=>e.onchange=safely(async()=>{if($('#allProfiles').checked){state.selected=new Set(await api('profiles/selection'));$('#allProfiles').checked=false}if(e.checked)state.selected.add(e.dataset.pick);else{state.selected.delete(e.dataset.pick);session.candidates.delete(e.dataset.pick)}await refresh();await load()}));
   $$('[data-candidate]').forEach(e=>e.onchange=safely(async()=>{if(e.checked)session.candidates.add(e.dataset.candidate);else session.candidates.delete(e.dataset.candidate);await refresh()}));
  };
  if(value){
   for(const [id,v] of Object.entries(value.fields||{})){const e=document.getElementById(id);if(!e||!root.contains(e))continue;if(e.type==='checkbox')e.checked=v;else e.value=v}
   if(value.preset){const index=state.presets.findIndex(p=>p.name===value.preset.name&&JSON.stringify(p.settings)===JSON.stringify(value.preset.settings));$('#tpreset').value=index<0?'':String(index);if(index<0)notify(ArenaI18n.t('The saved preset changed or was removed. Review resource settings before saving.'),true)}
   $('#tcontrol').innerHTML=tcEditor('ttc',value.control);wireTc('ttc');
   $$('[data-tiebreak]').forEach((e,i)=>e.value=value.ties?.[i]||'');
   await name.refreshSetup();$('#koConfig').loadSetup(value.ko);
   for(const id of ['topeningSource','openingPreset','scheduleOrder','koControlMode','autoPgnEnabled'])document.getElementById(id)?.dispatchEvent(new Event('change',{bubbles:true}));
  }else if(draft?.id&&draft.settings.format==='gauntlet'){
   for(let start=0;start<draft.settings.candidates;start+=50){const rows=await api('selected-participants',{...oldPayload(),offset:start});for(const p of rows)if(p.slot<draft.settings.candidates)session.candidates.add(p.id)}
  }
  // Newly selected gauntlets require an explicit named role; never infer it from a library row number.
  $('#setupSearch').oninput=()=>{clearTimeout(searchTimer);searchTimer=setTimeout(safely(async()=>{offset=0;await load()}),200)};
  $('#setupSelected').onchange=safely(async()=>{offset=0;await load()});
  $('#setupPrev').onclick=safely(async()=>{offset=Math.max(0,offset-50);await load()});$('#setupNext').onclick=safely(async()=>{offset+=50;await load()});
  $('#setupClearEngines').onclick=safely(async()=>{state.selected.clear();session.candidates.clear();$('#allProfiles').checked=false;offset=0;await refresh();await load()});
  $('#setupAll').onclick=safely(async()=>{$('#allProfiles').checked=true;offset=0;await refresh();await load()});
  $('#tformat').addEventListener('change',safely(async()=>{await refresh();await load()}),{signal});
  $('#editParticipants')?.addEventListener('change',safely(async()=>{session.candidates.clear();offset=0;await refresh();await load()}),{signal});
  if(!draft?.id){
   $('#setupFresh').onclick=safely(async()=>{session.dispose();active=null;await newTournament(null,true)});
   $('#setupLibrary').onclick=safely(async()=>{await session.save();lastSelection=selectionKey();dialog.close();view('engines')});
  }
  root.addEventListener('input',changed,{signal});root.addEventListener('change',changed,{signal});root.addEventListener('ko-settings-change',changed,{signal});root.addEventListener('click',e=>{if(e.target.closest('.add-stage,.remove-stage'))changed()},{signal});
  dialog.addEventListener('close',()=>{session.save();session.dispose();if(active===session)active=null},{signal});
  window.addEventListener('beforeunload',()=>session.save(),{signal});
  await refresh();await load();session.restoring=false;
  lastSelection=selectionKey();
  // Save a revised library selection too, so another restart cannot restore the
  // superseded participants. Other draft conditions have already been restored.
  if(value)await session.save();
 };
 $('#newTournament').onclick=safely(()=>newTournament());
})();
