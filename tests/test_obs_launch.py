import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
import psutil
import pytest
from aiohttp.test_utils import TestClient, TestServer
from arena import obs_launch
from arena.broadcast_server import Hub, make_app


def test_obs_priority_preference_preserves_other_settings_and_backup(tmp_path):
    path=tmp_path/'global.ini'
    original=b'\xef\xbb\xbf[General]\r\nProcessPriority=BelowNormal\r\nTheme=Dark\r\n[Basic]\r\nProfile=My stream\r\nSceneCollection=Tournament\r\n'
    path.write_bytes(original)
    obs_launch.save_normal_preference(path)
    expected=original.replace(b'ProcessPriority=BelowNormal',b'ProcessPriority=Normal')
    assert path.read_bytes()==expected
    assert path.with_name('global.ini.engine-arena-priority-backup').read_bytes()==original
    obs_launch.save_normal_preference(path)
    assert path.read_bytes()==expected
    assert path.with_name('global.ini.engine-arena-priority-backup').read_bytes()==original


@pytest.mark.parametrize('contents',['','[Basic]\nProfile=Test','[General]\nTheme=Dark','[General]\nTheme=Dark\n[Basic]\nProfile=Test\n'])
def test_obs_adds_missing_priority_without_losing_lines(tmp_path,contents):
    path=tmp_path/'global.ini';path.write_text(contents)
    obs_launch.save_normal_preference(path)
    import configparser
    config=configparser.ConfigParser();config.read(path)
    assert config['General']['ProcessPriority']=='Normal'
    if 'Profile=Test' in contents:assert config['Basic']['Profile']=='Test'
    if 'Theme=Dark' in contents:assert config['General']['Theme']=='Dark'


@pytest.mark.skipif(os.name!='nt',reason='Windows priority constants')
def test_obs_launch_reuses_running_process_without_launch_or_config_write(tmp_path,monkeypatch):
    exe=(tmp_path/'obs64.exe').resolve();exe.touch()
    class Process:
        value=psutil.BELOW_NORMAL_PRIORITY_CLASS
        def exe(self):return str(exe)
        def nice(self,value=None):
            if value is not None:self.value=value
            return self.value
    process=Process()
    monkeypatch.setattr(obs_launch,'find_executable',lambda *args:exe)
    monkeypatch.setattr(obs_launch,'running_instances',lambda *args:[process])
    monkeypatch.setattr(obs_launch,'save_normal_preference',lambda *args:pytest.fail('Must not edit OBS settings while it is running'))
    monkeypatch.setattr(obs_launch,'start_detached',lambda *args:pytest.fail('Must not launch a second OBS'))
    result=obs_launch.launch(tmp_path)
    assert result['normal'] and not result['started']
    assert process.nice()==psutil.NORMAL_PRIORITY_CLASS
    assert json.loads((tmp_path/'obs-launch.json').read_text())['path']==str(exe)


@pytest.mark.skipif(os.name!='nt',reason='Windows priority constants')
def test_obs_start_saves_preference_and_verifies_real_process_priority(tmp_path,monkeypatch):
    exe=(tmp_path/'bin/64bit/obs64.exe').resolve();exe.parent.mkdir(parents=True);exe.touch()
    preference=tmp_path/'settings/global.ini';calls=[]
    process=SimpleNamespace(exe=lambda:str(exe))
    process.priority=psutil.BELOW_NORMAL_PRIORITY_CLASS
    def nice(value=None):
        if value is not None:process.priority=value
        return process.priority
    process.nice=nice
    monkeypatch.setattr(obs_launch,'find_executable',lambda *args:exe)
    monkeypatch.setattr(obs_launch,'running_instances',lambda *args:[])
    monkeypatch.setattr(obs_launch,'preference_path',lambda *args:preference)
    def start(command,cwd):
        assert 'ProcessPriority=Normal' in preference.read_text()
        calls.append((command,cwd));return SimpleNamespace(pid=123)
    monkeypatch.setattr(obs_launch,'start_detached',start)
    monkeypatch.setattr(obs_launch.psutil,'Process',lambda pid:process)
    monkeypatch.setattr(obs_launch.time,'sleep',lambda seconds:None)
    result=obs_launch.launch(tmp_path)
    assert result['normal'] and result['started']
    assert calls==[([str(exe)],exe.parent)]  # No --startstreaming/recording.
    process.nice=lambda value=None:psutil.BELOW_NORMAL_PRIORITY_CLASS
    with pytest.raises(ValueError,match='did not confirm Normal'):
        obs_launch.launch(tmp_path)


def test_obs_endpoint_requires_controller_and_same_origin(tmp_path,monkeypatch):
    calls=[]
    monkeypatch.setattr(obs_launch,'launch',lambda folder,path:calls.append(path) or {'normal':True,'message':'Verified'})
    monkeypatch.setattr(obs_launch,'status',lambda folder:{'available':True,'running':False})
    async def check():
        async with TestClient(TestServer(make_app(Hub(None,{}),tmp_path,'viewer','control'))) as client:
            origin=str(client.make_url('')).rstrip('/')
            assert (await client.get('/obs?key=viewer')).status==403
            assert (await client.post('/obs?key=viewer',json={},headers={'Origin':origin})).status==403
            assert (await client.post('/obs?key=control',json={},headers={'Origin':'https://example.com'})).status==403
            assert (await client.post('/obs?key=control',json={'path':17},headers={'Origin':origin})).status==400
            assert not calls
            assert (await client.get('/obs?key=control')).status==200
            assert not calls
            result=await client.post('/obs?key=control',json={'path':'C:/OBS/obs64.exe'},headers={'Origin':origin})
            assert result.status==200 and (await result.json())['normal']
            assert calls==['C:/OBS/obs64.exe']
    asyncio.run(check())


@pytest.mark.skipif(os.name!='nt',reason='Real Windows process-priority acceptance')
def test_normal_detached_child_survives_below_normal_parent(tmp_path):
    # Only isolated Python probes run; this never launches or contacts OBS.
    root=Path(__file__).resolve().parents[1]
    report=tmp_path/'priority.json'
    child=tmp_path/'child.py'
    child.write_text('import json,time,psutil,sys\nfrom pathlib import Path\ntime.sleep(1)\nPath(sys.argv[1]).write_text(json.dumps({"pid":psutil.Process().pid,"parent_pid":psutil.Process().ppid(),"priority":int(psutil.Process().nice())}))\ntime.sleep(1)\n')
    parent=tmp_path/'parent.py'
    parent.write_text('import sys,psutil,json\nfrom pathlib import Path\nsys.path.insert(0,sys.argv[1])\nfrom arena.obs_launch import start_detached\np=psutil.Process();p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)\nchild=start_detached([sys.executable,sys.argv[2],sys.argv[3]],Path(sys.argv[2]).parent)\nprint(json.dumps({"parent_priority":int(p.nice()),"child_pid":child.pid}))\n')
    result=subprocess.run([sys.executable,str(parent),str(root),str(child),str(report)],capture_output=True,text=True,check=True,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
    receipt=json.loads(result.stdout)
    assert receipt['parent_priority']==psutil.BELOW_NORMAL_PRIORITY_CLASS
    for _ in range(50):
        if report.exists():break
        time.sleep(.1)
    observed=json.loads(report.read_text())
    # Windows venv python.exe may redirect to its base interpreter in a child.
    assert receipt['child_pid'] in (observed['pid'],observed['parent_pid'])
    assert observed['priority']==psutil.NORMAL_PRIORITY_CLASS
