"""CPU-only LibreHardwareMonitor helper. No driver installation or elevation."""
import json
import math
import os
import re
from pathlib import Path
import subprocess
import sys

def helper_path():
    if getattr(sys,'frozen',False):return Path(sys.executable).resolve().parent.parent/'ArenaSensors.exe'
    return Path(__file__).resolve().parents[1]/'release/EngineArena/ArenaSensors.exe'

def read_cpu():
    helper=helper_path()
    if not helper.is_file():return {'status':'helper_missing','message':'The CPU sensor reader is missing. Use the complete updated Engine Arena folder.','sensors':[]}
    try:
        result=subprocess.run([str(helper)],capture_output=True,text=True,encoding='utf-8',errors='replace',
            timeout=5,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),check=True)
        value=json.loads(result.stdout)
        if not isinstance(value,dict) or not isinstance(value.get('sensors'),list):raise ValueError('Invalid CPU sensor response')
        sensors=[]
        for sensor in value['sensors']:
            if not isinstance(sensor,dict):continue
            temp=sensor.get('celsius')
            if not isinstance(temp,(int,float)) or isinstance(temp,bool) or not math.isfinite(temp) or not 0<temp<=150:continue
            if not all(isinstance(sensor.get(k),str) for k in ('id','name','hardware')):continue
            sensors.append({k:sensor[k] for k in ('id','name','hardware','celsius')})
        clocks=[]
        raw_clocks=value.get('clocks',[])
        if isinstance(raw_clocks,list):
            for sensor in raw_clocks:
                if not isinstance(sensor,dict):continue
                mhz=sensor.get('mhz')
                if not isinstance(mhz,(int,float)) or isinstance(mhz,bool) or not math.isfinite(mhz) or not 0<mhz<=20000:continue
                if not all(isinstance(sensor.get(k),str) for k in ('id','name','hardware')):continue
                if not re.fullmatch(r'(?:CPU )?(?:[PE]-)?Core(?: #[0-9]+)?',sensor['name'],re.IGNORECASE):continue
                clocks.append({k:sensor[k] for k in ('id','name','hardware','mhz')})
        return {'status':'ok' if sensors or clocks else value.get('status','unavailable'),'sensors':sensors,'clocks':clocks,
                'provider':'LibreHardwareMonitor 0.9.6 / PawnIO','message':str(value.get('message','CPU temperature unavailable.'))[:500]}
    except subprocess.TimeoutExpired:return {'status':'timeout','message':'CPU sensor query timed out. Games continue normally.','sensors':[]}
    except (OSError,subprocess.SubprocessError,ValueError):return {'status':'error','message':'The CPU sensor reader could not return valid CPU sensor readings.','sensors':[]}


def fastest_clock(reading):
    """Highest current per-core operating clock; never use nominal or bus clocks."""
    return max(reading.get('clocks',[]),key=lambda s:(s['mhz'],s['id']),default=None)

def select_temperature(reading,selected='auto'):
    sensors=reading.get('sensors',[])
    if selected!='auto':return next((s for s in sensors if s['id']==selected),None)
    # Prefer die/package sensors over CCDs or individual cores; hottest package
    # is a useful aggregate on multi-socket systems, with its source retained.
    def rank(sensor):
        name=sensor['name'].casefold()
        if name in ('core (tdie)','core (tctl/tdie)','cpu package','package'):return 0
        if 'package' in name:return 1
        if name in ('core max','core (tctl)'):return 2
        return 3
    return min(sensors,key=lambda s:(rank(s),-s['celsius'],s['id'])) if sensors else None
