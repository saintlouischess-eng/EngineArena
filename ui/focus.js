'use strict';
// The board and search views share a game selection, but not layout space.
let retainedFocus=null,retainedTid='';
function selectedFocusGame(){
 if(retainedTid!==state.tid){retainedFocus=null;retainedTid=state.tid;focusId=''}
 const games=state.live.filter(g=>g.tid===state.tid);
 if(typeof focusDirectorSelect==='function'){
  const chosen=focusDirectorSelect(games);if(chosen){focusId=chosen.game;retainedFocus=chosen}
 }else{
  const live=games.find(g=>g.game===focusId);if(live)retainedFocus=live;
  if(!live&&games.length&&displayPrefs.followNextGame!==false&&!(typeof browsingRecordedMoves==='function'&&browsingRecordedMoves())){focusId=games[0].game;retainedFocus=games[0]}
 }
 if(retainedFocus&&!games.some(g=>g.game===retainedFocus.game))games.push({...retainedFocus,clock_active:null,status:retainedFocus.clock_active?ArenaI18n.t('Saved game'):retainedFocus.status});
 if(!games.some(g=>g.game===focusId))focusId=typeof followedProfile==='function'&&followedProfile()?'':games[0]?.game||'';
 const options=games.length?games.map(g=>ArenaI18n.h`<option value="${g.game}">Game ${g.number+1} · ${esc(g.white.name)} / ${esc(g.black.name)}</option>`).join(''):ArenaI18n.h('<option value="">No active game</option>');
 for(const id of ['focusPicker','searchGamePicker']){stableHtml('#'+id,options);$('#'+id).value=focusId;$('#'+id).disabled=!games.length}
 const chosen=games.find(g=>g.game===focusId);if(chosen)retainedFocus=chosen;return chosen;
}
for(const id of ['focusPicker','searchGamePicker'])$('#'+id).onchange=()=>{focusId=$('#'+id).value;if(typeof clearEngineFollow==='function')clearEngineFollow();renderFocus()};
$('#searchSide').onchange=()=>{displayPrefs.searchSide=$('#searchSide').value;saveDisplay();renderFocus()};
$('#searchGamePicker').dataset.help=ArenaI18n.t('Choose a live game. This selection is shared with the focused board and graphs that follow it.');
$('#searchSide').dataset.help=ArenaI18n.t('Follow the thinking engine automatically, or pin White or Black. A pinned engine retains its latest search while the opponent thinks. Scores always use White’s perspective.');

