"""Preview UCI profiles from Engine Arena, Cute Chess and Banksia JSON."""
import json
import math
import os
from pathlib import Path
import re
import sqlite3
from .engine_options import find_name
from .store import encode,uid


def arguments(value):
    if value in (None,''):return []
    if isinstance(value,list) and all(isinstance(x,str) and '\x00' not in x for x in value):return value
    if not isinstance(value,str):raise ValueError('Launch arguments must be text or a list')
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        shell=ctypes.WinDLL('shell32');kernel=ctypes.WinDLL('kernel32')
        shell.CommandLineToArgvW.argtypes=[wintypes.LPCWSTR,ctypes.POINTER(ctypes.c_int)]
        shell.CommandLineToArgvW.restype=ctypes.POINTER(wintypes.LPWSTR)
        kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree.restype=ctypes.c_void_p
        count=ctypes.c_int();ptr=shell.CommandLineToArgvW('engine.exe '+value,ctypes.byref(count))
        if not ptr:raise ValueError('Invalid launch arguments')
        try:return [ptr[i] for i in range(1,count.value)]
        finally:kernel.LocalFree(ptr)
    import shlex
    return shlex.split(value)


def path_from(value,base):
    if not isinstance(value,str) or not value.strip():raise ValueError('Executable path required')
    value=value.strip()
    if value.startswith('"') and value.endswith('"'):value=value[1:-1]
    if any(c in value for c in ('\x00','\r','\n','"')):raise ValueError('Use an executable path and separate launch arguments')
    p=Path(value)
    if not p.is_absolute():
        if not base or not Path(base).is_absolute():raise ValueError('Choose the original GUI folder to resolve relative paths')
        p=Path(base)/p
    return str(p.resolve())


def identity(p):
    # Different names or UCI settings intentionally form separate profiles.
    normalized={k:p.get(k) for k in ('name','time_control','gpu_group','move_book')}
    normalized.update(path=os.path.normcase(os.path.abspath(p.get('path',''))),
        cwd=os.path.normcase(os.path.abspath(p.get('cwd') or str(Path(p.get('path','')).parent))),
        args=arguments(p.get('args')),options=p.get('options') or {},threads=p.get('threads',1),hash=p.get('hash',1024))
    return json.dumps(normalized,sort_keys=True,ensure_ascii=False,allow_nan=False)


