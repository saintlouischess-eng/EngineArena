import json
from unittest.mock import patch

from arena import report_cache
from arena.i18n import using
from arena.report_overview import collect, conditions_changed
from arena.store import Store
from arena.tournament_report import render
from test_tournament_report import Tables


def test_official_color_and_attempt_accounting_with_replay_and_interruption(tmp_path):
    s=Store(tmp_path)
    try:
        tid=s.create_tournament('Accounting',[{'name':'A'},{'name':'B'}],{'cycles':1})['id']
        s.set_state(tid,'running');s.fill_queue(tid,2)
        first=s.claim(tid);s.finish(first['aid'],'1-0','timeout')
        second=s.claim(tid);s.finish(second['aid'],'*','interrupted')
        second=s.claim(tid);s.finish(second['aid'],'1/2-1/2','fixture')
        for mode,result in [('diagnostic','1-0'),('replacement','0-1')]:
            s.set_state(tid,'paused');s.requeue(tid,[first['id']],mode=mode);s.set_state(tid,'running')
            g=s.claim(tid);s.finish(g['aid'],result,'fixture')
        data=collect(s,tid)
        assert data['attempts']=={'total':5,'official':2,'running':0,'interrupted':1,'archived':2}
        assert data['colors'][first['white']]['white']==[0,0,1]
        assert data['colors'][first['white']]['black']==[0,1,0]
        s.execute("UPDATE tournaments SET state='completed',note='Recovered after restart.' WHERE id=?",(tid,))
        text=render(s.path,tid,technical=False);p=Tables();p.feed(text)
        assert 'Recorded tournament note: Recovered after restart.' in text
        assert '<p class="notice">Recovered' not in text
        matrix=next(t for t in p.tables if t[0]==['Engine','1','2'])
        assert matrix[1][1:] == ['—','1.5 / 2']
        assert matrix[2][1:] == ['0.5 / 2','—']
        assert '2 official games are included in complete opening pairs; 0 await' in text
    finally:s.close()


def test_unpaired_and_selfplay_report_color_semantics(tmp_path):
    s=Store(tmp_path)
    try:
        tid=s.create_tournament('Self',[{'name':'Solo'}],{'format':'self_play','cycles':1,'paired':False})['id']
        s.set_state(tid,'running');s.fill_queue(tid,1);g=s.claim(tid);s.finish(g['aid'],'1-0','fixture')
        text=render(s.path,tid,technical=False);p=Tables();p.feed(text)
        colors=next(t for t in p.tables if t[0]==['Engine','Color','Games','W–D–L','Score %'])
        assert colors[1:]==[['Solo','White','1','1–0–0','100.00'],['Solo','Black','1','0–0–1','0.00']]
        assert 'await a matching result' not in text
        matrix=next(t for t in p.tables if t[0]==['Engine','1'])
        assert matrix[1]==['1. Solo','1.0 / 1']
    finally:s.close()


def test_html_version_refresh_reuses_numerical_cache(tmp_path):
    s=Store(tmp_path)
    try:
        tid=s.create_tournament('Cache',[{'name':'A'},{'name':'B'}],{'cycles':1})['id']
        s.execute("UPDATE tournaments SET state='completed' WHERE id=?",(tid,))
        render(s.path,tid)
        with patch.object(report_cache,'RENDER_VERSION',report_cache.RENDER_VERSION+1),patch('arena.engine_readout.collect',side_effect=AssertionError('Unexpected move scan')):
            assert 'Engine technical overview' in render(s.path,tid)
    finally:s.close()


def test_localized_ko_excludes_irrelevant_standings_tiebreaks(tmp_path):
    s=Store(tmp_path)
    try:
        tid=s.create_tournament('KO',[{'name':'A'},{'name':'B'}],{'format':'knockout'})['id']
        with using('es'):
            html=render(s.path,tid,technical=False)
        assert 'wins, black_wins' not in html
    finally:s.close()


def test_hardware_variation_uses_recorded_configuration_not_sensor_noise():
    def session(cpu_threads,memory):return {'body':{'hardware':{'cpu':'CPU','physical_cores':16,'logical_processors':32},'resources':{'cpu_threads':cpu_threads,'memory_mb':memory}}}
    assert not conditions_changed([session(28,1000),session(28,2000)])
    assert conditions_changed([session(28,1000),session(16,1000)])


def test_network_evidence_does_not_claim_a_log_filename_when_none_was_recorded():
    from arena.report_evidence import observation_rows
    rows=dict(observation_rows({'observed':[{'options':{'Threads':1}}],'legacy':False,'truncated':False}))
    assert rows['Network identification']=='Not recorded'
