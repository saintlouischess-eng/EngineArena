'use strict';
let board3dTourElapsed=0,board3dTourTick=0;
let board3dTimer=0,board3dArgs=null,board3dTourStart=0,board3dTourCamera=null,board3dOnscreen=true,board3dPhotoOpen=false,board3dIntersection=null;
function sceneVisible(){return !document.hidden&&state.view==='overview'&&!panels.focus.hidden&&board3dOnscreen&&board3dCanvas?.isConnected&&!board3dPhotoOpen}
function stopSceneFrames(){if(!sceneVisible()){board3dTourTick=0;board3dInstance?.pauseEnvironment()}clearTimeout(board3dTimer);board3dTimer=0;cancelAnimationFrame(board3dPending);board3dPending=0}
function stopCameraTour(){const p=ArenaScene3D.settings(displayPrefs.scene3d);if(p.mode==='presentation'){if(board3dTourCamera)displayPrefs.camera3d=ArenaBoard3D.settings(board3dTourCamera);displayPrefs.scene3d={...p,mode:'testing'};board3dTourStart=0;stopSceneFrames();saveDisplay()}}
function drawSceneFrame(){
 board3dPending=0;if(!sceneVisible()||!board3dInstance||!board3dArgs)return;
 const args=[...board3dArgs],p=ArenaScene3D.settings(displayPrefs.scene3d),reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
 args[8]={...args[8],environmentMotion:ArenaScene3D.roomMotionEnabled(p,reduced)};
 showRoomMotionStatus(panels.focus,p);
 args[9]=reduced?{...p,motion:'instant',mode:'testing'}:p;
 if(p.mode==='presentation'&&!reduced){
  const now=performance.now();if(!board3dTourStart){board3dTourStart=now;board3dTourElapsed=0;board3dTourTick=0}
  if(board3dTourTick)board3dTourElapsed+=Math.min(.5,(now-board3dTourTick)/1000)*p.tourSpeed;board3dTourTick=now;
  args[2]=ArenaScene3D.tourCamera(board3dTourElapsed,ArenaBoard3D.settings(args[2]),p.tour,(displayPrefs.savedCameras3d||[]).filter(Boolean));
 }else {board3dTourStart=0;board3dTourTick=0;}
 board3dTourCamera={...args[2]};
 try{board3dInstance.render(...args);if(Number(board3dCanvas?.dataset.frames)>0)board3dRecovery.ready()}
 catch(error){console.warn('Focused 3D render failed:',error);failBoard3d();return}
 window.ArenaRoomAudio?.tick(board3dCanvas,p);
 if((p.mode==='presentation'&&!reduced)||board3dInstance.needsFrame())board3dTimer=setTimeout(()=>{board3dTimer=0;if(sceneVisible())board3dPending=requestAnimationFrame(drawSceneFrame)},1000/p.fps);
}
function requestSceneFrame(args){board3dArgs=args;stopSceneFrames();if(sceneVisible())board3dPending=requestAnimationFrame(drawSceneFrame)}
function observeSceneCanvas(canvas){
 board3dOnscreen=true;board3dIntersection?.disconnect();board3dIntersection=new IntersectionObserver(entries=>{board3dOnscreen=entries[0]?.isIntersecting!==false;if(!board3dOnscreen)stopSceneFrames();else if(board3dArgs)requestSceneFrame(board3dArgs)});board3dIntersection.observe(canvas);
 // Capture phase adopts the current touring view before drag/zoom reads it.
 canvas.addEventListener('pointerdown',stopCameraTour,true);canvas.addEventListener('wheel',stopCameraTour,true);canvas.addEventListener('keydown',stopCameraTour,true);
}
document.addEventListener('visibilitychange',()=>{stopSceneFrames();if(sceneVisible()&&board3dArgs)requestSceneFrame(board3dArgs)});
new MutationObserver(()=>{if(!sceneVisible())stopSceneFrames();else if(board3dArgs)requestSceneFrame(board3dArgs)}).observe(panels.focus,{attributes:true,attributeFilter:['hidden']});
new MutationObserver(()=>{if(!sceneVisible())stopSceneFrames();else if(board3dArgs)requestSceneFrame(board3dArgs)}).observe($('#overview'),{attributes:true,attributeFilter:['hidden']});

