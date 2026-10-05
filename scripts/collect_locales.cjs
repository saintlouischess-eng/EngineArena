// Extract explicit messages; no rewriting and no execution of UI/application data.
const fs=require('node:fs'),acorn=require('internal/deps/acorn/acorn/dist/acorn'),I=require('../ui/i18n.js');
const messages=JSON.parse(fs.readFileSync('locales/sources.json','utf8'));
let file='';const add=s=>{if(/[A-Za-z]/.test(s)){messages[s]??=[];if(!messages[s].includes(file))messages[s].push(file)}};
I.capture(add);
function walk(node){
 if(node.type==='CallExpression'&&node.callee.object?.name==='ArenaI18n'&&['t','h'].includes(node.callee.property.name)&&typeof node.arguments[0]?.value==='string'){
  if(node.callee.property.name==='h')I.h(node.arguments[0].value);else add(node.arguments[0].value);
 }
 if(node.type==='TaggedTemplateExpression'&&node.tag.object?.name==='ArenaI18n'){
  const parts=node.quasi.quasis.map(q=>q.value.cooked);
  if(node.tag.property.name==='h')I.h(parts,...parts.slice(1).map((_,i)=>'\uE100'+i+'\uE101'));
  else if(node.tag.property.name==='m')add(parts.reduce((out,p,i)=>out+(i?'{'+(i-1)+'}':'')+p,''));
 }
 for(const v of Object.values(node)){if(Array.isArray(v)){for(const child of v)if(child?.type)walk(child)}else if(v?.type)walk(v)}
}
for(const name of fs.readdirSync('ui').filter(n=>n.endsWith('.js')&&n!=='i18n.js'&&!n.startsWith('three'))){file='ui/'+name;walk(acorn.parse(fs.readFileSync(file,'utf8'),{ecmaVersion:'latest',sourceType:['board3d-studio.js','board3d-crowns.js'].includes(name)?'module':'script'}))}
file='ui/index.html';I.h(fs.readFileSync(file,'utf8'));I.capture(null);
fs.writeFileSync('locales/sources.json',JSON.stringify(messages,null,2)+'\n');console.log(Object.keys(messages).length+' catalog messages');
