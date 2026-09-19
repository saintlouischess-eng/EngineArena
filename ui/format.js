'use strict';
(function(root){
 const number=(value,digits=1)=>{
  if(value===null||value===undefined||Number.isNaN(value))return '—';
  if(value==='+infinity'||value===Infinity)return '+∞';
  if(value==='-infinity'||value===-Infinity)return '−∞';
  if(typeof value!=='number')return String(value);
  return (Math.abs(value)<.5*10**(-digits)?0:value).toLocaleString(undefined,{minimumFractionDigits:digits,maximumFractionDigits:digits});
 };
 const percent=value=>{
  if(value===null||value===undefined||!Number.isFinite(value))return '—';
  if(value>0&&value<.05)return '<0.1%';
  if(value<100&&value>99.95)return '>99.9%';
  return number(value)+'%';
 };
 const uncertainty=(value,method='normal')=>{
  if(value.model?.startsWith('Self-play'))return 'Self-play does not estimate strength between engines.';
  const samples=value.pairs??value.games;
  if(!samples)return value.pairs===0?'Waiting for a completed opening pair.':'No official results yet.';
  if(method==='normal'&&value.ci==null)return 'Normal uncertainty and LOS need at least two samples with varied scores. Conservative bounds remain available.';
  return `${samples.toLocaleString()} ${value.pairs==null?'individual games':'completed opening pairs'} in this estimate. Elo is relative to the sampled opposition.`;
 };
 const bytes=value=>{
  if(!Number.isFinite(value)||value<0)return '—';
  const units=['B','KiB','MiB','GiB','TiB'];let unit=0;
  while(value>=1024&&unit<units.length-1){value/=1024;unit++}
  return number(value,unit===0?0:2)+' '+units[unit];
 };
 const api={number,percent,uncertainty,bytes};root.ArenaFormat=api;
 if(typeof module!=='undefined')module.exports=api;
})(globalThis);