const roomMotionMedia=matchMedia('(prefers-reduced-motion: reduce)');
function roomMotionMessage(p){
 if(!p.live)return ArenaI18n.t('Room animation is turned off.');
 if(p.roomMotion==='still')return ArenaI18n.t('Room motion: Still. The wall clock keeps time.');
 if(!ArenaScene3D.roomMotionEnabled(p,roomMotionMedia.matches))return ArenaI18n.t('Room motion paused by Windows. Choose Animate to enable it here.');
 return ArenaI18n.t('Room animation is enabled.');
}
function showRoomMotionStatus(panel,p){
 if(!panel)return;
 let note=panel.querySelector('.room-motion-status');
 const paused=p.environment==='live-club'&&(!p.live||!ArenaScene3D.roomMotionEnabled(p,roomMotionMedia.matches));
 if(!note&&!paused)return;
 if(!note){note=document.createElement('div');note.className='room-motion-status';note.setAttribute('role','status');(panel.querySelector('.panel-heading,.pa-window-heading')||panel.firstElementChild).after(note)}
 note.hidden=!paused;const message=paused?roomMotionMessage(p):'';if(note.textContent!==message)note.textContent=message;
}
roomMotionMedia.addEventListener('change',()=>{
 if(sceneVisible()&&board3dArgs)requestSceneFrame(board3dArgs);
 if(typeof PlayerDesk!=='undefined')PlayerDesk.board?.paint();
 document.getElementById('sceneRoomMotion')?.dispatchEvent(new Event('change'));
});

