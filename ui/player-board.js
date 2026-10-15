'use strict';
// Input is independent of the tournament focus board and never changes its flip.
class PlayerBoard {
 constructor(host,onMove){
  this.host=host;this.onMove=onMove;this.game=null;this.review=null;this.selected=null;this.mode=displayPrefs.player3d?'3d':'2d';this.flip=false;this.renderer=null;this.canvas=null;this.dragging=null;this.frame=0;this.timer=0;this.onscreen=true;this.disposed=false;this.signature='';
  this.recovery=new Arena3DRecovery({workspace:'player',active:()=>!this.disposed&&this.mode==='3d'&&!document.hidden&&!host.closest('.view')?.hidden&&this.visibleBounds(),rebuild:()=>{this.release();this.paint()},changed:()=>{this.recovery.show(host);this.onGraphics?.()}});
  this.camera=ArenaBoard3D.settings(displayPrefs.playerCamera||{});this.resize=new ResizeObserver(()=>this.paint());this.resize.observe(host);
  this.intersection=new IntersectionObserver(entries=>{this.onscreen=entries[0]?.isIntersecting!==false;this.stopFrames();if(this.onscreen)this.paint();else this.renderer?.pauseEnvironment()});this.intersection.observe(host);
  document.addEventListener('visibilitychange',this.visibility=()=>{this.stopFrames();if(!document.hidden)this.paint();else this.renderer?.pauseEnvironment()});
  host.oncontextmenu=e=>e.preventDefault();host.onpointerdown=e=>this.down(e);host.onpointermove=e=>this.move(e);host.onpointerup=e=>this.up(e);host.onpointercancel=()=>this.cancel();host.onlostpointercapture=()=>this.cancel();
  host.onkeydown=e=>{if(e.target===this.canvas&&this.mode==='3d'&&this.cameraKey(e))return;if(e.key==='Escape'){this.cancel();this.selected=null;this.mark();return}const square=e.target.closest('[data-square]');if(square&&['Enter',' '].includes(e.key)){e.preventDefault();this.choose(square.dataset.square)}if(square&&e.key.startsWith('Arrow')){const cells=[...host.querySelectorAll('[data-square]')],i=cells.indexOf(square),step={ArrowRight:1,ArrowLeft:-1,ArrowDown:8,ArrowUp:-8}[e.key];e.preventDefault();cells[(i+step+64)%64]?.focus()}};
  host.addEventListener('wheel',this.wheel=e=>{if(this.mode!=='3d'||e.ctrlKey||e.metaKey)return;e.preventDefault();this.camera=ArenaBoard3D.wheelSettings(this.camera,e,this.host.clientHeight);this.paint();this.saveCamera()},{passive:false});
 }
 cameraKey(e){
  if(e.ctrlKey||e.metaKey||e.altKey)return false;
  const p=this.camera;if(e.shiftKey&&['ArrowUp','ArrowDown'].includes(e.key))this.camera=ArenaBoard3D.settings({...p,lift:p.lift+(e.key==='ArrowUp'?1:-1)*ArenaBoard3D.liftRange.step});
  else if(['+','=','-','_'].includes(e.key))this.camera=ArenaBoard3D.settings({...p,zoom:p.zoom+(['+','='].includes(e.key)?1:-1)*ArenaBoard3D.zoomRange.step});
  else if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home'].includes(e.key))this.camera=e.key==='Home'?ArenaBoard3D.settings({}):ArenaBoard3D.dragSettings(p,e.key==='ArrowRight'?12.5:e.key==='ArrowLeft'?-12.5:0,e.key==='ArrowUp'?-12:e.key==='ArrowDown'?12:0,this.host.clientHeight,false);
  else return false;e.preventDefault();this.paint();this.saveCamera();return true;
 }
 saveCamera(){displayPrefs.playerCamera={...this.camera};this.onCamera?.(this.camera);saveDisplay()}
 setMode(mode){this.cancel(false);this.mode=mode;this.recovery.reset();displayPrefs.player3d=mode==='3d';saveDisplay();this.release();this.paint()}
 fail3d(reason='unavailable'){if(this.disposed)return;if(reason==='context'&&this.canvas?.dataset.environment==='live-club')reason='live-context';Arena3DRecovery.record('player',reason,this.canvas);this.cancel(false);this.release();this.recovery.fail(reason);this.paint()}
 setGame(game,review=null){const previous=this.game;this.game=game;this.review=review;if(previous?.id!==game?.id){this.flip=game?.config.color==='black';this.selected=null}if(previous?.fen!==game?.fen||review!==null)this.selected=null;this.paint()}
 stopFrames(){clearTimeout(this.timer);this.timer=0;cancelAnimationFrame(this.frame);this.frame=0}
 release(){this.stopFrames();this.renderer?.dispose();this.renderer=null;this.canvas=null;this.signature='';this.host.replaceChildren()}
 legal(){return !this.blocked&&this.review===null&&this.game?.state==='playing'?this.game.legal||[]:[]}
 visibleBounds(){
  // An IntersectionObserver callback can describe the empty board between a
  // mode switch and its next layout. Recheck actual clipping on that rare path
  // so a visible board cannot remain blank waiting for an obsolete callback.
  const r=this.host.getBoundingClientRect();let left=Math.max(0,r.left),right=Math.min(innerWidth,r.right),top=Math.max(0,r.top),bottom=Math.min(innerHeight,r.bottom);
  for(let p=this.host.parentElement;p&&right>left&&bottom>top;p=p.parentElement){const s=getComputedStyle(p);if(s.display==='none'||s.visibility==='hidden')return false;const b=p.getBoundingClientRect();if(/hidden|clip|auto|scroll/.test(s.overflowX)){left=Math.max(left,b.left);right=Math.min(right,b.right)}if(/hidden|clip|auto|scroll/.test(s.overflowY)){top=Math.max(top,b.top);bottom=Math.min(bottom,b.bottom)}}
  return right>left&&bottom>top;
 }
 async paint(){
  this.stopFrames();if(this.photoOpen||this.disposed||document.hidden||this.host.closest('.view')?.hidden)return;if(!this.onscreen){if(!this.visibleBounds())return;this.onscreen=true}const game=this.game,record=this.review===null?null:game?.moves[this.review-1];
  const fen=this.review===null?(game?.fen||'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'):record?.fen||game.config.fen,last=record?.uci||(this.review===null?game?.moves.at(-1)?.uci:'')||'';
  if(this.recovery.failed)this.recovery.show(this.host);this.recovery.resume();
  if(this.mode==='2d'||this.recovery.failed){
   const note=this.host.closest('#paBoardPanel')?.querySelector('.room-motion-status');if(note)note.hidden=true;
   this.host.style.setProperty('--pa-square-size',Math.max(1,Math.min(this.host.clientWidth,this.host.clientHeight))+'px');
   const signature=[fen,last,this.flip,state.pieceSet].join('|');if(signature!==this.signature){this.host.innerHTML=boardHtml(fen,last,this.flip);this.signature=signature;for(const el of this.host.querySelectorAll('[data-square]')){el.tabIndex=0;el.setAttribute('role','button');el.setAttribute('aria-label',el.dataset.square+' '+(el.querySelector('img')?.alt||ArenaI18n.t('Empty square')))}}
   this.host.classList.remove('pa-3d');this.mark();return;
  }
  this.host.classList.add('pa-3d');
  const pieceSet=ArenaBoard3D.pieceSet(displayPrefs.pieces3d);
  if(this.canvas&&this.canvas.dataset.pieceSet!==pieceSet){this.cancel(false);this.release()}
  if(!ArenaBoard3D.isReady(pieceSet)){if(this.loading)return;this.loading=true;try{await ArenaBoard3D.prepare(pieceSet)}catch(error){console.warn('Player 3D assets could not load:',error);if(this.mode==='3d')this.fail3d()}finally{this.loading=false}if(!this.disposed)this.paint();return}
  if(!this.canvas){
   this.host.replaceChildren();const canvas=document.createElement('canvas');this.canvas=canvas;canvas.className='pa-canvas';canvas.tabIndex=0;canvas.setAttribute('aria-label',ArenaI18n.t('Player chessboard. Click or drag pieces. Right-drag or Alt+left-drag to turn the camera. Scroll to zoom; hold Shift while dragging to adjust height.')+' '+ArenaI18n.t('Right-drag to look up, down, left or right. Keep dragging upward to look above the board. No extra key is needed.'));canvas.dataset.help=ArenaI18n.t('Right-drag to look up, down, left or right. Keep dragging upward to look above the board. No extra key is needed.');this.host.append(canvas);
   try{this.renderer=ArenaBoard3D.create(canvas,()=>{if(this.canvas===canvas)this.fail3d('context')},error=>{if(this.canvas!==canvas||this.disposed)return;if(error)notify(ArenaI18n.t('Room assets could not load. The board remains available.'),true);this.paint()},pieceSet);this.onGraphics?.()}
   catch(error){console.warn('Player 3D board could not initialize:',error);this.fail3d();return}
  }
  const prefs={...ArenaScene3D.settings(displayPrefs.scene3d),tour:false},ctx={clock:game?{kind:'player',game:{clocks:game.clocks,moves:this.review===null?[]:game.moves,state:game.state,turn:game.turn,turn_elapsed:game.turn_elapsed},review:this.review,receivedAt:PlayerDesk.received,viewing:PlayerDesk.viewing}:null,environmentMotion:ArenaScene3D.roomMotionEnabled(prefs,matchMedia('(prefers-reduced-motion: reduce)').matches),key:game?.id||'player-ready',white:game?.config.color==='white'?game.name:game?.engine.name||'',black:game?.config.color==='black'?game.name:game?.engine.name||'',event:'Player Arena',captured:this.review===null?game?.captured:[],reviewing:this.review!==null};
  showRoomMotionStatus(this.host.closest('#paBoardPanel'),prefs);
  this.args=[fen,this.flip,this.camera,displayPrefs.theme==='light',last,this.review===null&&displayPrefs.crownMarks3d!==false?game?.crown_squares||[]:[],displayPrefs.knights3d,this.review===null?game?.knight_facings||{}:{},ctx,prefs];
  try{this.mark(false);this.renderer.render(...this.args);if(Number(this.canvas?.dataset.frames)>0)this.recovery.ready()}
  catch(error){console.warn('Player 3D render failed:',error);this.fail3d();return}
  window.ArenaRoomAudio?.tick(this.canvas,prefs);
  if(this.renderer.needsFrame()&&!document.hidden&&!this.host.closest('.view')?.hidden){this.timer=setTimeout(()=>{this.timer=0;this.frame=requestAnimationFrame(()=>{this.frame=0;this.paint()})},1000/prefs.fps)}
 }
 mark(repaint=true){
  const targets=this.legal().filter(m=>m.from===this.selected).map(m=>m.to),show=this.showLegal!==false,hint=this.review===null&&this.game?.hint?[this.game.hint.move.slice(0,2),this.game.hint.move.slice(2,4)]:[];
  if(this.renderer){this.renderer.interaction(this.selected,show?targets:[],hint);if(repaint)this.paint();return}
  for(const el of this.host.querySelectorAll('[data-square]')){el.classList.toggle('pa-selected',el.dataset.square===this.selected);el.classList.toggle('pa-target',show&&targets.includes(el.dataset.square));el.classList.toggle('pa-hint',hint.includes(el.dataset.square));el.setAttribute('aria-pressed',String(el.dataset.square===this.selected))}
 }
 pick(e,ground=false){return this.renderer?this.renderer.pick(e.clientX,e.clientY,ground):document.elementFromPoint(e.clientX,e.clientY)?.closest('[data-square]')?.dataset.square||null}
 down(e){
  if(![0,2].includes(e.button))return;const square=this.pick(e);this.host.setPointerCapture(e.pointerId);if(ArenaBoard3D.cameraGesture(e))this.canvas?.focus();
  this.dragging={square,selected:this.selected,x:e.clientX,y:e.clientY,moved:false,camera:ArenaBoard3D.cameraGesture(e),lift:e.shiftKey,p:{...this.camera},pointer:e.pointerId};
  if(!this.dragging.camera&&this.legal().some(m=>m.from===square)){this.selected=square;this.mark()}
  e.preventDefault();
 }
 move(e){
  const drag=this.dragging;if(!drag||drag.pointer!==e.pointerId)return;if(Math.hypot(e.clientX-drag.x,e.clientY-drag.y)>5)drag.moved=true;if(!drag.moved)return;
  if(drag.camera){if(this.mode==='3d'){this.camera=ArenaBoard3D.dragSettings(drag.p,e.clientX-drag.x,e.clientY-drag.y,this.host.clientHeight,drag.lift);this.onCamera?.(this.camera);this.paint()}return}
  if(!this.legal().some(m=>m.from===drag.square))return;
  if(this.renderer){this.renderer.drag(drag.square,e.clientX,e.clientY);this.paint();return}
  const img=this.host.querySelector(`[data-square="${drag.square}"] img`);if(!img)return;
  if(!this.ghost){this.ghost=img.cloneNode();this.ghost.className='pa-drag-ghost';this.ghost.style.width=img.getBoundingClientRect().width+'px';document.body.append(this.ghost);img.style.opacity='.3'}
  this.ghost.style.left=e.clientX+'px';this.ghost.style.top=e.clientY+'px';
 }
 up(e){const drag=this.dragging;if(!drag)return;const square=this.pick(e,drag.moved);this.cancel();if(drag.camera){this.saveCamera();return}if(drag.moved){if(drag.square&&square&&square!==drag.square)this.tryMove(drag.square,square);return}this.selected=drag.selected;this.choose(square)}
 cancel(repaint=true){this.dragging=null;this.ghost?.remove();this.ghost=null;for(const img of this.host.querySelectorAll('img'))img.style.opacity='';this.renderer?.drag(null);if(repaint)this.paint()}
 choose(square){if(!square)return;if(this.selected&&this.legal().some(m=>m.from===this.selected&&m.to===square)){this.tryMove(this.selected,square);return}this.selected=this.legal().some(m=>m.from===square)?square:null;this.mark()}
 tryMove(from,to){const choices=this.legal().filter(m=>m.from===from&&m.to===to);if(choices.length)this.onMove(choices);else{this.selected=null;this.mark()}}
 dispose(){this.disposed=true;this.recovery.dispose();this.cancel(false);this.resize.disconnect();this.intersection.disconnect();document.removeEventListener('visibilitychange',this.visibility);this.host.removeEventListener('wheel',this.wheel);this.release()}
}
