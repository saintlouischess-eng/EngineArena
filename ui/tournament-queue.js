'use strict';
const queueNav=document.createElement('button');queueNav.className='nav';queueNav.dataset.view='tournamentQueue';
queueNav.innerHTML=ArenaI18n.h('▶ <span>Tournament manager</span>');$('nav').insertBefore(queueNav,$('[data-view=engines]'));
const queueView=document.createElement('section');queueView.id='tournamentQueue';queueView.className='view';queueView.hidden=true;
queueView.innerHTML=ArenaI18n.h`<div id="managerEvent" class="manager-event" hidden></div><div class="queue-controls">
 <div class="manager-heading"><div><h2>Independent tournament queue</h2><p id="queueDescription" class="caption"></p></div><button id="managerConfigure">Shared resources…</button></div>
 <div class="manager-modes" role="group" aria-label="Execution mode">
  <button class="manager-mode" data-execution-mode="sequential" aria-pressed="true"><span class="mode-symbol" aria-hidden="true">Ⅰ</span><span><strong>One at a time</strong><small>Finish one tournament, then start the next.</small></span><span class="mode-check" aria-hidden="true">✓</span></button>
  <button class="manager-mode" data-execution-mode="parallel" aria-pressed="false"><span class="mode-symbol" aria-hidden="true">Ⅲ</span><span><strong>Run together</strong><small>Run multiple tournaments within shared CPU, memory and GPU limits.</small></span><span class="mode-check" aria-hidden="true">✓</span></button>
 </div><p id="managerModeHint" class="caption">Choose a mode, add tournaments below, then start when ready.</p>
 <div class="manager-session"><div><strong id="queueStatus" role="status"></strong><p id="queueNote" class="caption"></p></div><div class="manager-commands"><button class="primary" id="queueRun">Run queue</button><button id="queuePause">Pause & drain queue</button></div></div>
 <details class="manager-timing"><summary>Start time & stop options</summary><div class="queue-start"><label>Start time<select id="queueStartMode"><option value="now">When the worker is free</option><option value="later">At a chosen time</option></select></label><label id="queueDateLabel" hidden>Local date and time<input id="queueDate" type="datetime-local" data-help="Uses this computer’s local time. Keep Engine Arena open and the computer awake. After a restart, resume the queue explicitly."></label><button id="queueFinish">Finish current, then pause</button></div><p class="caption">Keep Engine Arena open and the computer awake for a timed start. Pauses, pairing problems and saving failures stop automatic advancement. Normal engine losses follow each tournament’s retry settings.</p></details>
 </div><div id="managerResources" class="manager-resources" hidden role="status"></div>
 <div class="manager-list-heading"><h2>Tournaments</h2><div class="queue-buttons"><button id="queueAddSelected">Add selected tournament</button><button id="queueAddAll">Add all unstarted tournaments</button><button id="queueClear">Clear finished entries</button><button id="queueRefresh">Refresh</button></div></div>
 <div id="managerTools" class="manager-tools"><label>Find tournament<input id="managerSearch" type="search" placeholder="Search by name"></label><label>Source<select id="managerScope"><option value="all">All tournaments</option><option value="queue">Independent queue</option><option value="events">Events & leagues</option></select></label><label>Show<select id="managerFilter"><option value="">All current tournaments</option><option value="active">Running / draining</option><option value="waiting">Waiting</option><option value="paused">Paused / needs attention</option><option value="finished">Finished</option><option value="archived">Archived / superseded</option></select></label><span class="spacer"></span><span id="managerSelected"></span></div>
 <div id="managerBulk" class="manager-bulk" hidden><button id="managerResume">Start / resume selected</button><button id="managerPause">Pause selected</button><button id="managerLimits">Priority & game limits…</button></div>
 <div class="queue-table table-scroll" tabindex="0"><table><thead id="queueHead"><tr><th>Queue order</th><th>Tournament</th><th>Status</th><th>Official / scheduled</th><th>Actions</th></tr></thead><tbody id="queueRows"></tbody></table></div>
 <div class="queue-paging"><button id="queuePrev">Previous</button><span id="queuePage"></span><button id="queueNext">Next</button></div>`;
