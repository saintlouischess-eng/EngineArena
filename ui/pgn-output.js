'use strict';
// Automatic official PGNs share the native path picker, not the download flow.
async function choosePgnOutput(){
 if(window.chrome?.webview)return new Promise(resolve=>{const id=++nativeId;nativePending.set(id,resolve);window.chrome.webview.postMessage({type:'pgnOutputPath',id})});
 const value=prompt(ArenaI18n.t('File path'));return value?[value]:[];
}
function pgnOutputFields(data,current={}){
 return ArenaI18n.h`<section class="pgn-section pgn-auto-fields"><h3>Automatic PGN file</h3>
 <label><input id="autoPgnEnabled" type="checkbox" ${current.enabled?'checked':''}> Save official games automatically to my file</label>
 <p class="caption">Combine tournaments in one PGN. Completed official games are added automatically; replacement results update the existing game. Diagnostic and interrupted attempts stay in the internal history.</p>
 <div class="fields" id="autoPgnFields">
 <label>Saved destinations<select id="autoPgnRecent"><option value="">Choose a file…</option>${data.targets.map((r,i)=>`<option value="${i}">${esc(r.path)}</option>`).join('')}</select></label>
 <label>File mode<select id="autoPgnMode" data-help="New file never overwrites an existing PGN. Append / continue keeps existing games and shares the file with other selected tournaments."><option value="new">New file</option><option value="append">Append / continue</option></select></label>
 <div class="field full"><label for="autoPgnPath">PGN file</label><div class="path"><input id="autoPgnPath" value="${esc(current.path||'')}" placeholder="C:\\Chess\\PGN\\my-rating-list.pgn"><button type="button" id="autoPgnBrowse">Browse…</button></div></div>
 <label>Export preset<select id="autoPgnPreset"><option value="clean">Clean games</option><option value="annotated">Annotated games</option><option value="testing">Engine testing</option><option value="archive">Complete archive</option></select></label>
 <label class="pgn-remember"><input id="autoPgnRemember" type="checkbox" ${displayPrefs.autoPgn?.remember?'checked':''}> Remember this destination for new tournaments</label>
 </div><p class="caption">Keep the .arena-pgn.sqlite3 export index beside your PGN for safe continuation. Copy just the PGN when sharing. Existing games without GameId tags are preserved, but cannot be matched to saved tournament games.</p>
 <p id="autoPgnStatus" role="status"></p></section>`;
}
function wirePgnOutput(data,current={}){
 $('#autoPgnMode').value=current.path?'append':'new';$('#autoPgnPreset').value=current.preset||'annotated';
 const update=()=>{$('#autoPgnFields').hidden=!$('#autoPgnEnabled').checked};
 $('#autoPgnEnabled').addEventListener('change',update);update();
 $('#autoPgnRecent').onchange=()=>{const r=data.targets[Number($('#autoPgnRecent').value)];if($('#autoPgnRecent').value===''||!r)return;$('#autoPgnPath').value=r.path;$('#autoPgnMode').value='append';$('#autoPgnPreset').value=r.preset;$('#autoPgnPath').dispatchEvent(new Event('change',{bubbles:true}))};
 $('#autoPgnBrowse').onclick=safely(async()=>{const paths=await choosePgnOutput();if(paths[0]){$('#autoPgnPath').value=paths[0];$('#autoPgnPath').dispatchEvent(new Event('change',{bubbles:true}))}});
}
function readPgnOutput(){return {enabled:$('#autoPgnEnabled').checked,path:$('#autoPgnPath').value.trim(),mode:$('#autoPgnMode').value,preset:$('#autoPgnPreset').value}}
async function rememberPgnOutput(value,remember){displayPrefs.autoPgn={...value,mode:'append',remember};await persistDisplay()}
async function automaticPgnDialog(){
 if(!state.tid)return;
 const tid=state.tid,data=await api('pgn-output'),link=data.links.find(r=>r.tid===tid),target=data.targets.find(r=>r.path===link?.path);
 const current=target?{...target,enabled:true}:{enabled:false,...(displayPrefs.autoPgn?.remember?displayPrefs.autoPgn:{})};
 modal(ArenaI18n.t('Automatic PGN file'),pgnOutputFields(data,current),ArenaI18n.h`<button id="autoPgnRetry">Retry saving</button><button id="autoPgnApply" class="primary">Save settings</button>`);
 wirePgnOutput(data,current);
 const status=$('#autoPgnStatus'),alive=()=>$('#autoPgnStatus')===status&&$('#modal').open;
 function show(row){status.textContent=row?.error?ArenaI18n.message(row.error):row?ArenaI18n.t('{0} tracked games · {1} waiting',row.games||0,row.pending||0):ArenaI18n.t('Previously completed official games will also be included.')}
 show(target);$('#autoPgnRetry').disabled=!target;
 $('#autoPgnRetry').onclick=safely(async()=>{const r=await api('pgn-output',{action:'retry',path:target.path});if(alive())show(r.targets.find(t=>t.path===target.path))});
 $('#autoPgnApply').onclick=safely(async()=>{
  const value=readPgnOutput(),remember=$('#autoPgnRemember').checked,button=$('#autoPgnApply');button.disabled=true;status.textContent=ArenaI18n.t('Saving…');
  try{await api('pgn-output',{tid,...value});await rememberPgnOutput(value,remember).catch(e=>notify(e.message,true));if(alive())$('#modal').close();notify(ArenaI18n.t('Automatic PGN settings saved.'))}
  finally{button.disabled=false}
 });
 const poll=setInterval(safely(async()=>{if(!alive())return;const r=await api('pgn-output');if(alive())show(r.targets.find(t=>t.path===target?.path))}),2000);
 $('#modal').addEventListener('close',()=>clearInterval(poll),{once:true});
}
$('#exportPgn').insertAdjacentHTML('afterend',ArenaI18n.h`<button id="automaticPgn" data-help="Choose a PGN file that receives official results automatically, including across multiple tournaments.">Automatic PGN…</button>`);
$('#automaticPgn').onclick=safely(automaticPgnDialog);

