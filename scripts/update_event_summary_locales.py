"""Translations for completed competition summaries."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
M={
'Championship standings':'Clasificación del campeonato|Classement du championnat|Meisterschaftstabelle|Classificação do campeonato|Classifica del campionato|Kampioenschapsstand|Klasyfikacja mistrzostw',
'Championship stage total':'Total de la etapa del campeonato|Total de la phase du championnat|Gesamtzahl der Meisterschaftsphase|Total da etapa do campeonato|Totale della fase del campionato|Totaal van de kampioenschapsfase|Łącznie w fazie mistrzowskiej',
'Final match':'Encuentro final|Match final|Finalmatch|Confronto final|Incontro finale|Finalewedstrijd|Mecz finałowy',
'Tiebreaks':'Desempates|Départages|Stichkämpfe|Desempates|Spareggi|Beslissingsmatches|Dogrywki',
'Stage leaders':'Líderes de etapa|Leaders des étapes|Phasenführende|Líderes das etapas|Leader delle fasi|Faseleiders|Liderzy etapów',
'All stages':'Todas las etapas|Toutes les étapes|Alle Phasen|Todas as etapas|Tutte le fasi|Alle fasen|Wszystkie etapy',
'Placement playoff history':'Historial de desempates de clasificación|Historique des barrages de classement|Historie der Platzierungsstichkämpfe|Histórico dos desempates de classificação|Cronologia degli spareggi di piazzamento|Geschiedenis van plaatsingsplayoffs|Historia baraży o miejsca',
'Separate tiebreak tournaments; their points do not change the original group standings.':'Torneos de desempate separados; sus puntos no modifican la clasificación original del grupo.|Tournois de départage distincts ; leurs points ne modifient pas le classement initial du groupe.|Separate Stichkampfturniere; ihre Punkte ändern die ursprüngliche Gruppentabelle nicht.|Torneios de desempate separados; seus pontos não alteram a classificação original do grupo.|Tornei di spareggio separati; i loro punti non modificano la classifica originale del gruppo.|Afzonderlijke beslissings­toernooien; hun punten wijzigen de oorspronkelijke groepsstand niet.|Osobne turnieje barażowe; ich punkty nie zmieniają pierwotnej klasyfikacji grupy.',
'Advancement and final placements are recorded.':'El avance y las posiciones finales están registrados.|Les qualifications et les places finales sont enregistrées.|Weiterkommen und Endplatzierungen sind festgeschrieben.|O avanço e as posições finais estão registrados.|I passaggi del turno e i piazzamenti finali sono registrati.|Doorstroming en eindplaatsen zijn vastgelegd.|Awanse i końcowe miejsca zostały zapisane.',
'Points and W–D–L include every game in this stage. Knockout placement follows match results, not total game points.':'Los puntos y V–T–D incluyen todas las partidas de esta etapa. La posición en la eliminatoria depende de los encuentros, no del total de puntos de las partidas.|Les points et V–N–D incluent toutes les parties de cette phase. Le classement éliminatoire suit les résultats des matchs, pas le total des points de parties.|Punkte und S–R–N umfassen alle Partien dieser Phase. Die KO-Platzierung folgt den Matchergebnissen, nicht der Gesamtpunktzahl der Partien.|Os pontos e V–E–D incluem todas as partidas desta etapa. A posição no mata-mata segue os resultados dos confrontos, não a soma dos pontos das partidas.|I punti e V–P–S includono tutte le partite di questa fase. Il piazzamento a eliminazione segue i risultati degli incontri, non il totale dei punti delle partite.|Punten en W–R–V omvatten alle partijen in deze fase. De knock-outplaats volgt de matchuitslagen, niet het totale aantal partijpunten.|Punkty i W–R–P obejmują wszystkie partie tego etapu. Miejsce w systemie pucharowym wynika z rezultatów meczów, a nie łącznych punktów z partii.',
}
sources=json.loads((ROOT/'locales/sources.json').read_text(encoding='utf-8'))
for k in M:sources[k]=['ui/season-insights.js']
for i,code in enumerate(['en','es','fr','de','pt','it','nl','pl']):
    p=ROOT/'locales'/f'{code}.json';data=json.loads(p.read_text(encoding='utf-8'))
    for k,v in M.items():
        values=v.split('|');assert len(values)==7,k
        data['messages'][k]=k if i==0 else values[i-1]
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'locales/sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
