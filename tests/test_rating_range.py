"""Opponent-range fits retain evidence and use a fixed, symmetric full baseline."""
from contextlib import closing
import csv
import io
import json
import math
from statistics import NormalDist
import pytest
from arena.store import Store
from arena.rating_center import entry,encode
from arena.rating_center_report import report,_cache,history
from test_rating_center import profile,tournament,finish,read


def seed(s,extras=0):
    tid=tournament(s);finish(s,tid,['1-0','0-1']);s.set_state(tid,'paused')
    base=s.one('SELECT * FROM rc_games LIMIT 1');ids={}
    tc={'kind':'fischer','seconds':180,'increment':2}
    for name in ['A','B','C','D','E','F']+[f'Extra {i:03}' for i in range(extras)]:
        key,label,threads,body,_=entry(profile(name),{},{},tc);ids[name]=key
        s.db.execute('INSERT OR IGNORE INTO rc_entries VALUES(?,?,?,?,?)',(key,label,threads,encode(body),1))
    s.db.execute('DELETE FROM rc_games');number=0;pair=0
    def matchup(a,b,w,l,d=0,paired=True):
        nonlocal number,pair
        for result in ['1-0']*w+['0-1']*l+['1/2-1/2']*d:
            for leg in range(2 if paired else 1):
                white,black=(ids[a],ids[b]) if not leg else (ids[b],ids[a])
                outcome=result if not leg or result=='1/2-1/2' else ('0-1' if result=='1-0' else '1-0')
                row=dict(base,gid=str(number),aid=str(number),pair_no=pair,leg=leg,paired=int(paired),white=white,black=black,result=outcome,ended=number+1)
                s.db.execute('INSERT INTO rc_games VALUES('+','.join('?' for _ in row)+')',tuple(row.values()));number+=1
            pair+=1
    matchup('A','B',70,30);matchup('B','C',70,30);matchup('A','C',95,5)
    matchup('C','D',99,1);matchup('D','E',60,40,paired=False);matchup('A','F',2,0)
    for name in ids:
        if name.startswith('Extra'):matchup('B',name,3,3,4)
    s.db.execute('INSERT OR REPLACE INTO rc_anchors VALUES(?,?,?,?)',('main','blitz',ids['A'],3500))
    s.db.execute('UPDATE rc_pools SET revision=revision+1')
    s.db.commit();return tid,ids


def mapped(r):return {x['id']:x for x in r['items']}


def test_known_chain_rating_ci_los_and_disconnected_results(tmp_path):
    with closing(Store(tmp_path)) as s:
        tid,ids=seed(s);full=read(s,export='json');r=read(s,opponent_range=250,export='json');rows=mapped(r)
        # All-opponent fit compromises between inconsistent A-C and A-B-C scores.
        assert abs(mapped(full)[ids['A']]['rating']-mapped(full)[ids['B']]['rating'])<250
        assert abs(mapped(full)[ids['A']]['rating']-mapped(full)[ids['C']]['rating'])>250
        step=400*math.log10(7/3)
        assert rows[ids['B']]['rating']==pytest.approx(3500-step,abs=1e-6)
        assert rows[ids['C']]['rating']==pytest.approx(3500-2*step,abs=1e-6)
        # Independent two-edge binary pair samples: analytic sandwich variance.
        se=400/math.log(10)*math.sqrt(2/(100*.7*.3)*200/198)
        ci=rows[ids['C']]['ci'];elo=rows[ids['C']]['rating']
        assert ci==pytest.approx([elo-NormalDist().inv_cdf(.975)*se,elo+NormalDist().inv_cdf(.975)*se])
        assert rows[ids['C']]['los']==pytest.approx(100*NormalDist().cdf(-2*step/se),abs=1e-10)
        for name in ('D','E'):
            row=rows[ids[name]];assert row['rating'] is row['rank'] is None
            assert row['status']=='disconnected' and row['full_rating'] is not None
        assert rows[ids['F']]['full_rating'] is None
        assert r['opponent_range']['unrated_baseline_games']==4
        assert r['opponent_range']['outside_range_games']==400
        assert r['pairs']==200 and r['unpaired']==100 and r['counted_games']==500
        assert r['official_games']==904 and r['fit_summary']['samples']==200
        assert sum(x['included_games'] for x in rows.values())==1000
        assert rows[ids['B']]['included_games']==400 and rows[ids['B']]['included_opponents']==2
        assert read(s)['items']==full['items']


