"""Build the broadcast appearance catalog from the shipped Arena artwork/themes."""
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
ui = root / 'ui'
themes = {}
names = dict(dark='Midnight', light='Daylight', charcoal='Charcoal', blue='Deep Blue',
    forest='Forest', parchment='Warm Parchment', contrast='High Contrast', ocean='Ocean Blue',
    emerald='Emerald Club', royal='Royal Violet', burgundy='Burgundy', lagoon='Mint Lagoon',
    lavender='Lavender', peach='Peach & Copper', sky='Sky Blue')
for key, body in re.findall(r'\.theme-([a-z]+)\{([^}]+)\}', (ui/'workflow-plus.css').read_text(encoding='utf-8')):
    if key in names:
        values = dict(re.findall(r'--([\w-]+):([^;}]+)', body))
        light = key in ('light','parchment','lagoon','lavender','peach','sky')
        themes[key] = dict(name=names[key], light=light, **values)
        themes[key].setdefault('border', '#617181' if not light else '#8799aa')
        themes[key].setdefault('accent', '#d6b98a' if key=='charcoal' else '#176c55' if light else '#e1bb75')
pieces = [p.name for p in (ui/'pieces').iterdir() if p.is_dir() and
          all((p/(c+t+'.svg')).exists() for c in 'wb' for t in 'PNBRQK')]
panels = dict(header='Title & event', board='Game board & clocks', rotation='Rotating standings / ratings',
    standings='Live standings', ratings='Rating Center', scoreboard='Match scoreboard', analysis='Moves & thinking',
    moves='Played moves', pv='Engine thinking', evalgraph='Engine statistics graph', recent='Recent results',
    resultsstrip='Match results strip', progress='Progress & pace', conditions='Testing conditions', hardware='Hardware',
    wdl='Win / draw / loss', scoregraph='Score progression', ratinggraph='Rating progression',
    opponents='Opponent comparison', upcoming='Next materialized pairings', text='Text / intermission', image='Logo / image', ticker='News ticker')
catalog = dict(themes=themes, pieces=sorted(pieces), panels=panels,
    woods=['theme','maple','ash','oak','walnut','rosewood','ebony'],
    pieces3d=dict(staunton1849='Staunton 1849', tal1962='Tal 1962 Soviet Championship'),
    boards3d=dict(classic='Original Engine Arena',drueke='Walnut & maple · Drueke',jaques='Purpleheart & maple · Jaques'),
    rooms=dict(club='Chess club',hall='Championship hall',study='Daylight study',studio='Studio',**{'live-club':'Live chess club'}))
(ui/'broadcast-catalog.json').write_text(json.dumps(catalog, indent=2), encoding='utf-8')
print(f'Broadcast catalog: {len(themes)} themes, {len(pieces)} 2D sets, {len(panels)} panel types.')
