const test=require('node:test'),assert=require('node:assert/strict');
const {duration,progress}=require('../ui/results-model.js');
test('ETA duration labels minutes, hours and days without negative values',()=>{
 assert.equal(duration(30),'less than a minute');assert.equal(duration(3600),'1h');assert.equal(duration(90061),'1d 1h 2m');assert.equal(duration(null),'—');
});
test('percentage never rounds an unfinished schedule up to 100%',()=>{
 const p=progress({percent:99.999,remaining_games:1,status:'collecting'});assert.equal(p.label,'99.9%');assert.equal(p.percent,99.999);
});
test('paused, ended-early and replay progress have truthful distinct labels',()=>{
 const p=status=>progress({percent:50,remaining_games:50,status});
 assert.match(p('paused').eta,/Paused/);assert.match(p('ended_early').eta,/Ended early/);assert.match(p('replays').eta,/replays/);
});
