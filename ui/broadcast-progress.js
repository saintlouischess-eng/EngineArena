'use strict';
const BroadcastProgress=(()=>{
 const finite=v=>typeof v==='number'&&Number.isFinite(v);
 function duration(seconds){
  if(!finite(seconds)||seconds<0)return '—';
  if(seconds<60)return '< 1m';
  const minutes=Math.ceil(seconds/60),days=Math.floor(minutes/1440),hours=Math.floor(minutes%1440/60),rest=minutes%60;
  return days?[days+'d',hours?hours+'h':''].filter(Boolean).join(' '):[hours?hours+'h':'',rest?rest+'m':''].filter(Boolean).join(' ');
 }
 function progress(data){
  const s=data.summary||{},p=s.progress||{},now=data.server_time||Date.now()/1000;
  const count=v=>Number.isFinite(Number(v))?Math.max(0,Number(v)):0;
  const completed=count(s.completed),total=count(s.total),remaining=Math.max(0,total-completed);
  const out={completed,total,remaining,percent:total?Math.min(100,completed/total*100):0,rate:null,seconds:null,eta:'Collecting pace',detail:'Estimate after more games',status:'collecting',source:null};
  const unavailable=(status,eta,detail)=>({...out,status,eta,detail});
  if(!data.connected)return unavailable('disconnected','Reconnecting','Last recorded progress');
  if(data.summary_at&&now-data.summary_at>120)return unavailable('stale','Updating progress','Waiting for a fresh snapshot');
  if(s.state==='completed')return unavailable(remaining?'ended_early':'finished',remaining?'Ended early':'Complete',remaining?'Scheduled total not reached':'All scheduled games finished');
  if(s.state==='paused'||p.status==='paused')return unavailable('paused','Paused','Estimate resumes with play');
  if(s.state==='draining'||p.status==='draining')return unavailable('draining','Draining','Finishing active games');
  if(p.status==='blocked')return unavailable('blocked','Waiting','Tournament needs attention');
  if(!total)return unavailable('waiting','Waiting for games','No schedule reported');
  if(!remaining)return unavailable(p.status==='replays'?'replays':'finishing',p.status==='replays'?'Replays in progress':'Finalizing','Official schedule complete');
  if(s.state!=='running'||p.status==='waiting')return unavailable('waiting','Waiting to play','Estimate after play resumes');
  let rate=null,seconds=null,source=null,windowMinutes=0;
   // Use a contiguous active segment only; pauses, roster/replay changes and
   // offline gaps cannot turn historical elapsed time into an active-play ETA.
   const observations=(data.observations||[]).filter(o=>finite(o.time)&&finite(o.completed)&&o.time<=now&&o.tid===data.config?.tid).slice(-720).sort((a,b)=>a.time-b.time);
   let segment=[];
   for(const o of observations){
    if(o.state!=='running'||o.total!==total||o.time<now-7200){segment=[];continue}
    const last=segment.at(-1);
    if(last&&(o.time-last.time>900||o.completed<last.completed))segment=[];
    if(!segment.length||o.time>segment.at(-1).time)segment.push(o);
   }
   const a=segment[0],b=segment.at(-1);
   const valid=a&&b&&b.time-a.time>=300&&now-b.time<=360&&b.completed<=completed&&b.completed-a.completed>=2;
   const worker=p.status==='estimated'&&finite(p.eta_seconds)&&p.eta_seconds>0&&finite(p.games_per_hour)&&p.games_per_hour>0;
   if(valid&&(!worker||b.time-a.time>=1800)){
    rate=(b.completed-a.completed)*3600/(b.time-a.time);seconds=remaining/rate*3600;source='observed';windowMinutes=Math.round((b.time-a.time)/60);
   }else if(worker){
    seconds=p.eta_seconds;rate=p.games_per_hour;source='worker';
   }
  if(!finite(seconds)||!finite(rate)||rate<=0)return out;
  return {...out,status:'estimated',seconds,rate,source,windowMinutes,eta:'≈ '+duration(seconds),detail:Math.round(rate).toLocaleString('en-US')+' games/hour · '+(windowMinutes>=30?windowMinutes+' min rolling pace':'recent pace')};
 }
 // Keep the on-air estimate steady for five minutes. Real state changes,
 // backwards counts, replay/roster changes and stale data take effect immediately.
 function stableEstimate(){
  let last=null;
  return data=>{
   const value=progress(data),now=data.server_time||Date.now()/1000,key=data.config?.tid||'';
   if(value.status!=='estimated'){last=null;return value}
   if(!last||last.key!==key||last.total!==value.total||value.completed<last.completed||now<last.time||now-last.time>=300){
    last={...value,key,time:now};return value;
   }
   return {...value,rate:last.rate,seconds:last.seconds,eta:last.eta,detail:last.detail,source:last.source};
  };
 }
 return {duration,progress,stableEstimate};
})();
if(typeof module!=='undefined')module.exports=BroadcastProgress;
