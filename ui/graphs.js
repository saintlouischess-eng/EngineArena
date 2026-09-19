'use strict';
const graphTypes={evaluation:['Evaluation','pawns · White perspective','game'],mate:['Mate distance','moves to mate · White perspective','game'],wdl:['Reported WDL','% · White perspective','game'],depth:['Depth / selective depth','plies','game'],nodes:['Searched nodes','nodes','game'],nps:['Search speed','nodes / second','game'],moveTime:['Move time','elapsed seconds','game'],clock:['Remaining clocks','seconds','game'],hash:['Hash occupancy','%','game'],tablebase:['Tablebase hits','hits','game'],cpu:['Host CPU utilization','% · whole computer','hardware'],memory:['Host memory usage','GiB · whole computer','hardware'],score:['Score trend','% · selected engine','tournament'],draw:['Draw-rate trend','% · selected engine','tournament'],elo:['Elo convergence','logistic Elo difference','tournament'],sprt:['SPRT likelihood','log likelihood ratio · engine #1','tournament']};
const graphColors=['#7de1c3','#8eb9ff','#eac16b','#de9ed9','#f29986','#b5c67b'];
const hardwareHistory=[],graphData=new Map();let graphBusy=false;
function recordHardware(status){hardwareHistory.push({x:Date.now()/1000,cpu:status.cpu_percent,memory:status.memory_used_gb});if(hardwareHistory.length>600)hardwareHistory.shift();}
function syncGraphs(){
  const configs=displayPrefs.graphs||[];const keep=new Set(configs.map(c=>c.id));
  for(const id of Object.keys(panels))if(id.startsWith('graph-')&&!keep.has(id)){panels[id].remove();delete panels[id];delete panelNames[id];graphData.delete(id);}
  for(const cfg of configs){
    if(!graphTypes[cfg.kind]||!/^graph-[a-f0-9-]+$/.test(cfg.id))continue;
    panelNames[cfg.id]=graphTypes[cfg.kind][0];
    if(!panels[cfg.id]){
      const panel=document.createElement('div');panel.className='panel graph-panel';panel.innerHTML='<div class="panel-title"><h2></h2><button data-graph-settings class="subtle">Settings</button><button data-graph-svg class="subtle">SVG</button><button data-graph-csv class="subtle">CSV</button><button data-graph-remove class="subtle">Remove</button></div><p class="graph-status caption" role="status">Waiting for samples…</p><div class="graph-plot"></div><p class="graph-hover caption"></p>';
      panels[cfg.id]=panel;installPanel(cfg.id,panel);dock.querySelector('[data-dock=right]').append(panel);
      panel.querySelector('[data-graph-settings]').onclick=safely(()=>graphDialog(cfg.id));
      panel.querySelector('[data-graph-remove]').onclick=()=>{displayPrefs.graphs=displayPrefs.graphs.filter(g=>g.id!==cfg.id);delete displayPrefs.panels[cfg.id];applyDisplay();saveDisplay();};
      panel.querySelector('[data-graph-svg]').onclick=()=>{const svg=panel.querySelector('svg');if(svg)download((graphData.get(cfg.id)?.title||'Graph')+'.svg',svg.outerHTML,'image/svg+xml');};
      panel.querySelector('[data-graph-csv]').onclick=()=>exportGraph(cfg.id);
      panel.querySelector('.graph-plot').onpointermove=e=>{
        const data=graphData.get(cfg.id);if(!data?.series.length)return;const plot=e.currentTarget,rect=plot.getBoundingClientRect();const ratio=Math.max(0,Math.min(1,(e.clientX-rect.left)/rect.width));
        const points=data.series[0].points;if(!points.length)return;const at=points[Math.min(points.length-1,Math.round(ratio*(points.length-1)))];
        panel.querySelector('.graph-hover').textContent=`${data.xLabel}: ${data.timeAxis?new Date(at.x*1000).toLocaleTimeString():at.x} · `+data.series.map(s=>`${s.name} ${fmt(s.points.find(p=>p.x===at.x)?.y,2)}`).join(' · ');
      };
    }
    const panel=panels[cfg.id],configKey=JSON.stringify(cfg);if(panel._configKey!==configKey){panel._configKey=configKey;panel.querySelector('.graph-plot').replaceChildren();panel.querySelector('.graph-plot')._content='';panel.querySelector('.graph-status').textContent='Loading selected metric…';graphData.delete(cfg.id);}
    panel.querySelector('h2').textContent=panelNames[cfg.id];
  }
}
const addGraphButton=document.createElement('button');addGraphButton.id='addGraph';addGraphButton.textContent='＋ Add graph';$('#newTournament').before(addGraphButton);addGraphButton.onclick=safely(()=>graphDialog());

