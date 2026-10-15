'use strict';
// Original modeled wooden impacts and soft cues. No idle audio loop or engine work.
const PlayerSound=(()=>{
 let context=null;const buffers=new Map(),previous=new Map();
 async function play(kind,enabled,volume=35){
  if(!enabled||!volume||document.hidden)return;
  try{
   context??=new (window.AudioContext||window.webkitAudioContext)();const audio=context;await audio.resume();
   if(!['move','capture','check','castle','promotion','win','loss','draw','low'].includes(kind))kind='move';
   const wooden=['move','capture','check','castle','promotion'].includes(kind);
   const variant=wooden?((previous.get(kind)??-1)+1+Math.floor(Math.random()*2))%3:0;previous.set(kind,variant);
   const key=kind+(variant?'-'+(variant+1):'');
   if(!buffers.has(key))buffers.set(key,fetch('/assets/player-'+key+'.wav').then(r=>{if(!r.ok)throw Error('Sound unavailable');return r.arrayBuffer()}).then(data=>audio.decodeAudioData(data)).catch(e=>{buffers.delete(key);throw e}));
   const buffer=await buffers.get(key);if(audio!==context||document.hidden)return;
   const source=audio.createBufferSource(),gain=audio.createGain();source.buffer=buffer;source.playbackRate.value=wooden?.985+Math.random()*.03:1;gain.gain.value=Math.max(0,Math.min(100,volume))/100*.65;source.connect(gain);gain.connect(audio.destination);source.start();source.onended=()=>{source.disconnect();gain.disconnect()};
  }catch{}
 }
 return {play,close(){context?.close().catch(()=>{});context=null;buffers.clear()}};
})();

const focusSoundButton=document.createElement('button');focusSoundButton.className='subtle';focusSoundButton.id='focusSound';focusSoundButton.textContent=ArenaI18n.t('Sound…');focusSoundButton.dataset.help=ArenaI18n.t('Optional sounds for new moves on the visible focus board. Independent of Player Arena.');panels.focus.querySelector('.panel-heading').append(focusSoundButton);
focusSoundButton.onclick=()=>{
 modal(ArenaI18n.t('Focus board sound'),ArenaI18n.h`<label><input id="focusSoundEnabled" type="checkbox" ${displayPrefs.focusSound?'checked':''}> Sound effects</label><label>Volume<input id="focusSoundVolume" type="range" min="0" max="100" value="${displayPrefs.focusSoundVolume??35}"></label><p class="caption">Only newly played moves on the visible focus board produce sound. Browsing saved moves, switching games and hidden boards stay quiet.</p>`,ArenaI18n.h`<button id="focusSoundTest">Test sound</button><button id="focusSoundSave" class="primary">Save settings</button>`);
 $('#focusSoundTest').onclick=()=>PlayerSound.play('capture',true,Number($('#focusSoundVolume').value));$('#focusSoundSave').onclick=safely(async()=>{displayPrefs.focusSound=$('#focusSoundEnabled').checked;displayPrefs.focusSoundVolume=Number($('#focusSoundVolume').value);await persistDisplay();$('#modal').close()});
};
const renderBeforeSound=renderFocus;let focusSoundLast=null;
renderFocus=function(){
 const result=renderBeforeSound();const g=retainedFocus,previous=focusSoundLast;focusSoundLast=g?{id:g.game,ply:g.ply}:null;
 // Scrolling the independent scoresheet does not change the live board. Only
 // selecting a recorded position should mute it; layout changes can also scroll.
 if(g&&previous?.id===g.game&&g.ply===previous.ply+1&&displayPrefs.focusSound&&state.view==='overview'&&!panels.focus.hidden&&!document.hidden&&!(typeof reviewingRecordedMove==='function'&&reviewingRecordedMove())){
  const san=g.san||'';PlayerSound.play(/[+#]/.test(san)?'check':san.includes('=')?'promotion':san.startsWith('O-O')?'castle':san.includes('x')?'capture':'move',true,displayPrefs.focusSoundVolume??35);
 }
 return result;
};

// Ambient taps use their own saved volume and the visible room's animation time.
// No audio timer, stream, microphone, or engine process is created for scenery.
window.ArenaRoomAudio=(()=>{const seen=new WeakMap();let last=0;return {tick(canvas,p){
 if(!canvas||p.environment!=='live-club'||!p.live||!p.ambience||!p.backgroundGames||!p.ambienceVolume||document.hidden||!ArenaScene3D.roomMotionEnabled(p,matchMedia('(prefers-reduced-motion: reduce)').matches)){if(canvas)seen.delete(canvas);return}
 const beat=Math.floor(Number(canvas.dataset.roomSeconds||0)/({quiet:18,social:12,busy:8}[p.activity])),prior=seen.get(canvas);seen.set(canvas,beat);
 if(prior!==undefined&&beat>prior&&performance.now()-last>4500){last=performance.now();PlayerSound.play(beat%3?'move':'capture',true,p.ambienceVolume*.45)}
}}})();
