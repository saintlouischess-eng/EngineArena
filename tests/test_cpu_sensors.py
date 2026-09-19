import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

from arena.cpu_sensors import read_cpu,select_temperature,fastest_clock

def sensor(name,value,id='sensor'):
    return {'id':id,'name':name,'hardware':'CPU fixture','celsius':value}

def test_prefer_die_package_preserve_identity_and_missing_choice():
    reading={'sensors':[sensor('CCD1 (Tdie)',75,'ccd'),sensor('Core (Tctl/Tdie)',62,'die'),sensor('CPU Package',70,'second')]}
    assert select_temperature(reading)['id']=='second'
    assert select_temperature(reading,'ccd')['celsius']==75
    assert select_temperature(reading,'missing') is None
    assert select_temperature({'sensors':[]}) is None

def test_helper_rejects_fake_zero_and_invalid_values_and_runs_hidden(tmp_path,monkeypatch):
    helper=tmp_path/'ArenaSensors.exe';helper.write_bytes(b'fixture')
    monkeypatch.setattr('arena.cpu_sensors.helper_path',lambda:helper)
    def run(args,**kwargs):
        assert args==[str(helper)] and kwargs['timeout']==5
        assert kwargs['creationflags']==getattr(subprocess,'CREATE_NO_WINDOW',0)
        assert not kwargs.get('shell')
        return SimpleNamespace(stdout=json.dumps({'status':'ok','sensors':[sensor('Core (Tctl/Tdie)',63.5),sensor('bad',0),sensor('bad',999),sensor('bad',True),sensor('bad',float('nan'))]}))
    monkeypatch.setattr('arena.cpu_sensors.subprocess.run',run)
    assert read_cpu()['sensors']==[sensor('Core (Tctl/Tdie)',63.5)]

def test_missing_driver_timeout_and_malformed_helper_are_explicit(tmp_path,monkeypatch):
    helper=tmp_path/'ArenaSensors.exe';monkeypatch.setattr('arena.cpu_sensors.helper_path',lambda:helper)
    assert read_cpu()['status']=='helper_missing';helper.write_bytes(b'fixture')
    def timeout(*args,**kwargs):raise subprocess.TimeoutExpired(args,5)
    monkeypatch.setattr('arena.cpu_sensors.subprocess.run',timeout);assert read_cpu()['status']=='timeout'
    monkeypatch.setattr('arena.cpu_sensors.subprocess.run',lambda *a,**k:SimpleNamespace(stdout='broken'))
    assert read_cpu()['status']=='error'
    monkeypatch.setattr('arena.cpu_sensors.subprocess.run',lambda *a,**k:SimpleNamespace(stdout='{"status":"driver_missing","message":"Install the signed driver","sensors":[]}'))
    assert read_cpu()['status']=='driver_missing' and read_cpu()['sensors']==[]

def test_monitor_uses_selected_sensor_and_keeps_all_observed_sensors(tmp_path):
    from arena.hardware import HardwareMonitor
    monitor=HardwareMonitor(tmp_path,{'cpu_sensor':'ccd'})
    try:
        monitor.latest={'metrics':{'cpu_temperature':50},'cpu':{'sensors':[sensor('CPU Package',50,'package'),sensor('CCD1',55,'ccd')]}}
        result=monitor.snapshot();assert result['metrics']['cpu_temperature']==55 and result['cpu_selected']['name']=='CCD1'
        assert monitor.latest['metrics']['cpu_temperature']==50
        monitor.configure({'cpu_sensor':'missing'});assert monitor.snapshot()['metrics']['cpu_temperature'] is None
    finally:monitor.executor.shutdown()


def test_fastest_live_core_excludes_bus_averages_effective_and_invalid_clocks(tmp_path,monkeypatch):
    helper=tmp_path/'ArenaSensors.exe';helper.write_bytes(b'fixture')
    monkeypatch.setattr('arena.cpu_sensors.helper_path',lambda:helper)
    def clock(name,mhz,id):return {'id':id,'name':name,'hardware':'CPU','mhz':mhz}
    valid=[clock('Core #1',4800,'a'),clock('Core #2',5200,'b'),clock('P-Core #1',5100,'c'),clock('E-Core #1',3000,'d'),clock('CPU Core',4000,'e')]
    invalid=[clock('Bus Speed',9000,'bus'),clock('Cores (Average)',9000,'average'),clock('Core #1 (Effective)',9000,'effective'),clock('Core #3',0,'zero'),clock('Core #4',True,'bool'),clock('Core #5',float('nan'),'nan'),clock('Core #6',float('inf'),'inf'),clock('Core #7',25000,'invalid')]
    monkeypatch.setattr('arena.cpu_sensors.subprocess.run',lambda *a,**k:SimpleNamespace(stdout=json.dumps({'status':'ok','sensors':[],'clocks':valid+invalid})))
    reading=read_cpu();assert reading['clocks']==valid
    assert fastest_clock(reading)==valid[1] and reading['sensors']==[]
    assert fastest_clock({'sensors':[sensor('CPU Package',65)]}) is None
    monkeypatch.setattr('arena.cpu_sensors.subprocess.run',lambda *a,**k:SimpleNamespace(stdout='{"status":"ok","sensors":[],"clocks":null}'))
    assert fastest_clock(read_cpu()) is None


def test_sampler_reports_fastest_current_clock_without_nominal_fallback(tmp_path,monkeypatch):
    import os
    if os.name!='nt':return
    from arena.hardware import Sampler
    samples=[{'status':'ok','message':'Ready','sensors':[],'clocks':[{'id':'a','name':'Core #1','hardware':'CPU','mhz':5250}]},
             {'status':'access_denied','message':'Enable CPU readings for this session','sensors':[],'clocks':[]}]
    monkeypatch.setattr('arena.cpu_sensors.read_cpu',lambda:samples.pop(0))
    sampler=Sampler(tmp_path);first=sampler.collect(cpu=True);second=sampler.collect(cpu=True)
    assert first['metrics']['cpu_fastest_clock']==5.25 and first['cpu_fastest_core']['name']=='Core #1'
    assert second['metrics']['cpu_fastest_clock'] is None and second['cpu_fastest_core'] is None
    assert 'Enable CPU readings' in second['notes']['cpu_fastest_clock']


def test_fastest_clock_alone_enables_cpu_reader_and_retains_preferences(tmp_path):
    import asyncio
    from arena.hardware import HardwareMonitor,settings
    class Fake:
        def __init__(self):self.calls=[]
        def collect(self,gpu,cpu):self.calls.append((gpu,cpu));return {'metrics':{},'cpu':{'sensors':[]},'notes':{}}
    async def run():
        fake=Fake();monitor=HardwareMonitor(tmp_path,{'fields':['cpu_fastest_clock']},fake)
        try:
            await monitor.request();assert fake.calls==[(False,True)]
            monitor.configure({'fields':['cpu_frequency']});await monitor.request();assert fake.calls[-1]==(False,False)
            assert settings({'fields':['cpu_fastest_clock'],'interval':2})['fields']==['cpu_fastest_clock']
        finally:await monitor.close()
    asyncio.run(run())
