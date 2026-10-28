"""Launch the independent broadcast process without touching the game runner."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
from aiohttp import ClientSession, ClientTimeout

_lock = asyncio.Lock()


async def ensure_broadcast(data_folder, restart=False):
    from .broadcast_server import VERSION
    async with _lock:
        folder=Path(data_folder)/'broadcast'
        ready_path=folder/'ready.json'
        async def existing():
            try:
                r=json.loads(ready_path.read_text())
                async with ClientSession(timeout=ClientTimeout(total=2)) as session:
                    async with session.get(r['control_url'].replace('/control?','/identity?')) as response:
                        identity=await response.json()
                        if response.status==200 and identity['version']==r['version'] and Path(identity['folder']).resolve()==folder.resolve():
                            return r
            except Exception: pass
        if result:=await existing():
            if result['version']==VERSION:return result
            if not restart:return result|{'outdated':True}
            # Only the separately confirmed broadcast helper is restarted.
            # The tournament worker is never a termination target.
            import psutil
            process=psutil.Process(int(result['pid']))
            command=process.cmdline()
            matches=('--broadcast' in command or 'arena.broadcast_server' in command)
            index=command.index('--config') if '--config' in command else -1
            if not matches or index<0 or index+1>=len(command) or Path(command[index+1]).resolve()!=folder.resolve():
                raise ValueError('The old broadcast process could not be verified. Close that broadcast helper before reopening the designer.')
            process.terminate()
            await asyncio.to_thread(process.wait,5)
        folder.mkdir(parents=True,exist_ok=True)
        command=[sys.executable,'--broadcast'] if getattr(sys,'frozen',False) else [sys.executable,'-m','arena.broadcast_server']
        command+=['--data',str(Path(data_folder).resolve()),'--config',str(folder.resolve()),'--port','8768']
        flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
        with (folder/'service.log').open('ab') as log:
            subprocess.Popen(command,cwd=str(Path(__file__).resolve().parent.parent),stdin=subprocess.DEVNULL,
                             stdout=log,stderr=log,creationflags=flags)
        for _ in range(30):
            await asyncio.sleep(.2)
            if result:=await existing():return result
        raise ValueError('Broadcast service did not start. Check whether local port 8768 is already in use.')
