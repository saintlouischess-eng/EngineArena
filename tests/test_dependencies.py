from arena.store import Store

def profiles(n):return [{'name':f'Engine {i}','path':'fixture.exe'} for i in range(n)]

def finish_round(s,tid):
    s.fill_queue(tid,10)
    games=[]
    while g:=s.claim(tid):
        s.finish(g['aid'],'1-0','checkmate');games.append(g)
    return games

def test_swiss_replacement_requires_explicit_dependency_invalidation(tmp_path):
    s=Store(tmp_path)
    try:
        t=s.create_tournament('Swiss',profiles(4),{'format':'swiss','cycles':1,'rounds':3,'paired':True});tid=t['id'];s.set_state(tid,'running')
        first=finish_round(s,tid);second=finish_round(s,tid);assert len(first)==4 and len(second)==4
        s.set_state(tid,'paused');r=s.requeue(tid,[first[0]['id']],mode='replacement');assert r['dependency'] and r['queued']==0
        r=s.requeue(tid,[first[0]['id']],mode='replacement',invalidate=True);assert r['queued']==1
        assert s.snapshot(tid)['official_games']==4
        for g in second:
            detail=s.game_detail(g['id']);assert detail['invalid']==1;assert len(detail['attempts'])==1
        s.set_state(tid,'running');g=s.claim(tid);assert g['id']==first[0]['id'];s.finish(g['aid'],'0-1','replacement_fixture')
        generated=finish_round(s,tid);assert len(generated)==4
        assert s.snapshot(tid)['official_games']==8
    finally:s.close()

def test_knockout_dependencies_and_byes(tmp_path):
    s=Store(tmp_path)
    try:
        t=s.create_tournament('Knockout',profiles(5),{'format':'knockout','cycles':1,'paired':False});tid=t['id'];s.set_state(tid,'running')
        all_games=[]
        for _ in range(6):all_games+=finish_round(s,tid)
        assert s.tournament(tid)['state']=='completed';assert len(all_games)==4
        assert 'Winner' in s.tournament(tid)['note']
        s.set_state(tid,'paused');r=s.requeue(tid,[all_games[0]['id']],mode='replacement');assert r['dependency']
    finally:s.close()

def test_retry_limit_zero_does_not_requeue(tmp_path):
    s=Store(tmp_path)
    try:
        t=s.create_tournament('No retries',profiles(2),{'cycles':1,'retry_limit':0});tid=t['id'];s.set_state(tid,'running');s.fill_queue(tid,2)
        g=s.claim(tid);s.finish(g['aid'],'0-1','hang');assert s.game_detail(g['id'])['state']=='completed'
    finally:s.close()
