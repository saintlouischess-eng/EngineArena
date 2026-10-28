'use strict';
(()=>{
 const nav=document.createElement('button');nav.className='nav';nav.dataset.view='broadcast';nav.innerHTML='◉ <span>Broadcast</span>';$('nav').append(nav);
 const panel=document.createElement('section');panel.id='broadcast';panel.className='view';panel.hidden=true;
 const intro=document.createElement('div');intro.className='panel';intro.style.padding='24px';intro.innerHTML='<h2>Broadcast Designer</h2><p>Build a viewer-facing show for OBS and YouTube. The broadcast follows games from opening to result while you use other workspaces.</p><button id="launchBroadcast" class="primary">Open Broadcast Designer</button><p class="caption">The studio runs separately from the normal focused game. Create saved scenes, choose 2D or 3D, customize graphs and ticker colors, then apply your private preview to the stable OBS output.</p>';
 panel.append(intro);$('main').append(panel);let frame=null;
 nav.onclick=()=>{view('broadcast');$('#pageTitle').textContent='Broadcast workspace';$('#breadcrumb').textContent='BROADCAST'};
 $('#launchBroadcast').onclick=safely(async()=>{let r=await api('broadcast-launch',{});if(r.outdated){if(!confirm('The previous broadcast helper is still running. Restart only the broadcast helper to load this update? This briefly interrupts its video output. Tournament play is unaffected.'))return;r=await api('broadcast-launch',{restart:true})}if(!frame){frame=document.createElement('iframe');frame.title='Broadcast studio';frame.style='width:100%;height:calc(100vh - 180px);min-height:650px;border:0;border-radius:12px';frame.allow='autoplay; clipboard-write';panel.append(frame)}frame.src=r.control_url;intro.hidden=true});
})();
