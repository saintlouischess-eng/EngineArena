'use strict';
// Presentation and workflow helpers; tournament data stays in the worker.
function compactNumber(n){return Number.isFinite(n)?ArenaI18n.number(n,{notation:'compact',maximumFractionDigits:2}):'—'}
function statTile(label,value,note='',help=''){return ArenaI18n.h`<div class="analysis-stat"${help?` data-help="${esc(help)}" tabindex="0"`:''}><span>${esc(label)}</span><strong>${esc(value)}</strong>${note?ArenaI18n.h`<small>${esc(note)}</small>`:''}</div>`}

function polishPanel(panel){
 if(panel.dataset.organized)return;
 const title=panel.querySelector('.panel-title');if(!title)return;
 const heading=document.createElement('div');heading.className='panel-heading';
 const tools=document.createElement('div');tools.className='panel-tools';
 for(const child of [...title.children]){
  if(child.classList.contains('spacer')){child.remove();continue}
  if(child.matches('h2,.dock-handle,.live-indicator')||child.title===ArenaI18n.t('Hide panel'))heading.append(child);else tools.append(child);
 }
 title.append(heading);if(tools.children.length)title.append(tools);panel.dataset.organized='true';
}
$$('.panel').forEach(polishPanel);
const installUnpolishedPanel=installPanel;
installPanel=function(id,panel){installUnpolishedPanel(id,panel);polishPanel(panel)};

// Keep the common run controls separate from the less frequent report tools.
const tournamentTools=$('#overview>.toolbar');tournamentTools.classList.add('tournament-toolbar');
const identityTools=document.createElement('div');identityTools.className='tournament-selection';
for(const id of ['tournamentPicker','tournamentState','editTournament','deleteTournament'])identityTools.append($('#'+id));
const runTools=document.createElement('div');runTools.className='tournament-run';
for(const id of ['start','pause','cancel'])runTools.append($('#'+id));
const reportsMenu=document.createElement('details');reportsMenu.className='reports-menu';reportsMenu.innerHTML=ArenaI18n.h('<summary data-help="Open live comparison reports or export the selected tournament’s current official results.">Results & exports</summary><div class="reports-menu-items"></div>');
for(const id of ['tournamentReport','openingReport','poolRatings','crossTable','pairingReview','exportPgn'])reportsMenu.lastElementChild.append($('#'+id));
tournamentTools.replaceChildren(identityTools,runTools,reportsMenu);
reportsMenu.addEventListener('click',e=>{if(e.target.closest('button'))reportsMenu.open=false});
document.addEventListener('click',e=>{if(!reportsMenu.contains(e.target))reportsMenu.open=false});
document.addEventListener('keydown',e=>{if(e.key==='Escape')reportsMenu.open=false});

