"""Offline translations for the competition desk; preserve existing catalogs."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
M={
'Stage conditions':'Condiciones de las etapas|Conditions des étapes|Phasenbedingungen|Condições das etapas|Condizioni delle fasi|Fasevoorwaarden|Warunki etapów',
'Per-engine controls':'Ritmos por motor|Cadences par moteur|Bedenkzeiten je Engine|Ritmos por motor|Cadenze per motore|Tempo per engine|Tempo dla każdego silnika',
'Official failure results':'Resultados oficiales por fallo|Résultats officiels sur défaillance|Offizielle Fehlerergebnisse|Resultados oficiais por falha|Risultati ufficiali per errore|Officiële uitslagen door fouten|Oficjalne wyniki awarii',
'All entrants':'Todos los participantes|Tous les participants|Alle Teilnehmer|Todos os participantes|Tutti i partecipanti|Alle deelnemers|Wszyscy uczestnicy',
'Career totals are descriptive. Versions, opponents and time controls can differ; no combined Elo is inferred.':'Los totales son descriptivos. Las versiones, rivales y ritmos pueden variar; no se calcula un Elo combinado.|Les totaux sont descriptifs. Versions, adversaires et cadences peuvent varier ; aucun Elo combiné n’est déduit.|Karrieresummen sind beschreibend. Versionen, Gegner und Bedenkzeiten können abweichen; es wird kein gemeinsames Elo abgeleitet.|Os totais são descritivos. Versões, adversários e ritmos podem variar; não se calcula Elo combinado.|I totali sono descrittivi. Versioni, avversari e cadenze possono variare; non viene dedotto un Elo complessivo.|Totalen zijn beschrijvend. Versies, tegenstanders en tempo’s kunnen verschillen; er wordt geen gecombineerd Elo afgeleid.|Sumy mają charakter opisowy. Wersje, przeciwnicy i tempa mogą się różnić; nie wylicza się łącznego Elo.',
'Champions':'Campeones|Champions|Meister|Campeões|Campioni|Kampioenen|Mistrzowie',
'Championship place':'Plaza en la final|Place en finale|Finalplatz|Vaga na final|Posto in finale|Finaleplaats|Miejsce w finale',
'Championship race':'Carrera por el título|Course au titre|Meisterschaftsrennen|Disputa pelo título|Corsa al titolo|Titelstrijd|Walka o tytuł',
'Championship seasons':'Temporadas con título|Saisons titrées|Meistersaisons|Temporadas com título|Stagioni vinte|Kampioensseizoenen|Sezony mistrzowskie',
'Climbs from initial seeding':'Ascensos desde la siembra inicial|Progressions depuis la tête de série initiale|Aufstieg gegenüber der Setzposition|Avanços desde a ordem inicial|Progressi dalla testa di serie iniziale|Stijging vanaf oorspronkelijke plaatsing|Awanse względem początkowego rozstawienia',
'Competition history follows the entrant across approved engine upgrades.':'El historial sigue al participante tras las actualizaciones aprobadas del motor.|L’historique suit le participant lors des mises à jour approuvées du moteur.|Die Historie folgt dem Teilnehmer über genehmigte Engine-Updates hinweg.|O histórico acompanha o participante nas atualizações aprovadas do motor.|La cronologia segue il partecipante negli aggiornamenti approvati del motore.|De historie volgt de deelnemer bij goedgekeurde engine-updates.|Historia uczestnika jest zachowywana przy zatwierdzonych aktualizacjach silnika.',
'Competition views':'Vistas de competición|Vues de compétition|Wettbewerbsansichten|Vistas da competição|Viste della competizione|Competitieweergaven|Widoki rozgrywek',
'Complete season tables':'Tablas completas de la temporada|Tableaux complets de la saison|Vollständige Saisontabellen|Tabelas completas da temporada|Tabelle complete della stagione|Volledige seizoenstabellen|Pełne tabele sezonu',
'Copy / save summary…':'Copiar / guardar resumen…|Copier / enregistrer le résumé…|Zusammenfassung kopieren / speichern…|Copiar / salvar resumo…|Copia / salva riepilogo…|Samenvatting kopiëren / opslaan…|Kopiuj / zapisz podsumowanie…',
'Current event':'Evento actual|Événement actuel|Aktueller Wettbewerb|Evento atual|Evento attuale|Huidig evenement|Bieżące wydarzenie',
'Current roster':'Plantilla actual|Effectif actuel|Aktueller Kader|Elenco atual|Elenco attuale|Huidige deelnemers|Bieżący skład',
'Detail':'Detalle|Détail|Detailgrad|Detalhe|Dettaglio|Detail|Szczegółowość',
'Division & stage history':'Historial de divisiones y etapas|Historique des divisions et étapes|Divisions- und Phasenhistorie|Histórico de divisões e etapas|Cronologia di divisioni e fasi|Divisie- en fasehistorie|Historia dywizji i etapów',
'Division leaders':'Líderes de división|Leaders des divisions|Divisionsführende|Líderes das divisões|Leader delle divisioni|Divisieleiders|Liderzy dywizji',
'Division races':'Lucha por las divisiones|Courses des divisions|Divisionsrennen|Disputas nas divisões|Gare nelle divisioni|Divisiestrijd|Rywalizacja w dywizjach',
'Engine career':'Trayectoria del motor|Carrière du moteur|Engine-Karriere|Carreira do motor|Carriera del motore|Enginecarrière|Kariera silnika',
'Engine careers':'Trayectorias de motores|Carrières des moteurs|Engine-Karrieren|Carreiras dos motores|Carriere dei motori|Enginecarrières|Kariery silników',
'Event official games':'Partidas oficiales del evento|Parties officielles de l’événement|Offizielle Wettbewerbspartien|Partidas oficiais do evento|Partite ufficiali dell’evento|Officiële evenementpartijen|Oficjalne partie wydarzenia',
'Fingerprint':'Huella digital|Empreinte|Fingerabdruck|Impressão digital|Impronta|Vingerafdruk|Odcisk',
'Forum recap':'Resumen para foro|Résumé pour forum|Forenrückblick|Resumo para fórum|Riepilogo per forum|Forumsamenvatting|Podsumowanie na forum',
'Historical entrant':'Participante histórico|Ancien participant|Früherer Teilnehmer|Participante histórico|Partecipante storico|Voormalige deelnemer|Dawny uczestnik',
'Latest 10 seasons':'Últimas 10 temporadas|10 dernières saisons|Letzte 10 Saisons|Últimas 10 temporadas|Ultime 10 stagioni|Laatste 10 seizoenen|Ostatnie 10 sezonów',
'Live places are provisional until advancement is recorded. Tied boundaries may need playoffs.':'Las plazas en vivo son provisionales hasta registrar el avance. Los empates en los límites pueden necesitar desempates.|Les places en direct sont provisoires jusqu’à l’enregistrement de l’avancement. Les égalités aux seuils peuvent nécessiter des barrages.|Live-Plätze sind vorläufig, bis der Aufstieg festgeschrieben ist. Gleichstände an Grenzen können Entscheidungsspiele erfordern.|As posições ao vivo são provisórias até registrar o avanço. Empates nos limites podem exigir desempates.|Le posizioni in diretta sono provvisorie fino alla registrazione dell’avanzamento. I pareggi ai confini possono richiedere spareggi.|Liveposities zijn voorlopig totdat doorstroming is vastgelegd. Gelijke standen op grenzen kunnen playoffs vereisen.|Pozycje na żywo są tymczasowe do zapisania awansu. Remisy na granicach mogą wymagać baraży.',
'Next steps':'Próximos pasos|Prochaines étapes|Nächste Schritte|Próximas etapas|Prossimi passi|Volgende stappen|Następne kroki',
'No champion yet.':'Aún no hay campeón.|Aucun champion pour le moment.|Noch kein Meister.|Ainda não há campeão.|Nessun campione ancora.|Nog geen kampioen.|Jeszcze brak mistrza.',
'No recorded movements yet.':'Aún no hay movimientos registrados.|Aucun mouvement enregistré.|Noch keine Wechsel verzeichnet.|Ainda não há movimentações registradas.|Nessun movimento registrato.|Nog geen bewegingen vastgelegd.|Brak zapisanych zmian dywizji.',
'No stages have been created for this season yet.':'Aún no se han creado etapas para esta temporada.|Aucune étape créée pour cette saison.|Für diese Saison wurden noch keine Phasen erstellt.|Ainda não foram criadas etapas para esta temporada.|Nessuna fase creata per questa stagione.|Er zijn nog geen fasen voor dit seizoen aangemaakt.|Nie utworzono jeszcze etapów tego sezonu.',
'Open a stage to follow play.':'Abre una etapa para seguir las partidas.|Ouvrez une étape pour suivre les parties.|Eine Phase öffnen, um die Partien zu verfolgen.|Abra uma etapa para acompanhar as partidas.|Apri una fase per seguire il gioco.|Open een fase om de partijen te volgen.|Otwórz etap, aby śledzić grę.',
'Open the stage for the complete table.':'Abre la etapa para ver la tabla completa.|Ouvrez l’étape pour le tableau complet.|Die Phase für die vollständige Tabelle öffnen.|Abra a etapa para ver a tabela completa.|Apri la fase per la tabella completa.|Open de fase voor de volledige tabel.|Otwórz etap, aby zobaczyć pełną tabelę.',
'Place':'Puesto|Place|Platz|Posição|Posizione|Plaats|Miejsce',
'Promotion & relegation':'Ascenso y descenso|Promotion et relégation|Auf- und Abstieg|Promoção e rebaixamento|Promozione e retrocessione|Promotie en degradatie|Awans i spadek',
'Provisional':'Provisional|Provisoire|Vorläufig|Provisório|Provvisorio|Voorlopig|Tymczasowo',
'Recorded versions':'Versiones registradas|Versions enregistrées|Gespeicherte Versionen|Versões registradas|Versioni registrate|Vastgelegde versies|Zapisane wersje',
'Retained':'Permanece|Maintien|Verbleib|Mantido|Confermato|Behoud|Utrzymanie',
'Review a fixed snapshot, then copy a forum post or save a text file.':'Revisa una instantánea fija y copia un mensaje para el foro o guarda un archivo de texto.|Vérifiez un instantané fixe, puis copiez un message pour forum ou enregistrez un fichier texte.|Einen festen Stand prüfen, dann einen Forenbeitrag kopieren oder eine Textdatei speichern.|Revise um retrato fixo e copie uma postagem para fórum ou salve um arquivo de texto.|Controlla un’istantanea fissa, poi copia un post per forum o salva un file di testo.|Bekijk een vaste momentopname en kopieer een forumbericht of sla een tekstbestand op.|Przejrzyj stałą migawkę, potem skopiuj wpis na forum lub zapisz plik tekstowy.',
'Rivalries':'Rivalidades|Rivalités|Rivalitäten|Rivalidades|Rivalità|Rivaliteiten|Rywalizacje',
'Roster review':'Revisión de plantilla|Revue de l’effectif|Kaderprüfung|Revisão do elenco|Revisione dell’elenco|Deelnemerscontrole|Przegląd składu',
'Scores are from this entrant’s perspective, across valid stages in this competition.':'Las puntuaciones se muestran desde la perspectiva de este participante, en las etapas válidas de esta competición.|Les scores sont vus du participant, sur les étapes valides de cette compétition.|Die Ergebnisse gelten aus Sicht dieses Teilnehmers über gültige Phasen dieses Wettbewerbs.|Os resultados são da perspectiva deste participante, nas etapas válidas desta competição.|I risultati sono dal punto di vista di questo partecipante, nelle fasi valide della competizione.|Scores zijn vanuit deze deelnemer gezien, over geldige fasen van deze competitie.|Wyniki są z perspektywy tego uczestnika, we wszystkich ważnych etapach rozgrywek.',
'Season champion':'Campeón de temporada|Champion de la saison|Saisonmeister|Campeão da temporada|Campione della stagione|Seizoenskampioen|Mistrz sezonu',
'Season official games':'Partidas oficiales de la temporada|Parties officielles de la saison|Offizielle Saisonpartien|Partidas oficiais da temporada|Partite ufficiali della stagione|Officiële seizoenpartijen|Oficjalne partie sezonu',
'Season overview':'Vista de temporada|Vue de la saison|Saisonübersicht|Visão da temporada|Panoramica della stagione|Seizoensoverzicht|Przegląd sezonu',
'Season summary':'Resumen de temporada|Résumé de la saison|Saisonrückblick|Resumo da temporada|Riepilogo della stagione|Seizoenssamenvatting|Podsumowanie sezonu',
'Seed changes describe this event, not a measured change in engine strength.':'Los cambios de siembra describen este evento, no un cambio medido de fuerza del motor.|Les changements de classement initial décrivent cet événement, pas une variation mesurée de force.|Änderungen gegenüber der Setzliste beschreiben diesen Wettbewerb, keine gemessene Änderung der Spielstärke.|Mudanças na ordem inicial descrevem este evento, não uma mudança medida na força do motor.|Le variazioni dalla testa di serie descrivono l’evento, non un cambiamento misurato della forza.|Veranderingen vanaf de plaatsing beschrijven dit evenement, geen gemeten verandering in enginesterkte.|Zmiany względem rozstawienia opisują wydarzenie, nie zmierzoną zmianę siły silnika.',
'Stages & records':'Etapas y registros|Étapes et archives|Phasen und Aufzeichnungen|Etapas e registros|Fasi e registri|Fasen en records|Etapy i zapisy',
'Titles':'Títulos|Titres|Titel|Títulos|Titoli|Titels|Tytuły',
'Version':'Versión|Version|Version|Versão|Versione|Versie|Wersja',
'Choose a scheduled season.':'Elige una temporada programada.|Choisissez une saison programmée.|Eine geplante Saison auswählen.|Escolha uma temporada programada.|Scegli una stagione programmata.|Kies een gepland seizoen.|Wybierz zaplanowany sezon.',
'Choose an entrant from this competition.':'Elige un participante de esta competición.|Choisissez un participant à cette compétition.|Einen Teilnehmer dieses Wettbewerbs auswählen.|Escolha um participante desta competição.|Scegli un partecipante di questa competizione.|Kies een deelnemer uit deze competitie.|Wybierz uczestnika tych rozgrywek.',
}
sources=json.loads((ROOT/'locales/sources.json').read_text(encoding='utf-8'))
for k in M:sources[k]=['ui/season-insights.js','arena/event_insights.py']
sources['Engine Arena — 1.4.2']=['desktop/Program.cs']
for i,code in enumerate(['en','es','fr','de','pt','it','nl','pl']):
    p=ROOT/'locales'/f'{code}.json';data=json.loads(p.read_text(encoding='utf-8'))
    for k,v in M.items():
        assert len(v.split('|'))==7,k
        data['messages'][k]=k if i==0 else v.split('|')[i-1]
    data['messages']['Engine Arena — 1.4.2']='Engine Arena — 1.4.2'
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'locales/sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
