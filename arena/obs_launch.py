"""User-requested OBS startup; never starts an output or touches game workers."""
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import threading
import time
import psutil

_lock = threading.Lock()


def find_executable(folder, requested=''):
    if os.name != 'nt':
        raise ValueError('OBS startup from Engine Arena is available on Windows.')
    saved = {}
    try:
        saved = json.loads((Path(folder)/'obs-launch.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        pass
    explicit = requested.strip() or saved.get('path', '')
    candidates = [Path(explicit)] if explicit else []
    if not explicit:
        for key in ('ProgramW6432', 'ProgramFiles', 'ProgramFiles(x86)'):
            if os.environ.get(key):
                candidates.append(Path(os.environ[key])/'obs-studio/bin/64bit/obs64.exe')
        located = shutil.which('obs64.exe')
        if located:
            candidates.append(Path(located))
    for candidate in candidates:
        if candidate.is_absolute() and candidate.name.lower() == 'obs64.exe' and candidate.is_file():
            return candidate.resolve()
    raise ValueError('OBS was not found. Install OBS Studio or enter the full path to obs64.exe below.')


def running_instances(executable):
    found = []
    for process in psutil.process_iter(['name']):
        if (process.info['name'] or '').lower() != 'obs64.exe':
            continue
        try:
            if Path(process.exe()).resolve() != executable:
                raise ValueError('Another OBS installation is running. Select its obs64.exe path or close it before opening another copy.')
            found.append(process)
        except psutil.NoSuchProcess:
            pass
        except psutil.AccessDenied as exc:
            raise ValueError('Cannot inspect the running OBS process. Run OBS and Engine Arena under the same Windows account and permission level.') from exc
    return found


def preference_path(executable):
    root = executable.parent.parent.parent
    if any((root/name).exists() for name in ('portable_mode', 'portable_mode.txt')):
        return root/'config/obs-studio/global.ini'
    if not os.environ.get('APPDATA'):
        raise ValueError('Windows application settings folder is unavailable; OBS was not started.')
    return Path(os.environ['APPDATA'])/'obs-studio/global.ini'


def save_normal_preference(path):
    """Change only the General/ProcessPriority entry while OBS is closed."""
    path = Path(path)
    raw = path.read_bytes() if path.exists() else b''
    bom = raw.startswith(b'\xef\xbb\xbf')
    text = raw.decode('utf-8-sig')
    newline = '\r\n' if '\r\n' in text else '\n'
    lines = text.splitlines(keepends=True)
    section = None
    written = False
    result = []
    for line in lines:
        heading = re.fullmatch(r'\s*\[([^]]+)\]\s*', line.strip())
        if heading:
            if section == 'General' and not written:
                result.append('ProcessPriority=Normal'+newline)
                written = True
            section = heading[1]
        if section == 'General' and re.match(r'^\s*ProcessPriority\s*=', line):
            if not written:
                result.append('ProcessPriority=Normal'+newline)
                written = True
        else:
            result.append(line)
    if not written:
        if result and not result[-1].endswith(('\n','\r')):
            result.append(newline)
        if section != 'General':
            result.append('[General]'+newline)
        result.append('ProcessPriority=Normal'+newline)
    updated = (''.join(result)).encode('utf-8-sig' if bom else 'utf-8')
    if updated != raw:
        path.parent.mkdir(parents=True, exist_ok=True)
        backup = path.with_name(path.name+'.engine-arena-priority-backup')
        if raw and not backup.exists():
            backup.write_bytes(raw)
        temporary = path.with_name(path.name+'.arena-priority.tmp')
        temporary.write_bytes(updated)
        temporary.replace(path)


def start_detached(command, cwd):
    # NORMAL_PRIORITY_CLASS overrides a BelowNormal/Idle parent's inheritance.
    # No stream/record flags; OBS remains open when its launcher exits.
    return subprocess.Popen(command, cwd=str(cwd), stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            creationflags=(subprocess.NORMAL_PRIORITY_CLASS |
                                           subprocess.DETACHED_PROCESS |
                                           subprocess.CREATE_NEW_PROCESS_GROUP))


def verify_normal(process):
    process.nice(psutil.NORMAL_PRIORITY_CLASS)
    if process.nice() != psutil.NORMAL_PRIORITY_CLASS:
        raise ValueError('OBS opened, but Windows did not confirm Normal process priority. Check Task Manager before broadcasting.')


def status(folder, requested=''):
    try:
        executable = find_executable(folder, requested)
        processes = running_instances(executable)
        normal = bool(processes) and all(p.nice() == psutil.NORMAL_PRIORITY_CLASS for p in processes)
        return dict(available=True, path=str(executable), running=bool(processes), normal=normal,
                    message=('OBS is running at verified Normal priority.' if normal else
                             'OBS is running; click Open OBS to apply and verify Normal priority.' if processes else
                             'OBS is ready to open. Streaming stays under your control.'))
    except (ValueError, OSError, psutil.Error) as exc:
        return dict(available=False, running=False, normal=False, message=str(exc))


def launch(folder, requested=''):
    with _lock:
        executable = find_executable(folder, requested)
        processes = running_instances(executable)
        started = not processes
        if started:
            save_normal_preference(preference_path(executable))
            child = start_detached([str(executable)], executable.parent)
            processes = [psutil.Process(child.pid)]
        try:
            # Observe startup long enough to catch OBS applying its preference.
            for attempt in range(8 if started else 1):
                if started:
                    time.sleep(.5)
                for process in processes:
                    if Path(process.exe()).resolve() != executable:
                        raise ValueError('The OBS process identity changed; startup could not be verified.')
                    verify_normal(process)
        except (OSError, psutil.Error) as exc:
            raise ValueError('OBS priority could not be verified. OBS may have closed or may require matching Windows permissions. No stream was started.') from exc
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        temp = folder/'obs-launch.tmp'
        temp.write_text(json.dumps({'path':str(executable)}, indent=2), encoding='utf-8')
        temp.replace(folder/'obs-launch.json')
        return dict(available=True, path=str(executable), running=True, normal=True, started=started,
                    message=('OBS opened at verified Normal priority. Start streaming in OBS when ready.' if started else
                             'OBS is already open; Normal process priority is verified. Its current outputs were not changed.'))