$('main').append(queueView);
const queueBanner=document.createElement('div');queueBanner.className='queue-banner';
queueBanner.innerHTML=ArenaI18n.h`<span id="queueBannerText">Tournament queue</span><span class="spacer"></span><button id="queueAddCurrent" data-help="Append the selected paused tournament to the automatic queue. Adding it does not start it.">Add to queue</button><button id="queueOpen">Tournament manager…</button>`;
$('#overview>.toolbar').after(queueBanner);
let queueData=null,queueOffset=0,queueGeneration=0,queueLoading=false,queueMutating=false,queueListRevision=-1;
let managerSort='position',managerDirection='asc',managerStatus={},managerSelection=new Set();
function queueModeText(q){
 if(q.mode==='running'&&q.not_before>Date.now()/1000)return ArenaI18n.t('Scheduled start: {0}',new Date(q.not_before*1000).toLocaleString(ArenaI18n.locale));
 if(q.execution_mode==='parallel')return ({paused:ArenaI18n.t('Paused'),running:ArenaI18n.t('Running'),finish_current:ArenaI18n.t('Finish active, then pause'),completed:ArenaI18n.t('Completed')})[q.mode];
 return ({paused:ArenaI18n.t('Queue paused'),running:ArenaI18n.t('Queue running'),finish_current:ArenaI18n.t('Finishing current tournament'),completed:ArenaI18n.t('Queue completed')})[q.mode];
}
function renderQueueSummary(q){
 if(!q)return;const first=!queueData;queueData={...queueData,...q};
 const parallel=q.execution_mode==='parallel',event=q.active_event;queueView.classList.toggle('parallel',parallel);queueView.classList.toggle('event-active',!!event);
 $('#managerEvent').hidden=!event;
 if(event){
  stableHtml('#managerEvent',ArenaI18n.h`<div><strong>${esc(event.name)}</strong><small>League stages appear below. Use the event controls for shared resources, pausing and season progression.</small></div><div class="queue-row-actions">${event.execution_mode==='parallel'?ArenaI18n.h('<button id="managerEventResources">Event resources…</button>'):''}<button data-manager-event="${event.id}">Open event</button></div>`);
  $('#managerEvent [data-manager-event]').onclick=safely(()=>showEvent(event.id));
  if($('#managerEventResources'))$('#managerEventResources').onclick=safely(async()=>editEventResources(await api('events/'+event.id)));
 }
 $('#managerConfigure').textContent=event?ArenaI18n.t('Event resources…'):ArenaI18n.t('Shared resources…');
 $('#managerConfigure').disabled=!!event&&event.execution_mode!=='parallel';
 $('#queueRun').textContent=parallel?ArenaI18n.t('Run tournaments'):ArenaI18n.t('Run queue');
 const modeLocked=['running','finish_current'].includes(q.mode)||q.running>0||state.live.length>0;
 $$('[data-execution-mode]').forEach(b=>{b.setAttribute('aria-pressed',String(b.dataset.executionMode===q.execution_mode));b.disabled=queueMutating||!!event||modeLocked&&b.dataset.executionMode!==q.execution_mode});
 $('#managerModeHint').textContent=event?ArenaI18n.t('The event manages its own execution mode and shared budget.'):modeLocked?ArenaI18n.t('Pause and drain before changing mode. Shared limits can be adjusted during play.'):ArenaI18n.t('Choose a mode, add tournaments below, then start when ready.');
 $('#managerBulk').hidden=!parallel||!managerSelection.size;
 $('#queueStartMode').options[0].textContent=parallel?ArenaI18n.t('Immediately'):ArenaI18n.t('When the worker is free');
 $('#managerTools').hidden=false;$('#managerResources').hidden=event?event.execution_mode!=='parallel':!parallel;
 $('#queueDescription').textContent=parallel?ArenaI18n.t('Run tournaments together within one shared budget. Each keeps its own engines, openings, clocks and results.'):ArenaI18n.t('Run saved tournaments one at a time, in the order below. Each tournament keeps its own engine, opening, time-control and resource settings.');
 $('#queuePause').textContent=parallel?ArenaI18n.t('Pause all & drain'):ArenaI18n.t('Pause & drain queue');
 $('#queuePause').dataset.help=parallel?ArenaI18n.t('Pause every running tournament. Active games finish normally.'):ArenaI18n.t('Stop dispatching new games and let active games finish. The current tournament and all later entries stay in the queue.');
 $('#queueFinish').textContent=parallel?ArenaI18n.t('Finish active, then pause'):ArenaI18n.t('Finish current, then pause');
 $('#queueFinish').dataset.help=parallel?ArenaI18n.t('Finish tournaments already running. Waiting tournaments will not start.'):ArenaI18n.t('Finish all remaining games in the current tournament, then pause before starting the next entry.');
 if(['running','finish_current'].includes(q.mode)||first&&q.not_before){
  $('#queueStartMode').value=q.not_before?'later':'now';$('#queueDateLabel').hidden=!q.not_before;
  if(q.not_before){const date=new Date(q.not_before*1000);$('#queueDate').value=new Date(date.getTime()-date.getTimezoneOffset()*60000).toISOString().slice(0,16)}
 }
 if(state.view==='tournamentQueue'&&q.revision!==queueListRevision&&!queueLoading&&!queueMutating)safely(loadQueue)();
 $('#queueBannerText').textContent=queueModeText(q)+' · '+ArenaI18n.t('{0} remaining',q.remaining)+(q.active?' · '+q.active.name:'');
 $('#queueStatus').textContent=ArenaI18n.t('Independent queue')+' · '+(q.total?queueModeText(q)+' · '+ArenaI18n.t('{0} of {1} tournaments finished',q.completed,q.total):ArenaI18n.t('No tournaments queued.'));
 $('#queueNote').textContent=ArenaI18n.message(q.note)||(parallel?ArenaI18n.t('{0} tournaments active',q.running||0):!q.active&&q.mode==='running'&&q.not_before<=Date.now()/1000?ArenaI18n.t('Waiting for the worker to become free.'):q.active?ArenaI18n.t('Current tournament: {0}',q.active.name):'');
 const running=['running','finish_current'].includes(q.mode),selected=state.snapshot?.id===state.tid?state.snapshot:null;
 const canAdd=!!selected&&!selected.event&&selected.state==='paused'&&!selected.dependency&&(!selected.queue||selected.queue.finished);
 for(const [id,disabled] of Object.entries({queueRun:!!event||running||!q.remaining||q.active?.state==='draining',queuePause:!!event||!running&&!(parallel&&q.running),queueFinish:!!event||(parallel?!q.running||q.mode==='finish_current':!q.active_tid||!running||q.mode==='finish_current'),queueClear:!q.completed,queueAddCurrent:!canAdd,queueAddSelected:!canAdd,queueStartMode:!!event||running,queueDate:!!event||running})){
  const button=$('#'+id);if(!button.hasAttribute('aria-busy'))button.disabled=queueMutating||disabled;
 }
 if(parallel||event)renderManagerResources();
}
async function loadQueue(){
 const generation=++queueGeneration;queueLoading=true;
 try{
  const q=await api(`tournament-queue?scope=${$('#managerScope').value}&offset=${queueOffset}&search=${encodeURIComponent($('#managerSearch').value)}&filter=${$('#managerFilter').value}&sort=${managerSort}&direction=${managerDirection}`);
  if(generation!==queueGeneration)return;
  const count=q.filtered_total??q.total;
  if(queueOffset&&queueOffset>=count){queueOffset=Math.max(0,Math.floor((count-1)/50)*50);return loadQueue()}
  queueListRevision=q.revision;renderQueueSummary(q);queueData=q;
  if(q.overview||q.execution_mode==='parallel'){renderManagerRows(q);return}
  stableHtml('#queueHead',ArenaI18n.h('<tr><th>Queue order</th><th>Tournament</th><th>Status</th><th>Official / scheduled</th><th>Actions</th></tr>'));
  stableHtml('#queueRows',q.items.length?q.items.map((item,i)=>{
   const label=item.finished?ArenaI18n.t('Finished'):item.active?ArenaI18n.message(item.state):ArenaI18n.t('Waiting');
   const removable=!item.active||(q.mode==='paused'&&item.state==='paused');
   return ArenaI18n.h`<tr data-queue-row="${item.tid}"><td>${queueOffset+i+1}</td><td><b>${esc(item.name)}</b>${item.dependency?`<small>${esc(ArenaI18n.message(item.dependency))}</small>`:''}</td><td>${esc(label)}</td><td>${item.official_games.toLocaleString(ArenaI18n.locale)} / ${item.total.toLocaleString(ArenaI18n.locale)}</td><td><div class="queue-row-actions"><button data-qview="${item.tid}">View</button><button data-qedit="${item.tid}" ${item.started_once||item.state!=='paused'||item.dependency?'disabled':''}>Edit setup…</button><button data-qmove="up" data-tid="${item.tid}" ${item.can_up?'':'disabled'} aria-label="Move earlier" data-help="Move this waiting tournament earlier in the queue.">↑</button><button data-qmove="down" data-tid="${item.tid}" ${item.can_down?'':'disabled'} aria-label="Move later" data-help="Move this waiting tournament later in the queue.">↓</button><button data-qremove="${item.tid}" ${removable?'':'disabled'} data-help="Remove only the queue entry. The tournament, settings and results are kept.">Remove</button></div></td></tr>`;
  }).join(''):ArenaI18n.h('<tr><td colspan="5">No tournaments queued. Add a saved tournament or all unstarted tournaments.</td></tr>'));
  $('#queuePage').textContent=ArenaI18n.t('{0}–{1} of {2}',q.total?queueOffset+1:0,Math.min(queueOffset+50,q.total),q.total);
  $('#queuePrev').disabled=queueOffset===0;$('#queueNext').disabled=queueOffset+50>=q.total;
  $$('[data-qview]').forEach(b=>b.onclick=safely(async()=>{state.tid=b.dataset.qview;state.standOffset=state.gameOffset=0;view('overview');await loadTournaments();await refreshTournament()}));
  $$('[data-qedit]').forEach(b=>b.onclick=safely(async()=>{await newTournament(await api(`tournaments/${b.dataset.qedit}/setup`))}));
  $$('[data-qmove]').forEach(b=>b.onclick=safely(()=>queueAction(b.dataset.qmove,{tid:b.dataset.tid})));
  $$('[data-qremove]').forEach(b=>b.onclick=safely(()=>queueAction('remove',{tid:b.dataset.qremove})));
 }finally{if(generation===queueGeneration)queueLoading=false}
}
async function queueAction(action,extra={}){
 if(queueMutating)return;queueMutating=true;
 if(queueData?.items)renderManagerRows(queueData);
 try{
  let revision=queueData?.revision;
  for(let attempt=0;attempt<2;attempt++){
   try{await api('tournament-queue',{action,revision,...extra});break}
   catch(error){
    if(attempt||queueData?.execution_mode!=='parallel'||error.message!==ArenaI18n.t('The tournament queue changed. Refresh it before trying again.'))throw error;
    const fresh=await api('tournament-queue?configuration=1');
    if(fresh.execution_mode!=='parallel')throw error;
    revision=fresh.revision;
   }
  }
  await loadQueue();if(state.tid)await refreshTournament();
 }finally{queueMutating=false;if(queueData){renderQueueSummary(queueData);if(queueData.items)renderManagerRows(queueData)}}
}
async function showQueue(){view('tournamentQueue');$('#pageTitle').textContent=ArenaI18n.t('Tournament manager');await loadQueue()}
queueNav.onclick=safely(showQueue);$('#queueOpen').onclick=safely(showQueue);
const addCurrent=async()=>{if(!state.tid)return;await queueAction('add',{ids:[state.tid]});notify(ArenaI18n.t('Tournament added to the queue.'))};
$('#queueAddCurrent').onclick=safely(addCurrent);$('#queueAddSelected').onclick=safely(addCurrent);
$('#queueAddAll').onclick=safely(()=>queueAction('add',{all_ready:true}));
$('#queueClear').onclick=safely(()=>queueAction('clear_finished'));$('#queuePause').onclick=safely(()=>queueAction('pause'));
$('#queueFinish').onclick=safely(()=>queueAction('finish_current'));$('#queueRefresh').onclick=safely(loadQueue);
$('#queuePrev').onclick=safely(async()=>{queueOffset=Math.max(0,queueOffset-50);await loadQueue()});$('#queueNext').onclick=safely(async()=>{queueOffset+=50;await loadQueue()});
$('#queueStartMode').onchange=()=>$('#queueDateLabel').hidden=$('#queueStartMode').value!=='later';
$('#queueRun').onclick=safely(async()=>{
 let notBefore=0;
 if($('#queueStartMode').value==='later'){
  notBefore=new Date($('#queueDate').value).getTime()/1000;
  if(!Number.isFinite(notBefore)||notBefore<=Date.now()/1000)throw Error(ArenaI18n.t('Choose a future local date and time.'));
 }
 await queueAction('run',{not_before:notBefore});
});
setInterval(()=>{if(state.view==='tournamentQueue'&&!$('#modal').open&&!queueLoading&&!queueMutating)safely(loadQueue)()},2000);

