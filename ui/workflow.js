'use strict';
const completionCard=document.createElement('section');completionCard.className='completion-card';completionCard.hidden=true;completionCard.setAttribute('aria-label',ArenaI18n.t('Tournament completed'));$('#tournamentNote').after(completionCard);
let completionKey='',completionBusy=false,completionData=null,completionChecked=0;
async function showFinalGame(id){
 const tid=state.tid,d=await api(`games/${id}/moves?limit=1`);if(tid!==state.tid)return;
 let last=d.items.at(-1);if(d.latest_ply>1){const tail=await api(`games/${id}/moves?after=${d.latest_ply-1}&limit=1`);if(tid!==state.tid)return;last=tail.items.at(-1)}
 if(typeof clearEngineFollow==='function')clearEngineFollow();
 retainedTid=tid;focusId=id;retainedFocus={...d,attempt:d.attempt?.id,ended:d.attempt?.ended,result:d.attempt?.result,reason:d.attempt?.reason,ply:d.latest_ply,fen:last?.fen||d.opening.fen,crown_squares:last?.crown_squares||d.opening_crown_squares||[],knight_facings:last?.knight_facings||d.opening_knight_facings||{},captured:last?.captured||d.opening_captured||[],last_move:last?.uci,san:last?.san,info:last?.info,info_side:last?.side,clocks:d.attempt?.clocks,clock_active:null,status:[d.attempt?.result,d.attempt?.reason].filter(Boolean).join(' · ')};
 revealFocusPanel('focus');renderFocus();
}
async function renderCompletion(){
 const t=state.snapshot;if(!t||t.id!==state.tid||t.state!=='completed'){completionCard.hidden=true;completionKey='';return}
 completionCard.hidden=false;
 const key=[t.id,t.official_games,JSON.stringify(t.counts)].join(':');
 if((key!==completionKey||Date.now()-completionChecked>15000)&&!completionBusy){
  completionBusy=true;try{const d=await api(`tournaments/${t.id}/completion`);if(t.id!==state.tid||state.snapshot?.state!=='completed')return;completionData=d;completionKey=key;completionChecked=Date.now()}
  catch(e){completionCard.textContent=e.message;return}finally{completionBusy=false}
 }
 if(completionKey!==key||!completionData)return;
 const failures=completionData.failures.reduce((n,r)=>n+r.official,0),all=completionData.failures.reduce((n,r)=>n+r.attempts,0);
 const html=ArenaI18n.h`<div><span class="section-eyebrow">TEST COMPLETE</span><h2>${esc(t.name)}</h2><p>${ArenaI18n.m`${Number(t.official_games).toLocaleString(ArenaI18n.locale)} official games · ${Number(t.complete_pairs||0).toLocaleString(ArenaI18n.locale)} completed opening pairs`}</p><p>${ArenaI18n.m`${failures} official engine failures · ${all} failures across original and replacement attempts`}</p><p>Final standings remain below. Diagnostic attempts do not change official results.</p></div><div class="completion-actions"><button data-complete="report">Tournament report</button><button data-complete="pgn">Export PGN</button><button data-complete="failures">Review failures</button><button data-complete="final" ${completionData.last_game?'':'disabled'}>Final game</button></div>`;
 if(completionCard._html!==html){completionCard.innerHTML=html;completionCard._html=html;
  completionCard.querySelector('[data-complete=report]').onclick=safely(()=>showTournamentReport());
  completionCard.querySelector('[data-complete=pgn]').onclick=()=>$('#exportPgn').click();
  completionCard.querySelector('[data-complete=failures]').onclick=safely(async()=>{$('#gameFilter').value='failed';state.gameOffset=0;revealFocusPanel('games');await refreshGames()});
  completionCard.querySelector('[data-complete=final]').onclick=safely(()=>showFinalGame(completionData.last_game));
 }
}
const refreshBeforeCompletion=refreshTournament;
refreshTournament=async function(){await refreshBeforeCompletion();await renderCompletion()};
$('#tournamentPicker').addEventListener('change',()=>{completionCard.hidden=true;completionKey=''});

