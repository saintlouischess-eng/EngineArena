'use strict';
// Presentation and workflow helpers; tournament data stays in the worker.
function compactNumber(n){return Number.isFinite(n)?new Intl.NumberFormat(undefined,{notation:'compact',maximumFractionDigits:2}).format(n):'—'}
function statTile(label,value,note='',help=''){return `<div class="analysis-stat"${help?` data-help="${esc(help)}" tabindex="0"`:''}><span>${esc(label)}</span><strong>${esc(value)}</strong>${note?`<small>${esc(note)}</small>`:''}</div>`}

function polishPanel(panel){
 if(panel.dataset.organized)return;
 const title=panel.querySelector('.panel-title');if(!title)return;
 const heading=document.createElement('div');heading.className='panel-heading';
 const tools=document.createElement('div');tools.className='panel-tools';
 for(const child of [...title.children]){
  if(child.classList.contains('spacer')){child.remove();continue}
  if(child.matches('h2,.dock-handle,.live-indicator')||child.title==='Hide panel')heading.append(child);else tools.append(child);
 }
 title.append(heading);if(tools.children.length)title.append(tools);panel.dataset.organized='true';
}
$$('.panel').forEach(polishPanel);
const installUnpolishedPanel=installPanel;
installPanel=function(id,panel){installUnpolishedPanel(id,panel);polishPanel(panel)};

// Keep the common run controls separate from the less frequent report tools.
const tournamentTools=$('#overview>.toolbar');tournamentTools.classList.add('tournament-toolbar');
const identityTools=document.createElement('div');identityTools.className='tournament-selection';
for(const id of ['tournamentPicker','tournamentState','deleteTournament'])identityTools.append($('#'+id));
const runTools=document.createElement('div');runTools.className='tournament-run';
for(const id of ['start','pause','cancel'])runTools.append($('#'+id));
const reportsMenu=document.createElement('details');reportsMenu.className='reports-menu';reportsMenu.innerHTML='<summary data-help="Open live comparison reports or export the selected tournament’s current official results.">Results & exports</summary><div class="reports-menu-items"></div>';
for(const id of ['tournamentReport','openingReport','poolRatings','crossTable','pairingReview','exportPgn'])reportsMenu.lastElementChild.append($('#'+id));
tournamentTools.replaceChildren(identityTools,runTools,reportsMenu);
reportsMenu.addEventListener('click',e=>{if(e.target.closest('button'))reportsMenu.open=false});
document.addEventListener('click',e=>{if(!reportsMenu.contains(e.target))reportsMenu.open=false});
document.addEventListener('keydown',e=>{if(e.key==='Escape')reportsMenu.open=false});