// Install before setup-workflow so draft collection includes these fields.
const newTournamentBeforePgn=newTournament;
newTournament=async function(draft=null){
 await newTournamentBeforePgn(draft);
 const data=await api('pgn-output'),link=data.links.find(r=>r.tid===draft?.id),target=data.targets.find(r=>r.path===link?.path);
 const current=draft?(target?{...target,enabled:true}:{enabled:false}):(displayPrefs.autoPgn?.remember?displayPrefs.autoPgn:{enabled:false});
 $('#modal .modal-body').insertAdjacentHTML('beforeend',pgnOutputFields(data,current));wirePgnOutput(data,current);
};
$('#newTournament').onclick=safely(newTournament);
const saveTournamentBeforePgn=saveTournamentSetup;
saveTournamentSetup=async function(payload,draft){
 // Quick match has a review screen, without the full setup's PGN controls.
 // Honor a remembered destination without reading nonexistent form elements
 // or overwriting the saved preference. Internal game saving is unaffected.
 if(!$('#autoPgnEnabled')){
  const saved=displayPrefs.autoPgn;
  const output=payload.pgn_output??(saved?.remember?{enabled:!!saved.enabled,path:saved.path,mode:'append',preset:saved.preset}:{enabled:false});
  return saveTournamentBeforePgn({...payload,pgn_output:output},draft);
 }
 const value=readPgnOutput(),remember=$('#autoPgnRemember').checked;
 await saveTournamentBeforePgn({...payload,pgn_output:value},draft);
 await rememberPgnOutput(value,remember).catch(e=>notify(e.message,true));
};

let lastPgnError='';
function renderPgnOutputStatus(outputs=[]){
 if(!$('#pgnOutputHealth'))$('#healthContent').insertAdjacentHTML('afterend','<section id="pgnOutputHealth" class="pgn-section" hidden></section>');
 const box=$('#pgnOutputHealth');box.hidden=!outputs.length;
 stableHtml('#pgnOutputHealth',`<h3>${esc(ArenaI18n.t('Automatic PGN files'))}</h3>`+outputs.map(r=>`<div class="pgn-output-state ${r.error?'health-problem':''}"><code>${esc(r.path)}</code><p>${esc(r.error?ArenaI18n.message(r.error):ArenaI18n.t('{0} tracked games · {1} waiting',r.games||0,r.pending||0))}</p>${r.error?`<button data-pgn-retry="${esc(r.path)}">${esc(ArenaI18n.t('Retry saving'))}</button>`:''}</div>`).join(''));
 $$('[data-pgn-retry]').forEach(b=>b.onclick=safely(()=>api('pgn-output',{action:'retry',path:b.dataset.pgnRetry})));
 const error=outputs.filter(r=>r.error).map(r=>r.path+': '+ArenaI18n.message(r.error)).join('\n');
 $('#automaticPgn').textContent=ArenaI18n.t(error?'Automatic PGN · needs attention':'Automatic PGN…');
 $('#automaticPgn').classList.toggle('danger',!!error);
 if(error&&error!==lastPgnError)notify(ArenaI18n.t('Automatic PGN needs attention. Results remain saved in the tournament database.')+'\n'+error,true);
 lastPgnError=error;
}
