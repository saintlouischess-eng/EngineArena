const test=require('node:test');
const assert=require('node:assert/strict');
const materials=require('../ui/board-materials.js');

test('old or malformed saved finishes fall back to solid and never become URLs',()=>{
 assert.deepEqual(materials.normalize(),{light:'solid',dark:'solid'});
 assert.deepEqual(materials.normalize({light:'../../private',dark:'__proto__'}),{light:'solid',dark:'solid'});
 assert.deepEqual(materials.normalize({light:'maple',dark:'rosewood'}),{light:'maple',dark:'rosewood'});
});
test('independent finishes reset images and keep readable coordinates on dark squares',()=>{
 const styles={};const host={style:{setProperty:(k,v)=>styles[k]=v}};
 materials.apply(host,{light:'maple',dark:'ebony'},{light:'#ffffff',dark:'#000000'});
 assert.equal(styles['--board-light-texture'],'url("/textures/maple.png")');
 assert.equal(styles['--board-dark-texture'],'url("/textures/ebony.png")');
 assert.notEqual(styles['--board-light-ink'],styles['--board-dark-ink']);
 materials.apply(host,{light:'solid',dark:'solid'},{light:'#ffffff',dark:'#000000'});
 assert.equal(styles['--board-light-texture'],'none');assert.equal(styles['--board-dark-texture'],'none');
 assert.notEqual(styles['--board-light-ink'],styles['--board-dark-ink']);
});
