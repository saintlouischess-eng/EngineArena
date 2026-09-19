"""Read-only, bounded hardware polling, isolated from UCI clocks and storage."""
from __future__ import annotations
import asyncio
from concurrent.futures import ThreadPoolExecutor
import csv
import io
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import time

import psutil

FIELDS={'cpu_percent','cpu_peak','cpu_frequency','cpu_fastest_clock','cpu_temperature','ram_used','ram_available','ram_percent',
        'ram_total','swap_used','disk_free','disk_percent','disk_read','disk_write','network_receive',
        'network_send','uptime','worker_memory','active_games','gpu_percent','gpu_memory','gpu_memory_percent',
        'gpu_temperature','gpu_power','gpu_power_limit','gpu_clock','gpu_memory_clock','gpu_fan'}
DEFAULTS={'fields':['cpu_percent','ram_used'],'interval':5,'gpu':'auto','cpu_sensor':'auto','temperature_unit':'C'}
GPU_QUERY='index,uuid,name,driver_version,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,power.limit,clocks.gr,clocks.mem,fan.speed'

def settings(value=None):
    if value is not None and not isinstance(value,dict):raise ValueError('Invalid hardware display settings')
    value=value if isinstance(value,dict) else {}
    fields=value.get('fields',DEFAULTS['fields'])
    if not isinstance(fields,list) or any(not isinstance(f,str) or f not in FIELDS for f in fields):raise ValueError('Unknown hardware display field')
    interval=value.get('interval',5)
    if isinstance(interval,bool) or interval not in (2,5,10,30):raise ValueError('Hardware refresh must be 2, 5, 10 or 30 seconds')
    gpu=value.get('gpu','auto');unit=value.get('temperature_unit','C')
    if not isinstance(gpu,str) or len(gpu)>160:raise ValueError('Invalid GPU selection')
    if unit not in ('C','F'):raise ValueError('Choose Celsius or Fahrenheit')
    cpu=value.get('cpu_sensor','auto')
    if not isinstance(cpu,str) or len(cpu)>200:raise ValueError('Invalid CPU temperature sensor')
    return {'fields':list(dict.fromkeys(fields)),'interval':interval,'gpu':gpu,'cpu_sensor':cpu,'temperature_unit':unit}

def number(value):
    try:
        result=float(value)
        return result if math.isfinite(result) and result>=0 else None
    except (ValueError,TypeError):return None

def parse_gpus(text):
    devices=[]
    for row in csv.reader(io.StringIO(text),skipinitialspace=True):
        if not row:continue
        if len(row)!=13:raise ValueError('Unexpected GPU driver response')
        index,uuid,name,driver=row[:4]
        values=dict(zip(('gpu_percent','memory_used_mib','memory_total_mib','gpu_temperature','gpu_power',
                         'gpu_power_limit','gpu_clock','gpu_memory_clock','gpu_fan'),map(number,row[4:])))
        total=values.pop('memory_total_mib');used=values.pop('memory_used_mib')
        values['gpu_memory']=used/1024 if used is not None else None
        values['gpu_memory_total']=total/1024 if total is not None else None
        values['gpu_memory_percent']=100*used/total if total and used is not None else None
        for key in ('gpu_percent','gpu_memory_percent','gpu_fan'):
            if values[key] is not None and values[key]>100:values[key]=None
        devices.append({'id':uuid.strip(),'index':index.strip(),'name':name.strip(),'driver':driver.strip(),'metrics':values})
    return devices

def nvidia_path():
    # Prefer the driver's known installation paths, never a user-entered command.
    if os.name=='nt':
        for path in (Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32/nvidia-smi.exe',
                     Path(os.environ.get('ProgramFiles',r'C:\Program Files'))/'NVIDIA Corporation/NVSMI/nvidia-smi.exe'):
            if path.is_file():return str(path)
        return None
    return shutil.which('nvidia-smi')

