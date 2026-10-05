'use strict';
const poolButton=document.createElement('button');poolButton.id='poolRatings';poolButton.textContent=ArenaI18n.t('Pool ratings');
$('#openingReport').after(poolButton);poolButton.onclick=safely(poolRatingsDialog);
async function poolRatingsDialog(){
  if(!state.tid)return;const tid=state.tid;let offset=0,total=0,generation=0,timer,searchTimer,peopleOffset=0,peopleTotal=0,peopleGeneration=0,anchor=null,sort='rating',direction='desc';
  const columns=[['slot',ArenaI18n.t('PARTICIPANT ID')],['name','ENGINE'],['rating','RATING'],['delta',ArenaI18n.t('Δ REFERENCE')],['ci',ArenaI18n.m`${state.confidence||95}% CI`],['los',ArenaI18n.t('LOS VS REFERENCE')],['samples','SAMPLES'],['status','STATUS']];
  modal(ArenaI18n.t('Anchored pool ratings'),ArenaI18n.h`<p class="caption">Fit every connected engine against the pool, with one fixed reference rating. Only completed opening pairs enter paired estimates. No finite estimate is reported for disconnected or separated results.</p>
    <div class="form-grid"><label>Find reference engine<input id="anchorSearch" placeholder="Search tournament participants"></label><label>Reference engine<select id="anchorEngine" aria-label="Reference engine"></select></label><label>Fixed reference rating<input id="anchorRating" type="number" step="any" value="0"></label></div>
    <div class="pager"><button id="anchorPrev">←</button><span id="anchorPage"></span><button id="anchorNext">→</button><button id="saveAnchor">Apply reference</button></div>
    <p id="ratingStatus" role="status">Calculating ratings…</p><input id="ratingSearch" placeholder="Filter rating rows by engine name"><div class="table-scroll"><table class="sortable-table" id="poolTable"><thead><tr>${columns.map(([key,label])=>ArenaI18n.h`<th aria-sort="none"><button data-pool-sort="${key}" data-help="${key==='ci'?ArenaI18n.t('Sort by confidence interval width; narrower intervals are more precise.'):ArenaI18n.t('Sort all matching engines by ')+label+'.'} Click again to reverse. Unavailable values stay last.">${label}<span class="sort-arrow"></span></button></th>`).join('')}</tr></thead><tbody id="poolRows"></tbody></table></div>
    <div class="pager"><button id="ratingPrev" aria-label="Previous ratings page">←</button><span id="ratingPage"></span><button id="ratingNext" aria-label="Next ratings page">→</button></div><p id="ratingModel" class="caption"></p><p class="caption">Normal sandwich intervals use independent pair scores (individual games when unpaired). They are approximate, can be unreliable in small samples, and do not include uncertainty in the reference rating. No stopping rule is implied. Click a header to sort the whole pool; selected order is retained during live updates. CI sorts by interval width. Participant ID is registration order, not rank. The default view is Rating, highest first.</p>`,
    ArenaI18n.h('<button id="ratingCsv">Export all ratings · CSV</button><button id="ratingJson">JSON</button><button id="ratingText">All ratings · Text…</button>'));
  const root=$('#ratingStatus'),alive=()=>$('#modal').open&&$('#ratingStatus')===root;
  const labels={fixed_anchor:ArenaI18n.t('Fixed reference'),estimated:ArenaI18n.t('Estimated'),disconnected:ArenaI18n.t('No comparison path to reference'),no_comparisons:ArenaI18n.t('No completed comparisons'),no_finite_fit:ArenaI18n.t('No finite fit: separated results'),not_converged:ArenaI18n.t('Fit did not converge'),uncertainty_unavailable:ArenaI18n.t('Uncertainty unavailable'),uncertainty_not_converged:ArenaI18n.t('Uncertainty did not converge')};
  const people=async()=>{
    const version=++peopleGeneration;
    try{
      const r=await api(`tournaments/${tid}/participants?q=${encodeURIComponent($('#anchorSearch').value)}&offset=${peopleOffset}`);
      if(!alive()||version!==peopleGeneration)return;peopleTotal=r.total;
      const choices=[...(anchor?[anchor]:[]),...r.items.filter(p=>p.slot!==anchor?.slot)];
      $('#anchorEngine').innerHTML=choices.map(p=>ArenaI18n.h`<option value="${p.slot}">ID ${p.slot+1} · ${esc(p.name)}</option>`).join('');if(anchor)$('#anchorEngine').value=anchor.slot;
      $('#anchorPage').textContent=r.total?ArenaI18n.m`${peopleOffset+1}–${Math.min(peopleOffset+50,r.total)} of ${r.total.toLocaleString(ArenaI18n.locale)} profiles`:ArenaI18n.t('No matches');$('#anchorPrev').disabled=peopleOffset===0;$('#anchorNext').disabled=peopleOffset+50>=r.total;
    }catch(e){if(alive())root.textContent=e.message;}
  };
  const refresh=async()=>{
    const version=++generation;clearTimeout(timer);root.textContent=ArenaI18n.t('Updating pool ratings…');
    try{
      const r=await api(`tournaments/${tid}/ratings?offset=${offset}&q=${encodeURIComponent($('#ratingSearch').value)}&sort=${sort}&direction=${direction}&confidence=${state.confidence||95}`);
      if(!alive()||version!==generation)return;total=r.total;
      if(!anchor){anchor=r.anchor;$('#anchorRating').value=anchor.rating;await people();if(!alive()||version!==generation)return;}
      root.textContent=ArenaI18n.m`${r.samples.toLocaleString(ArenaI18n.locale)} ${ArenaI18n.message(r.sample_unit)} · ${r.connected_participants.toLocaleString(ArenaI18n.locale)} of ${r.participant_count.toLocaleString(ArenaI18n.locale)} participants connected · reference ${r.anchor.name} = ${fmt(r.anchor.rating)} · updated ${new Date().toLocaleTimeString(ArenaI18n.locale)}`;
      stableHtml('#poolRows',r.items.map(x=>ArenaI18n.h`<tr><td>${x.slot+1}</td><td>${esc(x.name)}</td><td>${fmt(x.rating)}</td><td>${fmt(x.delta)}</td><td>${x.ci?x.ci.map(y=>fmt(y)).join(' – '):'—'}</td><td>${ArenaFormat.los(x.los)}</td><td>${x.samples.toLocaleString(ArenaI18n.locale)}</td><td>${labels[x.status]||esc(ArenaI18n.message(x.status))}</td></tr>`).join(''));
      $('#ratingPage').textContent=r.total?ArenaI18n.m`${offset+1}–${Math.min(offset+50,r.total)} of ${r.total.toLocaleString(ArenaI18n.locale)} engines`:ArenaI18n.t('No matching engines');$('#ratingPrev').disabled=offset===0;$('#ratingNext').disabled=offset+50>=total;$('#ratingModel').textContent=r.model+'. '+r.assumptions;
    }catch(e){if(alive()&&version===generation)root.textContent=e.message;}
    if(alive()&&version===generation)timer=setTimeout(refresh,3000);
  };
  $('#saveAnchor').onclick=safely(async()=>{const rating=Number($('#anchorRating').value),slot=Number($('#anchorEngine').value);if($('#anchorRating').value.trim()===''||!Number.isFinite(rating))throw Error(ArenaI18n.t('Enter a finite reference rating'));await api(`tournaments/${tid}/ratings`,{slot,rating});if(alive()){anchor=null;await refresh();}});
  $('#anchorSearch').oninput=()=>{++peopleGeneration;peopleOffset=0;clearTimeout(searchTimer);searchTimer=setTimeout(()=>{if(alive())people();},180);};
  $('#anchorPrev').onclick=()=>{peopleOffset=Math.max(0,peopleOffset-50);people();};$('#anchorNext').onclick=()=>{if(peopleOffset+50<peopleTotal){peopleOffset+=50;people();}};
  $('#ratingSearch').oninput=()=>{++generation;offset=0;clearTimeout(timer);timer=setTimeout(()=>{if(alive())refresh();},250);};
  $('#ratingPrev').onclick=()=>{offset=Math.max(0,offset-50);refresh();};$('#ratingNext').onclick=()=>{if(offset+50<total){offset+=50;refresh();}};
  const paintSort=()=>$$('[data-pool-sort]').forEach(button=>{const active=button.dataset.poolSort===sort;button.closest('th').setAttribute('aria-sort',active?(direction==='asc'?'ascending':'descending'):'none');button.querySelector('.sort-arrow').textContent=active?(direction==='asc'?' ↑':' ↓'):''});
  $$('[data-pool-sort]').forEach(button=>button.onclick=()=>{const key=button.dataset.poolSort;direction=key===sort?(direction==='asc'?'desc':'asc'):['rating','delta','los','samples'].includes(key)?'desc':'asc';sort=key;offset=0;paintSort();refresh()});paintSort();
  // DOM IDs and wire-format names must not pass through the language catalog.
  for(const format of ['Csv','Json'])$('#rating'+format).onclick=()=>window.open(`/api/tournaments/${tid}/ratings?export=${format.toLowerCase()}&sort=${sort}&direction=${direction}&confidence=${state.confidence||95}&token=${encodeURIComponent(token)}`,'_blank');
  $('#ratingText').onclick=safely(()=>{const query=`export=json&sort=${sort}&direction=${direction}&confidence=${state.confidence||95}`;return textExport(ArenaI18n.t('Anchored pool ratings'),async()=>ArenaText.ratings(await api(`tournaments/${tid}/ratings?${query}`)))});
  await refresh();
}
