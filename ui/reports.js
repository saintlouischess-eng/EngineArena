'use strict';
$('#exportStats').insertAdjacentHTML('afterend',ArenaI18n.h('<button id="exportStatsJson" class="subtle">JSON ↗</button>'));
$('#exportStatsJson').onclick=()=>exportUrl('json');
$('#exportPgn').insertAdjacentHTML('beforebegin',ArenaI18n.h('<button id="tournamentReport">Tournament report</button>'));
$('#tournamentReport').onclick=safely(()=>showTournamentReport());
async function showTournamentReport({all=false,technical=false,performance=false}={}){
  if(!state.tid)throw Error(ArenaI18n.t('Select a tournament first.'));const tid=state.tid;
  modal(ArenaI18n.t('Tournament report'),ArenaI18n.h`<div class="report-intro"><span>Saved-result snapshot · ${state.confidence||95}% confidence intervals${state.snapshot?.knockout?ArenaI18n.t(' · all KO matches'):''}</span><button id="refreshReport">Refresh snapshot</button></div><div class="fields"><label>Engines in report<select id="reportEngineScope" data-help="First 50 keeps a large tournament report concise. All engines includes every participant’s statistics, configuration and selected technical readouts in both exports."><option value="first" ${all?'':'selected'}>First 50 engines</option><option value="all" ${all?'selected':''}>All engines</option></select></label><label><input type="checkbox" id="reportIncludeTechnical" ${technical?'checked':''} data-help="Summarize saved move statistics for each engine, separated by time control and recorded hardware session. Reading extensive move histories can take longer. Uncheck for a shorter, faster report."> Include engine technical readouts</label><label><input type="checkbox" id="reportIncludePerformance" ${performance?'checked':''} data-help="Include saved system-wide sensor samples. These are not individual-engine CPU/GPU measurements. This changes the preview and both exports."> Include observed performance samples</label></div><p id="reportLoading" role="status">Preparing a committed result snapshot${technical?ArenaI18n.t(' and reading saved search statistics'):''}…</p>`,ArenaI18n.h('<button id="tournamentReportText" disabled>Text…</button><button id="saveTournamentReport" disabled>Save HTML report…</button>'));
  const root=$('#reportLoading');
  const reload=safely(()=>showTournamentReport({all:$('#reportEngineScope').value==='all',technical:$('#reportIncludeTechnical').checked,performance:$('#reportIncludePerformance').checked}));
  $('#refreshReport').onclick=reload;$('#reportEngineScope').onchange=reload;$('#reportIncludeTechnical').onchange=reload;
  root.insertAdjacentHTML('afterend',ArenaI18n.h('<button id="cancelReport" class="subtle">Cancel report</button>'));
  const alive=()=>$('#modal').open&&$('#reportLoading')===root;
  let job,r,finished=false;
  const cancel=async()=>{if(job&&!finished){finished=true;await fetch('/api/report-jobs/'+job.id,{method:'DELETE',headers:{'X-Arena-Token':token}}).catch(()=>{})}};
  const closed=()=>{cancel()};$('#modal').addEventListener('close',closed);
  $('#cancelReport').onclick=()=>{$('#modal').close();cancel()};
  try{
    job=await api(`tournaments/${tid}/report-jobs`,{all_engines:all,technical,confidence:state.confidence||95});
    while(alive()){
      r=await api('report-jobs/'+job.id);
      if(r.state==='complete'){finished=true;break}
      if(r.state==='failed')throw Error(r.error);
      if(r.state==='cancelled')return;
      if(r.total)root.textContent=ArenaI18n.t('Analyzing saved games: {0} / {1} ({2}%).',r.done.toLocaleString(ArenaI18n.locale),r.total.toLocaleString(ArenaI18n.locale),(100*r.done/r.total).toFixed(1));
      await new Promise(resolve=>setTimeout(resolve,500));
    }
  }catch(error){if(alive())root.textContent=ArenaI18n.t('The report could not be prepared. Resolve the error above, then choose Refresh snapshot.');throw error}
  finally{$('#modal').removeEventListener('close',closed);await cancel()}
  if(!alive())return;
  $('#cancelReport')?.remove();
  const frame=document.createElement('iframe');frame.title=ArenaI18n.t('Tournament report preview');frame.className='report-preview';frame.setAttribute('sandbox','');root.replaceWith(frame);
  let exportHtml=r.html;const refreshView=()=>{const doc=new DOMParser().parseFromString(r.html,'text/html');if(!$('#reportIncludePerformance').checked)doc.querySelectorAll('[data-report-performance]').forEach(e=>e.remove());exportHtml='<!doctype html>\n'+doc.documentElement.outerHTML;frame.srcdoc=exportHtml;delete frame.dataset.fontSize;if(typeof applyTextSizes==='function')applyTextSizes()};$('#reportIncludePerformance').onchange=refreshView;refreshView();
  $('#tournamentReportText').disabled=false;$('#tournamentReportText').onclick=()=>textExport(ArenaI18n.t('Tournament report'),()=>htmlReportText(exportHtml),{name:'tournament-report-'+tid});
  $('#saveTournamentReport').disabled=false;$('#saveTournamentReport').onclick=()=>download('engine-arena-report-'+tid+'.html',exportHtml,'text/html');
}
$('#exportPgn').insertAdjacentHTML('beforebegin',ArenaI18n.h('<button id="openingReport">Opening & color results</button>'));
$('#openingReport').onclick=safely(()=>{if(!state.tid)throw Error(ArenaI18n.t('Select a tournament first.'));return showOpeningReport(state.tid);});
async function showOpeningReport(tid){
  let offset=0,peopleOffset=0,peopleTotal=0,total=0,chosen={slot:-1,name:'White side across the tournament'},revision=0,peopleRevision=0,timer,searchTimer;
  modal(ArenaI18n.t('Opening & color results'),ArenaI18n.h`<div class="fields"><label class="report-picker">Participant search<input id="reportSearch" placeholder="Find an engine profile…"></label><label class="report-picker">Score perspective<select id="reportProfile"><option value="-1">White side across the tournament</option></select></label></div><div class="pager report-people"><button id="peoplePrev">← Profiles</button><span id="peoplePage"></span><button id="peopleNext">Profiles →</button></div><p class="caption" id="reportStatus" role="status">Loading official results…</p><div id="reportTotals"></div><div class="table-scroll"><table><thead><tr><th>COLOR</th><th>GAMES</th><th>W–D–L</th><th>SCORE</th><th>DRAW</th></tr></thead><tbody id="reportColors"></tbody></table></div><div class="section-label">RECORDED OPENINGS</div><div class="table-scroll"><table><thead><tr><th>OPENING</th><th>GAMES</th><th>W–D–L</th><th>SCORE</th><th>DRAW</th><th>COMPLETE PAIRS</th></tr></thead><tbody id="reportOpenings"></tbody></table></div><div class="pager"><button id="openingPrev">←</button><span id="openingPage"></span><button id="openingNext">→</button></div><p class="caption">Only current official results count. Diagnostic attempts and invalidated rounds are excluded. Color subsets are descriptive; they do not form independent opening pairs. In self-play, each game is counted once from White’s perspective.</p>`,ArenaI18n.h`<button id="downloadOpeningCsv">Export all openings · CSV</button><button id="downloadOpeningText">All openings · Text…</button>`);
  const root=$('#reportStatus'),alive=()=>$('#modal').open&&$('#reportStatus')===root;
  const values=s=>ArenaI18n.h`<td>${s.games.toLocaleString(ArenaI18n.locale)}</td><td class="nowrap">${s.wins}–${s.draws}–${s.losses}</td><td>${pct(s.score_pct)}</td><td>${pct(s.draw_pct)}</td>`;
  const refresh=async()=>{
    const current=++revision;clearTimeout(timer);root.textContent=ArenaI18n.t('Updating official results…');
    try{
      const r=await api(`tournaments/${tid}/openings?slot=${chosen.slot}&offset=${offset}`);
      if(!alive()||current!==revision)return;total=r.total_openings;
      root.textContent=ArenaI18n.m`${r.perspective} · updates every 2 seconds · updated ${new Date().toLocaleTimeString(ArenaI18n.locale)}`;
      $('#reportTotals').innerHTML=ArenaI18n.h`<strong>${esc(r.perspective)}</strong><p>${r.summary.games.toLocaleString(ArenaI18n.locale)} official games · ${r.summary.wins} wins / ${r.summary.draws} draws / ${r.summary.losses} losses · score ${pct(r.summary.score_pct)}</p>`;
      stableHtml('#reportColors',r.colors.map(c=>ArenaI18n.h`<tr><td>${c.color}</td>${values(c)}</tr>`).join(''));
      stableHtml('#reportOpenings',r.openings.map(o=>ArenaI18n.h`<tr><td><b>${Number(o.opening_index)+1}. ${esc(o.name)}</b><details><summary>Starting FEN</summary><code class="report-fen">${esc(o.fen)}</code></details></td>${values(o)}<td>${o.complete_pairs===null?ArenaI18n.t('Unpaired'):o.complete_pairs.toLocaleString(ArenaI18n.locale)}</td></tr>`).join(''));
      $('#openingPage').textContent=total?ArenaI18n.m`${offset+1}–${Math.min(offset+50,total)} of ${total.toLocaleString(ArenaI18n.locale)} openings`:ArenaI18n.t('No official opening results yet');
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
      $('#reportProfile').innerHTML=choices.map(p=>ArenaI18n.h`<option value="${p.slot}" ${p.slot===chosen.slot?'selected':''}>${p.slot>=0?'#'+(p.slot+1)+' ':''}${esc(p.name)}</option>`).join('');
      $('#peoplePage').textContent=r.total?ArenaI18n.m`${peopleOffset+1}–${Math.min(peopleOffset+50,r.total)} of ${r.total.toLocaleString(ArenaI18n.locale)} matching profiles`:ArenaI18n.t('No matching profiles');
      $('#peoplePrev').disabled=peopleOffset===0;$('#peopleNext').disabled=peopleOffset+50>=peopleTotal;
      $('#reportProfile').onchange=()=>{const slot=Number($('#reportProfile').value);chosen=choices.find(p=>p.slot===slot);offset=0;refresh();};
    }catch(e){if(alive()&&current===peopleRevision)root.textContent=e.message;}
  };
  $('#reportSearch').oninput=()=>{++peopleRevision;clearTimeout(searchTimer);peopleOffset=0;searchTimer=setTimeout(()=>{if(alive())people();},180);};
  $('#peoplePrev').onclick=()=>{peopleOffset=Math.max(0,peopleOffset-50);people();};$('#peopleNext').onclick=()=>{if(peopleOffset+50<peopleTotal){peopleOffset+=50;people();}};
  $('#openingPrev').onclick=()=>{offset=Math.max(0,offset-50);refresh();};$('#openingNext').onclick=()=>{if(offset+50<total){offset+=50;refresh();}};
  $('#downloadOpeningCsv').onclick=()=>window.open(`/api/tournaments/${tid}/openings?slot=${chosen.slot}&export=csv&token=${encodeURIComponent(token)}`,'_blank');
  $('#downloadOpeningText').onclick=safely(()=>{const slot=chosen.slot;return textExport(ArenaI18n.t('Opening and color results'),async()=>ArenaText.openings(await api(`tournaments/${tid}/openings?slot=${slot}&export=json`)))});
  await people();if(alive())await refresh();
}