// Long editors retain all fields in the DOM and gain a section index.
function organizeEditor(firstTitle='Overview'){
 const body=$('#modal .modal-body');if(!body||body.dataset.organized)return;
 body.dataset.organized='true';const nodes=[...body.children],sections=[];let section;
 function addSection(title){section=document.createElement('section');section.className='editor-section';section.id='editor-section-'+sections.length;const h=document.createElement('h3');h.textContent=title;section.append(h);sections.push(section);body.append(section)}
 addSection(firstTitle);
 for(const node of nodes){if(node.classList.contains('section-label')){addSection(node.textContent.toLowerCase().replace(/(^|\s)\S/g,c=>c.toUpperCase()).replace(/\bUci\b/g,'UCI').replace(/\bSprt\b/g,'SPRT'));node.remove()}else section.append(node)}
 if(sections.length>1){const nav=document.createElement('nav');nav.className='dialog-index';nav.setAttribute('aria-label','Settings sections');
  for(const target of sections){const button=document.createElement('button');button.type='button';button.textContent=target.querySelector('h3').textContent;button.dataset.help='Jump to '+button.textContent.toLowerCase()+' settings.';button.onclick=()=>{target.scrollIntoView({block:'start',behavior:'auto'});nav.querySelectorAll('button').forEach(b=>b.classList.toggle('active',b===button))};nav.append(button)}
  $('#modal .modal-head').after(nav);
 }
}
const tournamentEditorBeforePolish=newTournament;
newTournament=async function(){
 await tournamentEditorBeforePolish();if(!$('#tname'))return;
 const resource=$('#tconcurrency').closest('.fields'),watchdogs=document.createElement('div');watchdogs.className='fields';
 for(const id of ['tretries','tstartup','tready','thang','tstop','ttolerance','toverhead'])watchdogs.append($('#'+id).closest('.field'));
 resource.previousElementSibling.textContent='Resource budget';
 resource.insertAdjacentHTML('afterend','<div class="section-label">Clocks & failure handling</div>');resource.nextElementSibling.after(watchdogs);
 const adjudication=$('#tresign').closest('.fields');for(const id of ['tmaxplies','tannotations','tclaim'])adjudication.append($('#'+id).closest('.field')||$('#'+id).closest('label'));
 $('#resourceAdvice')&&resource.after($('#resourceAdvice'));$('#useRecommended')&&resource.after($('#useRecommended'));
 const preview=$('.preview-total');preview.classList.add('schedule-summary');$('#modal .modal-foot').prepend(preview);
 const relevance=()=>{const f=$('#tformat').value;$('#trounds').closest('.field').hidden=!['swiss','ladder'].includes(f);$('#tcandidates').closest('.field').hidden=f!=='gauntlet';for(const id of ['telo0','telo1'])$('#'+id).closest('.field').hidden=f!=='sprt'};
 $('#tformat').addEventListener('change',relevance);relevance();organizeEditor('Tournament & participants');
 if(!state.selected.size&&!$('#allProfiles').checked){const link=document.createElement('button');link.type='button';link.textContent='Choose engine profiles';link.dataset.help='Close this setup and select engines in the library before creating a tournament.';link.onclick=()=>{$('#modal').close();view('engines')};$('#tname').closest('.fields').after(link)}
};
$('#newTournament').onclick=safely(newTournament);
const engineEditorBeforePolish=editEngine;
editEngine=function(profile){engineEditorBeforePolish(profile);const first=$('#epath').closest('.fields'),resources=document.createElement('div');resources.className='fields';
 for(const id of ['ethreads','ehash','eaffinity','egpu','eextra','eindependent'])resources.append($('#'+id).closest('.field'));
 first.insertAdjacentHTML('afterend','<div class="section-label">Engine resources</div>');first.nextElementSibling.after(resources);organizeEditor('Executable & identity');
};