function renderManagerResources(scheduling){
 if(scheduling)managerStatus=scheduling;
 const event=queueData?.active_event;
 if((event?.execution_mode||queueData?.execution_mode)!=='parallel')return;
 const used=managerStatus.used||{threads:0,memory_mb:0,gpu:{}},r=event?event.resources:queueData.resources;
 const entries=[[ArenaI18n.t('Active games'),state.live.length,r.concurrency],[ArenaI18n.t('CPU threads reserved'),used.threads,r.cpu_budget],[ArenaI18n.t('Estimated engine memory (MB)'),used.memory_mb,r.memory_budget_mb]];
 for(const g of new Set([...Object.keys(r.gpu_limits||{}),...Object.keys(used.gpu||{})]))entries.push(['GPU '+g,used.gpu[g]||0,r.gpu_limits[g]??1]);
 stableHtml('#managerResources',entries.map(([label,n,limit])=>`<div class="manager-resource"><span>${esc(label)}</span><strong>${fmt(n,0)} <small>/ ${fmt(limit,0)}</small></strong><progress max="${Math.max(1,limit)}" value="${n}" aria-label="${esc(label)}"></progress></div>`).join('')+ArenaI18n.h('<small>Reservations, not measured utilization. Lowered limits take effect as active games finish. Unlisted GPU groups allow one process.</small>'));
}

