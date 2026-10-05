if(typeof module!=='undefined'&&!globalThis.ArenaI18n)require('./i18n.js');
'use strict';
(function(root){
 const moves=pv=>Array.isArray(pv)?pv:String(pv||'').trim().split(/\s+/).filter(Boolean);
 function numbered(pv,moveNumber=1,side='white'){
  let n=Number.isInteger(moveNumber)&&moveNumber>0?moveNumber:1,black=side==='black';
  return moves(pv).map((move,i)=>{const text=(!black?n+'. ':i===0?n+'… ':'')+move;if(black)n++;black=!black;return text}).join(' ');
 }
 const score=info=>{const value=Number.isFinite(info.mate)?'M'+info.mate:Number.isFinite(info.cp)?(info.cp>0?'+':'')+(info.cp/100).toFixed(2):'—';return value==='—'?value:(info.score_bound==='lowerbound'?'≥ ':info.score_bound==='upperbound'?'≤ ':'')+value};
 const seconds=value=>Number.isFinite(value)?(value/1000).toFixed(2)+ArenaI18n.t(' s'):'—';
 const nodes=value=>!Number.isFinite(value)?'—':value>=1e9?(value/1e9).toFixed(2)+'G':value>=1e6?(value/1e6).toFixed(2)+'M':value>=1e3?(value/1e3).toFixed(1)+'k':String(value);
 const model={numbered,score,seconds,nodes};root.ArenaSearch=model;
 if(typeof module!=='undefined')module.exports=model;
 if(typeof document==='undefined')return;
 let busy=false,loaded='',context='';
 const exact=n=>Number.isFinite(n)?n.toLocaleString(ArenaI18n.locale):'—';
 const metric=(name,value)=>ArenaI18n.h`<div><dt>${esc(name)}</dt><dd>${esc(value)}</dd></div>`;
 function entry(row,data,current){
  const i=row.info,wdl=Array.isArray(i.wdl)&&i.wdl.length===3?i.wdl:null,total=wdl?.reduce((a,b)=>a+b,0);
  const move=numbered(row.move,data.move_number,data.side),label=current?(data.selected?ArenaI18n.t('Selected move'):ArenaI18n.t('Current best move')):ArenaI18n.t('Earlier choice #')+row.number;
  return {summary:ArenaI18n.h`<span class="search-choice-move" title="${esc(label+' · '+move)}"><span class="search-choice-kind">${current?ArenaI18n.t('Now'):'#'+row.number}</span><strong>${esc(move)}</strong></span><b class="search-choice-score" title="Engine evaluation from White’s perspective. ≥ / ≤ indicate bounds.">${esc(score(i))}</b><span title="Depth / selective depth in plies">${esc(i.depth??'—')} / ${esc(i.seldepth??'—')}</span><span class="search-choice-time" title="Engine-reported search time">${esc(seconds(i.time))}</span><span class="search-choice-nodes" title="Exact reported nodes: ${esc(exact(i.nodes))}">${esc(nodes(i.nodes))}</span><span class="search-choice-toggle" aria-hidden="true"></span>`,
   detail:ArenaI18n.h`<dl class="search-candidate-stats">${metric(ArenaI18n.t('Depth / selective'),(i.depth??'—')+' / '+(i.seldepth??'—'))}${metric(ArenaI18n.t('Search time'),seconds(i.time))}${metric(ArenaI18n.t('Nodes'),exact(i.nodes))}${metric(ArenaI18n.t('Nodes / s'),exact(i.nps))}${metric(ArenaI18n.t('Hash'),i.hashfull===undefined?'—':(i.hashfull/10).toFixed(1)+'%')}${metric(ArenaI18n.t('TB hits'),exact(i.tbhits))}</dl><p class="search-candidate-wdl">White W / D / L: ${total?wdl.map(n=>(n/total*100).toFixed(1)).join(' / ')+'%':'—'}</p><p class="search-recorded-pv" tabindex="0" aria-label="Recorded principal variation">${esc(numbered(i.pv,data.move_number,data.side))}</p>`};
 }
 function updateEntry(node,row,data,current){
  const html=entry(row,data,current);
  if(!node){node=document.createElement('details');node.className='search-candidate';node.innerHTML=ArenaI18n.h('<summary class="search-choice-row" data-help="Expand this choice for exact statistics and its full numbered PV. Earlier choices retain their final reported values."></summary><div class="search-candidate-detail"></div>')}
  node.dataset.searchEntry=row.number;node.classList.toggle('current-candidate',current);
  // Keep the details/summary elements alive so focus and expansion survive updates.
  if(node._summary!==html.summary){node.querySelector('summary').innerHTML=html.summary;node._summary=html.summary}
  if(node._detail!==html.detail){
   const detail=node.querySelector('.search-candidate-detail');
   if(node._detail){const fresh=document.createElement('div');fresh.innerHTML=html.detail;const values=fresh.querySelectorAll('dd,p');detail.querySelectorAll('dd,p').forEach((el,i)=>{if(el.textContent!==values[i].textContent)el.textContent=values[i].textContent})}
   else detail.innerHTML=html.detail;
   node._detail=html.detail;
  }
  return node;
 }
 function updateHistory(list,data){
  const scroll=list.scrollTop,left=list.scrollLeft,top=list.getBoundingClientRect().top;
  const old=[...list.querySelectorAll('.search-candidate')],byId=new Map(old.map(e=>[e.dataset.searchEntry,e]));
  // Anchor an existing visible choice, not total height (which fails when the
  // bounded history evicts an old row as it prepends a new one).
  const retained=new Set(data.history.map(row=>String(row.number)));
  const anchor=scroll>5?old.find(e=>e.getBoundingClientRect().bottom>top&&retained.has(e.dataset.searchEntry)):null;
  const offset=anchor?anchor.getBoundingClientRect().top-top:0;
  let previous=null;
  list.querySelector('.search-history-empty')?.remove();
  for(const row of data.history){
   const node=byId.get(String(row.number))||updateEntry(null,row,data,false),next=previous?previous.nextElementSibling:list.firstElementChild;
   if(node!==next)list.insertBefore(node,next);previous=node;
  }
  for(const node of old)if(!retained.has(node.dataset.searchEntry))node.remove();
  if(!data.history.length)list.innerHTML=ArenaI18n.h('<p class="search-history-empty">No earlier choices in this search.</p>');
  list.scrollTop=anchor?scroll+anchor.getBoundingClientRect().top-top-offset:scroll<=5?0:scroll;
  list.scrollLeft=left;
 }
 root.paintSearchHistory=function(g,side,search){
  const panel=$('#searchContent .search-history');if(!panel)return;
  const key=[g.attempt||g.game,side,search?.ply??''].join('/');
  if(context!==key||panel.dataset.historyContext!==key){context=key;panel.dataset.historyContext=key;loaded='';panel.querySelector('.search-history-current').replaceChildren();panel.querySelector('.search-history-list').replaceChildren();panel.querySelector('.search-history-list').scrollTop=0}
  const caption=panel.querySelector('.search-history-caption');
  if(!search){caption.textContent=ArenaI18n.t('This engine has not searched yet.');return}
  if(search.history_revision===undefined||!g.attempt){caption.textContent=ArenaI18n.t('Reopen the updated app to capture search history for new searches.');return}
  const version=key+'/'+search.history_revision+'/'+Boolean(search.complete);
  if(loaded===version||busy)return;
  if(!loaded)caption.textContent=ArenaI18n.t('Loading search history…');
  busy=true;
  api('search/'+encodeURIComponent(g.attempt)+'?side='+side).then(data=>{
   if(context!==key||panel!==$('#searchContent .search-history'))return;
   if(!data.available||data.ply!==search.ply){caption.textContent=ArenaI18n.t('Waiting for this search…');return}
   loaded=key+'/'+data.revision+'/'+Boolean(data.complete);
   caption.textContent=ArenaI18n.m`${data.changes} best-move ${data.changes===1?'change':'changes'} · newest first${data.omitted?' · '+data.omitted+ArenaI18n.t(' older entries omitted (latest ')+data.limit+ArenaI18n.t(' retained)'):''}.`;
   caption.title=caption.textContent;
   const current=panel.querySelector('.search-history-current');
   if(data.current){const node=updateEntry(current.querySelector('.search-candidate'),data.current,data,true);if(node.parentNode!==current)current.replaceChildren(node)}
   else if(!current.querySelector('.search-history-empty'))current.innerHTML=ArenaI18n.h('<p class="search-history-empty">Waiting for the first reported PV…</p>');
   updateHistory(panel.querySelector('.search-history-list'),data);
  }).catch(()=>{if(context===key)caption.textContent=ArenaI18n.t('Search history is temporarily unavailable; retrying with the next update.')}).finally(()=>{busy=false});
 };
})(typeof globalThis!=='undefined'?globalThis:this);
