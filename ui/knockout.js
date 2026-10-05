'use strict';
function tournamentFormatName(format){return ({sprt:ArenaI18n.t('Two-engine SPRT'),custom:ArenaI18n.t('Custom matchups'),knockout:ArenaI18n.t('Knockout (KO — single elimination)'),double_elimination:ArenaI18n.t('Knockout (KO — double elimination)')})[format]||format.replaceAll('_',' ')}
function knockoutMatchTable(round){
 return ArenaI18n.h`<div class="ko-match-scroll" tabindex="0" aria-label="KO match results"><table><thead><tr><th>Match</th><th>Total game score</th><th>Current stage</th><th>Outcome</th></tr></thead><tbody>${round.matches.map(m=>{const last=m.stages.at(-1);return ArenaI18n.h`<tr><td>${esc(m.a_name)}<br>vs ${esc(m.b_name)}</td><td>${fmt(m.a_score,1)} – ${fmt(m.b_score,1)}</td><td>${last?ArenaI18n.h`${last.stage?ArenaI18n.t('Tiebreak ')+last.stage:ArenaI18n.t('Regular match')} · ${last.completed}/${last.games} games<br>${fmt(last.a_score,1)} – ${fmt(last.b_score,1)}<small>${esc(last.time_control?tcText(last.time_control):ArenaI18n.t('Normal engine controls'))}</small>`:ArenaI18n.t('Awaiting games')}</td><td>${esc(ArenaI18n.message(m.status))}${m.decision_basis?`<small>${esc(ArenaI18n.message(m.decision_basis))}</small>`:""}</td></tr>`}).join('')}</tbody></table></div>`;
}
function renderKnockoutResults(t){
 let root=$('#koLiveResults');if(!root){
  root=document.createElement('div');root.id='koLiveResults';root.className='ko-live-results';
  root.innerHTML=ArenaI18n.h('<div id="koRoundResults"></div><p class="ko-rules-summary caption">Match results determine KO places. Game statistics include tiebreaks.</p><details class="ko-rules" id="koRules"><summary>How KO standings work</summary><p class="caption" id="koRulesText"></p></details>');
  panels.standings.querySelector('.panel-title').after(root);
 }
 root.hidden=!t.knockout;if(!t.knockout)return;
 const k=t.knockout,round=k.rounds.at(-1);
 stableHtml('#koRoundResults',ArenaI18n.h`<div class="ko-stage-heading"><h3>${k.champion?ArenaI18n.t('Champion: ')+esc(k.champion):ArenaI18n.m`${k.round?ArenaI18n.t('KO round ')+k.round:ArenaI18n.t('KO ready')} · ${k.remaining} engines still in`}</h3><button type="button" id="koFullReport" data-help="Open the tournament report with every saved KO round, match score, tiebreak stage and outcome. HTML and readable text exports are available.">Full KO report…</button></div>${round?knockoutMatchTable(round)+(round.byes.length?ArenaI18n.h`<p class="caption">Byes${round.bye_count>round.byes.length?ArenaI18n.m` (first ${round.byes.length} of ${round.bye_count})`:""}: ${round.byes.map(p=>esc(p.name)).join(', ')}. No game or match win is awarded.</p>`:'')+(round.match_count>round.matches.length?ArenaI18n.h`<p class="caption">First ${round.matches.length} of ${round.match_count} matches in this round. The full KO report includes all matches.</p>`:''):ArenaI18n.h('<p>Matches will appear when the tournament starts.</p>')}`);
 // Keep the disclosure node intact so live score changes preserve focus and open state.
 $('#koRulesText').textContent=ArenaI18n.message(k.note);
 $('#koFullReport').onclick=()=>$('#tournamentReport').click();
}
function knockoutSettings(){
 if(!['knockout','double_elimination'].includes($('#tformat')?.value)||!$('#koConfig'))return {ko_round_games:[]};
 const legs=$('#tpaired').checked?2:1,games=Number($('#koPlayoffGames').value);
 if(!Number.isSafeInteger(games)||games<1||games%legs)throw Error(ArenaI18n.t('Tiebreak games must be positive whole numbers, and even when color reversal is enabled.'));
 return {ko_round_games:$('#tformat').value==='knockout'?$$('[data-ko-round]').map(e=>Number(e.value)):[],knockout_tiebreak:$('#koTiePolicy')?.value||'continuous',playoff_cycles:games/legs,
  playoff_controls:$('#koControlMode').value==='same'?[]:$$('#koStages .tc-editor').map(e=>readTc(e.id))};
}
function installKnockoutEditor(update){
 let n=tournamentParticipantCount(),count=n>1?Math.ceil(Math.log2(n)):0,size=2**count;
 const roundRows=()=>Array.from({length:count},(_,r)=>{const left=count-r,label=left===1?ArenaI18n.t('Final'):left===2?ArenaI18n.t('Semifinals'):left===3?ArenaI18n.t('Quarterfinals'):ArenaI18n.t('Round ')+(r+1),matches=r===0?n-size/2:2**(count-r-1);return ArenaI18n.h`<tr><td>Round ${r+1} · ${label}</td><td>${matches.toLocaleString(ArenaI18n.locale)}</td><td><input type="number" min="2" step="2" value="20" data-ko-round="${r}" aria-label="Games per match in round ${r+1}" data-help="Total regular games for each matchup in this round, excluding tiebreaks. Use an even count with reversed-color opening pairs. All these games will be played."></td></tr>`}).join('');
 $('#tformat').closest('.fields').insertAdjacentHTML('afterend',ArenaI18n.h`<div id="koConfig" class="ko-config" hidden>
  <h3>Knockout (KO) matches & tiebreaks</h3><p>A match winner advances; the loser is eliminated after one match loss in single elimination, or two in double elimination. All scheduled games in a match or tiebreak stage finish before deciding its winner.</p>
  <div id="koRoundLengths"><h4>Games per match, for each round</h4><div class="table-scroll"><table><thead><tr><th>Round</th><th>Matches</th><th>Games per match</th></tr></thead><tbody>${roundRows()}</tbody></table></div><p class="caption" id="koRoundNote"></p></div>
  <h4>Tied matches: keep playing until a winner</h4><p class="caption">If a stage is tied, another complete stage is played. No seed or standings tiebreak automatically eliminates an engine. With paired openings, both colors finish before the match is decided.</p>
  <div class="fields"><label>Games per tiebreak stage<input id="koPlayoffGames" type="number" min="2" step="2" value="2" data-help="Games in each additional stage. With color reversal enabled, 2 means one complete opening pair; split wins also count as a tied stage."></label>
  <label>Tiebreak time controls<select id="koControlMode" data-help="Keep each engine’s normal control, including handicaps, or define an ordered sequence for both engines. The last control repeats until a winner is decided."><option value="same">Keep each engine’s normal control</option><option value="sequence">Custom sequence / progressively shorter</option></select></label></div>
  <div id="koSequence" hidden><p>These controls apply to both engines during tiebreaks, replacing their normal time controls. Each game starts with fresh clocks. The last listed control repeats for any further tied stages.</p>
   <button type="button" id="koShorterPreset" data-help="Replace the sequence with an editable example: 60 seconds + 1, then 30 seconds + 0.5, then 15 seconds + 0.25. Check that these are appropriate for your regular control.">Load shorter-control example</button>
   <div id="koStages"></div><button type="button" id="koAddStage" data-help="Add another time-control step. The final step repeats until a match winner is decided.">Add tiebreak control</button></div>
  <p class="caption">Tiebreaks have no fixed game maximum. They continue while stages are tied; you can pause and resume. Original attempts, openings, stage numbers and actual controls are saved.</p></div>`);
 let next=0;
 const changed=()=>{update();$('#koConfig').dispatchEvent(new CustomEvent('ko-settings-change',{bubbles:true}))};
 const renumber=()=>$$('#koStages .ko-stage').forEach((e,i)=>{e.querySelector('h4').textContent=ArenaI18n.m`Tiebreak stage ${i+1}${i===$$('#koStages .ko-stage').length-1?ArenaI18n.t(' and all further stages'):''}`;e.querySelector('[data-ko-remove]').disabled=$$('#koStages .ko-stage').length===1});
 const add=control=>{const id='koTc'+next++;$('#koStages').insertAdjacentHTML('beforeend',ArenaI18n.h`<div class="ko-stage"><div class="ko-stage-heading"><h4></h4><button type="button" data-ko-remove data-help="Remove this step from the tiebreak sequence.">Remove control</button></div>${tcEditor(id,control)}</div>`);wireTc(id);const root=$('#'+id);root.closest('.ko-stage').querySelector('[data-ko-remove]').onclick=()=>{root.closest('.ko-stage').remove();renumber();changed()};renumber()};
 add(readTc('ttc'));
 $('#koConfig').loadSetup=settings=>{
  $$('[data-ko-round]').forEach((e,i)=>e.value=settings.ko_round_games?.[i]??settings.cycles*(settings.paired?2:1));
  $('#koPlayoffGames').value=settings.playoff_cycles*(settings.paired?2:1);
  const controls=settings.playoff_controls||[];$('#koControlMode').value=controls.length?'sequence':'same';$('#koSequence').hidden=!controls.length;
  $('#koStages').replaceChildren();for(const control of controls.length?controls:[settings.time_control])add(control);
  if(['knockout','double_elimination'].includes(settings.format)&&settings.knockout_tiebreak!=='continuous'){
   $('#koConfig').insertAdjacentHTML('afterbegin',ArenaI18n.h`<label>KO tie resolution<select id="koTiePolicy"><option value="${esc(settings.knockout_tiebreak)}">${ArenaI18n.t('Keep recorded tie policy')}: ${esc(settings.knockout_tiebreak)}</option><option value="continuous">Keep playing until a winner</option></select></label><p class="caption">The recorded legacy policy is retained unless you select continuous tiebreaks. The controls below describe continuous play.</p>`);$('#koTiePolicy').onchange=changed;
  }
 };
 $('#koControlMode').onchange=()=>{$('#koSequence').hidden=$('#koControlMode').value==='same';changed()};
 $('#koShorterPreset').onclick=()=>{$('#koStages').replaceChildren();for(const [seconds,increment] of [[60,1],[30,.5],[15,.25]])add({kind:'fischer',seconds,increment});changed()};
 $('#koAddStage').onclick=()=>{const last=$$('#koStages .tc-editor').at(-1);add(readTc(last.id));changed()};
 $('#koConfig').addEventListener('input',changed);
 $('#koStages').addEventListener('change',changed);
 $('#koStages').addEventListener('click',e=>{if(e.target.closest('.add-stage,.remove-stage'))changed()});
 return ()=>{
  const participants=tournamentParticipantCount();
  if(participants!==n){
   const previous=$$('[data-ko-round]').map(e=>e.value);n=participants;count=n>1?Math.ceil(Math.log2(n)):0;size=2**count;
   $('#koRoundLengths tbody').innerHTML=roundRows();$$('[data-ko-round]').forEach((e,i)=>{if(previous[i]!==undefined)e.value=previous[i]});
  }
  const format=$('#tformat').value,enabled=['knockout','double_elimination'].includes(format),legs=$('#tpaired').checked?2:1;
  $('#koConfig').hidden=!enabled;$('#koRoundLengths').hidden=format!=='knockout';$('#tcycles').closest('.field').hidden=format==='knockout';
  $$('[data-tiebreak]').forEach(e=>e.closest('label').hidden=enabled);
  for(const e of [...$$('[data-ko-round]'),$('#koPlayoffGames')]){e.min=String(legs);e.step=String(legs)}
  $('#koRoundNote').textContent=(size>n?ArenaI18n.m`${size-n} first-round byes; byes do not play games. `:'')+(legs===2?ArenaI18n.t('Even game counts preserve complete color-reversed opening pairs.'):ArenaI18n.t('Unpaired games alternate colors within each match; odd game counts are allowed.'));
 };
}