async function graphDialog(id=null){
  const original=(displayPrefs.graphs||[]).find(g=>g.id===id)||{kind:'evaluation',game:0,slot:0,ci:'normal'};let peopleOffset=0,peopleTotal=0,selected={slot:original.slot,name:'Participant #'+(original.slot+1)},peopleVersion=0,searchTimer;
  modal(id?'Graph settings':'Add monitoring graph',`<div class="fields"><div class="field full"><label for="graphKind">Metric</label><select id="graphKind">${Object.entries(graphTypes).map(([key,v])=>`<option value="${key}" ${key===original.kind?'selected':''}>${v[0]}</option>`).join('')}</select></div><div class="field" id="graphGameSource"><label for="graphGame">Game source</label><select id="graphGame"><option value="auto">Focused live game</option><option value="number" ${original.game?'selected':''}>Recorded game number</option></select><small>Follows the focused game, or the first active game.</small></div><div class="field" id="graphNumberField">${field('graphNumber','Game number',original.game||1,'number','min="1" step="1"')}</div></div><div id="graphParticipant"><div class="form-grid"><label>Find participant<input id="graphEngineSearch" placeholder="Search tournament participants"></label><label>Engine perspective<select id="graphEngine"></select></label><label id="graphCiField">Confidence interval<select id="graphCi"><option value="normal">Normal approximation</option><option value="conservative" ${original.ci==='conservative'?'selected':''}>Conservative Hoeffding bound</option></select></label></div><div class="pager"><button id="graphPeoplePrev">←</button><span id="graphPeoplePage"></span><button id="graphPeopleNext">→</button></div></div><p class="caption" id="graphHelp"></p>`, '<button class="primary" id="saveGraph">Save graph</button>');
  const root=$('#graphHelp'),alive=()=>$('#modal').open&&$('#graphHelp')===root;
  const people=async()=>{
    if(!state.tid)return;const version=++peopleVersion;const r=await api(`tournaments/${state.tid}/participants?q=${encodeURIComponent($('#graphEngineSearch').value)}&offset=${peopleOffset}`);if(!alive()||version!==peopleVersion)return;peopleTotal=r.total;
    selected=r.items.find(p=>p.slot===selected.slot)||selected;const choices=[selected,...r.items.filter(p=>p.slot!==selected.slot)];$('#graphEngine').innerHTML=choices.map(p=>`<option value="${p.slot}">#${p.slot+1} ${esc(p.name)}</option>`).join('');$('#graphEngine').value=selected.slot;
    $('#graphEngine').onchange=()=>selected=choices.find(p=>p.slot===Number($('#graphEngine').value));$('#graphPeoplePage').textContent=r.total?`${peopleOffset+1}–${Math.min(peopleOffset+50,r.total)} of ${r.total.toLocaleString()}`:'No participants';$('#graphPeoplePrev').disabled=peopleOffset===0;$('#graphPeopleNext').disabled=peopleOffset+50>=r.total;
  };
  const controls=()=>{const kind=$('#graphKind').value,type=graphTypes[kind][2];$('#graphGameSource').hidden=type!=='game';$('#graphNumberField').hidden=type!=='game'||$('#graphGame').value!=='number';$('#graphParticipant').hidden=type!=='tournament'||kind==='sprt';$('#graphCiField').hidden=kind!=='elo';root.textContent=type==='hardware'?'Whole-computer utilization, retaining the latest 600 UI observations for this session.':type==='game'?'Recorded move telemetry from the latest attempt. Missing engine fields and node-only clocks remain unavailable. Long games are sampled for display; original moves remain saved.':kind==='sprt'?'Uses the original recorded sequential samples and stopping boundaries. Manual replacement marks inference invalidated and preserves the original curve.':'Current official results in completion order. Replacement recomputes the curve. Fixed-sample Elo intervals are not stopping rules.';};
  $('#graphKind').onchange=controls;$('#graphGame').onchange=controls;controls();
  $('#graphEngineSearch').oninput=()=>{++peopleVersion;peopleOffset=0;clearTimeout(searchTimer);searchTimer=setTimeout(()=>{if(alive())safely(people)();},180);};$('#graphPeoplePrev').onclick=safely(async()=>{peopleOffset=Math.max(0,peopleOffset-50);await people();});$('#graphPeopleNext').onclick=safely(async()=>{peopleOffset+=50;await people();});
  $('#saveGraph').onclick=safely(async()=>{
    const kind=$('#graphKind').value,game=$('#graphGame').value==='number'?Number($('#graphNumber').value):0;if(graphTypes[kind][2]==='game'&&$('#graphGame').value==='number'&&(!Number.isInteger(game)||game<1))throw Error('Enter a positive game number');
    const config={id:id||'graph-'+crypto.randomUUID(),kind,game,slot:selected.slot,ci:$('#graphCi').value};displayPrefs.graphs=displayPrefs.graphs||[];const index=displayPrefs.graphs.findIndex(g=>g.id===id);if(index>=0)displayPrefs.graphs[index]=config;else displayPrefs.graphs.push(config);
    displayPrefs.panels[config.id]={...displayPrefs.panels[config.id],visible:true,column:displayPrefs.panels[config.id]?.column||'right'};$('#modal').close();applyDisplay();saveDisplay();await refreshGraphs();
  });
  await people();
}

