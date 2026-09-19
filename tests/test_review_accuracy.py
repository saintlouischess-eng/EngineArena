import csv
import io
import math
import re
from pathlib import Path

from arena.reports import crosstable
from arena.stat_exports import standings_csv
from arena.stats import summarize
from arena.store import Store
from arena.tournament_report import render,time_description
from arena.trends import tournament_series


def test_reports_agree_after_official_replacement(tmp_path):
    store=Store(tmp_path)
    try:
        t=store.create_tournament('Report agreement',[{'name':'A','threads':1,'hash':16,'options':{'Threads':3,'Hash':64}},{'name':'B'}],{'cycles':10})
        tid=t['id'];store.set_state(tid,'running');store.fill_queue(tid,20);first=None
        for i in range(20):
            g=store.claim(tid);first=first or g
            store.finish(g['aid'],['1-0','1/2-1/2','0-1','1-0','1/2-1/2'][i%5],'test')
        store.set_state(tid,'paused');store.requeue(tid,[first['id']],mode='replacement')
        store.set_state(tid,'running');g=store.claim(tid);store.finish(g['aid'],'0-1','replacement')
        store.set_state(tid,'paused')
        for confidence in (50,95,99.99):
            live=next(r for r in store.snapshot(tid,confidence=confidence)['standings'] if r['slot']==0)
            cross=next(r for r in crosstable(store.path,tid,confidence=confidence)['cells'] if r['a']==0 and r['b']==1)
            curve=tournament_series(store.path,tid,0,confidence=confidence)['points'][-1]
            for key in ('wins','draws','losses','elo','ci','ci_conservative','los','pairs'):
                assert live[key]==cross[key]==curve[key],key
            exported=list(csv.DictReader(io.StringIO(standings_csv([live],'conservative'))))[0]
            for key,index in (('ci_lower',0),('ci_upper',1)):
                assert math.isclose(float(exported[key]),float(live['ci_conservative'][index]))
            assert exported['ci_method']=='Conservative Hoeffding'
            html=render(store.path,tid,confidence)
            assert f'Normal {confidence:g}% CI' in html
            assert '<td>3</td><td>64</td>' in html
        assert live['games']==20 and live['pairs']==10
    finally:store.close()


def test_staged_conditions_are_readable_and_los_tail_is_preserved():
    text=time_description({'kind':'staged','stages':[{'moves':40,'seconds':120,'increment':1},{'moves':20,'seconds':60,'increment':2}],'repeat':True})
    assert text=='40 moves in 120 seconds + 1 seconds per move; then 20 moves in 60 seconds + 2 seconds per move; repeat final stage'
    assert math.isclose(summarize(40,0,160)['los'],1.843767874407613e-24,rel_tol=1e-12)


def test_all_interface_assets_are_allowed():
    source=Path('arena/server.py').read_text(encoding='utf-8')
    for asset in re.findall(r'/assets/([^"\s]+)',Path('ui/index.html').read_text(encoding='utf-8')):
        assert (Path('ui')/asset).is_file()
        assert repr(asset) in source,asset
