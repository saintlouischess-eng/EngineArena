from contextlib import closing
from arena.storage_forecast import project
from arena.storage import inventory
from arena.store import Store


def usage(**kw):
    return dict(settings={'backup_copies':3},database_bytes=1000,pgn_bytes=200,
                wal_bytes=50,temporary_bytes=0,total_bytes=4250,free_disk_bytes=10**9)|kw


def test_projection_counts_copies_growth_and_working_space():
    f=project(usage(),used_database_bytes=1000,completed=100,remaining=900)
    assert f['bytes_per_game']==12
    assert f['projected_total_bytes']==42050
    assert f['additional_bytes']==37800
    assert f['temporary_allowance_bytes']==20000
    assert f['headroom_bytes']==10**9-37800-20000
    assert not f['warning']
    fewer=project(usage(settings={'backup_copies':2}),used_database_bytes=1000,completed=100,remaining=900)
    assert f['projected_total_bytes']-fewer['projected_total_bytes']==10000


def test_empty_small_sample_reusable_pages_and_low_disk():
    f=project(usage(),used_database_bytes=300,completed=0,remaining=76500)
    assert f['bytes_per_game'] is None and f['projected_total_bytes'] is None
    assert f['temporary_allowance_bytes']==2000
    f=project(usage(),used_database_bytes=300,completed=100,remaining=100)
    assert f['projected_total_bytes']==4450  # growth fits existing pages
    assert project(usage(free_disk_bytes=100),used_database_bytes=1000,completed=100,remaining=0)['warning']


def test_forecast_uses_counters_and_recalculates_after_replacement_and_deletion(tmp_path):
    with closing(Store(tmp_path)) as s:
        t=s.create_tournament('Estimate',[{'name':'A'},{'name':'B'}],{'cycles':100},backup=False)
        s.set_state(t['id'],'running');s.fill_queue(t['id'],200)
        games=[]
        for _ in range(100):
            g=s.claim(t['id']);s.finish(g['aid'],'1/2-1/2','fixture');games.append(g)
        s.export_pending();s.set_state(t['id'],'paused')
        f=inventory(s)['forecast'];assert f['sample_games']==100 and f['remaining_games']==100
        # History is not queried to count games. A replacement cannot add a sample.
        s.requeue(t['id'],[games[0]['id']],mode='replacement');s.set_state(t['id'],'running')
        g=s.claim(t['id']);s.finish(g['aid'],'1-0','fixture')
        assert inventory(s)['forecast']['sample_games']==100
        s.set_state(t['id'],'paused')
        s.delete_tournament(t['id'],t['name'])
        f=inventory(s)['forecast'];assert f['sample_games']==0 and f['remaining_games']==0


def test_conditional_projection_and_unbounded_python_integer():
    f=project(usage(),used_database_bytes=10**12,completed=100,remaining=10**12,conditional=True)
    assert f['conditional'] and f['warning'] and f['projected_total_bytes']>10**22
