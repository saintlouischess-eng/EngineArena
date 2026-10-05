(function(root){
 if(!root.ArenaI18n&&typeof require==='function')require('./i18n.js');
 'use strict';
 function duration(seconds){
  if(!Number.isFinite(seconds)||seconds<0)return '—';
  if(seconds<60)return ArenaI18n.t('less than a minute');
  const minutes=Math.ceil(seconds/60),days=Math.floor(minutes/1440),hours=Math.floor(minutes%1440/60),rest=minutes%60;
  return [days?days+'d':'',hours?hours+'h':'',rest?rest+'m':''].filter(Boolean).join(' ');
 }
 function progress(p){
  if(!p)return {percent:0,label:'0%',eta:ArenaI18n.t('ETA —'),detail:ArenaI18n.t('Select a tournament')};
  const percent=Math.max(0,Math.min(100,Number(p.percent)||0));
  const messages={collecting:ArenaI18n.t('Collecting timing data…'),waiting:ArenaI18n.t('Waiting for engines / queued'),paused:ArenaI18n.t('Paused · estimate after resuming'),draining:ArenaI18n.t('Pausing after active games'),blocked:ArenaI18n.t('Waiting for a tournament or saving issue to be resolved'),finished:ArenaI18n.t('Completed'),ended_early:ArenaI18n.t('Ended early · scheduled total shown'),replays:ArenaI18n.t('Official schedule complete · replays in progress'),finishing:ArenaI18n.t('Finalizing tournament')};
  return {percent,label:(percent<100?Math.floor(percent*10)/10:100).toLocaleString(ArenaI18n.locale,{maximumFractionDigits:1})+'%',
   eta:p.status==='estimated'?(p.eta_seconds<60?ArenaI18n.t('Less than a minute remaining'):ArenaI18n.t('About ')+duration(p.eta_seconds)+ArenaI18n.t(' remaining')):messages[p.status]||ArenaI18n.t('ETA —'),
   detail:p.status==='estimated'?Math.round(p.games_per_hour).toLocaleString(ArenaI18n.locale)+ArenaI18n.t(' games/hour · recent observed pace'):p.remaining_games.toLocaleString(ArenaI18n.locale)+ArenaI18n.t(' scheduled games remaining')};
 }
 const api={duration,progress};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ArenaResults=api;
})(typeof globalThis!=='undefined'?globalThis:this);
