'use strict';
const broadcastWoods={maple:'#ead8ae',ash:'#ddd5be',oak:'#bd915c',walnut:'#70503a',rosewood:'#713e32',ebony:'#343538'};
function broadcastAppearance(config){
 const vars={};
 const raw=Number(config.dark_lighten),lighten=Number.isFinite(raw)?Math.max(0,Math.min(60,raw))/100:0;
 for(const side of ['light','dark']){
  const wood=Object.hasOwn(broadcastWoods,config['board_'+side])?config['board_'+side]:'theme';
  vars['--board-'+side+'-image']=wood==='theme'?'none':`url("/assets/textures/${wood}.png")`;
  vars['--board-'+side+'-color']=broadcastWoods[wood]||`var(--${side})`;
  if(wood!=='theme'){
   const rgb=broadcastWoods[wood].slice(1).match(/../g).map(x=>parseInt(x,16));
   const wash=[239,216,184],amount=side==='dark'?lighten:0;
   const luminance=rgb.map((v,i)=>(v*(1-amount)+wash[i]*amount)/255).reduce((n,v,i)=>n+v*[.2126,.7152,.0722][i],0);
   vars['--board-'+side+'-ink']=luminance>.57?'#332b23':'#fff4de';
  }else vars['--board-'+side+'-ink']=side==='light'||lighten>.4?'#332b23':'#fff4de';
 }
 vars['--board-dark-wash']=`linear-gradient(rgba(239,216,184,${lighten}),rgba(239,216,184,${lighten}))`;
 return vars;
}
function broadcastEvaluation(game={},range=5){
 const info=game.info||{},mate=Number.isFinite(info.mate),cp=Number.isFinite(info.cp);
 if(!mate&&!cp)return {available:false,label:'—',white:50,direction:0};
 const side=game.clock_active||game.info_side||'white',pawns=cp?info.cp/100:0;
 // Scores already use White's perspective, including the signed mate distance.
 const direction=mate?(Math.sign(info.mate)||(side==='white'?-1:1)):Math.sign(pawns);
 const label=mate?(direction<0?'−M':'M')+Math.abs(info.mate):(pawns>0?'+':'')+pawns.toFixed(2);
 const limit=Number.isFinite(range)&&range>0?range:5;
 return {available:true,label,direction,white:mate?50+50*direction:50+50*Math.max(-limit,Math.min(limit,pawns))/limit};
}
function paintBroadcastEvaluation(bar,label,fill,game,flip,range=5){
 const value=broadcastEvaluation(game||{},range);
 bar.classList.toggle('flipped',!!flip);
 bar.classList.toggle('white-favored',value.direction>=0);
 bar.classList.toggle('unavailable',!value.available);
 if(label.textContent!==value.label)label.textContent=value.label;
 fill.style.height=value.white+'%';
 const description=value.available?`${value.label} · White perspective · engine evaluation, not a win probability`:'Evaluation unavailable';
 bar.setAttribute('role','img');bar.setAttribute('aria-label',description);bar.title=description;
}
function broadcastTickerParts(wire){
 const separator='\u2003◆\u2003',parts=[];
 const engine=text=>{
  // Only decorate a trailing rating label beside a result's engine name.
  const label=/\((?:-?\d+ Elo|Elo pending)\)(\s*)$/.exec(text);
  if(!label){parts.push({text});return}
  const end=text.length-label[1].length;
  parts.push({text:text.slice(0,label.index)},
             {text:text.slice(label.index,end),kind:'rating'},
             {text:text.slice(end)});
 };
 for(const [i,line] of wire.split(separator).entries()){
  if(i)parts.push({text:separator,kind:'separator'});
  // Result headlines have double spaces around their PGN score. Match that
  // delimiter so an engine's version number is never treated as its score.
  const match=/ {2}(1\/2-1\/2|1-0|0-1) {2}/.exec(line);
  if(!match){parts.push({text:line});continue}
  const start=match.index+2,end=start+match[1].length;
  engine(line.slice(0,start));parts.push({text:match[1],accent:true,kind:'score'});
  const note=line.indexOf(' · winner ',end);
  const outcomeEnd=note<0?line.length:note;
  const divider=line.lastIndexOf(' · ',outcomeEnd-1);
  if(divider>=end&&divider+3<outcomeEnd){
   engine(line.slice(end,divider));
   parts.push({text:line.slice(divider,divider+3)},
              {text:line.slice(divider+3,outcomeEnd),accent:true,kind:'outcome'},
              {text:line.slice(outcomeEnd)});
  }else engine(line.slice(end));
 }
 return parts;
}
function createBroadcastTicker(node,clip){
 let pending='',shown=null,mode=null,visible=false;
 const commit=()=>{if(shown!==pending){
  const doc=node.ownerDocument;
  node.replaceChildren(...broadcastTickerParts(pending).map(part=>{
   if(!part.accent&&!part.kind)return doc.createTextNode(part.text);
   const span=doc.createElement('span');span.className=(part.kind==='rating'?'':'ticker-result ')+'ticker-'+(part.kind||'result');span.textContent=part.kind==='separator'?'◆':part.text;return span;
  }));shown=pending;
 }};
 // New results must not change the width or wording of a line still on air.
 // At the iteration boundary, the old line is gone and the next starts outside
 // the clip. Keep only the latest pending snapshot, not a backlog of old scores.
 node.addEventListener('animationiteration',event=>{
  if(event.target===node&&event.animationName==='wire'&&mode==='scroll')commit();
 });
 return function updateTicker(wire,config){
  const nextMode=config.ticker_mode==='headlines'?'headlines':'scroll';
  const fresh=shown===null||mode!==nextMode||!visible;
  pending=wire;mode=nextMode;visible=!!config.ticker;
  clip.style.visibility=visible?'visible':'hidden';
  node.className=(node.dataset?.tickerBase?node.dataset.tickerBase+' ':'')+(mode==='headlines'?'headlines':'');
  const duration=config.ticker_seconds+'s';
  if(node.style.animationDuration!==duration){
   // Changing CSS duration alone recalculates the current position and jumps
   // the on-screen text. Keep its pass progress while changing its velocity.
   const animation=!fresh&&mode==='scroll'?node.getAnimations?.().find(a=>a.animationName==='wire'):null;
   const oldDuration=animation?.effect?.getTiming().duration,oldTime=animation?.currentTime;
   node.style.animationDuration=duration;
   if(Number.isFinite(oldDuration)&&oldDuration>0&&Number.isFinite(oldTime))animation.currentTime=oldTime*config.ticker_seconds*1000/oldDuration;
  }
  node.style.fontSize=config.ticker_size+'px';
  node.style.setProperty('--ticker-start',clip.clientWidth+'px');
  if(fresh||mode==='headlines'||!visible)commit();
  const style=config.ticker_style||{};for(const[k,v]of Object.entries({text:style.text_color,score:style.score_color,outcome:style.outcome_color,separator:style.separator_color}))node.style.setProperty('--ticker-'+k,v||'');
  node.style.setProperty('--ticker-gap',(style.spacing||1)+'em');
  if(node.querySelectorAll)for(const sep of node.querySelectorAll('.ticker-separator'))sep.textContent=({diamond:'◆',bullet:'•',bar:'│',space:''})[style.separator||'diamond'];
 };
}
if(typeof module!=='undefined')module.exports={createBroadcastTicker,broadcastTickerParts,broadcastEvaluation,paintBroadcastEvaluation,broadcastAppearance};
(()=>{
 if(typeof document==='undefined')return;
 if(document.body.dataset.broadcastDesigner)return;
 const $=id=>document.getElementById(id), key=new URLSearchParams(location.search).get('key');
 const stage=$('stage'),updateTicker=createBroadcastTicker($('ticker'),$('tickerClip'));
 let data=null,last=0,revision=null,lastGame='',tableMode='',appearanceKey='';
 let boardFen='',boardStyle='',sound=null,flipped=null;
 let thinkingKey='',thinkingSince=0;
 function scale(){stage.style.transform=`scale(${Math.min(innerWidth/1920,innerHeight/1080)})`}
 addEventListener('resize',scale);scale();
 const text=(id,t)=>{if($(id).textContent!==String(t))$(id).textContent=t},num=n=>Number(n||0).toLocaleString('en-US');
 function board(fen,move,c){
  const style=c.pieces+':'+c.flip+':'+move;if(fen===boardFen&&style===boardStyle)return;boardFen=fen;boardStyle=style;
  const pieces={};let rank=8,file=0;for(const ch of fen.split(' ')[0]){if(ch==='/'){rank--;file=0}else if(/\d/.test(ch)){file+=+ch}else{pieces['abcdefgh'[file++]+rank]=ch}}
  const frag=document.createDocumentFragment();for(let row=0;row<8;row++)for(let col=0;col<8;col++){
   const f=c.flip?7-col:col,r=c.flip?row+1:8-row,sq='abcdefgh'[f]+r,el=document.createElement('div');el.className='square'+((f+r)%2===1?' dark':'')+(move&&(move.slice(0,2)===sq||move.slice(2,4)===sq)?' last':'');
   const p=pieces[sq];if(p){const img=document.createElement('img');img.src=`/assets/pieces/${c.pieces}/${p===p.toUpperCase()?'w':'b'}${p.toUpperCase()}.svg`;img.alt=p;el.append(img)}
   if(col===0){const label=document.createElement('span');label.className='coord';label.textContent=r;el.append(label)}
   if(row===7){const label=document.createElement('span');label.className='coord file';label.textContent='abcdefgh'[f];el.append(label)}frag.append(el)
  }$('board').replaceChildren(frag)
 }
 function clearThinking(){document.querySelector('#board .thinking-arrow')?.remove();text('arrowLegend','NOT PLAYED MOVES')}
 function thinkingArrow(d){
  const g=d.game,c=d.config,h=g?.thinking;
  const valid=c.thinking_arrows!==false&&d.connected&&g?.phase==='Live'&&g.clock_active&&
   h&&h.fen===g.fen&&h.side===g.clock_active&&h.from!==h.to&&['from','to'].every(k=>/^[a-h][1-8]$/.test(h[k]));
  const key=valid?[g.attempt,h.fen,h.uci,h.side].join('|'):'';
  if(key!==thinkingKey){thinkingKey=key;thinkingSince=performance.now();clearThinking()}
  if(!key||performance.now()-thinkingSince<1000*(c.arrow_delay??1)){clearThinking();return}
  const square=s=>{let x=s.charCodeAt(0)-97,y=8-Number(s[1]);if(c.flip){x=7-x;y=7-y}return [x*100+50,y*100+50]};
  const a=square(h.from),b=square(h.to),dx=b[0]-a[0],dy=b[1]-a[1],len=Math.hypot(dx,dy),ux=dx/len,uy=dy/len;
  const base=[b[0]-ux*32,b[1]-uy*32],ns='http://www.w3.org/2000/svg';
  let svg=document.querySelector('#board .thinking-arrow');
  if(!svg){svg=document.createElementNS(ns,'svg');svg.setAttribute('class','thinking-arrow');svg.setAttribute('viewBox','0 0 800 800');svg.setAttribute('role','img');$('board').append(svg)}
  const drawing=key+':'+c.flip;
  if(svg.dataset.drawing!==drawing){
   svg.dataset.drawing=drawing;svg.dataset.from=h.from;svg.dataset.to=h.to;
   svg.setAttribute('aria-label',`${h.side==='white'?'White':'Black'} thinking: ${h.san}`);
   const shaft=document.createElementNS(ns,'path'),head=document.createElementNS(ns,'path');
   shaft.setAttribute('d',`M${a} L${base}`);shaft.setAttribute('class','thinking-shaft');
   head.setAttribute('d',`M${b} L${base[0]-uy*23},${base[1]+ux*23} L${base[0]+uy*23},${base[1]-ux*23} Z`);head.setAttribute('class','thinking-head');
   svg.replaceChildren(shaft,head);
  }
  text('arrowLegend','CYAN ARROW · THINKING '+h.san);
 }
 function clock(side,g,age){
  const c=g?.clocks?.[side];if(!c)return '—';const tc=c.control||{};
  const active=g.clock_active===side,elapsed=active?Number(g.search_elapsed||0)+Number(g.clock_age||0)+(data.connected?Math.min(age,2.5):0):Number(c.elapsed||0);
  let n=Number(c.remaining);if(tc.kind==='nodes'||tc.kind==='depth')n=elapsed;
  else if(tc.kind==='movetime')n=Number(tc.seconds||0)-(active?elapsed:0);
  else if(active)n-=Math.max(0,elapsed-(['delay','bronstein'].includes(tc.kind)?Number(tc.delay||0):0));
  if(c.remaining===null&&!['nodes','depth','movetime'].includes(tc.kind))return '∞';if(!Number.isFinite(n))return '—';
  n=Math.max(0,n);return Math.floor(n/60)+':'+Math.floor(n%60).toString().padStart(2,'0')+'.'+Math.floor(n%1*10)
 }
 function drawTables(d){
  const c=d.config,step=Math.floor(d.server_time/c.panel_seconds);
  const ratings=c.show_ratings&&d.ratings.length&&Math.floor(step/2)%2===1;
  const rows=ratings?d.ratings:d.summary.standings||[];const page=step%2;
  const chosen=rows.length>10?rows.slice(page*10,page*10+10):rows.slice(0,10);
  text('tableEyebrow',ratings?'RATING CENTER • '+c.category.toUpperCase():'TOURNAMENT • CURRENT FIELD');text('tableTitle',ratings?'Opponent-adjusted ratings':'Live standings');text('tableTag',ratings?'ELO · GAMES':'POINTS · GAMES');
  const mode=JSON.stringify([ratings,chosen]);if(tableMode!==mode){tableMode=mode;
   $('ranking').replaceChildren(...chosen.map(r=>{const row=document.createElement('div');row.className='ranking-row';
    for(const [cls,value] of [['rank',r.rank||'—'],['name',r.name],['value',ratings?(r.rating==null?'—':Number(r.rating).toFixed(0)):(Number(r.points??r.score??0).toFixed(1))],['games',num(r.games)+' games']]){const cell=document.createElement('span');cell.className=cls;cell.textContent=value;row.append(cell)}return row}));
  }
  const when=ratings?d.ratings_at:d.summary_at;
  text('tableNote',ratings?`All recorded ${c.category} games · estimated Elo · snapshot ${when?new Date(when*1000).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}):'pending'}`:'Ranked by points, then tournament tiebreaks · unequal games while play continues');
 }
 function render(d){
  data=d;last=performance.now();const c=d.config,g=d.game,s=d.summary;stage.className=c.theme;
  const appearance=JSON.stringify([c.board_light,c.board_dark,c.dark_lighten]);
  if(appearanceKey!==appearance){appearanceKey=appearance;for(const [k,v]of Object.entries(broadcastAppearance(c)))stage.style.setProperty(k,v)}
  text('title',c.title||s.name||'Engine Arena');text('subtitle',c.subtitle);text('complete',num(s.completed)+' / '+num(s.total));
  const pct=s.total?100*s.completed/s.total:0;text('total',pct.toFixed(1)+'% complete · '+(s.active_participants||'—')+' engines');$('progressBar').style.width=pct+'%';
  text('connection',d.connected?'● CONNECTED':'● RECONNECTING');text('liveCount',num(d.status.active)+' LIVE');
  $('waiting').hidden=!!g;text('waitingDetail',!d.connected?'Waiting for Engine Arena to reconnect.':s.state==='paused'?'Tournament paused. Waiting for play to resume.':s.state==='completed'?'Tournament complete. Final standings are shown.':'Waiting for a new game to begin.');
  text('phase',g?.phase?.toUpperCase()||'BETWEEN GAMES');text('gameNumber',g?'FEATURED GAME':'Full-game coverage');
  text('whiteName',g?.white?.name||'White');text('blackName',g?.black?.name||'Black');
  for(const side of ['white','black']){const p=g?.[side],value=p?.rating;
   text(side+'Rating',value==null?'Elo —':'Elo '+Number(value).toFixed(0));
   $(side+'Rating').title=value==null?'No unambiguous rating available for this recorded profile':`${c.category} Rating Center · snapshot ${new Date(p.rating_at*1000).toLocaleTimeString()}`;
  }
  if(flipped!==c.flip){const wrap=document.querySelector('.board-wrap'),zone=wrap.parentElement;
   zone.insertBefore($(c.flip?'whiteName':'blackName').parentElement,wrap);
   zone.insertBefore($(c.flip?'blackName':'whiteName').parentElement,document.querySelector('.game-caption'));flipped=c.flip;
  }
  board(g?.fen||'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',g?.last_move,c);
  thinkingArrow(d);
  const info=g?.info||{};
  paintBroadcastEvaluation($('evalWhite').parentElement,$('evalScore'),$('evalWhite'),g,c.flip,c.eval_range??5);
  text('lastMove',g?.san?'LAST MOVE  '+g.san:'Waiting for the next opening');
  text('depth',info.depth?'DEPTH '+info.depth:'—');text('pv',info.pv||'No principal variation reported for this position');
  text('searchInfo',info.nps?num(info.nps)+' nodes/sec · engine-reported evaluation':'Engine-reported evaluation · not a win probability');
  const tc=s.conditions?.time_control;text('condition',tc?.seconds?`${tc.seconds/60} min + ${tc.increment||0} sec`:'');
  if(g&&(revision!==g.revision||lastGame!==g.attempt)){
   $('moves').replaceChildren(...(g.moves||[]).slice(-16).map((m,i,a)=>{const span=document.createElement('span');span.className='move'+(i===a.length-1?' latest':'');const n=document.createElement('span');n.className='number';n.textContent=m.label+' ';span.append(n,document.createTextNode(m.san||''));return span}));
   if(c.sound&&revision!==null&&lastGame===g.attempt){sound??=new Audio('/assets/player-move.wav');sound.currentTime=0;sound.play().catch(()=>{})}
   revision=g.revision;lastGame=g.attempt;
  }
  $('result').hidden=!g?.reason;if(g?.reason){$('result').replaceChildren();const b=document.createElement('b');b.textContent=g.official?g.result:'NO OFFICIAL RESULT';$('result').append(b,document.createTextNode(String(g.reason).replaceAll('_',' ')))}
  drawTables(d);
  const headlines=d.headlines.map(h=>h.text);if(!headlines.length)headlines.push(`${s.name||'Engine Arena'} · ${num(s.completed)} counted games · Full-game coverage, opening to result`,`Standings show tournament points. Rating Center estimates account for the opposition.`,`ENGINE ARENA · Independent broadcast output · Your normal workspace remains free to use`);
  const wire=c.ticker_mode==='headlines'?headlines[Math.floor(d.server_time/14)%headlines.length]:headlines.join('\u2003◆\u2003');
  updateTicker(wire,c);
 }
 async function poll(){try{const r=await fetch('/feed?key='+encodeURIComponent(key),{cache:'no-store'});if(!r.ok)throw Error();render(await r.json())}catch{if(data){data.connected=false;thinkingKey='';clearThinking();text('connection','● RECONNECTING');text('phase','UPDATES PAUSED')}}finally{setTimeout(poll,500)}}
 setInterval(()=>{if(!data)return;const age=(performance.now()-last)/1000;for(const side of ['white','black']){text(side+'Clock',clock(side,data.game,age));$(side+'Clock').classList.toggle('active',data.game?.clock_active===side&&data.connected&&age<4)}},100);
 setInterval(()=>{if(last&&performance.now()-last>4000){thinkingKey='';clearThinking()}},500);
 poll();
})();
