const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const ArenaI18n=require('../ui/i18n.js'),ArenaFormat=require('../ui/format.js'),ArenaClocks=require('../ui/clocks.js');

function firstHealthRefresh(status){
 // A fast status response can arrive after polish.js but before review.js.
 // Run the health renderer with only the declarations available at that point.
 const source=fs.readFileSync(path.join(__dirname,'../ui/polish.js'),'utf8');
 const declarations=['backupHealth','renderWorkerHealth'].map(name=>
  source.match(new RegExp('^function '+name+'\\([^]*?^\\}', 'm'))?.[0]||'').join('\n');
 let html='';
 const context={ArenaI18n,ArenaFormat,ArenaClocks,state:{},$:()=>({}),
  fmt:ArenaFormat.number,esc:value=>String(value??''),statTile:()=>'',
  stableHtml:(selector,value)=>{assert.equal(selector,'#healthContent');html=value}};
 vm.runInNewContext(declarations+'\nrenderWorkerHealth(status);',{...context,status});
 return html;
}

test('first worker status renders before the later review script loads',()=>{
 const html=firstHealthRefresh({backup:{phase:'waiting',backup_count:2}});
 assert.match(html,/Worker connected/);
 assert.match(html,/Waiting for first recovery copy/);
 assert.doesNotMatch(html,/Verified recovery copy ready/);
});

test('backup progress and verified state remain distinct',()=>{
 const copying=firstHealthRefresh({backup:{phase:'copying',percent:42}});
 assert.match(copying,/Creating recovery copy/);
 assert.match(copying,/<progress max="100" value="42"/);
 const ready=firstHealthRefresh({backup:{phase:'ready',completed_at:1700000000,size_bytes:1024,backup_count:2,retention:2,total_bytes:2048}});
 assert.match(ready,/Verified recovery copy ready/);
 assert.match(ready,/Last verified/);
 assert.match(ready,/2 \/ 2/);
 assert.doesNotMatch(ready,/<progress/);
});

test('saving failure remains visible and absent backup data is tolerated',()=>{
 assert.match(firstHealthRefresh({error:'Disk full',backup:{phase:'error'}}),/Recovery backup needs attention/);
 assert.match(firstHealthRefresh({error:'Disk full'}),/Disk full/);
 assert.match(firstHealthRefresh({}),/Worker connected/);
});