function managerSelectionChanged(){
 $('#managerSelected').textContent=managerSelection.size?ArenaI18n.t('{0} selected',managerSelection.size):'';
 $('#managerBulk').hidden=queueData?.execution_mode!=='parallel'||!managerSelection.size;
 for(const id of ['managerResume','managerPause','managerLimits'])$('#'+id).disabled=!managerSelection.size||queueMutating||(id!=='managerLimits'&&!!queueData?.active_event);
}

function renderManagerRows(q){
 queueView.classList.add('manager-overview');
 const selectable=q.items.filter(x=>q.execution_mode==='parallel'&&x.queued&&!x.event_id);
 const allowed=new Set(selectable.map(x=>x.tid));managerSelection=new Set([...managerSelection].filter(id=>allowed.has(id)));
 const focused=document.activeElement?.closest('#queueRows button,#queueRows input,#queueHead button,#queueHead input');
 const focusKeys=new Set(['id','data-tid','data-manager-action','data-manager-select','data-qview','data-qedit','data-qremove','data-manager-settings','data-manager-sort','data-manager-event','data-qmove']);
 const focusAttrs=focused?[...focused.attributes].filter(a=>focusKeys.has(a.name)).map(a=>[a.name,a.value]):[];
 const columns=[['name',ArenaI18n.t('Tournament')],['state',ArenaI18n.t('Status')],['progress',ArenaI18n.t('Completion')],['active',ArenaI18n.t('Active / limit')],['priority',ArenaI18n.t('Priority')]];
 stableHtml('#queueHead',ArenaI18n.h`<tr><th><input id="managerSelectPage" type="checkbox" aria-label="Select this page"></th>${columns.map(([key,label])=>`<th aria-sort="${managerSort===key?(managerDirection==='asc'?'ascending':'descending'):'none'}"><button data-manager-sort="${key}">${esc(label)}${managerSort===key?(managerDirection==='asc'?' ↑':' ↓'):''}</button></th>`).join('')}<th>Actions</th></tr>`);
 stableHtml('#queueRows',q.items.length?q.items.map(item=>{
  const percent=item.total?Math.min(100,100*item.official_games/item.total):0;
  const percentLabel=fmt(percent<100?Math.floor(percent*10)/10:100,1);
  const archived=item.event_id&&(!item.event_valid||item.event_state==='retired');
  const label=archived?ArenaI18n.t('Archived / superseded'):item.finished?ArenaI18n.t('Finished'):item.state==='draining'?ArenaI18n.t('Draining'):(item.dependency||item.held&&item.note?.startsWith('No remaining game fits'))?ArenaI18n.t('Needs attention'):item.state==='running'?ArenaI18n.t('Running'):item.held||!item.queued&&item.started_once?ArenaI18n.t('Paused'):ArenaI18n.t('Waiting');
  const note=item.dependency||(item.held?item.note:'')||(item.state==='running'?managerStatus.waiting?.[item.tid]:'');
  const priority=item.event_id?ArenaI18n.t('Event stage'):({1:ArenaI18n.t('Low'),2:ArenaI18n.t('Normal'),4:ArenaI18n.t('High')}[item.priority]||'—');
  const name=item.event_name&&item.name.startsWith(item.event_name+' — ')?item.name.slice(item.event_name.length+3):item.name;
  const source=item.event_name|| (item.queued?ArenaI18n.t('Independent queue'):ArenaI18n.t('Not queued'));
  let actions=ArenaI18n.h`<button data-qview="${item.tid}">View</button>`;
  if(item.event_id)actions+=ArenaI18n.h`<button data-manager-event="${item.event_id}">Open event</button>`;
  else if(item.queued&&q.execution_mode==='parallel')actions=ArenaI18n.h`<button data-manager-action="${item.state==='running'?'pause_selected':'resume_selected'}" data-tid="${item.tid}" ${q.active_event||item.finished||item.state==='draining'||item.dependency?'disabled':''}>${item.state==='running'?ArenaI18n.t('Pause'):ArenaI18n.t('Start / resume')}</button><button data-manager-settings="${item.tid}">Options…</button>`;
  else if(item.queued)actions+=ArenaI18n.h`<button data-qedit="${item.tid}" ${item.started_once||item.state!=='paused'||item.dependency?'disabled':''}>Edit setup…</button><button data-qmove="up" data-tid="${item.tid}" ${item.can_up?'':'disabled'} aria-label="Move earlier">↑</button><button data-qmove="down" data-tid="${item.tid}" ${item.can_down?'':'disabled'} aria-label="Move later">↓</button><button data-qremove="${item.tid}" ${item.active?'disabled':''}>Remove</button>`;
  const selection=allowed.has(item.tid)?`<input type="checkbox" data-manager-select="${item.tid}" aria-label="${esc(ArenaI18n.t('Select tournament {0}',item.name))}" ${managerSelection.has(item.tid)?'checked':''}>`:item.queued?String(item.position):'—';
  return ArenaI18n.h`<tr data-queue-row="${item.tid}"><td>${selection}</td><td><button class="manager-name" data-qview="${item.tid}">${esc(name)}</button><small class="manager-source">${esc(source)}</small>${note?`<small class="manager-wait">${esc(ArenaI18n.message(note))}</small>`:''}</td><td><span class="manager-state ${item.state}">${esc(label)}</span></td><td><div class="manager-progress-label"><strong>${percentLabel}%</strong><small>${fmt(item.official_games,0)} / ${fmt(item.total,0)}</small></div><progress max="100" value="${percent}" aria-label="${esc(ArenaI18n.t('Completion'))}"></progress></td><td><strong>${item.active_games}</strong><span class="manager-muted"> / ${item.game_limit}</span></td><td>${esc(priority)}</td><td><div class="queue-row-actions">${actions}</div></td></tr>`;
 }).join(''):ArenaI18n.h('<tr><td colspan="7">No tournaments match this view.</td></tr>'));
 const count=q.filtered_total;$('#queuePage').textContent=ArenaI18n.t('{0}–{1} of {2}',count?queueOffset+1:0,Math.min(queueOffset+50,count),count);
 $('#queuePrev').disabled=queueOffset===0;$('#queueNext').disabled=queueOffset+50>=count;
 $('#managerSelectPage').checked=selectable.length>0&&selectable.every(x=>managerSelection.has(x.tid));
 $('#managerSelectPage').onchange=e=>{selectable.forEach(x=>e.target.checked?managerSelection.add(x.tid):managerSelection.delete(x.tid));renderManagerRows(q)};
 $$('[data-manager-select]').forEach(b=>b.onchange=()=>{b.checked?managerSelection.add(b.dataset.managerSelect):managerSelection.delete(b.dataset.managerSelect);managerSelectionChanged()});
 $$('[data-manager-sort]').forEach(b=>b.onclick=safely(async()=>{managerDirection=managerSort===b.dataset.managerSort&&managerDirection==='asc'?'desc':'asc';managerSort=b.dataset.managerSort;queueOffset=0;await loadQueue()}));
 $$('[data-qview]').forEach(b=>b.onclick=safely(async()=>{state.tid=b.dataset.qview;state.standOffset=state.gameOffset=0;view('overview');await loadTournaments();await refreshTournament()}));
 $$('[data-qedit]').forEach(b=>b.onclick=safely(async()=>newTournament(await api(`tournaments/${b.dataset.qedit}/setup`))));
 $$('[data-qremove]').forEach(b=>b.onclick=safely(async()=>{await queueAction('remove',{tid:b.dataset.qremove});managerSelection.delete(b.dataset.qremove);managerSelectionChanged()}));
 $$('[data-manager-action]').forEach(b=>b.onclick=safely(()=>queueAction(b.dataset.managerAction,{ids:[b.dataset.tid]})));
 $$('[data-manager-settings]').forEach(b=>b.onclick=safely(()=>managerLimitsDialog([b.dataset.managerSettings])));
 $$('#queueRows [data-manager-event]').forEach(b=>b.onclick=safely(()=>showEvent(b.dataset.managerEvent)));
 $$('[data-qmove]').forEach(b=>b.onclick=safely(()=>queueAction(b.dataset.qmove,{tid:b.dataset.tid})));
 $('#managerSelectPage').disabled=queueMutating||!selectable.length;
 if(queueMutating){$$('#queueRows button:not([data-qview]),#queueRows input').forEach(b=>b.disabled=true);$('#queueRows')._renderedHtml=null}
 managerSelectionChanged();
 if(focusAttrs.length){const selector=focusAttrs.map(([k,v])=>'['+k+'=\"'+CSS.escape(v)+'\"]').join('');const replacement=$('#queueRows '+selector+',#queueHead '+selector);if(replacement&&!replacement.disabled)replacement.focus({preventScroll:true})}
}