// Long editors retain all fields in the DOM and gain a section index.
function organizeEditor(firstTitle=ArenaI18n.t('Overview')){
 const body=$('#modal .modal-body');if(!body||body.dataset.organized)return;
 body.dataset.organized='true';const nodes=[...body.children],sections=[];let section;
 function addSection(title){section=document.createElement('section');section.className='editor-section';section.id='editor-section-'+sections.length;const h=document.createElement('h3');h.textContent=title;section.append(h);sections.push(section);body.append(section)}
 addSection(firstTitle);
 for(const node of nodes){if(node.classList.contains('section-label')){addSection(node.textContent.toLowerCase().replace(/(^|\s)\S/g,c=>c.toUpperCase()).replace(/\bUci\b/g,'UCI').replace(/\bSprt\b/g,'SPRT'));node.remove()}else section.append(node)}
 if(sections.length>1){const nav=document.createElement('nav');nav.className='dialog-index';nav.setAttribute('aria-label',ArenaI18n.t('Settings sections'));
  for(const target of sections){const button=document.createElement('button');button.type='button';button.textContent=target.querySelector('h3').textContent;button.dataset.help=ArenaI18n.t('Jump to ')+button.textContent.toLowerCase()+ArenaI18n.t(' settings.');button.onclick=()=>{target.scrollIntoView({block:'start',behavior:'auto'});nav.querySelectorAll('button').forEach(b=>b.classList.toggle('active',b===button))};nav.append(button)}
  $('#modal .modal-head').after(nav);
 }
}
const tournamentEditorBeforePolish=newTournament;
newTournament=async function(draft=null){
 await tournamentEditorBeforePolish(draft);if(!$('#tname'))return;
 const resource=$('#tconcurrency').closest('.fields'),watchdogs=document.createElement('div');watchdogs.className='fields';
 for(const id of ['tretries','tstartup','tready','thang','tstop','ttolerance','toverhead'])watchdogs.append($('#'+id).closest('.field'));
 resource.previousElementSibling.textContent=ArenaI18n.t('Resource budget');
 resource.insertAdjacentHTML('afterend',ArenaI18n.h('<div class="section-label">Clocks & failure handling</div>'));resource.nextElementSibling.after(watchdogs);
 const adjudication=$('#tresign').closest('.fields');for(const id of ['tmaxplies','tannotations','tclaim'])adjudication.append($('#'+id).closest('.field')||$('#'+id).closest('label'));
 $('#resourceAdvice')&&resource.after($('#resourceAdvice'));$('#useRecommended')&&resource.after($('#useRecommended'));
 const preview=$('.preview-total');preview.classList.add('schedule-summary');$('#modal .modal-foot').prepend(preview);
 const relevance=()=>{const f=$('#tformat').value;$('#trounds').closest('.field').hidden=!['swiss','ladder'].includes(f);$('#tcandidates').closest('.field').hidden=f!=='gauntlet';for(const id of ['telo0','telo1'])$('#'+id).closest('.field').hidden=f!=='sprt'};
 $('#tformat').addEventListener('change',relevance);relevance();organizeEditor(ArenaI18n.t('Tournament & participants'));
 if(!tournamentParticipantCount()){const link=document.createElement('button');link.type='button';link.textContent=ArenaI18n.t('Choose engine profiles');link.dataset.help=ArenaI18n.t('Close this setup and select engines in the library before creating a tournament.');link.onclick=()=>{$('#modal').close();view('engines')};$('#tname').closest('.fields').after(link)}
};
$('#newTournament').onclick=safely(newTournament);
const engineEditorBeforePolish=editEngine;
editEngine=function(profile){engineEditorBeforePolish(profile);const first=$('#epath').closest('.fields'),resources=document.createElement('div');resources.className='fields';
 for(const id of ['ethreads','ehash','eaffinity','egpu','eextra','eindependent'])resources.append($('#'+id).closest('.field'));
 first.insertAdjacentHTML('afterend',ArenaI18n.h('<div class="section-label">Engine resources</div>'));first.nextElementSibling.after(resources);organizeEditor(ArenaI18n.t('Executable & identity'));
};

