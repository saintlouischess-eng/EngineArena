'use strict';
const crossButton=document.createElement('button');crossButton.id='crossTable';crossButton.textContent='Crosstable';$('#poolRatings').after(crossButton);crossButton.onclick=safely(crossDialog);
async function crossDialog(){
  if(!state.tid)return;const tid=state.tid;let row=0,column=0,total=0,generation=0,timer,selected=null;
  modal('Live crosstable','<p class="caption">Each cell shows the row engine’s score / games against the column engine. Select a cell for W–D–L, Elo and uncertainty. All values use current official results; diagonal self-play uses White’s perspective.</p><input id="crossSearch" placeholder="Search engines on both axes"><div class="pager"><span>Rows</span><button id="crossRowPrev">←</button><span id="crossRowPage"></span><button id="crossRowNext">→</button><span>Columns</span><button id="crossColumnPrev">←</button><span id="crossColumnPage"></span><button id="crossColumnNext">→</button></div><p id="crossStatus" role="status">Loading…</p><div class="table-scroll"><table id="crossGrid" class="cross-grid"></table></div><div id="crossDetail"></div>');
  const root=$('#crossStatus'),alive=()=>$('#modal').open&&$('#crossStatus')===root;
  const refresh=async()=>{
    const version=++generation;clearTimeout(timer);
    try{
      const data=await api(`tournaments/${tid}/crosstable?row=${row}&column=${column}&q=${encodeURIComponent($('#crossSearch').value)}`);
      if(!alive()||version!==generation)return;total=data.total;const cells=new Map(data.cells.map(c=>[`${c.a}:${c.b}`,c]));
      stableHtml('#crossGrid',`<thead><tr><th>Row engine ↓</th>${data.columns.map(p=>`<th title="${esc(p.name)}">#${p.slot+1}<small>${esc(p.name)}</small></th>`).join('')}</tr></thead><tbody>${data.rows.map(p=>`<tr><th>#${p.slot+1} ${esc(p.name)}</th>${data.columns.map(q=>{const c=cells.get(`${p.slot}:${q.slot}`);return `<td>${c?`<button class="subtle" data-comparison="${p.slot}:${q.slot}" aria-label="${esc(p.name)} against ${esc(q.name)}">${fmt(c.score)} / ${c.games}<small>${pct(c.score_pct)}</small></button>`:'—'}</td>`;}).join('')}</tr>`).join('')}</tbody>`);
      const detail=()=>{const c=cells.get(selected);if(!c){stableHtml('#crossDetail','');return;}const a=data.rows.find(p=>p.slot===c.a),b=data.columns.find(p=>p.slot===c.b);stableHtml('#crossDetail',`<h3>${esc(a.name)} against ${esc(b.name)}</h3><p>${c.wins}–${c.draws}–${c.losses} · score ${pct(c.score_pct)} · draws ${pct(c.draw_pct)} · Δ Elo ${fmt(c.elo)} · ${state.confidence||95}% CI ${ciText(c)} · LOS ${pct(c.los)}</p><p class="caption">${esc(c.model)} · ${state.ciMethod==='conservative'?'Conservative Hoeffding interval':'Normal-approximation interval'} · ${c.pairs??'unpaired'} ${c.pairs===null?'':'completed opening pairs'}. Fixed-sample inference assumes independent observations.</p>`);};
      $$('[data-comparison]').forEach(button=>button.onclick=()=>{selected=button.dataset.comparison;detail();});detail();
      for(const [key,start] of [['Row',row],['Column',column]]){$('#cross'+key+'Page').textContent=total?`${start+1}–${Math.min(start+20,total)} of ${total.toLocaleString()}`:'No matches';$('#cross'+key+'Prev').disabled=start===0;$('#cross'+key+'Next').disabled=start+20>=total;}
      root.textContent=`Updated ${new Date().toLocaleTimeString()} · refreshes every 2 seconds`;
    }catch(e){if(alive()&&version===generation)root.textContent=e.message;}
    if(alive()&&version===generation)timer=setTimeout(refresh,2000);
  };
  $('#crossSearch').oninput=()=>{++generation;row=column=0;clearTimeout(timer);timer=setTimeout(()=>{if(alive())refresh();},200);};
  $('#crossRowPrev').onclick=()=>{row=Math.max(0,row-20);refresh();};$('#crossRowNext').onclick=()=>{if(row+20<total){row+=20;refresh();}};
  $('#crossColumnPrev').onclick=()=>{column=Math.max(0,column-20);refresh();};$('#crossColumnNext').onclick=()=>{if(column+20<total){column+=20;refresh();}};
  await refresh();
}

let h2hGeneration=0;
async function refreshH2h(){
  if(!state.tid||state.h2hSlot===undefined)return;const tid=state.tid,slot=state.h2hSlot,version=++h2hGeneration;
  const root=$('#h2h');root.hidden=false;
  if(root.dataset.selection!==`${tid}:${slot}`){root.dataset.selection=`${tid}:${slot}`;state.h2hOffset=0;root.innerHTML='<div class="comparison-heading"><h3>Head-to-head · selected engine perspective</h3><button id="closeH2h" class="subtle">Close comparison</button></div><input id="h2hSearch" placeholder="Find an opponent"><div id="h2hResults"></div><div class="pager"><button id="h2hPrev">←</button><span id="h2hPage"></span><button id="h2hNext">→</button></div>';$('#closeH2h').onclick=()=>{delete state.h2hSlot;++h2hGeneration;root.hidden=true;root.dataset.selection='';};$('#h2hSearch').oninput=()=>{state.h2hOffset=0;refreshH2h();};}
  const result=await api(`tournaments/${tid}/h2h/${slot}?offset=${state.h2hOffset||0}&q=${encodeURIComponent($('#h2hSearch').value)}`);
  if(version!==h2hGeneration||state.tid!==tid||state.h2hSlot!==slot)return;
  stableHtml('#h2hResults',result.items.length?`<div class="table-scroll comparison-table" tabindex="0" role="region" aria-label="Head-to-head results"><table><thead><tr><th>Opponent</th><th>W–D–L</th><th>Score %</th><th>Δ Elo</th><th>${state.confidence||95}% CI</th><th>LOS %</th><th>Pairs</th></tr></thead><tbody>${result.items.map(h=>`<tr><td>${esc(h.name)}</td><td>${h.wins}–${h.draws}–${h.losses}</td><td>${pct(h.score_pct)}</td><td>${fmt(h.elo)}</td><td class="nowrap" tabindex="0" data-help="${esc(ArenaFormat.uncertainty(h,state.ciMethod))}">${ciText(h)}</td><td>${pct(h.los)}</td><td>${h.pairs===null?'Unpaired':h.pairs.toLocaleString()}</td></tr>`).join('')}</tbody></table></div>`:'<p class="caption">No matching official results.</p>');
  const offset=state.h2hOffset||0;$('#h2hPage').textContent=result.total?`${offset+1}–${Math.min(offset+50,result.total)} of ${result.total.toLocaleString()} opponents`:'0 opponents';$('#h2hPrev').disabled=offset===0;$('#h2hNext').disabled=offset+50>=result.total;
  $('#h2hPrev').onclick=safely(async()=>{state.h2hOffset=Math.max(0,offset-50);await refreshH2h();});$('#h2hNext').onclick=safely(async()=>{state.h2hOffset=offset+50;await refreshH2h();});
};
