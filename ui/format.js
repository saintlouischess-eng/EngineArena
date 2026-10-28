'use strict';
(function(root){
 if(!root.ArenaI18n&&typeof require==='function')require('./i18n.js');
 const number=(value,digits=1)=>{
  if(value===null||value===undefined||Number.isNaN(value))return '—';
  if(value==='+infinity'||value===Infinity)return '+∞';
  if(value==='-infinity'||value===-Infinity)return '−∞';
  if(typeof value!=='number')return String(value);
  return (Math.abs(value)<.5*10**(-digits)?0:value).toLocaleString(ArenaI18n.locale==='en'?'en-US':ArenaI18n.locale,{minimumFractionDigits:digits,maximumFractionDigits:digits});
 };
 const percent=value=>{
  if(value===null||value===undefined||!Number.isFinite(value))return '—';
  if(value>0&&value<.05)return '<0.1%';
  if(value<100&&value>99.95)return '>99.9%';
  return number(value)+'%';
 };
 const los=value=>value===null||value===undefined||!Number.isFinite(value)?'—':value<=.05?'<0.1%':value>=99.95?'>99.9%':number(value)+'%';
 const ratingDisplay=value=>({
  ciMode:value?.ciMode==='error'?'error':'bounds',
  ratingDigits:[0,1,2].includes(value?.ratingDigits)?value.ratingDigits:1,
  ciDigits:[0,1,2].includes(value?.ciDigits)?value.ciDigits:1
 });
 const interval=(bounds,center,mode='bounds',digits=1)=>{
  const valid=v=>typeof v==='number'&&!Number.isNaN(v)||v==='+infinity'||v==='-infinity';
  if(!Array.isArray(bounds)||bounds.length!==2||!bounds.every(valid))return '—';
  const [low,high]=bounds,full=()=>bounds.map(v=>number(v,digits)).join(' – ');
  // Unbounded or unavailable centers cannot define meaningful error offsets.
  if(mode!=='error'||!Number.isFinite(center)||!Number.isFinite(low)||!Number.isFinite(high)||low>center||high<center)return full();
  const lower=number(center-low,digits),upper=number(high-center,digits);
  // Do not replace an asymmetric interval with a fabricated symmetric one.
  return lower===upper?'±'+upper:'−'+lower+' / +'+upper;
 };
 const uncertainty=(value,method='normal')=>{
  if(value.model?.startsWith('Self-play'))return ArenaI18n.t('Self-play does not estimate strength between engines.');
  const samples=value.pairs??value.games;
  if(!samples)return value.pairs===0?ArenaI18n.t('Waiting for a completed opening pair.'):ArenaI18n.t('No official results yet.');
  if(method==='normal'&&value.ci==null)return ArenaI18n.t('Normal uncertainty and LOS need at least two samples with varied scores. Conservative bounds remain available.');
  return ArenaI18n.m`${samples.toLocaleString(ArenaI18n.locale)} ${value.pairs==null?ArenaI18n.t('individual games'):ArenaI18n.t('completed opening pairs')} in this estimate. Elo is relative to the sampled opposition.`;
 };
 const bytes=value=>{
  if(!Number.isFinite(value)||value<0)return '—';
  const units=['B','KiB','MiB','GiB','TiB'];let unit=0;
  while(value>=1024&&unit<units.length-1){value/=1024;unit++}
  return number(value,unit===0?0:2)+' '+units[unit];
 };
 const resourceOption=(options,name)=>{
  const names=name.toLowerCase()==='threads'?['threads','number of threads','maxthreads','max cpus']:[name.toLowerCase()];
  return names.map(n=>Object.keys(options||{}).find(k=>k.toLowerCase()===n)).find(Boolean);
 };
 const api={number,percent,los,uncertainty,bytes,resourceOption,ratingDisplay,interval};root.ArenaFormat=api;
 if(typeof module!=='undefined')module.exports=api;
})(globalThis);
