'use strict';
const ArenaFocusLayout=(()=>{
 const defaults={placement:'above',arrangement:'row',order:'white',height:86,digits:28,width:180,boardMax:0,names:true,details:true};
 function normalize(raw={}){
  if(!raw||typeof raw!=='object')raw={};const p={...defaults};
  for(const [key,values] of Object.entries({placement:['above','below','left','right','split'],arrangement:['row','stack'],order:['white','black','board']}))if(values.includes(raw[key]))p[key]=raw[key];
  for(const [key,min,max] of [['height',60,220],['digits',16,80],['width',140,400],['boardMax',0,1600]])if(Number.isFinite(raw[key]))p[key]=Math.round(Math.max(min,Math.min(max,raw[key])));
  for(const key of ['names','details'])if(typeof raw[key]==='boolean')p[key]=raw[key];
  return p;
 }
 return {defaults,normalize};
})();
if(typeof module!=='undefined')module.exports=ArenaFocusLayout;
if(typeof document!=='undefined'){
 const controlsToggle=document.createElement('button');controlsToggle.id='focusControlsToggle';controlsToggle.type='button';controlsToggle.className='subtle';
 controlsToggle.setAttribute('aria-controls','focusSetupTools focusWatchControls');
 controlsToggle.dataset.help=ArenaI18n.t('Hide setup controls to give the board more room. Clocks, game status and your watching settings stay active. Show controls brings them back.');
 panels.focus.querySelector('.panel-tools').id='focusSetupTools';
 panels.focus.querySelector('.panel-heading h2').after(controlsToggle);
 function syncFocusControls(){
  const hidden=displayPrefs.panels.focus?.controlsHidden===true;
  panels.focus.classList.toggle('focus-controls-hidden',hidden);
  controlsToggle.textContent=ArenaI18n.t(hidden?'Show controls':'Hide controls');
  controlsToggle.setAttribute('aria-expanded',String(!hidden));
 }
 controlsToggle.onclick=safely(async()=>{
  displayPrefs.panels.focus={...panelSettings('focus'),controlsHidden:!displayPrefs.panels.focus?.controlsHidden};
  // Only change presentation: keep the current game, renderer and follow state.
  syncFocusControls();await persistDisplay();
 });
 const displayBeforeFocusControls=applyDisplay;
 applyDisplay=function(){syncFocusControls();displayBeforeFocusControls()};
 syncFocusControls();
 function focusLayoutOptions(){return ArenaFocusLayout.normalize(displayPrefs.panels.focus?.clocks)}
 function styleFocusLayout(root,value=focusLayoutOptions()){
  const p=ArenaFocusLayout.normalize(value),stage=root.querySelector('.focus-stage');if(!stage)return;
  stage.dataset.placement=p.placement;stage.dataset.arrangement=p.arrangement;
  stage.dataset.first=p.order==='board'?(state.flip?'white':'black'):p.order;
  stage.dataset.names=String(p.names);stage.dataset.details=String(p.details);
  for(const [key,v] of Object.entries({'clock-height':p.height,'clock-digits':p.digits,'clock-width':p.width,'board-max':p.boardMax||100000}))stage.style.setProperty('--focus-'+key,v+'px');
 }
 window.styleFocusLayout=styleFocusLayout;
 const button=document.createElement('button');button.id='focusLayoutButton';button.className='subtle';button.textContent=ArenaI18n.t('Board & clocks');
 button.dataset.help=ArenaI18n.t('Arrange the focused board and clocks, adjust their sizes, and save this layout.');
 panels.focus.querySelector('.panel-heading').append(button);
 button.onclick=()=>{
  const p=focusLayoutOptions();
  modal(ArenaI18n.t('Focused game · board and clocks'),ArenaI18n.h`<div class="focus-layout-settings"><div class="fields">
   <label>Clock placement<select id="focusClockPlacement" data-help="Place both clocks above, below or beside the board, or put one clock above and one below it."><option value="above">Above board</option><option value="below">Below board</option><option value="left">Left of board</option><option value="right">Right of board</option><option value="split">One above, one below</option></select></label>
   <label>Clock arrangement<select id="focusClockArrangement" data-help="Above and below layouts can show the clocks side by side or stacked. Side layouts always stack the clocks."><option value="row">Side by side</option><option value="stack">Stacked vertically</option></select></label>
   <label>Clock order<select id="focusClockOrder" data-help="Choose which clock comes first (left or top). Follow board orientation puts the far-side player first and changes when you flip the board."><option value="white">White first</option><option value="black">Black first</option><option value="board">Follow board orientation</option></select></label>
   ${field('focusClockHeight',ArenaI18n.t('Minimum clock box height (px)'),p.height,'number','min="60" max="220" step="1" required')}
   ${field('focusClockDigits',ArenaI18n.t('Clock number size (px)'),p.digits,'number','min="16" max="80" step="1" required')}
   ${field('focusClockWidth',ArenaI18n.t('Side clock width (px)'),p.width,'number','min="140" max="400" step="1" required')}
   ${field('focusBoardMax',ArenaI18n.t('Maximum board size (px; 0 = fit window)'),p.boardMax,'number','min="0" max="1600" step="1" required')}
   <label><input id="focusDrawRule" type="checkbox"> Show draw-rule counter</label><label><input id="focusClockNames" type="checkbox"> Show engine names</label><label><input id="focusClockDetails" type="checkbox"> Show clock details</label>
  </div><p class="caption">Clocks stay labeled White and Black. Numbers shrink to fit narrow boxes. Small windows scroll internally when needed; side clocks move above the board on narrow panels.</p><div class="focus-layout-presets"><button data-focus-preset="compact">Compact</button><button data-focus-preset="large">Large clocks</button><button data-focus-preset="split">Board between clocks</button><button data-focus-preset="default">Reset layout</button></div><div id="focusLayoutPreview" class="focus-layout-preview"></div></div>`,ArenaI18n.h`<button class="primary" id="saveFocusLayout">Save board and clocks</button>`);
  $('#focusDrawRule').checked=displayPrefs.showDrawRule!==false;
  const fields={placement:'focusClockPlacement',arrangement:'focusClockArrangement',order:'focusClockOrder',height:'focusClockHeight',digits:'focusClockDigits',width:'focusClockWidth',boardMax:'focusBoardMax',names:'focusClockNames',details:'focusClockDetails'};
  const read=()=>Object.fromEntries(Object.entries(fields).map(([key,id])=>[key,typeof p[key]==='boolean'?$('#'+id).checked:typeof p[key]==='number'?Number($('#'+id).value):$('#'+id).value]));
  const preview=$('#focusLayoutPreview'),source=$('#focusContent .focus-stage');
  if(source)preview.append(source.cloneNode(true));else{
   preview.innerHTML='<div class="focus-stage"><div class="focus-clocks">'+clockFace({game:'layout-preview'},'white')+clockFace({game:'layout-preview'},'black')+'</div><div class="focus-board">'+boardHtml('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1','')+'</div></div>';
   preview.querySelectorAll('.clock-time').forEach(e=>e.textContent='03:00.0');
  }
  const paint=()=>{if(!Object.values(fields).every(id=>$('#'+id).validity.valid))return;styleFocusLayout(preview,read());$('#focusClockArrangement').disabled=!['above','below'].includes($('#focusClockPlacement').value);$('#focusClockWidth').disabled=!['left','right'].includes($('#focusClockPlacement').value)};
  const apply=value=>{for(const [key,id] of Object.entries(fields))if(typeof p[key]==='boolean')$('#'+id).checked=value[key];else $('#'+id).value=value[key];paint()};
  for(const [key,id] of Object.entries(fields))$('#'+id).addEventListener('input',paint);
  for(const id of ['focusClockHeight','focusClockDigits','focusClockWidth','focusBoardMax'])$('#'+id).dataset.help=ArenaI18n.t('Adjust this display size. The board still fits the available panel space.');
  $$('[data-focus-preset]').forEach(b=>b.onclick=()=>apply({...ArenaFocusLayout.defaults,...({compact:{height:60,digits:22,details:false},large:{height:130,digits:52},split:{placement:'split',order:'board'}}[b.dataset.focusPreset]||{})}));
  $('#saveFocusLayout').onclick=safely(async()=>{if(!Object.values(fields).every(id=>$('#'+id).reportValidity()))return;displayPrefs.showDrawRule=$('#focusDrawRule').checked;displayPrefs.panels.focus={...panelSettings('focus'),clocks:read()};renderFocus();await persistDisplay();$('#modal').close()});
  apply(p);
 };
 styleFocusLayout($('#focusContent'));
}
