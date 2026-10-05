'use strict';
// One review/copy/save workflow for numerical reports and other text exports.
async function textExport(title,producer,{name=title,paths=false}={}){
 modal(title+ArenaI18n.t(' · Text export'),ArenaI18n.h`<p class="caption">A fixed snapshot for posting or personal use. Tables align in a monospaced font. Select a code-block format when posting to a forum.</p><div class="text-export-tools"><label for="textCopyFormat">Copy formatting</label><select id="textCopyFormat" data-help="Plain text works in text editors. Forum adds [code] tags; Markdown adds a fenced code block. Save TXT always saves plain text."><option value="plain">Plain text</option><option value="forum">Forum [code] block</option><option value="markdown">Markdown code block</option></select>${paths?ArenaI18n.h('<label><input id="textIncludePaths" type="checkbox"> Include local file paths and launch arguments</label>'):''}</div><p id="textExportStatus" role="status">Preparing text…</p><textarea id="textExportPreview" class="text-export-preview" aria-label="Text export preview" data-help="Read-only snapshot. Scroll sideways for wide tables, or select and copy a portion. Save TXT keeps every row." readonly spellcheck="false" wrap="off"></textarea>`,ArenaI18n.h`<button id="copyTextExport" data-help="Copy the preview using the selected plain text or forum formatting." disabled>Copy text</button><button id="saveTextExport" data-help="Save the full snapshot as a UTF-8 text file. The desktop app lets you choose the folder and filename. Forum wrappers are excluded from the file." disabled>Save TXT as…</button>`);
 const preview=$('#textExportPreview'),status=$('#textExportStatus'),copy=$('#copyTextExport'),save=$('#saveTextExport');
 const alive=()=>$('#modal').open&&$('#textExportPreview')===preview;let plain='',generation=0;
 const update=async()=>{const version=++generation;copy.disabled=save.disabled=true;status.textContent=ArenaI18n.t('Preparing text…');try{const text=await producer($('#textIncludePaths')?.checked===true);if(!alive()||version!==generation)return;plain=text.replace(/\r\n?/g,'\n');preview.value=ArenaText.codeBlock(plain,$('#textCopyFormat').value);copy.disabled=save.disabled=false;status.textContent=plain.split('\n').length.toLocaleString(ArenaI18n.locale)+ArenaI18n.t(' lines · snapshot ready. Review before copying or saving.')}catch(error){if(alive()&&version===generation)status.textContent=ArenaI18n.t('Could not prepare text: ')+error.message}};
 $('#textCopyFormat').onchange=()=>{preview.value=ArenaText.codeBlock(plain,$('#textCopyFormat').value)};
 if(paths)$('#textIncludePaths').onchange=update;
 copy.onclick=safely(async()=>{try{await navigator.clipboard.writeText(preview.value);if(alive())status.textContent=ArenaI18n.t('Copied to clipboard.')}catch{if(alive()){preview.focus();preview.select();status.textContent=ArenaI18n.t('Automatic clipboard access is unavailable. The text is selected; press Ctrl+C to copy.')}}});
 save.onclick=()=>{const filename=name.replace(/[<>:"/\\|?*\x00-\x1f]/g,'_').slice(0,120)+'.txt';download(filename,plain.replaceAll('\n','\r\n'),'text/plain;charset=utf-8');status.textContent=window.chrome?.webview?ArenaI18n.t('Save requested. Choose a filename in the Save As dialog.'):ArenaI18n.t('Text download requested. Check your browser downloads.')};
 await update();
}

function htmlReportText(html){
 const doc=new DOMParser().parseFromString(html,'text/html'),T=ArenaText,blocks=[];
 // Include expandable engine details; omit only raw settings/evidence JSON.
 function visit(el){
  if(['SCRIPT','STYLE','NAV'].includes(el.tagName)||el.tagName==='DETAILS'&&!el.hasAttribute('data-report-details'))return;
  if(el.tagName==='TABLE'){
   if(el.hasAttribute('data-report-crosstable')){
    const rows=[...el.rows].map(r=>[...r.cells].map(c=>c.textContent));
    for(let start=1;start<rows[0].length;start+=4){
     const part=rows.map(r=>[r[0],...r.slice(start,start+4)]);
     blocks.push(T.table(part[0],part.slice(1),{limits:[32,15,15,15,15],right:[1,2,3,4]}));
    }return;
   }
   if(el.hasAttribute('data-report-tech-overview')){
    const rows=[...el.rows].map(r=>[...r.cells].map(c=>c.textContent));
    blocks.push(T.table(rows[0],rows.slice(1),{limits:[32,12,10,12,14,10],right:[1,2,3,4,5]}));return;
   }
   const rows=[...el.rows].map(r=>[...r.cells].map(c=>c.textContent));if(rows.length){const right=rows[0].map((_,i)=>i).filter(i=>rows.slice(1).every(r=>/^[+−\-]?[\d,.]+%?$/.test(T.clean(r[i]))));let limits=rows[0].length===2?[30,82]:[];if(rows[0][0]===ArenaI18n.t('Stage'))limits=[15,12,10,36,18];if(rows[0][2]===ArenaI18n.t('Δ Elo vs own opponents'))limits=[32,8,12,23,23,7];if(rows[0][0]===ArenaI18n.t('Seed'))limits=[5,32,15,8,6,12,11,8,8];if(rows[0][0]===ArenaI18n.t('Search measurement'))limits=[32,18,18,18,18];blocks.push(T.table(rows[0],rows.slice(1),{right,limits}))}return;
  }
  if(el.matches('.metrics')){blocks.push(T.table([ArenaI18n.t('Summary'),ArenaI18n.t('Value')],[...el.children].map(e=>[e.querySelector('small')?.textContent||ArenaI18n.t('Value'),[...e.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent).join('')]),{limits:[48,48]}));return}
  if(/^H[1-6]$/.test(el.tagName)||el.tagName==='SUMMARY'){const text=T.clean(el.textContent);blocks.push(text+'\n'+(el.tagName==='H1'?'=':'-').repeat(Math.min(100,T.width(text))));return}
  if(el.tagName==='P'){const text=el.innerHTML.replace(/<br\s*\/?\s*>/gi,'\n');const p=doc.createElement('p');p.innerHTML=text;blocks.push(p.textContent.split('\n').map(s=>T.wrap(s).join('\n')).join('\n'));return}
  for(const child of el.children)visit(child);
 }
 visit(doc.body);return blocks.filter(Boolean).join('\n\n')+'\n';
}

$('#exportStatsJson').after(Object.assign(document.createElement('button'),{id:'exportStatsText',className:'subtle',textContent:ArenaI18n.t('Text…')}));
$('#exportStatsText').dataset.help=ArenaI18n.t('Preview, copy or save all standings as an aligned text table, using the selected sort order and confidence interval.');
$('#exportStatsText').onclick=safely(()=>{if(!state.tid)throw Error(ArenaI18n.t('Select a tournament first.'));const tid=state.tid,query=statisticsQuery(),method=state.ciMethod||'normal';return textExport(ArenaI18n.t('Standings'),async()=>ArenaText.standings(await api(`export/${tid}/json?${query}`),method))});
$('#exportEngines').after(Object.assign(document.createElement('button'),{id:'exportEnginesText',textContent:ArenaI18n.t('Text profiles…')}));
$('#exportEnginesText').dataset.help=ArenaI18n.t('Create a readable engine configuration list. Local paths and file-related options are optional for sharing.');
$('#exportEnginesText').onclick=safely(()=>{const profiles=api('profiles?limit='+Math.max(1,state.libraryTotal));return textExport(ArenaI18n.t('Engine profiles'),async paths=>ArenaText.profiles((await profiles).items,paths),{paths:true})});

function exportGraphText(id){const data=graphData.get(id);if(!data){notify(ArenaI18n.t('No graph samples available yet.'),true);return}const frozen=structuredClone(data);return textExport(data.title,()=>ArenaText.graph(frozen))}

function comparisonText(title,data,context,method,confidence){return ArenaText.report(title,[context,ArenaText.statsTable(data,confidence,method),ArenaText.wrap(ArenaText.modelNote).join('\n')])}

function crosstableText(data,context){
 const T=ArenaText,cells=new Map(data.cells.map(c=>[c.a+':'+c.b,c])),legend=[...new Map([...data.rows,...data.columns].map(p=>[p.slot,p])).values()];
 return T.report(ArenaI18n.t('Crosstable'),[
  context,ArenaI18n.t('Scope: current row/column page and search filter. Each cell is row-engine points / games.\nDiagonal self-play is from White’s perspective; N/A means no completed comparison.'),
  T.table([ArenaI18n.t('Engine'),...data.columns.map(p=>'#'+(p.slot+1))],data.rows.map(p=>['#'+(p.slot+1),...data.columns.map(q=>{const c=cells.get(p.slot+':'+q.slot);return c?T.number(c.score)+' / '+T.number(c.games,0):'N/A'})]),{right:data.columns.map((_,i)=>i+1)}),
  T.section(ArenaI18n.t('Participant key'),T.table(['#',ArenaI18n.t('Engine')],legend.map(p=>[p.slot+1,p.name]),{limits:[6,90]}))
 ]);
}
