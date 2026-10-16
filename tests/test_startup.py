import json
from unittest.mock import patch

import pytest

from arena.startup import write_ready,StartupProgress
from arena.store import Store


def test_readiness_replaced_atomically(tmp_path):
    path=tmp_path/'worker-ready.json';old={'pid':1,'port':2,'token':'old'}
    value={'pid':3,'port':4,'token':'new'};path.write_text(json.dumps(old))
    import os
    replace=os.replace
    def check(source,destination):
        assert json.loads(path.read_text())==old
        assert json.loads(source.read_text())==value
        replace(source,destination)
    with patch('arena.startup.os.replace',side_effect=check):write_ready(path,value)
    assert json.loads(path.read_text())==value
    assert not path.with_name(path.name+'.tmp').exists()


def test_failed_readiness_write_preserves_previous_and_cleans_temp(tmp_path):
    path=tmp_path/'worker-ready.json';path.write_text('previous')
    with patch('arena.startup.os.replace',side_effect=OSError('disk unavailable')):
        with pytest.raises(OSError):write_ready(path,{'pid':1})
    assert path.read_text()=='previous'
    assert not path.with_name(path.name+'.tmp').exists()


def test_startup_phases_dont_change_recovery(tmp_path,capsys):
    phases=[]
    store=Store(tmp_path,startup_progress=phases.append)
    assert 'Checking database integrity' in phases
    assert phases[-1]=='Reconciling saved games and PGNs'
    store.close()
    # A diagnostics callback failure must not turn into a storage failure.
    def broken(_):raise OSError('output closed')
    store=Store(tmp_path,startup_progress=broken);assert not store.failure;store.close()
    StartupProgress(tmp_path)('Worker ready')
    value=json.loads(capsys.readouterr().out.removeprefix('ARENA_STARTUP '))
    assert value['phase']=='Worker ready' and value['seconds']>=0