def test_exports_filters_cache_anchor_and_history_are_non_destructive(tmp_path):
    with closing(Store(tmp_path)) as s:
        tid,ids=seed(s);before=[tuple(r) for r in s.db.execute('SELECT * FROM rc_games ORDER BY gid')]
        q={'opponent_range':250,'export':'json'};r=read(s,**q);baseline=mapped(r)
        for sort in ('full_rating','full_rank','rating_change','included_games','included_pairs','included_opponents','los'):
            got=read(s,**q,sort=sort);assert mapped(got)==baseline
        assert read(s,opponent_range=250,q=ids['C'])['items'][0]==baseline[ids['C']]
        best=mapped(read(s,opponent_range=250,versions='best'))
        assert set(best)==set(baseline)
        for key in best:
            for metric in ('rating','rank','full_rank','full_rating','ci','los','included_games'):
                assert best[key][metric]==baseline[key][metric]
        txt=read(s,opponent_range=250,export='txt');assert '+/-250 Elo' in txt and 'Full Elo' in txt
        csv_rows=list(csv.DictReader(io.StringIO(read(s,opponent_range=250,export='csv'))))
        assert len(csv_rows)==6 and all(x['Opponent range Elo']=='250.0' for x in csv_rows)
        assert next(x for x in csv_rows if x['Configuration ID']==ids['D'])['Rating']==''
        assert history(s.path,{'category':'blitz','entry':ids['C'],'opponent_range':250})['items'][0]['rating']['full_rating'] is not None
        # Range cache never overwrites full fit; confidence changes get new intervals.
        assert read(s,opponent_range=1)['counted_games']==0
        again=read(s,**q);assert again['items']==r['items']
        wide=read(s,opponent_range=100000,export='json');full=read(s,export='json')
        for key,row in mapped(full).items():
            for metric in ('rating','ci','los'):assert mapped(wide)[key][metric]==row[metric]
        assert mapped(read(s,opponent_range=250,confidence=99))[ids['C']]['ci'][0]<baseline[ids['C']]['ci'][0]
        s.rating_center_call('command',{'action':'anchor','category':'blitz','entry':ids['A'],'rating':3700})
        updated=read(s,**q)
        assert updated['opponent_range']['included_games']==r['opponent_range']['included_games']
        assert mapped(updated)[ids['C']]['rating']==pytest.approx(baseline[ids['C']]['rating']+200)
        assert [tuple(r) for r in s.db.execute('SELECT * FROM rc_games ORDER BY gid')]==before
        # Retained evidence requires neither PGNs nor the original tournament.
        s.delete_tournament(tid,'Rating test',True);retained=read(s,**q)
        assert retained['items']==updated['items'];assert retained['counted_games']==500
    with closing(Store(tmp_path)) as s:assert read(s,**q)['items']==retained['items']


@pytest.mark.parametrize('bad',['abc','nan','inf','-1'])
def test_bad_range(tmp_path,bad):
    with closing(Store(tmp_path)) as s:
        with pytest.raises(ValueError,match='Opponent range'):read(s,opponent_range=bad)


def test_empty_pagination_and_pair_integrity(tmp_path):
    with closing(Store(tmp_path)) as s:
        assert read(s,opponent_range=200)['items']==[]
        with pytest.raises(ValueError,match='one time category'):read(s,category='all',opponent_range=200)
        tid,ids=seed(s,extras=55)
        total=read(s,opponent_range=250,export='json');assert total['total']==61
        assert read(s,opponent_range=250,offset=50)['items']==total['items'][50:]
        assert len(read(s,opponent_range=250)['items'])==50
        # One timeout leg filtered out must also exclude its healthy partner.
        s.db.execute("UPDATE rc_games SET reason='timeout' WHERE pair_no=0 AND leg=0")
        s.db.execute('UPDATE rc_pools SET revision=revision+1');s.db.commit()
        included=read(s,opponent_range=100000);excluded=read(s,opponent_range=100000,failures='exclude')
        assert included['counted_games']-excluded['counted_games']==2
        assert excluded['sampling']['incomplete_pair_games']==1
        assert read(s,opponent_range=250,hardware='missing')['items']==[]


def test_range_boundary_and_fixed_baseline():
    from arena.rating_range import restrict
    v={'stats':{'a':{},'b':{},'c':{}},'ordered':['a','b','c'],'pairs':2,'unpaired':1,
       'observations':[(0,1,[0,1,0,0,0]),(1,2,[0,0,1,0,0]),(0,2,[1,0,0])]}
    baseline={k:{'rating':r} for k,r in zip(v['ordered'],[1000,1200,1400])}
    got=restrict(v,200,baseline)
    assert got['pairs']==2 and got['unpaired']==0
    assert got['observations']==v['observations'][:2] and v['unpaired']==1
    assert restrict(v,199.99,baseline)['observations']==[]
