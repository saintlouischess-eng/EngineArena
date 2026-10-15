'use strict';
// Player panels keep their DOM, input state and GPU renderer while being moved.
const PlayerWorkspace=(()=>{
 const names={board:'Playing board',moves:'Game moves',thinking:'Engine thinking',ratings:'Personal ratings',series:'Challenge series',saved:'Saved games'};
 const ids={board:'paBoardPanel',moves:'paMovesPanel',thinking:'paThinkingPanel',ratings:'paRatingsPanel',series:'paSeriesPanel',saved:'paSavedPanel'};
 const panels=Object.fromEntries(Object.entries(ids).map(([k,id])=>[k,document.getElementById(id)]));
 const grid=document.createElement('div');grid.className='pa-dock';
 grid.innerHTML='<div class="pa-column" data-pa-column="left"></div><div class="pa-divider" role="separator" tabindex="0" aria-orientation="vertical"></div><div class="pa-column" data-pa-column="right"></div><div class="pa-column pa-lower" data-pa-column="lower"></div>';
 paRoot.querySelector('.pa-layout').before(grid);
 let expanded=null,z=140,drag=null,fullscreenOwned=false;
 const defaults=()=>({split:59,panels:Object.fromEntries(Object.keys(names).map((k,i)=>[k,{column:['left','right','right','left','lower','lower'][i],order:i,visible:true,floating:false,height:[Math.max(620,Math.min(850,innerHeight-310)),365,445,220,225,350][i],width:k==='board'?800:480,x:65+i*25,y:55+i*22,font:100}]))});
 function config(){const d=defaults();displayPrefs.playerLayout={...d,...displayPrefs.playerLayout,panels:Object.fromEntries(Object.keys(names).map(k=>[k,{...d.panels[k],...displayPrefs.playerLayout?.panels?.[k]}]))};return displayPrefs.playerLayout}
 function clamp(v,min,max,fallback=min){return Math.max(min,Math.min(max,Number.isFinite(Number(v))?Number(v):fallback))}
 function bounds(p){const nav=document.querySelector('aside')?.getBoundingClientRect().right||0,left=innerWidth-nav>360?nav+8:8,available=innerWidth-left-8,width=clamp(p.width,Math.min(320,available),available),height=clamp(p.height,Math.min(200,innerHeight-16),innerHeight-16);return {width,height,x:clamp(p.x,left,Math.max(left,innerWidth-width-8)),y:clamp(p.y,8,Math.max(8,innerHeight-height-8))}}
 function apply(){
  const c=config();grid.style.setProperty('--pa-split',clamp(c.split,30,75,59)+'%');
  grid.querySelector('.pa-divider').setAttribute('aria-valuenow',Math.round(c.split));
  for(const k of Object.keys(names).sort((a,b)=>c.panels[a].order-c.panels[b].order)){
   const el=panels[k],p=c.panels[k],big=expanded===k,float=p.floating||big;
   const parent=float?paRoot:grid.querySelector(`[data-pa-column="${['left','right','lower'].includes(p.column)?p.column:'right'}"]`);
   // Reparent only when needed; reordering an unchanged canvas can reset focus.
   if(el.parentElement!==parent)parent.append(el);
   else if(!float&&el.nextElementSibling&&c.panels[el.nextElementSibling.dataset.paPanel]?.order<p.order)parent.append(el);
   el.hidden=!p.visible;el.classList.toggle('pa-floating',float);el.classList.toggle('pa-expanded',big);
   el.style.setProperty('--pa-text-scale',clamp(p.font,80,150,100)/100);
   Object.assign(el.style,{height:clamp(p.height,k==='board'?420:180,2400)+'px',width:'',left:'',top:''});
   if(float)Object.assign(el.style,Object.fromEntries(Object.entries(big?{x:8,y:8,width:innerWidth-16,height:innerHeight-16}:bounds(p)).map(([key,v])=>[key==='x'?'left':key==='y'?'top':key,v+'px'])));
   el.querySelector('[data-pa-float]').textContent=paT(p.floating?'Dock':'Float');
   el.querySelector('[data-pa-expand]').textContent=paT(big?'Restore':'Expand');
   el.querySelector('[data-pa-expand]').setAttribute('aria-pressed',String(big));
  }
  document.body.classList.toggle('pa-board-expanded',!!expanded&&state.view==='playerArena');
  const full=document.getElementById('paFullscreen');if(full)full.textContent=paT(expanded==='board'?'Restore':'Full screen');
 }
 function changed(){apply();saveDisplay()}
 function expand(k){if(fullscreenOwned&&document.fullscreenElement)document.exitFullscreen().catch(()=>{});expanded=expanded===k?null:k;config().panels[k].visible=true;panels[k].style.zIndex=++z;apply();PlayerDesk.board?.paint()}
 function float(k){if(expanded===k)expanded=null;const p=config().panels[k];p.floating=!p.floating;panels[k].style.zIndex=++z;changed()}
 function move(k,column,before=null){const c=config(),p=c.panels[k];p.floating=false;p.column=column;expanded=null;const ordered=Object.keys(names).filter(x=>x!==k&&c.panels[x].column===column).sort((a,b)=>c.panels[a].order-c.panels[b].order);const at=before?ordered.indexOf(before):-1;ordered.splice(at<0?ordered.length:at,0,k);ordered.forEach((x,i)=>c.panels[x].order=i);const target=grid.querySelector(`[data-pa-column="${column}"]`);ordered.forEach(x=>{if(!c.panels[x].floating)target.append(panels[x])});changed()}
 function panelOptions(k){
  const p=config().panels[k];modal(paT(names[k]),ArenaI18n.h`<div class="fields"><label>Dock position<select id="paPanelColumn"><option value="left">Left column</option><option value="right">Right column</option><option value="lower">Below the board</option></select></label><label>Panel height<input id="paPanelHeight" type="number" min="${k==='board'?420:180}" max="2400" value="${Math.round(p.height)}"></label><label>Floating width<input id="paPanelWidth" type="number" min="320" max="3840" value="${Math.round(p.width)}"></label><label>Panel text size (%)<input id="paPanelFont" type="number" min="80" max="150" step="5" value="${p.font}"></label></div><p class="caption">Drag panel headings to rearrange. Drag the bottom-right corner to resize. The center divider changes docked widths.</p>`,ArenaI18n.h`<button id="paPanelHide">Hide panel</button><button id="paPanelApply" class="primary">Apply</button>`);
  $('#paPanelColumn').value=p.column;
  $('#paPanelHide').onclick=()=>{config().panels[k].visible=false;if(expanded===k)expanded=null;$('#modal').close();changed()};
  $('#paPanelApply').onclick=()=>{for(const el of $$('#modal input'))if(!el.reportValidity())return;const col=$('#paPanelColumn').value;if(col!==p.column)move(k,col);Object.assign(config().panels[k],{height:Number($('#paPanelHeight').value),width:Number($('#paPanelWidth').value),font:Number($('#paPanelFont').value)});$('#modal').close();changed()};
 }
 for(const [k,el] of Object.entries(panels)){
  el.dataset.paPanel=k;el.classList.add('pa-window');el.querySelector('.pa-card-head h3')?.remove();
  const body=document.createElement('div');body.className='pa-window-body';body.append(...el.childNodes);el.append(body);
  const head=document.createElement('div');head.className='pa-window-heading';
  head.innerHTML=`<button class="pa-grip" draggable="true" aria-label="${esc(paT('Move panel'))}">⠿</button><h3>${esc(paT(names[k]))}</h3><div class="pa-window-tools"><button data-pa-float>${paT('Float')}</button><button data-pa-expand>${paT('Expand')}</button><button data-pa-options aria-label="${esc(paT('Panel options'))}">⋯</button></div>`;
  el.prepend(head);head.querySelector('[data-pa-float]').onclick=()=>float(k);head.querySelector('[data-pa-expand]').onclick=()=>expand(k);head.querySelector('[data-pa-options]').onclick=()=>panelOptions(k);
  const grip=head.querySelector('.pa-grip');grip.onclick=()=>panelOptions(k);grip.dataset.help=paT('Drag panel headings to rearrange. Drag the bottom-right corner to resize. The center divider changes docked widths.');
  grip.ondragstart=e=>{e.dataTransfer.setData('text/arena-player-panel',k);e.dataTransfer.effectAllowed='move'};
  head.onpointerdown=e=>{if(e.button!==0||e.target.closest('button')||!config().panels[k].floating||expanded===k)return;const r=el.getBoundingClientRect();start(e,head,{kind:'move',key:k,x:e.clientX,y:e.clientY,left:r.x,top:r.y})};
  el.addEventListener('pointerdown',()=>{if(el.classList.contains('pa-floating'))el.style.zIndex=++z});
  const handle=document.createElement('button');handle.className='pa-resizer';handle.setAttribute('aria-label',paT('Resize panel'));handle.dataset.help=paT('Resize panel');handle.textContent='◢';el.append(handle);
  handle.onpointerdown=e=>{if(e.button!==0||expanded===k)return;const r=el.getBoundingClientRect();start(e,handle,{kind:'size',key:k,x:e.clientX,y:e.clientY,width:r.width,height:r.height})};
  handle.onkeydown=e=>{if(!e.key.startsWith('Arrow')||expanded===k)return;e.preventDefault();const p=config().panels[k],step=e.shiftKey?40:10;if(e.key==='ArrowUp'||e.key==='ArrowDown')p.height=clamp(p.height+(e.key==='ArrowDown'?step:-step),k==='board'?420:180,2400);else if(p.floating)p.width=clamp(p.width+(e.key==='ArrowRight'?step:-step),320,innerWidth-16);else config().split=clamp(config().split+(e.key==='ArrowRight'?1:-1),30,75);changed()};
 }
 apply();paRoot.querySelector('.pa-layout').remove();
 function start(e,handle,value){e.preventDefault();handle.setPointerCapture(e.pointerId);drag={...value,handle,pointer:e.pointerId};document.body.classList.add('pa-adjusting')}
 document.addEventListener('pointermove',e=>{if(!drag||e.pointerId!==drag.pointer)return;const c=config(),p=c.panels[drag.key];if(drag.kind==='split'){const r=grid.getBoundingClientRect();c.split=clamp((e.clientX-r.left)/r.width*100,30,75)}else if(drag.kind==='move'){Object.assign(p,bounds({...p,x:drag.left+e.clientX-drag.x,y:drag.top+e.clientY-drag.y}))}else{p.height=clamp(drag.height+e.clientY-drag.y,drag.key==='board'?420:180,2400);if(p.floating)p.width=clamp(drag.width+e.clientX-drag.x,320,innerWidth-16)}apply()});
 function end(){if(!drag)return;drag=null;document.body.classList.remove('pa-adjusting');saveDisplay()}
 document.addEventListener('pointerup',end);document.addEventListener('pointercancel',end);
 const divider=grid.querySelector('.pa-divider');divider.setAttribute('aria-label',paT('Resize workspace columns'));divider.setAttribute('aria-valuemin','30');divider.setAttribute('aria-valuemax','75');divider.onpointerdown=e=>{if(e.button===0)start(e,divider,{kind:'split'})};divider.onkeydown=e=>{if(!['ArrowLeft','ArrowRight'].includes(e.key))return;e.preventDefault();config().split=clamp(config().split+(e.key==='ArrowRight'?2:-2),30,75);changed()};
 for(const col of grid.querySelectorAll('[data-pa-column]')){col.ondragover=e=>{if(e.dataTransfer.types.includes('text/arena-player-panel')){e.preventDefault();e.dataTransfer.dropEffect='move';col.classList.add('pa-drop')}};col.ondragleave=e=>{if(!col.contains(e.relatedTarget))col.classList.remove('pa-drop')};col.ondrop=e=>{const k=e.dataTransfer.getData('text/arena-player-panel');col.classList.remove('pa-drop');if(!panels[k])return;e.preventDefault();move(k,col.dataset.paColumn,e.target.closest('[data-pa-panel]')?.dataset.paPanel)}}
 function layout(){modal(paT('Player workspace'),ArenaI18n.h`<p>Choose visible panels. Your layout is saved automatically.</p><div class="pa-layout-options">${Object.keys(names).map(k=>`<label><input type="checkbox" data-pa-visible="${k}" ${config().panels[k].visible?'checked':''}> ${esc(paT(names[k]))}</label>`).join('')}</div><label>Board column width (%)<input id="paSplit" type="range" min="30" max="75" value="${config().split}"></label>`,ArenaI18n.h`<button id="paLayoutReset">Reset layout</button><button id="paLayoutDone" class="primary">Done</button>`);$$('[data-pa-visible]').forEach(el=>el.onchange=()=>{config().panels[el.dataset.paVisible].visible=el.checked;changed()});$('#paSplit').oninput=()=>{config().split=Number($('#paSplit').value);changed()};$('#paLayoutDone').onclick=()=>$('#modal').close();$('#paLayoutReset').onclick=()=>{displayPrefs.playerLayout=defaults();expanded=null;$('#modal').close();changed()}}
 const button=document.createElement('button');button.id='paLayout';button.textContent=paT('Workspace…');button.onclick=layout;paRoot.querySelector('.pa-hero .pa-actions').append(button);
 const full=document.createElement('button');full.id='paFullscreen';full.textContent=paT('Full screen');full.onclick=safely(async()=>{if(expanded==='board'){expanded=null;if(fullscreenOwned&&document.fullscreenElement)await document.exitFullscreen();fullscreenOwned=false;apply();return}expanded='board';panels.board.style.zIndex=++z;apply();if(document.documentElement.requestFullscreen){try{await document.documentElement.requestFullscreen();fullscreenOwned=true}catch{/* Expanded view also works in hosts that do not grant fullscreen. */}}});$('#paCameraToggle').before(full);
 document.addEventListener('fullscreenchange',()=>{if(fullscreenOwned&&!document.fullscreenElement){fullscreenOwned=false;expanded=null;apply()}});
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&expanded&&!$('#modal').open){expanded=null;if(fullscreenOwned&&document.fullscreenElement)document.exitFullscreen().catch(()=>{});apply()}});
 const oldView=view;view=function(name){oldView(name);if(name!=='playerArena'){expanded=null;if(fullscreenOwned&&document.fullscreenElement)document.exitFullscreen().catch(()=>{})}apply()};
 const oldDisplay=applyDisplay;applyDisplay=function(){oldDisplay();apply()};
 addEventListener('resize',()=>apply());apply();
 return {apply,config,move,expand,panels};
})();
