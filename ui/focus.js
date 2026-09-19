'use strict';
// The board and search views share a game selection, but not layout space.
function selectedFocusGame(){
 const games=state.live.filter(g=>g.tid===state.tid);
 if(!games.some(g=>g.game===focusId))focusId=games[0]?.game||'';
 const options=games.length?games.map(g=>`<option value="${g.game}">Game ${g.number+1} · ${esc(g.white.name)} / ${esc(g.black.name)}</option>`).join(''):'<option value="">No active game</option>';
 for(const id of ['focusPicker','searchGamePicker']){stableHtml('#'+id,options);$('#'+id).value=focusId;$('#'+id).disabled=!games.length}
 return games.find(g=>g.game===focusId);
}
for(const id of ['focusPicker','searchGamePicker'])$('#'+id).onchange=()=>{focusId=$('#'+id).value;renderFocus()};
$('#searchSide').onchange=()=>{displayPrefs.searchSide=$('#searchSide').value;saveDisplay();renderFocus()};
$('#searchGamePicker').dataset.help='Choose a live game. This selection is shared with the focused board and graphs that follow it.';
$('#searchSide').dataset.help='Follow the thinking engine automatically, or pin White or Black. A pinned engine retains its latest search while the opponent thinks. Scores always use White’s perspective.';

function revealFocusPanel(id){
 displayPrefs.panels[id]={...displayPrefs.panels[id],visible:true};applyDisplay();saveDisplay();
 if(!panels[id].classList.contains('floating-panel'))panels[id].scrollIntoView({block:'nearest'});
 panels[id].querySelector('.panel-heading').focus({preventScroll:true});
}
function syncFocusVisibility(){for(const id of ['focus','search','live'])panels[id].classList.toggle('workspace-inactive',state.view!=='overview'||!state.tid)}
const viewBeforeFocus=view;
view=function(name){viewBeforeFocus(name);syncFocusVisibility()};
function renderFocus(){
 syncFocusVisibility();
 const g=selectedFocusGame(),root=$('#focusContent');
 root.classList.toggle('is-empty',!g);
 if(!panels.focus.hidden){
  if(!g){root.dataset.game='';stableHtml('#focusContent','<div class="panel-empty"><span class="empty-icon">♞</span><h3>Ready for the next game</h3><p>Start or resume a tournament to follow a live board.<br>Completed games remain in Games & attempt history.</p></div>')}
  else{
   if(root.dataset.game!==g.game||!root.querySelector('.focus-board')){
    root.innerHTML=`<div class="focus-toolbar"><span class="focus-game-state"></span><span class="focus-last-move"></span><span class="spacer"></span><button class="subtle" data-focus-search data-help="Show the independently resizable Engine search panel for this game.">Engine search</button><button class="subtle" data-focus-flip data-help="Rotate the live boards without changing the position.">Flip</button><button class="subtle" data-focus-replay data-help="Open saved attempts, move replay, clocks and diagnostic logs for this game.">Replay</button></div><div class="focus-clocks">${clockFace(g,'white')}${clockFace(g,'black')}</div><div class="focus-board" data-help="The board fits the available width and height automatically. Right-drag to draw arrows, right-click to mark squares, or left-click to clear marks."></div>`;
    root.dataset.game=g.game;root._renderedHtml=null;
    root.querySelector('[data-focus-search]').onclick=()=>revealFocusPanel('search');
    root.querySelector('[data-focus-flip]').onclick=()=>{state.flip=!state.flip;renderBoards()};
    root.querySelector('[data-focus-replay]').onclick=safely(()=>gameDetail(g.game));
    for(const side of ['white','black'])root.querySelector(`[data-clock-side=${side}] .clock-name`).title=g[side].name;
   }
   root.querySelector('.focus-game-state').textContent=state.connected===false?'Connection unavailable':g.status;
   root.querySelector('.focus-game-state').classList.toggle('is-thinking',!!g.clock_active&&state.connected!==false);
   root.querySelector('.focus-last-move').textContent=g.san?'Last move '+g.san+' · '+g.ply+' ply':'Opening position';
   updateBoard(root.querySelector('.focus-board'),g.fen,g.last_move);
   if(typeof paintEvaluation==='function')paintEvaluation(root.querySelector('.focus-board'),g,'focus');
   paintLiveClocks();
  }
 }
 renderEngineSearch(g);
};