function revealFocusPanel(id){
 displayPrefs.panels[id]={...displayPrefs.panels[id],visible:true};applyDisplay();saveDisplay();
 if(!panels[id].classList.contains('floating-panel'))panels[id].scrollIntoView({block:'nearest'});
 panels[id].querySelector('.panel-heading').focus({preventScroll:true});
}
function syncFocusVisibility(){for(const id of ['focus','search','live','games','moves'])panels[id].classList.toggle('workspace-inactive',state.view!=='overview'||!state.tid)}
const viewBeforeFocus=view;
view=function(name){viewBeforeFocus(name);syncFocusVisibility()};
function renderFocus(){
 syncFocusVisibility();
 const current=selectedFocusGame(),g=typeof gameMovesView==='function'?gameMovesView(current):current,root=$('#focusContent');
 root.classList.toggle('is-empty',!g);
 if(!panels.focus.hidden){
  if(!g){root.dataset.game='';stableHtml('#focusContent',ArenaI18n.h('<div class="panel-empty"><span class="empty-icon">♞</span><h3>Ready for the next game</h3><p>Start or resume a tournament to follow a live board.<br>Completed games remain in Games & attempt history.</p></div>'))}
  else{
   const changedGame=root.dataset.game!==g.game;
   // Keep the canvas and GPU resources when following a different game.
   if(!root.querySelector('.focus-board')){
    root.innerHTML=ArenaI18n.h`<div class="focus-toolbar"><span class="focus-game-state"></span><span class="focus-last-move"></span><span class="spacer"></span><button class="subtle" data-focus-search data-help="Show the independently resizable Engine search panel for this game.">Engine search</button><button class="subtle" data-focus-flip data-help="Rotate the live boards without changing the position.">Flip</button><button class="subtle" data-focus-replay data-help="Open saved attempts, move replay, clocks and diagnostic logs for this game.">Replay</button></div><div class="focus-stage"><div class="focus-clocks">${clockFace(g,'white')}${clockFace(g,'black')}</div><div class="focus-board" data-help="The board fits the available width and height automatically. Right-drag to draw arrows, right-click to mark squares, or left-click to clear marks."></div></div>`;
    root.dataset.game=g.game;root._renderedHtml=null;
    root.querySelector('[data-focus-search]').onclick=()=>revealFocusPanel('search');
    root.querySelector('[data-focus-flip]').onclick=()=>{state.flip=!state.flip;renderBoards()};
    root.querySelector('[data-focus-replay]').onclick=safely(()=>gameDetail(root.dataset.game));
   }
   root.dataset.game=g.game;
   if(changedGame){
    root.querySelector('.board-arrows')?.replaceChildren();
    for(const side of ['white','black']){const name=root.querySelector(`[data-clock-side=${side}] .clock-name`);name.textContent=(side==='white'?ArenaI18n.t('White'):ArenaI18n.t('Black'))+' · '+g[side].name;name.title=g[side].name;}
   }
   root.querySelector('.focus-game-state').textContent=state.connected===false?ArenaI18n.t('Connection unavailable'):[g.competition_label,g.status].filter(Boolean).join(' · ');
   root.querySelector('.focus-game-state').classList.toggle('is-thinking',!!g.clock_active&&state.connected!==false);
   root.querySelector('.focus-last-move').textContent=g.san?(g.opening_move?ArenaI18n.t('Opening')+' · '+g.move_label+' '+g.san:ArenaI18n.t('Last move ')+g.san+' · '+g.ply+ArenaI18n.t(' ply')):ArenaI18n.t('Opening position');
   paintDrawRule(root,g);
   if(typeof paintFocusBoard==='function')paintFocusBoard(root.querySelector('.focus-board'),g.fen,g.last_move,g.crown_squares||[],g.knight_facings||{},g);
   else updateBoard(root.querySelector('.focus-board'),g.fen,g.last_move);
   if(typeof paintEvaluation==='function')paintEvaluation(root.querySelector('.focus-board'),g,'focus');
   if(typeof styleFocusLayout==='function')styleFocusLayout(root);
   for(const el of root.querySelectorAll('.clock-face')){if(g.reviewing||!state.live.some(x=>x.game===g.game))el.removeAttribute('data-clock-game');else el.dataset.clockGame=g.game;paintClock(el,g,el.dataset.clockSide)}
   paintLiveClocks();
  }
 }
 if(typeof syncBoard3dControlToggle==='function')syncBoard3dControlToggle();
 renderEngineSearch(current);
 if(typeof refreshGameMoves==='function')refreshGameMoves(current);
};

