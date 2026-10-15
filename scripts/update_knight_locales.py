"""Offline wording for the saved 3D knight-facing controls."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
rows={
 'Knight direction':['Dirección de los caballos','Orientation des cavaliers','Blickrichtung der Springer','Direção dos cavalos','Orientamento dei cavalli','Richting van de paarden','Kierunek skoczków'],
 'Toward the king':['Hacia el rey','Vers le roi','Zum König','Em direção ao rei','Verso il re','Naar de koning','W stronę króla'],
 'Away from the king':['En sentido opuesto al rey','À l’opposé du roi','Vom König weg','Para longe do rei','Lontano dal re','Van de koning af','Od króla'],
 'Forward':['Hacia delante','Vers l’avant','Vorwärts','Para a frente','In avanti','Vooruit','Do przodu'],
 'Backward':['Hacia atrás','Vers l’arrière','Rückwärts','Para trás','Indietro','Achteruit','Do tyłu'],
 'Left':['Izquierda','Gauche','Links','Esquerda','Sinistra','Links','W lewo'],
 'Right':['Derecha','Droite','Rechts','Direita','Destra','Rechts','W prawo'],
 "Choose how the 3D knights face. Left and right are from each player's side.":[
  'Elija la orientación de los caballos 3D. Izquierda y derecha se entienden desde el lado de cada jugador.',
  'Choisissez l’orientation des cavaliers 3D. La gauche et la droite sont vues du côté de chaque joueur.',
  'Wählen Sie die Blickrichtung der 3D-Springer. Links und rechts gelten aus der Sicht des jeweiligen Spielers.',
  'Escolha a orientação dos cavalos 3D. Esquerda e direita são vistas do lado de cada jogador.',
  'Scegli l’orientamento dei cavalli 3D. Sinistra e destra sono dal punto di vista di ciascun giocatore.',
  'Kies de richting van de 3D-paarden. Links en rechts worden bekeken vanaf de kant van elke speler.',
  'Wybierz kierunek skoczków 3D. Lewo i prawo są określane z perspektywy każdego gracza.'
 ],
 "Toward or away from the king uses each knight's starting side and stays fixed as it moves. Promoted knights and positions without verified starting history face forward.":[
  'Hacia el rey o en sentido opuesto se basa en el lado inicial de cada caballo y no cambia al moverse. Los caballos promocionados y las posiciones sin historial inicial verificado miran hacia delante.',
  'Vers le roi ou à l’opposé se base sur le côté initial de chaque cavalier et reste fixe lors des déplacements. Les cavaliers promus et les positions sans historique initial vérifié sont orientés vers l’avant.',
  'Zum König oder vom König weg richtet sich nach der Ausgangsseite des Springers und bleibt beim Ziehen gleich. Umgewandelte Springer und Stellungen ohne bestätigte Ausgangshistorie blicken vorwärts.',
  'Em direção ao rei ou para longe dele usa o lado inicial de cada cavalo e permanece fixo durante os lances. Cavalos promovidos e posições sem histórico inicial verificado ficam voltados para a frente.',
  'Verso il re o lontano dal re usa il lato iniziale di ogni cavallo e resta fisso durante le mosse. I cavalli promossi e le posizioni senza cronologia iniziale verificata sono rivolti in avanti.',
  'Naar de koning of ervan af gebruikt de beginzijde van elk paard en blijft gelijk tijdens het bewegen. Gepromoveerde paarden en stellingen zonder geverifieerde beginhistorie kijken vooruit.',
  'W stronę króla lub od króla zależy od początkowej strony skoczka i nie zmienia się podczas ruchów. Skoczki powstałe z promocji oraz pozycje bez zweryfikowanej historii początkowej są skierowane do przodu.'
 ],
}
sources_path=ROOT/'locales/sources.json';sources=json.loads(sources_path.read_text(encoding='utf-8'))
for index,code in enumerate(('en','es','fr','de','pt','it','nl','pl')):
 path=ROOT/'locales'/f'{code}.json';data=json.loads(path.read_text(encoding='utf-8'))
 for key,values in rows.items():
  data['messages'][key]=key if code=='en' else values[index-1]
  sources.setdefault(key,[])
  if 'ui/board3d-ui.js' not in sources[key]:sources[key].append('ui/board3d-ui.js')
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
sources_path.write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