def preview(store,body):
    data=body.get('source');base=body.get('base_dir','');fmt=body.get('format','auto')
    if fmt not in ('auto','arena','cutechess','banksia'):raise ValueError('Unknown profile format')
    if isinstance(data,str):data=json.loads(data)
    if isinstance(data,dict):data=data.get('engines',data.get('profiles'))
    if not isinstance(data,list):raise ValueError('Expected a JSON list of engines or an engines/profiles list')
    existing={identity(json.loads(r['body'])) for r in store.rows('SELECT body FROM profiles')}
    items=[];seen=set()
    for index,entry in enumerate(data):
        item={'index':index,'name':'','status':'ready','messages':[]};items.append(item)
        try:
            if not isinstance(entry,dict):raise ValueError('Engine entry must be an object')
            kind=fmt if fmt!='auto' else 'banksia' if 'app' in entry else 'arena' if 'path' in entry else 'cutechess'
            app=entry.get('app',entry);item['format']=kind
            if not isinstance(app,dict):raise ValueError('Invalid engine application record')
            item['name']=str(app.get('name') or entry.get('name') or 'Engine')
            if str(app.get('protocol','uci' if kind=='arena' else '')).lower()!='uci':raise ValueError('Only UCI engines are supported; WinBoard profiles are skipped')
            if app.get('initStrings') or app.get('whitepov') or entry.get('whitepov'):raise ValueError('Custom initialization or White-POV conversion requires manual engine setup')
            cwd=app.get('workingDirectory') or app.get('working folder') or app.get('workingFolder') or app.get('cwd')
            cwd=path_from(cwd,base) if cwd else None
            path=path_from(app.get('path',app.get('command','')),cwd or base)
            opts=entry.get('options',{})
            if isinstance(opts,list):opts={o['name']:o.get('value',o.get('default')) for o in opts if isinstance(o,dict) and o.get('name') and o.get('type')!='button' and ('value' in o or 'default' in o)}
            if not isinstance(opts,dict):raise ValueError('Invalid UCI options')
            for key,value in opts.items():
                if not isinstance(key,str) or any(c in key for c in '\r\n\x00') or not isinstance(value,(str,int,float,bool)) or isinstance(value,float) and not math.isfinite(value) or any(c in str(value) for c in '\r\n\x00'):raise ValueError('Invalid UCI option name or value')
            # The preview explicitly proposes a bounded thread count. An engine's
            # automatic (zero) setting cannot be admitted as zero CPU usage.
            opts=dict(opts);thread_key=find_name(opts,'Threads');hash_key=find_name(opts,'Hash')
            threads=int(opts[thread_key] if thread_key else app.get('threads',1))
            if threads==0:
                threads=1
                if thread_key:opts[thread_key]=1
                item['messages'].append('Automatic thread count (0) changed to 1 for predictable CPU budgeting. Review this setting before importing.')
            p={'name':item['name'],'path':path,'args':arguments(app.get('args',app.get('arguments'))),
               'options':opts,'threads':threads,
               'hash':int(opts[hash_key] if hash_key else app.get('hash',1024))}
            if cwd:p['cwd']=cwd
            if kind=='arena':
                for k in ('time_control','gpu_group','extra_memory_mb','affinity','move_book'):
                    if k in entry:p[k]=entry[k]
            p=store.validate_profile(p);p.pop('id',None)
            if not Path(path).is_file():raise ValueError('Executable not found; correct the source folder or install the engine first')
            if cwd and not Path(cwd).is_dir():raise ValueError('Working directory not found')
            key=identity(p)
            if key in existing or key in seen:item['status']='duplicate';item['messages'].append('An identical profile already exists')
            seen.add(key);item['profile']=p
            item['messages'].append('Review CPU/GPU budgets and test the UCI connection after import')
            if kind!='arena' and (app.get('ponder') or app.get('timeoutScaleFactor',1)!=1 or app.get('restart')):item['messages'].append('Pondering, timeout scaling and process restart policy are tournament settings; they were not imported')
        except (ValueError,TypeError,KeyError,OverflowError) as e:item['status']='skipped';item['messages'].append(str(e))
    return {'items':items,'ready':sum(i['status']=='ready' for i in items),'total':len(items)}


def commit(store,body):
    return commit_prepared(store,preview(store,body),body.get('selected'))


def commit_prepared(store,checked,selected):
    if not isinstance(selected,list) or any(type(i) is not int for i in selected):raise ValueError('Select profiles to import')
    chosen=set(selected)
    if any(i<0 or i>=checked['total'] for i in chosen):raise ValueError('Invalid profile selection')
    rows=[i for i in checked['items'] if i['index'] in chosen]
    if any(i['status']=='skipped' for i in rows):raise ValueError('Resolve skipped profiles before importing')
    # Parsing and filesystem checks run outside the writer. Recheck registry
    # identities and database references here, immediately before the transaction.
    existing={identity(json.loads(r['body'])) for r in store.rows('SELECT body FROM profiles')}
    ready=[]
    for item in rows:
        if item['status']!='ready':continue
        p=store.validate_profile(item['profile']);key=identity(p)
        if key not in existing:ready.append(p);existing.add(key)
    with store.tx():
        for p in ready:
            p={**p,'id':uid()}
            store.db.execute('INSERT INTO profiles VALUES(?,?,?)',(p['id'],p['name'],encode(p)))
    return {'count':len(ready),'duplicates':len(rows)-len(ready)}


def read_preview(path,body):
    from .store import Store
    store=Store.__new__(Store);store.path=Path(path);store.folder=store.path.parent
    store.db=sqlite3.connect(store.path.resolve().as_uri()+'?mode=ro',uri=True,timeout=10);store.db.row_factory=sqlite3.Row
    try:
        store.db.execute('BEGIN')
        return preview(store,body)
    finally:store.db.close()