const boardViewBeforeScenes=boardViewDialog;
boardViewDialog=function(options={}){
 boardViewBeforeScenes(options);const p=ArenaScene3D.settings(displayPrefs.scene3d);
 const choices=(id,label,items,value,help)=>`<label data-help="${esc(ArenaI18n.t(help))}">${esc(ArenaI18n.t(label))}<select id="${id}">${items.map(([v,t])=>`<option value="${v}" ${v===String(value)?'selected':''}>${esc(ArenaI18n.t(t))}</option>`).join('')}</select></label>`;
 $('#modal .modal-body').insertAdjacentHTML('beforeend',`<section class="scene-settings"><h3>${esc(ArenaI18n.t('Setting & lighting'))}</h3><div class="fields board-view-fields">`+
 choices('sceneBoard','Board design',[['classic','Original Engine Arena'],['drueke','Walnut & maple · Drueke'],['jaques','Purpleheart & maple · Jaques']],p.board,'Choose the board independently of the room and table. The two wood reproductions follow the reference boards with 2.5-inch squares.')+
 choices('sceneEnvironment','Environment',[['live-club','Live chess club · full 3D'],['club','Chess club'],['hall','Championship hall'],['study','Daylight study'],['studio','Studio']],p.environment,'Choose the surroundings for your board.')+
 field('sceneRoomRotation',ArenaI18n.t('Room rotation (degrees)'),p.roomRotation,'number','min="-180" max="180" step="any"')+
 choices('sceneSurface','Table surface',[['wood','Natural wood'],['felt','Green felt'],['leather','Leather']],p.surface,'Choose the table surface.')+
 choices('sceneLighting','Lighting',[['daylight','Daylight'],['evening','Warm evening'],['tournament','Tournament']],p.lighting,'Soft lighting presets preserve the carved details.')+
 field('sceneBrightness',ArenaI18n.t('Brightness (%)'),Math.round(p.brightness*100),'number','min="60" max="140"')+
 field('sceneWarmth',ArenaI18n.t('Warmth (−100 to 100)'),Math.round(p.warmth*100),'number','min="-100" max="100"')+
 field('sceneHighlight',ArenaI18n.t('Move highlight (%)'),Math.round(p.highlight*100),'number','min="20" max="60"')+
 `</div></section><section class="scene-settings"><h3>${esc(ArenaI18n.t('Live environment'))}</h3><div class="scene-checks">`+
 [['sceneLocalTime','Use computer time for daylight',p.localTime],['sceneLive','Bring the room to life',p.live],['scenePeople','Players & spectators',p.people],['sceneGames','Background chess games',p.backgroundGames],['sceneAtmosphere','Subtle room movement',p.atmosphere],['sceneAmbience','Distant chess sounds',p.ambience]].map(([id,label,checked])=>`<label><input id="${id}" type="checkbox" ${checked?'checked':''}> ${esc(ArenaI18n.t(label))}</label>`).join('')+
 `</div><div class="fields board-view-fields">`+
 choices('sceneRoomMotion','Room motion',[['system','Follow Windows'],['animate','Animate'],['still','Still']],p.roomMotion,'Follow Windows respects reduced motion. Animate enables this room without changing Windows. Still pauses people and scenery; the wall clock keeps time.')+
 choices('sceneActivity','Room activity',[['quiet','Quiet session'],['social','Club session'],['busy','Busy chess evening']],p.activity,'Quiet has two players. Club and Busy add two players and two individual visitors who arrive, watch games and leave.')+
 field('sceneAmbienceVolume',ArenaI18n.t('Room sound volume (%)'),p.ambienceVolume,'number','min="0" max="50"')+
 `</div><p id="sceneRoomMotionStatus" class="caption" role="status"></p><p class="caption">${esc(ArenaI18n.t('The club has six individual characters. Background games are illustrative opening studies. The clock beside your board shows game time; the wall clock follows your computer. Hidden boards pause animation.'))}</p>`+
 `</section><section class="scene-settings"><h3>${esc(ArenaI18n.t('Motion & performance'))}</h3><div class="fields board-view-fields">`+
 choices('sceneMode','Viewing mode',[['testing','Testing · render when needed'],['presentation','Presentation · camera tour']],p.mode,'Testing keeps the camera still. Presentation moves it continuously while visible.')+
 choices('sceneMotion','Piece movement',[['instant','Instant'],['quick','Quick'],['smooth','Smooth']],p.motion,'Animate only consecutive moves. Switching games and jumping through history stays instant.')+
 choices('sceneTour','Camera tour',[['cinematic','Cinematic tour'],['orbit','Slow orbit'],['views','Saved views']],p.tour,'Dragging, scrolling or using camera keys stops the tour.')+
 field('sceneTourSpeed',ArenaI18n.t('Tour speed (%)'),Math.round(p.tourSpeed*100),'number','min="50" max="150"')+
 choices('sceneFps','Animation limit',[['15','15 FPS'],['30','30 FPS']],p.fps,'Limit animation work. Hidden boards stop rendering.')+
 choices('sceneQuality','Graphics quality',[['low','Economy'],['balanced','Balanced'],['high','High']],p.quality,'Live room rendering is bounded to 720p, 1080p or 1440p pixel budgets. Photo export still supports 4K.')+
 `</div><p class="caption">${esc(ArenaI18n.t('Windows reduced motion still pauses camera tours and focus-board move animation. Room motion is controlled separately.'))}</p></section>`+
 `<section class="scene-settings"><h3>${esc(ArenaI18n.t('Table details'))}</h3><div class="scene-checks">`+
 [['sceneCoordinates','Board coordinates',p.coordinates],['sceneTrays','Captured-piece trays',p.trays],['scenePlates','Engine nameplates',p.plates],['scenePlaque','Engine Arena plaque',p.plaque]].map(([id,label,checked])=>`<label><input id="${id}" type="checkbox" ${checked?'checked':''}> ${esc(ArenaI18n.t(label))}</label>`).join('')+
 `</div><p class="caption">${esc(ArenaI18n.t('Trays show recorded captures only; pieces absent from a custom starting position are not counted.'))}</p></section>`+
 `<section class="scene-settings"><h3>${esc(ArenaI18n.t('Camera views'))}</h3><div class="scene-camera-actions">`+
 [['white','White’s seat'],['black','Black’s seat'],['overhead','Overhead'],['broadcast','Broadcast'],['room','Room view'],['detail','Piece close-up'],['low','Low angle']].map(([v,t])=>`<button type="button" data-scene-view="${v}">${esc(ArenaI18n.t(t))}</button>`).join('')+
 `</div><div class="scene-camera-actions"><select id="sceneCameraSlot" aria-label="${esc(ArenaI18n.t('Saved camera'))}">${[0,1,2].map(i=>`<option value="${i}">${esc(ArenaI18n.t('View {0}',i+1))}</option>`).join('')}</select><button id="sceneSaveView">${esc(ArenaI18n.t('Save current view'))}</button><button id="sceneLoadView">${esc(ArenaI18n.t('Load view'))}</button><span id="sceneViewStatus" role="status"></span></div></section>`);
 $('#sceneLocalTime').parentElement.dataset.help=ArenaI18n.t("Local-time daylight uses dawn from 06:00 to 08:00 and dusk from 18:00 to 20:00. Turn it off to use a lighting preset.");
 function syncRoomMotionDialog(){const settings={...p,live:$('#sceneLive').checked,roomMotion:$('#sceneRoomMotion').value};$('#sceneRoomMotionStatus').hidden=$('#sceneEnvironment').value!=='live-club';$('#sceneRoomMotionStatus').textContent=roomMotionMessage(settings)}
 $('#sceneRoomMotion').onchange=syncRoomMotionDialog;
 const liveInputs=['scenePeople','sceneGames','sceneAtmosphere','sceneAmbience','sceneActivity','sceneAmbienceVolume','sceneRoomMotion'];
 const liveEnabled=()=>{const club=$('#sceneEnvironment').value==='live-club';$('#sceneLocalTime').disabled=!club;$('#sceneLighting').disabled=club&&$('#sceneLocalTime').checked;$('#sceneLive').disabled=!club;$('#sceneRoomRotation').disabled=club;$('#sceneSurface').disabled=club;for(const id of liveInputs)$('#'+id).disabled=$('#sceneEnvironment').value!=='live-club'||!$('#sceneLive').checked;$('#sceneAmbienceVolume').disabled=$('#sceneEnvironment').value!=='live-club'||!$('#sceneLive').checked||!$('#sceneAmbience').checked;syncRoomMotionDialog()};$('#sceneLocalTime').onchange=$('#sceneLive').onchange=$('#sceneAmbience').onchange=liveEnabled;$('#sceneEnvironment').onchange=()=>{if($('#sceneEnvironment').value==='live-club')$('#sceneLive').checked=true;liveEnabled()};liveEnabled();
 let saved=structuredClone(displayPrefs.savedCameras3d||[]);
 const readCamera=()=>ArenaBoard3D.settings({angle:Number($('#cameraAngle').value),orbit:Number($('#cameraOrbit').value),zoom:Number($('#cameraZoom').value)/100,lift:Number($('#cameraLift').value)/100,tilt:Number($('#cameraTilt').value)});
 const setCamera=c=>{for(const [id,value] of Object.entries({cameraAngle:Number(c.angle.toFixed(2)),cameraOrbit:Number(c.orbit.toFixed(2)),cameraZoom:Math.round(c.zoom*100),cameraLift:Math.round(c.lift*100),cameraTilt:c.tilt||0}))$('#'+id).value=value};
 $$('[data-scene-view]').forEach(b=>b.onclick=()=>setCamera({...ArenaScene3D.views[b.dataset.sceneView],orbit:((ArenaScene3D.views[b.dataset.sceneView].orbit+((options?.player?paBoard().flip:state.flip)?180:0)+180)%360)-180}));
 $('#sceneSaveView').onclick=()=>{saved[Number($('#sceneCameraSlot').value)]=readCamera();$('#sceneViewStatus').textContent=ArenaI18n.t('View saved. Apply to keep changes.')};
 $('#sceneLoadView').onclick=()=>{const c=saved[Number($('#sceneCameraSlot').value)];if(c)setCamera(c);else $('#sceneViewStatus').textContent=ArenaI18n.t('This view has not been saved yet.')};
 const original=$('#applyBoardView').onclick;
 $('#applyBoardView').onclick=()=>{
  for(const el of $$('#modal input[type=number]'))if(!el.reportValidity())return;
  displayPrefs.scene3d=ArenaScene3D.settings({roomMotion:$('#sceneRoomMotion').value,localTime:$('#sceneLocalTime').checked,live:$('#sceneLive').checked,activity:$('#sceneActivity').value,people:$('#scenePeople').checked,backgroundGames:$('#sceneGames').checked,atmosphere:$('#sceneAtmosphere').checked,ambience:$('#sceneAmbience').checked,ambienceVolume:Number($('#sceneAmbienceVolume').value),board:$('#sceneBoard').value,coordinates:$('#sceneCoordinates').checked,environment:$('#sceneEnvironment').value,roomRotation:Number($('#sceneRoomRotation').value),surface:$('#sceneSurface').value,lighting:$('#sceneLighting').value,brightness:Number($('#sceneBrightness').value)/100,warmth:Number($('#sceneWarmth').value)/100,highlight:Number($('#sceneHighlight').value)/100,mode:$('#sceneMode').value,motion:$('#sceneMotion').value,tour:$('#sceneTour').value,tourSpeed:Number($('#sceneTourSpeed').value)/100,fps:Number($('#sceneFps').value),quality:$('#sceneQuality').value,trays:$('#sceneTrays').checked,plates:$('#scenePlates').checked,plaque:$('#scenePlaque').checked});
  displayPrefs.savedCameras3d=saved;board3dTourStart=0;original();
 };
};
boardViewButton.onclick=boardViewDialog;