async function managerConfigureDialog(mode){
 const q=await api('tournament-queue?configuration=1'),r=Object.keys(q.resources).length?q.resources:q.defaults;
 modal(ArenaI18n.t('Execution & resources'),ArenaI18n.h`<form id="managerForm" class="manager-form"><label>Execution mode<select id="managerMode"><option value="sequential">One at a time</option><option value="parallel">Run together</option></select></label><p class="caption">Shared limits apply across all running tournaments. Each tournament’s own limits also apply. Changing mode requires pausing and draining first.</p><div class="manager-budget-grid"><label>CPU thread budget<input id="managerCpu" type="number" min="1" step="1" required value="${r.cpu_budget}"></label><label>Engine memory budget (MB)<input id="managerMemory" type="number" min="1" step="1" required value="${r.memory_budget_mb}"></label><label>Total simultaneous games<input id="managerGames" type="number" min="1" step="1" required value="${r.concurrency}"></label></div><label>Shared GPU group slots (group:count, comma separated)<input id="managerGpu" value="${esc(Object.entries(r.gpu_limits).map(([k,v])=>k+':'+v).join(', '))}" placeholder="gpu0:1"></label><p class="caption">For one GPU running one Lc0 process, use gpu0:1. Unlisted groups allow one process; zero disables a group. Resources are reservations based on engine settings, not guaranteed physical limits.</p></form>`,ArenaI18n.h('<button id="managerSave" class="primary">Save</button>'));
 $('#managerMode').value=mode||q.execution_mode;
 const updateMode=()=>{const parallel=$('#managerMode').value==='parallel';$$('#managerCpu,#managerMemory,#managerGames,#managerGpu').forEach(e=>e.disabled=!parallel);$('#managerForm').classList.toggle('sequential',!parallel)};
 $('#managerMode').onchange=updateMode;updateMode();
 $('#managerSave').onclick=safely(async()=>{
  if(!$('#managerForm').reportValidity())return;
  const gpu={};for(const entry of $('#managerGpu').value.split(',').filter(x=>x.trim())){const parts=entry.trim().split(':');if(parts.length!==2||!parts[0].trim()||!/^\d+$/.test(parts[1].trim())||parts[0].trim() in gpu)throw Error(ArenaI18n.t('Enter GPU limits as group:count, for example gpu0:1.'));gpu[parts[0].trim()]=Number(parts[1])}
  await api('tournament-queue',{action:'configure',revision:q.revision,execution_mode:$('#managerMode').value,resources:{cpu_budget:Number($('#managerCpu').value),memory_budget_mb:Number($('#managerMemory').value),concurrency:Number($('#managerGames').value),gpu_limits:gpu}});
  $('#modal').close();queueOffset=0;managerSort='position';await loadQueue();notify(ArenaI18n.t('Execution settings saved.'));
 });
}
$('#managerConfigure').onclick=safely(async()=>queueData?.active_event?editEventResources(await api('events/'+queueData.active_event.id)):managerConfigureDialog());
$$('[data-execution-mode]').forEach(b=>b.onclick=safely(()=>{if(b.dataset.executionMode!==queueData?.execution_mode)return managerConfigureDialog(b.dataset.executionMode)}));

