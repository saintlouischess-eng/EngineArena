"""Offline translations for the optional animated chess rooms."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ROWS="""Live environment|Entorno animado|Décor animé|Lebendige Umgebung|Ambiente animado|Ambiente animato|Levendige omgeving|Żywe otoczenie
Bring the room to life|Dar vida a la sala|Animer la pièce|Raum beleben|Dar vida ao ambiente|Anima la stanza|Breng de ruimte tot leven|Ożyw pomieszczenie
Players & spectators|Jugadores y espectadores|Joueurs et spectateurs|Spieler und Zuschauer|Jogadores e espectadores|Giocatori e spettatori|Spelers en toeschouwers|Gracze i widzowie
Background chess games|Partidas de fondo|Parties en arrière-plan|Schachpartien im Hintergrund|Partidas ao fundo|Partite sullo sfondo|Partijen op de achtergrond|Partie w tle
Subtle room movement|Movimiento ambiental sutil|Mouvements discrets du décor|Dezente Bewegung im Raum|Movimento ambiente sutil|Movimenti ambientali discreti|Subtiele beweging in de ruimte|Subtelny ruch otoczenia
Distant chess sounds|Sonidos de ajedrez lejanos|Sons d’échecs lointains|Entfernte Schachgeräusche|Sons distantes de xadrez|Suoni degli scacchi in lontananza|Schaakgeluiden op afstand|Odległe odgłosy szachów
Room activity|Actividad de la sala|Activité de la pièce|Raumaktivität|Atividade do ambiente|Attività nella stanza|Activiteit in de ruimte|Aktywność w pomieszczeniu
Quiet session|Sesión tranquila|Séance calme|Ruhige Sitzung|Sessão tranquila|Sessione tranquilla|Rustige sessie|Spokojna sesja
Club session|Sesión del club|Séance de club|Vereinsabend|Sessão do clube|Sessione del circolo|Clubsessie|Spotkanie klubowe
Busy chess evening|Velada de ajedrez animada|Soirée d’échecs animée|Belebter Schachabend|Noite de xadrez movimentada|Serata di scacchi animata|Drukke schaakavond|Tętniący życiem wieczór szachowy
Choose how many background tables have players. Your game remains the focus.|Elija cuántas mesas de fondo tienen jugadores. Su partida sigue siendo el centro de atención.|Choisissez combien de tables du décor accueillent des joueurs. Votre partie reste au premier plan.|Wählen Sie, wie viele Tische im Hintergrund besetzt sind. Ihre Partie bleibt im Mittelpunkt.|Escolha quantas mesas ao fundo têm jogadores. Sua partida continua em destaque.|Scegli quanti tavoli sullo sfondo hanno giocatori. La tua partita rimane al centro dell’attenzione.|Kies hoeveel tafels op de achtergrond bezet zijn. Je eigen partij blijft centraal staan.|Wybierz, przy ilu stolikach w tle siedzą gracze. Twoja partia pozostaje najważniejsza.
Room sound volume (%)|Volumen ambiental (%)|Volume du décor (%)|Lautstärke im Raum (%)|Volume do ambiente (%)|Volume dell’ambiente (%)|Volume ruimtegeluid (%)|Głośność otoczenia (%)
Optional scenery for both 3D boards. Background games are decorative and do not affect results. Sound is off by default. Animation pauses when the board is hidden.|Decoración opcional para ambos tableros 3D. Las partidas de fondo son decorativas y no afectan a los resultados. El sonido está desactivado por defecto. La animación se pausa si se oculta el tablero.|Décor facultatif pour les deux échiquiers 3D. Les parties en arrière-plan sont décoratives et ne modifient pas les résultats. Le son est désactivé par défaut. L’animation s’arrête lorsque l’échiquier est masqué.|Optionale Kulisse für beide 3D-Bretter. Hintergrundpartien sind dekorativ und beeinflussen keine Ergebnisse. Der Ton ist standardmäßig aus. Bei ausgeblendetem Brett pausiert die Animation.|Cenário opcional para ambos os tabuleiros 3D. As partidas ao fundo são decorativas e não afetam os resultados. O som fica desativado por padrão. A animação pausa quando o tabuleiro está oculto.|Scenario facoltativo per entrambe le scacchiere 3D. Le partite sullo sfondo sono decorative e non influenzano i risultati. L’audio è disattivato per impostazione predefinita. L’animazione si ferma quando la scacchiera è nascosta.|Optioneel decor voor beide 3D-borden. Achtergrondpartijen zijn decoratief en beïnvloeden geen uitslagen. Geluid staat standaard uit. Animatie pauzeert als het bord verborgen is.|Opcjonalna sceneria obu szachownic 3D. Partie w tle są dekoracyjne i nie wpływają na wyniki. Dźwięk jest domyślnie wyłączony. Animacja zatrzymuje się po ukryciu szachownicy."""
sources=json.loads((ROOT/'locales/sources.json').read_text(encoding='utf-8'))
rows=[line.split('|') for line in ROWS.splitlines()]
assert all(len(row)==8 for row in rows)
for row in rows:sources.setdefault(row[0],['ui/board3d-presentation.js'])
for i,lang in enumerate(('en','es','fr','de','pt','it','nl','pl')):
    path=ROOT/'locales'/f'{lang}.json';data=json.loads(path.read_text(encoding='utf-8'))
    for row in rows:data['messages'][row[0]]=row[i]
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'locales/sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Live environment translated in eight languages.')
