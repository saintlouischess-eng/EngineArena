'use strict';
// Human-readable exports use the same reported values, never a second rating calculation.
(function(root){
 if(!root.ArenaI18n&&typeof require==='function')require('./i18n.js');
 const los=value=>value===null||value===undefined||!Number.isFinite(value)?'N/A':value<=.05?'<0.1%':value>=99.95?'>99.9%':number(value,2)+'%';
 const clean=value=>String(value??'N/A').normalize('NFC').replace(/[\x00-\x08\x0b-\x1f\x7f]/g,'').replace(/\s+/g,' ').trim();
 const width=s=>[...s].reduce((n,c)=>{const p=c.codePointAt(0);return n+(/\p{Mark}/u.test(c)?0:(p>=0x1100&&(p<=0x115f||p>=0x2e80&&p<=0xa4cf||p>=0xac00&&p<=0xd7af||p>=0xf900&&p<=0xfaff||p>=0xfe10&&p<=0xfe6f||p>=0xff01&&p<=0xff60||p>=0x1f300))?2:1)},0);
 function wrap(value,limit=100){
  const words=clean(value).split(' '),lines=[];let line='';
  for(let word of words){
   if(line&&width(line+' '+word)>limit){lines.push(line);line=''}
   while(width(word)>limit){let part='';for(const c of word){if(width(part+c)>limit)break;part+=c}lines.push(part);word=word.slice(part.length)}
   if(word)line+=(line?' ':'')+word;
  }
  if(line||!lines.length)lines.push(line);return lines;
 }
 function table(headers,rows,{right=[],limits=[]}={}){
  if(!rows.length)return ArenaI18n.t('(No records.)');
  const sizes=headers.map((h,i)=>Math.max(3,Math.min(limits[i]||32,rows.reduce((size,r)=>Math.max(size,width(clean(r[i]))),width(clean(h))))));
  const format=row=>{const cells=headers.map((_,i)=>wrap(row[i],sizes[i]));return Array.from({length:Math.max(...cells.map(c=>c.length))},(_,line)=>cells.map((c,i)=>{const v=c[line]||'',pad=' '.repeat(Math.max(0,sizes[i]-width(v)));return right.includes(i)?pad+v:v+pad}).join('  ').trimEnd()).join('\n')};
  return [format(headers),sizes.map(n=>'-'.repeat(n)).join('  '),...rows.map(format)].join('\n');
 }
 function number(v,digits=1){if(v===null||v===undefined||Number.isNaN(v))return 'N/A';if(v==='+infinity'||v===Infinity)return '+inf';if(v==='-infinity'||v===-Infinity)return '-inf';return typeof v==='number'?v.toLocaleString(ArenaI18n.locale==='en'?'en-US':ArenaI18n.locale,{minimumFractionDigits:digits,maximumFractionDigits:digits}):clean(v)}
 const pct=v=>v===null||v===undefined?'N/A':number(v,2)+'%';
 const interval=v=>Array.isArray(v)?v.map(x=>number(x)).join(ArenaI18n.t(' to ')):'N/A';
 const section=(title,body)=>clean(title)+'\n'+'-'.repeat(Math.min(100,width(clean(title))))+'\n'+body;
 const fields=rows=>table([ArenaI18n.t('Setting'),ArenaI18n.t('Value')],rows,{limits:[29,83]});
 function report(title,blocks,stamp=new Date().toISOString()){
  const heading=clean(title);return heading+'\n'+'='.repeat(Math.min(112,width(heading)))+ArenaI18n.t('\nEngine Arena | Snapshot: ')+stamp+'\n\n'+blocks.filter(Boolean).join('\n\n')+'\n';
 }
 function timeControl(t){
  if(!t)return ArenaI18n.t('Tournament default');
  if(t.kind==='nodes')return number(t.nodes,0)+ArenaI18n.t(' nodes per move; no chess clock');
  if(t.kind==='depth')return ArenaI18n.t('Depth ')+t.depth+ArenaI18n.t('; no chess clock');
  if(t.kind==='movetime')return number(t.seconds,3)+ArenaI18n.t(' seconds per move');
  if(t.kind==='staged')return (t.stages||[]).map(s=>(s.moves?s.moves+ArenaI18n.t(' moves in '):ArenaI18n.t('Rest of game in '))+s.seconds+ArenaI18n.t(' seconds')+(s.increment?' + '+s.increment+ArenaI18n.t(' seconds/move'):'')).join(ArenaI18n.t('; then '))+(t.repeat?ArenaI18n.t('; repeat final stage'):'');
  return t.seconds+ArenaI18n.t(' seconds')+(t.kind==='fischer'?' + '+t.increment+ArenaI18n.t(' seconds/move'):t.kind==='delay'||t.kind==='bronstein'?'; '+t.kind+' '+t.delay+ArenaI18n.t(' seconds'):'');
 }
 const modelNote=ArenaI18n.t('N/A = unavailable, not zero. +inf / -inf = an unbounded estimate or interval. Elo is relative to sampled opposition. LOS is an approximate likelihood of superiority. Fixed-sample intervals are not sequential stopping rules. Byes contribute points only; self-play does not infer between-engine strength.');
 function statsTable(rows,confidence=95,method='normal',nameKey='name'){
  const hasTF=rows.some(r=>r.tf!==undefined),hasBye=rows.some(r=>r.bye_points>0);
  return table(['#',ArenaI18n.t('Engine'),ArenaI18n.t('Games'),'W','D','L',ArenaI18n.t('Points'),ArenaI18n.t('Score %'),ArenaI18n.t('Draw %'),ArenaI18n.t('Elo'),ArenaI18n.t('CI ')+confidence+'%',ArenaI18n.t('LOS %'),ArenaI18n.t('Pairs'),...(hasTF?['TF',ArenaI18n.t('Official TF')]:[]),...(hasBye?[ArenaI18n.t('Bye points')]:[])],rows.map((r,i)=>[r.rank??i+1,r[nameKey],number(r.games,0),number(r.wins,0),number(r.draws,0),number(r.losses,0),number(r.points??r.score),pct(r.score_pct),pct(r.draw_pct),number(r.elo),interval(r[method==='conservative'?'ci_conservative':'ci']),los(r.los),r.pairs===null?ArenaI18n.t('Unpaired'):number(r.pairs,0),...(hasTF?[number(r.tf,0),number(r.tf_official,0)]:[]),...(hasBye?[number(r.bye_points??0)]:[])]),{right:[0,2,3,4,5,6,7,8,9,11,12,13,14,15],limits:[5,32,8,7,7,7,10,9,9,10,23,9,9,...(hasTF?[8,11]:[]),...(hasBye?[24]:[])]});
 }
 function standings(s,method='normal'){
  return report(s.name+ArenaI18n.t(' — Standings'),[
   fields([[ArenaI18n.t('Tournament state'),s.state],[ArenaI18n.t('Official games / scheduled'),number(s.official_games,0)+' / '+number(s.total,0)],[ArenaI18n.t('Participants'),number(s.participants,0)],[ArenaI18n.t('Opening pairs'),s.settings.paired?number(s.complete_pairs,0)+ArenaI18n.t(' complete'):ArenaI18n.t('Unpaired')],[ArenaI18n.t('Time control'),timeControl(s.settings.time_control)],[ArenaI18n.t('Confidence interval'),s.confidence+'% · '+(method==='conservative'?ArenaI18n.t('Conservative Hoeffding bound'):ArenaI18n.t('Normal approximation'))],[ArenaI18n.t('Order'),s.standings_sort.key+' / '+s.standings_sort.direction]]),
   s.knockout?section(ArenaI18n.t('Knockout (KO) results'),knockout(s.knockout,s.standings)):'',
   statsTable(s.standings,s.confidence,method),wrap(ArenaI18n.t('TF counts time forfeits in all competition attempts, including retries and replaced results. Diagnostics are excluded. Official TF counts only current official losses.')).join('\n'),wrap(s.settings.paired?ArenaI18n.t('W-D-L and points include all official games; paired Elo, CI and LOS use completed opening pairs only.'):ArenaI18n.t('Unpaired estimates use individual official games.')).join('\n'),wrap(modelNote).join('\n'),s.dependency||s.note?section(ArenaI18n.t('Tournament note'),wrap(s.dependency||s.note).join('\n')):'',
  ]);
 }
 function knockout(k,people){
  const blocks=[k.champion?ArenaI18n.t('Champion: ')+k.champion:ArenaI18n.m`Round ${k.round} | ${k.remaining} engines still in the KO`,wrap(k.note).join('\n'),
   table([ArenaI18n.t('Engine'),ArenaI18n.t('KO status'),ArenaI18n.t('Match W'),ArenaI18n.t('Match L'),ArenaI18n.t('Byes')],people.map(p=>[p.name,p.ko_finish||p.ko_status,p.match_wins,p.match_losses,p.byes]),{right:[2,3,4]})];
  for(const r of k.rounds){const rows=[];for(const m of r.matches)for(const stage of m.stages)rows.push([m.a_name+' / '+m.b_name,stage.stage?ArenaI18n.t('Tiebreak ')+stage.stage:ArenaI18n.t('Regular'),number(stage.a_score,1)+' - '+number(stage.b_score,1),stage.completed+'/'+stage.games,stage.time_control?timeControl(stage.time_control):ArenaI18n.t('Normal engine controls'),stage===m.stages.at(-1)?ArenaI18n.message(m.status)+(m.decision_basis?' / '+ArenaI18n.message(m.decision_basis):''):ArenaI18n.t('Tied; continued')]);blocks.push(section(ArenaI18n.t('KO round ')+r.round,table([ArenaI18n.t('Engine A / Engine B'),ArenaI18n.t('Stage'),ArenaI18n.t('A - B'),ArenaI18n.t('Games'),ArenaI18n.t('Control'),ArenaI18n.t('Outcome')],rows,{limits:[34,15,14,12,35,38]})));if(r.byes.length)blocks.push(ArenaI18n.t('Byes: ')+r.byes.map(p=>clean(p.name)).join(', ')+ArenaI18n.t(' (no game or match win).'));if(r.match_count>r.matches.length)blocks.push(ArenaI18n.m`Showing ${r.matches.length} of ${r.match_count} matches; use the full KO report for all matches.`)}
  return blocks.join('\n\n');
 }
 function openings(r){
  const values=s=>[number(s.games,0),number(s.wins,0),number(s.draws,0),number(s.losses,0),pct(s.score_pct),pct(s.draw_pct)];
  return report(r.name+ArenaI18n.t(' — Opening and color results'),[
   fields([[ArenaI18n.t('Perspective'),r.perspective],[ArenaI18n.t('Committed revision'),r.revision],[ArenaI18n.t('Recorded openings'),r.total_openings]]),
   section(ArenaI18n.t('Overall'),table([ArenaI18n.t('Games'),'W','D','L',ArenaI18n.t('Score %'),ArenaI18n.t('Draw %')],[values(r.summary)],{right:[0,1,2,3,4,5]})),
   section(ArenaI18n.t('By color'),table([ArenaI18n.t('Color'),ArenaI18n.t('Games'),'W','D','L',ArenaI18n.t('Score %'),ArenaI18n.t('Draw %')],r.colors.map(c=>[c.color,...values(c)]),{right:[1,2,3,4,5,6]})),
   section(ArenaI18n.t('All recorded openings'),table(['#',ArenaI18n.t('Opening'),ArenaI18n.t('Games'),'W','D','L',ArenaI18n.t('Score %'),ArenaI18n.t('Draw %'),ArenaI18n.t('Pairs')],r.openings.map(o=>[o.opening_index+1,o.name,...values(o),o.complete_pairs===null?ArenaI18n.t('Unpaired'):number(o.complete_pairs,0)]),{right:[0,2,3,4,5,6,7,8]})),
   section(ArenaI18n.t('Starting positions'),r.openings.map(o=>'#'+(o.opening_index+1)+' '+clean(o.name)+ArenaI18n.t('\nFEN: ')+clean(o.fen)).join('\n\n')||'(None.)'),wrap(r.model+ArenaI18n.t(' Only current official results count; diagnostic attempts and invalidated rounds are excluded.')).join('\n')
  ]);
 }
 const poolLabels={fixed_anchor:ArenaI18n.t('Fixed reference'),estimated:ArenaI18n.t('Estimated'),disconnected:ArenaI18n.t('No comparison path to reference'),no_comparisons:ArenaI18n.t('No completed comparisons'),no_finite_fit:ArenaI18n.t('No finite fit: separated results'),not_converged:ArenaI18n.t('Fit did not converge'),uncertainty_unavailable:ArenaI18n.t('Uncertainty unavailable'),uncertainty_not_converged:ArenaI18n.t('Uncertainty did not converge')};
 function ratings(r){return report(r.name+ArenaI18n.t(' — Anchored pool ratings'),[
  fields([[ArenaI18n.t('Reference'),r.anchor.name+' = '+number(r.anchor.rating)],[ArenaI18n.t('Samples'),number(r.samples,0)+' '+r.sample_unit],[ArenaI18n.t('Connected participants'),r.connected_participants+' / '+r.participant_count],[ArenaI18n.t('Confidence'),r.confidence+ArenaI18n.t('% normal intervals')],[ArenaI18n.t('Order'),r.sort+' / '+r.direction],[ArenaI18n.t('Committed revision'),r.revision]]),
  table([ArenaI18n.t('Participant ID'),ArenaI18n.t('Engine'),ArenaI18n.t('Rating'),ArenaI18n.t('Delta ref.'),ArenaI18n.t('Rating CI ')+r.confidence+'%',ArenaI18n.t('LOS ref.'),ArenaI18n.t('Samples'),ArenaI18n.t('Status')],r.items.map(x=>[x.slot+1,x.name,number(x.rating),number(x.delta),interval(x.ci),los(x.los),number(x.samples,0),poolLabels[x.status]||x.status]),{right:[0,2,3,5,6],limits:[14,28,10,10,24,10,10,30]}),wrap(r.model+'. '+r.assumptions).join('\n'),ArenaI18n.t('N/A = unavailable, not zero. Participant ID is registration order, not rank. The reference rating is fixed; its own uncertainty is excluded. LOS is an estimate, not certainty.')
 ])}
 const resource=(p={},name,fallback)=>p.advertised&&!Object.keys(p.advertised).some(k=>k.toLowerCase()===name.toLowerCase())?ArenaI18n.t('N/A (unsupported)'):Object.entries(p.options||{}).find(([k])=>k.toLowerCase()===name.toLowerCase())?.[1]??p[name.toLowerCase()]??fallback;
 function profiles(items,includePaths=false){return report(ArenaI18n.t('Engine profiles'),items.length?items.map((p,i)=>section((i+1)+'. '+p.name,fields([
  [ArenaI18n.t('Reported identity'),p.identity?.name||ArenaI18n.t('Not tested')],[ArenaI18n.t('Author'),p.identity?.author||'N/A'],[ArenaI18n.t('Threads'),resource(p,ArenaI18n.t('Threads'),1)],[ArenaI18n.t('Hash (MB)'),resource(p,ArenaI18n.t('Hash'),1024)],[ArenaI18n.t('Time control'),timeControl(p.time_control)],[ArenaI18n.t('Shared GPU group'),p.gpu_group||ArenaI18n.t('No shared GPU group')],[ArenaI18n.t('Additional memory (MB)'),p.extra_memory_mb??256],[ArenaI18n.t('CPU affinity'),p.affinity?.length?p.affinity.join(', '):ArenaI18n.t('Unrestricted logical processors (OS scheduling)')],
  ...Object.entries(p.options||{}).filter(([k,v])=>includePaths||!/(path|file|directory|folder|network|weights|syzygy|book)/i.test(k)&&!(typeof v==='string'&&/^(?:[a-z]:[\\/]|\\\\|\/|https?:)/i.test(v))).map(([k,v])=>[ArenaI18n.t('UCI ')+k,v]),
  ...(includePaths?[[ArenaI18n.t('Executable'),p.path],[ArenaI18n.t('Working directory'),p.cwd||p.working_directory||ArenaI18n.t('Default')],[ArenaI18n.t('Arguments'),Array.isArray(p.args)?p.args.join(' '):p.args||ArenaI18n.t('None')]]:[])
 ]))):[ArenaI18n.t('No profiles.')])+(includePaths?'':ArenaI18n.t('\nLocal paths, launch arguments and file-related UCI options omitted from this sharing copy.\n'))}
 function experiment(job){const suite=job.kind==='suite';return report(job.name+' — '+clean(job.kind).replaceAll('_',' '),[
  fields([[ArenaI18n.t('State'),job.state],[ArenaI18n.t('Completed / total cases'),job.completed+' / '+job.total],...(suite?[[ArenaI18n.t('Accuracy'),pct(job.accuracy_pct)]]:[]),[ArenaI18n.t('Failures'),job.failures??0],[ArenaI18n.t('Time control'),timeControl(job.settings?.time_control)]]),
  table([ArenaI18n.t('Engine / case'),ArenaI18n.t('Threads'),ArenaI18n.t('Move'),...(suite?[ArenaI18n.t('Accuracy')]:[]),ArenaI18n.t('Search s'),...(suite?[ArenaI18n.t('Solve s')]:[]),ArenaI18n.t('Measured NPS'),ArenaI18n.t('Attempt')],job.results.map(r=>[r.profile+' / '+r.case.id,r.effective_threads??'N/A',r.san||r.move||'N/A',...(suite?[r.correct==null?'N/A':r.correct?ArenaI18n.t('Correct'):ArenaI18n.t('Incorrect')]:[]),number(r.elapsed_seconds,4),...(suite?[number(r.time_to_solve_seconds,4)]:[]),number(r.measured_nps,0),(r.official?ArenaI18n.t('Official'):r.ended||r.reason==='interrupted'?ArenaI18n.t('Archived'):ArenaI18n.t('Running'))+' / '+(r.reason||'running')+(r.detail?' / '+r.detail:'')]),{right:suite?[1,4,5,6]:[1,3,4]}),
  ...(job.kind==='benchmark'?[section(ArenaI18n.t('Benchmark averages'),table([ArenaI18n.t('Engine'),ArenaI18n.t('Threads'),ArenaI18n.t('NPS samples / completed searches'),ArenaI18n.t('Mean NPS'),ArenaI18n.t('Min NPS'),ArenaI18n.t('Max NPS')],(job.benchmark_summary||[]).map(r=>[r.profile,r.threads??'N/A',`${r.nps_samples??r.samples} / ${r.samples}`,number(r.mean_nps,0),number(r.min_nps,0),number(r.max_nps,0)]),{right:[1,2,3,4,5]}))]:[]),
  wrap(ArenaI18n.t('Accuracy includes failed searches as unsolved cases; interrupted attempts are excluded. Solve time starts at the final uninterrupted sequence of correct primary PVs, provided the final move is correct. Earlier results retain their original definition. Measured NPS uses wall search time; startup is excluded. Each case uses a fresh engine process, the experiment search limit and no opening book.')).join('\n')
 ])}
 function graph(data){
  const xs=[...new Set(data.series.flatMap(s=>s.points.map(p=>p.x)))].sort((a,b)=>a-b),maps=data.series.map(s=>new Map(s.points.map(p=>[p.x,p.y])));
  return report(data.title+ArenaI18n.t(' — Graph data'),[fields([[ArenaI18n.t('Scope'),ArenaI18n.t('Displayed graph samples; long histories may be sampled')],[ArenaI18n.t('Units'),data.unit],[ArenaI18n.t('Context'),data.note||ArenaI18n.t('None')]]),table([data.timeAxis?ArenaI18n.t('Time (UTC)'):data.xLabel,...data.series.map(s=>s.name)],xs.map(x=>[data.timeAxis?new Date(x*1000).toISOString():x,...maps.map(m=>number(m.get(x),4))]),{right:data.series.map((_,i)=>i+1)}),ArenaI18n.t('N/A = no reported sample at this point, not zero.')])
 }
 function codeBlock(text,format){if(format==='forum')return '[code]\n'+text.replace(/\[\/code\]/gi,'[/ code]')+'[/code]';if(format==='markdown'){const runs=text.match(/`+/g)||[];const fence='`'.repeat(runs.reduce((n,s)=>Math.max(n,s.length+1),3));return fence+'text\n'+text+fence}return text}
 const api={clean,width,wrap,table,number,pct,los,interval,section,fields,report,timeControl,statsTable,standings,openings,ratings,profiles,experiment,graph,codeBlock,modelNote};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ArenaText=api;
})(typeof globalThis!=='undefined'?globalThis:this);
