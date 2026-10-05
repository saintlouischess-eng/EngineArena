(function(root){
 if(!root.ArenaI18n&&typeof require==='function')require('./i18n.js');
 'use strict';
 const fields={
  cpu_percent:[ArenaI18n.t('CPU load'),ArenaI18n.t('Processor'),'%',ArenaI18n.t('Average utilization across all logical processors.')],
  cpu_peak:[ArenaI18n.t('Busiest thread'),ArenaI18n.t('Processor'),'%',ArenaI18n.t('Highest utilization among logical processors; useful for single-thread tests.')],
  cpu_frequency:[ArenaI18n.t('CPU nominal clock'),ArenaI18n.t('Processor'),'GHz',ArenaI18n.t('OS-reported frequency. On Windows this is usually a nominal value, not live boost frequency.')],
  cpu_fastest_clock:[ArenaI18n.t('Fastest CPU core'),ArenaI18n.t('Processor'),'GHz',ArenaI18n.t('Highest current core clock reported by the CPU sensors in this sample. Updates at your selected refresh interval; brief boosts between samples can be missed. Enable CPU readings for this session to use it.')],
  cpu_temperature:[ArenaI18n.t('CPU temperature'),ArenaI18n.t('Processor'),'temperature',ArenaI18n.t('CPU die/package or the selected processor sensor, read through the bundled LibreHardwareMonitor reader and signed PawnIO driver.')],
  ram_used:[ArenaI18n.t('RAM used'),ArenaI18n.t('Memory'),'GiB',ArenaI18n.t('Physical memory used across the whole computer.')],
  ram_available:[ArenaI18n.t('RAM available'),ArenaI18n.t('Memory'),'GiB',ArenaI18n.t('Memory the operating system can make available to applications.')],
  ram_percent:[ArenaI18n.t('RAM load'),ArenaI18n.t('Memory'),'%',ArenaI18n.t('Physical memory utilization across the whole computer.')],
  ram_total:[ArenaI18n.t('RAM total'),ArenaI18n.t('Memory'),'GiB',ArenaI18n.t('Total physical memory reported by the operating system.')],
  swap_used:[ArenaI18n.t('Page file used'),ArenaI18n.t('Memory'),'GiB',ArenaI18n.t('System swap/page-file usage reported by the operating system.')],
  disk_free:[ArenaI18n.t('Data drive free'),ArenaI18n.t('Storage & network'),'GiB',ArenaI18n.t('Free space on the drive containing the tournament database.')],
  disk_percent:[ArenaI18n.t('Data drive used'),ArenaI18n.t('Storage & network'),'%',ArenaI18n.t('Used capacity of the drive containing the tournament database.')],
  disk_read:[ArenaI18n.t('Disk read'),ArenaI18n.t('Storage & network'),'MiB/s',ArenaI18n.t('Read throughput across all disks, not just tournament files.')],
  disk_write:[ArenaI18n.t('Disk write'),ArenaI18n.t('Storage & network'),'MiB/s',ArenaI18n.t('Write throughput across all disks, not just tournament files.')],
  network_receive:[ArenaI18n.t('Network receive'),ArenaI18n.t('Storage & network'),'MiB/s',ArenaI18n.t('Received bytes per second summed across network interfaces; virtual interfaces may also be included.')],
  network_send:[ArenaI18n.t('Network send'),ArenaI18n.t('Storage & network'),'MiB/s',ArenaI18n.t('Sent bytes per second summed across network interfaces; virtual interfaces may also be included.')],
  uptime:[ArenaI18n.t('System uptime'),ArenaI18n.t('Session'),'duration',ArenaI18n.t('Time since the computer booted, not time spent playing games.')],
  worker_memory:[ArenaI18n.t('Worker memory'),ArenaI18n.t('Session'),'MiB',ArenaI18n.t('Tournament worker working set. Engine and desktop processes have separate memory.')],
  active_games:[ArenaI18n.t('Active games'),ArenaI18n.t('Session'),'count',ArenaI18n.t('Currently active tournament games; independent of registered participant count.')],
  gpu_percent:[ArenaI18n.t('GPU load'),'GPU','%',ArenaI18n.t('Selected NVIDIA GPU utilization as reported by its driver.')],
  gpu_memory:[ArenaI18n.t('VRAM used'),'GPU','GiB',ArenaI18n.t('Selected GPU memory used and total, as reported by its driver.')],
  gpu_memory_percent:[ArenaI18n.t('VRAM load'),'GPU','%',ArenaI18n.t('Selected GPU used memory divided by its reported total.')],
  gpu_temperature:[ArenaI18n.t('GPU temperature'),'GPU','temperature',ArenaI18n.t('Selected GPU core temperature, when exposed by the driver.')],
  gpu_power:[ArenaI18n.t('GPU power'),'GPU','W',ArenaI18n.t('GPU power draw reported by the driver; not total computer power.')],
  gpu_power_limit:[ArenaI18n.t('GPU power limit'),'GPU','W',ArenaI18n.t('Configured GPU power limit. This control only reads it.')],
  gpu_clock:[ArenaI18n.t('GPU core clock'),'GPU','MHz',ArenaI18n.t('Current reported graphics clock for the selected GPU.')],
  gpu_memory_clock:[ArenaI18n.t('GPU memory clock'),'GPU','MHz',ArenaI18n.t('Current reported GPU memory clock, not effective transfer rate.')],
  gpu_fan:[ArenaI18n.t('GPU fan'),'GPU','%',ArenaI18n.t('Fan percentage reported by the GPU driver; not fan RPM.')]
 };
 const defaults={fields:['cpu_percent','ram_used'],interval:5,gpu:'auto',cpu_sensor:'auto',temperature_unit:'C'};
 function config(value){const v=value||{};return {fields:Array.isArray(v.fields)?[...new Set(v.fields.filter(k=>fields[k]))]:[...defaults.fields],interval:[2,5,10,30].includes(v.interval)?v.interval:5,gpu:typeof v.gpu==='string'?v.gpu:'auto',cpu_sensor:typeof v.cpu_sensor==='string'?v.cpu_sensor:'auto',temperature_unit:v.temperature_unit==='F'?'F':'C'};}
 function selectedGpu(snapshot,cfg){return cfg.gpu==='auto'?snapshot?.gpus?.[0]:snapshot?.gpus?.find(g=>g.id===cfg.gpu);}
 function selectedCpu(snapshot,cfg){
  const sensors=snapshot?.cpu?.sensors||[];if(cfg.cpu_sensor!=='auto')return sensors.find(s=>s.id===cfg.cpu_sensor);
  const rank=s=>{const name=s.name.toLowerCase();return [ArenaI18n.t('core (tdie)'),ArenaI18n.t('core (tctl/tdie)'),ArenaI18n.t('cpu package'),'package'].includes(name)?0:name.includes('package')?1:[ArenaI18n.t('core max'),ArenaI18n.t('core (tctl)')].includes(name)?2:3};
  return [...sensors].sort((a,b)=>rank(a)-rank(b)||b.celsius-a.celsius||a.id.localeCompare(b.id))[0];
 }
 function format(key,value,cfg,metrics={}){
  if(value===null||value===undefined||!Number.isFinite(value))return ArenaI18n.t('Unavailable');
  const unit=fields[key][2],n=(x,d=1)=>x.toLocaleString(ArenaI18n.locale,{maximumFractionDigits:d,minimumFractionDigits:0});
  if(unit==='temperature')return n(cfg.temperature_unit==='F'?value*9/5+32:value)+' °'+cfg.temperature_unit;
  if(unit==='duration'){const total=Math.floor(value/60);return [Math.floor(total/1440)+'d',Math.floor(total%1440/60)+'h',total%60+'m'].join(' ');}
  if(key==='gpu_memory')return n(value)+(Number.isFinite(metrics.gpu_memory_total)?' / '+n(metrics.gpu_memory_total):'')+ArenaI18n.t(' GiB');
  return n(value,unit==='count'||unit==='MHz'?0:unit==='GHz'?2:1)+(unit==='count'?'':unit==='%'?'%':' '+unit);
 }
 function readings(status,cfg){
  const snapshot=status?.hardware,gpu=selectedGpu(snapshot,cfg),stale=!snapshot||snapshot.stale||status?.disconnected;
  const metrics={...snapshot?.metrics,...gpu?.metrics,active_games:status?.active_games};
  const cpu=selectedCpu(snapshot,cfg);if(snapshot?.cpu?.sensors?.length)metrics.cpu_temperature=cpu?.celsius??null;
  return cfg.fields.map(key=>({key,label:fields[key][0],value:format(key,stale?null:metrics[key],cfg,metrics),
   help:fields[key][3]+(key==='cpu_fastest_clock'?' '+(snapshot?.cpu_fastest_core?snapshot.cpu_fastest_core.hardware+' · '+snapshot.cpu_fastest_core.name:snapshot?.notes?.cpu_fastest_clock||ArenaI18n.t('Live core clocks are unavailable.')):'')+(key==='cpu_temperature'?' '+(cpu?cpu.hardware+' · '+cpu.name:snapshot?.notes?.cpu_temperature||ArenaI18n.t('Selected CPU sensor is unavailable.')):'')+(key.startsWith('gpu_')?' '+(gpu?gpu.name+ArenaI18n.t(' · driver ')+gpu.driver:snapshot?.notes?.gpu||ArenaI18n.t('Selected GPU is unavailable.')):'')+(stale?ArenaI18n.t(' Waiting for current hardware data.'):'')}));
 }
 const api={fields,defaults,config,selectedGpu,selectedCpu,format,readings};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ArenaHardware=api;
})(typeof globalThis!=='undefined'?globalThis:this);
