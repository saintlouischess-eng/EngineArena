const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(require.resolve('../ui/app.js'),'utf8');
const ctx=vm.createContext({ArenaI18n:require('../ui/i18n.js'),state:{flip:false,pieceSet:'classic'}});
vm.runInContext(source.slice(source.indexOf('function boardHtml('),source.indexOf('function clockFace(')),ctx);
const fen='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
test('coordinates include files and ranks on the correct edges in both orientations',()=>{
 for(const flip of [false,true]){
  const html=ctx.boardHtml(fen,'a1',flip),squares=[...html.matchAll(/data-square="([a-h][1-8])"[^>]*>(.*?)<\/div>/g)];
  assert.equal(squares.length,64);assert.equal((html.match(/coord-file/g)||[]).length,8);assert.equal((html.match(/coord-rank/g)||[]).length,8);
  const files=squares.filter(([,sq,content])=>content.includes('coord-file'));
  const ranks=squares.filter(([,sq,content])=>content.includes('coord-rank'));
  assert.equal(files.map(([,sq])=>sq[0]).join(''),flip?'hgfedcba':'abcdefgh');
  assert.equal(ranks.map(([,sq])=>sq[1]).join(''),flip?'12345678':'87654321');
  assert.ok(files.every(([,sq])=>sq[1]===(flip?'8':'1')));assert.ok(ranks.every(([,sq])=>sq[0]===(flip?'h':'a')));
  const corner=squares.find(([,sq])=>sq===(flip?'h8':'a1'))[2];assert.ok(corner.includes('coord-file')&&corner.includes('coord-rank'));
 }
});
