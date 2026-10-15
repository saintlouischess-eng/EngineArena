'use strict';
const pgnSaves=new Map();let pgnSaveId=0;
window.chrome?.webview?.addEventListener('message',e=>{
 const m=e.data;if(m.type==='pgnSaved'&&pgnSaves.has(m.id)){pgnSaves.get(m.id)(m);pgnSaves.delete(m.id)}
 else if(m.type==='exportError')notify(m.error,true);
});
async function savePgn(url,name){
 if(window.chrome?.webview){
  const result=await new Promise(resolve=>{const id=++pgnSaveId;pgnSaves.set(id,resolve);window.chrome.webview.postMessage({type:'savePgn',id,url,name})});
  if(result.error)throw Error(result.error);return result;
 }
 if(window.showSaveFilePicker){
  const txt=name.endsWith('.txt');let handle;
  try{handle=await window.showSaveFilePicker({suggestedName:name,types:[{description:ArenaI18n.t(txt?'Text files':'Chess games'),accept:txt?{'text/plain':['.txt']}:{'application/x-chess-pgn':['.pgn']}}]})}
  catch(e){if(e.name==='AbortError')return {cancelled:true};throw e}
  const response=await fetch(url,{headers:{'X-Arena-Token':token}});if(!response.ok)throw Error((await response.json()).error||ArenaI18n.t('PGN export failed'));
  const file=await handle.createWritable();try{await response.body.pipeTo(file)}catch(e){try{await file.abort()}catch{}throw e}return {path:handle.name};
 }
 const a=document.createElement('a');a.href=url+(url.includes('?')?'&':'?')+'token='+encodeURIComponent(token);a.download=name;a.click();return {download:true};
}

