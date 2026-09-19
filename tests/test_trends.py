import chess
from arena.store import Store
from arena.trends import tournament_series,game_series


def test_official_trends_pair_completion_replacement_and_diagnostics(tmp_path):
    s=Store(tmp_path);t=s.create_tournament('Trends',[{'name':'A'},{'name':'B'}],{'cycles':2});tid=t['id'];s.set_state(tid,'running');s.fill_queue(tid,4)
    a=s.claim(tid);s.finish(a['aid'],'0-1','timeout')
    first=tournament_series(s.path,tid);assert first['points'][-1]['elo'] is None and first['points'][-1]['pairs']==0
    b=s.claim(tid);s.finish(b['aid'],'1/2-1/2','fixture');before=tournament_series(s.path,tid)
    assert before['points'][-1]['pairs']==1 and before['points'][-1]['score_pct']==25
    s.set_state(tid,'paused');s.requeue(tid,[a['id']],mode='diagnostic');s.set_state(tid,'running');g=s.claim(tid);s.finish(g['aid'],'1-0','fixture')
    assert tournament_series(s.path,tid)==before
    s.set_state(tid,'paused');s.requeue(tid,[a['id']],mode='replacement');s.set_state(tid,'running');g=s.claim(tid);s.finish(g['aid'],'1-0','fixture')
    after=tournament_series(s.path,tid);assert after['official_games']==2 and after['points'][-1]['score_pct']==75 and after['points'][-1]['pairs']==1
    s.close();s=Store(tmp_path);assert tournament_series(s.path,tid)==after;s.close()


def test_sequential_curve_preserves_original_evidence_after_replacement(tmp_path):
    s=Store(tmp_path);t=s.create_tournament('Sequential charts',[{'name':'A'},{'name':'B'}],{'format':'sprt','cycles':20});tid=t['id'];s.set_state(tid,'running');s.fill_queue(tid,8);games=[]
    for _ in range(6):
        g=s.claim(tid);s.finish(g['aid'],'1-0' if g['white']==0 else '0-1','fixture');games.append(g)
    before=tournament_series(s.path,tid);assert len(before['sequential'])==3
    s.set_state(tid,'paused');s.requeue(tid,[games[0]['id']],mode='replacement');s.set_state(tid,'running');g=s.claim(tid);s.finish(g['aid'],'0-1','fixture')
    after=tournament_series(s.path,tid);assert after['sequential']==before['sequential'] and after['sequential_state']['decision']=='invalidated';s.close()


def test_game_chart_preserves_both_colors_and_absent_node_clocks(tmp_path):
    s=Store(tmp_path);t=s.create_tournament('Telemetry',[{'name':'A'},{'name':'B'}],{'cycles':1,'time_control':{'kind':'nodes','nodes':100}});tid=t['id'];s.set_state(tid,'running');s.fill_queue(tid,2);g=s.claim(tid)
    board=chess.Board();moves=['g1f3','g8f6','f3g1','f6g8'];clock={'white':{'remaining':None},'black':{'remaining':None}}
    # Long reversible move sequence exercises downsampling independent of runner adjudication.
    for i in range(1200):
        move=chess.Move.from_uci(moves[i%4]);san=board.san(move);board.push(move)
        s.move(g['aid'],i+1,move.uci(),san,board.fen(),.01,clock,{'cp':i,'nodes':100,'wdl':[100,800,100]})
    r=game_series(s.path,tid,1,limit=100)
    assert len(r['points'])<=102 and {p['color'] for p in r['points']}=={'white','black'}
    assert r['points'][0]['x']==1 and r['points'][-1]['x']==1200
    assert all(p['clocks']['white']['remaining'] is None for p in r['points'])
    s.finish(g['aid'],'1/2-1/2','fixture');assert game_series(s.path,tid,1)['official'];s.close()


def test_selfplay_trend_does_not_infer_ratings(tmp_path):
    s=Store(tmp_path);t=s.create_tournament('Self',[{'name':'Only engine'}],{'format':'self_play','cycles':1});tid=t['id'];s.set_state(tid,'running');s.fill_queue(tid,2)
    for _ in range(2):g=s.claim(tid);s.finish(g['aid'],'1-0','fixture')
    r=tournament_series(s.path,tid);assert r['official_games']==2 and r['points'][-1]['wins']==2 and r['points'][-1]['elo'] is None;s.close()
