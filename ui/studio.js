'use strict';
// One-time chrome only. No observers, timers, or work on the live telemetry path.
(() => {
 const paths={
  overview:'M4 3h16v7H4zM4 14h7v7H4zM15 14h5v7h-5z',
  tournamentQueue:'M4 5h11M4 12h11M4 19h7M18 14l4 3-4 3z',
  events:'M8 3h8v6a4 4 0 0 1-8 0zM8 5H4v3a4 4 0 0 0 4 4m8-7h4v3a4 4 0 0 1-4 4M12 13v6m-4 2h8',
  engines:'M6 6h12v12H6zM9 9h6v6H9zM9 2v4m6-4v4M9 18v4m6-4v4M2 9h4m-4 6h4M18 9h4m-4 6h4',
  presets:'M14 3H10M12 8v5l3 2M19 5l-2 2M20 13a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z',
  experiments:'M9 3h6M10 3v6L4 19a1.3 1.3 0 0 0 1 2h14a1.3 1.3 0 0 0 1-2L14 9V3M7 15h10',
  health:'M3 12h4l3-8 4 16 3-8h4',
  display:'M3 4h18v13H3zM8 21h8M12 17v4M8 4v13',
  language:'M3 5h12M9 3v2M6 5c0 7 6 10 6 10M12 5c0 7-7 11-9 11M13 21l4-10 4 10m-6-4h4',
  theme:'M20 15a8 8 0 0 1-11-11A8 8 0 1 0 20 15Z',
  graph:'M4 3v17h17M8 15l4-6 4 3 5-8'
 };
 const icon=name=>{const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('class','studio-icon');svg.setAttribute('aria-hidden','true');svg.setAttribute('focusable','false');const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',paths[name]);svg.append(path);return svg};
 document.querySelectorAll('aside .nav').forEach(button=>{
  if(!paths[button.dataset.view])return;
  [...button.childNodes].filter(n=>n.nodeType===Node.TEXT_NODE).forEach(n=>n.remove());
  button.prepend(icon(button.dataset.view));
 });
 // The labels and click handlers remain the same in every language.
 const theme=document.getElementById('theme');
 if(theme){theme.textContent=theme.textContent.replace(/^◐\s*/, '');theme.prepend(icon('theme'))}
 const display=displayButton;
 if(display)display.prepend(icon('display'));
 const graph=document.getElementById('addGraph');
 if(graph){graph.textContent=graph.textContent.replace(/^＋\s*/, '');graph.prepend(icon('graph'))}
 const language=document.getElementById('languageButton');
 if(language)language.prepend(icon('language'));
 const empty=document.querySelector('#empty>span');
 if(empty){empty.replaceChildren();const img=document.createElement('img');img.src='/assets/engine-arena.svg';img.alt='';img.width=88;img.height=88;empty.append(img)}
})();
