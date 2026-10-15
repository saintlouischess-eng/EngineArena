import csv
import io
from contextlib import closing

from arena.rating_center_report import assign_ranks
from arena.store import Store
from test_rating_center import tournament,finish,read


def test_rating_rank_ties_roundoff_unavailable_and_page_boundaries():
    rows=[{'rating':4000-n} for n in range(70)]+[{'rating':None},{'rating':float('inf')}]
    rows[1]['rating']=4000+1e-12
    assign_ranks(rows)
    assert rows[0]['rank']==rows[1]['rank']==1
    assert rows[2]['rank']==3 and rows[50]['rank']==51 and rows[69]['rank']==70
    assert rows[70]['rank'] is rows[71]['rank'] is None


def test_ranks_survive_search_sort_export_and_category_switch(tmp_path):
    with closing(Store(tmp_path)) as s:
        tid=tournament(s);finish(s,tid,['1-0','1/2-1/2']);s.set_state(tid,'paused')
        baseline=read(s);assert [r['rank'] for r in baseline['items']]==[1,2]
        ranks={r['id']:r['rank'] for r in baseline['items']}
        for sort,direction in [('name','asc'),('rating','asc'),('rank','desc'),('games','desc')]:
            r=read(s,sort=sort,direction=direction)
            assert {x['id']:x['rank'] for x in r['items']}==ranks
        last=baseline['items'][1]
        assert read(s,q=last['id'])['items'][0]['rank']==2
        assert read(s,offset=1)['items'][0]['rank']==2
        exported=list(csv.DictReader(io.StringIO(read(s,export='csv'))))
        assert [int(r['Rank']) for r in exported]==[1,2]
        assert 'Rank' in read(s,export='txt')
        # The same CPU entries have independent ranks in another time category.
        bullet=tournament(s,tc={'kind':'fischer','seconds':30,'increment':.5})
        finish(s,bullet,['0-1','1/2-1/2']);s.set_state(bullet,'paused')
        all_rows=read(s,category='all')['items']
        for r in all_rows:
            assert 'rank' not in r
            assert r['categories']['blitz']['rank']==ranks[r['id']]
            assert r['categories']['bullet']['rank']==3-ranks[r['id']]
            assert r['categories']['classical']['rank'] is None
        exported=list(csv.DictReader(io.StringIO(read(s,category='all',export='csv'))))
        assert sorted(int(x['Rank']) for x in exported if x['Category']=='blitz')==[1,2]
        assert all(x['Rank']=='' for x in exported if x['Category']=='classical')
        assert 'blitz (rank / Elo)' in read(s,category='all',export='txt')