function renderEngineSearch(g){
 if(panels.search.hidden)return;
 const root=$('#searchContent');
 if(!g){root.dataset.game='';stableHtml('#searchContent','<div class="panel-empty"><h3>Engine search</h3><p>Analysis follows the focused game.<br>You can move or resize this panel independently of the board.</p></div>');return}
 if(root.dataset.game!==g.game||!root.querySelector('.search-stats')){
  root.innerHTML='<div class="search-engine"><div><span class="search-side section-eyebrow"></span><h3 class="search-name"></h3></div><span class="search-phase"></span></div><div class="search-stats"></div><section class="search-pv"><h3 data-help="The principal variation is this engine’s suggested continuation in UCI square notation. It belongs to the move shown above and may change while the engine searches.">Principal variation</h3><p></p></section><p class="search-referee" hidden></p><p class="search-note">Scores and reported WDL use White’s perspective. Missing engine measurements are shown as —.</p>';
  root.dataset.game=g.game;root._renderedHtml=null;
 }
 const choice=$('#searchSide').value,side=choice==='auto'?(g.clock_active||g.info_side||'white'):choice;
 const search=g.searches?.[side],info=search?.info||{},active=g.clock_active===side&&state.connected!==false;
 const label=side==='white'?'White':'Black';
 root.querySelector('.search-side').textContent=label+' engine'+(search?' · move '+search.move_number+(side==='white'?'.':'…'):'');
 root.querySelector('.search-name').textContent=g[side].name;
 root.querySelector('.search-phase').textContent=state.connected===false?'Updates unavailable':active?'Thinking':search?.complete?'Last completed search':search?'Search stopped':'Not searched yet';
 root.querySelector('.search-phase').classList.toggle('thinking',active);
 const cp=info.mate!==undefined?'M'+info.mate:info.cp===undefined?'—':(info.cp>0?'+':'')+(info.cp/100).toFixed(2);
 const exact=n=>Number.isFinite(n)?n.toLocaleString():'not reported';
 const wdl=Array.isArray(info.wdl)&&info.wdl.length===3?info.wdl:null,total=wdl?.reduce((a,b)=>a+b,0);
 stableHtml('#searchContent .search-stats',
  statTile('Evaluation',cp,'White perspective','Positive scores favor White; negative scores favor Black. M indicates a reported mate distance, not a win probability.')+
  statTile('Search depth',info.depth??'—',info.seldepth===undefined?'plies':'Selective '+info.seldepth,'Main depth and selective depth, in plies, for this engine’s displayed search.')+
  statTile('Nodes searched',compactNumber(info.nodes),'positions','Exact node count: '+exact(info.nodes)+'. Counts belong to this search; engine architectures may count differently.')+
  statTile('Search speed',compactNumber(info.nps),'nodes / second','Exact reported NPS: '+exact(info.nps)+'. This is reported by the engine, not estimated by the interface.')+
  statTile('Search time',info.time===undefined?'—':(info.time/1000).toFixed(2)+' s','engine reported','Engine-reported search time. This is separate from the game clock and watchdogs.')+
  statTile('Hash used',info.hashfull===undefined?'—':(info.hashfull/10).toFixed(1)+'%','hash table','Engine hash occupancy converted from per mille to percent.')+
  statTile('Tablebase hits',compactNumber(info.tbhits),'successful probes','Exact reported tablebase hits: '+exact(info.tbhits)+'. Referee tablebases are configured separately.')+
  statTile('White W / D / L',total?wdl.map(n=>(100*n/total).toFixed(0)).join(' / ')+'%':'—','engine estimate','Engine-reported win, draw and loss estimates from White’s perspective, normalized to percentages. These are not tournament results.'));
 const pv=Array.isArray(info.pv)?info.pv.join(' '):info.pv;
 root.querySelector('.search-pv p').textContent=pv||'Waiting for this engine’s analysis…';
 const note=root.querySelector('.search-referee');note.hidden=!g.tablebase_note;note.textContent=g.tablebase_note||'';
}

