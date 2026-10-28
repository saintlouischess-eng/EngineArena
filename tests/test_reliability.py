import contextlib
import json
from arena.store import Store
from arena.tournament_report import render
from test_core import profile,run_claim


def test_tf_attempts_official_replacements_diagnostics_restart_and_migration(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        t=s.create_tournament('TF',[profile('A'),profile('B')],{'cycles':1,'retry_limit':1});tid=t['id'];g=run_claim(s,t)
        s.finish(g['aid'],'0-1','timeout');s.finish(g['aid'],'0-1','timeout')
        auto=s.claim(tid);assert auto['id']==g['id'];s.finish(auto['aid'],'0-1','timeout')
        def counts():return next(r for r in s.snapshot(tid)['standings'] if r['slot']==g['white'])
        assert (counts()['tf'],counts()['tf_official'])==(2,1)
        for mode,result,reason in [('diagnostic','0-1','timeout'),('replacement','1-0','checkmate')]:
            s.set_state(tid,'paused');s.requeue(tid,[g['id']],mode=mode);s.set_state(tid,'running');a=s.claim(tid);s.finish(a['aid'],result,reason)
        assert (counts()['tf'],counts()['tf_official'])==(2,0)
        page=s.engine_failures(tid,g['white']);assert page['total']==2 and all(not i['official'] for i in page['items'])
        assert s.snapshot(tid,sort='tf',direction='desc')['standings'][0]['tf']==2
        assert 'Official TF' in render(s.path,tid,technical=False)
        s.execute('DROP TABLE engine_failures')  # simulate migration from pre-feature DB
    with contextlib.closing(Store(tmp_path)) as s:
        r=s.engine_failures(tid,g['white']);assert r['total']==2 and r['counts'][0]['official']==0
        assert s.snapshot(tid)['standings'][0]['tf'] in (0,2)


def test_tf_selfplay_invalidated_and_non_timeout_failures(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        t=s.create_tournament('Self',[profile('Self')],{'format':'self_play','cycles':2,'paired':False});g=run_claim(s,t)
        s.finish(g['aid'],'1-0','timeout')
        assert s.engine_failures(t['id'],0)['total']==1
        with s.tx():s._set_official(s.one('SELECT * FROM games WHERE id=?',(g['id'],)),None);s.db.execute('UPDATE games SET invalid=1 WHERE id=?',(g['id'],))
        assert s.engine_failures(t['id'],0)['counts'][0]=={'reason':'timeout','attempts':1,'official':0}
        g=s.claim(t['id']);s.finish(g['aid'],'0-1','illegal_move')
        assert s.engine_failures(t['id'],0,'illegal_move')['total']==1
        s.execute('DROP TABLE engine_failures')
    with contextlib.closing(Store(tmp_path)) as s:
        assert s.engine_failures(t['id'],0)['total']==1


def test_official_tf_sort_and_paging_after_replacement_preserve_attempt_history(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        t=s.create_tournament('TF modes',[profile('A'),profile('B')],{'cycles':1,'retry_limit':0})
        tid=t['id'];g=run_claim(s,t);s.finish(g['aid'],'0-1','timeout')
        for reason,result in [('timeout','0-1'),('checkmate','1-0')]:
            s.set_state(tid,'paused');s.requeue(tid,[g['id']],mode='replacement')
            s.set_state(tid,'running');a=s.claim(tid);assert a['id']==g['id'];s.finish(a['aid'],result,reason)
        other=s.claim(tid);assert other['white']==g['black'];s.finish(other['aid'],'0-1','timeout')
        historical=s.snapshot(tid,limit=1,sort='tf',direction='desc')['standings'][0]
        official=s.snapshot(tid,limit=1,sort='tf_official',direction='desc')['standings'][0]
        assert (historical['slot'],historical['tf'],historical['tf_official'])==(g['white'],2,0)
        assert (official['slot'],official['tf'],official['tf_official'])==(other['white'],1,1)
        second=s.snapshot(tid,offset=1,limit=1,sort='tf_official',direction='desc')['standings'][0]
        assert second['slot']==g['white'] and second['tf_official']==0
        assert s.engine_failures(tid,g['white'])['total']==2
    with contextlib.closing(Store(tmp_path)) as s:
        assert s.snapshot(tid,limit=1,sort='tf_official',direction='desc')['standings'][0]['slot']==other['white']
