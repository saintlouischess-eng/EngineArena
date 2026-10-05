'use strict';
const graphTypes={evaluation:[ArenaI18n.t('Evaluation'),ArenaI18n.t('pawns · White perspective'),'game'],mate:[ArenaI18n.t('Mate distance'),ArenaI18n.t('moves to mate · White perspective'),'game'],wdl:[ArenaI18n.t('Reported WDL'),ArenaI18n.t('% · White perspective'),'game'],depth:[ArenaI18n.t('Depth / selective depth'),'plies','game'],nodes:[ArenaI18n.t('Searched nodes'),'nodes','game'],nps:[ArenaI18n.t('Search speed'),ArenaI18n.t('nodes / second'),'game'],moveTime:[ArenaI18n.t('Move time'),ArenaI18n.t('elapsed seconds'),'game'],clock:[ArenaI18n.t('Remaining clocks'),'seconds','game'],hash:[ArenaI18n.t('Hash occupancy'),'%','game'],tablebase:[ArenaI18n.t('Tablebase hits'),'hits','game'],cpu:[ArenaI18n.t('Host CPU utilization'),ArenaI18n.t('% · whole computer'),'hardware'],memory:[ArenaI18n.t('Host memory usage'),ArenaI18n.t('GiB · whole computer'),'hardware'],score:[ArenaI18n.t('Score trend'),ArenaI18n.t('% · selected engine'),'tournament'],draw:[ArenaI18n.t('Draw-rate trend'),ArenaI18n.t('% · selected engine'),'tournament'],elo:[ArenaI18n.t('Elo convergence'),ArenaI18n.t('logistic Elo difference'),'tournament'],sprt:[ArenaI18n.t('SPRT likelihood'),ArenaI18n.t('Log likelihood ratio'),'tournament']};
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
      const panel=document.createElement('div');panel.className='panel graph-panel';panel.innerHTML=ArenaI18n.h('<div class="panel-title"><h2></h2><button data-graph-settings class="subtle">Settings</button><button data-graph-svg class="subtle">SVG</button><button data-graph-csv class="subtle">CSV</button><button data-graph-text class="subtle" data-help="Export the displayed graph samples as readable text, including units and sampling context.">Text…</button><button data-graph-remove class="subtle">Remove</button></div><p class="graph-status caption" role="status">Waiting for samples…</p><div class="graph-plot"></div><p class="graph-hover caption"></p>');
      panels[cfg.id]=panel;installPanel(cfg.id,panel);dock.querySelector('[data-dock=right]').append(panel);
      panel.querySelector('[data-graph-settings]').onclick=safely(()=>graphDialog(cfg.id));
      panel.querySelector('[data-graph-remove]').onclick=()=>{displayPrefs.graphs=displayPrefs.graphs.filter(g=>g.id!==cfg.id);delete displayPrefs.panels[cfg.id];applyDisplay();saveDisplay();};
      panel.querySelector('[data-graph-svg]').onclick=()=>{const data=graphData.get(cfg.id);if(data&&panel.querySelector('svg'))download(data.title+'.svg',graphSvg(data),'image/svg+xml');};
      panel.querySelector('[data-graph-csv]').onclick=()=>exportGraph(cfg.id);
      panel.querySelector('[data-graph-text]').onclick=()=>exportGraphText(cfg.id);
      panel.querySelector('.graph-plot').onpointermove=e=>{
        const data=graphData.get(cfg.id);if(!data?.series.length)return;const plot=e.currentTarget,rect=plot.getBoundingClientRect();const ratio=Math.max(0,Math.min(1,(e.clientX-rect.left)/rect.width));
        const points=data.series[0].points;if(!points.length)return;const at=points[Math.min(points.length-1,Math.round(ratio*(points.length-1)))];
        panel.querySelector('.graph-hover').textContent=`${data.xLabel}: ${data.timeAxis?new Date(at.x*1000).toLocaleTimeString(ArenaI18n.locale):at.x} · `+data.series.map(s=>`${s.name} ${fmt(s.points.find(p=>p.x===at.x)?.y,2)}`).join(' · ');
      };
    }
    const panel=panels[cfg.id],configKey=JSON.stringify(cfg);if(panel._configKey!==configKey){panel._configKey=configKey;panel.querySelector('.graph-plot').replaceChildren();panel.querySelector('.graph-plot')._content='';panel.querySelector('.graph-status').textContent=ArenaI18n.t('Loading selected metric…');graphData.delete(cfg.id);}
    panel.querySelector('h2').textContent=panelNames[cfg.id];
  }
}
const addGraphButton=document.createElement('button');addGraphButton.id='addGraph';addGraphButton.textContent=ArenaI18n.t('＋ Add graph');$('#newTournament').before(addGraphButton);addGraphButton.onclick=safely(()=>graphDialog());

