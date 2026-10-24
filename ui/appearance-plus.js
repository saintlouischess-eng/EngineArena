'use strict';
const arenaThemes={dark:['Midnight',false],light:['Daylight',true],charcoal:['Charcoal',false],blue:['Deep Blue',false],forest:['Forest',false],parchment:['Warm Parchment',true],contrast:['High Contrast',false]};
const themeMedia=matchMedia('(prefers-color-scheme: dark)');
function effectiveTheme(){return displayPrefs.themeSystem?(themeMedia.matches?'dark':'light'):(arenaThemes[displayPrefs.theme]?displayPrefs.theme:'dark')}
function applyThemePlus(){const theme=effectiveTheme();document.body.dataset.arenaTheme=theme;document.body.classList.toggle('light',arenaThemes[theme][1]);document.body.dataset.accent=['teal','blue','amber','rose'].includes(displayPrefs.accent)?displayPrefs.accent:'teal'}
themeMedia.addEventListener('change',()=>{if(displayPrefs.themeSystem)applyDisplay()});
function themeFields(){return ArenaI18n.h`<div class="theme-gallery">${Object.entries(arenaThemes).map(([key,[name]])=>`<button type="button" class="theme-swatch" data-theme-choice="${key}" aria-pressed="${key===displayPrefs.theme}"><span class="theme-sample theme-${key}"><b>Aa</b><i></i><i></i></span>${esc(ArenaI18n.t(name))}</button>`).join('')}</div><div class="fields"><label>Accent<select id="themeAccent">${['teal','blue','amber','rose'].map(k=>`<option value="${k}" ${displayPrefs.accent===k?'selected':''}>${ArenaI18n.t(k[0].toUpperCase()+k.slice(1))}</option>`).join('')}</select></label><label><input id="themeSystem" type="checkbox" ${displayPrefs.themeSystem?'checked':''}> Follow Windows light/dark appearance</label></div><p class="caption">Interface colors are independent of chessboard finishes, pieces and 3D rooms.</p><div id="themePreview" class="theme-preview"><h3>Live standings</h3><p>Engine profile · Games · Rating</p><button class="primary">Selected control</button><span class="caption">Secondary text</span></div><button type="button" id="resetTheme">Reset theme</button>`}
function wireThemeFields(){
 const preview=()=>{const key=$('#displayTheme').value;$('#themePreview').className='theme-preview theme-'+key;$$('[data-theme-choice]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.themeChoice===key)))};
 $$('[data-theme-choice]').forEach(b=>b.onclick=()=>{$('#displayTheme').value=b.dataset.themeChoice;$('#themeSystem').checked=false;preview()});$('#displayTheme').addEventListener('change',preview);
 $('#resetTheme').onclick=()=>{$('#displayTheme').value='dark';$('#themeAccent').value='teal';$('#themeSystem').checked=false;preview()};preview();
}
function themeOptions(){return Object.entries(arenaThemes).map(([key,[name]])=>`<option value="${key}" ${key===displayPrefs.theme?'selected':''}>${esc(ArenaI18n.t(name))}</option>`).join('')}
function saveThemeFields(){displayPrefs.accent=$('#themeAccent').value;displayPrefs.themeSystem=$('#themeSystem').checked;displayPrefs.theme=$('#displayTheme').value}
function themeDialog(){
 modal(ArenaI18n.t('Interface themes'),`<label>${ArenaI18n.t('Theme')}<select id="displayTheme">${themeOptions()}</select></label>${themeFields()}`,ArenaI18n.h('<button id="applyTheme" class="primary">Apply theme</button>'));
 wireThemeFields();$('#applyTheme').onclick=safely(async()=>{saveThemeFields();applyDisplay();await persistDisplay();$('#modal').close()});
}
$('#theme').onclick=themeDialog;$('#theme').textContent=ArenaI18n.t('Interface themes…');
const displayDialogBeforeThemes=displayDialog;displayDialog=async function(...args){await displayDialogBeforeThemes(...args);const select=$('#displayTheme');if(!select)return;select.innerHTML=themeOptions();select.closest('.fields').after(Object.assign(document.createElement('section'),{className:'appearance-themes',innerHTML:themeFields()}));wireThemeFields();const apply=$('#applyDisplay').onclick;$('#applyDisplay').onclick=async e=>{saveThemeFields();await apply(e)}};displayButton.onclick=safely(displayDialog);

function textSize(host,key,heading){
 if(!host||!heading)return;
 host.dataset.textPanel=key;
 if(!host.querySelector(`[data-text-control="${key}"]`)){
  const label=document.createElement('label');label.className='panel-text-size';label.dataset.textControl=key;label.innerHTML=`${ArenaI18n.t('Text')} <input type="number" min="11" max="28" step="1" aria-label="${esc(ArenaI18n.t('Panel text size'))}"><button type="button" class="subtle">${ArenaI18n.t('Reset')}</button>`;heading.append(label);
  label.querySelector('input').onchange=e=>{if(!e.target.reportValidity())return;displayPrefs.textSizes={...displayPrefs.textSizes,[key]:Number(e.target.value)};applyTextSizes();saveDisplay()};
  label.querySelector('button').onclick=()=>{if(displayPrefs.textSizes)delete displayPrefs.textSizes[key];applyTextSizes();saveDisplay()};
 }
 applyTextSize(host,key);
}
function applyTextSize(host,key){const value=Math.max(11,Math.min(28,Number(displayPrefs.textSizes?.[key])||14));host.style.setProperty('--panel-text-size',value+'px');document.querySelectorAll(`[data-text-control="${key}"] input`).forEach(el=>{if(el!==document.activeElement)el.value=value});for(const frame of host.querySelectorAll('iframe')){if(frame.srcdoc&&frame.dataset.fontSize!==String(value)){const doc=new DOMParser().parseFromString(frame.srcdoc,'text/html');let style=doc.querySelector('#panelFontOverride');if(!style){style=doc.createElement('style');style.id='panelFontOverride';doc.head.append(style)}style.textContent=`body,table{font-size:${value}px!important}`;frame.dataset.fontSize=String(value);frame.srcdoc='<!doctype html>'+doc.documentElement.outerHTML}}}

function applyTextSizes(){$$('[data-text-panel]').forEach(host=>applyTextSize(host,host.dataset.textPanel))}
for(const key of ['standings','games'])textSize(panels[key],key,panels[key].querySelector('.panel-title'));
textSize($('#engineTable').closest('.panel'),'engines',$('#engineTable').closest('.panel').querySelector('.panel-title'));
textSize($('#rcRows').closest('.panel'),'ratings',$('#rcRows').closest('.panel').querySelector('.panel-title'));
const modalBeforeTextSize=modal;modal=function(...args){modalBeforeTextSize(...args);const root=$('#modal .modal-body');const key=$('#crossGrid')?'crosstable':$('#poolRatingRows')||$('#anchorSearch')?'pool-ratings':$('#reportLoading')?'report':root?.querySelector('table')?'details':null;if(key)textSize(root,key,$('#modal .modal-head'));else if(root){delete root.dataset.textPanel;root.style.removeProperty('--panel-text-size')}};
const eventBeforeTextSize=showEvent;showEvent=async function(...args){await eventBeforeTextSize(...args);const host=$('#eventInsights');if(host)textSize(host,'events',host.querySelector('.si-toolbar')||host)};
const displayBeforeThemes=applyDisplay;applyDisplay=function(){applyThemePlus();displayBeforeThemes();applyThemePlus();applyTextSizes()};
applyThemePlus();applyTextSizes();
