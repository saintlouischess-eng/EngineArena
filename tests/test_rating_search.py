"""Multi-name searches select rows, never a new rating population."""
from contextlib import closing
import csv
import io
import sys

from arena.store import Store
import arena.rating_center_report as reports
from test_rating_center import profile, finish, read


def seed(s):
    names=['Rebel 14','Rebel 17','Chess System Tal 2.0','Chess System Tal Assassin','Stockfish 19','Other 1.0']
    ps=[s.save_profile(profile(n)|{'path':sys.executable,'identity':{'name':n}}) for n in names]
    t=s.create_tournament('Search fixture',ps,{'format':'round_robin','cycles':2,
        'time_control':{'kind':'fischer','seconds':180,'increment':2}},backup=False)
    s.set_state(t['id'],'running');s.fill_queue(t['id'],t['total'])
    finish(s,t['id'],['1-0','0-1','1/2-1/2']*(t['total']//3))
    s.set_state(t['id'],'paused')
    return ps


def test_multi_name_union_keeps_ratings_ranks_cache_and_exports(tmp_path,monkeypatch):
    with closing(Store(tmp_path)) as s:
        seed(s);base=read(s);ledger=s.rows('SELECT * FROM rc_games ORDER BY gid')
        expected=[r for r in base['items'] if r['name'].startswith(('Rebel','Chess System Tal'))]
        assert len(expected)==4
        def unexpected_fit(*args,**kwargs):raise AssertionError('Search refitted the population')
        monkeypatch.setattr(reports,'fit_pool',unexpected_fit)
        for query in ['Rebel; Chess System Tal','  REBEL, chess system tal; rebel ; ', 'Rebel\nChess System Tal']:
            got=read(s,q=query)
            assert got['items']==expected and got['total']==4
            assert got['official_games']==base['official_games']
            assert got['anchor']==base['anchor']
            assert read(s,q=query,offset=2)['items']==expected[2:]
            csv_rows=list(csv.DictReader(io.StringIO(read(s,q=query,export='csv'))))
            assert {r['Configuration ID'] for r in csv_rows}=={r['id'] for r in expected}
            text=read(s,q=query,export='txt')
            assert 'Rebel 14' in text and 'Chess System Tal Assassin' in text and 'Stockfish 19' not in text
        assert read(s,q=' ;, \n ')['items']==base['items']
        assert read(s,q='not-a-name; missing too')['items']==[]
        assert s.rows('SELECT * FROM rc_games ORDER BY gid')==ledger


def test_multi_search_alias_family_id_best_and_all_categories(tmp_path):
    with closing(Store(tmp_path)) as s:
        profiles=seed(s)
        s.save_profile(profiles[-1]|{'name':'Personal display alias'})
        other=read(s,q='Personal display alias')['items'][0]
        s.rating_center_call('command',{'action':'family','entry':other['id'],'family':'Custom family'})
        for query in ['Custom family; no such name','Personal display alias; no such name',other['id'].upper()+'; no such name']:
            assert [r['id'] for r in read(s,q=query)['items']]==[other['id']]
        # Spaces remain part of a term, not an OR between individual words.
        assert read(s,q='System Tal; no such name')['total']==2
        for options in [{'versions':'best'},{'category':'all'},{'opponent_range':400}]:
            baseline=read(s,**options)
            expected=[r for r in baseline['items'] if r['name'].startswith(('Rebel','Chess System Tal'))]
            assert read(s,q='Rebel; Chess System Tal',**options)['items']==expected


def test_search_before_pagination_and_complete_export(tmp_path):
    from test_rating_range import seed as large_seed
    with closing(Store(tmp_path)) as s:
        _,ids=large_seed(s,extras=55)
        query='Extra; '+ids['A']
        full=read(s,q=query,sort='name',direction='asc',export='json')
        assert full['total']==56
        assert read(s,q=query,sort='name',direction='asc')['items']==full['items'][:50]
        assert read(s,q=query,sort='name',direction='asc',offset=50)['items']==full['items'][50:]
