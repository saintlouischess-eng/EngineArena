'use strict';
const tieToggle=document.createElement('label');tieToggle.innerHTML=ArenaI18n.h('<input id="showTiebreaks" type="checkbox"> Tiebreak values');resultControls.append(tieToggle);
const tieExplanation=document.createElement('button');tieExplanation.textContent=ArenaI18n.t('Ranking explained…');resultControls.append(tieExplanation);
const rankNote=document.createElement('p');rankNote.className='ranking-note';resultControls.after(rankNote);
function explainRanking(row){const t=state.snapshot;if(!t)return;const keys=t.standings[0]?.tiebreak_values||[];modal(ArenaI18n.t('Ranking explained'),`<p>${esc(t.standings[0]?.tiebreak_order||'')}</p><p>${ArenaI18n.t('Ranking numbers retain the tournament order even when you sort another display column. Values remain provisional until play finishes.')}</p>${row?`<h3>${esc(row.name)}</h3><p>${esc(ArenaI18n.message(row.ranking_basis))}</p><table><thead><tr><th>${ArenaI18n.t('Criterion')}</th><th>${ArenaI18n.t('Value')}</th><th>${ArenaI18n.t('Order')}</th></tr></thead><tbody><tr><td>${ArenaI18n.t('Points')}</td><td>${fmt(row.points,1)}</td><td>${ArenaI18n.t('Higher first')}</td></tr>${row.tiebreak_values.map(v=>`<tr><td>${esc(ArenaI18n.t(v.name))}</td><td>${fmt(v.value,2)}</td><td>${esc(ArenaI18n.message(v.direction))}</td></tr>`).join('')}</tbody></table>`:''}<p>${ArenaI18n.t('Buchholz sums opponents’ tournament points once per played game. Sonneborn–Berger weights those points by the score earned against each opponent. Seed is a deterministic fallback, not a strength measurement.')}</p><p>${t.knockout?ArenaI18n.t('Knockout placement follows bracket progress and match results. Game points do not replace the bracket result.'):keys.map(v=>esc(ArenaI18n.t(v.name))).join(' → ')}</p>`)}
tieExplanation.onclick=()=>explainRanking();$('#showTiebreaks').onchange=()=>{displayPrefs.showTiebreaks=$('#showTiebreaks').checked;saveDisplay();if(state.snapshot)renderStandings(state.snapshot)};
const standingsBeforeDetails=renderStandings;renderStandings=function(t){
 standingsBeforeDetails(t);$('#showTiebreaks').checked=!!displayPrefs.showTiebreaks;
 $$('#standings [data-tiebreak-cell]').forEach(el=>el.remove());
 const keys=displayPrefs.showTiebreaks&&!t.knockout?(t.standings[0]?.tiebreak_values||[]):[];
 for(const v of keys){const th=document.createElement('th');th.dataset.tiebreakCell='1';th.textContent=ArenaI18n.t(v.name);$('#standings thead tr').append(th)}
 for(const tr of $$('#standings tbody tr[data-slot]')){const row=t.standings.find(r=>r.slot===Number(tr.dataset.slot));if(!row)continue;
  tr.querySelector('[data-withdrawn-badge]')?.remove();
  if(row.withdrawn){const badge=document.createElement('small');badge.dataset.withdrawnBadge='1';badge.textContent=ArenaI18n.t('Withdrawn · played results retained');tr.cells[1].append(badge)}
  const rank=tr.cells[0];rank.innerHTML=`<button class="subtle" aria-label="${esc(ArenaI18n.t('Explain rank'))} ${row.rank}">${row.rank}</button>`;rank.querySelector('button').onclick=e=>{e.stopPropagation();explainRanking(row)};
  for(const v of keys){const td=document.createElement('td');td.dataset.tiebreakCell='1';td.className='tie-details';td.textContent=fmt(row.tiebreak_values.find(x=>x.key===v.key)?.value,2);tr.append(td)}
 }
 rankNote.textContent=(t.standings[0]?.tiebreak_order||'')+(t.state==='completed'?'':' · '+ArenaI18n.t('Provisional'))+(state.standSort!=='rank'?' · '+ArenaI18n.t('Display sorted separately; rank numbers are unchanged'):'');
 $('#tournamentNote [data-roster-status]')?.remove();
 if(t.settings.rr_withdrawn_excluded?.length){
  rankNote.textContent+=' · '+ArenaI18n.t('Withdrawn results excluded from standings; historical ratings retained.');
 }
 if(t.settings.rr_withdrawn_retained?.length){
  rankNote.textContent+=' · '+ArenaI18n.t('Withdrawn entrants keep played results; unplayed games are canceled. Game totals may differ.');
  const status=document.createElement('span');status.dataset.rosterStatus='1';status.textContent=' · '+ArenaI18n.t('{0} active · {1} withdrawn',t.active_participants,t.settings.rr_withdrawn_retained.length);$('#tournamentNote').append(status);
 }
};
async function activityDialog(tid=''){
 let offset=0;
 modal(ArenaI18n.t('Activity and uptime history'),ArenaI18n.h('<div id="activityTotals" class="activity-totals"></div><p id="activityNote"></p><div class="table-scroll"><table><thead><tr><th>From</th><th>Last observed</th><th>Activity</th><th>Session outcome</th></tr></thead><tbody id="activityRows"></tbody></table></div><div class="pager"><button id="activityPrev">Previous</button><span id="activityPage"></span><button id="activityNext">Next</button><button id="activityRefresh">Refresh</button></div>'));
 const root=$('#activityRows');async function load(){const r=await api('activity?'+new URLSearchParams({tid,offset}));if(root!==$('#activityRows'))return;$('#activityTotals').innerHTML=r.totals.map(x=>`<div>${esc(ArenaI18n.message(x.state))}<strong>${ArenaClocks.format(x.seconds)}</strong></div>`).join('')+`<div>${ArenaI18n.t('Unobserved gaps')}<strong>${ArenaClocks.format(r.unobserved_seconds)}</strong></div>`;$('#activityNote').textContent=ArenaI18n.message(r.note);root.innerHTML=r.items.map(x=>`<tr><td>${esc(new Date(x.started*1000).toLocaleString())}</td><td>${esc(new Date(x.last_seen*1000).toLocaleString())}</td><td>${esc(ArenaI18n.message(x.state))}</td><td>${esc(ArenaI18n.message(x.outcome))}</td></tr>`).join('');$('#activityPage').textContent=`${r.total?offset+1:0}–${Math.min(offset+50,r.total)} / ${r.total}`;$('#activityPrev').disabled=!offset;$('#activityNext').disabled=offset+50>=r.total}
 $('#activityPrev').onclick=safely(()=>{offset=Math.max(0,offset-50);return load()});$('#activityNext').onclick=safely(()=>{offset+=50;return load()});$('#activityRefresh').onclick=safely(load);await load();
}
const activityButton=document.createElement('button');activityButton.textContent=ArenaI18n.t('Activity history…');activityButton.onclick=safely(()=>activityDialog());$('#health .panel-title').append(activityButton);
const tournamentActivity=document.createElement('button');tournamentActivity.textContent=ArenaI18n.t('Tournament activity…');tournamentActivity.onclick=safely(()=>{if(state.tid)return activityDialog(state.tid)});$('#tournamentReport').after(tournamentActivity);
