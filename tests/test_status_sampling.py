from types import SimpleNamespace
from arena.runner import Runner


def test_status_never_samples_cpu_on_the_clock_loop(monkeypatch):
    def blocked(*args,**kwargs):raise AssertionError('CPU query on UCI event loop')
    monkeypatch.setattr('arena.runner.psutil.cpu_percent',blocked)
    store=SimpleNamespace(failure='',backup_state={},storage_settings={'backup_copies':2,'backup_minutes':5})
    runner=Runner(SimpleNamespace(store=store))
    assert runner.status()['cpu_percent'] is None
    runner.runtime.monitor=SimpleNamespace(snapshot=lambda:{'metrics':{'cpu_percent':37.5},'stale':False})
    assert runner.status()['cpu_percent']==37.5
    runner.runtime.monitor=SimpleNamespace(snapshot=lambda:{'metrics':{'cpu_percent':37.5},'stale':True})
    assert runner.status()['cpu_percent'] is None
