'use strict';
const bulkSelectAll=document.createElement('button');bulkSelectAll.textContent=ArenaI18n.t('Select all matching profiles');bulkSelectAll.id='bulkSelectAll';$('#bulkEngine').before(bulkSelectAll);
bulkSelectAll.onclick=safely(async()=>{state.selected=new Set(await api('profiles/selection?q='+encodeURIComponent($('#engineSearch').value)));await loadEngines()});
const bulkClear=document.createElement('button');bulkClear.textContent=ArenaI18n.t('Clear selection');bulkClear.id='bulkClearSelection';bulkSelectAll.after(bulkClear);bulkClear.onclick=safely(async()=>{state.selected.clear();await loadEngines()});
$('#bulkEngine').onclick=safely(async()=>{
 const ids=[...state.selected];if(!ids.length)throw Error(ArenaI18n.t('Select engine profiles first.'));
 let [catalog,books]=await Promise.all([api('profiles/bulk',{ids,catalog:true}),api('move-books')]);
 modal(ArenaI18n.t('Bulk engine settings'),ArenaI18n.h`<p>${ArenaI18n.m`${ids.length} selected profiles`}</p><p class="caption">Only checked changes are applied. Preview shows unsupported options and values outside an engine’s range. Saved tournaments keep their recorded profiles.</p>
 <div id="bulkEditor"><div id="bulkDiscovery" ${catalog.missing.length?'':'hidden'}><p id="bulkDiscoveryCount">${ArenaI18n.m`${catalog.missing.length} profiles need option discovery.`}</p><p class="caption">Imported profiles may not contain option definitions. Discover missing options while games are paused: one engine starts at a time, without searching. Saved option values are retained.</p><div class="toolbar"><button id="bulkDiscover">Discover missing options</button><button id="bulkStopDiscovery" hidden>Stop after current engine</button></div><p id="bulkDiscoveryStatus" role="status"></p></div><div class="fields"><label><span><input id="bulkUseThreads" type="checkbox"> CPU threads</span><input id="bulkThreads" type="number" min="1" step="1" value="1"></label><label><span><input id="bulkUseHash" type="checkbox"> Hash MB</span><input id="bulkHash" type="number" min="1" step="1" value="1024"></label></div>
 <label><span><input id="bulkUseTb" type="checkbox"> Engine SyzygyPath</span><div class="path"><input id="bulkTb"><button data-browse="bulkTb" data-folder="true">Browse…</button></div></label>
 <p class="caption">This configures engine probing only where SyzygyPath is advertised. GUI tablebase adjudication is a separate tournament setting.</p>
 <div class="section-label">Engine move book</div><p class="caption">These are each engine’s own move-book settings. A shared tournament opening file is configured in tournament setup.</p>
 <div class="fields"><label>Saved book<select id="bulkBook"><option value="keep">Keep existing books</option><option value="none">No engine move book</option>${books.map(b=>`<option value="${esc(b.id)}">${esc(b.name)}</option>`).join('')}</select></label><label><span><input id="bulkUsePlies" type="checkbox"> Maximum book plies (0 = unlimited)</span><input id="bulkPlies" type="number" min="0" step="1" value="16"></label><label><span><input id="bulkUsePolicy" type="checkbox"> Move selection</span><select id="bulkPolicy"><option value="weighted">Weighted by book frequency</option><option value="uniform">Equal chance per move</option><option value="best">Highest book weight</option></select></label></div>
 <label>Time control<select id="bulkControl"><option value="keep">Keep existing controls</option><option value="tournament">Use tournament time control</option><option value="custom">Set a common profile control</option></select></label><div id="bulkTcWrap" hidden>${tcEditor('bulkTc')}</div>
 <details><summary>Other UCI options</summary><p class="caption">Use the engine’s advertised option name and value. Unsupported options are skipped. Ponder and chess variant are controlled by the tournament.</p><datalist id="bulkNames">${catalog.options.map(n=>`<option value="${esc(n)}"></option>`).join('')}</datalist><div id="bulkOptions"></div><button id="bulkAddOption">Add option</button></details></div>
 <div id="bulkPreview" hidden><p id="bulkSummary" role="status"></p><div class="table-scroll bulk-table"><table><thead><tr><th>Engine</th><th>Changes</th><th>Skipped / warnings</th></tr></thead><tbody id="bulkRows"></tbody></table></div><div class="pager"><button id="bulkPrev">←</button><span id="bulkPage"></span><button id="bulkNext">→</button></div></div>`,ArenaI18n.h`<button id="bulkBack" hidden>Back</button><button class="primary" id="bulkReview">Preview changes</button><button class="primary" id="applyBulk" hidden>Apply reviewed changes</button>`);
 wireBrowsers();wireTc('bulkTc');$('#bulkControl').onchange=()=>$('#bulkTcWrap').hidden=$('#bulkControl').value!=='custom';
 const discoveryRoot=$('#bulkDiscovery');let stopDiscovery=false;
 $('#bulkStopDiscovery').onclick=()=>{stopDiscovery=true};
 $('#bulkDiscover').onclick=safely(async()=>{
  stopDiscovery=false;$('#bulkReview').disabled=true;$('#bulkStopDiscovery').hidden=false;let completed=0;const failures=[];
  try{
   for(const p of catalog.missing){
    if(stopDiscovery||!discoveryRoot.isConnected||!$('#modal').open)break;
    $('#bulkDiscoveryStatus').textContent=`${completed+1} / ${catalog.missing.length} · ${p.name}`;
    try{await api('profiles/inspect-options',{id:p.id})}catch(e){failures.push(`${p.name}: ${e.message}`)}completed++;
   }
   if(!discoveryRoot.isConnected)return;
   catalog=await api('profiles/bulk',{ids,catalog:true});$('#bulkDiscoveryCount').textContent=ArenaI18n.m`${catalog.missing.length} profiles need option discovery.`;$('#bulkDiscover').hidden=!catalog.missing.length;$('#bulkNames').innerHTML=catalog.options.map(n=>`<option value="${esc(n)}"></option>`).join('');
   $('#bulkDiscoveryStatus').textContent=ArenaI18n.m`${completed} profiles checked; ${catalog.missing.length} still need discovery.`+(failures.length?'\n'+failures.join('\n'):'');
  }finally{if(discoveryRoot.isConnected){$('#bulkReview').disabled=false;$('#bulkStopDiscovery').hidden=true}}
 });
 $('#bulkAddOption').onclick=()=>{const row=document.createElement('div');row.className='bulk-option';row.innerHTML=ArenaI18n.h`<input data-option-name list="bulkNames" aria-label="UCI option name" placeholder="UCI option name"><input data-option-value aria-label="Value" placeholder="Value"><button type="button">Remove</button>`;row.querySelector('button').onclick=()=>row.remove();$('#bulkOptions').append(row)};
 let patch,signature,offset=0;
 const read=()=>{
  const p={},options={};for(const [use,id,key] of [['bulkUseThreads','bulkThreads','threads'],['bulkUseHash','bulkHash','hash']])if($('#'+use).checked)p[key]=Number($('#'+id).value);
  if($('#bulkUseTb').checked)options.SyzygyPath=$('#bulkTb').value.trim();
  for(const row of $$('#bulkOptions .bulk-option')){const key=row.querySelector('[data-option-name]').value.trim();if(!key)throw Error(ArenaI18n.t('Enter an advertised UCI option name.'));if(Object.keys(options).some(k=>k.toLowerCase()===key.toLowerCase()))throw Error(ArenaI18n.t('Each UCI option can appear only once.'));options[key]=row.querySelector('[data-option-value]').value}
  if(Object.keys(options).length)p.options=options;
  if($('#bulkBook').value==='none')p.move_book=null;
  else{const b={};if($('#bulkBook').value!=='keep')b.id=$('#bulkBook').value;if($('#bulkUsePlies').checked)b.max_plies=Number($('#bulkPlies').value);if($('#bulkUsePolicy').checked)b.policy=$('#bulkPolicy').value;if(Object.keys(b).length)p.move_book=b}
  if($('#bulkControl').value!=='keep')p.time_control=$('#bulkControl').value==='tournament'?null:readTc('bulkTc');return p;
 };
 const display=async()=>{
  const r=await api('profiles/bulk',{ids,patch,offset});if(signature&&signature!==r.signature)throw Error(ArenaI18n.t('Profiles changed after preview. Review the changes again.'));signature=r.signature;
  const show=(field,value)=>value==null?'—':field==='time_control'?tcText(value):field==='move_book'?`${value.name||value.id} · ${value.max_plies??16} ${ArenaI18n.t('plies')} · ${value.policy||'weighted'}`:String(value);
  $('#bulkRows').innerHTML=r.items.map(p=>`<tr><td>${esc(p.name)}</td><td>${p.changes.map(c=>`${esc(c.field==='move_book'?ArenaI18n.t('Engine move book'):c.field==='time_control'?ArenaI18n.t('Time control'):c.field)}: ${esc(show(c.field,c.before))} → ${esc(show(c.field,c.after))}`).join('<br>')||'—'}</td><td>${p.warnings.map(w=>esc(ArenaI18n.message(w))).join('<br>')||'—'}</td></tr>`).join('');
  $('#bulkSummary').textContent=ArenaI18n.m`${r.changed} profiles will change; ${r.skipped} unsupported or invalid settings skipped.`;
  $('#bulkPage').textContent=`${offset+1}–${Math.min(offset+50,r.total)} / ${r.total}`;$('#bulkPrev').disabled=!offset;$('#bulkNext').disabled=offset+50>=r.total;$('#applyBulk').disabled=!r.changed;
  $('#bulkEditor').hidden=true;$('#bulkPreview').hidden=false;$('#bulkBack').hidden=false;$('#applyBulk').hidden=false;$('#bulkReview').hidden=true;
 };
 $('#bulkReview').onclick=safely(async()=>{patch=read();offset=0;signature=null;await display()});
 $('#bulkPrev').onclick=safely(async()=>{offset=Math.max(0,offset-50);await display()});$('#bulkNext').onclick=safely(async()=>{offset+=50;await display()});
 $('#bulkBack').onclick=()=>{$('#bulkEditor').hidden=false;$('#bulkPreview').hidden=true;$('#bulkBack').hidden=true;$('#applyBulk').hidden=true;$('#bulkReview').hidden=false};
 $('#applyBulk').onclick=safely(async()=>{const r=await api('profiles/bulk',{ids,patch,signature,apply:true});$('#modal').close();await loadEngines();notify(ArenaI18n.m`${r.changed} engine profiles updated.`)});
});