def read_gpus():
    path=nvidia_path()
    if not path:return [],'GPU telemetry requires an NVIDIA driver with nvidia-smi. Other GPU vendors are not supported by this sensor provider.'
    try:
        completed=subprocess.run([path,'--query-gpu='+GPU_QUERY,'--format=csv,noheader,nounits'],
            capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=3,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),check=True)
        return parse_gpus(completed.stdout),''
    except subprocess.TimeoutExpired:return [],'GPU driver query timed out; readings are unavailable until a later sample succeeds.'
    except (OSError,subprocess.SubprocessError,ValueError):return [],'GPU driver readings are unavailable. Check the installed NVIDIA driver.'

def cpu_name():
    if os.name=='nt':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:
                return winreg.QueryValueEx(key,'ProcessorNameString')[0].strip()
        except OSError:pass
    return platform.processor() or 'Processor identity unavailable'

class Sampler:
    def __init__(self,folder):
        self.folder=Path(folder);self.previous={};self.cpu_primed=False
        self.identity=None;self.frequency=None;self.last_static=0

    def rate(self,key,value,now):
        previous=self.previous.get(key);self.previous[key]=(now,value)
        if previous is None or now<=previous[0] or value<previous[1]:return None
        return (value-previous[1])/(now-previous[0])/2**20

    def collect(self,gpu=False,cpu=False):
        started=time.monotonic();metrics={};notes={}
        if self.identity is None:
            self.identity={'cpu_name':cpu_name(),'physical_cores':psutil.cpu_count(logical=False),'logical_cpus':psutil.cpu_count()}
        try:
            cores=psutil.cpu_percent(percpu=True)
            metrics.update(cpu_percent=sum(cores)/len(cores) if cores and self.cpu_primed else None,
                           cpu_peak=max(cores) if cores and self.cpu_primed else None)
            self.cpu_primed=True
        except (OSError,psutil.Error):notes['cpu']='CPU utilization is unavailable.'
        try:
            memory=psutil.virtual_memory()
            metrics.update(ram_used=memory.used/2**30,ram_available=memory.available/2**30,
                           ram_total=memory.total/2**30,ram_percent=memory.percent,swap_used=psutil.swap_memory().used/2**30)
        except (OSError,psutil.Error):notes['ram']='Memory readings are unavailable.'
        if not self.last_static or started-self.last_static>=60:
            try:
                frequency=psutil.cpu_freq();self.frequency=frequency.current/1000 if frequency else None
            except (OSError,psutil.Error,NotImplementedError):self.frequency=None
            self.last_static=started
        metrics['cpu_frequency']=self.frequency
        metrics['cpu_temperature']=None
        metrics['cpu_fastest_clock']=None;fastest=None
        if hasattr(psutil,'sensors_temperatures'):
            try:
                sensors=psutil.sensors_temperatures()
                temperatures=[s.current for group,values in sensors.items() if group.lower() in ('coretemp','k10temp','cpu_thermal') for s in values if number(s.current) is not None]
                if temperatures:metrics['cpu_temperature']=max(temperatures)
            except (OSError,psutil.Error):pass
        cpu_reading={'status':'disabled','message':'Select CPU temperature or Fastest CPU core to enable processor sensor readings.','sensors':[],'clocks':[]}
        if cpu and os.name=='nt':
            from .cpu_sensors import read_cpu,select_temperature,fastest_clock
            cpu_reading=read_cpu();selected=select_temperature(cpu_reading)
            metrics['cpu_temperature']=selected['celsius'] if selected else None
            fastest=fastest_clock(cpu_reading)
            metrics['cpu_fastest_clock']=fastest['mhz']/1000 if fastest else None
        if metrics['cpu_temperature'] is None:notes['cpu_temperature']=cpu_reading['message'] if cpu_reading['status']!='ok' else 'No valid CPU temperature sensor was reported.'
        if fastest is None:notes['cpu_fastest_clock']=cpu_reading['message'] if cpu_reading['status']!='ok' else 'Live core clocks have not been reported yet. Allow another refresh; clock sensor support depends on the processor.'
        try:
            disk=psutil.disk_usage(str(self.folder));metrics.update(disk_free=disk.free/2**30,disk_percent=disk.percent)
        except (OSError,psutil.Error):notes['disk']='Space on the tournament data drive is unavailable.'
        for group,reader,fields in (('disk_io',psutil.disk_io_counters,{'disk_read':'read_bytes','disk_write':'write_bytes'}),
                                    ('network',psutil.net_io_counters,{'network_receive':'bytes_recv','network_send':'bytes_sent'})):
            try:
                counters=reader()
                if counters is None:raise OSError()
                for key,field in fields.items():metrics[key]=self.rate(key,getattr(counters,field),started)
            except (OSError,psutil.Error):notes[group]='Counters unavailable; no system settings were changed.'
        metrics['uptime']=max(0,time.time()-psutil.boot_time())
        try:metrics['worker_memory']=psutil.Process().memory_info().rss/2**20
        except (OSError,psutil.Error):metrics['worker_memory']=None
        devices,message=read_gpus() if gpu else ([], 'GPU polling is off until a GPU metric is selected.')
        if message:notes['gpu']=message
        return {'metrics':metrics,'identity':self.identity,'gpus':devices,'cpu':cpu_reading,'cpu_fastest_core':fastest,'notes':notes,
                'sampled_at':time.time(),'collection_ms':round((time.monotonic()-started)*1000,2)}