async function graphDialog(id=null){
  const original=(displayPrefs.graphs||[]).find(g=>g.id===id)||{kind:'evaluation',game:0,slot:0,ci:'normal'};let peopleOffset=0,peopleTotal=0,selected={slot:original.slot,name:ArenaI18n.t('Participant #')+(original.slot+1)},peopleVersion=0,searchTimer;
  modal(id?ArenaI18n.t('Graph settings'):ArenaI18n.t('Add monitoring graph'),ArenaI18n.h`<div class="fields"><div class="field full"><label for="graphKind">Metric</label><select id="graphKind">${Object.entries(graphTypes).map(([key,v])=>ArenaI18n.h`<option value="${key}" ${key===original.kind?'selected':''}>${v[0]}</option>`).join('')}</select></div><div class="field" id="graphGameSource"><label for="graphGame">Game source</label><select id="graphGame"><option value="auto">Focused live game</option><option value="number" ${original.game?'selected':''}>Recorded game number</option></select><small>Follows the focused game, or the first active game.</small></div><div class="field" id="graphNumberField">${field('graphNumber',ArenaI18n.t('Game number'),original.game||1,'number','min="1" step="1"')}</div></div><div id="graphParticipant"><div class="form-grid"><label>Find participant<input id="graphEngineSearch" placeholder="Search tournament participants"></label><label>Engine perspective<select id="graphEngine"></select></label><label id="graphCiField">Confidence interval<select id="graphCi"><option value="normal">Normal approximation</option><option value="conservative" ${original.ci==='conservative'?'selected':''}>Conservative Hoeffding bound</option></select></label></div><div class="pager"><button id="graphPeoplePrev">←</button><span id="graphPeoplePage"></span><button id="graphPeopleNext">→</button></div></div><p class="caption" id="graphHelp"></p>`, ArenaI18n.h('<button class="primary" id="saveGraph">Save graph</button>'));
  const root=$('#graphHelp'),alive=()=>$('#modal').open&&$('#graphHelp')===root;
  const people=async()=>{
    if(!state.tid)return;const version=++peopleVersion;const r=await api(`tournaments/${state.tid}/participants?q=${encodeURIComponent($('#graphEngineSearch').value)}&offset=${peopleOffset}`);if(!alive()||version!==peopleVersion)return;peopleTotal=r.total;
    selected=r.items.find(p=>p.slot===selected.slot)||selected;const choices=[selected,...r.items.filter(p=>p.slot!==selected.slot)];$('#graphEngine').innerHTML=choices.map(p=>ArenaI18n.h`<option value="${p.slot}">#${p.slot+1} ${esc(p.name)}</option>`).join('');$('#graphEngine').value=selected.slot;
    $('#graphEngine').onchange=()=>selected=choices.find(p=>p.slot===Number($('#graphEngine').value));$('#graphPeoplePage').textContent=r.total?ArenaI18n.m`${peopleOffset+1}–${Math.min(peopleOffset+50,r.total)} of ${r.total.toLocaleString(ArenaI18n.locale)}`:ArenaI18n.t('No participants');$('#graphPeoplePrev').disabled=peopleOffset===0;$('#graphPeopleNext').disabled=peopleOffset+50>=r.total;
  };
  const controls=()=>{const kind=$('#graphKind').value,type=graphTypes[kind][2];$('#graphGameSource').hidden=type!=='game';$('#graphNumberField').hidden=type!=='game'||$('#graphGame').value!=='number';$('#graphParticipant').hidden=type!=='tournament'||kind==='sprt';$('#graphCiField').hidden=kind!=='elo';root.textContent=type==='hardware'?ArenaI18n.t('Whole-computer utilization, retaining the latest 600 UI observations for this session.'):type==='game'?ArenaI18n.t('Recorded move telemetry from the latest attempt. Missing engine fields and node-only clocks remain unavailable. Long games are sampled for display; original moves remain saved.'):kind==='sprt'?ArenaI18n.t('Uses the original recorded sequential samples and stopping boundaries. Manual replacement marks inference invalidated and preserves the original curve.'):ArenaI18n.t('Current official results in completion order. Replacement recomputes the curve. Fixed-sample Elo intervals are not stopping rules.');};
  $('#graphKind').onchange=controls;$('#graphGame').onchange=controls;controls();
  $('#graphEngineSearch').oninput=()=>{++peopleVersion;peopleOffset=0;clearTimeout(searchTimer);searchTimer=setTimeout(()=>{if(alive())safely(people)();},180);};$('#graphPeoplePrev').onclick=safely(async()=>{peopleOffset=Math.max(0,peopleOffset-50);await people();});$('#graphPeopleNext').onclick=safely(async()=>{peopleOffset+=50;await people();});
  $('#saveGraph').onclick=safely(async()=>{
    const kind=$('#graphKind').value,game=$('#graphGame').value==='number'?Number($('#graphNumber').value):0;if(graphTypes[kind][2]==='game'&&$('#graphGame').value==='number'&&(!Number.isInteger(game)||game<1))throw Error(ArenaI18n.t('Enter a positive game number'));
    const config={id:id||'graph-'+crypto.randomUUID(),kind,game,slot:selected.slot,ci:$('#graphCi').value};displayPrefs.graphs=displayPrefs.graphs||[];const index=displayPrefs.graphs.findIndex(g=>g.id===id);if(index>=0)displayPrefs.graphs[index]=config;else displayPrefs.graphs.push(config);
    displayPrefs.panels[config.id]={...displayPrefs.panels[config.id],visible:true,column:displayPrefs.panels[config.id]?.column||'right'};$('#modal').close();applyDisplay();saveDisplay();await refreshGraphs();
  });
  await people();
}

