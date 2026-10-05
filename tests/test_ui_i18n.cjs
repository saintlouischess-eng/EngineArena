const test=require('node:test'),assert=require('node:assert/strict');
const I=require('../ui/i18n.js');
test('catalog formatting preserves opaque names, paths and markup',()=>{
 I.configure('es',{'Game {0}':'Partida {0}','White':'Blancas','Move {1}':'Jugada {1}','Open game':'Abrir partida'});
 assert.equal(I.m`Game ${'White {9} <script>'}`,'Partida White {9} <script>');
 const result=I.h`<button data-id="${'White'}" title="Move ${4}">Open game</button><b>${'White &lt;engine&gt;'}</b>`;
 assert.equal(result,'<button data-id="White" title="Jugada 4">Abrir partida</button><b>White &lt;engine&gt;</b>');
 I.configure('en');
});
test('missing keys and invalid placeholders fall back without losing values',()=>{
 I.configure('fr',{'Game {0}':'Partie {1}','White':'<Blancs> & "x"'});
 assert.equal(I.t('Game {0}',5),'Game 5');
 assert.equal(I.h`<b>White</b>`,'<b>&lt;Blancs&gt; &amp; &quot;x&quot;</b>');
 assert.equal(I.h`<code>White</code><style>b { color: red }</style>`,'<code>White</code><style>b { color: red }</style>');
 assert.equal(I.configure('../../private',{}),'en');
});
test('switching language invalidates cached templates and uses regional numbers',()=>{
 I.configure('de',{'White':'Weiß'});assert.equal(I.h`<b>White</b>`,'<b>Weiß</b>');
 assert.equal(I.number(1234.5,{minimumFractionDigits:1}),'1.234,5');
 I.configure('pl',{'White':'Białe'});assert.equal(I.h`<b>White</b>`,'<b>Białe</b>');
 I.configure('en');assert.equal(I.h`<b>White</b>`,'<b>White</b>');
});
test('application errors translate placeholders while engine values stay exact',()=>{
 I.configure('es',{'Engine {0} is unavailable':'El motor {0} no está disponible','Paused':'En pausa'});
 assert.equal(I.message('Engine Draw is unavailable'),'El motor Draw no está disponible');
 assert.equal(I.message('paused'),'En pausa');
 assert.equal(I.message('info depth 20 pv e2e4'),'info depth 20 pv e2e4');
 I.configure('en');
});