class HardwareMonitor:
    def __init__(self,folder,config=None,sampler=None):
        self.config=settings(config);self.sampler=sampler or Sampler(folder)
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='HardwareReadings')
        self.task=None;self.latest=None;self.sampled=0;self.due=0;self.closed=False

    def configure(self,value):self.config=settings(value);self.due=0

    def request(self,probe=False):
        if self.closed or (self.task and not self.task.done()):return self.task
        if not probe and time.monotonic()<self.due:return self.task
        gpu=probe or any(f.startswith('gpu_') for f in self.config['fields'])
        cpu=probe or bool({'cpu_temperature','cpu_fastest_clock'} & set(self.config['fields']))
        self.task=asyncio.create_task(self._collect(gpu,cpu));return self.task

    async def _collect(self,gpu,cpu):
        try:
            self.latest=await asyncio.get_running_loop().run_in_executor(self.executor,self.sampler.collect,gpu,cpu)
            self.sampled=time.monotonic()
        except Exception:
            # A sensor failure must not mark a tournament or its durable storage as failed.
            self.latest={'metrics':{},'identity':{},'gpus':[],'notes':{'hardware':'Hardware readings are temporarily unavailable.'},'sampled_at':None}
            self.sampled=time.monotonic()
        finally:self.due=time.monotonic()+self.config['interval']

    def snapshot(self):
        from .cpu_sensors import select_temperature
        age=max(0,time.monotonic()-self.sampled) if self.latest else None
        value=self.latest or {'metrics':{},'identity':{},'gpus':[],'notes':{},'sampled_at':None}
        if value.get('cpu',{}).get('sensors'):
            selected=select_temperature(value['cpu'],self.config['cpu_sensor'])
            value=value|{'metrics':value['metrics']|{'cpu_temperature':selected['celsius'] if selected else None},'cpu_selected':selected}
        return value|{
            'age_seconds':age,'stale':age is None or age>max(10,self.config['interval']*2+3),'interval':self.config['interval']}

    async def probe(self):
        # Serialize with an existing basic sample; never queue overlapping driver probes.
        if self.task and not self.task.done():await asyncio.shield(self.task)
        await asyncio.shield(self.request(True));return self.snapshot()

    async def close(self):
        self.closed=True
        if self.task:await asyncio.gather(self.task,return_exceptions=True)
        await asyncio.to_thread(self.executor.shutdown,wait=True,cancel_futures=True)