async function managerLimitsDialog(ids){
 const item=ids.length===1?queueData.items?.find(x=>x.tid===ids[0]):null;
 modal(ArenaI18n.t('Tournament resource sharing'),ArenaI18n.h`<form id="managerLimitsForm"><p>${ArenaI18n.t('{0} selected',ids.length)}</p><label>Priority<select id="managerPriority"><option value="">Keep current priority</option><option value="1">Low</option><option value="2">Normal</option><option value="4">High</option></select></label><label>Maximum simultaneous games per tournament<input id="managerLimit" type="number" min="1" step="1" value="${item?.game_limit??''}" placeholder="Keep current limit"></label><p class="caption">Priority changes the share of resource time, not engine strength or time controls. Every eligible tournament gets a turn. Lower game limits let active games finish.</p></form>`,ArenaI18n.h('<button id="managerApplyLimits" class="primary">Apply</button>'));
 $('#managerPriority').value=item?.priority??'';
 if(item){
  $('#managerLimitsForm>p').textContent=item.name;
  const actions=document.createElement('div');actions.className='manager-entry-actions';actions.innerHTML=ArenaI18n.h`<button type="button" id="managerEditSetup" ${item.started_once||item.state!=='paused'||item.dependency?'disabled':''}>Edit setup…</button><button type="button" id="managerRemoveEntry" ${item.active?'disabled':''}>Remove from manager</button><small>Removing an entry keeps the tournament, settings and results.</small>`;
  $('#managerLimitsForm').after(actions);
  $('#managerEditSetup').onclick=safely(async()=>newTournament(await api(`tournaments/${item.tid}/setup`)));
  $('#managerRemoveEntry').onclick=safely(async()=>{await queueAction('remove',{tid:item.tid});managerSelection.delete(item.tid);managerSelectionChanged();$('#modal').close()});
  if(item.finished)$$('#managerPriority,#managerLimit,#managerApplyLimits').forEach(b=>b.disabled=true);
 }
 $('#managerApplyLimits').onclick=safely(async()=>{if(!$('#managerLimitsForm').reportValidity())return;const priority=$('#managerPriority').value,limit=$('#managerLimit').value;await queueAction('set_limits',{ids,priority:priority?Number(priority):null,concurrency:limit?Number(limit):null});$('#modal').close()});
}
$('#managerResume').onclick=safely(()=>queueAction('resume_selected',{ids:[...managerSelection]}));
$('#managerPause').onclick=safely(()=>queueAction('pause_selected',{ids:[...managerSelection]}));
$('#managerLimits').onclick=safely(()=>managerLimitsDialog([...managerSelection]));
let managerSearchTimer;
$('#managerSearch').oninput=()=>{clearTimeout(managerSearchTimer);managerSearchTimer=setTimeout(()=>{queueOffset=0;safely(loadQueue)()},250)};
$('#managerFilter').onchange=safely(async()=>{queueOffset=0;await loadQueue()});
$('#managerScope').onchange=safely(async()=>{queueOffset=0;managerSelection.clear();await loadQueue()});

const liveScope=document.createElement('label');liveScope.className='live-scope';liveScope.innerHTML=ArenaI18n.h('Tournaments<select id="liveTournamentScope"><option value="selected">Selected tournament</option><option value="all">All running tournaments</option></select>');
$('#boardCount').after(liveScope);
$('#liveTournamentScope').value=localStorage.getItem('arenaLiveTournamentScope')==='all'?'all':'selected';
$('#liveTournamentScope').onchange=()=>{localStorage.setItem('arenaLiveTournamentScope',$('#liveTournamentScope').value);renderBoards()};
