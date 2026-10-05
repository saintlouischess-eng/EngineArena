'use strict';
function openingSettings(){return {opening_policy:$('#openingPreset')?.value==='game'?'pair':$('#openingPreset')?.value||'pair'}}
const tournamentBeforeOpeningPresets=newTournament;
newTournament=async function(draft=null){
 await tournamentBeforeOpeningPresets(draft);if(!$('#topening'))return;
 const anchor=$('#topening').closest('.fields');
 anchor.insertAdjacentHTML('beforebegin',ArenaI18n.h`<div class="fields"><label>Opening preset<select id="openingPreset" data-help="Choose which games share a position. A color-reversed pair always uses the identical opening for both games."><option value="pair">Fresh position for every opening pair</option><option value="round">One shared position per round</option><option value="cycle">Same opening suite for every matchup</option><option value="game">Fresh position for every single game (unpaired)</option><option value="fixed">One fixed position for the whole tournament</option></select></label></div><p class="caption" id="openingPresetHelp"></p>`);
 $('#torder').innerHTML=ArenaI18n.h('<option value="sequential">Sequential, without repeats within the pool</option><option value="shuffle">Seeded shuffle, without repeats within the pool</option><option value="random">Seeded random, repeats allowed immediately</option>');
 $('#torder').dataset.help=ArenaI18n.t('Sequential and shuffled orders exhaust the unique pool before repeating it. Shuffle records a repeatable permutation. Random selection samples with replacement and can repeat immediately.');
 $('#tdepth').dataset.help=ArenaI18n.t('Maximum opening plies for PGN games and Polyglot branches. Shorter lines stop at their end. FEN and EPD already specify final positions, so depth does not change them.');
 anchor.insertAdjacentHTML('afterend',ArenaI18n.h('<div id="openingCapacity" class="opening-capacity" role="status" aria-live="polite"></div><button type="button" id="analyzeOpenings" data-help="Re-read the selected opening source and calculate its unique-position capacity for the current participants, pairing preset and color policy.">Recalculate opening capacity</button>'));
 let revision=0,timer;const node=$('#openingCapacity');
 const alive=()=>node.isConnected&&$('#modal').open;
 const explain=()=>{
  const ko=['knockout','double_elimination'].includes($('#tformat').value),paired=$('#tpaired').checked;
  const shared=$('#openingPreset option[value=round]'),suite=$('#openingPreset option[value=cycle]');
  shared.textContent=ko?ArenaI18n.t('KO: shared sequence; new opening each ')+(paired?'pair':'game'):ArenaI18n.t('One shared position per round');
  shared.disabled=$('#tformat').value==='custom';
  if(shared.disabled&&$('#openingPreset').value==='round')$('#openingPreset').value='pair';
  const recordedCycle=ko&&tournamentDraft?.settings.opening_policy==='cycle';
  suite.hidden=suite.disabled=ko&&!recordedCycle;
  if(ko&&!recordedCycle&&$('#openingPreset').value==='cycle')$('#openingPreset').value='round';
  const preset=$('#openingPreset').value;
  $('#openingPresetHelp').textContent=({pair:ArenaI18n.t('Assign one new opening to each matchup pair; both colors start from that same position. With color reversal off, each game gets a new position.'),round:ArenaI18n.t('Every matchup in a round starts from the same position. Round robin uses one opponent per engine per round, with byes for odd fields; each new round uses the next opening. Swiss and ladder share a position across all cycles in their round.'),cycle:ArenaI18n.t('Every matchup gets the same suite: cycle 1 uses opening 1, cycle 2 opening 2, and so on. Swiss, ladder and elimination advance the suite for each new round.'),game:ArenaI18n.t('Color reversal is off: every individual game consumes a new position. Paired-game statistics are unavailable for unpaired games.'),fixed:ArenaI18n.t('Use the first position in the selected order for every game. Shuffle lets the recorded seed choose that position.')})[preset]||ArenaI18n.t('Recorded legacy opening assignment');
  if(ko&&['round','cycle'].includes(preset))$('#openingPresetHelp').textContent=paired?ArenaI18n.t('All KO matches share opening 1 for games 1–2, opening 2 for games 3–4, and so on. Each tiebreak pair and each later KO round continues with fresh positions. Both colors always use the same position.'):ArenaI18n.t('All KO matches share the same sequence, advancing after every game. Tiebreak games and later KO rounds continue with fresh positions. Colors alternate; paired statistics are off.');
  if(ko&&preset==='fixed')$('#openingPresetHelp').textContent=ArenaI18n.t('Intentional repetition: every regular game AND every tiebreak uses this one position. Select the KO shared sequence or fresh opening pairs to advance through the book.');
 };
 const analyze=async()=>{
  if(!alive())return;const version=++revision;node.textContent=ArenaI18n.t('Counting unique positions… Large Polyglot books may take time; running games remain available.');
  node.classList.remove('capacity-warning');
  try{
   const source=startingPositionPayload();
   if($('#topeningSource').value==='file'&&!source.opening_file.trim())throw Error(ArenaI18n.t('Choose an opening file to calculate its capacity.'));
   const settings={...formatSettings(),...openingSettings(),format:$('#tformat').value,cycles:Number($('#tcycles').value),rounds:Number($('#trounds').value),candidates:Number($('#tcandidates').value),paired:$('#tpaired').checked,opening_order:$('#torder').value,chess960:tournamentChess960()};
   const result=await api('opening-preview',{...source,book_depth:Number($('#tdepth').value),participants:tournamentParticipantCount(),settings});
   if(version!==revision||!alive())return;
   const number=v=>BigInt(v).toLocaleString(ArenaI18n.locale);
   node.innerHTML=ArenaI18n.h`<strong>${number(result.unique_positions)} unique ${result.unique_positions===1?'position':'positions'}</strong><p>${number(result.paired_game_capacity)} games as color-reversed pairs, or ${number(result.single_game_capacity)} unpaired games, when each position is assigned once.</p><p>${result.random_repeats?ArenaI18n.t('Random selection can repeat immediately; choose Sequential or Seeded shuffle to exhaust the pool before reuse.'):settings.opening_policy==='fixed'?ArenaI18n.t('This preset deliberately repeats one fixed position.'):result.games_before_reuse!==null?ArenaI18n.m`With this preset and field: ${number(result.games_before_reuse)} games before recycling the pool.`:ArenaI18n.t('The number of games per shared round depends on byes, results and playoffs; a fixed game capacity is not available.')} ${settings.opening_policy!=='fixed'?ArenaI18n.m`${result.unbounded?ArenaI18n.t('Regular matches need'):result.conditional?ArenaI18n.t('Up to'):ArenaI18n.t('This schedule needs')} ${number(result.required_positions)} position assignments (${esc(result.pool_units)}).`:''}</p><p>${esc(ArenaI18n.message(result.note))}</p>${result.unique_positions===1?ArenaI18n.h('<p class="capacity-warning-text">Only one unique position is available. Every game will start from it, including all tiebreaks. Choose a book with more positions for opening variety.</p>'):''}${result.duplicates_removed?ArenaI18n.h`<p>${number(result.duplicates_removed)} duplicate positions removed.</p>`:''}<small>Uniqueness uses pieces, side to move, castling rights and legal en passant; move counters do not create new positions. ${result.kind==='polyglot'?ArenaI18n.t('All reachable positive-weight legal branches are counted at the chosen depth or their earlier book exit. Weights select eligible moves; they do not duplicate positions. '):''}${esc(result.exhaustion)}</small>${result.reuse_expected&&settings.opening_policy!=='fixed'?ArenaI18n.h('<p class="capacity-warning-text">This schedule exceeds the unique pool. Openings will repeat; reduce the schedule or select a larger book to avoid reuse.</p>'):''}`;
   node.classList.toggle('capacity-warning',result.reuse_expected&&settings.opening_policy!=='fixed');
  }catch(e){if(version===revision&&alive()){node.textContent=e.message;node.classList.add('capacity-warning')}}
 };
 const schedule=()=>{explain();++revision;clearTimeout(timer);node.textContent=ArenaI18n.t('Updating opening capacity…');timer=setTimeout(analyze,300)};
 $('#openingPreset').onchange=()=>{const p=$('#openingPreset').value;if(p==='game')$('#tpaired').checked=false;else if(p==='pair')$('#tpaired').checked=true;$('#tpaired').dispatchEvent(new Event('change',{bubbles:true}));explain();schedule()};
 $('#tpaired').addEventListener('change',()=>{if($('#openingPreset').value==='game'&&$('#tpaired').checked){$('#openingPreset').value='pair';explain()}});
 for(const id of ['topeningSource','tsavedPosition','tfile960','topening','tdepth','tseed','torder','tpaired','tformat','tcycles','trounds','tcandidates','tpreset','fknockout','fplayoffLimit','fplayoffCycles','fdistance']){
  $('#'+id)?.addEventListener('change',schedule);if($('#'+id)?.matches('input'))$('#'+id).addEventListener('input',schedule);
 }
 const browseButton=$('[data-browse=topening]'),oldBrowse=browseButton.onclick;
 browseButton.onclick=async e=>{await oldBrowse(e);schedule()};
 $('#koConfig')?.addEventListener('ko-settings-change',schedule);
 $('#analyzeOpenings').onclick=safely(analyze);explain();await analyze();
};
$('#newTournament').onclick=safely(newTournament);
