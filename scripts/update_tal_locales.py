"""Offline labels for the approved Tal 1962 playing set."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
rows={
 '3D board':['Tablero 3D','Échiquier 3D','3D-Brett','Tabuleiro 3D','Scacchiera 3D','3D-bord','Szachownica 3D'],
 '3D piece set':['Piezas 3D','Jeu de pièces 3D','3D-Figurensatz','Conjunto de peças 3D','Set di pezzi 3D','3D-stukkenset','Zestaw bierek 3D'],
 '1849 Staunton':['1849 Staunton']*7,
 'Tal 1962 · Soviet Championship':['Tal 1962 · Campeonato soviético','Tal 1962 · Championnat soviétique','Tal 1962 · Sowjetische Meisterschaft','Tal 1962 · Campeonato soviético','Tal 1962 · Campionato sovietico','Tal 1962 · Sovjetkampioenschap','Tal 1962 · Mistrzostwa ZSRR'],
 'Choose the 3D pieces for both Focused Game and Player Arena.':[
  'Elija las piezas 3D para Partida enfocada y Player Arena.',
  'Choisissez les pièces 3D pour la partie suivie et Player Arena.',
  'Wählen Sie die 3D-Figuren für die fokussierte Partie und Player Arena.',
  'Escolha as peças 3D para a partida em foco e Player Arena.',
  'Scegli i pezzi 3D per la partita in primo piano e Player Arena.',
  'Kies de 3D-stukken voor de gevolgde partij en Player Arena.',
  'Wybierz bierki 3D dla obserwowanej partii i Player Arena.'
 ],
 'Red crowns apply to the 1849 Staunton set only and follow the original kingside rook and knight.':[
  'Las coronas rojas solo se aplican al juego 1849 Staunton y siguen a la torre y al caballo originales del flanco de rey.',
  'Les couronnes rouges concernent uniquement le jeu 1849 Staunton et suivent la tour et le cavalier d’origine de l’aile roi.',
  'Rote Kronen gelten nur für den Satz 1849 Staunton und folgen dem ursprünglichen Königsturm und Königsspringer.',
  'As coroas vermelhas aplicam-se apenas ao conjunto 1849 Staunton e acompanham a torre e o cavalo originais da ala do rei.',
  'Le corone rosse si applicano solo al set 1849 Staunton e seguono la torre e il cavallo originali dell’ala di re.',
  'Rode kronen gelden alleen voor de set 1849 Staunton en volgen de oorspronkelijke toren en het paard aan de koningskant.',
  'Czerwone korony dotyczą tylko zestawu 1849 Staunton i podążają za pierwotną wieżą i skoczkiem ze skrzydła królewskiego.'
 ],
}
source=ROOT/'locales/sources.json';sources=json.loads(source.read_text(encoding='utf-8'))
for index,code in enumerate(('en','es','fr','de','pt','it','nl','pl')):
 path=ROOT/'locales'/f'{code}.json';data=json.loads(path.read_text(encoding='utf-8'))
 for key,values in rows.items():data['messages'][key]=key if code=='en' else values[index-1];sources[key]=['ui/board3d-ui.js']
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
source.write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
