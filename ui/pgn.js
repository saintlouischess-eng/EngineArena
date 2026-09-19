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
  let handle;try{handle=await window.showSaveFilePicker({suggestedName:name,types:[{description:'Chess games',accept:{'application/x-chess-pgn':['.pgn']}}]})}catch(e){if(e.name==='AbortError')return {cancelled:true};throw e}
  const response=await fetch(url,{headers:{'X-Arena-Token':token}});if(!response.ok)throw Error((await response.json()).error||'PGN export failed');
  const file=await handle.createWritable();try{await response.body.pipeTo(file)}catch(e){try{await file.abort()}catch{}throw e}return {path:handle.name};
 }
 const a=document.createElement('a');a.href=url+(url.includes('?')?'&':'?')+'token='+encodeURIComponent(token);a.download=name;a.click();return {download:true};
}
function pgnDialog(){
 if(!state.tid)return;const tid=state.tid,p=displayPrefs.pgnExport||{},style=p.style||'compact';
 const defaults=style==='compact'?['eval','depth','elapsed']:['eval','depth','elapsed','clock','nodes','nps','seldepth'],selected=p.annotations||defaults;
 modal('Export tournament PGN',`<p>Export the current official results, including recorded opening moves. Previous attempts remain in the tournament history. Existing tournaments can be re-exported with these corrections.</p><div class="fields"><div class="field"><label for="pgnStyle">PGN format</label><select id="pgnStyle" data-help="Compact follows the score/depth/time style of your reference games. Tagged uses [%eval], [%clk] and [%emt]. Archive adds the complete encoded settings for technical auditing.">${[['compact','Compact · score / depth / seconds'],['tagged','Tagged · standard evaluation and clock annotations'],['moves','Moves only · no engine measurements'],['archive','Full technical archive · all settings']].map(([value,label])=>`<option value="${value}" ${style===value?'selected':''}>${label}</option>`).join('')}</select></div><div class="field"><label for="pgnPerspective">Evaluation perspective</label><select id="pgnPerspective" data-help="Moving engine matches the reference PGN: positive favors the engine that played the move. Tagged annotations always use White’s perspective for compatibility."><option value="engine" ${p.perspective!=='white'?'selected':''}>Moving engine</option><option value="white" ${p.perspective==='white'?'selected':''}>White</option></select></div></div><div id="pgnAnnotations" class="fields">${[['eval','Evaluation'],['depth','Depth'],['elapsed','Time spent on move'],['clock','Remaining clock'],['nodes','Nodes'],['nps','Nodes per second'],['seldepth','Selective depth']].map(([key,label])=>`<label><input type="checkbox" data-pgn-field="${key}" ${selected.includes(key)?'checked':''} data-help="Include ${label.toLowerCase()} when recorded; missing measurements are left absent."> ${label}</label>`).join('')}</div><pre class="log" id="pgnExample"></pre><p class="caption" id="pgnNote"></p><p class="caption">Book moves are marked {book}. FEN-only starts retain their starting position. New automatic PGNs use compact comments; full measurements and settings remain saved in the database.</p><p id="pgnSaveStatus" role="status"></p>`,`<button id="savePgnFile" class="primary">Save PGN as…</button>`);
 const update=()=>{const value=$('#pgnStyle').value,tagged=['tagged','archive'].includes(value);$('#pgnPerspective').disabled=tagged||value==='moves';if(tagged)$('#pgnPerspective').value='white';$('#pgnAnnotations').hidden=value==='moves';$('#pgnExample').textContent=value==='moves'?'1. e4 {book} e5 {book} 2. Nf3 Nc6':tagged?'2. Nf3 {[%eval 0.35,24] [%emt 0:00:03] [%clk 0:02:45]}':'2. Nf3 {+0.35/24 3s}';$('#pgnNote').textContent=value==='archive'?'Includes large encoded configuration headers. Use Compact for normal reading and sharing.':window.chrome?.webview||window.showSaveFilePicker?'Choose your folder and filename in the Save As dialog. A failed or cancelled save does not replace an existing file.':'Your browser controls the download location. The desktop app provides a Save As dialog.'};
 $('#pgnStyle').onchange=()=>{const value=$('#pgnStyle').value;for(const e of $$('[data-pgn-field]'))e.checked=value==='compact'?['eval','depth','elapsed'].includes(e.dataset.pgnField):true;update()};update();
 $('#savePgnFile').onclick=safely(async()=>{
  const values={style:$('#pgnStyle').value,perspective:$('#pgnPerspective').value,annotations:$$('[data-pgn-field]:checked').map(e=>e.dataset.pgnField)};
  const query=new URLSearchParams({...values,annotations:values.annotations.join(',')});
  const name=(state.snapshot?.name||'tournament').replace(/[<>:"/\\|?*\x00-\x1f]/g,'_').slice(0,100)+'-'+values.style+'.pgn';
  const status=$('#pgnSaveStatus');status.textContent='Choose a location, then saving will begin…';
  let result;try{result=await savePgn(`/api/export/${tid}/pgn?${query}`,name)}catch(e){status.textContent='Save failed. The selected file was not replaced.';throw e}
  if(result.cancelled){status.textContent='Save cancelled. No file was changed.';return}
  displayPrefs.pgnExport=values;await persistDisplay();
  status.textContent=result.download?'Download requested. Check your browser’s download location.':'Saved '+result.path;notify(result.download?'PGN download requested.':'Saved '+result.path);
 });
}
$('#exportPgn').textContent='Export PGN…';$('#exportPgn').onclick=pgnDialog;