async function boardPhotoDialog(){
 if(!board3dInstance||!board3dArgs){notify(ArenaI18n.t('Open a game in 3D before taking a photo.'),true);return}
 board3dPhotoOpen=true;stopSceneFrames();board3dInstance.freezeEnvironment(true);const frozen=structuredClone(board3dArgs);if(board3dTourCamera)frozen[2]={...board3dTourCamera};frozen[9]={...ArenaScene3D.settings(displayPrefs.scene3d),motion:'instant'};
 modal(ArenaI18n.t('Board photo'),ArenaI18n.h`<img id="scenePhotoPreview" class="scene-photo-preview" alt="Board photo preview"><div class="fields board-view-fields"><label>Camera view<select id="photoView"><option value="current">Current view</option><option value="white">White’s seat</option><option value="black">Black’s seat</option><option value="overhead">Overhead</option><option value="broadcast">Broadcast</option><option value="room">Room view</option><option value="detail">Piece close-up</option><option value="low">Low angle</option></select></label>${field('photoTilt',ArenaI18n.t('Camera tilt (degrees)'),ArenaBoard3D.settings(frozen[2]).tilt,'number','min="-30" max="70" step="1"')}<label>Background blur<select id="photoBlur"><option value="0">Off</option><option value="0.6">Subtle</option><option value="1">Soft</option></select></label></div><p class="caption">A frozen board position, with no controls in the picture. Export size: 3840 × 2160 PNG.</p><p id="scenePhotoStatus" role="status"></p>`,ArenaI18n.h`<button id="scenePhotoExport" class="primary">Save 4K PNG…</button>`);
 photoFolderControls($('#scenePhotoStatus'));
 const renderPhoto=async size=>{if(!board3dInstance)throw Error(ArenaI18n.t('Open a game in 3D before taking a photo.'));const args=[...frozen],view=$('#photoView').value;if(view!=='current')args[2]={...ArenaScene3D.views[view],orbit:((ArenaScene3D.views[view].orbit+(args[1]?180:0)+180)%360)-180};args[2]=ArenaBoard3D.settings({...args[2],tilt:Number($('#photoTilt').value)});board3dInstance.render(...args);if(!await board3dInstance.ready())throw Error(ArenaI18n.t('Room assets could not load. The board remains available.'));return board3dInstance.photo({...size,blur:Number($('#photoBlur').value)})};
 let previewVersion=0;const preview=async()=>{const version=++previewVersion,data=await renderPhoto({width:960,height:540});if(version===previewVersion&&$('#scenePhotoPreview'))$('#scenePhotoPreview').src=data};
 $('#photoTilt').onchange=$('#photoBlur').onchange=safely(preview);$('#photoView').onchange=safely(()=>{$('#photoTilt').value=ArenaBoard3D.settings($('#photoView').value==='current'?frozen[2]:ArenaScene3D.views[$('#photoView').value]).tilt;return preview()});
 $('#scenePhotoExport').onclick=safely(async()=>{
  const button=$('#scenePhotoExport'),status=$('#scenePhotoStatus');button.disabled=true;status.textContent=ArenaI18n.t('Rendering 4K image…');
  try{await new Promise(r=>setTimeout(r,30));const data=await renderPhoto({width:3840,height:2160}),name='EngineArena-board-'+new Date().toISOString().replace(/[:.]/g,'-')+'.png';
   if(window.chrome?.webview){const result=await new Promise(resolve=>{const id=++nativeId;nativePending.set(id,resolve);window.chrome.webview.postMessage({type:'imageExport',id,name,data})});status.textContent=result.error?result.error:result.saved?ArenaI18n.t('Image saved.'):ArenaI18n.t('Save canceled.')}
   else{const a=document.createElement('a');a.download=name;a.href=data;a.click();status.textContent=ArenaI18n.t('Image ready for download.')}
  }finally{button.disabled=false}
 });
 $('#modal').addEventListener('close',()=>{board3dPhotoOpen=false;board3dInstance?.freezeEnvironment(false);board3dSignature='';renderFocus()},{once:true});
 try{await preview()}catch(e){$('#scenePhotoStatus').textContent=e.message}
}
const boardPhotoButton=document.createElement('button');boardPhotoButton.className='subtle';boardPhotoButton.id='boardPhoto';boardPhotoButton.textContent=ArenaI18n.t('Photo…');boardPhotoButton.dataset.help=ArenaI18n.t('Export the focused 3D board as a 4K picture.');boardPhotoButton.onclick=safely(boardPhotoDialog);boardControlsButton.after(boardPhotoButton);

function photoNative(type,extra={}){return new Promise(resolve=>{const id=++nativeId;nativePending.set(id,resolve);window.chrome.webview.postMessage({type,id,...extra})})}
function photoFolderControls(before){
 const row=document.createElement('div');row.className='photo-destination';
 row.innerHTML=ArenaI18n.h`<strong>Photo folder</strong><span class="caption" style="overflow-wrap:anywhere"></span><button type="button">Choose folder…</button>`;
 before.before(row);const label=row.querySelector('span'),button=row.querySelector('button');
 if(!window.chrome?.webview){label.textContent=ArenaI18n.t('Your browser controls the download folder. Use the desktop app to remember a photo folder.');button.hidden=true;return}
 const update=async choose=>{const r=await photoNative('photoFolder',{choose});if(r.error)throw Error(r.error);label.textContent=r.folder};
 button.onclick=safely(()=>update(true));safely(()=>update(false))();
}
