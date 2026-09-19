'use strict';
const poolButton=document.createElement('button');poolButton.id='poolRatings';poolButton.textContent='Pool ratings';
$('#openingReport').after(poolButton);poolButton.onclick=safely(poolRatingsDialog);
async function poolRatingsDialog(){
  if(!state.tid)return;const tid=state.tid;let offset=0,total=0,generation=0,timer,searchTimer,peopleOffset=0,peopleTotal=0,peopleGeneration=0,anchor=null;
  modal('Anchored pool ratings',`<p class="caption">Fit every connected engine against the pool, with one fixed reference rating. Only completed opening pairs enter paired estimates. No finite estimate is reported for disconnected or separated results.</p>
    <div class="form-grid"><label>Find reference engine<input id="anchorSearch" placeholder="Search tournament participants"></label><label>Reference engine<select id="anchorEngine" aria-label="Reference engine"></select></label><label>Fixed reference rating<input id="anchorRating" type="number" step="any" value="0"></label></div>
    <div class="pager"><button id="anchorPrev">←</button><span id="anchorPage"></span><button id="anchorNext">→</button><button id="saveAnchor">Apply reference</button></div>
    <p id="ratingStatus" role="status">Calculating ratings…</p><input id="ratingSearch" placeholder="Filter rating rows by engine name"><div class="table-scroll"><table><thead><tr><th>ENGINE</th><th>RATING</th><th>Δ REFERENCE</th><th>${state.confidence||95}% CI</th><th>LOS VS REFERENCE</th><th>SAMPLES</th><th>STATUS</th></tr></thead><tbody id="poolRows"></tbody></table></div>
    <div class="pager"><button id="ratingPrev">←</button><span id="ratingPage"></span><button id="ratingNext">→</button></div><p id="ratingModel" class="caption"></p><p class="caption">Normal sandwich intervals use independent pair scores (individual games when unpaired). They are approximate, can be unreliable in small samples, and do not include uncertainty in the reference rating. No stopping rule is implied. Participant order stays fixed while ratings update.</p>`,
    '<button id="ratingCsv">Export all ratings · CSV</button><button id="ratingJson">JSON</button>');
  const root=$('#ratingStatus'),alive=()=>$('#modal').open&&$('#ratingStatus')===root;
  const labels={fixed_anchor:'Fixed reference',estimated:'Estimated',disconnected:'No comparison path to reference',no_comparisons:'No completed comparisons',no_finite_fit:'No finite fit: separated results',not_converged:'Fit did not converge',uncertainty_unavailable:'Uncertainty unavailable',uncertainty_not_converged:'Uncertainty did not converge'};
  const people=async()=>{
    const version=++peopleGeneration;
    try{
      const r=await api(`tournaments/${tid}/participants?q=${encodeURIComponent($('#anchorSearch').value)}&offset=${peopleOffset}`);
      if(!alive()||version!==peopleGeneration)return;peopleTotal=r.total;
      const choices=[...(anchor?[anchor]:[]),...r.items.filter(p=>p.slot!==anchor?.slot)];
      $('#anchorEngine').innerHTML=choices.map(p=>`<option value="${p.slot}">#${p.slot+1} ${esc(p.name)}</option>`).join('');if(anchor)$('#anchorEngine').value=anchor.slot;
      $('#anchorPage').textContent=r.total?`${peopleOffset+1}–${Math.min(peopleOffset+50,r.total)} of ${r.total.toLocaleString()} profiles`:'No matches';$('#anchorPrev').disabled=peopleOffset===0;$('#anchorNext').disabled=peopleOffset+50>=r.total;
    }catch(e){if(alive())root.textContent=e.message;}
  };
  const refresh=async()=>{
    const version=++generation;clearTimeout(timer);root.textContent='Updating pool ratings…';
    try{
      const r=await api(`tournaments/${tid}/ratings?offset=${offset}&q=${encodeURIComponent($('#ratingSearch').value)}`);
      if(!alive()||version!==generation)return;total=r.total;
      if(!anchor){anchor=r.anchor;$('#anchorRating').value=anchor.rating;await people();if(!alive()||version!==generation)return;}
      root.textContent=`${r.samples.toLocaleString()} ${r.sample_unit} · ${r.connected_participants.toLocaleString()} of ${r.participant_count.toLocaleString()} participants connected · reference ${r.anchor.name} = ${fmt(r.anchor.rating)} · updated ${new Date().toLocaleTimeString()}`;
      stableHtml('#poolRows',r.items.map(x=>`<tr><td>#${x.slot+1} ${esc(x.name)}</td><td>${fmt(x.rating)}</td><td>${fmt(x.delta)}</td><td>${x.ci?x.ci.map(y=>fmt(y)).join(' to '):'—'}</td><td>${pct(x.los)}</td><td>${x.samples.toLocaleString()}</td><td>${labels[x.status]||esc(x.status)}</td></tr>`).join(''));
      $('#ratingPage').textContent=r.total?`${offset+1}–${Math.min(offset+50,r.total)} of ${r.total.toLocaleString()} engines`:'No matching engines';$('#ratingPrev').disabled=offset===0;$('#ratingNext').disabled=offset+50>=total;$('#ratingModel').textContent=r.model+'. '+r.assumptions;
    }catch(e){if(alive()&&version===generation)root.textContent=e.message;}
    if(alive()&&version===generation)timer=setTimeout(refresh,3000);
  };
  $('#saveAnchor').onclick=safely(async()=>{const rating=Number($('#anchorRating').value),slot=Number($('#anchorEngine').value);if($('#anchorRating').value.trim()===''||!Number.isFinite(rating))throw Error('Enter a finite reference rating');await api(`tournaments/${tid}/ratings`,{slot,rating});if(alive()){anchor=null;await refresh();}});
  $('#anchorSearch').oninput=()=>{++peopleGeneration;peopleOffset=0;clearTimeout(searchTimer);searchTimer=setTimeout(()=>{if(alive())people();},180);};
  $('#anchorPrev').onclick=()=>{peopleOffset=Math.max(0,peopleOffset-50);people();};$('#anchorNext').onclick=()=>{if(peopleOffset+50<peopleTotal){peopleOffset+=50;people();}};
  $('#ratingSearch').oninput=()=>{++generation;offset=0;clearTimeout(timer);timer=setTimeout(()=>{if(alive())refresh();},250);};
  $('#ratingPrev').onclick=()=>{offset=Math.max(0,offset-50);refresh();};$('#ratingNext').onclick=()=>{if(offset+50<total){offset+=50;refresh();}};
  for(const format of ['Csv','Json'])$('#rating'+format).onclick=()=>window.open(`/api/tournaments/${tid}/ratings?export=${format.toLowerCase()}&confidence=${state.confidence||95}&token=${encodeURIComponent(token)}`,'_blank');
  await refresh();
}
