from contextlib import closing
from arena import rating_center_report as rc
from arena.store import Store
from arena.broadcast_server import Hub


def test_player_rating_uses_exact_profile_and_rejects_ambiguous_configurations():
    hub=Hub(None, {})
    hub.remember_ratings({'snapshot':100,'items':[
        {'id':'entry-a','rating':0,'profiles':[{'profile_id':'profile-a','name':'Engine'}]},
        {'id':'entry-b','rating':3210.25,'profiles':[{'profile_id':'profile-b','name':'Other'}]}]})
    assert hub.player_rating({'id':'profile-a','name':'Renamed'}) == {'rating':0,'rating_at':100}
    assert hub.player_rating({'id':'profile-b','name':'Other'})['rating']==3210.25
    assert hub.player_rating({'id':'unknown','name':'Other'})['rating'] is None
    hub.remember_ratings({'snapshot':200,'items':[
        {'id':'entry-b','rating':3220.5,'profiles':[{'profile_id':'profile-b','name':'Other'}]}]})
    assert hub.player_rating({'id':'profile-b'}) == {'rating':3220.5,'rating_at':200}
    hub.remember_ratings({'snapshot':200,'items':[
        {'id':'entry-b-32-threads','rating':3400,'profiles':[{'profile_id':'profile-b','name':'Other'}]}]})
    assert hub.player_rating({'id':'profile-b','name':'Other'})['rating'] is None


def test_broadcast_uses_same_estimates_without_covariance_solves(tmp_path, monkeypatch):
    with closing(Store(tmp_path)) as store:
        profiles = [{'name': name, 'sha256': name, 'threads': 1} for name in ('One', 'Two', 'Three')]
        tid = store.create_tournament('Broadcast fixture', profiles, {
            'format': 'round_robin', 'cycles': 2, 'paired': True,
            'time_control': {'kind': 'fischer', 'seconds': 180, 'increment': 2}})['id']
        store.set_state(tid, 'running')
        store.fill_queue(tid, 30)
        for outcome in ['1-0', '0-1', '1/2-1/2'] * 4:
            game = store.claim(tid)
            if not game:
                break
            store.finish(game['aid'], outcome, 'fixture')
        query = {'category': 'blitz', 'sort': 'rating', 'direction': 'desc'}
        normal = rc.report(store.path, query)
        real_rating = rc.rating
        calls = []

        def checked(values, key, confidence, full=True):
            calls.append(full)
            return real_rating(values, key, confidence, full=full)

        monkeypatch.setattr(rc, 'rating', checked)
        broadcast = rc.report(store.path, query | {'view': 'broadcast'})
        assert calls and not any(calls)
        assert [(r['id'], r['rank'], r['rating']) for r in broadcast['items']] == [
            (r['id'], r['rank'], r['rating']) for r in normal['items']]
        assert broadcast['official_games'] == normal['official_games']
