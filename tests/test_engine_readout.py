import json
import chess
import pytest

from arena.store import Store
from arena.engine_readout import collect
from arena.tournament_report import render


def displayed(store, tid):
    return [{'rank': {'slot': r['slot']}, 'profile': json.loads(r['profile'])}
            for r in store.rows('SELECT * FROM participants WHERE tid=? ORDER BY slot', (tid,))]


def session(store, tid, sid, cpu):
    body = {'hardware': {'cpu': cpu}, 'resources': {}}
    store.execute('INSERT INTO run_sessions VALUES(?,?,?,?,?,?,?)', (sid, tid, 1, 2, 2, 'closed', json.dumps(body)))


def sessions(store, tid):
    return [r | {'body': json.loads(r['body'])} for r in store.rows('SELECT * FROM run_sessions WHERE tid=? ORDER BY started,id', (tid,))]


def finish(store, tid, metrics, sid=None, result='1/2-1/2', reason='fixture', opening=None):
    g = store.claim(tid)
    if opening:
        g['opening'].update(opening)
        store.execute('UPDATE games SET opening=? WHERE id=?', (json.dumps(g['opening']), g['id']))
    if sid:
        for side in ('white', 'black'):
            store.record_engine_evidence(g['aid'], side, {'options': {'Threads': 2, 'Hash': 128}}, 1, 2, sid)
    b = chess.Board(g['opening']['fen'])
    for i, info in enumerate(metrics, 1):
        move = next(iter(b.legal_moves))
        san = b.san(move)
        b.push(move)
        clocks = {side: {'remaining': -0.01 if i == 3 else 0.5} for side in ('white', 'black')}
        store.move(g['aid'], i, move.uci(), san, b.fen(), i/10, clocks, info)
    store.finish(g['aid'], result, reason)
    return g


def test_engine_metrics_math_missing_values_and_official_scope(tmp_path):
    s = Store(tmp_path)
    try:
        t = s.create_tournament('Readouts', [{'name': 'A'}, {'name': 'B'}], {'cycles': 1})
        tid = t['id'];s.set_state(tid, 'running');s.fill_queue(tid, 2)
        session(s, tid, 'one', 'Recorded CPU')
        g = finish(s, tid, [
            {'depth': 10, 'seldepth': 20, 'nodes': 100, 'time': 50, 'nps': 2000, 'hashfull': 500, 'tbhits': 0, 'cp': 20, 'wdl': [300, 500, 200]},
            {'nodes': 200, 'time': 100, 'nps': 2000, 'depth': -1},
            {'depth': 20, 'seldepth': 40, 'nodes': 300, 'time': 150, 'nps': 2000, 'hashfull': 700, 'tbhits': 4, 'mate': 3},
            {}], 'one')
        data = collect(s, tid, t['settings'], displayed(s, tid), sessions(s, tid))
        a, = data[0];b, = data[1]
        assert a['moves'] == b['moves'] == 2
        assert a['metrics']['depth'] == {'count': 2, 'sum': 30, 'min': 10, 'max': 20}
        assert a['metrics']['hashfull']['sum'] == 120  # permille -> percent
        assert a['timed_nodes']/a['timed_seconds'] == pytest.approx(1000)
        assert a['reported_nodes']/a['reported_seconds'] == pytest.approx(2000)
        assert a['cp_moves'] == a['mate_moves'] == a['wdl_moves'] == 1
        assert a['low_clock'] == 2 and a['negative_clock'] == 1
        assert 'depth' not in b['metrics'] and b['invalid_values'] == 1
        assert b['timed_seconds'] == .2 and b['timed_moves'] == 1
        assert a['session'] == 1
        # Diagnostic work must not alter official search measurements.
        s.set_state(tid, 'paused');s.requeue(tid, [g['id']], mode='diagnostic');s.set_state(tid, 'running')
        finish(s, tid, [{'nodes': 999999}], 'one')
        assert collect(s, tid, t['settings'], displayed(s, tid), sessions(s, tid)) == data
        # A running attempt is excluded until its official result commits.
        pending = s.claim(tid)
        s.move(pending['aid'], 1, 'g1h3', 'Nh3', chess.STARTING_FEN, .1, {}, {'nodes': 777777})
        assert collect(s, tid, t['settings'], displayed(s, tid), sessions(s, tid)) == data
        html = render(s.path, tid)
        assert 'Engine technical readout' in html and 'Recorded CPU' in html
        assert 'Reported hash occupancy (%)' in html and '60.00' in html
        assert 'Not reported' in html and '999,999' not in html and '777,777' not in html
    finally:
        s.close()