function renderEngineSearch(g){
 if(panels.search.hidden)return;
 const root=$('#searchContent');
 if(!g){root.dataset.game='';stableHtml('#searchContent',ArenaI18n.h('<div class="panel-empty"><h3>Engine search</h3><p>Analysis follows the focused game.<br>You can move or resize this panel independently of the board.</p></div>'));return}
 if(root.dataset.game!==g.game||!root.querySelector('.search-stats')){
  root.innerHTML=ArenaI18n.h('<div class="search-engine"><div><span class="search-side section-eyebrow"></span><h3 class="search-name"></h3></div><span class="search-phase"></span></div><div class="search-stats"></div><section class="search-pv"><h3 data-help="The principal variation is this engine’s suggested continuation in UCI square notation, with move numbers from its searched position. A line starting with Black uses an ellipsis.">Current principal variation</h3><p tabindex="0" role="region" aria-label="Current principal variation"></p></section><section class="search-history" aria-label="Best move and search history"><div class="search-history-heading"><h3 data-help="A new entry is recorded only when the first, best move changes. Refinements to the continuation or statistics update the current entry. Earlier entries keep their last reported statistics and full numbered PV.">Best-move history</h3><div class="search-history-actions"><button type="button" class="subtle search-history-focus" aria-pressed="false" data-help="Hide the overview statistics and current PV to give history more space. Expand any move row for its full search statistics and PV. This display preference is saved.">More history</button><button type="button" class="subtle search-history-latest" data-help="Return to the newest earlier choices. When you scroll down to read older choices, incoming updates preserve your place.">Latest</button></div></div><p class="search-history-caption"></p><div class="search-history-columns search-choice-row" aria-hidden="true"><span>Move · newest first</span><span>Eval</span><span>D / SD</span><span class="search-choice-time">Time</span><span class="search-choice-nodes">Nodes</span><span></span></div><div class="search-history-current"></div><div class="search-history-list" tabindex="0" role="region" aria-label="Earlier search choices" data-help="Earlier choices for this engine’s displayed search, newest first. Compact rows keep your reading position as new choices arrive. Expand a row for exact statistics and its complete numbered PV."></div></section><p class="search-referee" hidden></p><p class="search-note">White’s perspective · D / SD: depth / selective depth · —: not reported. History resets for each new search.</p>');
  root.dataset.game=g.game;root._renderedHtml=null;
  root.querySelector('.search-history-latest').onclick=()=>{root.querySelector('.search-history-list').scrollTop=0};
  root.querySelector('.search-history-focus').onclick=()=>{displayPrefs.searchHistoryFocus=!displayPrefs.searchHistoryFocus;saveDisplay();renderFocus()};
 }
 root.dataset.historyFocus=displayPrefs.searchHistoryFocus?'yes':'no';
 styleSearchStats(root.querySelector('.search-stats'));
 root.querySelector('.search-history-focus').setAttribute('aria-pressed',String(!!displayPrefs.searchHistoryFocus));
 const choice=$('#searchSide').value,side=choice==='auto'?(g.clock_active||g.info_side||'white'):choice;
 const search=g.searches?.[side],info=search?.info||{},active=g.clock_active===side&&state.connected!==false;
 const label=side==='white'?ArenaI18n.t('White'):ArenaI18n.t('Black');
 root.querySelector('.search-side').textContent=label+ArenaI18n.t(' engine')+(search?ArenaI18n.t(' · move ')+search.move_number+(side==='white'?'.':'…'):'');
 root.querySelector('.search-name').textContent=g[side].name;
 root.querySelector('.search-name').title=g[side].name;
 root.querySelector('.search-phase').textContent=state.connected===false?ArenaI18n.t('Updates unavailable'):active?ArenaI18n.t('Thinking'):search?.complete?ArenaI18n.t('Last completed search'):search?ArenaI18n.t('Search stopped'):ArenaI18n.t('Not searched yet');
 root.querySelector('.search-phase').classList.toggle('thinking',active);
 const cp=ArenaSearch.score(info);
 const exact=n=>Number.isFinite(n)?n.toLocaleString(ArenaI18n.locale):ArenaI18n.t('not reported');
 const wdl=Array.isArray(info.wdl)&&info.wdl.length===3?info.wdl:null,total=wdl?.reduce((a,b)=>a+b,0);
 stableHtml('#searchContent .search-stats',
  statTile(ArenaI18n.t('Evaluation'),cp,ArenaI18n.t('White perspective'),ArenaI18n.t('Positive scores favor White; negative scores favor Black. M indicates a reported mate distance, not a win probability. ≥ and ≤ identify engine-reported lower and upper bounds.'))+
  statTile(ArenaI18n.t('Search depth'),info.depth??'—',info.seldepth===undefined?'plies':ArenaI18n.t('Selective ')+info.seldepth,ArenaI18n.t('Main depth and selective depth, in plies, for this engine’s displayed search.'))+
  statTile(ArenaI18n.t('Nodes searched'),compactNumber(info.nodes),'positions',ArenaI18n.t('Exact node count: ')+exact(info.nodes)+'. Counts belong to this search; engine architectures may count differently.')+
  statTile(ArenaI18n.t('Search speed'),compactNumber(info.nps),ArenaI18n.t('nodes / second'),ArenaI18n.t('Exact reported NPS: ')+exact(info.nps)+'. This is reported by the engine, not estimated by the interface.')+
  statTile(ArenaI18n.t('Search time'),info.time===undefined?'—':(info.time/1000).toFixed(2)+ArenaI18n.t(' s'),ArenaI18n.t('engine reported'),ArenaI18n.t('Engine-reported search time. This is separate from the game clock and watchdogs.'))+
  statTile(ArenaI18n.t('Hash used'),info.hashfull===undefined?'—':(info.hashfull/10).toFixed(1)+'%',ArenaI18n.t('hash table'),ArenaI18n.t('Engine hash occupancy converted from per mille to percent.'))+
  statTile(ArenaI18n.t('Tablebase hits'),compactNumber(info.tbhits),ArenaI18n.t('successful probes'),ArenaI18n.t('Exact reported tablebase hits: ')+exact(info.tbhits)+'. Referee tablebases are configured separately.')+
 statTile(ArenaI18n.t('White W / D / L'),total?wdl.map(n=>(100*n/total).toFixed(0)).join(' / ')+'%':'—',ArenaI18n.t('engine estimate'),ArenaI18n.t('Engine-reported win, draw and loss estimates from White’s perspective, normalized to percentages. These are not tournament results.')));
 for(const value of root.querySelectorAll('.search-stats strong'))value.title=value.textContent;
 root.querySelector('.search-pv h3').textContent=search?.complete?ArenaI18n.t('Last reported principal variation'):ArenaI18n.t('Current principal variation');
 root.querySelector('.search-pv p').textContent=ArenaSearch.numbered(info.pv,search?.move_number,side)||(search?.complete?ArenaI18n.t('No principal variation reported for this search.'):ArenaI18n.t('Waiting for this engine’s analysis…'));
 paintSearchHistory(g,side,search);
 const note=root.querySelector('.search-referee');note.hidden=!g.tablebase_note;note.textContent=g.tablebase_note||'';
}

