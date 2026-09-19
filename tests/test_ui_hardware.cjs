const test=require('node:test'),assert=require('node:assert/strict');
const H=require('../ui/hardware-model.js');
test('format temperature, VRAM, nominal frequency and unavailable data honestly',()=>{
 const c=H.config({temperature_unit:'F'});
 assert.equal(H.format('gpu_temperature',40,c),'104 °F');
 assert.equal(H.format('gpu_memory',4,c,{gpu_memory_total:16}),'4 / 16 GiB');
 assert.equal(H.format('gpu_percent',null,c),'Unavailable');
 assert.equal(H.format('gpu_percent',0,c),'0%');
 assert.equal(H.format('cpu_frequency',4.001,c),'4 GHz');
});
test('saved selection order and an explicitly hidden display are retained',()=>{
 assert.deepEqual(H.config({fields:[]}).fields,[]);
 assert.deepEqual(H.config({fields:['gpu_power','ram_used','gpu_power','unknown']}).fields,['gpu_power','ram_used']);
});
test('missing selected GPU never silently switches to another device',()=>{
 const status={hardware:{metrics:{ram_used:5},gpus:[{id:'one',name:'First',metrics:{gpu_percent:80}}],stale:false}};
 let c=H.config({fields:['gpu_percent','ram_used'],gpu:'missing'});
 assert.deepEqual(H.readings(status,c).map(r=>r.value),['Unavailable','5 GiB']);
 c=H.config({fields:['gpu_percent'],gpu:'one'});assert.equal(H.readings(status,c)[0].value,'80%');
});
test('stale and disconnected values do not appear current',()=>{
 const status={active_games:4,hardware:{metrics:{cpu_percent:75},stale:true}};
 const c=H.config({fields:['cpu_percent','active_games']});
 assert.ok(H.readings(status,c).every(r=>r.value==='Unavailable'));
 status.hardware.stale=false;status.disconnected=true;
 assert.ok(H.readings(status,c).every(r=>r.value==='Unavailable'));
});
test('CPU sensor selection prefers the package, allows a CCD and retains missing choice',()=>{
 const status={hardware:{stale:false,metrics:{},cpu:{sensors:[{id:'ccd',name:'CCD1',hardware:'CPU',celsius:75},{id:'die',name:'Core (Tctl/Tdie)',hardware:'CPU',celsius:65}]}}};
 let c=H.config({fields:['cpu_temperature']});assert.equal(H.readings(status,c)[0].value,'65 °C');
 c=H.config({fields:['cpu_temperature'],cpu_sensor:'ccd',temperature_unit:'F'});assert.equal(H.readings(status,c)[0].value,'167 °F');
 c=H.config({fields:['cpu_temperature'],cpu_sensor:'missing'});assert.equal(H.readings(status,c)[0].value,'Unavailable');
});
test('fastest live CPU core is distinct from nominal and unavailable when stale or missing',()=>{
 const cfg=H.config({fields:['cpu_fastest_clock','cpu_frequency']});
 const status={hardware:{stale:false,metrics:{cpu_fastest_clock:5.257,cpu_frequency:4.001},cpu_fastest_core:{hardware:'Threadripper',name:'Core #12',mhz:5257}}};
 const values=H.readings(status,cfg);assert.deepEqual(values.map(r=>r.value),['5.26 GHz','4 GHz']);assert.ok(values[0].help.includes('Core #12'));
 status.hardware.metrics.cpu_fastest_clock=null;assert.equal(H.readings(status,cfg)[0].value,'Unavailable');
 status.hardware.stale=true;assert.ok(H.readings(status,cfg).every(r=>r.value==='Unavailable'));
});
