'use strict';
// Presentation-only recovery. Never contacts the worker or changes game state.
class Arena3DRecovery {
 static held=new Set();
 static record(workspace,reason,canvas){
  const data=canvas?.dataset||{},entry={workspace,reason,utc:new Date().toISOString(),version:'1.9.2'};
  for(const key of ['environment','pieceSet','frames','renderWidth','renderHeight','bufferResizes','gpuWaits','drawCalls','aoWidth','aoHeight','roomPeople'])if(data[key]!==undefined)entry[key]=String(data[key]).slice(0,80);
  entry.viewport=[canvas?.clientWidth||0,canvas?.clientHeight||0,devicePixelRatio];
  try{const key='arena.graphicsDiagnostics',saved=JSON.parse(localStorage.getItem(key)||'[]');localStorage.setItem(key,JSON.stringify([...(Array.isArray(saved)?saved:[]).slice(-19),entry]))}catch{}
  try{window.chrome?.webview?.postMessage({type:'graphicsDiagnostic',entry})}catch{}
 }

 constructor({workspace='',active,rebuild,changed=()=>{},delay=3000,stable=60000,now=()=>performance.now()}){
  Object.assign(this,{workspace,active,rebuild,changed,delay,stable,now});this.phase='ready';this.reason='';this.timer=0;this.pending=false;this.used=false;this.healthySince=null;this.disposed=false;if(workspace&&Arena3DRecovery.held.has(workspace)){this.phase='fallback';this.reason='live-context'}
 }
 get failed(){return this.phase==='fallback'}
 fail(reason='unavailable'){
  if(this.disposed)return;
  if(this.healthySince!==null&&this.now()-this.healthySince>=this.stable)this.used=false;
  this.cancel();this.healthySince=null;this.phase='fallback';this.reason=reason;
  if(reason==='live-context'&&this.workspace)Arena3DRecovery.held.add(this.workspace);
  this.pending=reason==='context'&&!this.used;this.changed();this.resume();
 }
 resume(){
  if(this.disposed||!this.pending||this.timer||!this.active())return;
  this.timer=setTimeout(()=>{this.timer=0;if(!this.active())return;this.retry()},this.delay);
 }
 retry(){
  if(this.disposed||this.phase==='retrying')return;
  Arena3DRecovery.held.delete(this.workspace);this.cancel();this.used=true;this.phase='retrying';this.changed();
  try{this.rebuild()}catch(error){console.warn('3D retry failed:',error);this.fail('unavailable')}
 }
 ready(){
  if(this.disposed||this.failed)return;
  if(this.healthySince===null)this.healthySince=this.now();
  if(this.phase!=='ready'){this.cancel();this.phase='ready';this.reason='';this.changed()}
 }
 cancel(){clearTimeout(this.timer);this.timer=0;this.pending=false}
 reset(){Arena3DRecovery.held.delete(this.workspace);this.cancel();this.phase='ready';this.reason='';this.healthySince=null;this.used=false;this.changed()}
 dispose(){this.cancel();this.disposed=true;this.notice?.remove()}
 show(before){
  if(this.disposed||!before)return;
  if(!this.notice){
   const box=document.createElement('div');box.className='board-3d-recovery';
   const message=document.createElement('span');message.setAttribute('role','status');
   const button=document.createElement('button');button.type='button';button.textContent=ArenaI18n.t('Retry 3D');button.onclick=()=>this.retry();
   box.append(message,button);this.notice=box;
  }
  if(this.notice.nextElementSibling!==before)before.before(this.notice);
  this.notice.hidden=this.phase==='ready';this.notice.dataset.phase=this.phase;
  const message=this.phase==='retrying'?'Restoring 3D…':this.pending?
   'Graphics interrupted. Showing 2D; one automatic retry when the board is visible.':
   this.reason==='live-context'?'Live room graphics were interrupted. Staying in 2D until you choose Retry 3D. Game clocks and play are unchanged.':
   '3D is unavailable. Continue in 2D or retry. Game clocks and play are unchanged.';
  this.notice.firstChild.textContent=ArenaI18n.t(message);this.notice.lastChild.disabled=this.phase==='retrying';
 }
}
if(typeof module!=='undefined')module.exports=Arena3DRecovery;
