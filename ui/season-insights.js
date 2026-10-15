'use strict';
// Presentation only. Every number comes from the same official aggregate snapshot.
const SeasonDesk={id:null,tab:'overview',season:null,follow:true,offset:0,identity:null,careerOffset:0,rivalOffset:0,search:'',entryOffsets:{},generation:0};
const siText=k=>ArenaI18n.t(k),siNum=v=>ArenaText.number(v,Number.isInteger(v)?0:1);
const siName=p=>`<button class="si-engine" data-career="${esc(p.identity)}">${esc(p.name)}</button>`;
const siStageButton=s=>`<button data-insight-stage="${s.tid}">${siText('Open stage')}</button>`;
const siTable=(heads,rows)=>`<div class="table-scroll"><table><thead><tr>${heads.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
const siLabel=k=>siText({qualification:'Qualification',division:'Divisions',championship:'Championship final',playoff:'Placement playoff',completed:'Completed'}[k]||k);
const siNote=()=>siText('Career totals are descriptive. Versions, opponents and time controls can differ; no combined Elo is inferred.');

function insightShell(e){
 if($('#eventInsights'))return;
 const summary=$('#eventSummary'),records=document.createElement('div');records.id='eventRecords';
 for(let n=summary.nextSibling;n;){const next=n.nextSibling;records.append(n);n=next}summary.after(records);
 summary.insertAdjacentHTML('afterend',`<div id="eventInsights"><div class="si-toolbar"><div class="si-tabs" role="tablist" aria-label="${siText('Competition views')}">${[['overview','Season overview'],['careers','Engine careers'],['summary','Season summary'],['stages','Stages & records']].map(([key,label])=>`<button role="tab" id="siTab-${key}" data-si-tab="${key}" aria-controls="siPanel-${key}">${siText(label)}</button>`).join('')}</div><label id="siSeasonField">${siText('Season')} <select id="siSeason" aria-label="${siText('Season')}"></select></label></div><p id="siStatus" role="status"></p><div id="siPanel-overview" role="tabpanel" aria-labelledby="siTab-overview"></div><div id="siPanel-careers" role="tabpanel" aria-labelledby="siTab-careers" hidden></div><div id="siPanel-summary" role="tabpanel" aria-labelledby="siTab-summary" hidden></div></div>`);
 records.setAttribute('role','tabpanel');records.setAttribute('aria-labelledby','siTab-stages');records.id='siPanel-stages';
 if(SeasonDesk.id!==e.id)Object.assign(SeasonDesk,{id:e.id,tab:'overview',season:null,follow:true,offset:0,identity:null,careerOffset:0,rivalOffset:0,search:'',entryOffsets:{}});
 $('#siSeason').onchange=()=>{SeasonDesk.follow=$('#siSeason').value==='latest';SeasonDesk.season=SeasonDesk.follow?null:Number($('#siSeason').value);SeasonDesk.offset=0;SeasonDesk.entryOffsets={};void loadInsights()};
 $('#eventRefresh').addEventListener('click',()=>{if(SeasonDesk.tab==='careers')void loadInsights()});
 $$('[data-si-tab]').forEach(b=>{b.onclick=()=>{SeasonDesk.tab=b.dataset.siTab;switchInsightTab();void loadInsights()};b.onkeydown=ev=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(ev.key))return;ev.preventDefault();const tabs=$$('[data-si-tab]'),i=tabs.indexOf(b),next=ev.key==='Home'?0:ev.key==='End'?tabs.length-1:(i+(ev.key==='ArrowRight'?1:tabs.length-1))%tabs.length;tabs[next].focus();tabs[next].click()}});
 switchInsightTab();
}
function switchInsightTab(){
 for(const b of $$('[data-si-tab]')){const selected=b.dataset.siTab===SeasonDesk.tab;b.setAttribute('aria-selected',String(selected));b.tabIndex=selected?0:-1;$('#siPanel-'+b.dataset.siTab).hidden=!selected}
 $('#siSeasonField').hidden=!['overview','summary'].includes(SeasonDesk.tab);
 $('#eventSummary').hidden=SeasonDesk.tab!=='stages';
 $('#siStatus').textContent='';
}
async function loadInsights(){
 const host=$('#eventInsights');if(!host||!$('#modal').open||SeasonDesk.tab==='stages')return;
 // A newer navigation invalidates old replies without losing focused controls.
 const generation=++SeasonDesk.generation,id=SeasonDesk.id,tab=SeasonDesk.tab;
 const alive=()=>generation===SeasonDesk.generation&&host===$('#eventInsights')&&$('#modal').open;
 try{
  if(tab==='careers'){
   const query=SeasonDesk.identity?`&identity=${encodeURIComponent(SeasonDesk.identity)}&offset=${SeasonDesk.careerOffset}&rival_offset=${SeasonDesk.rivalOffset}`:`&search=${encodeURIComponent(SeasonDesk.search)}&offset=${SeasonDesk.careerOffset}`;
   const data=await api(`events/${id}?view=careers${query}`);if(!alive())return;renderCareers(data);return;
  }
  const data=await api(`events/${id}?view=insights&offset=${SeasonDesk.offset}${!SeasonDesk.follow&&SeasonDesk.season?'&season='+SeasonDesk.season:''}${tab==='summary'?'&export=1':'&entry_offsets='+encodeURIComponent(JSON.stringify(SeasonDesk.entryOffsets))}`);if(!alive())return;
  SeasonDesk.season=data.season;
  stableHtml('#siSeason',`<option value="latest">${siText('Latest')}</option>`+Array.from({length:data.seasons},(_,i)=>`<option value="${i+1}">${i+1}</option>`).join(''));$('#siSeason').value=SeasonDesk.follow?'latest':data.season;
  if(tab==='summary')renderSeasonSummary(data);else renderSeasonOverview(data);
  bindInsights();
 }catch(error){if(alive())$('#siStatus').textContent=error.message}
}
function bindInsights(){
 $$('#eventInsights [data-career]').forEach(b=>b.onclick=()=>{SeasonDesk.identity=b.dataset.career;SeasonDesk.careerOffset=SeasonDesk.rivalOffset=0;SeasonDesk.tab='careers';switchInsightTab();void loadInsights()});
 $$('#eventInsights [data-insight-stage]').forEach(b=>b.onclick=safely(async()=>{$('#modal').close();state.tid=b.dataset.insightStage;await loadTournaments();view('overview');await refreshTournament()}));
}
function renderSeasonOverview(d,prefix=''){
 const host=$('#siPanel-overview'),focus=host.contains(document.activeElement)?document.activeElement.id:null;
 const scrolls=new Map([...host.querySelectorAll('[data-entry-table]')].map(el=>[el.dataset.entryTable,{offset:el.dataset.offset,top:el.scrollTop,left:el.scrollLeft}]));
 const hero=d.champion?`<span class="si-eyebrow">${siText('Season champion')}</span><h2>${esc(d.champion.name)}</h2>`:`<span class="si-eyebrow">${siText('Championship race')}</span><h2>${siLabel(d.phase)}</h2>`;
 const f=d.final,m=f?.deciding_match;
 const match=m&&f.players.length>2?`<div class="si-match"><h4>${siText('Final match')}</h4><p class="event-match-score">${esc(m.a_name)} <b>${siNum(m.a_score)} — ${siNum(m.b_score)}</b> ${esc(m.b_name)}</p><p class="caption">${m.games} ${siText('Games')} · ${m.tiebreaks} ${siText('Tiebreaks')}</p></div>`:'';
 const final=f?`<section class="si-final"><div class="si-section-title"><h3>${siText(f.players.length>2?'Championship standings':'Championship final')}</h3>${siStageButton(f)}</div>${match}${f.players.length>2?siTable([siText('Place'),siText('Engine'),siText('Points'),'W–D–L'],f.players.map(p=>`<tr><td>${esc(ArenaI18n.message(String(p.rank)))}</td><td>${siName(p)}</td><td>${siNum(p.points)}</td><td>${p.wins}–${p.draws}–${p.losses}</td></tr>`)):`<div class="si-score">${f.players.map(p=>`<div>${siName(p)}<strong>${siNum(p.points)}</strong><small>${p.wins} W · ${p.draws} D · ${p.losses} L</small></div>`).join('<span>—</span>')}</div>`}<p class="caption">${siText(f.players.length>2?'Championship stage total':'Official / scheduled')}: ${f.games} / ${f.scheduled} · ${ArenaI18n.message(f.state)}</p>${f.players.length>2?`<p class="caption">${siText('Points and W–D–L include every game in this stage. Knockout placement follows match results, not total game points.')}</p>`:''}</section>`:'';
 const stages=d.stages.filter(s=>!['championship','playoff'].includes(s.role)).map(s=>`<section class="si-division" data-division="${s.tid}"><div class="si-section-title"><div><span class="si-eyebrow">${s.role==='circuit'?siText({swiss:'Swiss',round_robin:'Round robin',knockout:'Knockout (KO)'}[s.format]||s.format):siLabel(s.role)}</span><h3>${esc(s.label)}</h3></div>${siStageButton(s)}</div><div class="si-progress"><progress max="${Math.max(1,s.total)}" value="${s.official}"></progress><span>${s.official} / ${s.total} · ${esc(ArenaI18n.message(s.state))}</span></div>${siTable(['#',siText('Engine'),siText('Games'),siText('Points'),siText('Outcome')],s.entries.map(p=>`<tr><td>${p.rank}</td><td>${siName(p)}</td><td>${p.games}</td><td class="si-points">${siNum(p.points)}</td><td><span class="si-outcome ${['Promoted','Championship place'].includes(p.outcome)?'si-up':p.outcome==='Relegated'?'si-down':''}">${p.provisional&&p.outcome?siText('Provisional')+' · ':''}${p.outcome?siText(p.outcome):'—'}</span></td></tr>`)).replace('<div class="table-scroll">',`<div class="table-scroll si-entry-table" tabindex="0" role="region" aria-label="${esc(s.label)}" data-entry-table="${s.tid}" data-offset="${s.entry_offset}">`)}<div class="pager si-entry-pager" aria-label="${esc(s.label)}"><button id="siEntryPrev-${s.tid}" data-entry-stage="${s.tid}" data-entry-offset="${Math.max(0,s.entry_offset-s.entry_limit)}" ${s.entry_offset?'':'disabled'} aria-label="${esc(s.label)} · ${siText('Previous')}">${siText('Previous')}</button><span>${siText('Participants')}: ${Math.min(s.entry_offset+1,s.field)}–${s.entry_offset+s.entries.length} / ${s.field}</span><button id="siEntryNext-${s.tid}" data-entry-stage="${s.tid}" data-entry-offset="${s.entry_offset+s.entry_limit}" ${s.more?'':'disabled'} aria-label="${esc(s.label)} · ${siText('Next')}">${siText('Next')}</button></div></section>`).join('');
 const playoffRows=d.stages.filter(s=>s.role==='playoff');
 const playoffs=playoffRows.length?`<section class="si-card si-playoffs"><h3>${siText('Placement playoff history')}</h3><p class="caption">${siText('Separate tiebreak tournaments; their points do not change the original group standings.')}</p>${siTable([siText('Stage'),siText('Engine'),siText('Points'),siText('Games'),siText('Actions')],playoffRows.map(s=>`<tr><td>${esc(s.label)}<small>${esc(ArenaI18n.message(s.state))}</small></td><td>${s.entries.map(p=>`<div>${siName(p)}</div>`).join('')}</td><td>${s.entries.map(p=>`<div>${siNum(p.points)}</div>`).join('')}</td><td>${s.official} / ${s.total}</td><td>${siStageButton(s)}</td></tr>`))}</section>`:'';
 const history=d.champions.slice(-10).map(c=>`<li><span>${siText('Season')} ${c.season}</span>${c.identity?siName(c):esc(c.name)}</li>`).join('');
 const movements=d.movements.map(m=>`<li><strong>${esc(m.name)}</strong><span>${siText(m.outcome)} → ${esc(d.division_names[m.to]||'')}</span></li>`).join('');
 stableHtml('#siPanel-overview',prefix+`<header class="si-hero"><div>${hero}<p>${esc(d.name)} · ${siText('Season')} ${d.season} / ${d.seasons}</p></div><span class="si-status">${siText(d.complete?'Completed':d.stages.length?'In progress':'Not started')}</span></header><div class="si-metrics"><div><small>${siText('Season official games')}</small><strong>${siNum(d.official)}</strong></div><div><small>${siText('Event official games')}</small><strong>${siNum(d.all_official)}</strong></div><div><small>${siText('Active games')}</small><strong>${siNum(d.active)}</strong></div><div><small>${siText('CPU thread budget')}</small><strong>${d.resources.cpu_budget??'—'}</strong></div></div>${d.admission?seasonAdmissionSummary(d.admission,true):''}${final}<div class="si-layout"><div><div class="si-section-title"><h3>${siText('Division races')}</h3><span class="caption">${siText('Season')} ${d.season}</span></div><p class="caption">${siText(d.complete?'Advancement and final placements are recorded.':'Live places are provisional until advancement is recorded. Tied boundaries may need playoffs.')}</p>${stages}${playoffs}${!d.stage_count?`<p>${siText('No stages have been created for this season yet.')}</p>`:''}<div class="pager"><button id="siPrev">${siText('Previous')}</button><span>${Math.min(d.offset+1,d.stage_count)}–${Math.min(d.offset+8,d.stage_count)} / ${d.stage_count}</span><button id="siNext">${siText('Next')}</button></div></div><div class="si-sidebar"><section class="si-card"><h3>${siText('Next steps')}</h3><p class="caption">${siText('Current event')}</p>${d.upcoming.length?`<ol>${d.upcoming.map(v=>`<li>${esc(ArenaI18n.message(v))}</li>`).join('')}</ol>`:`<p>${siText(d.state==='completed'?'All scheduled seasons completed.':'Open a stage to follow play.')}</p>`}</section>${d.kind==='circuit'?'':`<section class="si-card"><h3>${siText('Promotion & relegation')}</h3><ul class="si-list">${movements||`<li>${siText('No recorded movements yet.')}</li>`}</ul></section>`}<section class="si-card"><h3>${siText('Champions')}</h3><ul class="si-list">${history||`<li>${siText('No champion yet.')}</li>`}</ul>${d.champions.length>10?`<p class="caption">${siText('Latest 10 seasons')}</p>`:''}</section></div></div>`);
 for(const el of host.querySelectorAll('[data-entry-table]')){const saved=scrolls.get(el.dataset.entryTable);if(saved&&saved.offset===el.dataset.offset){el.scrollTop=saved.top;el.scrollLeft=saved.left}}
 if(focus&&document.activeElement.id!==focus)document.getElementById(focus)?.focus({preventScroll:true});
 $$('[data-entry-stage]').forEach(b=>b.onclick=()=>{SeasonDesk.entryOffsets[b.dataset.entryStage]=Number(b.dataset.entryOffset);void loadInsights()});
 $('#siPrev').disabled=!d.offset;$('#siNext').disabled=d.offset+8>=d.stage_count;
 $('#siPrev').onclick=()=>{SeasonDesk.offset=Math.max(0,SeasonDesk.offset-8);void loadInsights()};$('#siNext').onclick=()=>{SeasonDesk.offset+=8;void loadInsights()};
}
function renderCareers(d){
 const detail=Boolean(SeasonDesk.identity);
 if(!detail){
  if(!$('#siCareerRows'))stableHtml('#siPanel-careers',`<div class="si-section-title"><div><h2>${siText('Engine careers')}</h2><p>${siText('Competition history follows the entrant across approved engine upgrades.')}</p></div><label>${siText('Search')}<input id="siSearch" type="search" value="${esc(SeasonDesk.search)}"></label></div><p class="caption">${siNote()}</p>${siTable([siText('Engine'),siText('Titles'),siText('Games'),'W–D–L',siText('Status')],[]).replace('<tbody>','<tbody id="siCareerRows">')}<div class="pager"><button id="siCareerPrev">${siText('Previous')}</button><span id="siCareerPage"></span><button id="siCareerNext">${siText('Next')}</button></div>`);
  stableHtml('#siCareerRows',d.items.map(p=>`<tr><td>${siName(p)}</td><td>${p.titles.length}</td><td>${siNum(p.games)}</td><td>${p.wins}–${p.draws}–${p.losses}</td><td>${siText(p.active?'Current roster':p.candidate?'Candidate pool':'Historical entrant')}</td></tr>`).join(''));
  let timer;$('#siSearch').oninput=()=>{clearTimeout(timer);timer=setTimeout(()=>{SeasonDesk.search=$('#siSearch')?.value||'';SeasonDesk.careerOffset=0;void loadInsights()},220)};
  $('#siCareerPage').textContent=`${Math.min(d.offset+1,d.total)}–${Math.min(d.offset+50,d.total)} / ${d.total}`;
  $('#siCareerPrev').disabled=!d.offset;$('#siCareerNext').disabled=d.offset+50>=d.total;
  $('#siCareerPrev').onclick=()=>{SeasonDesk.careerOffset=Math.max(0,d.offset-50);void loadInsights()};$('#siCareerNext').onclick=()=>{SeasonDesk.careerOffset=d.offset+50;void loadInsights()};
 }else{
  stableHtml('#siPanel-careers',`<button id="siCareerBack">← ${siText('All entrants')}</button><header class="si-hero"><div><span class="si-eyebrow">${siText('Engine career')}</span><h2>${esc(d.name)}</h2><p>${siText(d.active?'Current roster':d.candidate?'Candidate pool':'Historical entrant')}</p></div><div><strong class="si-title-count">${d.titles.length}</strong><span>${siText('Titles')}</span></div></header><div class="si-metrics"><div><small>${siText('Games')}</small><strong>${siNum(d.games)}</strong></div><div><small>${siText('Wins')}</small><strong>${siNum(d.wins)}</strong></div><div><small>${siText('Draws')}</small><strong>${siNum(d.draws)}</strong></div><div><small>${siText('Losses')}</small><strong>${siNum(d.losses)}</strong></div></div><p class="caption">${siNote()}</p><p>${siText('Championship seasons')}: ${d.titles.join(', ')||'—'}</p><h3>${siText('Recorded versions')}</h3>${siTable([siText('Engine'),siText('Seasons'),siText('Games'),siText('Fingerprint')],d.versions.map(v=>`<tr><td>${esc(v.name)}</td><td>${v.first_season}–${v.last_season}</td><td>${v.games}</td><td><code>${esc(v.sha256?v.sha256.slice(0,12):siText('Not recorded'))}</code></td></tr>`))}<h3>${siText('Division & stage history')}</h3>${siTable([siText('Season'),siText('Stage'),siText('Version'),siText('Place'),'W–D–L',siText('Points'),siText('Time control'),siText('Actions')],d.history.map(h=>`<tr><td>${h.season}</td><td>${esc(h.label)}<small>${esc(ArenaI18n.message(h.state))}</small></td><td>${esc(h.name)}</td><td>${esc(ArenaI18n.message(String(h.rank)))}</td><td>${h.wins}–${h.draws}–${h.losses}</td><td>${siNum(h.points)}</td><td>${esc(tcText(h.time_control))}<small>${h.threads} ${siText('Threads')} · ${h.hash} MB</small></td><td>${siStageButton(h)}</td></tr>`))}<div class="pager"><button id="siHistoryPrev">${siText('Previous')}</button><span>${Math.min(d.offset+1,d.history_count)}–${Math.min(d.offset+50,d.history_count)} / ${d.history_count}</span><button id="siHistoryNext">${siText('Next')}</button></div><h3>${siText('Rivalries')}</h3><p class="caption">${siText('Scores are from this entrant’s perspective, across valid stages in this competition.')}</p>${siTable([siText('Opponent'),siText('Games'),'W–D–L'],d.rivals.map(r=>`<tr><td>${siName(r)}</td><td>${r.games}</td><td>${r.wins}–${r.draws}–${r.losses}</td></tr>`))}<div class="pager"><button id="siRivalPrev">${siText('Previous')}</button><span>${Math.min(d.rival_offset+1,d.rival_count)}–${Math.min(d.rival_offset+50,d.rival_count)} / ${d.rival_count}</span><button id="siRivalNext">${siText('Next')}</button></div>`);
  $('#siCareerBack').onclick=()=>{SeasonDesk.identity=null;SeasonDesk.careerOffset=0;void loadInsights()};
  for(const [stem,key,count,offset] of [['History','careerOffset',d.history_count,d.offset],['Rival','rivalOffset',d.rival_count,d.rival_offset]]){
   $('#si'+stem+'Prev').disabled=!offset;$('#si'+stem+'Next').disabled=offset+50>=count;
   $('#si'+stem+'Prev').onclick=()=>{SeasonDesk[key]=Math.max(0,offset-50);void loadInsights()};$('#si'+stem+'Next').onclick=()=>{SeasonDesk[key]=offset+50;void loadInsights()};
  }
 }
 bindInsights();
}
function seasonSummaryText(d,complete=true){
 const t=siText,parts=[ArenaText.fields([[t('Status'),t(d.complete?'Completed':'In progress')],[t('Season'),d.season],[t('Official games'),d.official],[t('Event official games'),d.all_official]])];
 if(d.admission)parts.push(ArenaText.fields(seasonAdmissionFields(d.admission,true)));
 if(d.admission_result){const a=d.admission_result;parts.push(ArenaText.fields([['Protected places',a.protected],['Qualified',a.qualified],['Not qualified',a.not_qualified]].map(([label,slots])=>[t(label),complete?slots.map(s=>a.names?.[s]||s+1).join(', ')||'—':slots.length])))}
 if(d.champion)parts.push(t('Season champion')+': '+d.champion.name);
 if(d.final){
  const f=d.final,m=f.deciding_match;
  if(m&&f.players.length>2)parts.push(ArenaText.section(t('Final match'),`${m.a_name}  ${siNum(m.a_score)} — ${siNum(m.b_score)}  ${m.b_name}\n${m.games} ${t('Games')} · ${m.tiebreaks} ${t('Tiebreaks')}`));
  parts.push(ArenaText.section(t(f.players.length>2?'Championship standings':'Championship final'),ArenaText.table([t('Place'),t('Engine'),t('Points'),'W','D','L'],f.players.map(p=>[ArenaI18n.message(String(p.rank)),p.name,p.points,p.wins,p.draws,p.losses]),{limits:[20,44,8,6,6,6],right:[2,3,4,5]})+'\n'+t('Championship stage total')+`: ${f.games} / ${f.scheduled}`));
  if(f.players.length>2)parts.push(t('Points and W–D–L include every game in this stage. Knockout placement follows match results, not total game points.'));
 }
 const main=d.stages.filter(s=>!['playoff','championship'].includes(s.role));
 if(main.length)parts.push(ArenaText.section(t(d.kind==='circuit'?'Stage leaders':'Division leaders'),ArenaText.table([t('Stage'),t('Engine'),t('Points'),t('Status')],main.filter(s=>s.entries.length).map(s=>[s.label,s.entries[0].name,s.entries[0].points,ArenaI18n.message(s.state)]),{limits:[48,44,8,12],right:[2]})));
 // Share the book once when conditions match, instead of wrapping its filename
 // into every playoff row in a short forum recap.
 const conditions=new Map();
 for(const s of d.stages){const key=JSON.stringify([s.profile_controls,s.time_control,s.book]);const row=conditions.get(key);if(row)row.stages.push(s.label);else conditions.set(key,{...s,stages:[s.label]})}
 parts.push(ArenaText.section(t('Stage conditions'),[...conditions.values()].map(s=>ArenaText.fields([[t('Stage'),conditions.size===1?t('All stages'):s.stages.join('; ')],[t('Time control'),s.profile_controls?t('Per-engine controls'):tcText(s.time_control)],[t('Opening book file'),s.book||t('Initial position')]])).join('\n\n')));
 const playoffs=d.stages.filter(s=>s.role==='playoff');
 if(playoffs.length)parts.push(ArenaText.section(t('Placement playoff history'),ArenaText.fields([[t('Tournaments'),playoffs.length],[t('Official games'),playoffs.reduce((n,s)=>n+s.official,0)]])+'\n'+t('Separate tiebreak tournaments; their points do not change the original group standings.')));
 parts.push(ArenaText.section(t('Official failure results'),d.failures.length?ArenaText.table([t('Engine'),t('Termination reason'),t('Games')],d.failures.map(f=>[f.name,ArenaI18n.message(f.reason),f.games])):t('(No records.)')));
 if(d.movements.length)parts.push(ArenaText.section(t('Promotion & relegation'),ArenaText.table([t('Engine'),t('Outcome'),t('Division')],d.movements.map(m=>[m.name,t(m.outcome),d.division_names[m.to]]))));
 if(d.highlights.length)parts.push(ArenaText.section(t('Climbs from initial seeding'),ArenaText.table([t('Engine'),t('Stage'),t('Initial seed'),t('Place')],d.highlights.map(h=>[h.name,h.label,h.seed,h.rank]))+'\n'+t('Seed changes describe this event, not a measured change in engine strength.')));
 if(d.updates.length)parts.push(ArenaText.section(t('Engine upgrades'),ArenaText.table([t('Previous version'),t('New version')],d.updates.map(u=>[u.previous,u.name]))));
 if(complete)for(const s of d.stages){
  parts.push(ArenaText.section(s.label,ArenaText.fields([[t('Status'),ArenaI18n.message(s.state)],[t('Official / scheduled'),`${s.official} / ${s.total}`],[t('Time control'),tcText(s.time_control)],[t('Opening book file'),s.book||t('Initial position')],[t('Opening random seed'),s.seed],[t('Clock tolerance'),s.tolerance+' s']])+'\n\n'+ArenaText.table([t('Place'),t('Engine'),t('Games'),'W','D','L',t('Points'),t('Bye points')],s.entries.map(p=>[ArenaI18n.message(String(p.rank)),p.name,p.games,p.wins,p.draws,p.losses,p.points,p.bye_points]),{limits:[20,44,8,6,6,6,8,10],right:[2,3,4,5,6,7]})));
 }
 parts.push(t(d.complete?'Advancement and final placements are recorded.':'Live places are provisional until advancement is recorded. Tied boundaries may need playoffs.'),t('Stage ratings describe their own opposition and conditions; ratings are not combined across stages.'));
 return ArenaText.report(d.name+' — '+t('Season')+' '+d.season,parts,new Date(d.generated_at*1000).toISOString());
}
function renderSeasonSummary(d){
 // Keep a fixed snapshot while it is being reviewed; refresh is explicit here.
 if($('#siSummaryPreview')&&$('#siSummaryPreview').dataset.season===String(d.season))return;
 stableHtml('#siPanel-summary',`<div class="si-section-title"><div><h2>${siText('Season summary')}</h2><p>${siText('Review a fixed snapshot, then copy a forum post or save a text file.')}</p></div><label>${siText('Detail')}<select id="siSummaryDetail"><option value="brief">${siText('Forum recap')}</option><option value="full">${siText('Complete season tables')}</option></select></label></div><div class="si-summary-actions"><button class="primary" id="siExportSummary">${siText('Copy / save summary…')}</button><button id="siRefreshSummary">${siText('Refresh snapshot')}</button></div><textarea id="siSummaryPreview" data-season="${d.season}" readonly spellcheck="false" aria-label="${siText('Season summary')}" wrap="off"></textarea>`);
 const update=()=>{$('#siSummaryPreview').value=seasonSummaryText(d,$('#siSummaryDetail').value==='full')};$('#siSummaryDetail').onchange=update;update();
 $('#siExportSummary').onclick=()=>{const text=$('#siSummaryPreview').value;textExport(d.name+' — '+siText('Season')+' '+d.season,()=>text)};
 $('#siRefreshSummary').onclick=()=>{$('#siSummaryPreview').dataset.season='';void loadInsights()};
}
const insightOriginalShow=showEvent;
showEvent=async function(id,offset=0){await insightOriginalShow(id,offset);insightShell(eventDetailData);await loadInsights()};
const insightOriginalRender=renderEventDetail;
renderEventDetail=function(e){insightOriginalRender(e);if($('#eventInsights')){switchInsightTab();if(SeasonDesk.tab==='overview')void loadInsights()}};
