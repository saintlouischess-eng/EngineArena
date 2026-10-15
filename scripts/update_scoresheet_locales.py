"""Offline translations for continuous game-move history navigation."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
rows={
 'Beginning':['Inicio','Début','Anfang','Início','Inizio','Begin','Początek'],
 'Browsing history':['Consultando el historial','Consultation de l’historique','Verlauf ansehen','Consultando o histórico','Consultazione della cronologia','Geschiedenis bekijken','Przeglądanie historii'],
 'Showing moves {0}–{1}':['Mostrando jugadas {0}–{1}','Coups affichés : {0}–{1}','Angezeigte Züge: {0}–{1}','Mostrando lances {0}–{1}','Mosse visualizzate: {0}–{1}','Getoonde zetten: {0}–{1}','Wyświetlane ruchy: {0}–{1}'],
 'Show the opening and earliest recorded moves. Home also returns to the beginning.':[
  'Mostrar la apertura y las primeras jugadas registradas. La tecla Inicio también vuelve al principio.',
  'Afficher l’ouverture et les premiers coups enregistrés. La touche Début revient aussi au début.',
  'Eröffnung und erste aufgezeichnete Züge anzeigen. Pos1 springt ebenfalls zum Anfang.',
  'Mostrar a abertura e os primeiros lances registrados. A tecla Home também volta ao início.',
  'Mostra l’apertura e le prime mosse registrate. Anche il tasto Home torna all’inizio.',
  'Toon de opening en de eerste vastgelegde zetten. Home gaat ook terug naar het begin.',
  'Pokaż debiut i pierwsze zapisane ruchy. Klawisz Home również wraca do początku.'
 ],
 'Scroll up for earlier moves and down for later moves. Your reading position stays in place while games continue.':[
  'Desplácese hacia arriba para ver jugadas anteriores y hacia abajo para ver las siguientes. La vista permanece en su lugar mientras continúan las partidas.',
  'Faites défiler vers le haut pour les coups précédents et vers le bas pour les suivants. Votre position de lecture reste en place pendant que les parties continuent.',
  'Für frühere Züge nach oben und für spätere nach unten scrollen. Die Leseposition bleibt während laufender Partien erhalten.',
  'Role para cima para ver lances anteriores e para baixo para ver os seguintes. Sua posição de leitura permanece no lugar enquanto as partidas continuam.',
  'Scorri verso l’alto per le mosse precedenti e verso il basso per quelle successive. La posizione di lettura resta ferma mentre le partite continuano.',
  'Scrol omhoog voor eerdere zetten en omlaag voor latere zetten. Uw leespositie blijft behouden terwijl de partijen doorgaan.',
  'Przewiń w górę, aby zobaczyć wcześniejsze ruchy, lub w dół, aby zobaczyć późniejsze. Pozycja czytania pozostaje bez zmian podczas dalszej gry.'
 ],
}
path=ROOT/'locales/sources.json';sources=json.loads(path.read_text(encoding='utf-8'))
for index,code in enumerate(('en','es','fr','de','pt','it','nl','pl')):
 file=ROOT/'locales'/f'{code}.json';catalog=json.loads(file.read_text(encoding='utf-8'))
 for key,values in rows.items():
  catalog['messages'][key]=key if code=='en' else values[index-1]
  sources.setdefault(key,[])
  if 'ui/game-moves.js' not in sources[key]:sources[key].append('ui/game-moves.js')
 file.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path.write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