const quickButton=document.createElement('button');quickButton.id='quickMatch';quickButton.textContent=ArenaI18n.t('Quick match');quickButton.dataset.help=ArenaI18n.t('Set up two engine profiles, review their conditions and save a paused match.');$('#newTournament').before(quickButton);quickButton.onclick=safely(()=>quickMatch());
async function quickMatch(draft={}){
 const picked=draft.picked||[...state.selected].map(id=>state.engines.find(p=>p.id===id)).filter(Boolean).slice(0,2),profiles=[picked[0]||null,picked[1]||null];
 modal(ArenaI18n.t('Quick match'),ArenaI18n.h`<p class="caption">Two profiles, one shared opening suite, colors reversed. Save first, then start when ready.</p><div class="quick-engine-grid">${[0,1].map(i=>ArenaI18n.h`<section class="quick-engine"><h3>${i===0?ArenaI18n.t('First engine'):ArenaI18n.t('Second engine')}</h3><input id="quickSearch${i}" placeholder="Search engine profiles…"><select id="quickEngine${i}" aria-label="Engine profile"></select><div class="toolbar"><button id="quickPrev${i}" aria-label="Previous profiles">←</button><small id="quickPage${i}"></small><button id="quickNext${i}" aria-label="Next profiles">→</button></div><small id="quickInfo${i}"></small></section>`).join('')}</div><div class="fields">${field('quickName',ArenaI18n.t('Tournament name'),draft.name||ArenaI18n.t('Quick match'))}${field('quickPairs',ArenaI18n.t('Opening pairs per matchup'),draft.pairs??10,'number','required min="1" step="1"')}${field('quickConcurrency',ArenaI18n.t('Concurrent games'),draft.concurrency??1,'number','required min="1" step="1"')}</div>${tcEditor('quickTc',draft.tc)}<label><input id="quickCommon" type="checkbox" ${draft.common===false?'':'checked'}> Use this time control for both profiles</label><p class="caption">Uncheck to keep independent profile controls. Threads, Hash, GPU groups and UCI options use each profile’s saved configuration. Ponder is off.</p><div class="fields">${pathField('quickBook',ArenaI18n.t('Shared opening file (optional)'),draft.book||'')}${field('quickDepth',ArenaI18n.t('Book depth (plies)'),draft.depth??16,'number','required min="0" step="1"')}${field('quickSeed',ArenaI18n.t('Opening random seed'),draft.seed??7970,'number','required step="1"')}${field('quickGpu',ArenaI18n.t('Shared GPU group slots (group:count, comma separated)'),draft.gpu||'')}</div><label><input id="quickEngineBooks" type="checkbox" ${draft.engineBooks?'checked':''}> Use each profile’s engine move book</label><p class="caption">The shared file supplies paired starting positions in seeded shuffled order. A blank file uses the initial chess position. Engine move books are optional and act after that starting position.</p>`,ArenaI18n.h('<button id="quickReview" class="primary">Review match</button>'));
 wireTc('quickTc');wireBrowsers();
 const dialog=$('#quickName');
 for(const i of [0,1]){
  let offset=0,request=0,page=[],timer;
  const load=async()=>{const gen=++request,q=$('#quickSearch'+i).value,r=await api(`profiles?q=${encodeURIComponent(q)}&offset=${offset}&limit=50`);if(gen!==request||!dialog.isConnected)return;page=r.items;
   if(!profiles[i])profiles[i]=page[i]||page[0]||null;
   const options=[...page];if(profiles[i]&&!options.some(p=>p.id===profiles[i].id))options.unshift(profiles[i]);
   $('#quickEngine'+i).innerHTML=options.map(p=>`<option value="${esc(p.id)}">${esc(p.name)}</option>`).join('');$('#quickEngine'+i).value=profiles[i]?.id||'';
   $('#quickPage'+i).textContent=`${r.total?offset+1:0}–${Math.min(offset+50,r.total)} / ${r.total}`;$('#quickPrev'+i).disabled=offset===0;$('#quickNext'+i).disabled=offset+50>=r.total;info();
  };
  const info=()=>{const p=profiles[i];$('#quickInfo'+i).textContent=p?`${profileResource(p,'threads',1)} ${ArenaI18n.t('threads')} · ${profileResource(p,'hash',1024)} MB · ${p.gpu_group||'CPU'} · ${tcText(p.time_control)}`:ArenaI18n.t('Add engine profiles in Engine library first.')};
  $('#quickEngine'+i).onchange=()=>{profiles[i]=page.find(p=>p.id===$('#quickEngine'+i).value)||profiles[i];info()};
  $('#quickSearch'+i).oninput=()=>{clearTimeout(timer);timer=setTimeout(safely(async()=>{if(!dialog.isConnected)return;offset=0;await load()}),200)};
  $('#quickPrev'+i).onclick=safely(()=>{offset=Math.max(0,offset-50);return load()});$('#quickNext'+i).onclick=safely(()=>{offset+=50;return load()});await load();
 }
 $('#quickReview').onclick=safely(async()=>{
  for(const el of $$('#modal input[type=number]'))if(!el.closest('[hidden]')&&!el.reportValidity())return;
  if(!profiles[0]||!profiles[1]||profiles[0].id===profiles[1].id)throw Error(ArenaI18n.t('Choose two different profiles. Clone an engine to compare two configurations.'));
  const d={picked:profiles,name:$('#quickName').value.trim(),pairs:Number($('#quickPairs').value),concurrency:Number($('#quickConcurrency').value),tc:readTc('quickTc'),common:$('#quickCommon').checked,book:$('#quickBook').value.trim(),depth:Number($('#quickDepth').value),seed:Number($('#quickSeed').value),gpu:$('#quickGpu').value,engineBooks:$('#quickEngineBooks').checked};
  if(!d.name)throw Error(ArenaI18n.t('Enter a tournament name'));
  const groups=Object.fromEntries(d.gpu.split(',').filter(s=>s.trim()).map(s=>{const parts=s.split(':');if(parts.length!==2||!parts[0].trim()||!Number.isInteger(Number(parts[1]))||Number(parts[1])<1)throw Error(ArenaI18n.t('Use GPU group:count with a positive whole number'));return [parts[0].trim(),Number(parts[1])]}));
  for(const p of profiles)if(p.gpu_group&&!groups[p.gpu_group])groups[p.gpu_group]=1;
  const settings={format:'match',cycles:d.pairs,paired:true,concurrency:d.concurrency,time_control:d.tc,ponder:false,opening_policy:'pair',opening_order:'shuffle',seed:d.seed,use_engine_books:d.engineBooks,gpu_limits:groups};
  const payload={name:d.name,profiles:profiles.map(p=>p.id),settings,common_control:d.common,opening_file:d.book,book_depth:d.depth};
  const button=$('#quickReview');button.disabled=true;
  try{
   const capacity=await api('opening-preview',{settings,participants:2,opening_file:d.book,book_depth:d.depth}),resources=await api('resource-preview',{profiles:payload.profiles,settings});
   if(!dialog.isConnected)return;
   if(resources.recommended===0)throw Error(ArenaI18n.t('These profiles cannot fit one game in the resource budget. Review GPU slots, Threads and Hash.'));
   modal(ArenaI18n.t('Review match'),ArenaI18n.h`<h3>${esc(d.name)}</h3><div class="quick-review"><article>Scheduled games<strong>${(d.pairs*2).toLocaleString(ArenaI18n.locale)}</strong><small>${d.pairs} ${ArenaI18n.t('opening pairs')} · ${ArenaI18n.t('Colors reversed')}</small></article><article>Concurrent games<strong>${d.concurrency}</strong><small>${ArenaI18n.m`Resource estimate: up to ${resources.recommended} games`}</small></article>${profiles.map(p=>ArenaI18n.h`<article>${esc(p.name)}<strong>${esc(tcText(d.common?d.tc:p.time_control||d.tc))}</strong><small>${profileResource(p,'threads',1)} threads · ${profileResource(p,'hash',1024)} MB · ${esc(p.gpu_group||'CPU')}</small></article>`).join('')}</div><p>${esc(d.book||ArenaI18n.t('Initial position'))} · ${ArenaI18n.m`${capacity.unique_positions} unique starting positions`}</p><p class="caption">Openings repeat after the available suite is exhausted. Paired games always reverse colors from the same starting position. Startup, readiness and hang watchdogs remain separate from the chess clock.</p><p class="caption">Default policy: 0.05 s clock tolerance, no charged overhead, no automatic retries, no evaluation adjudication. You can edit these conditions in the full setup before starting.</p>`,ArenaI18n.h('<button id="quickBack">Back</button><button id="createTournament" class="primary">Create paused tournament</button>'));
   $('#quickBack').onclick=safely(()=>quickMatch(d));$('#createTournament').onclick=safely(()=>saveTournamentSetup(payload,null));
  }finally{if(button.isConnected)button.disabled=false}
 });
}

