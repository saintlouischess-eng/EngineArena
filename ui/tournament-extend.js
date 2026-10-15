'use strict';
const extendButton=document.createElement('button');extendButton.id='extendTournament';extendButton.textContent=ArenaI18n.t('Add engines…');
extendButton.dataset.help=ArenaI18n.t('Extend a completed round robin with new engines. Existing results are retained; only missing matchups are added.');
$('#editTournament').after(extendButton);extendButton.disabled=true;
const editBeforeExtension=renderTournamentEdit;
renderTournamentEdit=function(t){editBeforeExtension(t);extendButton.disabled=!(t?.state==='completed'&&t.settings.format==='round_robin'&&!t.event)};
extendButton.onclick=safely(async()=>{
 const tid=state.tid,details=await api(`tournaments/${tid}/extend`);
 if(details.reason)throw Error(ArenaI18n.message(details.reason));
 const selected=new Map(),existing=new Set(details.existing_ids);let offset=0,total=0,generation=0,preview=null;
 modal(ArenaI18n.t('Extend round robin'),ArenaI18n.h`<p>Existing games, engine settings and ratings are retained. New engines play every existing engine and each other using the recorded tournament conditions.</p><label>Find engine<input id="extendSearch" type="search" autocomplete="off"></label><p id="extendSelected" class="caption" role="status"></p><div class="extend-list table-scroll" tabindex="0"><table><thead><tr><th></th><th>Engine</th></tr></thead><tbody id="extendRows"></tbody></table></div><div class="queue-paging"><button id="extendPrev">Previous</button><span id="extendPage"></span><button id="extendNext">Next</button></div><div id="extendPreview" role="status"></div>`,ArenaI18n.h`<button id="extendCheck">Preview added games</button><button id="extendSave" class="primary" disabled>Save extension paused</button>`);
 function changed(){preview=null;$('#extendPreview').replaceChildren();$('#extendSave').disabled=true;$('#extendSelected').textContent=ArenaI18n.t('{0} new engines selected',selected.size);$('#extendCheck').disabled=!selected.size}
 async function load(){
  const seq=++generation,data=await api(`profiles?q=${encodeURIComponent($('#extendSearch').value)}&offset=${offset}&limit=50`);
  if(seq!==generation||!$('#extendRows'))return;total=data.total;
  $('#extendRows').innerHTML=data.items.map(p=>`<tr><td><input type="checkbox" data-add-engine="${esc(p.id)}" aria-label="${esc(p.name)}" ${selected.has(p.id)?'checked':''} ${existing.has(p.id)?'disabled':''}></td><td>${esc(p.name)}${existing.has(p.id)?' · '+esc(ArenaI18n.t('Already included')):''}</td></tr>`).join('');
  $('#extendPage').textContent=`${total?offset+1:0}–${Math.min(offset+50,total)} / ${total}`;$('#extendPrev').disabled=!offset;$('#extendNext').disabled=offset+50>=total;
  for(const el of $$('[data-add-engine]'))el.onchange=()=>{const p=data.items.find(p=>p.id===el.dataset.addEngine);if(el.checked)selected.set(p.id,p.name);else selected.delete(p.id);changed()};
 }
 $('#extendSearch').oninput=safely(async()=>{offset=0;await load()});$('#extendPrev').onclick=safely(async()=>{offset=Math.max(0,offset-50);await load()});$('#extendNext').onclick=safely(async()=>{offset+=50;await load()});
 $('#extendCheck').onclick=safely(async()=>{
  const ids=[...selected.keys()];$('#extendCheck').disabled=true;
  try{
   const p=await api(`tournaments/${tid}/extend`,{preview:true,profiles:ids});
   if(JSON.stringify(ids)!==JSON.stringify([...selected.keys()])||!$('#extendPreview'))return;
   preview=p;$('#extendPreview').innerHTML=ArenaI18n.h`<div class="notice"><strong>${ArenaI18n.t('{0} additional games · {1} total scheduled',p.additional_games.toLocaleString(ArenaI18n.locale),p.total_games.toLocaleString(ArenaI18n.locale))}</strong><p>${ArenaI18n.t('{0} completed games retained · {1} participants',p.retained_games.toLocaleString(ArenaI18n.locale),p.new_participants.toLocaleString(ArenaI18n.locale))}</p><p class="caption">${esc(p.names.slice(0,20).join(' · '))}${p.names.length>20?' …':''}</p><p>${ArenaI18n.t('Recorded cycles: {0} · color-reversed pairs: {1}',p.cycles,ArenaI18n.t(p.paired?'On':'Off'))}</p><p>Opening-pair and round presets continue their recorded sequence. Shared-cycle and fixed-position presets deliberately reuse their suite. Random selection or an exhausted book may repeat positions.</p><p>New profiles keep their current thread, hash and per-engine time-control settings. Review these in Engine library before saving.</p><p>The extension is saved paused. Start it when ready.</p></div>`;$('#extendSave').disabled=false;
  }finally{if($('#extendCheck'))$('#extendCheck').disabled=!selected.size}
 });
 $('#extendSave').onclick=safely(async()=>{
  if(!preview)return;$('#extendSave').disabled=true;
  try{await api(`tournaments/${tid}/extend`,{profiles:[...selected.keys()],expected:preview.expected});$('#modal').close();await loadTournaments();state.tid=tid;$('#tournamentPicker').value=tid;await refreshTournament();notify(ArenaI18n.t('Tournament extended and saved paused. Start when ready.'))}
  catch(e){if($('#extendSave'))$('#extendSave').disabled=false;throw e}
 });
 changed();await load();
});