function chartSeries(cfg,data){
  const [title,unit,category]=graphTypes[cfg.kind];let series=[],note='',xLabel=ArenaI18n.t('Ply'),timeAxis=false;
  const make=(name,fn,points=data.points)=>({name,points:points.map(p=>({x:p.x,y:fn(p)}))});
  if(category==='hardware'){
    series=[{name:title,points:hardwareHistory.map(p=>({x:p.x,y:p[cfg.kind]}))}];xLabel=ArenaI18n.t('Local time');timeAxis=true;note=ArenaI18n.t('Whole computer · latest 600 observations · this UI session');
  }else if(category==='tournament'){
    xLabel=cfg.kind==='sprt'?(data.paired?ArenaI18n.t('Completed pairs'):ArenaI18n.t('Completed games')):ArenaI18n.t('Official games');note=data.perspective+' · '+data.note+(data.stride>1?ArenaI18n.m` Displayed every ${data.stride} results.`:'');
    if(cfg.kind==='elo'){
      series=[make(ArenaI18n.t('Elo'),p=>p.elo),make(ArenaI18n.m`${data.confidence||95}% lower`,p=>(cfg.ci==='conservative'?p.ci_conservative:p.ci)?.[0]),make(ArenaI18n.m`${data.confidence||95}% upper`,p=>(cfg.ci==='conservative'?p.ci_conservative:p.ci)?.[1])];note+=ArenaI18n.m` ${cfg.ci==='conservative'?ArenaI18n.t('Conservative Hoeffding'):ArenaI18n.t('Normal approximation')}; infinite bounds are not plotted.`;
    }else if(cfg.kind==='sprt'){
      series=[make('LLR',p=>p.llr,data.sequential),make(ArenaI18n.t('H0 boundary'),p=>p.lower,data.sequential),make(ArenaI18n.t('H1 boundary'),p=>p.upper,data.sequential)];note=(data.sequential_candidate||ArenaI18n.t('Tested engine'))+' · '+(data.sequential_state?.decision||ArenaI18n.t('No sequential observations'))+'. '+(data.sequential_state?.reason||ArenaI18n.t('First stopping observation is frozen; subsequent games do not move this curve.'));
    }else series=[make(title,p=>p[cfg.kind==='score'?'score_pct':'draw_pct'])];
  }else{
    note=ArenaI18n.m`Game ${data.number} · attempt ${data.attempt??'—'} · ${data.mode||ArenaI18n.t('not started')} · ${data.state||''}${data.invalidated?ArenaI18n.t(' · invalidated game'):''} · `+data.note+(data.stride>1?ArenaI18n.m` Displayed in two-move windows every ${data.stride} moves.`:'');
    for(const color of ['white','black']){
      const label=(color==='white'?ArenaI18n.t('White'):ArenaI18n.t('Black'))+' · '+(data.names?.[color]||'engine');const points=data.points.filter(p=>p.color===color);
      const field={evaluation:'cp',mate:'mate',nodes:'nodes',nps:'nps',moveTime:'elapsed',hash:'hashfull',tablebase:'tbhits'}[cfg.kind];
      if(field)series.push(make(label,p=>typeof p[field]==='number'?p[field]/(cfg.kind==='evaluation'?100:cfg.kind==='hash'?10:1):null,points));
      else if(cfg.kind==='depth'){series.push(make(label+ArenaI18n.t(' depth'),p=>p.depth,points),make(label+ArenaI18n.t(' selective'),p=>p.seldepth,points));}
      else if(cfg.kind==='clock')series.push(make(label,p=>p.clocks?.[color]?.remaining));
      else if(cfg.kind==='wdl')for(const [index,result] of [ArenaI18n.t('White win'),ArenaI18n.t('Draw'),ArenaI18n.t('White loss')].entries())series.push(make(label+' · '+result,p=>{const sum=p.wdl?.reduce((a,b)=>a+b,0);return sum>0?100*p.wdl[index]/sum:null;},points));
    }
    if(cfg.kind==='clock')note+=ArenaI18n.t(' Pure node/depth/move-time controls have no chess clocks.');
  }
  return {title,unit,series,note,xLabel,timeAxis};
}

