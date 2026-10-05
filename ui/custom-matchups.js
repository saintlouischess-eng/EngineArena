'use strict';
function customMatchupSettings(){
 if($('#tformat')?.value!=='custom')return {};
 const rows=($('#customPairs')?.value||'').trim().split('\n').filter(s=>s.trim());
 const custom_matchups=rows.map(line=>{
  const v=line.trim().split(/[\s,;]+/).map(Number);
  if(v.length!==3||v.some(n=>!Number.isSafeInteger(n)||n<1))throw Error(ArenaI18n.t('Each matchup line needs three positive whole numbers: first engine, second engine, count.'));
  return {a:v[0]-1,b:v[1]-1,count:v[2]};
 });
 return {custom_matchups};
}
function installCustomMatchups(){
 $('#formatFields').insertAdjacentHTML('beforebegin',ArenaI18n.h`<div data-format="custom" id="customEditor" hidden><h3>Custom matchups</h3><p>Choose the opponent combinations and a count for each. With color reversal enabled, the count means opening pairs; otherwise it means individual games. Unpaired games alternate colors within each matchup.</p><div class="fields"><label>First engine number<input id="customA" type="number" min="1" value="1"></label><label>Second engine number<input id="customB" type="number" min="1" value="2"></label><label>Pairs / games<input id="customCount" type="number" min="1" value="10"></label></div><button type="button" id="customAdd">Add matchup</button><label>Matchups: first engine, second engine, count<textarea id="customPairs" rows="5" spellcheck="false" data-help="One opponent combination per line. You can paste a list. Reversed duplicates and self-play are rejected; increase the count to repeat a matchup."></textarea></label><details><summary>Participant numbers and names</summary><div id="customNames"></div><div class="pager"><button type="button" id="customPrev">←</button><button type="button" id="customNext">→</button></div></details><p class="caption">Use fresh opening pairs or shared opening cycles. Custom matchups do not have shared tournament rounds. Unequal opponent lists and game counts can produce different raw points rankings; head-to-head results and pool ratings help interpret them.</p></div>`);
 $('#customPairs').value=(tournamentDraft?.settings.custom_matchups||[]).map(v=>`${v.a+1} ${v.b+1} ${v.count}`).join('\n');
 let offset=0;
 const refresh=()=>$('#tname').refreshSetup?.();
 $('#customPairs').oninput=refresh;
 $('#customAdd').onclick=()=>{$('#customPairs').value+=($('#customPairs').value.trim()?'\n':'')+[$('#customA').value,$('#customB').value,$('#customCount').value].join(' ');refresh()};
 const names=async()=>{const node=$('#customNames'),rows=await api('selected-participants',{...tournamentParticipantPayload(),offset});if(node!==$('#customNames'))return;node.innerHTML=rows.map(p=>`<div>#${p.slot+1} ${esc(p.name)}</div>`).join('');$('#customPrev').disabled=!offset;$('#customNext').disabled=offset+50>=tournamentParticipantCount()};
 $('#customPrev').onclick=safely(async()=>{offset=Math.max(0,offset-50);await names()});$('#customNext').onclick=safely(async()=>{offset+=50;await names()});
 $('#customNames').closest('details').ontoggle=safely(names);
}
