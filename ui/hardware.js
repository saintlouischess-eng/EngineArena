'use strict';
const hardwareBar=document.createElement('section');hardwareBar.className='hardware-bar';hardwareBar.setAttribute('aria-label','Computer hardware');
hardwareBar.innerHTML='<div id="hardwareReadings" class="hardware-readings"></div><div class="hardware-actions"><button id="configureHardware" data-help="Choose the hardware readings shown here, their order, GPU, temperature units and refresh interval.">Hardware display…</button><small id="hardwareFreshness"></small></div>';
document.querySelector('main > header').after(hardwareBar);$('#resources').remove();
let lastHardwareStatus=null;
function renderHardware(status){
 lastHardwareStatus=status;const cfg=ArenaHardware.config(displayPrefs.hardware),snapshot=status?.hardware;
 stableHtml('#hardwareReadings',ArenaHardware.readings(status,cfg).map(r=>`<div class="hardware-reading" tabindex="0" data-help="${esc(r.help)}"><span>${esc(r.label)}</span><strong>${esc(r.value)}</strong></div>`).join('')||'<span class="muted">Hardware readings hidden</span>');
 $('#hardwareFreshness').textContent=status?.disconnected?'Worker disconnected':!snapshot||snapshot.stale?'Waiting for readings…':`Every ${cfg.interval}s · sampled ${Math.floor(snapshot?.age_seconds||0)}s ago`;
 hardwareBar.classList.toggle('hardware-stale',!!(status?.disconnected||snapshot?.stale));
}
function hardwareDisconnected(){renderHardware({...lastHardwareStatus,disconnected:true})}
async function hardwareDialog(){
 const cfg=ArenaHardware.config(displayPrefs.hardware);let selected=[...cfg.fields],snapshot=lastHardwareStatus?.hardware;
 const groups=[...new Set(Object.values(ArenaHardware.fields).map(v=>v[1]))];
 modal('Hardware display',`<p class="hardware-description">Choose the readings to show at the top. These settings are saved for this workspace. Monitoring reads sensors only.</p><div id="hardwareIdentity" class="hardware-identity">Detecting hardware…</div><div class="fields hardware-settings"><label>Refresh interval<select id="hardwareInterval" aria-label="Hardware refresh interval">${[2,5,10,30].map(n=>`<option value="${n}" ${cfg.interval===n?'selected':''}>Every ${n} seconds</option>`).join('')}</select></label><label>Temperature units<select id="hardwareTemperature" aria-label="Hardware temperature units"><option value="C" ${cfg.temperature_unit==='C'?'selected':''}>Celsius (°C)</option><option value="F" ${cfg.temperature_unit==='F'?'selected':''}>Fahrenheit (°F)</option></select></label><label class="full">GPU<select id="hardwareGpu" aria-label="Hardware GPU"><option value="auto">First detected NVIDIA GPU</option></select></label><label class="full">CPU temperature sensor<select id="hardwareCpuSensor" aria-label="CPU temperature sensor"><option value="auto">Automatic CPU die/package (hottest package)</option></select></label></div><div class="hardware-presets"><button id="cpuSensorSetup">CPU sensor setup…</button><button id="enableCpuReadings" data-help="Approve Windows permission for the separate CPU sensor reader. The reader closes with this app; chess engines keep normal permissions.">Enable CPU readings for this session</button><button id="probeCpuAgain">Check sensors again</button></div><p id="hardwareSensorNote" class="hardware-description"></p><div class="hardware-presets"><button data-hardware-preset="basic">CPU & RAM</button><button data-hardware-preset="testing">Engine testing</button><button data-hardware-preset="gpu">CPU, RAM & GPU</button><button data-hardware-preset="none">Hide readings</button></div><div class="hardware-choices">${groups.map(group=>`<fieldset><legend>${esc(group)}</legend>${Object.entries(ArenaHardware.fields).filter(([,v])=>v[1]===group).map(([key,v])=>`<label data-help="${esc(v[3])}"><input type="checkbox" data-hardware-field="${key}" aria-label="${esc(v[0])}" ${selected.includes(key)?'checked':''}>${esc(v[0])}<small data-hardware-value="${key}"></small></label>`).join('')}</fieldset>`).join('')}</div><h3>Display order</h3><p class="hardware-description">Move selected readings up or down to arrange them from left to right.</p><div id="hardwareOrder" class="hardware-order"></div>`,`<button id="saveHardware" class="primary">Save hardware display</button>`);
 const dialogBody=$('#hardwareIdentity');let chosenGpu=cfg.gpu,chosenCpu=cfg.cpu_sensor;
 function drawOrder(){stableHtml('#hardwareOrder',selected.map((key,i)=>`<div><span>${esc(ArenaHardware.fields[key][0])}</span><button data-hardware-up="${key}" aria-label="Move ${esc(ArenaHardware.fields[key][0])} earlier" ${!i?'disabled':''}>↑</button><button data-hardware-down="${key}" aria-label="Move ${esc(ArenaHardware.fields[key][0])} later" ${i===selected.length-1?'disabled':''}>↓</button></div>`).join('')||'<p class="muted">No readings selected. The configuration button stays visible.</p>')}
 function showSensors(){
  if(!dialogBody.isConnected)return;
  const identity=snapshot?.identity||{},gpuCfg={...cfg,gpu:$('#hardwareGpu').value,cpu_sensor:$('#hardwareCpuSensor').value,fields:Object.keys(ArenaHardware.fields),temperature_unit:$('#hardwareTemperature').value};
  $('#hardwareIdentity').textContent=[identity.cpu_name,identity.physical_cores?`${identity.physical_cores} physical cores · ${identity.logical_cpus} logical processors`:''].filter(Boolean).join(' — ')||'Hardware identity unavailable';
  $('#hardwareSensorNote').textContent=[...new Set([snapshot?.notes?.gpu, snapshot?.notes?.cpu_temperature, snapshot?.notes?.cpu_fastest_clock,'Disk activity covers all disks; free space refers to the tournament data drive. Unavailable sensors are never shown as zero.'].filter(Boolean))].join(' ');
  for(const reading of ArenaHardware.readings({...lastHardwareStatus,hardware:snapshot},gpuCfg))$(`[data-hardware-value="${reading.key}"]`).textContent=reading.value;
 }
 function setDevices(){
  const items=snapshot?.gpus||[],cpus=snapshot?.cpu?.sensors||[];
  $('#hardwareGpu').innerHTML='<option value="auto">First detected NVIDIA GPU</option>'+items.map(g=>`<option value="${esc(g.id)}">${esc(g.name)} · GPU ${esc(g.index)}</option>`).join('')+(chosenGpu!=='auto'&&!items.some(g=>g.id===chosenGpu)?`<option value="${esc(chosenGpu)}">Selected GPU currently unavailable</option>`:'');$('#hardwareGpu').value=chosenGpu;
  $('#hardwareCpuSensor').innerHTML='<option value="auto">Automatic CPU die/package (hottest package)</option>'+cpus.map(s=>`<option value="${esc(s.id)}">${esc(s.hardware)} · ${esc(s.name)} (${Number(s.celsius).toFixed(1)} °C)</option>`).join('')+(chosenCpu!=='auto'&&!cpus.some(s=>s.id===chosenCpu)?`<option value="${esc(chosenCpu)}">Selected CPU sensor unavailable</option>`:'');$('#hardwareCpuSensor').value=chosenCpu;
  showSensors();
 }
 $$('[data-hardware-field]').forEach(input=>input.onchange=()=>{selected=selected.filter(k=>k!==input.dataset.hardwareField);if(input.checked)selected.push(input.dataset.hardwareField);drawOrder()});
 $('#hardwareOrder').onclick=e=>{const up=e.target.closest('[data-hardware-up]'),down=e.target.closest('[data-hardware-down]');if(!up&&!down)return;const key=up?.dataset.hardwareUp||down.dataset.hardwareDown,index=selected.indexOf(key),other=index+(up?-1:1);if(other>=0&&other<selected.length){[selected[index],selected[other]]=[selected[other],selected[index]];drawOrder()}};
 $$('[data-hardware-preset]').forEach(button=>button.onclick=()=>{selected={basic:['cpu_percent','ram_used'],testing:['cpu_percent','cpu_peak','cpu_fastest_clock','ram_available','disk_free','active_games'],gpu:['cpu_percent','ram_used','gpu_percent','gpu_memory','gpu_temperature','gpu_power'],none:[]}[button.dataset.hardwarePreset];$$('[data-hardware-field]').forEach(input=>input.checked=selected.includes(input.dataset.hardwareField));drawOrder()});
 $('#hardwareCpuSensor').onchange=()=>{chosenCpu=$('#hardwareCpuSensor').value;showSensors()};$('#hardwareGpu').onchange=()=>{chosenGpu=$('#hardwareGpu').value;showSensors()};$('#hardwareTemperature').onchange=showSensors;
 $('#saveHardware').onclick=safely(async()=>{displayPrefs.hardware={fields:selected,interval:Number($('#hardwareInterval').value),gpu:$('#hardwareGpu').value,cpu_sensor:$('#hardwareCpuSensor').value,temperature_unit:$('#hardwareTemperature').value};await persistDisplay();renderHardware(lastHardwareStatus);$('#modal').close();notify('Hardware display saved.')});
 $('#cpuSensorSetup').onclick=()=>{modal('Enable CPU sensors',`<p>Engine Arena includes its own CPU sensor reader using LibreHardwareMonitor. Windows also needs the signed <b>PawnIO</b> hardware-access driver.</p><p>The beta installer includes the official driver setup for offline use. Install the signed edition once, approve the Windows administrator prompt, then choose <b>Enable CPU readings for this session</b> in Hardware display. Approve the separate reader each time you open the app and want temperatures. Select CPU temperature and/or Fastest CPU core, then save the display. Keep Windows security protections enabled.</p><p>The reader reports available CPU die/package and other processor temperature sensors, plus current per-core clock speeds when available. Only this separate reader receives administrator permission; the app and engines keep normal permissions. The reader closes automatically when the app closes, including after a crash. It does not change clocks, fan settings or voltages. Hardware and driver support determine which sensors are available.</p>`,`<button id="openCpuDriverPage" class="primary">Open CPU driver setup</button><button id="backToHardware">Back to hardware display</button>`);$('#openCpuDriverPage').onclick=()=>{if(window.chrome?.webview)window.chrome.webview.postMessage({type:'cpuSensorSetup'});else window.open('https://pawnio.eu/','_blank','noopener')};$('#backToHardware').onclick=safely(hardwareDialog)};
 $('#enableCpuReadings').onclick=()=>{
  if(!window.chrome?.webview){notify('Enable CPU readings in the Engine Arena desktop window for this session.',true);return}
  $('#enableCpuReadings').disabled=true;$('#hardwareSensorNote').textContent='Waiting for Windows permission and CPU sensor detection…';window.chrome.webview.postMessage({type:'enableCpuSensors'});
 };
 $('#probeCpuAgain').onclick=safely(async()=>{snapshot=await api('hardware');if(dialogBody.isConnected)setDevices()});
 drawOrder();setDevices();
 try{snapshot=await api('hardware');if(dialogBody.isConnected)setDevices()}catch(e){if(dialogBody.isConnected)$('#hardwareSensorNote').textContent=e.message}
}
$('#configureHardware').onclick=safely(hardwareDialog);
renderHardware(null);

window.chrome?.webview?.addEventListener('message',e=>{
 if(e.data?.type!=='cpuSensorsEnabled')return;
 const button=$('#enableCpuReadings');if(button)button.disabled=false;
 notify(e.data.message,!e.data.ok);
 if($('#hardwareSensorNote'))$('#hardwareSensorNote').textContent=e.data.message;
 if(e.data.ok&&$('#probeCpuAgain'))$('#probeCpuAgain').click();
});