function seriesLabel(series){return series.name+(series.points.some(p=>Number.isFinite(p.y))?'':series.points.some(p=>typeof p.y==='string'&&p.y.includes('infinity'))?ArenaI18n.t(' · unbounded'):ArenaI18n.t(' · unavailable'));}
function graphSvg(data,frame=null){
  const finite=data.series.flatMap(s=>s.points.filter(p=>Number.isFinite(p.y)));if(!finite.length)return ArenaI18n.h('<p class="caption">No available samples for this metric.</p>');
  const width=frame?.width||800,height=frame?.height||390,fontSize=frame?.fontSize||11,left=Math.ceil(fontSize*6.7),right=24,top=frame?fontSize*3:54+16*Math.ceil(data.series.length/2),bottom=fontSize*4+24;const ink=frame?.light?'#526379':'#b8c7d6',surface=frame?.light?'#f7f9fc':'#141920',grid=frame?.light?'#d4dce5':'#343e4b',colors=frame?.light?['#17684f','#305fad','#8a600e','#895285','#a64435','#536c2a']:graphColors;let xmin=Math.min(...finite.map(p=>p.x)),xmax=Math.max(...finite.map(p=>p.x)),ymin=Math.min(...finite.map(p=>p.y)),ymax=Math.max(...finite.map(p=>p.y));
  if(xmin===xmax)xmax=xmin+1;if(ymin===ymax){const pad=Math.max(1,Math.abs(ymin)*.05);ymin-=pad;ymax+=pad;}else{const pad=(ymax-ymin)*.08;ymin-=pad;ymax+=pad;}
  const x=v=>left+(v-xmin)/(xmax-xmin)*(width-left-right),y=v=>height-bottom-(v-ymin)/(ymax-ymin)*(height-top-bottom),short=v=>Math.abs(v)>=1e6?fmt(v/1e6,1)+'M':Math.abs(v)>=1000?fmt(v/1000,1)+'k':fmt(v,1);
  const text=(a,b,s,anchor='start')=>ArenaI18n.h`<text x="${a}" y="${b}" fill="${ink}" font-size="${fontSize}" font-family="Segoe UI,Arial,sans-serif" text-anchor="${anchor}">${esc(s)}</text>`;
  let svg=ArenaI18n.h`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(data.title+'; '+data.unit)}"><title>${esc(data.title+' · '+data.note)}</title><rect width="${width}" height="${height}" fill="${surface}"/>${text(16,fontSize*2,frame?data.unit:data.title+' · '+data.unit)}`;
  if(!frame)for(const [index,series] of data.series.entries()){
    const lx=16+(index%2)*390,ly=40+Math.floor(index/2)*16,label=seriesLabel(series),name=label.length>53?label.slice(0,50)+'…':label;
    svg+=ArenaI18n.h`<rect x="${lx}" y="${ly-5}" width="12" height="3" fill="${graphColors[index%graphColors.length]}"/>`+text(lx+18,ly,name);
  }
  for(let i=0;i<=4;i++){
    const value=ymin+(ymax-ymin)*i/4,yp=y(value);svg+=ArenaI18n.h`<path d="M${left} ${yp}H${width-right}" stroke="${grid}"/>`+text(left-8,yp+4,short(value),'end');
    const xv=xmin+(xmax-xmin)*i/4;if(width>=600||i%2===0)svg+=text(x(xv),height-bottom+20,data.timeAxis?new Date(xv*1000).toLocaleTimeString(ArenaI18n.locale):short(xv),'middle');
  }
  for(const [index,s] of data.series.entries()){
    let path='',segment=false;for(const p of s.points){if(!Number.isFinite(p.y)){segment=false;continue;}path+=(segment?'L':'M')+x(p.x).toFixed(2)+' '+y(p.y).toFixed(2);segment=true;}
    const color=colors[index%colors.length];svg+=ArenaI18n.h`<path d="${path}" fill="none" stroke="${color}" stroke-width="2"${s.name.includes('% ')||s.name.includes('boundary')?' stroke-dasharray="5 4"':''}/>`;
    if(s.points.filter(p=>Number.isFinite(p.y)).length===1){const p=s.points.find(p=>Number.isFinite(p.y));svg+=ArenaI18n.h`<circle cx="${x(p.x)}" cy="${y(p.y)}" r="3" fill="${color}"/>`;}
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
          if(!tid){panel.querySelector('.graph-status').textContent=ArenaI18n.t('Select a tournament.');return;}
          if(panel._tournament!==tid){panel._tournament=tid;panel.querySelector('.graph-plot').replaceChildren();panel.querySelector('.graph-plot')._content='';graphData.delete(cfg.id);}
          let path=`tournaments/${tid}/series?slot=${cfg.slot}`;
          if(category==='game'){
            const focused=state.live.find(g=>g.tid===tid&&g.game===focusId)||state.live.find(g=>g.tid===tid);const number=cfg.game|| (focused?focused.number+1:0);
            if(!number){panel.querySelector('.graph-status').textContent=ArenaI18n.t('No active game. Choose a recorded game number to view saved telemetry.');return;}
            path=`tournaments/${tid}/series?game=${number}`;
          }
          data=await fetchOnce(path);if(state.tid!==tid||panels[cfg.id]!==panel||(displayPrefs.graphs||[]).find(g=>g.id===cfg.id)!==cfg)return;
        }
        const chart=chartSeries(cfg,data);graphData.set(cfg.id,chart);panel.querySelector('.graph-status').textContent=chart.note;
        const plot=panel.querySelector('.graph-plot'),fontSize=Math.max(11,Number(displayPrefs.fontSize)*.8),light=document.body.classList.contains('light');
        // Use the actual plot dimensions so a narrow dock never scales 11px labels
        // down to 5px. The existing refresh timer also picks up panel resizing.
        const legendHeight=plot.querySelector('.graph-legend')?.offsetHeight||Math.ceil(chart.series.length/2)*fontSize*1.8;
        const frame={width:Math.max(300,Math.floor(plot.clientWidth-24)),height:Math.max(200,Math.floor(plot.clientHeight-legendHeight-24)),fontSize,light};
        const content=graphSvg(chart,frame)+ArenaI18n.h`<div class="graph-legend">${chart.series.map((s,i)=>ArenaI18n.h`<span><i style="background:${(light?['#17684f','#305fad','#8a600e','#895285','#a64435','#536c2a']:graphColors)[i%graphColors.length]}"></i>${esc(seriesLabel(s))}</span>`).join('')}</div>`;
        if(plot._content!==content){plot.innerHTML=content;plot._content=content;}
      }catch(e){if(panels[cfg.id]===panel)panel.querySelector('.graph-status').textContent=e.message;}
    }));
  }finally{graphBusy=false;}
}
function exportGraph(id){
  const data=graphData.get(id);if(!data)return;const quote=x=>'"'+String(x??'').replaceAll('"','""')+'"';const xs=[...new Set(data.series.flatMap(s=>s.points.map(p=>p.x)))].sort((a,b)=>a-b);const maps=data.series.map(s=>new Map(s.points.map(p=>[p.x,p.y])));
  const rows=[[data.timeAxis?ArenaI18n.t('Unix timestamp (seconds)'):data.xLabel,...data.series.map(s=>s.name+' ['+data.unit+']'),ArenaI18n.t('Context')],...xs.map(x=>[x,...maps.map(m=>m.get(x)),data.note])];download(data.title+'.csv',rows.map(r=>r.map(quote).join(',')).join('\r\n'),'text/csv');
}
syncGraphs();applyDisplay();setInterval(()=>refreshGraphs().catch(e=>notify(e.message,true)),1500);