displayDialog=async function(){
 const sets=await api('pieces');
 modal('Appearance & workspace',`<section class="appearance-section"><div class="section-intro"><h3>Choose your pieces</h3><p>Six built-in designs, with custom SVG sets supported.</p></div><label class="sr-only" for="pieceChoice">Chess piece design</label><select id="pieceChoice">${sets.map(s=>`<option value="${s.id}" ${s.id===displayPrefs.pieceSet?'selected':''}>${esc(s.name)}</option>`).join('')}</select><div class="piece-gallery" role="group" aria-label="Chess piece designs">${sets.map(s=>`<button type="button" class="piece-choice" data-piece-choice="${s.id}" aria-label="${esc(s.name)} pieces" aria-pressed="${s.id===displayPrefs.pieceSet}" data-help="Preview ${esc(s.name)} pieces. Choose Apply appearance to save this design."><span class="piece-sample">${['wK','wQ','wN','bK','bQ','bN'].map(p=>`<img alt="${p[0]==='w'?'White':'Black'} ${{K:'king',Q:'queen',N:'knight'}[p[1]]}" src="/pieces/${s.id}/${p}.svg">`).join('')}</span><strong>${esc(s.name)}</strong><span class="piece-selected" aria-hidden="true">Selected</span></button>`).join('')}</div></section><section class="appearance-section appearance-preview"><div><h3>Board preview</h3><div id="appearanceBoard"></div></div><div><h3>Colors & text</h3><div class="fields"><div class="field"><label for="displayTheme">Theme</label><select id="displayTheme"><option value="dark" ${displayPrefs.theme==='dark'?'selected':''}>Midnight</option><option value="light" ${displayPrefs.theme==='light'?'selected':''}>Daylight</option></select></div>${field('displayFontSize','Font size',displayPrefs.fontSize,'number','required min="12" max="24" step="1" aria-describedby="fontSizeHelp"')}${field('squareLight','Light squares',displayPrefs.light,'color')}${field('squareDark','Dark squares',displayPrefs.dark,'color')}</div><p class="caption" id="fontSizeHelp">12–24 px. Text and controls scale together and are saved with this workspace.</p><button id="importPieces">Import custom SVG pieces…</button></div></section><section class="appearance-section"><div class="section-intro"><h3>Your workspace</h3><p>Show the panels you need. Drag their handles to move them, or their lower-right edges to resize.</p></div><div class="panel-choices">${Object.entries(panelNames).map(([id,name])=>`<label><input type="checkbox" data-showpanel="${id}" ${!panels[id].hidden?'checked':''}> ${esc(name)}</label>`).join('')}</div><div class="layout-tools"><label>Save current arrangement<input id="layoutName" placeholder="Layout name"></label><button id="saveLayout">Save layout</button><label>Saved layouts<select id="layoutChoice"><option value="">Choose a layout</option>${Object.keys(displayPrefs.layouts).map(n=>`<option>${esc(n)}</option>`).join('')}</select></label><button id="loadLayout">Load</button><button id="resetLayout">Reset sizes</button></div></section>`,`<button class="primary" id="applyDisplay">Apply appearance</button>`);
 const preview=()=>{const selected=$('#pieceChoice').value;$$('[data-piece-choice]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.pieceChoice===selected)));const host=$('#appearanceBoard');host.innerHTML=boardHtml('r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3','',false).replaceAll('/pieces/'+(state.pieceSet||'classic')+'/', '/pieces/'+selected+'/');host.style.setProperty('--board-light',$('#squareLight').value);host.style.setProperty('--board-dark',$('#squareDark').value)};
 $('#pieceChoice').onchange=preview;for(const b of $$('[data-piece-choice]'))b.onclick=()=>{$('#pieceChoice').value=b.dataset.pieceChoice;preview()};$('#squareLight').oninput=preview;$('#squareDark').oninput=preview;preview();
 $('#applyDisplay').onclick=safely(async()=>{if(!$('#displayFontSize').reportValidity())return;Object.assign(displayPrefs,{fontSize:Number($('#displayFontSize').value),pieceSet:$('#pieceChoice').value,theme:$('#displayTheme').value,light:$('#squareLight').value,dark:$('#squareDark').value});$$('[data-showpanel]').forEach(c=>displayPrefs.panels[c.dataset.showpanel]={...displayPrefs.panels[c.dataset.showpanel],visible:c.checked});applyDisplay();await persistDisplay();$('#modal').close();notify('Appearance and workspace saved.')});
 $('#saveLayout').onclick=safely(async()=>{const name=$('#layoutName').value.trim();if(!name)throw Error('Enter a name for this layout.');displayPrefs.layouts[name]={split:displayPrefs.split,panels:structuredClone(displayPrefs.panels),boardCount:displayPrefs.boardCount,graphs:structuredClone(displayPrefs.graphs||[]),evaluation:structuredClone(displayPrefs.evaluation||{})};await persistDisplay();await displayDialog();notify('Layout saved.')});
 $('#loadLayout').onclick=safely(async()=>{const layout=displayPrefs.layouts[$('#layoutChoice').value];if(!layout)throw Error('Choose a saved layout first.');Object.assign(displayPrefs,structuredClone(layout));applyDisplay();await persistDisplay();$('#modal').close()});
 $('#resetLayout').onclick=safely(async()=>{displayPrefs.panels={focus:{visible:true,order:0},search:{visible:true,order:1},live:{order:2}};displayPrefs.split=58;applyDisplay();await persistDisplay();$('#modal').close()});
 $('#importPieces').onclick=safely(async()=>{const paths=await browse(true);if(paths[0]){const set=await api('pieces',{folder:paths[0]});displayPrefs.pieceSet=set.id;applyDisplay();await persistDisplay();await displayDialog()}});
};
displayButton.onclick=safely(displayDialog);

// Experiments accept search budgets, not tournament chess clocks.
const experimentEditorBeforePolish=newExperiment;
newExperiment=function(kind){experimentEditorBeforePolish(kind);const control=$('#extc [data-tc=kind]');
 for(const option of [...control.options])if(!['nodes','depth','movetime'].includes(option.value))option.remove();
 organizeEditor(kind==='suite'?'Suite source & participants':'Benchmark cases & participants');
};

const loadEnginesBeforePolish=loadEngines;
loadEngines=async function(){await loadEnginesBeforePolish();const rows=$('#engineTable tbody');
 if(!state.engines.length){const tr=document.createElement('tr'),td=document.createElement('td');td.colSpan=7;td.className='library-empty';td.textContent=$('#engineSearch').value?'No profiles match this search. Clear the search to see your library.':'No engines registered yet. Add an executable or scan a folder to begin.';tr.append(td);rows.replaceChildren(tr)}
};

// Field validation occurs before a dialog's save handler; hidden alternative
// control families must never block saving the selected family.
const saveButtons=new Set(['createTournament','saveEngine','testEngine','saveP','savePosition','createExperiment','applyBulk','saveGraph','applyDisplay']);
document.addEventListener('click',e=>{
 const button=e.target.closest('button');if(!button||!saveButtons.has(button.id))return;
 for(const input of $$('#modal input,#modal select,#modal textarea')){
  if(!input.getClientRects().length||input.disabled)continue;
  if(['tname','presetName','positionName','exname','epath','expath'].includes(input.id)){input.required=true;if(input.value.trim()==='')input.value=''}
  if(!input.checkValidity()){e.preventDefault();e.stopImmediatePropagation();input.reportValidity();input.focus();return}
 }
},true);

function updateRunControls(){
 const t=state.snapshot?.id===state.tid?state.snapshot:null,selected=!!state.tid,live=state.live.some(g=>g.tid===state.tid),status=t?.state;
 for(const id of ['start','pause','cancel','deleteTournament','exportPgn','tournamentReport','openingReport','poolRatings','crossTable','pairingReview']){
  const el=$('#'+id);if(el.getAttribute('aria-busy')==='true')continue;
  el.disabled=!selected||(id==='pause'&&!['running','draining'].includes(status))||(id==='cancel'&&!live)||(id==='start'&&(status==='running'||status==='draining'||status==='completed'||!!t?.dependency||!!state.workerError));
 }
 $('#start').textContent=status==='completed'?'✓ Completed':status==='running'?'▶ Running':status==='draining'?'Ⅱ Draining':'▶ Start / resume';
 $('#cloneEngine').disabled=$('#bulkEngine').disabled=$('#deleteEngines').disabled=!state.selected.size;
 for(const [prefix,offset,total,size] of [['eng',state.engOffset,state.engineTotal,50],['stand',state.standOffset,state.standTotal,50],['games',state.gameOffset,state.gameTotal,50]]){
  $('#'+prefix+'Prev').disabled=offset<=0;$('#'+prefix+'Next').disabled=offset+size>=total;
 }
 $('#gamesFirst').disabled=state.gameOffset<=0;$('#gamesLast').disabled=state.gameOffset+50>=state.gameTotal;
 $('#replaySelected').disabled=!state.gameSelected.size||['running','draining'].includes(status);
 $('#replayAll').disabled=!state.gameTotal||['running','draining'].includes(status)||['','running','pending'].includes($('#gameFilter').value);
}
const originalRefreshTournament=refreshTournament;
refreshTournament=async function(){await originalRefreshTournament();updateRunControls()};
document.addEventListener('change',e=>{if(e.target.matches('[data-engine],#tournamentPicker'))updateRunControls()});
setInterval(updateRunControls,750);

function renderWorkerHealth(s){
 state.workerError=s.error||'';const box=$('#healthContent');
 stableHtml('#healthContent',`<div class="health-banner ${s.error?'health-problem':''}"><span class="status-orb"></span><div><strong>${s.error?'Storage or worker needs attention':s.maintenance?'Cleaning tournament data':'Worker connected'}</strong><p>${s.error?esc(s.error):'Moves and results are saved automatically. Recovery preserves committed results.'}</p></div></div><div class="health-grid">${statTile('Active games',s.active_games,'up to '+s.engine_process_bound+' engine processes')}${statTile('Peak concurrency',s.max_active_games,'games this session')}${statTile('Available memory',fmt(s.memory_available_gb)+' GiB','system memory')}${statTile('Worker uptime',ArenaClocks.format(s.uptime),'this session')}</div><div class="storage-location"><span class="section-eyebrow">Tournament data folder</span><code>${esc(s.data_folder)}</code></div>${backupHealth(s.backup)}${s.warning?`<p class="recovery-notice">${esc(s.warning)}</p>`:''}`);
}
renderBoards();updateRunControls();
