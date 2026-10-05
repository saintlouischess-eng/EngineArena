'use strict';
// Only authored messages enter this catalog. Interpolated names, paths and
// engine output are inserted afterwards and are never searched for translations.
(function(root){
 const languages={en:'English',es:'Español',fr:'Français',de:'Deutsch',pt:'Português',it:'Italiano',nl:'Nederlands',pl:'Polski'};
 let locale='en',catalog={},capture=null,patterns=null;
 const messageCache=new Map();
 const htmlCache=new Map(),marker=/\uE100(\d+)\uE101/g;
 const placeholders=s=>[...s.matchAll(/\{(\d+)\}/g)].map(m=>m[1]).sort().join(',');
 const normalize=s=>s.replace(/\s+/g,' ').trim();
 const decode=s=>s.replace(/&(#x[\da-f]+|#\d+|amp|lt|gt|quot|apos|nbsp);/gi,(all,x)=>x[0]==='#'?String.fromCodePoint(parseInt(x.slice(x[1].toLowerCase()==='x'?2:1),x[1].toLowerCase()==='x'?16:10)):({amp:'&',lt:'<',gt:'>',quot:'"',apos:"'",nbsp:'\u00a0'}[x.toLowerCase()]||all));
 const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function translated(source){
  capture?.(source);
  const result=catalog[source];
  return typeof result==='string'?result:source;
 }
 function t(source,...values){return translated(source).replace(/\{(\d+)\}/g,(all,n)=>n<values.length?String(values[n]):all)}
 function m(parts,...values){return t(parts.reduce((out,p,i)=>out+(i?'{'+(i-1)+'}':'')+p,''),...values)}
 function text(source){
  const leading=source.match(/^\s*/)[0],trailing=source.match(/\s*$/)[0];
  const key=normalize(decode(source).replace(marker,(_,n)=>'{'+n+'}'));
  if(!/[A-Za-z]/.test(key))return source;
  const result=translated(key);
  if(result===key)return source;
  return leading+escape(result).replace(/\{(\d+)\}/g,(_,n)=>'\uE100'+n+'\uE101')+trailing;
 }
 function markup(source){
  // Tokenize tags with quoted attributes. Engine/user values are opaque markers
  // at this point; the original markup is preserved around translated text.
  let out='',cursor=0,skip='';
  const tags=/<!--[\s\S]*?-->|<\/?[A-Za-z!][^<>"']*(?:(?:"[^"]*"|'[^']*')[^<>"']*)*>/g;
  for(const found of source.matchAll(tags)){
   out+=skip?source.slice(cursor,found.index):text(source.slice(cursor,found.index));
   const tag=found[0],name=tag.match(/^<\/?([\w-]+)/)?.[1]?.toLowerCase();
   out+=tag.replace(/\b(title|placeholder|aria-label|aria-description|data-help)=("[^"]*"|'[^']*')/g,(all,key,value)=>key+'='+value[0]+text(value.slice(1,-1))+value[0]);
   if(/^<\//.test(tag)&&name===skip)skip='';else if(['script','style','pre','code','textarea'].includes(name)&&!/^<\//.test(tag))skip=name;
   cursor=found.index+tag.length;
  }
  return out+(skip?source.slice(cursor):text(source.slice(cursor)));
 }
 function h(parts,...values){
  if(typeof parts==='string')parts=[parts];
  if(locale==='en'&&!capture)return parts.reduce((out,p,i)=>out+(i?String(values[i-1]):'')+p,'');
  const source=parts.reduce((out,p,i)=>out+(i?'\uE100'+(i-1)+'\uE101':'')+p,'');
  let rendered=htmlCache.get(source);
  if(rendered===undefined){rendered=markup(source);if(htmlCache.size>2048)htmlCache.clear();htmlCache.set(source,rendered)}
  return rendered.replace(marker,(_,n)=>String(values[Number(n)]));
 }
 function configure(code,messages={}){
  locale=Object.hasOwn(languages,code)?code:'en';catalog=Object.create(null);
  if(messages&&typeof messages==='object'&&!Array.isArray(messages))for(const [key,value] of Object.entries(messages)){
   if(typeof value==='string'&&placeholders(value)===placeholders(key))catalog[key]=value;
  }
  htmlCache.clear();messageCache.clear();patterns=null;
  if(root.document)root.document.documentElement.lang=locale;
  return locale;
 }
 function message(value){
  if(value==null)return value;const source=String(value);
  if(locale==='en')return source;
  if(Object.hasOwn(catalog,source))return t(source);
  const status={running:'Running',paused:'Paused',pending:'Pending',completed:'Completed',interrupted:'Interrupted',failed:'Failed',timeout:'Timeout',crash:'Crash',hang:'Hang',illegal_move:'Illegal move',startup_timeout:'Startup timeout',readiness_timeout:'Readiness timeout',protocol_error:'Protocol error',original:'Original',diagnostic:'Diagnostic replay',replacement:'Replace official result'};
  if(status[source])return t(status[source]);
  if(messageCache.has(source))return messageCache.get(source);
  if(patterns===null)patterns=Object.keys(catalog).filter(s=>s.includes('{')&&/[A-Za-z]{3}/.test(s)&&!s.includes('<')).map(key=>{
   const ids=[];let cursor=0,pattern='^';
   for(const found of key.matchAll(/\{(\d+)\}/g)){
    pattern+=key.slice(cursor,found.index).replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'([\\s\\S]*?)';ids.push(Number(found[1]));cursor=found.index+found[0].length;
   }
   pattern+=key.slice(cursor).replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'$';return {key,ids,expression:new RegExp(pattern)};
  });
  let result=source;
  for(const item of patterns){const found=item.expression.exec(source);if(found){const values=[];item.ids.forEach((id,i)=>values[id]=found[i+1]);result=t(item.key,...values);break}}
  if(messageCache.size>512)messageCache.clear();messageCache.set(source,result);return result;
 }
 function fileFilter(source){return source.split('|').map((part,index)=>index%2?part:t(part)).join('|')}
 function staticRoot(node){
  // This is called once for the authored page, before live data is rendered.
  for(const el of [node,...node.querySelectorAll('*')]){
   if(el.closest('script,style,pre,code,textarea,[translate="no"]'))continue;
   for(const child of [...el.childNodes])if(child.nodeType===3){
    const original=child.nodeValue,key=normalize(original);
    if(/[A-Za-z]/.test(key))child.nodeValue=original.match(/^\s*/)[0]+translated(key)+original.match(/\s*$/)[0];
   }
   for(const key of ['title','placeholder','aria-label','aria-description','data-help'])if(el.hasAttribute(key))el.setAttribute(key,t(el.getAttribute(key)));
  }
 }
 const api={t,m,h,message,fileFilter,markup,languages,configure,staticRoot,escape,normalize,
  get locale(){return locale},capture(fn){capture=fn;htmlCache.clear()},
  number(value,options={}){return new Intl.NumberFormat(locale==='en'?'en-US':locale,options).format(value)},
  date(value,options={}){return new Intl.DateTimeFormat(locale,options).format(value)}};
 root.ArenaI18n=api;if(typeof module!=='undefined')module.exports=api;
 if(root.ARENA_LANGUAGE)configure(root.ARENA_LANGUAGE,root.ARENA_MESSAGES||{});
})(globalThis);