function chartSeries(cfg,data){
  const [title,unit,category]=graphTypes[cfg.kind];let series=[],note='',xLabel='Ply',timeAxis=false;
  const make=(name,fn,points=data.points)=>({name,points:points.map(p=>({x:p.x,y:fn(p)}))});
  if(category==='hardware'){
    series=[{name:title,points:hardwareHistory.map(p=>({x:p.x,y:p[cfg.kind]}))}];xLabel='Local time';timeAxis=true;note='Whole computer · latest 600 observations · this UI session';
  }else if(category==='tournament'){
    xLabel=cfg.kind==='sprt'?(data.paired?'Completed pairs':'Completed games'):'Official games';note=data.perspective+' · '+data.note+(data.stride>1?` Displayed every ${data.stride} results.`:'');
    if(cfg.kind==='elo'){
      series=[make('Elo',p=>p.elo),make(`${data.confidence||95}% lower`,p=>(cfg.ci==='conservative'?p.ci_conservative:p.ci)?.[0]),make(`${data.confidence||95}% upper`,p=>(cfg.ci==='conservative'?p.ci_conservative:p.ci)?.[1])];note+=` ${cfg.ci==='conservative'?'Conservative Hoeffding':'Normal approximation'}; infinite bounds are not plotted.`;
    }else if(cfg.kind==='sprt'){
      series=[make('LLR',p=>p.llr,data.sequential),make('H0 boundary',p=>p.lower,data.sequential),make('H1 boundary',p=>p.upper,data.sequential)];note='Engine #1 perspective · recorded sequential samples · '+(data.sequential_state?.decision||'No sequential observations')+'. '+(data.sequential_state?.reason||'First stopping observation is frozen; subsequent games do not move this curve.');
    }else series=[make(title,p=>p[cfg.kind==='score'?'score_pct':'draw_pct'])];
  }else{
    note=`Game ${data.number} · attempt ${data.attempt??'—'} · ${data.mode||'not started'} · ${data.state||''}${data.invalidated?' · invalidated game':''} · `+data.note+(data.stride>1?` Displayed in two-move windows every ${data.stride} moves.`:'');
    for(const color of ['white','black']){
      const label=(color==='white'?'White':'Black')+' · '+(data.names?.[color]||'engine');const points=data.points.filter(p=>p.color===color);
      const field={evaluation:'cp',mate:'mate',nodes:'nodes',nps:'nps',moveTime:'elapsed',hash:'hashfull',tablebase:'tbhits'}[cfg.kind];
      if(field)series.push(make(label,p=>typeof p[field]==='number'?p[field]/(cfg.kind==='evaluation'?100:cfg.kind==='hash'?10:1):null,points));
      else if(cfg.kind==='depth'){series.push(make(label+' depth',p=>p.depth,points),make(label+' selective',p=>p.seldepth,points));}
      else if(cfg.kind==='clock')series.push(make(label,p=>p.clocks?.[color]?.remaining));
      else if(cfg.kind==='wdl')for(const [index,result] of ['White win','Draw','White loss'].entries())series.push(make(label+' · '+result,p=>{const sum=p.wdl?.reduce((a,b)=>a+b,0);return sum>0?100*p.wdl[index]/sum:null;},points));
    }
    if(cfg.kind==='clock')note+=' Pure node/depth/move-time controls have no chess clocks.';
  }
  return {title,unit,series,note,xLabel,timeAxis};
}