// Floating windows remain inside this application and share the same worker.
let focusWindowZ=100;
const focusWindowIds=['focus','search','live','games','moves'];
const panelSettings=id=>displayPrefs.panels[id]||{};
const floating=id=>!!(panelSettings(id).floating||panelSettings(id).maximized);
function panelMinimum(id){
 const historyChrome=id==='games'?panels.games.querySelector('.panel-title').getBoundingClientRect().height+panels.games.querySelector('.pager').getBoundingClientRect().height:0;
 return {width:Math.min(id==='games'?Math.max(520,28*displayPrefs.fontSize):Math.max(320,(id==='focus'?22:20)*displayPrefs.fontSize),innerWidth-16),height:Math.min(id==='focus'?Math.max(480,320+12*displayPrefs.fontSize):id==='games'?Math.max(340,Math.ceil(historyChrome)+120):id==='live'?300:240,innerHeight-16)};
}
function dockPanelHeight(id,height){return ['live','games'].includes(id)?Math.min(innerHeight-16,Math.max(panelMinimum(id).height,height)):Math.max(panelMinimum(id).height,height)}
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
  panel.querySelector('[data-float]').textContent=isFloating?ArenaI18n.t('Dock'):ArenaI18n.t('Float');
  panel.querySelector('[data-float]').dataset.help=isFloating?ArenaI18n.t('Return this window to its saved workspace column.'):ArenaI18n.t('Float this panel inside the app, with independent width and height. Drag its heading to move it.');
  panel.querySelector('[data-expand]').textContent=p.maximized?ArenaI18n.t('Restore'):ArenaI18n.t('Expand');
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
 heading.tabIndex=0;heading.dataset.help=ArenaI18n.t('Float this panel to move it by its heading. Use the corner grip to resize. With a floating heading focused, arrow keys move the window.');
 const float=document.createElement('button');float.className='subtle';float.dataset.float='';float.textContent=ArenaI18n.t('Float');heading.insertBefore(float,hide);
 const expand=document.createElement('button');expand.className='subtle';expand.dataset.expand='';expand.textContent=ArenaI18n.t('Expand');expand.dataset.help=ArenaI18n.t('Use the full application area for this panel. Restore returns to the previous size and position.');heading.insertBefore(expand,hide);
 float.onclick=()=>{displayPrefs.panels[id]={...panelSettings(id),floating:!floating(id),maximized:false};applyDisplay();saveDisplay()};
 expand.onclick=()=>{displayPrefs.panels[id]={...panelSettings(id),maximized:!panelSettings(id).maximized};applyDisplay();saveDisplay()};
 const grip=document.createElement('div');grip.className='focus-resizer';grip.tabIndex=0;grip.setAttribute('role','separator');grip.setAttribute('aria-label',ArenaI18n.t('Resize ')+panelNames[id]);grip.dataset.help=['live','games'].includes(id)?ArenaI18n.t('Drag to change height; floating windows also change width. Use arrow keys when focused, or Size in the header. Scroll inside the panel to see more ')+(id==='games'?'games.':'boards.'):ArenaI18n.t('Drag to change height; floating windows also change width. Use arrow keys when focused. The board and text scale automatically.');panel.append(grip);
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
for(const id of ['live','games']){
 const title=id==='live'?ArenaI18n.t('Live boards'):ArenaI18n.t('Game history'),prefix=id==='live'?'Live':'Games',content=id==='live'?ArenaI18n.t('Boards'):ArenaI18n.t('Games');
 const sizeButton=document.createElement('button');sizeButton.className='subtle';sizeButton.textContent=ArenaI18n.t('Size…');sizeButton.dataset.panelSize=id;sizeButton.dataset.help=ArenaI18n.t('Set the ')+title.toLowerCase()+ArenaI18n.t(' height here without reaching its bottom corner. Float the panel to choose its width too.');panels[id].querySelector('.panel-heading').insertBefore(sizeButton,panels[id].querySelector('[data-float]'));
 sizeButton.onclick=()=>{
  const p=panelSettings(id),r=panels[id].getBoundingClientRect(),min=panelMinimum(id),free=!!p.floating;
  const heightId=id+'PanelHeight',widthId=id+'PanelWidth';
  modal(title+ArenaI18n.t(' size'),ArenaI18n.h`<p>${content} scroll inside this panel. Its size is saved with your workspace.</p><div class="fields">${field(heightId,ArenaI18n.t('Panel height (px)'),Math.round(r.height),'number',`required min="${Math.ceil(min.height)}" max="${Math.floor(innerHeight-16)}" step="1"`)}${field(widthId,ArenaI18n.t('Panel width (px)'),Math.round(r.width),'number',free?`required min="${Math.ceil(min.width)}" max="${Math.floor(innerWidth-16)}" step="1"`:'disabled')}</div><p class="caption">${free?ArenaI18n.t('Width and height are independent in a floating window.'):ArenaI18n.t('Docked width follows the workspace column. Choose Float to resize width independently.')}</p>`,ArenaI18n.h`<button id="fit${prefix}Panel">Fit to window</button><button class="primary" id="apply${prefix}PanelSize">Apply size</button>`);
  $('#'+heightId).dataset.help=ArenaI18n.t('Set the panel height in pixels, limited to the available application height. Extra ')+content.toLowerCase()+ArenaI18n.t(' scroll inside it.');
  $('#'+widthId).dataset.help=free?ArenaI18n.t('Set the floating panel width in pixels.'):ArenaI18n.t('Docked width follows the workspace divider. Float this panel to set its width.');
  const apply=safely(async(height,width)=>{displayPrefs.panels[id]={...p,maximized:false,...(free?{bounds:fitPanelBounds(id,{left:r.left,top:r.top,width,height})}:{height:dockPanelHeight(id,height)})};applyDisplay();await persistDisplay();$('#modal').close()});
  $('#apply'+prefix+'PanelSize').onclick=()=>{if(!$('#'+heightId).reportValidity()||(free&&!$('#'+widthId).reportValidity()))return;apply(Number($('#'+heightId).value),Number($('#'+widthId).value))};
  $('#fit'+prefix+'Panel').dataset.help=ArenaI18n.t('Restore a manageable height that fits the app; floating windows also return to a standard width.');
  $('#fit'+prefix+'Panel').onclick=()=>apply(Math.min(id==='live'?680:640,innerHeight*.8),Math.min(id==='live'?800:960,innerWidth-16));
 };
}
function applyLiveCardSize(){
 const p=panelSettings('live'),width=Number(p.cardWidth);
 const valid=Number.isFinite(width)&&width>=160&&width<=1200;
 // Preserve existing custom widths; new workspaces start with two equal columns.
 const saved=Number(p.cardColumns),columns=Number.isInteger(saved)&&saved>=0&&saved<=8?saved:valid?0:2;
 const list=$('#liveBoards');list.style.setProperty('--live-card-width',(valid?Math.round(width):280)+'px');list.dataset.cardFill=p.cardFill===true?'yes':'no';
 list.dataset.cardLayout=columns?'columns':'width';list.style.setProperty('--live-card-columns',String(columns||2));
 $('#liveBoardsAcross').value=String(columns);
}
const liveColumnsLabel=document.createElement('label');liveColumnsLabel.className='live-columns-control';liveColumnsLabel.htmlFor='liveBoardsAcross';
liveColumnsLabel.innerHTML=ArenaI18n.h`<span>Boards across</span><select id="liveBoardsAcross" data-help="Choose 1–8 boards across the full panel width. Fewer columns make larger boards. Boards resize with the dock or floating window; scroll down for the remaining games. Custom uses your pixel width instead.">${Array.from({length:8},(_,i)=>ArenaI18n.h`<option value="${i+1}">${i+1} across</option>`).join('')}<option value="0">Custom width</option></select>`;
const liveCardSizeButton=document.createElement('button');liveCardSizeButton.className='subtle';liveCardSizeButton.textContent=ArenaI18n.t('Custom width…');liveCardSizeButton.dataset.help=ArenaI18n.t('Set a custom card width in pixels instead of a fixed number across. For boards that fill the dock width, use Boards across.');
$('#boardCount').before(liveColumnsLabel,liveCardSizeButton);
$('#liveBoardsAcross').onchange=safely(async()=>{
 displayPrefs.panels.live={...panelSettings('live'),cardColumns:Number($('#liveBoardsAcross').value)};
 applyLiveCardSize();$('#liveBoards').scrollTop=0;await persistDisplay();
});
liveCardSizeButton.onclick=()=>{
 const p=panelSettings('live'),value=Number(p.cardWidth),width=Number.isFinite(value)&&value>=160&&value<=1200?Math.round(value):280;
 modal(ArenaI18n.t('Custom live card width'),ArenaI18n.h`<p>Applying a custom width switches <b>Boards across</b> to <b>Custom width</b>. To fit 1, 2, 3 or more equal boards across the panel, use the Boards across selector in the Live boards header.</p><div class="card-size-presets" role="group" aria-label="Card size presets">${[[180,ArenaI18n.t('Compact')],[280,ArenaI18n.t('Standard')],[400,ArenaI18n.t('Large')],[560,ArenaI18n.t('Extra large')]].map(([size,label])=>ArenaI18n.h`<button data-card-preset="${size}" data-help="Set card width to ${size} pixels.">${label} · ${size} px</button>`).join('')}</div><div class="fields">${field('liveCardWidth',ArenaI18n.t('Card width (px)'),width,'number','required min="160" max="1200" step="1" aria-describedby="liveCardWidthHelp"')}<div class="field"><label for="liveCardFill">Row layout</label><select id="liveCardFill"><option value="no" ${p.cardFill!==true?'selected':''}>Keep selected width</option><option value="yes" ${p.cardFill===true?'selected':''}>Fill each row</option></select></div><div class="field full"><label for="liveCardSlider">Adjust card width</label><input id="liveCardSlider" type="range" min="160" max="1200" step="1" value="${width}" aria-label="Adjust card width"></div></div><p class="caption" id="liveCardWidthHelp">160–1200 px for the whole card. The board stays square; height follows the board, clocks and text. A card shrinks to fit if the panel is narrower than your selected width.</p><p class="caption">Keep selected width leaves unused space at the end of a row. Fill each row treats your width as a minimum and shares spare space between columns. Extra rows scroll inside Live boards. Use Size… in the panel header to resize the window itself.</p>`,ArenaI18n.h`<button class="primary" id="applyLiveCardSize">Apply custom width</button>`);
 const input=$('#liveCardWidth'),slider=$('#liveCardSlider');
 const sync=()=>{const size=Number(input.value);if(input.validity.valid)slider.value=String(size);$$('[data-card-preset]').forEach(button=>button.setAttribute('aria-pressed',String(Number(button.dataset.cardPreset)===size)))};
 input.dataset.help=ArenaI18n.t('Exact card width in pixels. This changes the board and card width, not tournament concurrency or displayed game count.');
 slider.dataset.help=ArenaI18n.t('Drag or use arrow keys for fine adjustment. Apply custom width saves the chosen width.');
 $('#liveCardFill').dataset.help=ArenaI18n.t('Keep selected width for a fixed card size, or fill available columns using that width as the minimum. Empty columns are reserved when fewer games are visible.');
 input.oninput=sync;slider.oninput=()=>{input.value=slider.value;sync()};
 $$('[data-card-preset]').forEach(button=>button.onclick=()=>{input.value=button.dataset.cardPreset;sync()});sync();
 $('#applyLiveCardSize').onclick=safely(async()=>{
  if(!input.reportValidity())return;
  displayPrefs.panels.live={...panelSettings('live'),cardColumns:0,cardWidth:Number(input.value),cardFill:$('#liveCardFill').value==='yes'};
  applyLiveCardSize();await persistDisplay();$('#modal').close();notify(ArenaI18n.t('Live game card size saved.'));
 });
};
const historyScroll=panels.games.querySelector('.table-scroll');
historyScroll.tabIndex=0;historyScroll.setAttribute('role','region');historyScroll.setAttribute('aria-label',ArenaI18n.t('Game and attempt history'));historyScroll.dataset.help=ArenaI18n.t('Scroll through this page of games. Filters and page controls stay visible. Use Page Up, Page Down, Home or End when this list is focused.');
for(const id of ['gamesFirst','gamesPrev','gamesNext','gamesLast'])$('#'+id).addEventListener('click',()=>{historyScroll.scrollTop=0});
$('#gameFilter').addEventListener('change',()=>{historyScroll.scrollTop=0});
const historyChromeObserver=new ResizeObserver(()=>{
 const panel=panels.games;if(!panel.getClientRects().length)return;
 const min=panelMinimum('games');panel.style.setProperty('--history-min-height',min.height+'px');
 if(floating('games')&&!panelSettings('games').maximized){const r=panel.getBoundingClientRect();setPanelBounds(panel,fitPanelBounds('games',{left:r.left,top:r.top,width:r.width,height:r.height}))}
});
historyChromeObserver.observe(panels.games.querySelector('.panel-title'));historyChromeObserver.observe(panels.games.querySelector('.pager'));
const applyDisplayBeforeFocus=applyDisplay;
applyDisplay=function(){applyDisplayBeforeFocus();applyFocusWindows();applyLiveCardSize();renderFocus()};