async function pgnDialog(context=null){
 const player=context?.player===true;
 if(!player&&!state.tid)return;
 const tid=player?context.id:state.tid,name=player?context.name:state.snapshot?.name||'tournament',schema=await api('pgn-options');
 const previewUrl=player?'/api/player/pgn-preview?id='+encodeURIComponent(tid):`/api/tournaments/${tid}/pgn-preview`;
 const exportBase=player?'/api/player/pgn?id='+encodeURIComponent(tid)+'&':`/api/export/${tid}/pgn?`;
 // Old preferences combined annotation style and header detail. Migrate them
 // once into the new explicit model without importing unwanted archive tags.
 const saved=displayPrefs.pgnExport||{};
 let choices=structuredClone(saved.version===2?saved:schema.default);
 if(saved.version!==2&&saved.style){
  choices=structuredClone(schema.presets[saved.style==='archive'?'archive':saved.style==='moves'?'clean':'annotated'].options);
  if(saved.style!=='archive')choices.style=saved.style;
  if(saved.annotations)choices.annotations=saved.annotations;
  if(saved.perspective)choices.perspective=saved.perspective;
 }
 const presetOptions=Object.entries(schema.presets).map(([key,p])=>`<option value="${key}">${esc(ArenaI18n.t(p.label))}${key==='annotated'?' · '+ArenaI18n.t('Recommended'):''}</option>`).join('');
 const annotationLabels=[['eval','Evaluation'],['depth','Depth'],['elapsed','Time spent on move'],['clock','Remaining clock'],['nodes','Nodes'],['nps','Nodes per second'],['seldepth','Selective depth']];
 modal(ArenaI18n.t(player?'Export player PGN':'Export tournament PGN'),ArenaI18n.h`
  <div class="pgn-export">
   <p>Export current official results, with verified opening moves. Choose a preset, then customize only what you need.</p>
   <div class="fields">
    <label>Export preset<select id="pgnPreset" data-help="Presets set headers, move annotations and opening markers together. Custom changes are remembered after saving.">${presetOptions}<option value="custom">Custom</option></select></label>
    <label>Move annotations<select id="pgnStyle" data-help="Compact is easy to read. Tagged uses evaluation and clock commands understood by many chess programs. Moves only removes engine measurements."><option value="moves">Moves only</option><option value="compact">Compact · score / depth / seconds</option><option value="tagged">Tagged · evaluation and clocks</option></select></label>
   </div>
   <p class="caption" id="pgnPresetNote"></p>
   <div id="pgnAnnotations" class="pgn-checks">${annotationLabels.map(([key,label])=>`<label><input type="checkbox" data-pgn-field="${key}" data-help="${esc(ArenaI18n.t('Include this measurement when recorded. Missing values remain absent.'))}"> ${esc(ArenaI18n.t(label))}</label>`).join('')}</div>
   <details class="pgn-section" id="pgnHeaderSection"><summary>Choose headers <span id="pgnHeaderCount"></span></summary>
    <p class="caption">The seven basic game tags stay enabled. FEN, variant, evaluation perspective and exceptional time controls are kept when needed to interpret the game correctly.</p>
    <p class="pgn-required">${schema.required.map(key=>`<code>${key}</code>`).join(' ')}</p>
    <div class="pgn-header-actions"><button type="button" id="pgnMinimalHeaders">Essential headers</button><button type="button" id="pgnTestingHeaders">Testing headers</button></div>
    <div class="pgn-header-groups">${schema.groups.map(group=>`<fieldset><legend>${esc(ArenaI18n.t(group.label))}</legend>${group.headers.map(key=>`<label><input type="checkbox" data-pgn-header="${key}" data-help="${esc(ArenaI18n.t('Include this PGN tag when its value is available.'))}"><code>${key}</code></label>`).join('')}</fieldset>`).join('')}</div>
    <p id="pgnArchiveWarning" class="caption">Encoded settings make large headers and can contain local file paths and launch arguments. Use them for technical archives.</p>
   </details>
   <details class="pgn-section"><summary>Formatting and labels</summary><div class="fields pgn-format-fields">
    <label>Opening markers<select id="pgnBookComments" data-help="Opening moves are always included when their saved history can be verified. This changes comments only."><option value="none">None</option><option value="boundary">End of opening only</option><option value="all">Every book move</option></select></label>
    <label>Movetext line width<select id="pgnColumns" data-help="Wrap movetext at the selected width where possible. Header values and long individual comments are not split.">${[60,80,100,120,160].map(n=>`<option value="${n}">${n}</option>`).join('')}</select></label>
    <label>Evaluation perspective<select id="pgnPerspective" data-help="Compact scores can favor the moving engine or White. Tagged evaluations always use White’s perspective."><option value="engine">Moving engine</option><option value="white">White</option></select></label>
    <label>Engine names<select id="pgnNames" data-help="Profile names distinguish clones and configurations. Reported engine names use the identity saved when the engine ran."><option value="profile">Tournament profile names</option><option value="engine">Reported engine names</option></select></label>
    <label>Date in PGN<select id="pgnDateZone" data-help="UTC is consistent across computers. Local uses this computer’s time zone. UTCDate and UTCTime, when selected, always use UTC."><option value="utc">UTC</option><option value="local">Local computer time</option></select></label>
    <label>Event label<input id="pgnEvent" maxlength="200" placeholder="Use tournament name" data-help="Optional export-only label. The saved tournament name is unchanged."></label>
    <label>Site label<input id="pgnSite" maxlength="200" placeholder="Engine Arena" data-help="Optional export-only site label."></label>
   </div></details>
   <section class="pgn-preview"><div class="pgn-preview-title"><strong>Saved-game preview</strong><button id="pgnRefreshPreview" type="button">Refresh preview</button><button id="pgnCopyPreview" type="button" disabled>Copy sample</button></div>
    <p id="pgnPreviewStatus" role="status">Preparing preview…</p><textarea id="pgnExample" aria-label="PGN preview" readonly spellcheck="false" wrap="off"></textarea>
   </section>
   <p class="caption">Exports do not change saved games. New automatic PGNs retain testing headers and attempt identifiers; detailed measurements and settings remain in the database.</p>
   <p id="pgnSaveStatus" role="status"></p>
  </div>`,ArenaI18n.h`<button id="rememberPgnSettings">Remember choices</button><button id="savePgnText">Save TXT as…</button><button id="savePgnFile" class="primary">Save PGN as…</button>`);
 const root=$('#pgnExample'),status=$('#pgnSaveStatus'),alive=()=>$('#modal').open&&$('#pgnExample')===root;
 if(player){
  $('#modal .pgn-export>p').textContent=ArenaI18n.t('Export saved Player Arena games. Human moves include elapsed time and clocks; engine measurements appear only when recorded.');
  $('#modal .pgn-export>p.caption').textContent=ArenaI18n.t('Automatic copies use Player settings. Export choices never change stored moves or results.');
 }
 let timer,revision=0,previewController,saving=false;
 const fields={style:'pgnStyle',perspective:'pgnPerspective',book_comments:'pgnBookComments',columns:'pgnColumns',event:'pgnEvent',site:'pgnSite',names:'pgnNames',date_zone:'pgnDateZone',preset:'pgnPreset'};
 function read(){
  const value=Object.fromEntries(Object.entries(fields).map(([key,id])=>[key,$('#'+id).value]));value.columns=Number(value.columns);
  value.headers=$$('[data-pgn-header]:checked').map(e=>e.dataset.pgnHeader);value.annotations=$$('[data-pgn-field]:checked').map(e=>e.dataset.pgnField);
  return value;
 }
 function refreshControls(){
  const value=$('#pgnStyle').value;$('#pgnAnnotations').hidden=value==='moves';$('#pgnPerspective').disabled=value!=='compact';
  if(value==='tagged')$('#pgnPerspective').value='white';
  const count=$$('[data-pgn-header]:checked').length;$('#pgnHeaderCount').textContent='· '+count.toLocaleString(ArenaI18n.locale)+' '+ArenaI18n.t('optional tags selected');
  const archive=$$('[data-pgn-header]:checked').some(e=>['WhiteSettings','BlackSettings','TournamentSettings'].includes(e.dataset.pgnHeader));
  $('#pgnArchiveWarning').hidden=!archive;
  $('#pgnPresetNote').textContent=ArenaI18n.t(schema.presets[$('#pgnPreset').value]?.description||'Your custom header and annotation choices. Only recorded values are exported.');
 }
 function apply(value){
  for(const [key,id] of Object.entries(fields))$('#'+id).value=value[key]??schema.default[key];
  for(const e of $$('[data-pgn-header]'))e.checked=value.headers.includes(e.dataset.pgnHeader);
  for(const e of $$('[data-pgn-field]'))e.checked=(value.annotations||[]).includes(e.dataset.pgnField);
  refreshControls();schedule();
 }
 function schedule(){
  clearTimeout(timer);previewController?.abort();++revision;
  $('#pgnPreviewStatus').textContent=ArenaI18n.t('Preparing preview…');$('#pgnCopyPreview').disabled=true;
  timer=setTimeout(preview,250);
 }
 async function preview(){
  if(!alive())return;const version=revision,controller=new AbortController();previewController=controller;
  try{
   const response=await fetch(previewUrl,{method:'POST',signal:controller.signal,headers:{'X-Arena-Token':token,'Content-Type':'application/json'},body:JSON.stringify(read())});
   const data=await response.json();if(!response.ok)throw Error(ArenaI18n.message(data.error)||ArenaI18n.t('PGN export failed'));
   if(!alive()||version!==revision)return;
   root.value=data.pgn;$('#pgnCopyPreview').disabled=!data.pgn||data.truncated;
   $('#pgnPreviewStatus').textContent=data.game_number===null?ArenaI18n.t('No completed official games yet. The preview appears after the first result.'):
    ArenaI18n.t('Game {0} · {1} headers · preview uses your current choices.',data.game_number.toLocaleString(ArenaI18n.locale),data.headers.length.toLocaleString(ArenaI18n.locale))+(data.truncated?' '+ArenaI18n.t('Preview shortened; saved exports contain the full game.'):'');
  }catch(error){if(error.name!=='AbortError'&&alive()&&version===revision)$('#pgnPreviewStatus').textContent=error.message}
 }
 const changed=()=>{$('#pgnPreset').value='custom';refreshControls();schedule()};
 $('#pgnPreset').onchange=()=>{const preset=schema.presets[$('#pgnPreset').value];if(preset)apply(structuredClone(preset.options));else changed()};
 for(const [key,id] of Object.entries(fields))if(key!=='preset')$('#'+id).addEventListener(key==='event'||key==='site'?'input':'change',changed);
 for(const e of $$('[data-pgn-header],[data-pgn-field]'))e.onchange=changed;
 $('#pgnMinimalHeaders').onclick=()=>{for(const e of $$('[data-pgn-header]'))e.checked=false;changed()};
 $('#pgnTestingHeaders').onclick=()=>{for(const e of $$('[data-pgn-header]'))e.checked=schema.presets.testing.options.headers.includes(e.dataset.pgnHeader);changed()};
 $('#pgnRefreshPreview').onclick=schedule;
 $('#pgnCopyPreview').onclick=safely(async()=>{try{await navigator.clipboard.writeText(root.value);status.textContent=ArenaI18n.t('Copied to clipboard.')}catch{root.focus();root.select();status.textContent=ArenaI18n.t('Automatic clipboard access is unavailable. The text is selected; press Ctrl+C to copy.')}});
 async function remember(value=read()){displayPrefs.pgnExport={version:2,...value};await persistDisplay();if(player)await api('player/settings',{pgn_options:value})}
 $('#rememberPgnSettings').onclick=safely(async()=>{await remember();if(alive())status.textContent=ArenaI18n.t('Export choices saved for next time.')});
 async function save(filetype){
  if(saving)return;saving=true;const value=read();const query=new URLSearchParams({...value,headers:value.headers.join(','),annotations:value.annotations.join(','),filetype});
  const filename=name.replace(/[<>:"/\\|?*\x00-\x1f]/g,'_').slice(0,100)+'-'+value.preset+'.'+filetype;
  for(const id of ['savePgnText','savePgnFile'])$('#'+id).disabled=true;
  status.textContent=ArenaI18n.t('Choose a location. The export streams to disk; large tournaments can take time.');
  try{
   const result=await savePgn(exportBase+query,filename);
   if(result.cancelled){if(alive())status.textContent=ArenaI18n.t('Save cancelled. No file was changed.');return}
   // A preference-write failure must not misreport a successfully saved PGN.
   await remember(value).catch(error=>notify(error.message,true));
   const message=result.download?ArenaI18n.t('Download requested. Check your browser’s download location.'):ArenaI18n.t('Saved ')+result.path;
   if(alive())status.textContent=message;notify(message);
  }catch(error){if(alive())status.textContent=ArenaI18n.t('Save failed. The selected file was not replaced.');throw error}
  finally{saving=false;if(alive())for(const id of ['savePgnText','savePgnFile'])$('#'+id).disabled=false}
 }
 $('#savePgnFile').onclick=safely(()=>save('pgn'));$('#savePgnText').onclick=safely(()=>save('txt'));
 const close=()=>{clearTimeout(timer);previewController?.abort();$('#modal').removeEventListener('close',close)};$('#modal').addEventListener('close',close);
 apply(choices);
}
$('#exportPgn').textContent=ArenaI18n.t('Export PGN…');$('#exportPgn').onclick=safely(pgnDialog);