def test_readouts_split_hardware_controls_and_replace_without_double_counting(tmp_path):
    s = Store(tmp_path)
    try:
        t = s.create_tournament('Split', [{'name': '<A>'}, {'name': 'B'}], {'cycles': 2})
        tid = t['id'];s.set_state(tid, 'running');s.fill_queue(tid, 4)
        session(s, tid, 'one', 'CPU one');session(s, tid, 'two', 'CPU two')
        first = finish(s, tid, [{'nodes': 10}, {'nodes': 20}], 'one')
        finish(s, tid, [{'nodes': 30}, {'nodes': 40}], 'two')
        # A saved KO playoff control replaces both participants' normal controls.
        playoff = finish(s, tid, [{'nodes': 50}, {'nodes': 60}], 'two', result='0-1', reason='timeout',
               opening={'competition_stage': 'playoff', 'playoff_time_control': {'kind': 'nodes', 'nodes': 77}})
        data = collect(s, tid, t['settings'], displayed(s, tid), sessions(s, tid))
        assert len(data[0]) == len(data[1]) == 3
        assert data[0][2]['control']['kind'] == 'nodes' and 'remaining' not in data[0][2]['metrics']
        assert data[0][2]['failures'] == {'timeout': 1} and data[1][2]['failures'] == {}
        s.set_state(tid, 'paused');s.requeue(tid, [first['id']], mode='replacement');s.set_state(tid, 'running')
        finish(s, tid, [{'nodes': 100}, {'nodes': 200}], 'one')
        data = collect(s, tid, t['settings'], displayed(s, tid), sessions(s, tid))
        assert data[0][0]['metrics']['nodes']['sum'] == 100
        assert sum(b['games'] for b in data[0]) == 3
        html = render(s.path, tid)
        assert 'CPU one' in html and 'CPU two' in html and '77 nodes per move; no chess clock' in html
        assert '&lt;A&gt;' in html and '<A>' not in html
        # Invalidated rounds cannot contribute search work or failures.
        s.execute('UPDATE games SET invalid=1 WHERE id=?', (playoff['id'],))
        data = collect(s, tid, t['settings'], displayed(s, tid), sessions(s, tid))
        assert len(data[0]) == 2 and not any(b['failures'] for b in data[0])
    finally:
        s.close()


def test_black_start_selfplay_and_legacy_hardware(tmp_path):
    s = Store(tmp_path)
    try:
        opening = chess.Board();opening.push_uci('e2e4')
        t = s.create_tournament('Self', [{'name': 'Self'}], {'format': 'self_play', 'cycles': 1, 'paired': False}, [{'fen': opening.fen()}])
        tid = t['id'];s.set_state(tid, 'running');s.fill_queue(tid, 1)
        finish(s, tid, [{'nodes': 2, 'time': 0}, {'nodes': 4, 'time': 1}], result='1-0')
        b, = collect(s, tid, t['settings'], displayed(s, tid), [])[0]
        assert b['games'] == 2 and b['white'] == b['black'] == 1
        assert b['moves'] == 2 and b['wins'] == b['losses'] == 1
        assert b['timed_nodes'] == 6 and b['reported_nodes'] == 4 and b['reported_moves'] == 1
        assert b['session'] is None
        assert 'Not recorded; current hardware is not substituted' in render(s.path, tid)
    finally:
        s.close()


def test_all_engine_report_has_no_fifty_participant_cutoff_and_can_skip_search_read(tmp_path, monkeypatch):
    s = Store(tmp_path)
    try:
        t = s.create_tournament('All', [{'name': f'Engine {i:03}'} for i in range(61)], {'format': 'round_robin'})
        concise = render(s.path, t['id'])
        assert 'Engine 060' not in concise
        complete = render(s.path, t['id'], all_engines=True)
        assert 'All 61 participants' in complete and 'Engine 060' in complete
        assert complete.count('<h4>Engine technical readout</h4>') == 61
        def forbidden(*args):
            raise AssertionError('Search history must not be scanned when disabled')
        monkeypatch.setattr('arena.engine_readout.collect', forbidden)
        assert 'Engine technical readout' not in render(s.path, t['id'], technical=False)
    finally:
        s.close()


def test_black_to_move_assigns_metrics_to_correct_engine_and_splits_configuration(tmp_path):
    s = Store(tmp_path)
    try:
        board = chess.Board();board.push_uci('e2e4')
        t = s.create_tournament('Black start', [{'name': 'A'}, {'name': 'B'}], {'cycles': 2}, [{'fen': board.fen()}])
        tid = t['id'];s.set_state(tid, 'running');s.fill_queue(tid, 4)
        session(s, tid, 'one', 'CPU')
        g = finish(s, tid, [{'nodes': 7}, {'nodes': 11}], 'one')
        data = collect(s, tid, t['settings'], displayed(s, tid), sessions(s, tid))
        assert data[g['black']][0]['metrics']['nodes']['sum'] == 7
        assert data[g['white']][0]['metrics']['nodes']['sum'] == 11
        g2 = finish(s, tid, [{'nodes': 13}, {'nodes': 17}], 'one')
        # Same machine and control, but a changed observed thread count.
        side = 'white' if g2['white'] == g['white'] else 'black'
        s.record_engine_evidence(g2['aid'], side, {'options': {'Threads': 4, 'Hash': 128}}, 1, 2, 'one')
        data = collect(s, tid, t['settings'], displayed(s, tid), sessions(s, tid))
        assert len(data[g['white']]) == 2 and len(data[g['black']]) == 1
        assert {b['observation']['options']['Threads'] for b in data[g['white']]} == {2, 4}
    finally:
        s.close()


def test_report_api_respects_engine_and_technical_export_selections(tmp_path):
    import asyncio
    import contextlib
    from aiohttp.test_utils import TestClient, TestServer
    from arena.server import create_app

    async def run():
        app = await create_app(tmp_path, 'readout-test')
        app['runner'].scheduler.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await app['runner'].scheduler
        async with TestClient(TestServer(app), headers={'X-Arena-Token': 'readout-test'}) as client:
            t = await app['db'].call('create_tournament', 'All engines', [{'name': f'E{i:03}'} for i in range(51)], {'format': 'round_robin'})
            tid = t['id']
            response = await client.get(f'/api/tournaments/{tid}/report?technical=0&all_engines=1')
            html = (await response.json())['html']
            assert 'E050' in html and 'Engine technical readout' not in html
            response = await client.get(f'/api/export/{tid}/html?technical=1&all_engines=1')
            html = await response.text()
            assert response.status == 200 and 'E050' in html
            assert html.count('<h4>Engine technical readout</h4>') == 51
    asyncio.run(run())
