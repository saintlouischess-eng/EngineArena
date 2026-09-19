(function(root){
 'use strict';
 function duration(seconds){
  if(!Number.isFinite(seconds)||seconds<0)return '—';
  if(seconds<60)return 'less than a minute';
  const minutes=Math.ceil(seconds/60),days=Math.floor(minutes/1440),hours=Math.floor(minutes%1440/60),rest=minutes%60;
  return [days?days+'d':'',hours?hours+'h':'',rest?rest+'m':''].filter(Boolean).join(' ');
 }
 function progress(p){
  if(!p)return {percent:0,label:'0%',eta:'ETA —',detail:'Select a tournament'};
  const percent=Math.max(0,Math.min(100,Number(p.percent)||0));
  const messages={collecting:'Collecting timing data…',waiting:'Waiting for engines / queued',paused:'Paused · estimate after resuming',draining:'Pausing after active games',blocked:'Waiting for a tournament or saving issue to be resolved',finished:'Completed',ended_early:'Ended early · scheduled total shown',replays:'Official schedule complete · replays in progress',finishing:'Finalizing tournament'};
  return {percent,label:(percent<100?Math.floor(percent*10)/10:100).toLocaleString(undefined,{maximumFractionDigits:1})+'%',
   eta:p.status==='estimated'?(p.eta_seconds<60?'Less than a minute remaining':'About '+duration(p.eta_seconds)+' remaining'):messages[p.status]||'ETA —',
   detail:p.status==='estimated'?Math.round(p.games_per_hour).toLocaleString()+' games/hour · recent observed pace':p.remaining_games.toLocaleString()+' scheduled games remaining'};
 }
 const api={duration,progress};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ArenaResults=api;
})(typeof globalThis!=='undefined'?globalThis:this);
