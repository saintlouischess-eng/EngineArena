'use strict';
const BroadcastModel=(()=>{
 const clone=v=>JSON.parse(JSON.stringify(v)), clamp=(n,a,b)=>Math.max(a,Math.min(b,Number(n)||0));
 const panel=(type,x,y,w,h,extra={})=>({id:type+'-'+Math.random().toString(36).slice(2,9),type,x,y,w,h,visible:true,locked:false,font_size:24,heading_size:0,detail_size:0,auto_fit:true,logo_size:96,header_progress:true,header_eta:true,padding:20,title:'',background:'',color:'',columns:type==='ratings'?['rating','games']:['points','games'],rows:10,limit:20,text:'',image:'',graph_style:'line',metric:'evaluation',engines:'both',white_color:'#dfbb76',black_color:'#56bed9',legend:true,grid:true,series_colors:{},series_styles:{},...extra});
 const layouts={
  tournament:[['header',2,2,96,9],['board',2,12,47,79],['rotation',51,12,47,46],['analysis',51,60,47,31],['ticker',0,93,100,7]],
  match:[['header',2,2,96,9],['board',2,12,48,79],['scoreboard',52,12,46,21],['evalgraph',52,35,46,23],['analysis',52,60,46,25],['resultsstrip',52,86,46,6],['ticker',0,94,100,6]],
  board:[['header',2,2,96,8],['board',2,11,67,82],['analysis',71,11,27,42],['progress',71,55,27,18],['conditions',71,75,27,18],['ticker',0,94,100,6]],
  graph:[['header',2,2,96,8],['board',2,11,45,81],['standings',49,11,49,48],['evalgraph',49,61,49,31],['ticker',0,94,100,6]],
  statistics:[['header',2,2,96,9],['standings',2,13,46,60],['ratings',50,13,48,60],['progress',2,75,30,16],['wdl',34,75,30,16],['conditions',66,75,32,16],['ticker',0,94,100,6]],
  intermission:[['header',2,2,96,10],['text',12,25,76,35],['progress',20,65,60,20],['ticker',0,94,100,6]]
 };
 const presetInfo={
  tournament:['Tournament classic','A familiar board with rotating standings and ratings.','tournament','charcoal',400],
  match:['Head-to-head studio','Two engines, match points and a shared thinking graph.','match','royal',2],
  league:['Small league','Eight-engine field, all scores and compact analysis.','graph','forest',8],
  swiss:['Swiss / open event','Sixteen leaders, paired pages and game statistics.','graph','ocean',32],
  marathon:['Marathon TV','Warm ash and rosewood, large field and a slow gold ticker.','tournament','charcoal',400],
  light:['Daylight magazine','Light parchment, readable wood and quiet headlines.','board','parchment',64],
  board:['Board first','A large board with conditions and progress at the side.','board','burgundy',64],
  cinema:['3D showcase','Walnut and maple, Soviet pieces and a slow room tour.','board','charcoal',64],
  club:['Live chess club','A living room around the board, bounded to 30 FPS.','board','forest',64],
  graph:['Analyst desk','Board, standings and both engines in one graph.','graph','blue',64],
  statistics:['Statistics overview','Side-by-side rankings, progress and results.','statistics','emerald',400],
  intermission:['Intermission','A message and progress while the event continues.','intermission','royal',400]
 };
 const tickerPresets={
  warm:{name:'Warm TV · your look',ticker_mode:'scroll',ticker_seconds:150,ticker_size:28,ticker_style:{score_color:'#dfbb76',outcome_color:'#dfbb76',text_color:'#f2f0eb',separator_color:'#a99574',background:'#1d1e1f',spacing:1.3,separator:'diamond',label:'ARENA WIRE'}},
  colorful:{name:'Results in color',ticker_mode:'scroll',ticker_seconds:150,ticker_size:28,ticker_style:{score_color:'#74dfb0',outcome_color:'#ffc273',text_color:'#f1f4f8',separator_color:'#8ca8ff',background:'#18212d',spacing:1.4,separator:'diamond',label:'LIVE RESULTS'}},
  quiet:{name:'Quiet headlines',ticker_mode:'headlines',ticker_seconds:150,ticker_size:26,ticker_style:{score_color:'#f5c775',outcome_color:'#9edbce',headline_seconds:20,spacing:1,separator:'bullet',label:'LATEST'}},
  light:{name:'Daylight ticker',ticker_mode:'scroll',ticker_seconds:180,ticker_size:27,ticker_style:{score_color:'#8c391f',outcome_color:'#245f4b',text_color:'#30291e',separator_color:'#7d603d',background:'#f3ecda',label_color:'#30291e',spacing:1.5,separator:'bar',label:'ARENA WIRE'}}
 };
 function preset(key,pool){const info=presetInfo[key]||presetInfo.tournament;pool=Math.max(2,Number(pool)||info[4]);const panels=layouts[info[2]].map(v=>panel(...v));
  for(const p of panels){if(p.type==='header')p.padding=8;if(p.type==='ticker')p.padding=0;if(p.type==='resultsstrip'){p.padding=10;p.font_size=16}if(p.type==='conditions'){p.font_size=18;p.padding=16}if(p.type==='progress')p.font_size=20}
  const rows=pool<=8?pool:10,limit=pool<=16?0:20;
  for(const p of panels){p.rows=rows;p.limit=limit;if(p.type==='rotation'){p.inherit_counts=false}if(p.type==='evalgraph')p.graph_style=key==='match'?'dots':'line'}
  const text=panels.find(p=>p.type==='text');if(text)text.text='We’ll be right back.\nThe tournament continues.';
  const appearance={theme:info[3],board_mode:'2d',board_light:'ash',board_dark:'rosewood',dark_lighten:28};
  if(key==='marathon')Object.assign(appearance,clone(tickerPresets.warm),{pieces:'classic-bold'});
  if(key==='light')Object.assign(appearance,clone(tickerPresets.light),{pieces:'classic',board_light:'maple',board_dark:'walnut'});
  if(['cinema','club'].includes(key))Object.assign(appearance,{board_mode:'3d',pieces3d:key==='cinema'?'tal1962':'staunton1849',scene3d:{board:'drueke',environment:key==='club'?'live-club':'study',mode:'presentation',tour:'cinematic',tourSpeed:.65,live:key==='club',fps:30,roomMotion:'animate'}});
  delete appearance.name;
  return {id:'scene-'+Date.now().toString(36)+Math.random().toString(36).slice(2,5),name:info[0],seconds:60,tid:'',enabled:true,appearance,panels}}
 function effective(c){const a=scene(c)?.appearance||{},out={...c,...a};for(const k of ['scene3d','camera3d','ticker_style'])out[k]={...c[k],...a[k]};return out}
 function scene(c){return c.design.scenes.find(s=>s.id===c.design.active)||c.design.scenes[0]}
 function paginate(rows,limit,size){const picked=limit>0?rows.slice(0,limit):rows;size=Math.max(1,size);return Array.from({length:Math.max(1,Math.ceil(picked.length/size))},(_,i)=>picked.slice(i*size,i*size+size))}
 function pages(c,d,p){
  const ratings=c.rating_scope==='field'?(d.ratings||[]).filter(r=>(d.field_rating_ids||[]).includes(r.id)):(d.ratings||[]);
  const types=p.type==='rotation'?(c.show_ratings?['standings','ratings']:['standings']):[p.type];
  return types.flatMap(type=>paginate(type==='ratings'?ratings:(d.summary?.standings||[]),p.type==='rotation'&&p.inherit_counts!==false?c[type==='ratings'?'ratings_limit':'standings_limit']:p.limit,p.type==='rotation'&&p.inherit_counts!==false?c.rows:p.rows).map((rows,i,a)=>({type,rows,page:i+1,pages:a.length})));
 }
 function geometry(p,dx,dy,resize=false,snap=1){const q=clone(p),grid=n=>snap>0?Math.round(n/snap)*snap:n;if(resize){q.w=clamp(grid(p.w+dx),2,100-p.x);q.h=clamp(grid(p.h+dy),2,100-p.y)}else{q.x=clamp(grid(p.x+dx),0,100-p.w);q.y=clamp(grid(p.y+dy),0,100-p.h)}return q}
 class History{constructor(){this.undoStack=[];this.redoStack=[]}push(value){this.undoStack.push(clone(value));this.undoStack=this.undoStack.slice(-60);this.redoStack=[]}undo(value){if(!this.undoStack.length)return value;this.redoStack.push(clone(value));return this.undoStack.pop()}redo(value){if(!this.redoStack.length)return value;this.undoStack.push(clone(value));return this.redoStack.pop()}}
 // Presentation only: retain the complete recorded identity in data and tooltips.
 function commonConfiguration(rows){
  const suffixes=rows.map(r=>String(r.name||'').match(/\s+[·•]\s+(\d+\s+threads?(?:\s.*)?)$/i)?.[1]);
  return suffixes.length&&suffixes.every(s=>s&&s===suffixes[0])?suffixes[0]:'';
 }
 function displayName(name,common=''){
  let text=String(name||'');
  if(common&&text.endsWith(' · '+common))text=text.slice(0,-common.length-3);
  else if(common&&text.endsWith(' • '+common))text=text.slice(0,-common.length-3);
  return text.replace(/\bdev-(\d{8})-([a-f0-9]{6})[a-f0-9]+\b/ig,'dev-$1-$2');
 }
 function gameContext(game){
  if(!game)return 'Waiting for the next game';
  if(game.waiting_next)return 'Final position · waiting for the next game';
  if(game.reason)return game.official?'Official final position':'Attempt ended';
  const fen=String(game.fen||'').split(' '),move=Number(fen[5]);
  return Number.isInteger(move)&&move>0?`Move ${move} · ${fen[1]==='b'?'Black':'White'} to move`:'Following the game';
 }
 function analysisSide(game){
  if(['white','black'].includes(game?.info_side))return game.info_side;
  if(game?.phase==='Live'&&['white','black'].includes(game.clock_active))return game.clock_active;
  const last=game?.moves?.at(-1);
  return last?.info&&game?.info&&['cp','mate','depth','pv'].every(k=>last.info[k]===game.info[k])?last.side:null;
 }
 function shortPV(pv,maxMoves=6){
  const tokens=String(pv||'').trim().split(/\s+/).filter(Boolean);let moves=0,end=0;
  for(const token of tokens){if(!/^\d+\.(?:\.\.)?$/.test(token))moves++;if(moves>maxMoves)break;end++}
  return tokens.slice(0,end).join(' ')+(end<tokens.length?' …':'');
 }
 class FinalPosition{
  constructor(){this.tid=null;this.game=null}
  present(data){
   const tid=data.config?.tid||'';
   if(tid!==this.tid){this.tid=tid;this.game=null}
   if(data.game){this.game=data.game.reason?clone(data.game):null;return data}
   if(!this.game||!data.connected)return data;
   return {...data,game:{...this.game,phase:'Waiting for the next game',waiting_next:true,clock_active:null,thinking:null}};
  }
 }
 return {clone,panel,preset,presetInfo,tickerPresets,effective,scene,paginate,pages,geometry,History,layouts,commonConfiguration,displayName,gameContext,analysisSide,shortPV,FinalPosition};
})();
if(typeof module!=='undefined')module.exports=BroadcastModel;
