"""A small one-sided match must not erase established retained ratings."""
from contextlib import closing
import csv
import io
import pytest
from arena.store import Store
from arena.rating_center_report import report
from test_rating_center import profile,tournament,finish,read


def test_new_separated_match_deletion_filters_exports_and_restart(tmp_path):
    with closing(Store(tmp_path)) as s:
        a,b,c=[profile(name) for name in ('Reference','Established','Newcomer')]
        tid=tournament(s,profiles=[a,b]);finish(s,tid,['1-0','1/2-1/2','0-1','1-0','1/2-1/2','0-1'])
        s.set_state(tid,'paused');initial=read(s)
        anchor=next(r for r in initial['items'] if r['configuration']['version']=='Reference')['id']
        s.rating_center_call('command',{'action':'anchor','category':'blitz','entry':anchor,'rating':3628})
        initial=read(s);original={r['id']:r for r in initial['items']}
        s.delete_tournament(tid,'Rating test',True)
        extra=tournament(s,profiles=[a,c],cycles=1);finish(s,extra,['1-0','0-1']);s.set_state(extra,'paused')
        added=read(s)
        assert added['status']=='ok' and added['official_games']==8 and added['counted_games']==8
        assert added['fit_summary']=={'finite_configurations':2,'separated_configurations':1,'disconnected_configurations':0,'samples':3}
        for row in added['items']:
            if row['id'] in original:
                for key in ('rating','ci','los'):
                    expected=original[row['id']][key]
                    assert row[key]==pytest.approx(expected) if expected is not None else row[key] is None
            else:assert row['status']=='no_finite_fit' and row['rating'] is row['rank'] is None
        new=next(r for r in added['items'] if r['id'] not in original)
        s.delete_tournament(extra,'Rating test',True)
        assert read(s)['items']==added['items']
        for sort in ('name','rank','los','games'):
            rows=read(s,sort=sort,export='json')['items']
            assert {r['id']:r['rating'] for r in rows}=={r['id']:r['rating'] for r in added['items']}
        assert read(s,q=new['id'])['items'][0]['status']=='no_finite_fit'
        assert read(s,category='all')['total']==3
        assert read(s,versions='best')['fit_summary']==added['fit_summary']
        filtered=read(s,tid=tid)
        assert filtered['official_games']==6 and not filtered['fit_summary']['separated_configurations']
        exported=list(csv.DictReader(io.StringIO(read(s,export='csv'))))
        assert sum(bool(r['Rating']) for r in exported)==2
        text=read(s,export='txt');assert 'Separated results' in text and '3628.0' in text
    with closing(Store(tmp_path)) as s:
        assert read(s)['items']==added['items']
