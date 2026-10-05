'use strict';
const concurrencyMetric=$('#activeMetric').closest('article');
concurrencyMetric.insertAdjacentHTML('beforeend',ArenaI18n.h`<div class="concurrency-control"><label for="liveConcurrency">Concurrent games<input id="liveConcurrency" disabled type="number" min="1" step="1" required data-help="Maximum simultaneous games for this tournament. CPU threads, memory and shared GPU limits still apply; this does not change engine Threads settings."></label><button id="applyConcurrency" disabled data-help="Apply while running or paused. Increasing allows more starts; decreasing lets existing games finish normally.">Apply</button></div><small class="concurrency-note" id="concurrencyNote" role="status"></small>`);
let concurrencyTid='',concurrencySaved=0,concurrencyBusy=false;
function renderConcurrency(t){
 const input=$('#liveConcurrency'),button=$('#applyConcurrency'),changed=concurrencyTid!==t.id;
 if(changed||input.value===String(concurrencySaved)){input.value=t.settings.concurrency;concurrencyTid=t.id}
 concurrencySaved=t.settings.concurrency;
 const editable=['running','paused','draining'].includes(t.state)&&!t.saving_error;
 input.disabled=concurrencyBusy||!editable;button.disabled=concurrencyBusy||!editable;
 const active=t.counts.running||0,limit=t.settings.concurrency;
 $('#concurrencyNote').textContent=concurrencyBusy?ArenaI18n.t('Applying concurrency…'):active>limit?ArenaI18n.t('Finishing existing games: {0} active, target {1}.',active,limit):
  t.saving_error?ArenaI18n.t('Save failure'):t.state==='paused'||t.state==='draining'?ArenaI18n.t('Saved limit applies when resumed.'):editable?ArenaI18n.t('CPU, memory and GPU budgets still apply.'):ArenaI18n.t('Tournament finished.');
}
$('#applyConcurrency').onclick=safely(async()=>{
 const input=$('#liveConcurrency');if(concurrencyBusy||!input.reportValidity()||!state.tid||!state.snapshot||state.snapshot.id!==state.tid)return;
 const tid=state.tid,value=Number(input.value);if(!Number.isSafeInteger(value))throw Error(ArenaI18n.t('Concurrent games must be a positive whole number'));
 concurrencyBusy=true;renderConcurrency(state.snapshot);
 try{
  const result=await api(`tournaments/${tid}/concurrency`,{concurrency:value});
  if(state.tid===tid){concurrencySaved=result.concurrency;input.value=result.concurrency;await refreshTournament()}
  notify(ArenaI18n.t('Concurrent game limit saved: {0}.',result.concurrency));
 }finally{concurrencyBusy=false;if(state.snapshot)renderConcurrency(state.snapshot)}
});
if(state.snapshot)renderConcurrency(state.snapshot);
$('#liveConcurrency').onkeydown=event=>{if(event.key==='Enter'){event.preventDefault();$('#applyConcurrency').click()}};
