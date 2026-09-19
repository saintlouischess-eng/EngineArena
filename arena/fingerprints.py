"""Executable and explicit network file identity, cached by stable file metadata."""
import hashlib
from pathlib import Path
import threading

_cache={};_lock=threading.Lock()

def fingerprint(path):
    path=Path(path).resolve();stat=path.stat();key=(str(path).casefold(),stat.st_size,stat.st_mtime_ns)
    with _lock:
        if key not in _cache:
            with path.open('rb') as source:digest=hashlib.file_digest(source,'sha256').hexdigest()
            after=path.stat()
            if (after.st_size,after.st_mtime_ns)!=(stat.st_size,stat.st_mtime_ns):raise ValueError('File changed while its fingerprint was read: '+str(path))
            _cache[key]={'path':str(path),'size':stat.st_size,'mtime_ns':stat.st_mtime_ns,'sha256':digest}
        return dict(_cache[key])

def capture(profile):
    result={'executable':fingerprint(profile['path']),'networks':[],'unresolved_network_options':[]}
    options={str(k).casefold():v for k,v in profile.get('options',{}).items()}
    for name,o in profile.get('advertised',{}).items():
        key=name.casefold()
        if o.get('type')!='string' or not any(word in key for word in ('evalfile','weightsfile','networkfile','nnue')):continue
        value=options.get(key,o.get('default'))
        if not value:continue
        raw=Path(str(value));candidates=[raw] if raw.is_absolute() else [Path(profile.get('cwd') or Path(profile['path']).parent)/raw,Path(profile['path']).parent/raw]
        found=next((p for p in candidates if p.is_file()),None)
        if found:result['networks'].append({'option':name,**fingerprint(found)})
        else:result['unresolved_network_options'].append({'option':name,'value':str(value),'note':'May be embedded in the executable or resolved internally by the engine'})
    return result

def verify(profile):
    expected=profile.get('fingerprints')
    if expected:
        for old in [expected['executable'],*expected['networks']]:
            actual=fingerprint(old['path'])
            if actual['sha256']!=old['sha256']:raise ValueError('Engine or network file changed since tournament setup: '+old['path'])
    elif profile.get('sha256') and fingerprint(profile['path'])['sha256']!=profile['sha256']:
        raise ValueError('Engine executable changed since discovery. Test the connection and save the updated profile: '+profile['path'])
