'use strict';
// Preferences belong to the durable workspace, independent of the local HTTP port.
let displayPrefs={theme:'dark',fontSize:14,pieceSet:'classic',boardCount:2,light:'#dae1d6',dark:'#718e88',split:65,panels:{},layouts:{}};
let preferenceTimer,preferenceSave=Promise.resolve();
function persistDisplay(){
 clearTimeout(preferenceTimer);const prefs=structuredClone(displayPrefs);
 preferenceSave=preferenceSave.catch(()=>{}).then(()=>api('preferences',prefs));return preferenceSave;
}
function saveDisplay(){clearTimeout(preferenceTimer);preferenceTimer=setTimeout(safely(persistDisplay),250)}
const panelNames={standings:'Live standings',live:'Live boards',games:'Games & attempt history',focus:'Focused game',search:'Engine search'};
const dock=document.createElement('div');dock.className='dock-workspace';dock.innerHTML='<div class="dock-column" data-dock="left"></div><div class="dock-divider" role="separator" tabindex="0" aria-label="Resize workspace columns" aria-orientation="vertical"></div><div class="dock-column" data-dock="right"></div>';
const oldGrid=$('.workspace-grid');oldGrid.before(dock);
const panels={standings:$('.standings-panel'),live:$('.live-panel'),games:$('.games-panel')};
panels.focus=document.createElement('div');panels.focus.className='panel';panels.focus.innerHTML='<div class="panel-title"><h2>Focused game</h2><select id="focusPicker" aria-label="Focused game"></select></div><div id="focusContent" class="focus-content"></div>';
panels.search=document.createElement('div');panels.search.className='panel';panels.search.innerHTML='<div class="panel-title"><h2>Engine search</h2><select id="searchGamePicker" aria-label="Search information game"></select><select id="searchSide" aria-label="Engine search perspective"><option value="auto">Follow thinking engine</option><option value="white">White engine</option><option value="black">Black engine</option></select></div><div id="searchContent" class="search-content"></div>';
function installPanel(id,panel){
 panel.dataset.panel=id;panel.classList.add('dock-panel');const handle=document.createElement('button');handle.className='dock-handle subtle';handle.textContent='⠿';handle.draggable=true;handle.title='Drag panel to either workspace column';handle.setAttribute('aria-label','Move '+panelNames[id]);panel.querySelector('.panel-title').prepend(handle);
 handle.ondragstart=e=>{e.dataTransfer.setData('text/arena-panel',id);e.dataTransfer.effectAllowed='move';dock.classList.add('dragging')};handle.ondragend=()=>dock.classList.remove('dragging');
 const hide=document.createElement('button');hide.className='subtle';hide.textContent='×';hide.title='Hide panel';hide.onclick=()=>{displayPrefs.panels[id]={...displayPrefs.panels[id],visible:false};applyDisplay();saveDisplay()};panel.querySelector('.panel-title').append(hide);
 panel.addEventListener('pointerup',()=>{if(panel.style.height&&!panel.classList.contains('floating-panel')){displayPrefs.panels[id]={...displayPrefs.panels[id],height:Math.round(panel.getBoundingClientRect().height)};saveDisplay()}});
}
for(const [id,panel] of Object.entries(panels))installPanel(id,panel);
oldGrid.remove();
for(const [id,panel] of Object.entries(panels))dock.querySelector(`[data-dock=${['live','focus','search'].includes(id)?'right':'left'}]`).append(panel);
for(const column of dock.querySelectorAll('.dock-column')){
 column.ondragover=e=>{if(e.dataTransfer.types.includes('text/arena-panel')){e.preventDefault();e.dataTransfer.dropEffect='move'}};
 column.ondrop=e=>{const id=e.dataTransfer.getData('text/arena-panel');if(!panels[id])return;e.preventDefault();const target=e.target.closest('[data-panel]');if(target&&target!==panels[id])column.insertBefore(panels[id],target);else column.append(panels[id]);savePanelOrder();dock.classList.remove('dragging')};
}
function savePanelOrder(){for(const column of dock.querySelectorAll('.dock-column'))[...column.children].forEach((p,i)=>displayPrefs.panels[p.dataset.panel]={...displayPrefs.panels[p.dataset.panel],column:column.dataset.dock,order:i});saveDisplay()}
function applyDisplay(){
 if(typeof syncGraphs==='function')syncGraphs();
 applyConfidenceDisplay();
 const fontSize=Number(displayPrefs.fontSize);displayPrefs.fontSize=Number.isFinite(fontSize)?Math.max(12,Math.min(24,fontSize)):14;
 document.documentElement.style.fontSize=displayPrefs.fontSize+'px';
 document.body.classList.toggle('light',displayPrefs.theme==='light');state.pieceSet=displayPrefs.pieceSet;$('#boardCount').value=String(displayPrefs.boardCount);document.documentElement.style.setProperty('--board-light',displayPrefs.light);document.documentElement.style.setProperty('--board-dark',displayPrefs.dark);dock.style.setProperty('--dock-split',Math.max(25,Math.min(80,displayPrefs.split))+'%');
 Object.keys(panels).sort((a,b)=>(displayPrefs.panels[a]?.order??({focus:0,search:1,live:2}[a]??Object.keys(panels).indexOf(a)))-(displayPrefs.panels[b]?.order??({focus:0,search:1,live:2}[b]??Object.keys(panels).indexOf(b)))).forEach(id=>{const p=displayPrefs.panels[id]||{},column=p.column||(['live','focus','search'].includes(id)?'right':'left');dock.querySelector(`[data-dock=${column==='right'?'right':'left'}]`).append(panels[id]);panels[id].hidden=p.visible===false;panels[id].style.height=p.height?Math.max(200,p.height)+'px':''});renderBoards();
}
const divider=dock.querySelector('.dock-divider');
function resizeSplit(value){displayPrefs.split=Math.max(25,Math.min(80,value));dock.style.setProperty('--dock-split',displayPrefs.split+'%')}
divider.onpointerdown=e=>{divider.setPointerCapture(e.pointerId);divider.dataset.drag='yes'};divider.onpointermove=e=>{if(divider.dataset.drag){const rect=dock.getBoundingClientRect();resizeSplit(100*(e.clientX-rect.left)/rect.width)}};divider.onpointerup=()=>{delete divider.dataset.drag;saveDisplay()};divider.onkeydown=e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();resizeSplit(displayPrefs.split+(e.key==='ArrowRight'?2:-2));saveDisplay()}};
$('#theme').onclick=()=>{displayPrefs.theme=displayPrefs.theme==='light'?'dark':'light';applyDisplay();saveDisplay()};$('#boardCount').onchange=()=>{displayPrefs.boardCount=Number($('#boardCount').value);renderBoards();saveDisplay()};
const displayButton=document.createElement('button');displayButton.className='subtle';displayButton.textContent='Display & layout';$('#theme').after(displayButton);displayButton.onclick=safely(displayDialog);
async function displayDialog(){
 const sets=await api('pieces');modal('Display & saved workspace',`<div class="fields"><div class="field"><label>Vector pieces</label><select id="pieceChoice">${sets.map(s=>`<option value="${s.id}" ${s.id===displayPrefs.pieceSet?'selected':''}>${esc(s.name)}</option>`).join('')}</select></div><div class="field"><label>Theme</label><select id="displayTheme"><option value="dark" ${displayPrefs.theme==='dark'?'selected':''}>Dark</option><option value="light" ${displayPrefs.theme==='light'?'selected':''}>Light</option></select></div><div class="field full"><label for="displayFontSize">Font size</label><input id="displayFontSize" type="number" required min="12" max="24" step="1" value="${displayPrefs.fontSize}" aria-describedby="fontSizeHelp"><small id="fontSizeHelp">12–24 px (default 14). Scales text, labels and controls throughout the interface. Saved for this workspace.</small></div>${field('squareLight','Light squares',displayPrefs.light,'color')}${field('squareDark','Dark squares',displayPrefs.dark,'color')}</div><div class="section-label">WORKSPACE PANELS</div><p class="caption">Drag a panel handle into either column or above another panel. Drag the divider to change column widths. Resize a panel from its lower-right corner; the focused board fits its width and height. Preferences save automatically.</p><div class="fields">${Object.entries(panelNames).map(([id,name])=>`<label><input type="checkbox" data-showpanel="${id}" ${!panels[id].hidden?'checked':''}> ${name}</label>`).join('')}</div><div class="section-label">NAMED LAYOUTS</div><div class="toolbar"><input id="layoutName" placeholder="Layout name"><button id="saveLayout">Save layout</button><select id="layoutChoice"><option value="">Choose saved layout</option>${Object.keys(displayPrefs.layouts).map(n=>`<option>${esc(n)}</option>`).join('')}</select><button id="loadLayout">Load</button><button id="resetLayout">Reset sizes</button></div><div class="section-label">CUSTOM PIECES</div><p class="caption">Import a folder containing 12 static SVG files: wK.svg, wQ.svg, wR.svg, wB.svg, wN.svg, wP.svg and matching b files.</p><button id="importPieces">Import SVG folder…</button>`,`<button class="primary" id="applyDisplay">Apply display</button>`);
 $('#applyDisplay').onclick=safely(async()=>{if(!$('#displayFontSize').reportValidity())return;Object.assign(displayPrefs,{fontSize:Number($('#displayFontSize').value),pieceSet:$('#pieceChoice').value,theme:$('#displayTheme').value,light:$('#squareLight').value,dark:$('#squareDark').value});$$('[data-showpanel]').forEach(c=>displayPrefs.panels[c.dataset.showpanel]={...displayPrefs.panels[c.dataset.showpanel],visible:c.checked});applyDisplay();await persistDisplay();$('#modal').close()});
 $('#saveLayout').onclick=()=>{const name=$('#layoutName').value.trim();if(!name)return;displayPrefs.layouts[name]={split:displayPrefs.split,panels:structuredClone(displayPrefs.panels),boardCount:displayPrefs.boardCount,graphs:structuredClone(displayPrefs.graphs||[]),evaluation:structuredClone(displayPrefs.evaluation||{})};saveDisplay();displayDialog()};
 $('#loadLayout').onclick=()=>{const layout=displayPrefs.layouts[$('#layoutChoice').value];if(layout){Object.assign(displayPrefs,structuredClone(layout));applyDisplay();saveDisplay();$('#modal').close()}};
 $('#resetLayout').onclick=()=>{displayPrefs.panels={};displayPrefs.split=65;applyDisplay();saveDisplay();$('#modal').close()};
 $('#importPieces').onclick=safely(async()=>{const paths=await browse(true);if(paths[0]){const set=await api('pieces',{folder:paths[0]});displayPrefs.pieceSet=set.id;applyDisplay();saveDisplay();await displayDialog()}});
}
const intervalChoice=document.createElement('select');intervalChoice.id='confidenceMethod';intervalChoice.setAttribute('aria-label','Confidence interval method');intervalChoice.innerHTML='<option value="normal">Normal approximation</option><option value="conservative">Conservative Hoeffding bound</option>';
panels.standings.querySelector('.panel-title').insertBefore(intervalChoice,$('#exportStats'));
function applyConfidenceDisplay(){
 state.confidence=Number(displayPrefs.confidence)||95;state.standSort=displayPrefs.standSort||'rank';state.standDirection=displayPrefs.standDirection||'asc';
 state.ciMethod=displayPrefs.ciMethod==='conservative'?'conservative':'normal';intervalChoice.value=state.ciMethod;if(typeof syncResultControls==='function')syncResultControls();
 panels.standings.querySelector('.caption').textContent=`Δ Elo versus sampled opposition · ${state.confidence}% ${state.ciMethod==='conservative'?'conservative':'normal'} confidence intervals · complete opening pairs when paired. Select an engine for head-to-head results.`;
}
intervalChoice.onchange=safely(async()=>{displayPrefs.ciMethod=intervalChoice.value;applyConfidenceDisplay();++tournamentRefresh;await persistDisplay();if(state.tid)await refreshTournament();});
applyConfidenceDisplay();
let focusId='';
// Board annotations are local analysis marks and never modify official moves.
let annotationStart=null;
document.addEventListener('contextmenu',e=>{if(e.target.closest('.board'))e.preventDefault()});
document.addEventListener('pointerdown',e=>{const sq=e.target.closest('[data-square]'),board=sq?.closest('.board');if(!board)return;if(e.button===2){e.preventDefault();annotationStart={square:sq.dataset.square,board}}else if(e.button===0)board.querySelector('.board-arrows')?.replaceChildren()});
document.addEventListener('pointerup',e=>{if(e.button!==2||!annotationStart)return;const start=annotationStart;annotationStart=null;const sq=e.target.closest('[data-square]');if(!sq||sq.closest('.board')!==start.board)return;e.preventDefault();const center=s=>{let x=s.charCodeAt(0)-97,y=8-Number(s[1]);if(start.board.dataset.flip==='true'){x=7-x;y=7-y}return [x*100+50,y*100+50]},a=center(start.square),b=center(sq.dataset.square),svg=start.board.querySelector('.board-arrows');if(start.square===sq.dataset.square){svg.insertAdjacentHTML('beforeend',`<circle cx="${a[0]}" cy="${a[1]}" r="39" fill="none" stroke="#f5b443" stroke-width="12"/>`)}else{const dx=b[0]-a[0],dy=b[1]-a[1],length=Math.hypot(dx,dy),ux=dx/length,uy=dy/length,tip=[b[0]-ux*7,b[1]-uy*7],base=[b[0]-ux*38,b[1]-uy*38];svg.insertAdjacentHTML('beforeend',`<path d="M${a} L${base}" fill="none" stroke="#f5b443" stroke-width="18" stroke-linecap="round"/><path d="M${tip} L${base[0]-uy*25},${base[1]+ux*25} L${base[0]+uy*25},${base[1]-ux*25} Z" fill="#f5b443"/>`)}});
// Browser frame intervals and Event Timing are reported separately from engine throughput.
const frameSamples=[],eventSamples=[];let previousFrame=0,longTasks=0,longTaskMs=0;
function recordFrame(t){if(document.visibilityState==='visible'&&previousFrame){frameSamples.push(t-previousFrame);if(frameSamples.length>1800)frameSamples.shift()}previousFrame=document.visibilityState==='visible'?t:0;requestAnimationFrame(recordFrame)}requestAnimationFrame(recordFrame);
try{new PerformanceObserver(list=>{for(const entry of list.getEntries()){longTasks++;longTaskMs+=entry.duration}}).observe({type:'longtask',buffered:true})}catch{}
try{new PerformanceObserver(list=>{for(const entry of list.getEntries()){eventSamples.push(entry.duration);if(eventSamples.length>500)eventSamples.shift()}}).observe({type:'event',buffered:true,durationThreshold:16})}catch{}
const percentile=(v,p)=>v.length?[...v].sort((a,b)=>a-b)[Math.min(v.length-1,Math.floor(v.length*p))]:null;
setInterval(safely(async()=>{const metrics={time:new Date().toISOString(),client:window.chrome?.webview?'desktop':'browser',graph_panels:document.querySelectorAll('.graph-panel:not([hidden])').length,visible:document.visibilityState==='visible',visible_boards:Number($('#boardCount').value),frame_samples:frameSamples.length,frame_p50_ms:percentile(frameSamples,.5),frame_p95_ms:percentile(frameSamples,.95),frame_max_ms:frameSamples.length?Math.max(...frameSamples):null,event_samples:eventSamples.length,event_p95_ms:percentile(eventSamples,.95),long_tasks:longTasks,long_task_ms:longTaskMs};await api('ui-metrics',metrics)}),5000);
applyDisplay();
safely(async()=>{const prefs=await api('preferences');displayPrefs={...displayPrefs,...prefs,panels:prefs.panels||{},layouts:prefs.layouts||{}};applyDisplay()})();