function seriesLabel(series){return series.name+(series.points.some(p=>Number.isFinite(p.y))?'':series.points.some(p=>typeof p.y==='string'&&p.y.includes('infinity'))?' · unbounded':' · unavailable');}
function graphSvg(data){
  const finite=data.series.flatMap(s=>s.points.filter(p=>Number.isFinite(p.y)));if(!finite.length)return '<p class="caption">No available samples for this metric.</p>';
  const width=800,height=390,left=74,right=24,top=54+16*Math.ceil(data.series.length/2),bottom=68;let xmin=Math.min(...finite.map(p=>p.x)),xmax=Math.max(...finite.map(p=>p.x)),ymin=Math.min(...finite.map(p=>p.y)),ymax=Math.max(...finite.map(p=>p.y));
  if(xmin===xmax)xmax=xmin+1;if(ymin===ymax){const pad=Math.max(1,Math.abs(ymin)*.05);ymin-=pad;ymax+=pad;}else{const pad=(ymax-ymin)*.08;ymin-=pad;ymax+=pad;}
  const x=v=>left+(v-xmin)/(xmax-xmin)*(width-left-right),y=v=>height-bottom-(v-ymin)/(ymax-ymin)*(height-top-bottom),short=v=>Math.abs(v)>=1e6?fmt(v/1e6,1)+'M':Math.abs(v)>=1000?fmt(v/1000,1)+'k':fmt(v,1);
  const text=(a,b,s,anchor='start')=>`<text x="${a}" y="${b}" fill="#b8c7d6" font-size="11" text-anchor="${anchor}">${esc(s)}</text>`;
  let svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(data.title+'; '+data.unit)}"><title>${esc(data.title+' · '+data.note)}</title><rect width="800" height="390" fill="#141d28"/>${text(16,22,data.title+' · '+data.unit)}`;
  for(const [index,series] of data.series.entries()){
    const lx=16+(index%2)*390,ly=40+Math.floor(index/2)*16,label=seriesLabel(series),name=label.length>53?label.slice(0,50)+'…':label;
    svg+=`<rect x="${lx}" y="${ly-5}" width="12" height="3" fill="${graphColors[index%graphColors.length]}"/>`+text(lx+18,ly,name);
  }
  for(let i=0;i<=4;i++){
    const value=ymin+(ymax-ymin)*i/4,yp=y(value);svg+=`<path d="M${left} ${yp}H${width-right}" stroke="#2e3c4b"/>`+text(left-8,yp+4,short(value),'end');
    const xv=xmin+(xmax-xmin)*i/4;svg+=text(x(xv),height-bottom+20,data.timeAxis?new Date(xv*1000).toLocaleTimeString():short(xv),'middle');
  }
  for(const [index,s] of data.series.entries()){
    let path='',segment=false;for(const p of s.points){if(!Number.isFinite(p.y)){segment=false;continue;}path+=(segment?'L':'M')+x(p.x).toFixed(2)+' '+y(p.y).toFixed(2);segment=true;}
    const color=graphColors[index%graphColors.length];svg+=`<path d="${path}" fill="none" stroke="${color}" stroke-width="2"${s.name.includes('% ')||s.name.includes('boundary')?' stroke-dasharray="5 4"':''}/>`;
    if(s.points.filter(p=>Number.isFinite(p.y)).length===1){const p=s.points.find(p=>Number.isFinite(p.y));svg+=`<circle cx="${x(p.x)}" cy="${y(p.y)}" r="3" fill="${color}"/>`;}
  }
  svg+=text(width/2,height-10,data.xLabel,'middle')+'</svg>';return svg;
}

