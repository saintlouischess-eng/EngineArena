"""Offline translations for safer Rating Center defaults."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
key='Kept by default: already-collected results remain available for future ratings. Moves, PGNs and engine logs are deleted. Uncheck to also remove rating history.'
values={
    'en':key,
    'es':'Se conservan por defecto: los resultados ya recopilados siguen disponibles para futuras clasificaciones. Se eliminan las jugadas, los PGN y los registros de los motores. Desmarque para eliminar también el historial de clasificación.',
    'fr':'Conservation par défaut : les résultats déjà collectés restent disponibles pour les futurs classements. Les coups, les PGN et les journaux des moteurs sont supprimés. Décochez pour supprimer également l’historique des classements.',
    'de':'Standardmäßig behalten: Bereits erfasste Ergebnisse bleiben für künftige Wertungen verfügbar. Züge, PGNs und Engine-Protokolle werden gelöscht. Deaktivieren Sie diese Option, um auch den Wertungsverlauf zu löschen.',
    'pt':'Mantidos por padrão: os resultados já coletados continuam disponíveis para classificações futuras. Lances, PGNs e registros dos motores são excluídos. Desmarque para excluir também o histórico de classificação.',
    'it':'Conservati per impostazione predefinita: i risultati già raccolti restano disponibili per le valutazioni future. Mosse, PGN e registri dei motori vengono eliminati. Deselezionare per eliminare anche la cronologia delle valutazioni.',
    'nl':'Standaard behouden: al verzamelde resultaten blijven beschikbaar voor toekomstige ratings. Zetten, PGN’s en enginelogboeken worden verwijderd. Vink uit om ook de ratinggeschiedenis te verwijderen.',
    'pl':'Domyślnie zachowane: zebrane wyniki pozostają dostępne do obliczania przyszłych rankingów. Ruchy, pliki PGN i dzienniki silników są usuwane. Odznacz, aby usunąć również historię rankingu.',
}
for code,value in values.items():
    path=ROOT/'locales'/f'{code}.json';catalog=json.loads(path.read_text(encoding='utf-8'))
    catalog['messages'][key]=value
    catalog['messages']['Engine Arena — 1.5.3']='Engine Arena — 1.5.3'
    path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=ROOT/'locales/sources.json';sources=json.loads(path.read_text(encoding='utf-8'))
sources[key]=['ui/app.js','ui/seasons.js'];sources['Engine Arena — 1.5.3']=['desktop/Program.cs']
path.write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