function searchStatSettings(){
 const p=displayPrefs.searchStats||{};
 return {scale:Number.isFinite(p.scale)&&p.scale>=75&&p.scale<=250?p.scale:100,columns:Number.isInteger(p.columns)&&p.columns>=0&&p.columns<=8?p.columns:4};
}
function styleSearchStats(element,p=searchStatSettings()){
 const key=p.scale+'/'+p.columns;if(element.dataset.statSize===key)return;element.dataset.statSize=key;
 element.style.setProperty('--search-stat-scale',p.scale/100);
 element.style.setProperty('--search-stat-columns',p.columns||4);
 element.dataset.statLayout=p.columns?'fixed':'auto';
}
const searchStatSizeButton=document.createElement('button');searchStatSizeButton.className='subtle';searchStatSizeButton.textContent=ArenaI18n.t('Stat size…');
searchStatSizeButton.dataset.help=ArenaI18n.t('Resize the evaluation, depth, nodes and other overview boxes independently of best-move history. Preview text size and choose how many boxes fit across the panel.');
panels.search.querySelector('.panel-heading').insertBefore(searchStatSizeButton,panels.search.querySelector('[data-float]'));
searchStatSizeButton.onclick=()=>{
 const p=searchStatSettings(),live=$('#searchContent .search-stats'),width=$('#searchContent').clientWidth,font=parseFloat(getComputedStyle($('#searchContent')).fontSize);
 const preview=live?.innerHTML||statTile(ArenaI18n.t('Evaluation'),'+0.42',ArenaI18n.t('White perspective'))+statTile(ArenaI18n.t('Search depth'),'28','plies')+statTile(ArenaI18n.t('Nodes searched'),'12.34M','positions')+statTile(ArenaI18n.t('Search speed'),'1.56M',ArenaI18n.t('nodes / second'));
 modal(ArenaI18n.t('Search statistic size'),ArenaI18n.h`<p>Enlarge the evaluation and other overview values. Best-move history keeps its own compact text size.</p><div class="fields"><div class="field"><label for="searchStatPercent">Statistic text size (%)</label><input id="searchStatPercent" type="number" min="75" max="250" step="5" required value="${p.scale}" data-help="75–250% of the current search-panel text size. Labels, values and box heights scale together. This does not change history rows or board text."></div><div class="field"><label for="searchStatColumns">Boxes across</label><select id="searchStatColumns" data-help="Auto-fit gives larger text wider boxes as the window changes size. Choose a fixed count to control the arrangement. If values are shortened, use fewer boxes across or Auto-fit."><option value="0" ${p.columns===0?'selected':''}>Auto-fit to text and window</option>${Array.from({length:8},(_,i)=>ArenaI18n.h`<option value="${i+1}" ${p.columns===i+1?'selected':''}>${i+1} across</option>`).join('')}</select></div><div class="field full"><label for="searchStatSlider">Adjust statistic text size</label><input id="searchStatSlider" type="range" min="75" max="250" step="5" value="${p.scale}" data-help="Drag or use arrow keys to preview statistic sizing. Apply size saves the setting."></div></div><div class="search-stat-presets">${[100,150,200,250].map(size=>ArenaI18n.h`<button type="button" data-search-stat-preset="${size}" data-help="Preview ${size}% statistic text with automatic box widths.">${size}%</button>`).join('')}<button type="button" id="resetSearchStatSize" data-help="Restore 100% text and four boxes across, matching the compact overview.">Reset</button></div><p class="caption">${live?ArenaI18n.t('Preview of the current values'):ArenaI18n.t('Example preview')} · preview width follows the search window where space permits. Large boxes may need a taller window; values keep their size during live updates.</p><div class="search-stat-preview"><div class="search-stats"></div></div>`,ArenaI18n.h`<button class="primary" id="applySearchStatSize">${displayPrefs.searchHistoryFocus?ArenaI18n.t('Apply & show statistics'):ArenaI18n.t('Apply size')}</button>`);
 const sample=$('#modal .search-stat-preview'),grid=sample.querySelector('.search-stats');grid.innerHTML=preview;sample.style.width=Math.max(240,width)+'px';sample.style.fontSize=font+'px';
 const percent=$('#searchStatPercent'),slider=$('#searchStatSlider'),columns=$('#searchStatColumns');
 const paint=()=>{if(!percent.validity.valid)return;const draft={scale:Number(percent.value),columns:Number(columns.value)};slider.value=percent.value;styleSearchStats(grid,draft);$$('[data-search-stat-preset]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.searchStatPreset)===draft.scale)))};
 percent.oninput=paint;slider.oninput=()=>{percent.value=slider.value;paint()};columns.onchange=paint;
 $$('[data-search-stat-preset]').forEach(b=>b.onclick=()=>{percent.value=b.dataset.searchStatPreset;columns.value='0';paint()});
 $('#resetSearchStatSize').onclick=()=>{percent.value='100';columns.value='4';paint()};
 $('#applySearchStatSize').onclick=safely(async()=>{if(!percent.reportValidity())return;displayPrefs.searchStats={scale:Number(percent.value),columns:Number(columns.value)};displayPrefs.searchHistoryFocus=false;renderFocus();await persistDisplay();$('#modal').close()});
 paint();
};
const focusSizeObserver=new ResizeObserver(entries=>{for(const entry of entries){const {width,height}=entry.contentRect,id=entry.target.dataset.panel;const scale=Math.max(1,Math.min(id==='search'?1.15:1.6,width/(id==='focus'?620:600),height/(id==='focus'?720:580)));entry.target.style.setProperty('--focus-text-scale',scale.toFixed(3))}});
for(const id of focusWindowIds)focusSizeObserver.observe(panels[id]);
window.addEventListener('resize',()=>{for(const id of focusWindowIds)if(floating(id)){const p=panelSettings(id);setPanelBounds(panels[id],p.maximized?{left:8,top:8,width:innerWidth-16,height:innerHeight-16}:fitPanelBounds(id,p.bounds))}});
setInterval(()=>{if(state.connected===false)renderFocus()},1000);
applyDisplay();
