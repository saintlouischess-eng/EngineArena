const test=require('node:test'),assert=require('node:assert/strict');
const {createBroadcastTicker,broadcastTickerParts}=require('../ui/broadcast.js');
function ticker(){
 const listeners={},writes=[];
 const node={style:{setProperty(k,v){this[k]=v}},addEventListener(k,fn){listeners[k]=fn},
  ownerDocument:{createTextNode:textContent=>({textContent}),createElement:()=>({})},
  replaceChildren(...children){this.children=children;writes.push(children.map(c=>c.textContent).join(''))},
  get textContent(){return writes.at(-1)}};
 const clip={clientWidth:1516,style:{}};
 const update=createBroadcastTicker(node,clip);
 const config={ticker:true,ticker_mode:'scroll',ticker_seconds:130,ticker_size:26};
 const boundary=(target=node,animationName='wire')=>listeners.animationiteration({target,animationName});
 return {node,clip,writes,config,update,boundary};
}
test('visible ticker finishes its pass despite many new, longer or shorter results',()=>{
 const t=ticker();t.update('Original result',t.config);
 for(let i=0;i<260;i++)t.update('New result '+i+' x'.repeat(i%20),t.config);
 assert.equal(t.node.textContent,'Original result');assert.equal(t.writes.length,1);
 t.update('Latest score',t.config);t.boundary();
 assert.equal(t.node.textContent,'Latest score');assert.equal(t.writes.length,2);
 t.boundary();assert.equal(t.writes.length,2);
 assert.equal(t.node.style['--ticker-start'],'1516px');
 assert.equal(t.node.style.animationDuration,'130s');
});
test('unrelated animations cannot replace an on-screen line',()=>{
 const t=ticker();t.update('A',t.config);t.update('B',t.config);
 t.boundary({},'wire');t.boundary(t.node,'other');assert.equal(t.node.textContent,'A');
 t.boundary();assert.equal(t.node.textContent,'B');
});
test('speed changes retain the visible pass position and keep new stories queued',()=>{
 const t=ticker();t.update('Original line',t.config);
 const animation={animationName:'wire',currentTime:32500,effect:{getTiming:()=>({duration:parseFloat(t.node.style.animationDuration)*1000})}};
 t.node.getAnimations=()=>[animation];
 t.update('Queued line',{...t.config,ticker_seconds:260});
 assert.equal(animation.currentTime,65000);assert.equal(t.node.textContent,'Original line');
 t.update('Queued line',{...t.config,ticker_seconds:65});
 assert.equal(animation.currentTime,16250);assert.equal(t.node.textContent,'Original line');
 t.boundary();assert.equal(t.node.textContent,'Queued line');
});
test('headline mode remains immediate and returning to scroll queues correctly',()=>{
 const t=ticker();t.update('Scrolling',t.config);
 const headlines={...t.config,ticker_mode:'headlines'};
 t.update('Headline 1',headlines);t.update('Headline 2',headlines);
 assert.equal(t.node.textContent,'Headline 2');assert.equal(t.node.className,'headlines');
 t.update('Scroll 1',t.config);t.update('Scroll 2',t.config);
 assert.equal(t.node.textContent,'Scroll 1');t.boundary();assert.equal(t.node.textContent,'Scroll 2');
});
test('hidden ticker can refresh and resumes with the latest snapshot',()=>{
 const t=ticker();t.update('Old',t.config);
 t.update('Hidden',{...t.config,ticker:false});assert.equal(t.clip.style.visibility,'hidden');
 t.update('Current',t.config);assert.equal(t.node.textContent,'Current');
 assert.equal(t.clip.style.visibility,'visible');
 t.update('Queued',t.config);assert.equal(t.node.textContent,'Current');
});
test('ticker accents results and endings while retaining names, spaces and diamond gaps',()=>{
 const wire='Rose 1.0.1  1-0  Polaris 1.8.1 · checkmate\u2003◆\u2003Altair 7.0.0  1/2-1/2  Minic 3.0 · threefold repetition';
 const parts=broadcastTickerParts(wire);
 assert.equal(parts.map(p=>p.text).join(''),wire);
 assert.deepEqual(parts.filter(p=>p.accent).map(p=>p.text),['1-0','checkmate','1/2-1/2','threefold repetition']);
 const t=ticker();t.update(wire,t.config);
 assert.deepEqual(t.node.children.filter(c=>c.className?.startsWith('ticker-result')&&!c.className.includes('separator')).map(c=>c.textContent),['1-0','checkmate','1/2-1/2','threefold repetition']);
});
test('upset explanation and standings prose stay unaccented; names stay literal text',()=>{
 const wire='UPSET · Engine <test>  0-1  Strong Engine · resignation adjudication · winner beat an opponent rated approximately 250 Elo higher in the latest rating snapshot';
 const parts=broadcastTickerParts(wire);
 assert.equal(parts.map(p=>p.text).join(''),wire);
 assert.deepEqual(parts.filter(p=>p.accent).map(p=>p.text),['0-1','resignation adjudication']);
 assert.deepEqual(broadcastTickerParts('STANDINGS LEADER · Engine 1-0 moves to first place').filter(p=>p.accent),[]);
});
test('engine rating badges stay attached to names and preserve result accents and literal text',()=>{
 const wire='UPSET · Engine <test> (2200 Elo)  1-0  Rival 2.0 (2500 Elo) · checkmate · winner beat an opponent rated approximately 300 Elo higher in the latest rating snapshot\u2003◆\u2003New engine (Elo pending)  1/2-1/2  Old engine (0 Elo) · stalemate';
 const parts=broadcastTickerParts(wire);
 assert.equal(parts.map(p=>p.text).join(''),wire);
 assert.deepEqual(parts.filter(p=>p.kind==='rating').map(p=>p.text),['(2200 Elo)','(2500 Elo)','(Elo pending)','(0 Elo)']);
 assert.deepEqual(parts.filter(p=>p.accent).map(p=>p.text),['1-0','checkmate','1/2-1/2','stalemate']);
 const t=ticker();t.update(wire,t.config);
 const rendered=wire.replaceAll('\u2003◆\u2003','◆');
 assert.equal(t.node.textContent,rendered);
 assert.equal(t.node.children.filter(c=>c.className==='ticker-rating').length,4);
 t.update(wire.replace('2200 Elo','2300 Elo'),t.config);
 assert.equal(t.node.textContent,rendered);t.boundary();
 assert.ok(t.node.textContent.includes('(2300 Elo)'));
});
