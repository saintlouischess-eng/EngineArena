'use strict';
const storagePanel=document.createElement('div');storagePanel.className='panel storage-panel';
storagePanel.innerHTML=ArenaI18n.h`<div class="panel-title"><h2>Storage & backup settings</h2><button id="optimizeStorage" data-help="Losslessly compress older engine logs, compact the database and recovery backups, and return freed space to Windows. Games and experiments must be stopped. Every move, result and diagnostic line is retained.">Reclaim disk space</button></div>
<p id="backupCadence" class="caption"></p><div id="storageUsage" class="health-grid"></div><p id="storageProgress" role="status" aria-live="polite"></p>
<details><summary>Storage planning estimate</summary><div id="storageForecast" class="health-grid"></div><p id="storageForecastNote" class="caption"></p><p class="caption">Uses the average storage per official game across this workspace, including retries and imported data. Different engines, game lengths and logging can change growth substantially. Includes paused tournaments and all configured recovery copies. Temporary space is an allowance, not a guarantee. External exports are excluded.</p></details>
<div class="form-grid"><label>Recovery copies<input id="backupCopies" type="number" min="2" max="10" step="1" data-help="Keep 2–10 rotating, verified recovery snapshots of the shared database. Default: 3. Lower retention is applied after a new backup is safely verified; Reclaim disk space applies it now."></label>
<label>Minimum backup interval (minutes)<input id="backupMinutes" type="number" min="1" max="60" step="1" data-help="Default: 5 minutes. Slow backups automatically run less often. Moves and results still commit transactionally after every move, independently of this recovery-copy interval."></label></div>
<div class="toolbar"><button id="saveStorageSettings" data-help="Save the recovery-copy count and minimum interval. Existing extra copies are removed only after a new verified backup, or when you run Reclaim disk space.">Save backup settings</button><span id="storageSettingsMessage" role="status"></span></div>
<p class="caption">Deleted database space is reused automatically. Use Reclaim disk space under Worker & recovery to shrink the files.</p>`;
$('#health').append(storagePanel);polishPanel(storagePanel);
const storageWarning=document.createElement('div');storageWarning.id='storageWarning';storageWarning.className='dialog-error';storageWarning.hidden=true;storageWarning.setAttribute('role','status');$('#notice').after(storageWarning);
let storageLoaded=false,storageBusy=false,storagePolling=false,storageLastPoll=0;
async function refreshStorage(){
 if(storagePolling||state.view!=='health'&&!storageBusy&&!state.deletingTid&&Date.now()-storageLastPoll<30000)return;
 storagePolling=true;storageLastPoll=Date.now();
 try{
  const s=await api('storage'),m=s.maintenance;storageBusy=!!m.busy;
  if(!storageLoaded){$('#backupCopies').value=s.settings.backup_copies;$('#backupMinutes').value=s.settings.backup_minutes;storageLoaded=true}
  stableHtml('#storageUsage',[[ArenaI18n.t('Database'),s.database_bytes],[ArenaI18n.t('Recovery backups'),s.backup_bytes],[ArenaI18n.t('PGN files'),s.pgn_bytes],[ArenaI18n.t('Transaction journal'),s.wal_bytes],[ArenaI18n.t('Temporary cleanup files'),s.temporary_bytes],[ArenaI18n.t('Total managed storage'),s.total_bytes],[ArenaI18n.t('Free drive space'),s.free_disk_bytes]].map(([label,value])=>statTile(label,ArenaFormat.bytes(value),'')).join(''));
  $('#backupCadence').textContent=ArenaI18n.m`Effective backup interval: ${ArenaI18n.number(s.effective_backup_seconds/60,{maximumFractionDigits:1})} minutes after the previous backup finishes.`;
  const f=s.forecast;
  storageWarning.hidden=!f?.warning;
  storageWarning.textContent=f?.warning?ArenaI18n.t('Storage space may be insufficient for scheduled games and recovery work. Check Worker & recovery → Storage planning estimate.'):'';
  stableHtml('#storageForecast',f?[[ArenaI18n.t('Estimated storage at completion'),f.projected_total_bytes],[ArenaI18n.t('Additional storage needed'),f.additional_bytes],[ArenaI18n.t('Temporary space allowance'),f.temporary_allowance_bytes]].map(([label,value])=>statTile(label,value===null?'—':ArenaFormat.bytes(value),'')).join(''):'');
  $('#storageForecastNote').textContent=!f?ArenaI18n.t('Available after storage maintenance.'):f.bytes_per_game===null?ArenaI18n.m`Estimate available after ${f.minimum_sample} official games. Growth depends on engines, game length and logging.`:ArenaI18n.m`${f.sample_games.toLocaleString(ArenaI18n.locale)} official games sampled · ${f.remaining_games.toLocaleString(ArenaI18n.locale)} scheduled games remaining`+(f.conditional?' · '+ArenaI18n.t('Conditional rounds, playoffs or early stopping can change this estimate.'):'');
  const message=m.error|| (m.busy?ArenaI18n.message(m.phase)+(m.attempts_packed?' · '+m.attempts_packed.toLocaleString(ArenaI18n.locale):'')+(m.lines_processed?' · '+m.lines_processed.toLocaleString(ArenaI18n.locale)+ArenaI18n.t(' log lines processed'):''):m.reclaimed_bytes!==undefined?ArenaI18n.t('Cleanup complete · ')+ArenaFormat.bytes(m.reclaimed_bytes)+ArenaI18n.t(' returned to Windows.'):ArenaI18n.m`${s.backup_count} recovery copies · ${ArenaFormat.bytes(s.reclaimable_bytes)} reusable database space${s.legacy_logs?ArenaI18n.t(' · older logs can be compressed'):''}.`);
  $('#storageProgress').textContent=message;
  if($('#deleteProgress'))$('#deleteProgress').textContent=message;
  $('#optimizeStorage').disabled=storageBusy;$('#saveStorageSettings').disabled=storageBusy;
 }catch(e){$('#storageProgress').textContent=e.message}finally{storagePolling=false}
}
$('#saveStorageSettings').onclick=safely(async()=>{
 if(!$('#backupCopies').reportValidity()||!$('#backupMinutes').reportValidity())return;
 await api('storage',{action:'settings',settings:{backup_copies:Number($('#backupCopies').value),backup_minutes:Number($('#backupMinutes').value)}});
 $('#storageSettingsMessage').textContent=ArenaI18n.t('Saved. Reclaim disk space applies the copy limit now.');await refreshStorage();
});
$('#optimizeStorage').onclick=safely(async()=>{
 $('#optimizeStorage').disabled=true;
 try{await api('storage',{action:'optimize'});storageBusy=true;await refreshStorage()}
 finally{if(!storageBusy)$('#optimizeStorage').disabled=false}
});
document.addEventListener('click',e=>{if(e.target.closest('[data-view="health"]'))setTimeout(refreshStorage,0)});
setInterval(refreshStorage,2000);
