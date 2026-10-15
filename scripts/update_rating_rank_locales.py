"""Offline translations for Rating Center ranks."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ROWS='''
Rank|Puesto|Rang|Rang|Posição|Posizione|Rang|Pozycja
Rank follows Elo within this category and filters; sorting or searching does not change it.|El puesto sigue el Elo de esta categoría y filtros; ordenar o buscar no lo cambia.|Le rang suit l’Elo dans cette catégorie et ces filtres ; le tri ou la recherche ne le modifie pas.|Der Rang folgt der Elo in dieser Kategorie und den gewählten Filtern; Sortieren oder Suchen ändert ihn nicht.|A posição segue o Elo nesta categoria e filtros; ordenar ou pesquisar não a altera.|La posizione segue l’Elo in questa categoria e nei filtri selezionati; ordinare o cercare non la modifica.|De rang volgt de Elo binnen deze categorie en filters; sorteren of zoeken verandert deze niet.|Pozycja wynika z Elo w tej kategorii i wybranych filtrach; sortowanie ani wyszukiwanie jej nie zmienia.
Each time category has its own rating rank.|Cada categoría de tiempo tiene su propia clasificación.|Chaque catégorie de cadence a son propre classement.|Jede Bedenkzeitkategorie hat ihre eigene Rangliste.|Cada categoria de tempo tem sua própria classificação.|Ogni categoria di cadenza ha la propria classifica.|Elke tijdcategorie heeft een eigen ranglijst.|Każda kategoria tempa gry ma własny ranking.
'''
messages={}
for line in ROWS.strip().splitlines():
    key,*values=line.split('|');assert len(values)==7,key;messages[key]=values
sources=json.loads((ROOT/'locales/sources.json').read_text(encoding='utf-8'))
for key in messages:sources[key]=['ui/rating-center.js']
sources['Engine Arena — 1.5.2']=['desktop/Program.cs']
for index,code in enumerate(('en','es','fr','de','pt','it','nl','pl')):
    path=ROOT/'locales'/f'{code}.json';catalog=json.loads(path.read_text(encoding='utf-8'))
    for key,values in messages.items():catalog['messages'][key]=key if index==0 else values[index-1]
    catalog['messages']['Engine Arena — 1.5.2']='Engine Arena — 1.5.2'
    path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'locales/sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
