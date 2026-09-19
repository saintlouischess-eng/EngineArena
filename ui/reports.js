'use strict';
$('#exportStats').insertAdjacentHTML('afterend','<button id="exportStatsJson" class="subtle">JSON ↗</button>');
$('#exportStatsJson').onclick=()=>exportUrl('json');
$('#exportPgn').insertAdjacentHTML('beforebegin','<button id="tournamentReport">Tournament report</button>');
$('#tournamentReport').onclick=safely(async()=>{
  if(!state.tid)throw Error('Select a tournament first.');const tid=state.tid;
  modal('Tournament report',`<div class="report-intro"><span>Saved-result snapshot · ${state.confidence||95}% confidence intervals · first 50 participants</span><button id="refreshReport">Refresh snapshot</button></div><p id="reportLoading" role="status">Preparing a committed result snapshot…</p>`,'<button id="saveTournamentReport" disabled>Save HTML report…</button>');
  const root=$('#reportLoading');$('#refreshReport').onclick=()=>$('#tournamentReport').click();
  let r;try{r=await api(`tournaments/${tid}/report`)}catch(error){if($('#reportLoading')===root)root.textContent='The report could not be prepared. Resolve the error above, then choose Refresh snapshot.';throw error}if(!$('#modal').open||$('#reportLoading')!==root)return;
  const frame=document.createElement('iframe');frame.title='Tournament report preview';frame.className='report-preview';frame.setAttribute('sandbox','');frame.srcdoc=r.html;root.replaceWith(frame);
  $('#saveTournamentReport').disabled=false;$('#saveTournamentReport').onclick=()=>download('engine-arena-report-'+tid+'.html',r.html,'text/html');
});
$('#exportPgn').insertAdjacentHTML('beforebegin','<button id="openingReport">Opening & color results</button>');
$('#openingReport').onclick=safely(()=>{if(!state.tid)throw Error('Select a tournament first.');return showOpeningReport(state.tid);});
async function showOpeningReport(tid){
  let offset=0,peopleOffset=0,peopleTotal=0,total=0,chosen={slot:-1,name:'White side across the tournament'},revision=0,peopleRevision=0,timer,searchTimer;
  modal('Opening & color results',`<div class="fields"><label class="report-picker">Participant search<input id="reportSearch" placeholder="Find an engine profile…"></label><label class="report-picker">Score perspective<select id="reportProfile"><option value="-1">White side across the tournament</option></select></label></div><div class="pager report-people"><button id="peoplePrev">← Profiles</button><span id="peoplePage"></span><button id="peopleNext">Profiles →</button></div><p class="caption" id="reportStatus" role="status">Loading official results…</p><div id="reportTotals"></div><div class="table-scroll"><table><thead><tr><th>COLOR</th><th>GAMES</th><th>W–D–L</th><th>SCORE</th><th>DRAW</th></tr></thead><tbody id="reportColors"></tbody></table></div><div class="section-label">RECORDED OPENINGS</div><div class="table-scroll"><table><thead><tr><th>OPENING</th><th>GAMES</th><th>W–D–L</th><th>SCORE</th><th>DRAW</th><th>COMPLETE PAIRS</th></tr></thead><tbody id="reportOpenings"></tbody></table></div><div class="pager"><button id="openingPrev">←</button><span id="openingPage"></span><button id="openingNext">→</button></div><p class="caption">Only current official results count. Diagnostic attempts and invalidated rounds are excluded. Color subsets are descriptive; they do not form independent opening pairs. In self-play, each game is counted once from White’s perspective.</p>`,`<button id="downloadOpeningCsv">Export all openings · CSV</button>`);
  const root=$('#reportStatus'),alive=()=>$('#modal').open&&$('#reportStatus')===root;
  const values=s=>`<td>${s.games.toLocaleString()}</td><td class="nowrap">${s.wins}–${s.draws}–${s.losses}</td><td>${pct(s.score_pct)}</td><td>${pct(s.draw_pct)}</td>`;
  const refresh=async()=>{
    const current=++revision;clearTimeout(timer);root.textContent='Updating official results…';
    try{
      const r=await api(`tournaments/${tid}/openings?slot=${chosen.slot}&offset=${offset}`);
      if(!alive()||current!==revision)return;total=r.total_openings;
      root.textContent=`${r.perspective} · updates every 2 seconds · updated ${new Date().toLocaleTimeString()}`;
      $('#reportTotals').innerHTML=`<strong>${esc(r.perspective)}</strong><p>${r.summary.games.toLocaleString()} official games · ${r.summary.wins} wins / ${r.summary.draws} draws / ${r.summary.losses} losses · score ${pct(r.summary.score_pct)}</p>`;
      stableHtml('#reportColors',r.colors.map(c=>`<tr><td>${c.color}</td>${values(c)}</tr>`).join(''));
      stableHtml('#reportOpenings',r.openings.map(o=>`<tr><td><b>${Number(o.opening_index)+1}. ${esc(o.name)}</b><details><summary>Starting FEN</summary><code class="report-fen">${esc(o.fen)}</code></details></td>${values(o)}<td>${o.complete_pairs===null?'Unpaired':o.complete_pairs.toLocaleString()}</td></tr>`).join(''));
      $('#openingPage').textContent=total?`${offset+1}–${Math.min(offset+50,total)} of ${total.toLocaleString()} openings`:'No official opening results yet';
      $('#openingPrev').disabled=offset===0;$('#openingNext').disabled=offset+50>=total;
    }catch(e){if(alive()&&current===revision)root.textContent=e.message;}
    if(alive()&&current===revision)timer=setTimeout(refresh,2000);
  };
  const people=async()=>{
    const current=++peopleRevision;
    try{
      const r=await api(`tournaments/${tid}/participants?q=${encodeURIComponent($('#reportSearch').value)}&offset=${peopleOffset}`);
      if(!alive()||current!==peopleRevision)return;peopleTotal=r.total;
      const choices=[{slot:-1,name:'White side across the tournament'},...(chosen.slot>=0?[chosen]:[]),...r.items.filter(p=>p.slot!==chosen.slot)];
      $('#reportProfile').innerHTML=choices.map(p=>`<option value="${p.slot}" ${p.slot===chosen.slot?'selected':''}>${p.slot>=0?'#'+(p.slot+1)+' ':''}${esc(p.name)}</option>`).join('');
      $('#peoplePage').textContent=r.total?`${peopleOffset+1}–${Math.min(peopleOffset+50,r.total)} of ${r.total.toLocaleString()} matching profiles`:'No matching profiles';
      $('#peoplePrev').disabled=peopleOffset===0;$('#peopleNext').disabled=peopleOffset+50>=peopleTotal;
      $('#reportProfile').onchange=()=>{const slot=Number($('#reportProfile').value);chosen=choices.find(p=>p.slot===slot);offset=0;refresh();};
    }catch(e){if(alive()&&current===peopleRevision)root.textContent=e.message;}
  };
  $('#reportSearch').oninput=()=>{++peopleRevision;clearTimeout(searchTimer);peopleOffset=0;searchTimer=setTimeout(()=>{if(alive())people();},180);};
  $('#peoplePrev').onclick=()=>{peopleOffset=Math.max(0,peopleOffset-50);people();};$('#peopleNext').onclick=()=>{if(peopleOffset+50<peopleTotal){peopleOffset+=50;people();}};
  $('#openingPrev').onclick=()=>{offset=Math.max(0,offset-50);refresh();};$('#openingNext').onclick=()=>{if(offset+50<total){offset+=50;refresh();}};
  $('#downloadOpeningCsv').onclick=()=>window.open(`/api/tournaments/${tid}/openings?slot=${chosen.slot}&export=csv&token=${encodeURIComponent(token)}`,'_blank');
  await people();if(alive())await refresh();
}
