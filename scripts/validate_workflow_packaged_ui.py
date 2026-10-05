import json,subprocess
from pathlib import Path
from rc_acceptance import Candidate,ROOT

ready=json.loads((ROOT/'test-output/workflow-package-ready.json').read_text())
c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',Path(ready['folder']))
try:
    c.launch();ready['url']=f"http://127.0.0.1:{c.info['port']}/?token={c.info['token']}"
    (ROOT/'test-output/workflow-native-ui-ready.json').write_text(json.dumps(ready),encoding='utf-8')
    result=subprocess.run(['node','scripts/validate_workflow_packaged_ui.cjs'],cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW,capture_output=True,text=True,encoding='utf-8')
    print(result.stdout,flush=True);print(result.stderr,flush=True)
    if result.returncode:raise SystemExit(result.returncode)
finally:c.stop()
