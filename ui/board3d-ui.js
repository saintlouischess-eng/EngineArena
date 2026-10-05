'use strict';
let board3dInstance=null,board3dCanvas=null,board3dSignature='',board3dPending=0,board3dFailed=false,board3dObserver=null,board3dHost=null;
let board3dAssetLoading=false;
function releaseBoard3d(){cancelAnimationFrame(board3dPending);board3dPending=0;board3dObserver?.disconnect();board3dObserver=null;board3dInstance?.dispose();board3dInstance=null;board3dCanvas?.remove();board3dCanvas=null;board3dHost?.querySelector('.board-3d-labels')?.remove();board3dHost?.querySelector('.board-3d-controls')?.remove();board3dHost?.classList.remove('is-3d');board3dHost=null;board3dSignature=''}
function setBoard3dZoom(value){
 const current=ArenaBoard3D.settings(displayPrefs.camera3d),next=ArenaBoard3D.settings({...current,zoom:Math.round(value*1000)/1000});
 if(next.zoom===current.zoom)return;
 displayPrefs.camera3d=next;board3dSignature='';renderFocus();saveDisplay();
}
function setBoard3dLift(value){
 const current=ArenaBoard3D.settings(displayPrefs.camera3d),next=ArenaBoard3D.settings({...current,lift:Math.round(value*1000)/1000});
 if(next.lift===current.lift)return;
 displayPrefs.camera3d=next;board3dSignature='';renderFocus();saveDisplay();
}
function syncBoard3dControlToggle(){
 boardControlsButton.hidden=displayPrefs.focus3d!==true||board3dFailed||!board3dCanvas?.isConnected;
 const visible=displayPrefs.board3dControls!==false;
 boardControlsButton.textContent=visible?ArenaI18n.t('Hide 3D controls'):ArenaI18n.t('Show 3D controls');
 boardControlsButton.setAttribute('aria-expanded',String(visible));
}
function setBoard3dControls(visible){displayPrefs.board3dControls=visible;renderFocus();saveDisplay()}
function syncBoard3dZoom(){
 const controls=board3dHost?.querySelector('.board-3d-controls');if(!controls)return;
 controls.hidden=displayPrefs.board3dControls===false;
 const p=ArenaBoard3D.settings(displayPrefs.camera3d),range=ArenaBoard3D.zoomRange,percent=Math.round(p.zoom*100);
 const slider=controls.querySelector('input');slider.value=percent;slider.setAttribute('aria-valuetext',percent+'%');
 controls.querySelector('[data-zoom=out]').disabled=p.zoom<=range.min;
 controls.querySelector('[data-zoom=in]').disabled=p.zoom>=range.max;
 controls.querySelector('[data-zoom=reset]').textContent=percent+'%';
 const lift=controls.querySelector('#board3dLift');lift.value=Math.round(p.lift*100);lift.setAttribute('aria-valuetext',lift.value+'%');
 controls.querySelector('[data-lift=down]').disabled=p.lift<=ArenaBoard3D.liftRange.min;
 controls.querySelector('[data-lift=up]').disabled=p.lift>=ArenaBoard3D.liftRange.max;
}
function addBoard3dZoom(host){
 const controls=document.createElement('div'),range=ArenaBoard3D.zoomRange;controls.id='board3dControls';controls.className='board-3d-controls';controls.setAttribute('role','group');controls.setAttribute('aria-label',ArenaI18n.t('3D board controls'));
 controls.innerHTML=ArenaI18n.h`<label for="board3dZoom">Zoom</label><button type="button" data-zoom="out" aria-label="Zoom out" data-help="Zoom out">−</button><input id="board3dZoom" type="range" min="${range.min*100}" max="${range.max*100}" step="1" aria-label="3D board zoom" data-help="Adjust the 3D board zoom from 60% to 240%. Your view is saved."><button type="button" data-zoom="in" aria-label="Zoom in" data-help="Zoom in">+</button><button type="button" data-zoom="reset" aria-label="Reset zoom to 100%" data-help="Reset zoom to 100%">100%</button>`;
 controls.querySelector('input').oninput=e=>setBoard3dZoom(Number(e.target.value)/100);
 controls.querySelector('[data-zoom=out]').onclick=()=>setBoard3dZoom(ArenaBoard3D.settings(displayPrefs.camera3d).zoom-range.step);
 controls.querySelector('[data-zoom=in]').onclick=()=>setBoard3dZoom(ArenaBoard3D.settings(displayPrefs.camera3d).zoom+range.step);
 controls.querySelector('[data-zoom=reset]').onclick=()=>setBoard3dZoom(1);
 controls.insertAdjacentHTML('beforeend',ArenaI18n.h`<label for="board3dLift">Height</label><button type="button" data-lift="down" aria-label="Lower board" data-help="Lower board">↓</button><input id="board3dLift" type="range" min="-50" max="50" step="1" aria-label="Vertical board position (%)" data-help="Raise or lower the board without changing its angle or zoom. Shift-drag or Shift+Up/Down also adjusts height."><button type="button" data-lift="up" aria-label="Raise board" data-help="Raise board">↑</button><button type="button" data-lift="reset" aria-label="Center board vertically" data-help="Center board vertically">↕</button>`);
 controls.querySelector('#board3dLift').oninput=e=>setBoard3dLift(Number(e.target.value)/100);
 controls.querySelector('[data-lift=down]').onclick=()=>setBoard3dLift(ArenaBoard3D.settings(displayPrefs.camera3d).lift-ArenaBoard3D.liftRange.step);
 controls.querySelector('[data-lift=up]').onclick=()=>setBoard3dLift(ArenaBoard3D.settings(displayPrefs.camera3d).lift+ArenaBoard3D.liftRange.step);
 controls.querySelector('[data-lift=reset]').onclick=()=>setBoard3dLift(0);
 host.append(controls);syncBoard3dZoom();
}
function paintFocusBoard(host,fen,last,crownSquares=[]){
 if(displayPrefs.focus3d!==true||board3dFailed){if(board3dInstance)releaseBoard3d();updateBoard(host,fen,last);return}
 updateBoard(host,fen,last);
 // Load the studio renderer and original models only when 3D is requested.
 if(!ArenaBoard3D.isReady()){
  if(!board3dAssetLoading){board3dAssetLoading=true;ArenaBoard3D.prepare().then(()=>{board3dAssetLoading=false;renderFocus()}).catch(e=>{console.warn('3D assets could not load:',e);board3dAssetLoading=false;board3dFailed=true;notify(ArenaI18n.t('3D is unavailable on this device. The 2D board remains available.'),true);renderFocus()})}
  return;
 }
 if(board3dCanvas&&!board3dCanvas.isConnected)releaseBoard3d();
 host.classList.add('is-3d');
 if(!board3dCanvas){
  const canvas=document.createElement('canvas');canvas.className='board-3d';canvas.tabIndex=0;canvas.setAttribute('role','img');canvas.setAttribute('aria-label',ArenaI18n.t('3D chessboard. Drag or use arrow keys to orbit. Scroll or press plus/minus to zoom. Home resets the camera.'));canvas.dataset.help=ArenaI18n.t('Drag to turn the board. Scroll to zoom, or use the zoom controls. Home resets the camera.');host.append(canvas);board3dCanvas=canvas;board3dHost=host;
  const fail=()=>{board3dFailed=true;releaseBoard3d();notify(ArenaI18n.t('3D is unavailable on this device. The 2D board remains available.'),true);renderFocus()};
  try{board3dInstance=ArenaBoard3D.create(canvas,fail)}catch(e){console.warn('Focused 3D board could not initialize:',e);fail();return}
  let drag=null;canvas.onpointerdown=e=>{if(e.button!==0)return;drag={x:e.clientX,y:e.clientY,lift:e.shiftKey,p:ArenaBoard3D.settings(displayPrefs.camera3d)};canvas.setPointerCapture(e.pointerId)};
  canvas.onpointermove=e=>{if(!drag)return;displayPrefs.camera3d=ArenaBoard3D.settings(drag.lift?{...drag.p,lift:drag.p.lift-(e.clientY-drag.y)/canvas.clientHeight}:{...drag.p,orbit:drag.p.orbit+(e.clientX-drag.x)*.4,angle:drag.p.angle+(e.clientY-drag.y)*.25});board3dSignature='';renderFocus()};
  canvas.onpointerup=canvas.onpointercancel=()=>{if(drag){drag=null;saveDisplay()}};
  canvas.addEventListener('wheel',e=>{if(e.ctrlKey||e.metaKey||!e.deltaY)return;e.preventDefault();const pixels=e.deltaY*(e.deltaMode===1?16:e.deltaMode===2?canvas.clientHeight:1),delta=Math.max(-120,Math.min(120,pixels));setBoard3dZoom(ArenaBoard3D.settings(displayPrefs.camera3d).zoom*Math.exp(-delta*.0015))},{passive:false});
  canvas.onkeydown=e=>{
   if(e.ctrlKey||e.metaKey||e.altKey)return;
   if(e.shiftKey&&['ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();setBoard3dLift(ArenaBoard3D.settings(displayPrefs.camera3d).lift+(e.key==='ArrowUp'?1:-1)*ArenaBoard3D.liftRange.step);return}
   if(['+','=','-','_'].includes(e.key)){e.preventDefault();setBoard3dZoom(ArenaBoard3D.settings(displayPrefs.camera3d).zoom+(['+','='].includes(e.key)?1:-1)*ArenaBoard3D.zoomRange.step);return}
   if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home'].includes(e.key))return;e.preventDefault();const p=ArenaBoard3D.settings(displayPrefs.camera3d);displayPrefs.camera3d=e.key==='Home'?{}:{...p,orbit:p.orbit+(e.key==='ArrowRight'?5:e.key==='ArrowLeft'?-5:0),angle:p.angle+(e.key==='ArrowUp'?3:e.key==='ArrowDown'?-3:0)};board3dSignature='';renderFocus();saveDisplay();
  };
  addBoard3dZoom(host);
  board3dObserver=new ResizeObserver(()=>{board3dSignature='';renderFocus()});board3dObserver.observe(host);
 }
 syncBoard3dZoom();
 const signature=JSON.stringify([fen,last,crownSquares,!!state.flip,displayPrefs.camera3d,displayPrefs.crownMarks3d,displayPrefs.theme,host.clientWidth,host.clientHeight]);
 if(signature!==board3dSignature&&!document.hidden&&state.view==='overview'&&!panels.focus.hidden){board3dSignature=signature;cancelAnimationFrame(board3dPending);board3dPending=requestAnimationFrame(()=>{board3dPending=0;board3dInstance?.render(fen,state.flip,displayPrefs.camera3d,displayPrefs.theme==='light',last,displayPrefs.crownMarks3d===false?[]:crownSquares)})}
}
function boardViewDialog(){const p=ArenaBoard3D.settings(displayPrefs.camera3d),range=ArenaBoard3D.zoomRange;
 modal(ArenaI18n.t('Focused board view'),ArenaI18n.h`<div class="fields"><label>Board style<select id="focusBoardStyle"><option value="2d" ${!displayPrefs.focus3d?'selected':''}>2D · selected SVG pieces</option><option value="3d" ${displayPrefs.focus3d?'selected':''}>3D · 1849 Staunton</option></select></label>${field('cameraAngle',ArenaI18n.t('Viewing angle (degrees)'),p.angle,'number','required min="25" max="78"')}${field('cameraOrbit',ArenaI18n.t('Rotation (degrees)'),p.orbit,'number','required min="-180" max="180"')}${field('cameraZoom',ArenaI18n.t('Zoom (%)'),Math.round(p.zoom*100),'number',`required min="${range.min*100}" max="${range.max*100}" step="1"`)}${field('cameraLift',ArenaI18n.t('Vertical board position (%)'),Math.round(p.lift*100),'number','required min="-50" max="50" step="1"')}<label><input id="showBoard3dControls" type="checkbox" ${displayPrefs.board3dControls!==false?'checked':''}> Show 3D controls</label><label><input id="crownMarks3d" type="checkbox" ${displayPrefs.crownMarks3d!==false?'checked':''}> Kingside crown marks</label></div><p class="caption">Raise or lower the board without changing its angle or zoom. Shift-drag or Shift+Up/Down also adjusts height.</p><p class="caption">Red crowns follow the original kingside rook and knight. Positions without verified starting history have no marks.</p><p class="caption">Drag or use arrow keys to turn the 3D board. Scroll, use the zoom controls, or press plus/minus to zoom. Click the percentage to restore 100%; Home resets the camera. Your view is saved. Live game cards stay in 2D.</p>`,ArenaI18n.h('<button id="resetCamera">Reset camera</button><button id="applyBoardView" class="primary">Apply board view</button>'));
 $('#resetCamera').onclick=()=>{$('#cameraAngle').value=50;$('#cameraOrbit').value=0;$('#cameraZoom').value=100;$('#cameraLift').value=0};
 $('#applyBoardView').onclick=()=>{for(const el of $$('#modal input[type=number]'))if(!el.reportValidity())return;displayPrefs.focus3d=$('#focusBoardStyle').value==='3d';displayPrefs.camera3d={angle:Number($('#cameraAngle').value),orbit:Number($('#cameraOrbit').value),zoom:Number($('#cameraZoom').value)/100,lift:Number($('#cameraLift').value)/100};displayPrefs.crownMarks3d=$('#crownMarks3d').checked;displayPrefs.board3dControls=$('#showBoard3dControls').checked;board3dFailed=false;releaseBoard3d();saveDisplay();$('#modal').close();renderFocus()};
}
const boardViewButton=document.createElement('button');boardViewButton.className='subtle';boardViewButton.textContent=ArenaI18n.t('2D / 3D');boardViewButton.dataset.help=ArenaI18n.t('Choose the focused board style and camera. The default 2D view uses your selected SVG piece set.');boardViewButton.onclick=boardViewDialog;panels.focus.querySelector('.panel-heading').append(boardViewButton);
const boardControlsButton=document.createElement('button');boardControlsButton.id='toggleBoard3dControls';boardControlsButton.type='button';boardControlsButton.className='subtle';boardControlsButton.hidden=true;boardControlsButton.setAttribute('aria-controls','board3dControls');boardControlsButton.dataset.help=ArenaI18n.t('Show or hide the zoom and height controls. Your camera position stays the same.');boardControlsButton.onclick=()=>setBoard3dControls(displayPrefs.board3dControls===false);boardViewButton.after(boardControlsButton);
document.addEventListener('visibilitychange',()=>{board3dSignature='';if(!document.hidden)renderFocus()});
window.addEventListener('pagehide',releaseBoard3d);
