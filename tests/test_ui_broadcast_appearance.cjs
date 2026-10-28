const test=require('node:test'),assert=require('node:assert/strict');
const {broadcastAppearance}=require('../ui/broadcast.js');
test('wood choices use bundled grain, keep light squares independent and clear old textures',()=>{
 const vars=broadcastAppearance({board_light:'ash',board_dark:'rosewood',dark_lighten:28});
 assert.equal(vars['--board-light-image'],'url("/assets/textures/ash.png")');
 assert.equal(vars['--board-dark-image'],'url("/assets/textures/rosewood.png")');
 assert.equal(vars['--board-light-color'],'#ddd5be');assert.equal(vars['--board-dark-color'],'#713e32');
 assert.equal(vars['--board-dark-wash'],'linear-gradient(rgba(239,216,184,0.28),rgba(239,216,184,0.28))');
 const reset=broadcastAppearance({});assert.equal(reset['--board-light-image'],'none');assert.equal(reset['--board-dark-image'],'none');
 assert.equal(reset['--board-light-color'],'var(--light)');
});
test('invalid texture paths cannot become asset URLs and coordinate ink follows brightness',()=>{
 const bad=broadcastAppearance({board_light:'../../secret',board_dark:'url(https://evil.invalid)',dark_lighten:Infinity});
 assert.equal(bad['--board-light-image'],'none');assert.equal(bad['--board-dark-image'],'none');
 const reversed=broadcastAppearance({board_light:'ebony',board_dark:'ash',dark_lighten:60});
 assert.equal(reversed['--board-light-ink'],'#fff4de');assert.equal(reversed['--board-dark-ink'],'#332b23');
});
