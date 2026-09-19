'use strict';
// Reusable conditions are copied into a tournament at creation. Editing the
// library never changes an existing tournament or any recorded attempt.
loadPresets=async function(){
  state.presets=await api('presets');
  $('#presetList').innerHTML=state.presets.map((p,i)=>`<article class="preset"><h3>${esc(p.name)}</h3><p>${esc(tcText(p.settings.time_control))}<br>${p.settings.threads} thread(s) · ${p.settings.hash} MB hash<br>${p.settings.paired?'Paired openings':'Single games'} · Ponder ${p.settings.ponder?'ON':'OFF'}</p><button data-edit-preset="${i}">Edit</button> <button data-copy-preset="${i}">Save a copy</button></article>`).join('');
  $$('[data-edit-preset]').forEach(b=>b.onclick=()=>editPreset(state.presets[Number(b.dataset.editPreset)]));
  $$('[data-copy-preset]').forEach(b=>b.onclick=()=>editPreset(state.presets[Number(b.dataset.copyPreset)],true));
};
function editPreset(p=null,copy=false){
  const s=p?.settings||{threads:1,hash:1024,paired:true,ponder:false};
  modal(copy?'Copy test conditions':p?'Edit test conditions':'New test conditions',`${field('presetName','Preset name',p?p.name+(copy?' (copy)':''):'My control')}${tcEditor('ptc',s.time_control)}<div class="fields">${field('pThreads','Threads per engine',s.threads,'number','min="1" step="1"')}${field('pHash','Hash per engine (MB)',s.hash,'number','min="1" step="1"')}<label><input id="pPaired" type="checkbox" ${s.paired?'checked':''}> Paired openings</label><label><input id="pPonder" type="checkbox" ${s.ponder?'checked':''}> Enable pondering</label></div><p class="caption">Existing tournaments retain their recorded conditions. A different name saves another preset and keeps the original.</p>`,`<button class="primary" id="saveP">Save preset</button>`);
  wireTc('ptc');$('#saveP').onclick=safely(async()=>{
    await api('presets',{name:$('#presetName').value,original_name:p&&!copy?p.name:null,settings:{...s,time_control:readTc('ptc'),threads:Number($('#pThreads').value),hash:Number($('#pHash').value),paired:$('#pPaired').checked,ponder:$('#pPonder').checked}});
    $('#modal').close();await loadPresets();notify('Test conditions saved.');
  });
}
$('#savePreset').textContent='＋ New preset';$('#savePreset').onclick=()=>editPreset();
$('#presets').insertAdjacentHTML('beforeend',`<div class="panel position-library"><div class="panel-title"><h2>Starting positions</h2><button id="newPosition">＋ Set up a position</button></div><div id="positionList"></div><p class="caption">Place pieces on the board or paste a FEN. Saved positions can be selected when creating a tournament.</p></div>`);
const loadConditionsPresets=loadPresets;
loadPresets=async function(){await loadConditionsPresets();await loadPositions();};
async function loadPositions(){
  const items=await api('positions');
  $('#positionList').innerHTML=items.length?items.map((p,i)=>`<article class="preset"><h3>${esc(p.name)}</h3><p>${p.chess960?'Chess960':'Standard chess'}</p><code>${esc(p.fen)}</code><div class="position-actions"><button data-edit-position="${i}">Edit position</button><button data-export-position="${i}">Export FEN</button></div></article>`).join(''):'<p class="caption">No saved positions yet.</p>';
  $$('[data-edit-position]').forEach(b=>b.onclick=()=>editPosition(items[Number(b.dataset.editPosition)]));
  $$('[data-export-position]').forEach(b=>b.onclick=()=>download('starting-position.fen',items[Number(b.dataset.exportPosition)].fen+'\n','text/plain'));
}
$('#newPosition').onclick=()=>editPosition();
function editPosition(saved=null){
  const initial='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
  let cells=[],piece='P',flip=false,revision=0,timer;
  modal('Set up a starting position',`<div class="position-editor"><div><div id="setupBoard"></div><div class="toolbar position-actions"><button id="setupFlip">Flip board</button><button id="setupInitial">Initial position</button><button id="setupClear">Clear board</button></div><div id="piecePalette" class="piece-palette">${'KQRBNPkqrbnp'.split('').map(p=>`<button type="button" data-place-piece="${p}" aria-label="Place ${p===p.toUpperCase()?'White':'Black'} ${{K:'king',Q:'queen',R:'rook',B:'bishop',N:'knight',P:'pawn'}[p.toUpperCase()]}"><img alt="" src="/pieces/${state.pieceSet||'classic'}/${p===p.toUpperCase()?'w':'b'}${p.toUpperCase()}.svg"></button>`).join('')}<button data-place-piece="" class="erase-piece">Erase</button></div><p class="caption">Choose a piece, then click a square. Right-click to erase. Squares also support Tab and Enter.</p></div><div>${field('positionName','Position name',saved?.name||'My starting position')}<label class="setup-fen">FEN<textarea id="positionFen" rows="3" spellcheck="false"></textarea></label><div class="fields"><label>Side to move<select id="setupTurn"><option value="w">White</option><option value="b">Black</option></select></label>${field('setupCastle','Castling rights (KQkq or rook files for Chess960)','KQkq')}${field('setupEp','En-passant square (or -)','-')}${field('setupHalf','Halfmove clock',0,'number','min="0" step="1"')}${field('setupFull','Fullmove number',1,'number','min="1" step="1"')}<label><input type="checkbox" id="setup960" ${saved?.chess960?'checked':''}> Chess960 rules</label></div><div class="position-actions">${field('setup960Index','Chess960 start (0–959)',518,'number','min="0" max="959" step="1"')}<button id="setupGenerate">Generate start</button></div><p id="positionValidation" role="status"></p></div></div>`,`<button id="savePosition" class="primary" disabled>Save position</button>`);
  const fenNode=$('#positionFen'),statusNode=$('#positionValidation'),saveNode=$('#savePosition');
  const alive=()=>$('#positionFen')===fenNode&&$('#modal').open;
  const validate=async()=>{
    const current=++revision;saveNode.disabled=true;statusNode.textContent='Checking position…';
    try{const p=await api('position-preview',{fen:fenNode.value,chess960:$('#setup960').checked});
      if(current!==revision||!alive())return;
      statusNode.textContent=p.valid?`Valid position · ${p.legal_moves.length} legal moves${p.check?' · in check':''}`:p.errors.join(' · ');
      statusNode.className=p.valid?'position-valid':'pairing-error';saveNode.disabled=!p.valid;
    }catch(e){if(current===revision&&alive()){statusNode.textContent=e.message;statusNode.className='pairing-error';}}
  };
  const schedule=()=>{++revision;clearTimeout(timer);saveNode.disabled=true;timer=setTimeout(()=>{if(alive())validate();},160);};
  const placement=()=>Array.from({length:8},(_,r)=>{let row='',empty=0;for(const p of cells.slice(r*8,r*8+8)){if(!p)empty++;else{if(empty)row+=empty;empty=0;row+=p;}}return row+(empty||'');}).join('/');
  const write=()=>{fenNode.value=`${placement()} ${$('#setupTurn').value} ${$('#setupCastle').value.trim()||'-'} ${$('#setupEp').value.trim()||'-'} ${$('#setupHalf').value} ${$('#setupFull').value}`;draw();schedule();};
  const draw=()=>{
    $('#setupBoard').innerHTML=boardHtml(placement(),'',flip);
    $$('#setupBoard [data-square]').forEach(el=>{
      const index=(8-Number(el.dataset.square[1]))*8+'abcdefgh'.indexOf(el.dataset.square[0]);
      el.setAttribute('role','button');el.tabIndex=0;el.setAttribute('aria-label',`${el.dataset.square}, ${el.querySelector('img')?.alt||'empty'}`);
      const put=p=>{cells[index]=p;write();$('#setupBoard [data-square="'+el.dataset.square+'"]').focus({preventScroll:true});};
      el.onclick=()=>put(piece);el.oncontextmenu=e=>{e.preventDefault();put('');};el.onkeydown=e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();put(piece);}};
    });
  };
  const read=()=>{
    try{
      const parts=fenNode.value.trim().split(/\s+/),rows=parts[0].split('/'),next=[];
      if(rows.length!==8)throw Error('FEN needs eight ranks.');
      for(const row of rows){const start=next.length;for(const c of row){if(/[1-8]/.test(c))next.push(...Array(Number(c)).fill(''));else if(/[KQRBNPkqrbnp]/.test(c))next.push(c);else throw Error('Invalid FEN piece.');}if(next.length-start!==8)throw Error('Each FEN rank needs eight squares.');}
      cells=next;$('#setupTurn').value=parts[1]||'w';$('#setupCastle').value=parts[2]||'-';$('#setupEp').value=parts[3]||'-';$('#setupHalf').value=parts[4]??0;$('#setupFull').value=parts[5]??1;draw();schedule();
    }catch(e){++revision;clearTimeout(timer);saveNode.disabled=true;statusNode.textContent=e.message;statusNode.className='pairing-error';}
  };
  fenNode.value=saved?.fen||initial;fenNode.oninput=read;
  $$('#piecePalette button').forEach(b=>b.onclick=()=>{piece=b.dataset.placePiece;$$('#piecePalette button').forEach(x=>x.classList.toggle('primary',x===b));});
  $('#piecePalette [data-place-piece="P"]').classList.add('primary');
  ['setupTurn','setupCastle','setupEp','setupHalf','setupFull','setup960'].forEach(id=>$('#'+id).onchange=write);
  $('#setupFlip').onclick=()=>{flip=!flip;draw();};
  $('#setupInitial').onclick=()=>{$('#setup960').checked=false;fenNode.value=initial;read();};
  $('#setupClear').onclick=()=>{fenNode.value='8/8/8/8/8/8/8/8 w - - 0 1';read();};
  $('#setupGenerate').onclick=safely(async()=>{
    const current=++revision;clearTimeout(timer);saveNode.disabled=true;
    const p=await api('position-preview',{chess960_index:Number($('#setup960Index').value)});
    if(current!==revision||!alive())return;$('#setup960').checked=true;fenNode.value=p.fen;read();
  });
  saveNode.onclick=safely(async()=>{
    await api('positions',{name:$('#positionName').value,fen:fenNode.value,chess960:$('#setup960').checked,original_name:saved?.name||null});
    ++revision;clearTimeout(timer);$('#modal').close();await loadPositions();notify('Starting position saved. Existing tournaments keep their recorded opening.');
  });
  read();
}
function startingPositionPayload(){
  const source=$('#topeningSource')?.value||'initial';
  return {saved_position:source==='saved'?$('#tsavedPosition').value:null,opening_file:source==='file'?$('#topening').value:'',all960:source==='all960'};
}
const tournamentBeforeConditions=newTournament;
newTournament=async function(){
  await tournamentBeforeConditions();const node=$('#tname');const positions=await api('positions');if($('#tname')!==node||!$('#modal').open)return;
  const openings=$('#topening').closest('.fields');
  openings.insertAdjacentHTML('beforebegin',`<div class="fields opening-selection"><label>Starting position source<select id="topeningSource"><option value="initial">Standard initial position</option><option value="file">Opening file or Polyglot book</option><option value="saved" ${positions.length?'':'disabled'}>Saved starting position</option><option value="all960">All 960 Chess960 starts</option></select></label><label id="savedPositionField" hidden>Saved position<select id="tsavedPosition">${positions.map(p=>`<option value="${esc(p.name)}">${esc(p.name)} · ${p.chess960?'Chess960':'Standard'}</option>`).join('')}</select></label><label id="file960Field" hidden><input id="tfile960" type="checkbox"> Opening file uses Chess960 rules</label></div>`);
  $('#t960').closest('label').hidden=true;
  const sourceChanged=()=>{const s=$('#topeningSource').value;$('#savedPositionField').hidden=s!=='saved';$('#file960Field').hidden=s!=='file';$('#topening').closest('.field').hidden=s!=='file';$('#tdepth').closest('.field').hidden=s!=='file';};
  $('#topeningSource').onchange=sourceChanged;sourceChanged();
  const presetChanged=$('#tpreset').onchange;$('#tpreset').onchange=()=>{const key=$('#tpreset').value;if(key!=='')$('#tponder').checked=state.presets[Number(key)].settings.ponder;return presetChanged?.();};
};
$('#newTournament').onclick=safely(newTournament);
