(function(root){
 'use strict';
 const fields={
  cpu_percent:['CPU load','Processor','%','Average utilization across all logical processors.'],
  cpu_peak:['Busiest thread','Processor','%','Highest utilization among logical processors; useful for single-thread tests.'],
  cpu_frequency:['CPU nominal clock','Processor','GHz','OS-reported frequency. On Windows this is usually a nominal value, not live boost frequency.'],
  cpu_fastest_clock:['Fastest CPU core','Processor','GHz','Highest current core clock reported by the CPU sensors in this sample. Updates at your selected refresh interval; brief boosts between samples can be missed. Enable CPU readings for this session to use it.'],
  cpu_temperature:['CPU temperature','Processor','temperature','CPU die/package or the selected processor sensor, read through the bundled LibreHardwareMonitor reader and signed PawnIO driver.'],
  ram_used:['RAM used','Memory','GiB','Physical memory used across the whole computer.'],
  ram_available:['RAM available','Memory','GiB','Memory the operating system can make available to applications.'],
  ram_percent:['RAM load','Memory','%','Physical memory utilization across the whole computer.'],
  ram_total:['RAM total','Memory','GiB','Total physical memory reported by the operating system.'],
  swap_used:['Page file used','Memory','GiB','System swap/page-file usage reported by the operating system.'],
  disk_free:['Data drive free','Storage & network','GiB','Free space on the drive containing the tournament database.'],
  disk_percent:['Data drive used','Storage & network','%','Used capacity of the drive containing the tournament database.'],
  disk_read:['Disk read','Storage & network','MiB/s','Read throughput across all disks, not just tournament files.'],
  disk_write:['Disk write','Storage & network','MiB/s','Write throughput across all disks, not just tournament files.'],
  network_receive:['Network receive','Storage & network','MiB/s','Received bytes per second summed across network interfaces; virtual interfaces may also be included.'],
  network_send:['Network send','Storage & network','MiB/s','Sent bytes per second summed across network interfaces; virtual interfaces may also be included.'],
  uptime:['System uptime','Session','duration','Time since the computer booted, not time spent playing games.'],
  worker_memory:['Worker memory','Session','MiB','Tournament worker working set. Engine and desktop processes have separate memory.'],
  active_games:['Active games','Session','count','Currently active tournament games; independent of registered participant count.'],
  gpu_percent:['GPU load','GPU','%','Selected NVIDIA GPU utilization as reported by its driver.'],
  gpu_memory:['VRAM used','GPU','GiB','Selected GPU memory used and total, as reported by its driver.'],
  gpu_memory_percent:['VRAM load','GPU','%','Selected GPU used memory divided by its reported total.'],
  gpu_temperature:['GPU temperature','GPU','temperature','Selected GPU core temperature, when exposed by the driver.'],
  gpu_power:['GPU power','GPU','W','GPU power draw reported by the driver; not total computer power.'],
  gpu_power_limit:['GPU power limit','GPU','W','Configured GPU power limit. This control only reads it.'],
  gpu_clock:['GPU core clock','GPU','MHz','Current reported graphics clock for the selected GPU.'],
  gpu_memory_clock:['GPU memory clock','GPU','MHz','Current reported GPU memory clock, not effective transfer rate.'],
  gpu_fan:['GPU fan','GPU','%','Fan percentage reported by the GPU driver; not fan RPM.']
 };
 const defaults={fields:['cpu_percent','ram_used'],interval:5,gpu:'auto',cpu_sensor:'auto',temperature_unit:'C'};
 function config(value){const v=value||{};return {fields:Array.isArray(v.fields)?[...new Set(v.fields.filter(k=>fields[k]))]:[...defaults.fields],interval:[2,5,10,30].includes(v.interval)?v.interval:5,gpu:typeof v.gpu==='string'?v.gpu:'auto',cpu_sensor:typeof v.cpu_sensor==='string'?v.cpu_sensor:'auto',temperature_unit:v.temperature_unit==='F'?'F':'C'};}
 function selectedGpu(snapshot,cfg){return cfg.gpu==='auto'?snapshot?.gpus?.[0]:snapshot?.gpus?.find(g=>g.id===cfg.gpu);}
 function selectedCpu(snapshot,cfg){
  const sensors=snapshot?.cpu?.sensors||[];if(cfg.cpu_sensor!=='auto')return sensors.find(s=>s.id===cfg.cpu_sensor);
  const rank=s=>{const name=s.name.toLowerCase();return ['core (tdie)','core (tctl/tdie)','cpu package','package'].includes(name)?0:name.includes('package')?1:['core max','core (tctl)'].includes(name)?2:3};
  return [...sensors].sort((a,b)=>rank(a)-rank(b)||b.celsius-a.celsius||a.id.localeCompare(b.id))[0];
 }
 function format(key,value,cfg,metrics={}){
  if(value===null||value===undefined||!Number.isFinite(value))return 'Unavailable';
  const unit=fields[key][2],n=(x,d=1)=>x.toLocaleString(undefined,{maximumFractionDigits:d,minimumFractionDigits:0});
  if(unit==='temperature')return n(cfg.temperature_unit==='F'?value*9/5+32:value)+' °'+cfg.temperature_unit;
  if(unit==='duration'){const total=Math.floor(value/60);return [Math.floor(total/1440)+'d',Math.floor(total%1440/60)+'h',total%60+'m'].join(' ');}
  if(key==='gpu_memory')return n(value)+(Number.isFinite(metrics.gpu_memory_total)?' / '+n(metrics.gpu_memory_total):'')+' GiB';
  return n(value,unit==='count'||unit==='MHz'?0:unit==='GHz'?2:1)+(unit==='count'?'':unit==='%'?'%':' '+unit);
 }
 function readings(status,cfg){
  const snapshot=status?.hardware,gpu=selectedGpu(snapshot,cfg),stale=!snapshot||snapshot.stale||status?.disconnected;
  const metrics={...snapshot?.metrics,...gpu?.metrics,active_games:status?.active_games};
  const cpu=selectedCpu(snapshot,cfg);if(snapshot?.cpu?.sensors?.length)metrics.cpu_temperature=cpu?.celsius??null;
  return cfg.fields.map(key=>({key,label:fields[key][0],value:format(key,stale?null:metrics[key],cfg,metrics),
   help:fields[key][3]+(key==='cpu_fastest_clock'?' '+(snapshot?.cpu_fastest_core?snapshot.cpu_fastest_core.hardware+' · '+snapshot.cpu_fastest_core.name:snapshot?.notes?.cpu_fastest_clock||'Live core clocks are unavailable.'):'')+(key==='cpu_temperature'?' '+(cpu?cpu.hardware+' · '+cpu.name:snapshot?.notes?.cpu_temperature||'Selected CPU sensor is unavailable.'):'')+(key.startsWith('gpu_')?' '+(gpu?gpu.name+' · driver '+gpu.driver:snapshot?.notes?.gpu||'Selected GPU is unavailable.'):'')+(stale?' Waiting for current hardware data.':'')}));
 }
 const api={fields,defaults,config,selectedGpu,selectedCpu,format,readings};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ArenaHardware=api;
})(typeof globalThis!=='undefined'?globalThis:this);
