'use strict';
let board3dInstance=null,board3dCanvas=null,board3dSignature='',board3dPending=0,board3dObserver=null,board3dHost=null;
let board3dAssetLoading=false;
const board3dRecovery=new Arena3DRecovery({workspace:'focus',
 active:()=>displayPrefs.focus3d===true&&!document.hidden&&state.view==='overview'&&!panels.focus.hidden&&!!$('#focusContent .focus-board')&&board3dOnscreen,
 rebuild:()=>{releaseBoard3d();renderFocus()},
 changed:()=>board3dRecovery.show($('#focusContent'))
});
function failBoard3d(reason='unavailable'){if(reason==='context'&&board3dCanvas?.dataset.environment==='live-club')reason='live-context';Arena3DRecovery.record('focus',reason,board3dCanvas);releaseBoard3d();board3dRecovery.fail(reason);renderFocus()}
function releaseBoard3d(){const roomNote=panels.focus.querySelector('.room-motion-status');if(roomNote)roomNote.hidden=true;if(typeof stopSceneFrames==='function'){stopSceneFrames();board3dArgs=null;board3dIntersection?.disconnect();board3dIntersection=null;}cancelAnimationFrame(board3dPending);board3dPending=0;board3dObserver?.disconnect();board3dObserver=null;board3dInstance?.dispose();board3dInstance=null;board3dCanvas?.remove();board3dCanvas=null;board3dHost?.querySelector('.board-3d-labels')?.remove();board3dHost?.querySelector('.board-3d-controls')?.remove();board3dHost?.classList.remove('is-3d');board3dHost=null;board3dSignature=''}
function setBoard3dZoom(value){
 stopCameraTour();
 const current=ArenaBoard3D.settings(displayPrefs.camera3d),next=ArenaBoard3D.settings({...current,zoom:Math.round(value*1000)/1000});
 if(next.zoom===current.zoom)return;
 displayPrefs.camera3d=next;board3dSignature='';renderFocus();saveDisplay();
}
function setBoard3dTilt(value){
 stopCameraTour();displayPrefs.camera3d=ArenaBoard3D.settings({...displayPrefs.camera3d,tilt:value});board3dSignature='';renderFocus();saveDisplay();
}
function setBoard3dLift(value){
 stopCameraTour();
 const current=ArenaBoard3D.settings(displayPrefs.camera3d),next=ArenaBoard3D.settings({...current,lift:Math.round(value*1000)/1000});
 if(next.lift===current.lift)return;
 displayPrefs.camera3d=next;board3dSignature='';renderFocus();saveDisplay();
}
function syncBoard3dControlToggle(){
 boardControlsButton.hidden=displayPrefs.focus3d!==true||board3dRecovery.failed||!board3dCanvas?.isConnected;
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
 controls.querySelector('#board3dTilt').value=p.tilt;controls.querySelector('#board3dTiltValue').textContent=Math.round(p.tilt)+'°';
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
 controls.insertAdjacentHTML('beforeend',ArenaI18n.h`<label for="board3dLift">Height</label><button type="button" data-lift="down" aria-label="Lower board" data-help="Lower board">↓</button><input id="board3dLift" type="range" min="-50" max="50" step="1" aria-label="Vertical board position (%)" data-help="Raise or lower the board without changing its angle or zoom. Shift+right-drag or Shift+Up/Down also adjusts height."><button type="button" data-lift="up" aria-label="Raise board" data-help="Raise board">↑</button><button type="button" data-lift="reset" aria-label="Center board vertically" data-help="Center board vertically">↕</button>`);
 controls.querySelector('#board3dLift').oninput=e=>setBoard3dLift(Number(e.target.value)/100);
 controls.querySelector('[data-lift=down]').onclick=()=>setBoard3dLift(ArenaBoard3D.settings(displayPrefs.camera3d).lift-ArenaBoard3D.liftRange.step);
 controls.querySelector('[data-lift=up]').onclick=()=>setBoard3dLift(ArenaBoard3D.settings(displayPrefs.camera3d).lift+ArenaBoard3D.liftRange.step);
 controls.querySelector('[data-lift=reset]').onclick=()=>setBoard3dLift(0);
 controls.insertAdjacentHTML('beforeend',ArenaI18n.h`<label for="board3dTilt">Tilt</label><input id="board3dTilt" type="range" min="-30" max="70" step="1" aria-label="Camera tilt (degrees)" data-help="Positive tilt aims upward; negative tilt aims downward. Lower the viewing angle for a table-level shot."><output id="board3dTiltValue" for="board3dTilt"></output><button type="button" data-tilt="reset" aria-label="Reset tilt" data-help="Reset tilt">↶</button>`);
 controls.querySelector('#board3dTilt').oninput=e=>setBoard3dTilt(Number(e.target.value));controls.querySelector('[data-tilt=reset]').onclick=()=>setBoard3dTilt(0);
 host.append(controls);syncBoard3dZoom();
}
function paintFocusBoard(host,fen,last,crownSquares=[],knightFacings={},game={}){
 if(displayPrefs.focus3d!==true){board3dRecovery.reset();if(board3dInstance)releaseBoard3d();updateBoard(host,fen,last);return}
 if(board3dRecovery.failed){board3dRecovery.show($('#focusContent'));board3dRecovery.resume();updateBoard(host,fen,last);return}
 updateBoard(host,fen,last);
 // Load the studio renderer and original models only when 3D is requested.
 const pieceSet=ArenaBoard3D.pieceSet(displayPrefs.pieces3d);
 if(board3dCanvas&&board3dCanvas.dataset.pieceSet!==pieceSet)releaseBoard3d();
 if(!ArenaBoard3D.isReady(pieceSet)){
  if(!board3dAssetLoading){board3dAssetLoading=true;ArenaBoard3D.prepare(pieceSet).then(()=>{board3dAssetLoading=false;renderFocus()}).catch(e=>{console.warn('3D assets could not load:',e);board3dAssetLoading=false;if(displayPrefs.focus3d)failBoard3d()})}
  return;
 }
 if(board3dCanvas&&!board3dCanvas.isConnected)releaseBoard3d();
 host.classList.add('is-3d');
 if(!board3dCanvas){
  const canvas=document.createElement('canvas');canvas.className='board-3d';canvas.tabIndex=0;canvas.setAttribute('role','img');canvas.setAttribute('aria-label',ArenaI18n.t('3D chessboard. Right-drag or Alt+left-drag to orbit. Scroll to zoom. Shift-drag adjusts height. Home resets the camera.')+' '+ArenaI18n.t('Right-drag to look up, down, left or right. Keep dragging upward to look above the board. No extra key is needed.'));canvas.dataset.help=ArenaI18n.t('Right-drag or Alt+left-drag to turn the board. Scroll to zoom. Hold Shift while dragging to adjust height.')+' '+ArenaI18n.t('Right-drag to look up, down, left or right. Keep dragging upward to look above the board. No extra key is needed.');host.append(canvas);board3dCanvas=canvas;board3dHost=host;
  const fail=()=>{if(board3dCanvas===canvas)failBoard3d('context')};
  try{board3dInstance=ArenaBoard3D.create(canvas,fail,error=>{if(board3dCanvas!==canvas)return;if(error){notify(ArenaI18n.t('Room assets could not load. The board remains available.'),true);return}if(board3dArgs&&sceneVisible())requestSceneFrame(board3dArgs)},pieceSet)}catch(e){console.warn('Focused 3D board could not initialize:',e);failBoard3d();return}
  let drag=null;canvas.oncontextmenu=e=>e.preventDefault();canvas.onpointerdown=e=>{if(!ArenaBoard3D.cameraGesture(e))return;e.preventDefault();e.stopPropagation();canvas.focus();drag={x:e.clientX,y:e.clientY,lift:e.shiftKey,p:ArenaBoard3D.settings(displayPrefs.camera3d),pointer:e.pointerId};canvas.setPointerCapture(e.pointerId)};
  canvas.onpointermove=e=>{if(!drag||drag.pointer!==e.pointerId)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(!drag.moved&&Math.hypot(dx,dy)<=5)return;drag.moved=true;e.preventDefault();e.stopPropagation();displayPrefs.camera3d=ArenaBoard3D.dragSettings(drag.p,dx,dy,canvas.clientHeight,drag.lift);board3dSignature='';renderFocus()};
  canvas.onpointerup=canvas.onpointercancel=canvas.onlostpointercapture=e=>{if(drag){drag=null;e.stopPropagation();saveDisplay()}};
  canvas.addEventListener('wheel',e=>{if(e.ctrlKey||e.metaKey||!e.deltaY)return;e.preventDefault();setBoard3dZoom(ArenaBoard3D.wheelSettings(ArenaBoard3D.settings(displayPrefs.camera3d),e,canvas.clientHeight).zoom)},{passive:false});
  canvas.onkeydown=e=>{
   if(e.ctrlKey||e.metaKey||e.altKey)return;
   if(e.shiftKey&&['ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();setBoard3dLift(ArenaBoard3D.settings(displayPrefs.camera3d).lift+(e.key==='ArrowUp'?1:-1)*ArenaBoard3D.liftRange.step);return}
   if(['+','=','-','_'].includes(e.key)){e.preventDefault();setBoard3dZoom(ArenaBoard3D.settings(displayPrefs.camera3d).zoom+(['+','='].includes(e.key)?1:-1)*ArenaBoard3D.zoomRange.step);return}
   if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home'].includes(e.key))return;e.preventDefault();const p=ArenaBoard3D.settings(displayPrefs.camera3d);displayPrefs.camera3d=e.key==='Home'?{}:ArenaBoard3D.dragSettings(p,e.key==='ArrowRight'?12.5:e.key==='ArrowLeft'?-12.5:0,e.key==='ArrowUp'?-12:e.key==='ArrowDown'?12:0,canvas.clientHeight,false);board3dSignature='';renderFocus();saveDisplay();
  };
  addBoard3dZoom(host);observeSceneCanvas(canvas);
  board3dObserver=new ResizeObserver(()=>{board3dSignature='';renderFocus()});board3dObserver.observe(host);
 }
 syncBoard3dZoom();
 const context={clock:ArenaScene3D.settings(displayPrefs.scene3d).environment==='live-club'?{kind:'focus',receivedAt:game.receivedAt||0,game:{clocks:game.clocks,clock_active:game.reviewing||state.connected===false?null:game.clock_active,search_elapsed:game.search_elapsed,last_move_seconds:game.last_move_seconds}}:null,game:game.game,plates:ArenaScene3D.settings(displayPrefs.scene3d).plates,key:(game.game||'')+':'+(game.attempt||''),white:game.white?.name||'',black:game.black?.name||'',event:game.tournament_name||state.snapshot?.name||'',score:game.result||'',captured:game.captured||[],reviewing:!!game.reviewing};
 context.intention=typeof focusedIntention==='function'?focusedIntention(game):null;
 const signature=JSON.stringify([context,displayPrefs.scene3d,fen,last,crownSquares,knightFacings,displayPrefs.knights3d,!!state.flip,displayPrefs.camera3d,displayPrefs.crownMarks3d,displayPrefs.theme,host.clientWidth,host.clientHeight]);
 if(signature!==board3dSignature&&!document.hidden&&state.view==='overview'&&!panels.focus.hidden){board3dSignature=signature;requestSceneFrame([fen,state.flip,displayPrefs.camera3d||{},displayPrefs.theme==='light',last,displayPrefs.crownMarks3d===false?[]:crownSquares,displayPrefs.knights3d,knightFacings,context,displayPrefs.scene3d||{}])}
}
function boardViewDialog(options={}){const player=options?.player===true,p=ArenaBoard3D.settings(player?paBoard().camera:displayPrefs.camera3d),range=ArenaBoard3D.zoomRange;
 modal(ArenaI18n.t(player?'Player board view':'Focused board view'),ArenaI18n.h`<div class="fields board-view-fields"><label>Board style<select id="focusBoardStyle"><option value="2d" ${!(player?displayPrefs.player3d:displayPrefs.focus3d)?'selected':''}>2D · selected SVG pieces</option><option value="3d" ${(player?displayPrefs.player3d:displayPrefs.focus3d)?'selected':''}>3D board</option></select></label><label data-help="Choose the 3D pieces for both Focused Game and Player Arena.">3D piece set<select id="pieces3d"><option value="staunton1849" ${ArenaBoard3D.pieceSet(displayPrefs.pieces3d)==='staunton1849'?'selected':''}>1849 Staunton</option><option value="tal1962" ${displayPrefs.pieces3d==='tal1962'?'selected':''}>Tal 1962 · Soviet Championship</option></select></label><label data-help="Choose how the 3D knights face. Left and right are from each player's side.">Knight direction<select id="knights3d">${ArenaBoard3D.knightModes.map((mode,i)=>`<option value="${mode}" ${mode===ArenaBoard3D.knightMode(displayPrefs.knights3d)?'selected':''}>${ArenaI18n.t(['Toward the king','Away from the king','Forward','Backward','Left','Right'][i])}</option>`).join('')}</select></label>${field('cameraAngle',ArenaI18n.t('Viewing angle (degrees)'),Number(p.angle.toFixed(2)),'number','required min="6" max="78" step="any"')}${field('cameraTilt',ArenaI18n.t('Camera tilt (degrees)'),Number(p.tilt.toFixed(2)),'number','required min="-30" max="70" step="any"')}${field('cameraOrbit',ArenaI18n.t('Rotation (degrees)'),Number(p.orbit.toFixed(2)),'number','required min="-180" max="180" step="any"')}${field('cameraZoom',ArenaI18n.t('Zoom (%)'),Math.round(p.zoom*100),'number',`required min="${range.min*100}" max="${range.max*100}" step="1"`)}${field('cameraLift',ArenaI18n.t('Vertical board position (%)'),Math.round(p.lift*100),'number','required min="-50" max="50" step="1"')}<label><input id="showBoard3dControls" type="checkbox" ${(player?displayPrefs.playerCameraShown:displayPrefs.board3dControls!==false)?'checked':''}> Show 3D controls</label><label id="crownMarks3dLabel"><input id="crownMarks3d" type="checkbox" ${displayPrefs.crownMarks3d!==false?'checked':''}> Kingside crown marks</label></div><p class="caption">Right-drag to look up, down, left or right. Keep dragging upward to look above the board. No extra key is needed.</p><p class="caption">Positive tilt aims upward; negative tilt aims downward. Lower the viewing angle for a table-level shot.</p><p class="caption">Raise or lower the board without changing its angle or zoom. Shift+right-drag or Shift+Up/Down also adjusts height.</p><p class="caption">Toward or away from the king uses each knight's starting side and stays fixed as it moves. Promoted knights and positions without verified starting history face forward.</p><p class="caption">Red crowns apply to the 1849 Staunton set only and follow the original kingside rook and knight.</p><p class="caption">Right-drag or Alt+left-drag to turn the 3D board in either workspace. Left-click or drag pieces in Player Arena. Arrow keys turn the camera; Shift+Up/Down adjusts height. Scroll or press plus/minus to zoom; Home resets the camera. Your view is saved.</p>`,ArenaI18n.h('<button id="resetCamera">Reset camera</button><button id="applyBoardView" class="primary">Apply board view</button>'));
 const syncSet=()=>{$('#crownMarks3d').disabled=$('#pieces3d').value!=='staunton1849'};$('#pieces3d').onchange=syncSet;syncSet();
 $('#resetCamera').onclick=()=>{$('#cameraAngle').value=50;$('#cameraOrbit').value=0;$('#cameraZoom').value=100;$('#cameraLift').value=0;$('#cameraTilt').value=0};
 $('#applyBoardView').onclick=()=>{for(const el of $$('#modal input[type=number]'))if(!el.reportValidity())return;const is3d=$('#focusBoardStyle').value==='3d',camera={angle:Number($('#cameraAngle').value),orbit:Number($('#cameraOrbit').value),zoom:Number($('#cameraZoom').value)/100,lift:Number($('#cameraLift').value)/100,tilt:Number($('#cameraTilt').value)};displayPrefs.pieces3d=ArenaBoard3D.pieceSet($('#pieces3d').value);displayPrefs.knights3d=ArenaBoard3D.knightMode($('#knights3d').value);displayPrefs.crownMarks3d=$('#crownMarks3d').checked;if(player){const b=paBoard();b.camera=ArenaBoard3D.settings(camera);b.onCamera?.(b.camera);displayPrefs.playerCamera={...b.camera};displayPrefs.playerCameraShown=$('#showBoard3dControls').checked;b.setMode(is3d?'3d':'2d');paRender()}else{displayPrefs.focus3d=is3d;displayPrefs.camera3d=camera;displayPrefs.board3dControls=$('#showBoard3dControls').checked}if(!player)board3dRecovery.reset();board3dSignature='';saveDisplay();$('#modal').close();renderFocus()};
}
const boardViewButton=document.createElement('button');boardViewButton.className='subtle';boardViewButton.textContent=ArenaI18n.t('2D / 3D');boardViewButton.dataset.help=ArenaI18n.t('Choose the focused board style and camera. The default 2D view uses your selected SVG piece set.');boardViewButton.onclick=boardViewDialog;panels.focus.querySelector('.panel-heading').append(boardViewButton);
const boardControlsButton=document.createElement('button');boardControlsButton.id='toggleBoard3dControls';boardControlsButton.type='button';boardControlsButton.className='subtle';boardControlsButton.hidden=true;boardControlsButton.setAttribute('aria-controls','board3dControls');boardControlsButton.dataset.help=ArenaI18n.t('Show or hide the zoom and height controls. Your camera position stays the same.');boardControlsButton.onclick=()=>setBoard3dControls(displayPrefs.board3dControls===false);boardViewButton.after(boardControlsButton);
document.addEventListener('visibilitychange',()=>{board3dSignature='';if(!document.hidden)renderFocus()});
window.addEventListener('pagehide',()=>{board3dRecovery.dispose();releaseBoard3d()});
