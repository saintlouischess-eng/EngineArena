'use strict';
// Presentation only: use the existing snapshot, without requesting another fit.
function ratingDisplayControls(host,scope){
 const controls=document.createElement('div');controls.className='rating-display-controls';controls.dataset.ratingDisplay=scope;
 controls.innerHTML=ArenaI18n.h('<label>CI display<select data-rating-setting="ciMode"><option value="bounds">Full bounds</option><option value="error">Plus / minus (±)</option></select></label><label>Rating decimals<select data-rating-setting="ratingDigits"><option value="0">0</option><option value="1">1</option><option value="2">2</option></select></label><label>CI decimals<select data-rating-setting="ciDigits"><option value="0">0</option><option value="1">1</option><option value="2">2</option></select></label>');
 controls.dataset.help=ArenaI18n.t('Display only. Asymmetric intervals show separate minus and plus values; unbounded intervals keep their full bounds. Sorting and calculations use unrounded values.');
 host.append(controls);
 for(const select of controls.querySelectorAll('select')){
  const label=select.closest('label').firstChild.textContent;select.setAttribute('aria-label',label);
  select.onchange=safely(async()=>{
   const key=select.dataset.ratingSetting,value=key==='ciMode'?select.value:Number(select.value);
   displayPrefs.ratingDisplay={...displayPrefs.ratingDisplay,[scope]:{...ratingDisplayPrefs(scope),[key]:value}};
   if(scope==='standings'&&state.snapshot)renderStandings(state.snapshot);
   if(scope==='center'&&RatingDesk.data)renderRatingRows(RatingDesk.data);
   await persistDisplay();
  });
 }
}
function syncRatingDisplayControls(){
 for(const host of $$('[data-rating-display]')){const prefs=ratingDisplayPrefs(host.dataset.ratingDisplay);for(const select of host.querySelectorAll('select'))select.value=String(prefs[select.dataset.ratingSetting])}
}
ratingDisplayControls(resultControls,'standings');
const ratingCenterControls=document.createElement('div');ratingCenterControls.className='results-controls rc-display-controls';$('#rcRows').closest('.panel').querySelector('.panel-title').after(ratingCenterControls);
ratingDisplayControls(ratingCenterControls,'center');
const displayBeforeRatingControls=applyDisplay;applyDisplay=function(){displayBeforeRatingControls();syncRatingDisplayControls()};
syncRatingDisplayControls();
