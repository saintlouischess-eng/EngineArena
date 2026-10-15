'use strict';
function scheduleOrderLabel(order){return ({balanced:ArenaI18n.t('Balanced round order'),matchup:ArenaI18n.t('Matchup order'),shuffle:ArenaI18n.t('Seeded shuffle'),legacy:ArenaI18n.t('Recorded schedule order')})[order||'legacy']}
function schedulingSettings(){return {schedule_order:$('#tScheduleOrder')?.value||'legacy',schedule_seed:Number($('#tScheduleSeed')?.value??7970)}}
const tournamentBeforeScheduling=newTournament;
newTournament=async function(draft=null){
 await tournamentBeforeScheduling(draft);if(!$('#tformat'))return;
 $('#tformat').closest('.fields').insertAdjacentHTML('afterend',ArenaI18n.h`<div class="section-label">GAME SCHEDULING</div><div class="fields"><div class="field"><label for="tScheduleOrder">Game scheduling</label><select id="tScheduleOrder" data-help="Controls which scheduled game starts next. It does not change opponents, openings, color reversal or resource limits."><option value="balanced">Balanced round order</option><option value="matchup">Matchup order</option><option value="shuffle">Seeded shuffle</option></select></div><div class="field" id="tScheduleSeedField"><label for="tScheduleSeed">Scheduling seed</label><input id="tScheduleSeed" type="number" min="0" max="2147483647" step="1" value="7970" data-help="The same seed and tournament setup reproduce the same shuffled launch order. This is separate from the opening seed."></div></div><p class="caption" id="scheduleOrderHelp"></p><p class="caption" id="scheduleFormatHelp"></p>`);
 const order=$('#tScheduleOrder'),seed=$('#tScheduleSeed');
 if(draft){
  if(!draft.settings.schedule_order||draft.settings.schedule_order==='legacy')order.add(new Option(ArenaI18n.t('Recorded schedule order'),'legacy'));
  order.value=draft.settings.schedule_order||'legacy';seed.value=draft.settings.schedule_seed??7970;
 }
 const explain=()=>{
  $('#tScheduleSeedField').hidden=order.value!=='shuffle';seed.disabled=order.value!=='shuffle';
  $('#scheduleOrderHelp').textContent=({balanced:ArenaI18n.t('Spread matchups across the field before repeating them. New games start as resources become free; round-robin rounds may overlap. Finished game counts can still differ.'),matchup:ArenaI18n.t('Play the scheduled repetitions of each matchup together, in participant order.'),shuffle:ArenaI18n.t('Shuffle opening pairs, or individual unpaired games, without repeats. Both colors retain the same opening. Shuffle varies the order; it does not guarantee even participation.'),legacy:ArenaI18n.t('Keep the recorded scheduling behavior, including any ordering linked to the opening preset.')})[order.value];
  const fmt=$('#tformat').value;
  $('#scheduleFormatHelp').textContent=['swiss','knockout','double_elimination','ladder'].includes(fmt)?ArenaI18n.t('Applies within each committed round or tiebreak stage. Later rounds still wait for the results needed to determine their pairings.'):fmt==='sprt'?ArenaI18n.t('SPRT keeps its recorded statistical sampling order. Shuffled launches can delay a stopping decision until earlier samples finish.'):ArenaI18n.t('Standalone tournaments and event stages use the same choices. A gauntlet or custom matchup list may require some engines to play more often.');
 };
 order.onchange=explain;$('#tformat').addEventListener('change',explain);explain();
};
$('#newTournament').onclick=safely(newTournament);