$('#importEngines').onclick=()=>profileImportDialog();
function profileImportDialog(){
 let source=null,filename='',checked=null,checkedSource=null,page=0,selected=new Set();
 modal(ArenaI18n.t('Import engine profiles'),ArenaI18n.h`<p>Import UCI profiles from Engine Arena, Cute Chess or Banksia. Review the preview before adding anything. Engine executables are not copied or started.</p><div class="fields"><label>JSON configuration<input id="profileSource" type="file" accept=".json"></label>${pathField('profileBase',ArenaI18n.t('Original GUI folder (for relative paths)'),' ',true)}</div><p class="caption">Absolute executable paths are preserved. For relative paths, select the folder used by the original GUI. Missing engines and WinBoard profiles are skipped. Test imported connections from Engine library.</p><button id="previewProfiles">Preview import</button><p id="profileImportStatus" role="status"></p><div id="profileImportPreview"></div>`,ArenaI18n.h('<button id="commitProfiles" class="primary" disabled>Import selected profiles</button>'));wireBrowsers();$('#profileBase').value='';
 const anchor=$('#profileSource');
 const clear=()=>{checked=null;selected.clear();$('#commitProfiles').disabled=true;$('#profileImportPreview').replaceChildren()};
 anchor.onchange=safely(async()=>{clear();source=null;const file=anchor.files[0];if(!file)return;filename=file.name;source=JSON.parse(await file.text());$('#profileImportStatus').textContent=filename});$('#profileBase').oninput=clear;
 const body=()=>({source,base_dir:$('#profileBase').value.trim(),format:'auto'});
 const render=()=>{const items=checked.items.slice(page*50,page*50+50);$('#profileImportStatus').textContent=ArenaI18n.m`${checked.ready} ready · ${checked.total-checked.ready} skipped or duplicate · ${selected.size} selected`;
  $('#profileImportPreview').innerHTML=ArenaI18n.h`<div class="toolbar"><button id="importSelectAll">Select all ready</button><button id="importSelectNone">Clear selection</button><span class="spacer"></span><button id="importPrev" ${page?'':'disabled'}>←</button><span>${page+1} / ${Math.max(1,Math.ceil(checked.total/50))}</span><button id="importNext" ${(page+1)*50<checked.total?'':'disabled'}>→</button></div><div class="import-scroll"><table><thead><tr><th></th><th>Engine profile</th><th>Status</th></tr></thead><tbody>${items.map(i=>ArenaI18n.h`<tr><td><input data-import-index="${i.index}" type="checkbox" aria-label="${esc(i.name)}" ${i.status==='ready'?'':'disabled'} ${selected.has(i.index)?'checked':''}></td><td><b>${esc(i.name)}</b><small>${esc(i.profile?.path||'')}</small></td><td><b class="import-status">${esc(ArenaI18n.message(i.status))}</b><small>${i.messages.map(s=>esc(ArenaI18n.message(s))).join('<br>')}</small></td></tr>`).join('')}</tbody></table></div>`;
  $('#importSelectAll').onclick=()=>{selected=new Set(checked.items.filter(i=>i.status==='ready').map(i=>i.index));render()};$('#importSelectNone').onclick=()=>{selected.clear();render()};$('#importPrev').onclick=()=>{page--;render()};$('#importNext').onclick=()=>{page++;render()};$$('[data-import-index]').forEach(c=>c.onchange=()=>{const id=Number(c.dataset.importIndex);c.checked?selected.add(id):selected.delete(id);$('#commitProfiles').disabled=!selected.size});$('#commitProfiles').disabled=!selected.size;
 };
 $('#previewProfiles').onclick=safely(async()=>{if(!source)throw Error(ArenaI18n.t('Select a JSON configuration file'));const request=body();$('#previewProfiles').disabled=true;try{const result=await api('profiles/import-preview',{...request,preview:true});if(!anchor.isConnected)return;if(source!==request.source||body().base_dir!==request.base_dir)return;checkedSource=request;checked=result;selected=new Set(result.items.filter(i=>i.status==='ready').map(i=>i.index));page=0;render()}finally{if(anchor.isConnected)$('#previewProfiles').disabled=false}});
 $('#commitProfiles').onclick=safely(async()=>{const b=$('#commitProfiles');b.disabled=true;try{const r=await api('profiles/import-preview',{...checkedSource,preview:false,selected:[...selected]});if(!anchor.isConnected)return;$('#modal').close();await loadEngines();notify(ArenaI18n.m`${r.count} profiles imported; ${r.duplicates} identical profiles skipped.`)}finally{if(b.isConnected)b.disabled=false}});
}