async function refreshGraphs(){
  if(graphBusy||state.view!=='overview')return;graphBusy=true;const tid=state.tid,requests=new Map();
  const fetchOnce=path=>{if(!requests.has(path))requests.set(path,api(path));return requests.get(path);};
  try{
    await Promise.all((displayPrefs.graphs||[]).map(async cfg=>{
      const panel=panels[cfg.id];if(!panel||panel.hidden||!graphTypes[cfg.kind])return;const category=graphTypes[cfg.kind][2];
      try{
        let data={points:[]};
        if(category!=='hardware'){
          if(!tid){panel.querySelector('.graph-status').textContent='Select a tournament.';return;}
          if(panel._tournament!==tid){panel._tournament=tid;panel.querySelector('.graph-plot').replaceChildren();panel.querySelector('.graph-plot')._content='';graphData.delete(cfg.id);}
          let path=`tournaments/${tid}/series?slot=${cfg.slot}`;
          if(category==='game'){
            const focused=state.live.find(g=>g.tid===tid&&g.game===focusId)||state.live.find(g=>g.tid===tid);const number=cfg.game|| (focused?focused.number+1:0);
            if(!number){panel.querySelector('.graph-status').textContent='No active game. Choose a recorded game number to view saved telemetry.';return;}
            path=`tournaments/${tid}/series?game=${number}`;
          }
          data=await fetchOnce(path);if(state.tid!==tid||panels[cfg.id]!==panel||(displayPrefs.graphs||[]).find(g=>g.id===cfg.id)!==cfg)return;
        }
        const chart=chartSeries(cfg,data);graphData.set(cfg.id,chart);panel.querySelector('.graph-status').textContent=chart.note;
        const content=graphSvg(chart)+`<div class="graph-legend">${chart.series.map((s,i)=>`<span><i style="background:${graphColors[i%graphColors.length]}"></i>${esc(seriesLabel(s))}</span>`).join('')}</div>`;
        const plot=panel.querySelector('.graph-plot');if(plot._content!==content){plot.innerHTML=content;plot._content=content;}
      }catch(e){if(panels[cfg.id]===panel)panel.querySelector('.graph-status').textContent=e.message;}
    }));
  }finally{graphBusy=false;}
}
function exportGraph(id){
  const data=graphData.get(id);if(!data)return;const quote=x=>'"'+String(x??'').replaceAll('"','""')+'"';const xs=[...new Set(data.series.flatMap(s=>s.points.map(p=>p.x)))].sort((a,b)=>a-b);const maps=data.series.map(s=>new Map(s.points.map(p=>[p.x,p.y])));
  const rows=[[data.timeAxis?'Unix timestamp (seconds)':data.xLabel,...data.series.map(s=>s.name+' ['+data.unit+']'),'Context'],...xs.map(x=>[x,...maps.map(m=>m.get(x)),data.note])];download(data.title+'.csv',rows.map(r=>r.map(quote).join(',')).join('\r\n'),'text/csv');
}
syncGraphs();applyDisplay();setInterval(()=>refreshGraphs().catch(e=>notify(e.message,true)),1500);
