import asyncio
import contextlib
import json
import os
import subprocess
import sys
import time
import pytest
from arena.store import Store
from arena.stats import sprt_llr
from arena.tournament_report import render
from arena.trends import tournament_series


def create(s,**kw):
    return s.create_tournament('SPRT review',[{'name':'Reference <A>'},{'name':'Candidate B'}],
        {'format':'sprt','cycles':100,'sprt_candidate':1,'sprt':{'elo0':-100,'elo1':100,'alpha':.1,'beta':.1},**kw},backup=False)


def finish(s,g,score=1):
    s.finish(g['aid'],'1/2-1/2' if score==.5 else '1-0' if (g['white']==1)==bool(score) else '0-1','checkmate')


@pytest.mark.parametrize('paired',[False,True])
@pytest.mark.parametrize('score,decision',[(1,'H1'),(0,'H0')])
def test_scheduled_prefix_direction_freeze_and_charts(tmp_path,paired,score,decision):
    with contextlib.closing(Store(tmp_path)) as s:
        t=create(s,paired=paired);tid=t['id'];s.set_state(tid,'running');s.fill_queue(tid,40)
        games=[s.claim(tid) for _ in range(40)]
        for g in games[2:]:finish(s,g,score)
        assert s.snapshot(tid)['sprt'].get('samples',0)==0
        for g in games[:2]:finish(s,g,score)
        snap=s.snapshot(tid);state=snap['sprt']
        assert state['frozen'] and state['decision']==decision and state['samples']<20
        assert snap['sprt_status']['candidate']=='Candidate B'
        assert snap['sprt_status']['post_stop_games']==40-state['samples']*(2 if paired else 1)
        assert s.claim(tid) is None
        graph=tournament_series(s.path,tid,slot=0)
        assert graph['sequential_candidate']=='Candidate B'
        assert graph['sequential'][-1]['llr']==pytest.approx(state['llr'])
        assert len(s.rows('SELECT * FROM sequential_samples WHERE tid=?',(tid,)))==state['samples']


def test_cap_report_and_empty_report(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        t=create(s,cycles=2,sprt={'elo0':-5,'elo1':5,'alpha':.05,'beta':.05});tid=t['id']
        empty=render(s.path,tid,technical=False)
        assert 'Sequential test' in empty and 'Candidate B' in empty and 'Reference &lt;A&gt;' in empty
        s.set_state(tid,'running');s.fill_queue(tid,4)
        while g:=s.claim(tid):finish(s,g,.5)
        s.execute("UPDATE tournaments SET state='completed' WHERE id=?",(tid,))
        assert s.snapshot(tid)['sprt_status']['status']=='inconclusive'
        report=render(s.path,tid,technical=False)
        assert 'Inconclusive — game limit reached' in report and 'Test continuing' not in report


def test_manual_adjudication_invalidates_once_and_preserves_evidence(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        tid=create(s)['id'];s.set_state(tid,'running');s.fill_queue(tid,4)
        a,b=s.claim(tid),s.claim(tid);finish(s,a,.5);finish(s,b,.5)
        prior=s.snapshot(tid)['sprt'];g=s.claim(tid)
        s.request_adjudication(tid,g['id'],g['aid'],'1-0','operator decision')
        finish(s,g);assert s.snapshot(tid)['sprt']['decision']=='invalidated'
        assert s.snapshot(tid)['sprt']['previous']==prior
        s.set_state(tid,'paused');s.requeue(tid,[a['id']],mode='replacement')
        assert s.snapshot(tid)['sprt']['previous']==prior


def test_frozen_diagnostics_cannot_start_more_official_games(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        tid=create(s)['id'];s.set_state(tid,'running');s.fill_queue(tid,40)
        while g:=s.claim(tid):finish(s,g)
        stopped=s.snapshot(tid)['sprt'];assert stopped['frozen']
        s.set_state(tid,'paused');gid=s.one('SELECT id FROM games WHERE tid=? AND official IS NOT NULL',(tid,))['id']
        s.requeue(tid,[gid],mode='diagnostic');s.set_state(tid,'running');cursor=s.tournament(tid)['cursor']
        s.fill_queue(tid,1000);assert s.tournament(tid)['cursor']==cursor
        g=s.claim(tid);assert g['mode']=='diagnostic';finish(s,g,0)
        assert s.claim(tid) is None and s.snapshot(tid)['sprt']==stopped
        s.set_state(tid,'paused')
        with pytest.raises(ValueError,match='stopping boundary'):s.set_state(tid,'running')


def test_force_exit_preserves_prefix_and_buffered_results(tmp_path):
    code='''import os,sys
from arena.store import Store
s=Store(sys.argv[1]);t=s.create_tournament('Crash',[{'name':'A'},{'name':'B'}],{'format':'sprt','cycles':2,'sprt':{'elo0':-5,'elo1':5,'alpha':.05,'beta':.05}},backup=False)
s.set_state(t['id'],'running');s.fill_queue(t['id'],4);games=[s.claim(t['id']) for _ in range(4)]
for g in [games[0],games[2],games[3]]:s.finish(g['aid'],'1/2-1/2','stalemate')
print(t['id'],flush=True);os._exit(0)
'''
    tid=subprocess.check_output([sys.executable,'-c',code,str(tmp_path)],text=True).strip()
    with contextlib.closing(Store(tmp_path)) as s:
        assert s.snapshot(tid)['official_games']==3
        assert s.snapshot(tid)['sprt'].get('samples',0)==0
        s.set_state(tid,'running');g=s.claim(tid);finish(s,g,.5)
        assert s.snapshot(tid)['sprt']['samples']==2
        assert s.one("SELECT count(*) n FROM attempts WHERE reason='interrupted'")['n']==1


def test_pending_retry_blocks_later_samples(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        tid=create(s,retry_limit=1)['id'];s.set_state(tid,'running');s.fill_queue(tid,4)
        games=[s.claim(tid) for _ in range(4)]
        s.finish(games[0]['aid'],'0-1','crash')
        for g in games[1:]:finish(s,g,.5)
        assert s.snapshot(tid)['sprt'].get('samples',0)==0
        retry=s.claim(tid);assert retry['id']==games[0]['id'];finish(s,retry,.5)
        assert s.snapshot(tid)['sprt']['samples']==2
