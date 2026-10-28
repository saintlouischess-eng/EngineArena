'use strict';
(()=>{const key=new URLSearchParams(location.search).get('key'),form=document.getElementById('settings'),message=document.getElementById('message');let saved={};
 async function api(path,body){const r=await fetch(path+'?key='+encodeURIComponent(key),body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});if(!r.ok)throw Error(await r.text());return r.json()}
 function apply(c){saved=c;for(const [k,v]of Object.entries(c)){const e=form.elements.namedItem(k);if(e){if(e.type==='checkbox')e.checked=v;else e.value=v}}}
 document.getElementById('warmTvPreset').onclick=()=>{
  const preset={theme:'charcoal',pieces:'classic-bold',board_light:'ash',board_dark:'rosewood',dark_lighten:28,eval_range:4,ticker_seconds:150};
  for(const [k,v]of Object.entries(preset))form.elements.namedItem(k).value=v;
  message.textContent='Warm TV preset selected. Choose Apply to broadcast to save it.';
 };
 async function load(){try{const [r,ts]=await Promise.all([api('/config'),api('/tournaments')]);const select=document.getElementById('tournaments');for(const t of ts){const o=document.createElement('option');o.value=t.id;o.textContent=t.name+' ('+t.state+')';select.append(o)}apply(r.config);document.getElementById('preview').src=r.viewer_url;document.getElementById('url').textContent=r.viewer_url;document.getElementById('open').href=r.viewer_url;document.getElementById('copy').onclick=async()=>{try{await navigator.clipboard.writeText(r.viewer_url);message.textContent='OBS source URL copied.'}catch{message.textContent='Select and copy the URL above.'}}}catch(e){message.textContent='Cannot connect to the broadcast service. '+e.message}}
 form.onsubmit=async e=>{e.preventDefault();const c={...saved};for(const[k,v]of Object.entries(c)){const el=form.elements.namedItem(k);if(el)c[k]=typeof v==='boolean'?el.checked:typeof v==='number'?Number(el.value):el.value}try{apply((await api('/config',c)).config);message.textContent='Applied. Current game stays on air; selection preferences apply to the next game.'}catch(err){message.textContent=err.message}};load();
})();
