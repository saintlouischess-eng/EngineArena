'use strict';
if(typeof module!=='undefined'&&!globalThis.ArenaI18n)require('./i18n.js');
// Static, bundled artwork only. Saved preferences never supply asset URLs.
const ArenaMaterials=(()=>{
 const woods={solid:{name:ArenaI18n.t('Solid color')},maple:{name:ArenaI18n.t('Maple'),color:'#ead8ae'},ash:{name:ArenaI18n.t('Ash'),color:'#ddd5be'},oak:{name:ArenaI18n.t('Golden oak'),color:'#bd915c'},walnut:{name:ArenaI18n.t('Walnut'),color:'#70503a'},rosewood:{name:ArenaI18n.t('Rosewood'),color:'#713e32'},ebony:{name:ArenaI18n.t('Ebony'),color:'#343538'}};
 const presets={plain:{name:ArenaI18n.t('Solid colors'),light:'solid',dark:'solid'},classicWood:{name:ArenaI18n.t('Maple & walnut'),light:'maple',dark:'walnut'},warmWood:{name:ArenaI18n.t('Oak & rosewood'),light:'oak',dark:'rosewood'},coolWood:{name:ArenaI18n.t('Ash & ebony'),light:'ash',dark:'ebony'}};
 const safe=value=>Object.hasOwn(woods,value)?value:'solid';
 function normalize(value){return {light:safe(value?.light),dark:safe(value?.dark)}}
 function ink(hex){const rgb=/^#[0-9a-f]{6}$/i.test(hex)?hex.slice(1).match(/../g).map(x=>parseInt(x,16)/255):[.8,.8,.8];return rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722>.57?'#332b23':'#fff4de'}
 function apply(host,value,colors){const cfg=normalize(value);for(const side of ['light','dark']){const wood=woods[cfg[side]],color=wood.color||colors?.[side]||'#dae1d6';host.style.setProperty('--board-'+side+'-texture',cfg[side]==='solid'?'none':`url("/textures/${cfg[side]}.png")`);host.style.setProperty('--board-'+side+'-ink',ink(color))}}
 return {woods,presets,normalize,apply};
})();
if(typeof module!=='undefined')module.exports=ArenaMaterials;
