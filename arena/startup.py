"""Small startup diagnostics; no database contents or session tokens are logged."""
import json
import os
from pathlib import Path
import time


class StartupProgress:
    def __init__(self,folder):
        self.started=time.monotonic()

    def __call__(self,phase):
        print('ARENA_STARTUP '+json.dumps({'phase':phase,'seconds':round(time.monotonic()-self.started,3)}),flush=True)


def write_ready(path,info):
    path=Path(path)
    temporary=path.with_name(path.name+'.tmp')
    try:
        with temporary.open('w',encoding='utf-8') as output:
            json.dump(info,output);output.flush();os.fsync(output.fileno())
        os.replace(temporary,path)
    finally:
        temporary.unlink(missing_ok=True)
