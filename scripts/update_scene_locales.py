"""Maintain the eight-language 3D presentation controls, including dynamic labels."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ROWS='''Board design|Diseño del tablero|Modèle d’échiquier|Brettdesign|Modelo de tabuleiro|Modello di scacchiera|Bordontwerp|Wzór szachownicy
Original Engine Arena|Engine Arena original|Engine Arena original|Engine Arena Original|Engine Arena original|Engine Arena originale|Origineel Engine Arena|Oryginalna Engine Arena
Walnut & maple · Drueke|Nogal y arce · Drueke|Noyer et érable · Drueke|Nussbaum und Ahorn · Drueke|Nogueira e bordo · Drueke|Noce e acero · Drueke|Walnoot en esdoorn · Drueke|Orzech i klon · Drueke
Purpleheart & maple · Jaques|Amaranto y arce · Jaques|Amarante et érable · Jaques|Amaranth und Ahorn · Jaques|Amaranto e bordo · Jaques|Amaranto e acero · Jaques|Amarant en esdoorn · Jaques|Amarant i klon · Jaques
Board coordinates|Coordenadas del tablero|Coordonnées de l’échiquier|Brettkoordinaten|Coordenadas do tabuleiro|Coordinate della scacchiera|Bordcoördinaten|Współrzędne szachownicy
Choose the board independently of the room and table. The two wood reproductions follow the reference boards with 2.5-inch squares.|Elija el tablero por separado de la sala y la mesa. Las dos reproducciones de madera siguen los tableros de referencia con casillas de 2,5 pulgadas.|Choisissez l’échiquier indépendamment de la pièce et de la table. Les deux reproductions en bois suivent les modèles de référence à cases de 2,5 pouces.|Wählen Sie das Brett unabhängig von Raum und Tisch. Die beiden Holzreproduktionen folgen den Vorlagen mit 2,5-Zoll-Feldern.|Escolha o tabuleiro independentemente do ambiente e da mesa. As duas reproduções em madeira seguem os modelos de referência com casas de 2,5 polegadas.|Scegli la scacchiera indipendentemente dalla stanza e dal tavolo. Le due riproduzioni in legno seguono i modelli di riferimento con case da 2,5 pollici.|Kies het bord onafhankelijk van de ruimte en tafel. De twee houten reproducties volgen de referentieborden met velden van 2,5 inch.|Wybierz szachownicę niezależnie od pomieszczenia i stołu. Dwie drewniane reprodukcje wzorują się na szachownicach z polami o boku 2,5 cala.
Room rotation (degrees)|Rotación de la sala (grados)|Rotation de la pièce (degrés)|Raumdrehung (Grad)|Rotação do ambiente (graus)|Rotazione della stanza (gradi)|Rotatie van de ruimte (graden)|Obrót pomieszczenia (stopnie)
Room view|Vista de la sala|Vue de la pièce|Raumansicht|Vista do ambiente|Vista della stanza|Ruimteweergave|Widok pomieszczenia
Piece close-up|Primer plano de las piezas|Gros plan des pièces|Figurennahaufnahme|Close das peças|Primo piano dei pezzi|Close-up van de stukken|Zbliżenie figur
Cinematic tour|Recorrido cinematográfico|Parcours cinématographique|Filmische Kamerafahrt|Passeio cinematográfico|Percorso cinematografico|Cinematische rondgang|Filmowy objazd
Tour speed (%)|Velocidad del recorrido (%)|Vitesse du parcours (%)|Geschwindigkeit der Kamerafahrt (%)|Velocidade do passeio (%)|Velocità del percorso (%)|Snelheid rondgang (%)|Prędkość objazdu (%)
Natural wood|Madera natural|Bois naturel|Naturholz|Madeira natural|Legno naturale|Natuurlijk hout|Naturalne drewno
Room assets could not load. The board remains available.|No se pudieron cargar los recursos de la sala. El tablero sigue disponible.|Impossible de charger le décor. L’échiquier reste disponible.|Die Raumdaten konnten nicht geladen werden. Das Brett bleibt verfügbar.|Não foi possível carregar o ambiente. O tabuleiro continua disponível.|Impossibile caricare l’ambiente. La scacchiera resta disponibile.|De ruimte kon niet worden geladen. Het bord blijft beschikbaar.|Nie udało się załadować pomieszczenia. Szachownica pozostaje dostępna.
Setting & lighting|Entorno e iluminación|Décor et éclairage|Umgebung und Beleuchtung|Ambiente e iluminação|Ambiente e illuminazione|Omgeving en verlichting|Otoczenie i oświetlenie
Environment|Entorno|Décor|Umgebung|Ambiente|Ambiente|Omgeving|Otoczenie
Chess club|Club de ajedrez|Club d’échecs|Schachclub|Clube de xadrez|Circolo di scacchi|Schaakclub|Klub szachowy
Championship hall|Sala de campeonato|Salle de championnat|Meisterschaftssaal|Salão de campeonato|Sala del campionato|Kampioenschapszaal|Sala mistrzostw
Daylight study|Estudio con luz natural|Bureau en lumière naturelle|Arbeitszimmer bei Tageslicht|Escritório com luz natural|Studio con luce naturale|Studeerkamer bij daglicht|Gabinet w świetle dziennym
Studio|Estudio|Studio|Studio|Estúdio|Studio|Studio|Studio
Table surface|Superficie de la mesa|Surface de la table|Tischoberfläche|Superfície da mesa|Superficie del tavolo|Tafelblad|Powierzchnia stołu
Walnut|Nogal|Noyer|Nussbaum|Nogueira|Noce|Walnoot|Orzech
Green felt|Fieltro verde|Feutre vert|Grüner Filz|Feltro verde|Feltro verde|Groen vilt|Zielony filc
Leather|Cuero|Cuir|Leder|Couro|Pelle|Leer|Skóra
Lighting|Iluminación|Éclairage|Beleuchtung|Iluminação|Illuminazione|Verlichting|Oświetlenie
Daylight|Luz natural|Lumière naturelle|Tageslicht|Luz natural|Luce naturale|Daglicht|Światło dzienne
Warm evening|Atardecer cálido|Soirée chaleureuse|Warmer Abend|Entardecer acolhedor|Sera calda|Warme avond|Ciepły wieczór
Tournament|Torneo|Tournoi|Turnier|Torneio|Torneo|Toernooi|Turniej
Brightness (%)|Brillo (%)|Luminosité (%)|Helligkeit (%)|Brilho (%)|Luminosità (%)|Helderheid (%)|Jasność (%)
Warmth (−100 to 100)|Calidez (−100 a 100)|Chaleur (−100 à 100)|Wärme (−100 bis 100)|Calor (−100 a 100)|Calore (−100 a 100)|Warmte (−100 tot 100)|Ciepło (−100 do 100)
Move highlight (%)|Resaltado de jugada (%)|Surbrillance du coup (%)|Zughervorhebung (%)|Destaque da jogada (%)|Evidenza della mossa (%)|Zetmarkering (%)|Podświetlenie ruchu (%)
Motion & performance|Movimiento y rendimiento|Mouvement et performances|Bewegung und Leistung|Movimento e desempenho|Movimento e prestazioni|Beweging en prestaties|Ruch i wydajność
Viewing mode|Modo de visualización|Mode d’affichage|Ansichtsmodus|Modo de visualização|Modalità di visualizzazione|Weergavemodus|Tryb wyświetlania
Testing · render when needed|Pruebas · renderizar cuando sea necesario|Tests · rendu à la demande|Testen · bei Bedarf rendern|Testes · renderizar quando necessário|Test · rendering su richiesta|Testen · renderen wanneer nodig|Testy · renderowanie w razie potrzeby
Presentation · camera tour|Presentación · recorrido de cámara|Présentation · parcours de caméra|Präsentation · Kamerafahrt|Apresentação · passeio da câmera|Presentazione · percorso della camera|Presentatie · camerarondgang|Prezentacja · objazd kamery
Piece movement|Movimiento de piezas|Mouvement des pièces|Figurenbewegung|Movimento das peças|Movimento dei pezzi|Stukbeweging|Ruch figur
Instant|Instantáneo|Instantané|Sofort|Instantâneo|Istantaneo|Direct|Natychmiastowy
Quick|Rápido|Rapide|Schnell|Rápido|Rapido|Snel|Szybki
Smooth|Suave|Fluide|Sanft|Suave|Fluido|Vloeiend|Płynny
Camera tour|Recorrido de cámara|Parcours de caméra|Kamerafahrt|Passeio da câmera|Percorso della camera|Camerarondgang|Objazd kamery
Slow orbit|Órbita lenta|Orbite lente|Langsame Umkreisung|Órbita lenta|Orbita lenta|Langzame omloop|Powolny obrót
Saved views|Vistas guardadas|Vues enregistrées|Gespeicherte Ansichten|Vistas salvas|Viste salvate|Opgeslagen weergaven|Zapisane widoki
Animation limit|Límite de animación|Limite d’animation|Animationslimit|Limite de animação|Limite animazione|Animatielimiet|Limit animacji
Graphics quality|Calidad gráfica|Qualité graphique|Grafikqualität|Qualidade gráfica|Qualità grafica|Grafische kwaliteit|Jakość grafiki
Economy|Económica|Économique|Sparsam|Econômica|Economica|Zuinig|Oszczędna
Balanced|Equilibrada|Équilibrée|Ausgewogen|Equilibrada|Bilanciata|Gebalanceerd|Zrównoważona
High|Alta|Élevée|Hoch|Alta|Alta|Hoog|Wysoka
Table details|Detalles de la mesa|Détails de la table|Tischdetails|Detalhes da mesa|Dettagli del tavolo|Tafeldetails|Szczegóły stołu
Captured-piece trays|Bandejas de piezas capturadas|Plateaux des pièces capturées|Ablagen für geschlagene Figuren|Bandejas de peças capturadas|Vassoi dei pezzi catturati|Bakjes voor geslagen stukken|Tacki na zbite figury
Engine nameplates|Placas con nombres de motores|Plaques des moteurs|Namensschilder der Engines|Placas com nomes dos motores|Targhette dei motori|Naambordjes van engines|Tabliczki z nazwami silników
Engine Arena plaque|Placa de Engine Arena|Plaque Engine Arena|Engine-Arena-Plakette|Placa Engine Arena|Targa Engine Arena|Engine Arena-plaatje|Tabliczka Engine Arena
Camera views|Vistas de cámara|Vues de caméra|Kameraansichten|Vistas da câmera|Viste della camera|Cameraweergaven|Widoki kamery
Saved camera|Cámara guardada|Caméra enregistrée|Gespeicherte Kamera|Câmera salva|Camera salvata|Opgeslagen camera|Zapisana kamera
View {0}|Vista {0}|Vue {0}|Ansicht {0}|Vista {0}|Vista {0}|Weergave {0}|Widok {0}
Save current view|Guardar vista actual|Enregistrer la vue actuelle|Aktuelle Ansicht speichern|Salvar vista atual|Salva vista attuale|Huidige weergave opslaan|Zapisz bieżący widok
Load view|Cargar vista|Charger la vue|Ansicht laden|Carregar vista|Carica vista|Weergave laden|Wczytaj widok
View saved. Apply to keep changes.|Vista guardada. Aplique para conservar los cambios.|Vue enregistrée. Appliquez pour conserver les modifications.|Ansicht gespeichert. Zum Behalten Änderungen übernehmen.|Vista salva. Aplique para manter as alterações.|Vista salvata. Applica per mantenere le modifiche.|Weergave opgeslagen. Pas toe om wijzigingen te behouden.|Widok zapisany. Zastosuj, aby zachować zmiany.
This view has not been saved yet.|Esta vista aún no se ha guardado.|Cette vue n’a pas encore été enregistrée.|Diese Ansicht wurde noch nicht gespeichert.|Esta vista ainda não foi salva.|Questa vista non è ancora stata salvata.|Deze weergave is nog niet opgeslagen.|Ten widok nie został jeszcze zapisany.
Open a game in 3D before taking a photo.|Abra una partida en 3D antes de tomar una foto.|Ouvrez une partie en 3D avant de prendre une photo.|Vor dem Fotografieren eine Partie in 3D öffnen.|Abra uma partida em 3D antes de tirar uma foto.|Apri una partita in 3D prima di scattare una foto.|Open een partij in 3D voordat u een foto maakt.|Przed zrobieniem zdjęcia otwórz partię w 3D.
Board photo|Foto del tablero|Photo de l’échiquier|Schachbrettfoto|Foto do tabuleiro|Foto della scacchiera|Bordfoto|Zdjęcie szachownicy
Board photo preview|Vista previa de la foto|Aperçu de la photo|Fotovorschau|Prévia da foto|Anteprima della foto|Fotovoorbeeld|Podgląd zdjęcia
Camera view|Vista de cámara|Vue de caméra|Kameraansicht|Vista da câmera|Vista della camera|Cameraweergave|Widok kamery
Current view|Vista actual|Vue actuelle|Aktuelle Ansicht|Vista atual|Vista attuale|Huidige weergave|Bieżący widok
White’s seat|Lado de las blancas|Côté des blancs|Sicht von Weiß|Lado das brancas|Lato del Bianco|Kant van wit|Strona białych
Black’s seat|Lado de las negras|Côté des noirs|Sicht von Schwarz|Lado das pretas|Lato del Nero|Kant van zwart|Strona czarnych
Overhead|Desde arriba|Vue du dessus|Von oben|Vista superior|Dall’alto|Van boven|Z góry
Broadcast|Retransmisión|Diffusion|Übertragung|Transmissão|Trasmissione|Uitzending|Transmisja
Background blur|Desenfoque del fondo|Flou d’arrière-plan|Hintergrundunschärfe|Desfoque do fundo|Sfocatura dello sfondo|Achtergrondvervaging|Rozmycie tła
Subtle|Sutil|Discret|Dezent|Sutil|Leggero|Subtiel|Delikatne
Soft|Suave|Doux|Sanft|Suave|Morbido|Zacht|Miękkie
Save 4K PNG…|Guardar PNG 4K…|Enregistrer le PNG 4K…|4K-PNG speichern…|Salvar PNG 4K…|Salva PNG 4K…|4K-PNG opslaan…|Zapisz PNG 4K…
Rendering 4K image…|Renderizando imagen 4K…|Rendu de l’image 4K…|4K-Bild wird gerendert…|Renderizando imagem 4K…|Rendering dell’immagine 4K…|4K-afbeelding renderen…|Renderowanie obrazu 4K…
Image saved.|Imagen guardada.|Image enregistrée.|Bild gespeichert.|Imagem salva.|Immagine salvata.|Afbeelding opgeslagen.|Obraz zapisany.
Save canceled.|Guardado cancelado.|Enregistrement annulé.|Speichern abgebrochen.|Salvamento cancelado.|Salvataggio annullato.|Opslaan geannuleerd.|Zapis anulowany.
Image ready for download.|Imagen lista para descargar.|Image prête à télécharger.|Bild zum Herunterladen bereit.|Imagem pronta para download.|Immagine pronta da scaricare.|Afbeelding klaar om te downloaden.|Obraz gotowy do pobrania.
Photo…|Foto…|Photo…|Foto…|Foto…|Foto…|Foto…|Zdjęcie…
Export the focused 3D board as a 4K picture.|Exportar el tablero 3D enfocado como imagen 4K.|Exporter l’échiquier 3D suivi en image 4K.|Das fokussierte 3D-Brett als 4K-Bild exportieren.|Exportar o tabuleiro 3D em foco como imagem 4K.|Esporta la scacchiera 3D in primo piano come immagine 4K.|Exporteer het actieve 3D-bord als 4K-afbeelding.|Eksportuj aktywną szachownicę 3D jako obraz 4K.
Choose the surroundings for your board.|Elija el entorno del tablero.|Choisissez le décor de votre échiquier.|Umgebung für das Brett wählen.|Escolha o ambiente do tabuleiro.|Scegli l’ambiente della scacchiera.|Kies de omgeving van uw bord.|Wybierz otoczenie szachownicy.
Choose the table surface.|Elija la superficie de la mesa.|Choisissez la surface de la table.|Tischoberfläche wählen.|Escolha a superfície da mesa.|Scegli la superficie del tavolo.|Kies het tafelblad.|Wybierz powierzchnię stołu.
Soft lighting presets preserve the carved details.|Los ajustes de luz suave conservan los detalles tallados.|Les éclairages doux préservent les détails sculptés.|Weiche Lichtvorlagen erhalten geschnitzte Details.|A iluminação suave preserva os detalhes esculpidos.|La luce morbida preserva i dettagli scolpiti.|Zachte verlichting houdt uitgesneden details zichtbaar.|Miękkie oświetlenie zachowuje rzeźbione szczegóły.
Testing keeps the camera still. Presentation moves it continuously while visible.|Pruebas mantiene la cámara fija. Presentación la mueve mientras sea visible.|Tests garde la caméra fixe. Présentation la déplace tant qu’elle est visible.|Testen hält die Kamera still. Präsentation bewegt sie, solange sie sichtbar ist.|Testes mantém a câmera parada. Apresentação a move enquanto visível.|Test mantiene ferma la camera. Presentazione la muove finché è visibile.|Testen houdt de camera stil. Presentatie beweegt deze zolang het bord zichtbaar is.|Testy utrzymują kamerę nieruchomo. Prezentacja porusza nią, gdy jest widoczna.
Animate only consecutive moves. Switching games and jumping through history stays instant.|Solo se animan jugadas consecutivas. Cambiar de partida o saltar por el historial es instantáneo.|Seuls les coups consécutifs sont animés. Changer de partie ou sauter dans l’historique reste instantané.|Nur aufeinanderfolgende Züge animieren. Partie- und Verlaufssprünge bleiben sofortig.|Apenas jogadas consecutivas são animadas. Trocar de partida ou saltar no histórico é instantâneo.|Anima solo mosse consecutive. Cambiare partita o saltare nella cronologia resta istantaneo.|Alleen opeenvolgende zetten animeren. Partijwissels en sprongen in de geschiedenis blijven direct.|Animowane są tylko kolejne ruchy. Zmiana partii i przeskoki w historii pozostają natychmiastowe.
Dragging, scrolling or using camera keys stops the tour.|Arrastrar, desplazar o usar teclas de cámara detiene el recorrido.|Glisser, défiler ou utiliser les touches de caméra arrête le parcours.|Ziehen, Scrollen oder Kameratasten stoppen die Fahrt.|Arrastar, rolar ou usar teclas da câmera interrompe o passeio.|Trascinare, scorrere o usare i tasti della camera ferma il percorso.|Slepen, scrollen of cameratoetsen stoppen de rondgang.|Przeciąganie, przewijanie lub klawisze kamery zatrzymują objazd.
Limit animation work. Hidden boards stop rendering.|Limita el trabajo de animación. Los tableros ocultos dejan de renderizarse.|Limitez le travail d’animation. Les échiquiers masqués cessent le rendu.|Animationsaufwand begrenzen. Versteckte Bretter rendern nicht.|Limita o trabalho de animação. Tabuleiros ocultos param de renderizar.|Limita il lavoro di animazione. Le scacchiere nascoste smettono di renderizzare.|Beperk animatiewerk. Verborgen borden stoppen met renderen.|Ogranicz pracę animacji. Ukryte szachownice nie są renderowane.
Higher quality uses more graphics resources.|Mayor calidad usa más recursos gráficos.|Une qualité supérieure utilise plus de ressources graphiques.|Höhere Qualität benötigt mehr Grafikressourcen.|Maior qualidade usa mais recursos gráficos.|Una qualità superiore usa più risorse grafiche.|Hogere kwaliteit gebruikt meer grafische middelen.|Wyższa jakość zużywa więcej zasobów graficznych.
Reduced-motion preferences disable movement. GPU engines share graphics resources with the display.|La preferencia de movimiento reducido desactiva la animación. Los motores GPU comparten recursos gráficos con la pantalla.|La préférence de réduction des mouvements désactive l’animation. Les moteurs GPU partagent les ressources graphiques avec l’affichage.|Reduzierte Bewegung deaktiviert Animationen. GPU-Engines teilen Grafikressourcen mit der Anzeige.|A preferência por movimento reduzido desativa animações. Motores GPU compartilham recursos gráficos com a exibição.|La preferenza di movimento ridotto disattiva le animazioni. I motori GPU condividono le risorse grafiche con lo schermo.|Verminderde beweging schakelt animaties uit. GPU-engines delen grafische middelen met de weergave.|Preferencja ograniczenia ruchu wyłącza animacje. Silniki GPU współdzielą zasoby graficzne z wyświetlaniem.
Trays show recorded captures only; pieces absent from a custom starting position are not counted.|Las bandejas solo muestran capturas registradas; no cuentan piezas ausentes de una posición inicial personalizada.|Les plateaux montrent uniquement les captures enregistrées ; les pièces absentes d’une position initiale personnalisée ne sont pas comptées.|Ablagen zeigen nur erfasste Schläge; in eigenen Startstellungen fehlende Figuren werden nicht gezählt.|As bandejas mostram apenas capturas registradas; peças ausentes de uma posição inicial personalizada não são contadas.|I vassoi mostrano solo catture registrate; i pezzi assenti da una posizione iniziale personalizzata non sono conteggiati.|Bakjes tonen alleen geregistreerde slagen; ontbrekende stukken uit een aangepaste beginstelling tellen niet mee.|Tacki pokazują tylko zapisane zbicia; figury nieobecne w niestandardowej pozycji początkowej nie są liczone.
A frozen board position, with no controls in the picture. Export size: 3840 × 2160 PNG.|Posición fija, sin controles en la imagen. Tamaño: PNG de 3840 × 2160.|Position figée, sans commandes dans l’image. Taille : PNG 3840 × 2160.|Eingefrorene Stellung ohne Bedienelemente im Bild. Export: 3840 × 2160 PNG.|Posição congelada, sem controles na imagem. Tamanho: PNG de 3840 × 2160.|Posizione fissa, senza controlli nell’immagine. Dimensioni: PNG 3840 × 2160.|Een bevroren stelling zonder bediening in de afbeelding. Export: 3840 × 2160 PNG.|Zamrożona pozycja bez elementów sterujących na zdjęciu. Eksport: PNG 3840 × 2160.
4K export is unavailable on this graphics device.|La exportación 4K no está disponible en este dispositivo gráfico.|L’export 4K n’est pas disponible sur ce périphérique graphique.|4K-Export ist auf diesem Grafikgerät nicht verfügbar.|A exportação 4K não está disponível neste dispositivo gráfico.|L’esportazione 4K non è disponibile su questo dispositivo grafico.|4K-export is niet beschikbaar op dit grafische apparaat.|Eksport 4K jest niedostępny na tym urządzeniu graficznym.'''

sources=json.loads((ROOT/'locales/sources.json').read_text(encoding='utf-8'))
rows=[line.split('|') for line in ROWS.splitlines()]
assert all(len(row)==8 for row in rows)
for row in rows:sources.setdefault(row[0],['ui/board3d-presentation.js'])
for fps in (15,30):sources.setdefault(f'{fps} FPS',['ui/board3d-presentation.js'])
for i,lang in enumerate(('en','es','fr','de','pt','it','nl','pl')):
    path=ROOT/'locales'/f'{lang}.json';data=json.loads(path.read_text(encoding='utf-8'))
    for row in rows:data['messages'][row[0]]=row[i]
    for fps in (15,30):data['messages'][f'{fps} FPS']=f'{fps} FPS'
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'locales/sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('3D presentation translations updated in eight languages.')