// Floating windows remain inside this application and share the same worker.
let focusWindowZ=100;
const focusWindowIds=['focus','search','live'];
const panelSettings=id=>displayPrefs.panels[id]||{};
const floating=id=>!!(panelSettings(id).floating||panelSettings(id).maximized);
function panelMinimum(id){return {width:Math.min(Math.max(320,(id==='focus'?22:20)*displayPrefs.fontSize),innerWidth-16),height:Math.min(id==='focus'?Math.max(480,320+12*displayPrefs.fontSize):id==='live'?300:240,innerHeight-16)}}
function dockPanelHeight(id,height){return id==='live'?Math.min(innerHeight-16,Math.max(panelMinimum(id).height,height)):Math.max(panelMinimum(id).height,height)}
function fitPanelBounds(id,bounds={}){
 const min=panelMinimum(id),width=Math.min(innerWidth-16,Math.max(min.width,Number(bounds.width)||640)),height=Math.min(innerHeight-16,Math.max(min.height,Number(bounds.height)||(id==='focus'?740:570)));
 return {width,height,left:Math.max(8,Math.min(innerWidth-width-8,Number.isFinite(bounds.left)?bounds.left:Math.max(8,(innerWidth-width)/2))),top:Math.max(8,Math.min(innerHeight-height-8,Number.isFinite(bounds.top)?bounds.top:40))};
}
function setPanelBounds(panel,bounds){for(const key of ['width','height','left','top'])panel.style[key]=bounds[key]+'px'}
function applyFocusWindows(){
 $('#searchSide').value=['white','black'].includes(displayPrefs.searchSide)?displayPrefs.searchSide:'auto';
 for(const id of focusWindowIds){
  const panel=panels[id],p=panelSettings(id),isFloating=floating(id);
  panel.classList.toggle('floating-panel',isFloating);panel.classList.toggle('expanded-panel',!!p.maximized);
  panel.querySelector('.dock-handle').hidden=isFloating;
  panel.querySelector('[data-float]').textContent=isFloating?'Dock':'Float';
  panel.querySelector('[data-float]').dataset.help=isFloating?'Return this window to its saved workspace column.':'Float this panel inside the app, with independent width and height. Drag its heading to move it.';
  panel.querySelector('[data-expand]').textContent=p.maximized?'Restore':'Expand';
  panel.querySelector('[data-expand]').setAttribute('aria-pressed',String(!!p.maximized));
  const grip=panel.querySelector('.focus-resizer');grip.hidden=!!p.maximized;
  if(isFloating){document.body.append(panel);panel.style.zIndex=String(++focusWindowZ);setPanelBounds(panel,p.maximized?{left:8,top:8,width:innerWidth-16,height:innerHeight-16}:fitPanelBounds(id,p.bounds))}
  else{for(const key of ['width','left','top','zIndex'])panel.style[key]='';panel.style.height=p.height?dockPanelHeight(id,p.height)+'px':''}
 }
}
function saveFocusSize(id){
 const panel=panels[id],p=panelSettings(id),r=panel.getBoundingClientRect();
 displayPrefs.panels[id]={...p,...(floating(id)?{bounds:{left:r.left,top:r.top,width:r.width,height:r.height}}:{height:r.height})};saveDisplay();
}
for(const id of focusWindowIds){
 const panel=panels[id],heading=panel.querySelector('.panel-heading'),hide=heading.querySelector('button[title="Hide panel"]');
 heading.tabIndex=0;heading.dataset.help='Float this panel to move it by its heading. Use the corner grip to resize. With a floating heading focused, arrow keys move the window.';
 const float=document.createElement('button');float.className='subtle';float.dataset.float='';float.textContent='Float';heading.insertBefore(float,hide);
 const expand=document.createElement('button');expand.className='subtle';expand.dataset.expand='';expand.textContent='Expand';expand.dataset.help='Use the full application area for this panel. Restore returns to the previous size and position.';heading.insertBefore(expand,hide);
 float.onclick=()=>{displayPrefs.panels[id]={...panelSettings(id),floating:!floating(id),maximized:false};applyDisplay();saveDisplay()};
 expand.onclick=()=>{displayPrefs.panels[id]={...panelSettings(id),maximized:!panelSettings(id).maximized};applyDisplay();saveDisplay()};
 const grip=document.createElement('div');grip.className='focus-resizer';grip.tabIndex=0;grip.setAttribute('role','separator');grip.setAttribute('aria-label','Resize '+panelNames[id]);grip.dataset.help=id==='live'?'Drag to change height; floating windows also change width. Use arrow keys when focused, or Size in the header. Scroll inside the panel to reach more boards.':'Drag to change height; floating windows also change width. Use arrow keys when focused. The board and text scale automatically.';panel.append(grip);
 let gesture;
 function begin(e,kind){if(e.button!==0||panelSettings(id).maximized)return;if(kind==='move'&&(!floating(id)||e.target.closest('button,select')))return;e.preventDefault();e.stopPropagation();const r=panel.getBoundingClientRect();gesture={kind,x:e.clientX,y:e.clientY,width:r.width,height:r.height,left:r.left,top:r.top};e.currentTarget.setPointerCapture(e.pointerId);panel.style.zIndex=String(++focusWindowZ)}
 function move(e){if(!gesture)return;const dx=e.clientX-gesture.x,dy=e.clientY-gesture.y;
  if(gesture.kind==='move')setPanelBounds(panel,fitPanelBounds(id,{...gesture,left:gesture.left+dx,top:gesture.top+dy}));
  else if(floating(id))setPanelBounds(panel,fitPanelBounds(id,{...gesture,width:Math.min(innerWidth-gesture.left-8,gesture.width+dx),height:Math.min(innerHeight-gesture.top-8,gesture.height+dy)}));
  else panel.style.height=dockPanelHeight(id,gesture.height+dy)+'px';
 }
 function end(e){if(!gesture)return;gesture=null;if(e.currentTarget.hasPointerCapture(e.pointerId))e.currentTarget.releasePointerCapture(e.pointerId);saveFocusSize(id)}
 for(const [target,kind] of [[heading,'move'],[grip,'size']]){target.onpointerdown=e=>begin(e,kind);target.onpointermove=move;target.onpointerup=end;target.onpointercancel=end;target.onlostpointercapture=()=>{if(gesture){gesture=null;saveFocusSize(id)}};
  target.onkeydown=e=>{if(e.target!==target||!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)||panelSettings(id).maximized)return;if(kind==='move'&&!floating(id))return;e.preventDefault();const r=panel.getBoundingClientRect(),dx=e.key==='ArrowLeft'?-20:e.key==='ArrowRight'?20:0,dy=e.key==='ArrowUp'?-20:e.key==='ArrowDown'?20:0;
   if(kind==='move')setPanelBounds(panel,fitPanelBounds(id,{width:r.width,height:r.height,left:r.left+dx,top:r.top+dy}));
   else if(floating(id))setPanelBounds(panel,fitPanelBounds(id,{width:r.width+dx,height:r.height+dy,left:r.left,top:r.top}));
   else panel.style.height=dockPanelHeight(id,r.height+dy)+'px';saveFocusSize(id);
  };
 }
 panel.addEventListener('pointerdown',()=>{if(floating(id))panel.style.zIndex=String(++focusWindowZ)});
}
const liveSizeButton=document.createElement('button');liveSizeButton.className='subtle';liveSizeButton.textContent='Size…';liveSizeButton.dataset.help='Set the Live boards height here without reaching its bottom corner. Float the panel to choose its width too.';panels.live.querySelector('.panel-heading').insertBefore(liveSizeButton,panels.live.querySelector('[data-float]'));
liveSizeButton.onclick=()=>{
 const p=panelSettings('live'),r=panels.live.getBoundingClientRect(),min=panelMinimum('live'),free=!!p.floating;
 modal('Live boards size',`<p>Boards scroll inside this panel. Its size is saved with your workspace.</p><div class="fields">${field('livePanelHeight','Panel height (px)',Math.round(r.height),'number',`required min="${Math.ceil(min.height)}" max="${Math.floor(innerHeight-16)}" step="1"`)}${field('livePanelWidth','Panel width (px)',Math.round(r.width),'number',free?`required min="${Math.ceil(min.width)}" max="${Math.floor(innerWidth-16)}" step="1"`:'disabled')}</div><p class="caption">${free?'Width and height are independent in a floating window.':'Docked width follows the workspace column. Choose Float to resize width independently.'}</p>`,`<button id="fitLivePanel">Fit to window</button><button class="primary" id="applyLivePanelSize">Apply size</button>`);
 $('#livePanelHeight').dataset.help='Set the panel height in pixels, limited to the available application height. Extra boards scroll inside it.';
 $('#livePanelWidth').dataset.help=free?'Set the floating panel width in pixels. Boards reflow into columns automatically.':'Docked width follows the workspace divider. Float this panel to set its width.';
 const apply=safely(async(height,width)=>{displayPrefs.panels.live={...p,maximized:false,...(free?{bounds:fitPanelBounds('live',{left:r.left,top:r.top,width,height})}:{height:dockPanelHeight('live',height)})};applyDisplay();await persistDisplay();$('#modal').close()});
 $('#applyLivePanelSize').onclick=()=>{if(!$('#livePanelHeight').reportValidity()||(free&&!$('#livePanelWidth').reportValidity()))return;apply(Number($('#livePanelHeight').value),Number($('#livePanelWidth').value))};
 $('#fitLivePanel').dataset.help='Restore a manageable height that fits the app; floating windows also return to a standard width.';
 $('#fitLivePanel').onclick=()=>apply(Math.min(680,innerHeight*.8),Math.min(800,innerWidth-16));
};
const applyDisplayBeforeFocus=applyDisplay;
applyDisplay=function(){applyDisplayBeforeFocus();applyFocusWindows();renderFocus()};
const focusSizeObserver=new ResizeObserver(entries=>{for(const entry of entries){const {width,height}=entry.contentRect,id=entry.target.dataset.panel;const scale=Math.max(1,Math.min(1.6,width/(id==='focus'?620:600),height/(id==='focus'?720:580)));entry.target.style.setProperty('--focus-text-scale',scale.toFixed(3))}});
for(const id of focusWindowIds)focusSizeObserver.observe(panels[id]);
window.addEventListener('resize',()=>{for(const id of focusWindowIds)if(floating(id)){const p=panelSettings(id);setPanelBounds(panels[id],p.maximized?{left:8,top:8,width:innerWidth-16,height:innerHeight-16}:fitPanelBounds(id,p.bounds))}});
setInterval(()=>{if(state.connected===false)renderFocus()},1000);
applyDisplay();
