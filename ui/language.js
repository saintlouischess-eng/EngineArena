'use strict';
const languageButton=document.createElement('button');languageButton.id='languageButton';languageButton.className='subtle';
languageButton.textContent=ArenaI18n.t('Language')+' · '+ArenaI18n.languages[ArenaI18n.locale];
languageButton.dataset.help=ArenaI18n.t('Choose the interface language. Games keep running while the interface reloads.');
displayButton.after(languageButton);
languageButton.onclick=()=>{
 modal(ArenaI18n.t('Language'),ArenaI18n.h`<label for="languageChoice">Interface language</label><select id="languageChoice">${Object.entries(ArenaI18n.languages).map(([code,name])=>`<option value="${code}" ${code===ArenaI18n.locale?'selected':''}>${name}</option>`).join('')}</select><p class="caption">Translations are included with the app and work offline. Engine names, UCI commands, PGN notation, and recorded diagnostic output retain their original values.</p><p class="caption">Apply reloads the interface. Running tournaments continue in the worker.</p><p class="caption">These are initial translations. Feedback from native speakers is welcome, particularly for chess terminology.</p>`,ArenaI18n.h`<button id="applyLanguage" class="primary">Apply language</button>`);
 $('#applyLanguage').onclick=safely(async()=>{
  const code=$('#languageChoice').value;
  displayPrefs.language=code;await persistDisplay();
  if(state.tid)sessionStorage.setItem('arenaLanguageTournament',state.tid);
  window.chrome?.webview?.postMessage({type:'language',language:code});
  const next=new URL(location.href);next.searchParams.set('lang',code);location.replace(next.href);
 });
};
