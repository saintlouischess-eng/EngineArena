import asyncio
import contextlib
import subprocess
import threading
import time
from types import SimpleNamespace

from aiohttp.test_utils import TestClient,TestServer
import pytest

from arena.hardware import HardwareMonitor,Sampler,parse_gpus,read_gpus,settings
from arena.server import create_app


def test_gpu_units_identity_multiple_devices_and_unavailable_values():
    data=parse_gpus('0, GPU-a, RTX test, 1.0, 50, 4096, 16384, 62, 140.5, 350, 2400, 12000, 42\n'
                    '1, GPU-b, Other NVIDIA, 2.0, [N/A], N/A, N/A, NaN, [Not Supported], N/A, N/A, N/A, N/A\n')
    assert len(data)==2 and data[0]['id']=='GPU-a'
    assert data[0]['metrics']['gpu_memory']==4 and data[0]['metrics']['gpu_memory_total']==16
    assert data[0]['metrics']['gpu_memory_percent']==25 and data[0]['metrics']['gpu_power']==140.5
    assert all(v is None for v in data[1]['metrics'].values())
    with pytest.raises(ValueError):parse_gpus('truncated, response')


def test_gpu_timeout_missing_driver_and_hidden_read_only_command(monkeypatch):
    monkeypatch.setattr('arena.hardware.nvidia_path',lambda:None)
    assert read_gpus()[0]==[] and 'not supported' in read_gpus()[1]
    monkeypatch.setattr('arena.hardware.nvidia_path',lambda:'driver/nvidia-smi.exe')
    calls=[]
    def run(args,**kwargs):
        calls.append((args,kwargs));raise subprocess.TimeoutExpired(args,3)
    monkeypatch.setattr('arena.hardware.subprocess.run',run)
    assert 'timed out' in read_gpus()[1]
    args,kwargs=calls[0]
    assert args[1].startswith('--query-gpu=') and kwargs['timeout']==3 and kwargs['capture_output']
    assert not kwargs.get('shell',False) and kwargs['creationflags']==getattr(subprocess,'CREATE_NO_WINDOW',0)


def test_rates_warmup_reset_and_elapsed_time(tmp_path):
    s=Sampler(tmp_path)
    assert s.rate('read',100,0) is None
    assert s.rate('read',100+2**20*5,2)==2.5
    assert s.rate('read',20,4) is None
    assert s.rate('read',20,4) is None
    assert s.rate('read',20,6)==0


def test_config_validation_preserves_empty_order_and_gpu():
    value=settings({'fields':['gpu_power','ram_used','gpu_power'],'interval':10,'gpu':'GPU-x','temperature_unit':'F'})
    assert value['fields']==['gpu_power','ram_used'] and value['gpu']=='GPU-x'
    assert settings({'fields':[]})['fields']==[]
    for bad in ({'fields':['bogus']},{'fields':[{}]},{'interval':1},{'interval':True},{'gpu':23},{'temperature_unit':'K'},[]):
        with pytest.raises(ValueError):settings(bad)


def test_monitor_caches_nonoverlap_stale_and_isolates_failures(tmp_path):
    class Fake:
        def __init__(self):self.calls=[];self.fail=False
        def collect(self,gpu,cpu=False):
            self.calls.append(gpu)
            if self.fail:raise OSError('sensor unavailable')
            return {'metrics':{'ram_used':3},'gpus':[],'notes':{}}
    async def run():
        fake=Fake();monitor=HardwareMonitor(tmp_path,sampler=fake)
        try:
            assert monitor.snapshot()['stale']
            first=monitor.request();assert monitor.request() is first;await first
            assert not monitor.snapshot()['stale'] and fake.calls==[False]
            assert monitor.request() is first
            monitor.configure({'fields':['gpu_percent'],'interval':2});await monitor.request()
            assert fake.calls==[False,True]
            monitor.sampled=time.monotonic()-20;assert monitor.snapshot()['stale']
            fake.fail=True;monitor.due=0;await monitor.request()
            assert monitor.snapshot()['metrics']=={} and 'temporarily unavailable' in monitor.snapshot()['notes']['hardware']
        finally:await monitor.close()
    asyncio.run(run())


def test_slow_sensor_does_not_block_status_or_game_commit_and_preferences_restart(tmp_path,monkeypatch):
    entered=threading.Event();release=threading.Event()
    def collect(self,gpu=False,cpu=False):
        entered.set();assert release.wait(5)
        return {'metrics':{'ram_used':2},'identity':{'cpu_name':'fixture'},'gpus':[],'notes':{}}
    monkeypatch.setattr(Sampler,'collect',collect)
    chosen={'fields':['ram_available','gpu_temperature'],'interval':10,'gpu':'GPU-saved','temperature_unit':'F'}
    async def run():
        app=await create_app(tmp_path,'hardware');runner=app['runner'];runner.scheduler.cancel()
        with contextlib.suppress(asyncio.CancelledError):await runner.scheduler
        db=app['db'];t=await db.call('create_tournament','Sensor isolation',[{'name':'A'},{'name':'B'}],{'cycles':1})
        await db.call('set_state',t['id'],'running');await db.call('fill_queue',t['id'],2);g=await db.call('claim',t['id'])
        try:
            async with TestClient(TestServer(app),headers={'X-Arena-Token':'hardware'}) as client:
                r=await asyncio.wait_for(client.get('/api/status'),1);assert (await r.json())['hardware']['stale']
                assert await asyncio.to_thread(entered.wait,2)
                await asyncio.wait_for(db.call('finish',g['aid'],'1/2-1/2','fixture'),1)
                r=await asyncio.wait_for(client.get('/api/status'),1);assert r.status==200
                release.set()
                r=await client.post('/api/preferences',json={'hardware':chosen,'fontSize':16});assert r.status==200
                assert (await (await client.get('/api/preferences')).json())['hardware']==chosen
                assert (await client.post('/api/preferences',json={'hardware':{'interval':0}})).status==400
                assert (await client.get('/api/hardware')).status==200
        finally:release.set()
        app=await create_app(tmp_path,'hardware')
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'hardware'}) as client:
            assert (await (await client.get('/api/preferences')).json())['hardware']==chosen
            assert (await (await client.get('/api/status')).json())['hardware']['interval']==10
    asyncio.run(run())