displayDialog=async function(){
 const sets=await api('pieces');
 const materials=ArenaMaterials.normalize(displayPrefs.boardMaterials);
 const materialOptions=side=>Object.entries(ArenaMaterials.woods).map(([key,value])=>ArenaI18n.h`<option value="${key}" ${materials[side]===key?'selected':''}>${value.name}</option>`).join('');
 const swatch=key=>{const wood=ArenaMaterials.woods[key];return key==='solid'?'background-color:#8a9b88':`background-color:${wood.color};background-image:url(/textures/${key}.png)`};
 const materialFields=ArenaI18n.h`<h3>Board finish</h3><p class="wood-note">Original wood textures, built in and available offline. Choose each side independently or use a matching pair.</p><div class="wood-presets" role="group" aria-label="Board finish presets">${Object.entries(ArenaMaterials.presets).map(([key,p])=>ArenaI18n.h`<button data-wood-preset="${key}" data-help="Preview ${p.name}. Apply appearance saves your choices."><span class="wood-swatch" aria-hidden="true"><span style="${swatch(p.light)}"></span><span style="${swatch(p.dark)}"></span></span>${p.name}</button>`).join('')}</div><div class="fields"><div class="field"><label for="lightMaterial">Light-square finish</label><select id="lightMaterial">${materialOptions('light')}</select></div><div class="field"><label for="darkMaterial">Dark-square finish</label><select id="darkMaterial">${materialOptions('dark')}</select></div></div><p class="wood-note">Wood uses its natural colors. Choose Solid color to use the color pickers below.</p>`;

 modal(ArenaI18n.t('Appearance & workspace'),ArenaI18n.h`<section class="appearance-section"><div class="section-intro"><h3>Choose your pieces</h3><p>New raised Classic designs: Refined, Bold and Heritage. Choose from twenty-one built-in SVG designs, or import your own.</p></div><label class="sr-only" for="pieceChoice">Chess piece design</label><select id="pieceChoice">${sets.map(s=>ArenaI18n.h`<option value="${s.id}" ${s.id===displayPrefs.pieceSet?'selected':''}>${esc(s.name)}</option>`).join('')}</select><div class="piece-gallery" role="group" aria-label="Chess piece designs">${sets.map(s=>ArenaI18n.h`<button type="button" class="piece-choice" data-piece-choice="${s.id}" aria-label="${esc(s.name)} pieces" aria-pressed="${s.id===displayPrefs.pieceSet}" data-help="Preview ${esc(s.name)} pieces. Choose Apply appearance to save this design."><span class="piece-sample">${['wK','wQ','wN','bK','bQ','bN'].map(p=>ArenaI18n.h`<img alt="${p[0]==='w'?ArenaI18n.t('White'):ArenaI18n.t('Black')} ${{K:'king',Q:'queen',N:'knight'}[p[1]]}" src="/pieces/${s.id}/${p}.svg">`).join('')}</span><strong>${esc(s.name)}</strong><span class="piece-selected" aria-hidden="true">Selected</span></button>`).join('')}</div></section><section class="appearance-section appearance-preview"><div><h3>Board preview</h3><div id="appearanceBoard"></div></div><div>${materialFields}<h3>Colors & text</h3><div class="fields"><div class="field"><label for="displayTheme">Theme</label><select id="displayTheme"><option value="dark" ${displayPrefs.theme==='dark'?'selected':''}>Midnight</option><option value="light" ${displayPrefs.theme==='light'?'selected':''}>Daylight</option></select></div>${field('displayFontSize',ArenaI18n.t('Font size'),displayPrefs.fontSize,'number','required min="12" max="24" step="1" aria-describedby="fontSizeHelp"')}${field('squareLight',ArenaI18n.t('Light squares'),displayPrefs.light,'color')}${field('squareDark',ArenaI18n.t('Dark squares'),displayPrefs.dark,'color')}</div><p class="caption" id="fontSizeHelp">12–24 px. Text and controls scale together and are saved with this workspace.</p><button id="importPieces">Import custom SVG pieces…</button></div></section><section class="appearance-section"><div class="section-intro"><h3>Your workspace</h3><p>Show the panels you need. Drag their handles to move them, or their lower-right edges to resize.</p></div><div class="panel-choices">${Object.entries(panelNames).map(([id,name])=>ArenaI18n.h`<label><input type="checkbox" data-showpanel="${id}" ${!panels[id].hidden?'checked':''}> ${esc(name)}</label>`).join('')}</div><div class="layout-tools"><label>Save current arrangement<input id="layoutName" placeholder="Layout name"></label><button id="saveLayout">Save layout</button><label>Saved layouts<select id="layoutChoice"><option value="">Choose a layout</option>${Object.keys(displayPrefs.layouts).map(n=>ArenaI18n.h`<option>${esc(n)}</option>`).join('')}</select></label><button id="loadLayout">Load</button><button id="resetLayout">Reset sizes</button></div></section>`,ArenaI18n.h`<label class="hover-help-setting" data-help="Show control descriptions on mouse hover and keyboard navigation. Turn off for a quieter workspace."><input id="displayHoverHelp" type="checkbox" ${displayPrefs.hoverHelp!==false?'checked':''}> Hover help</label><button class="primary" id="applyDisplay">Apply appearance</button>`);
 // Shortcuts keep text, board finish and layout controls reachable past the gallery.
 const appearanceIndex=document.createElement('nav');appearanceIndex.className='dialog-index';appearanceIndex.setAttribute('aria-label',ArenaI18n.t('Settings sections'));
 for(const target of $$('.appearance-section h3')){const button=document.createElement('button');button.type='button';button.textContent=target.textContent;button.onclick=()=>{target.scrollIntoView({block:'start',behavior:'auto'});appearanceIndex.querySelectorAll('button').forEach(b=>b.classList.toggle('active',b===button))};appearanceIndex.append(button)}
 $('#modal .modal-head').after(appearanceIndex);
 const preview=()=>{const selected=$('#pieceChoice').value;$$('[data-piece-choice]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.pieceChoice===selected)));const host=$('#appearanceBoard');host.innerHTML=boardHtml('r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3','',false).replaceAll('/pieces/'+(state.pieceSet||'classic')+'/', '/pieces/'+selected+'/');host.style.setProperty('--board-light',$('#squareLight').value);host.style.setProperty('--board-dark',$('#squareDark').value);const finish={light:$('#lightMaterial').value,dark:$('#darkMaterial').value};ArenaMaterials.apply(host,finish,{light:$('#squareLight').value,dark:$('#squareDark').value});$('#squareLight').disabled=finish.light!=='solid';$('#squareDark').disabled=finish.dark!=='solid';$$('[data-wood-preset]').forEach(b=>{const preset=ArenaMaterials.presets[b.dataset.woodPreset];b.setAttribute('aria-pressed',String(preset.light===finish.light&&preset.dark===finish.dark))})};
 $('#pieceChoice').onchange=preview;for(const b of $$('[data-piece-choice]'))b.onclick=()=>{$('#pieceChoice').value=b.dataset.pieceChoice;preview()};$('#squareLight').oninput=preview;$('#squareDark').oninput=preview;$('#lightMaterial').onchange=preview;$('#darkMaterial').onchange=preview;for(const b of $$('[data-wood-preset]'))b.onclick=()=>{const p=ArenaMaterials.presets[b.dataset.woodPreset];$('#lightMaterial').value=p.light;$('#darkMaterial').value=p.dark;preview()};$('#lightMaterial').dataset.help=ArenaI18n.t('Choose a built-in finish for light squares. Solid color uses your color picker.');$('#darkMaterial').dataset.help=ArenaI18n.t('Choose a built-in finish for dark squares. All textures work on live, focused and replay boards.');preview();
 $('#applyDisplay').onclick=safely(async()=>{if(!$('#displayFontSize').reportValidity())return;Object.assign(displayPrefs,{hoverHelp:$('#displayHoverHelp').checked,fontSize:Number($('#displayFontSize').value),pieceSet:$('#pieceChoice').value,theme:$('#displayTheme').value,light:$('#squareLight').value,dark:$('#squareDark').value,boardMaterials:{light:$('#lightMaterial').value,dark:$('#darkMaterial').value}});$$('[data-showpanel]').forEach(c=>displayPrefs.panels[c.dataset.showpanel]={...displayPrefs.panels[c.dataset.showpanel],visible:c.checked});applyDisplay();await persistDisplay();$('#modal').close();notify(ArenaI18n.t('Appearance and workspace saved.'))});
 $('#saveLayout').onclick=safely(async()=>{const name=$('#layoutName').value.trim();if(!name)throw Error(ArenaI18n.t('Enter a name for this layout.'));displayPrefs.layouts[name]={pieceSet:displayPrefs.pieceSet,light:displayPrefs.light,dark:displayPrefs.dark,boardMaterials:structuredClone(displayPrefs.boardMaterials||{}),split:displayPrefs.split,panels:structuredClone(displayPrefs.panels),boardCount:displayPrefs.boardCount,graphs:structuredClone(displayPrefs.graphs||[]),evaluation:structuredClone(displayPrefs.evaluation||{})};await persistDisplay();await displayDialog();notify(ArenaI18n.t('Layout saved.'))});
 $('#loadLayout').onclick=safely(async()=>{const layout=displayPrefs.layouts[$('#layoutChoice').value];if(!layout)throw Error(ArenaI18n.t('Choose a saved layout first.'));Object.assign(displayPrefs,structuredClone(layout));applyDisplay();await persistDisplay();$('#modal').close()});
 $('#resetLayout').onclick=safely(async()=>{displayPrefs.panels={focus:{visible:true,order:0},search:{visible:true,order:1},live:{order:2}};displayPrefs.split=58;applyDisplay();await persistDisplay();$('#modal').close()});
 $('#importPieces').onclick=safely(async()=>{const paths=await browse(true);if(paths[0]){const set=await api('pieces',{folder:paths[0]});displayPrefs.pieceSet=set.id;applyDisplay();await persistDisplay();await displayDialog()}});
};
displayButton.onclick=safely(displayDialog);

// Experiments accept search budgets, not tournament chess clocks.
const experimentEditorBeforePolish=newExperiment;
newExperiment=function(kind){experimentEditorBeforePolish(kind);const control=$('#extc [data-tc=kind]');
 for(const option of [...control.options])if(!['nodes','depth','movetime'].includes(option.value))option.remove();
 organizeEditor(kind==='suite'?ArenaI18n.t('Suite source & participants'):ArenaI18n.t('Benchmark cases & participants'));
};

const loadEnginesBeforePolish=loadEngines;
loadEngines=async function(){await loadEnginesBeforePolish();const rows=$('#engineTable tbody');
 if(!state.engines.length){const tr=document.createElement('tr'),td=document.createElement('td');td.colSpan=7;td.className='library-empty';td.textContent=$('#engineSearch').value?ArenaI18n.t('No profiles match this search. Clear the search to see your library.'):ArenaI18n.t('No engines registered yet. Add an executable or scan a folder to begin.');tr.append(td);rows.replaceChildren(tr)}
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
  const disabled=!!(!selected||(id==='pause'&&!['running','draining'].includes(status))||(id==='cancel'&&!live)||(id==='start'&&(status==='running'||status==='draining'||status==='completed'||!!t?.dependency||!!state.workerError||(t?.event&&!t.event.can_diagnostic_start)||(t?.sprt?.frozen&&!t?.sprt_status?.can_diagnostic_start)||(t?.queue&&!t.queue.finished&&t.queue.execution_mode!=='parallel'))));
  if(el.disabled!==disabled)el.disabled=disabled;
 }
 const runLabel=status==='completed'?ArenaI18n.t('✓ Completed'):status==='running'?ArenaI18n.t('▶ Running'):status==='draining'?ArenaI18n.t('Ⅱ Draining'):ArenaI18n.t('▶ Start / resume');
 if($('#start').textContent!==runLabel)$('#start').textContent=runLabel;
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
 stableHtml('#healthContent',ArenaI18n.h`<div class="health-banner ${s.error?'health-problem':''}"><span class="status-orb"></span><div><strong>${s.error?ArenaI18n.t('Storage or worker needs attention'):s.maintenance?ArenaI18n.t('Cleaning tournament data'):ArenaI18n.t('Worker connected')}</strong><p>${s.error?esc(s.error):ArenaI18n.t('Moves and results are saved automatically. Recovery preserves committed results.')}</p></div></div><div class="health-grid">${statTile(ArenaI18n.t('Active games'),s.active_games,ArenaI18n.t('up to ')+s.engine_process_bound+ArenaI18n.t(' engine processes'))}${statTile(ArenaI18n.t('Peak concurrency'),s.max_active_games,ArenaI18n.t('games this session'))}${statTile(ArenaI18n.t('Available memory'),fmt(s.memory_available_gb)+ArenaI18n.t(' GiB'),ArenaI18n.t('system memory'))}${statTile(ArenaI18n.t('Worker uptime'),ArenaClocks.format(s.uptime),ArenaI18n.t('this session'))}</div><div class="storage-location"><span class="section-eyebrow">Tournament data folder</span><code>${esc(s.data_folder)}</code></div>${backupHealth(s.backup)}${s.warning?ArenaI18n.h`<p class="recovery-notice">${esc(s.warning)}</p>`:''}`);
}
renderBoards();updateRunControls();
