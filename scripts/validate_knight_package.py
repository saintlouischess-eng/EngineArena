"""Bind 3D polish acceptance evidence to the private installer and its payload."""
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    version=re.search(r'__version__ = "([^"]+)"',(ROOT/'arena/__init__.py').read_text())[1]
    tag='v'+version.replace('.','');payload=ROOT/'build/installer-payload'
    manifest=read(payload/'package-manifest.json')
    for item in manifest:
        target=(payload/item['path']).resolve();assert target.is_relative_to(payload.resolve())
        assert target.stat().st_size==item['bytes'] and digest(target)==item['sha256'],item['path']
    for folder in ('ui','locales'):
        for source in (ROOT/folder).rglob('*'):
            if not source.is_file():continue
            rel=source.relative_to(ROOT)
            for base in (ROOT/'release/EngineArena',payload):
                assert digest(source)==digest(base/'worker/_internal'/rel),str(rel)
                assert digest(source)==digest(base/'Source'/rel),str(rel)
    for source in (ROOT/'arena').glob('*.py'):
        assert digest(source)==digest(payload/'Source'/source.relative_to(ROOT)),str(source)
    checks={};correction='--crown-correction' in sys.argv;moves='--move-history' in sys.argv;lighting='--lighting' in sys.argv
    if lighting:
        evidence=[('lighting','lighting-after/result.json'),('controls','staunton1849-quality/result.json'),('lifetime','board3d-lifetime.json'),('packaged_lighting','lighting-package.json')]
    elif moves:
        evidence=[('long_history','long-scoresheet/result.json'),('packaged_history','scoresheet-package.json')]
    elif correction:
        evidence=[('packaged_correction','crown-correction-package.json')]
    else:
        evidence=[('display','knight-display/result.json'),('controls','staunton1849-quality/result.json'),
                     ('lifetime','board3d-lifetime.json'),('packaged_games','workflow-packaged-result.json'),
                     ('packaged_ui','workflow-packaged-ui/result.json')]
    for key,name in evidence:
        checks[key]=read(ROOT/'test-output'/name);assert checks[key]['passed'],key
        assert (ROOT/'test-output'/name).stat().st_mtime>max(p.stat().st_mtime for p in (ROOT/'ui').rglob('*') if p.is_file()),key+' evidence is stale'
    if lighting:
        game_proof=checks['packaged_lighting']
        assert len(game_proof['display']['views'])==8 and game_proof['display']['idleNoRedraw']
        assert checks['lifetime']['checks']['retiredContextsBounded'] and checks['controls']['contextLossFallback']
    elif moves:
        game_proof=checks['packaged_history']
        assert game_proof['display']['all805RecordedHalfMovesReachable'] and len(game_proof['display']['languages'])==8
        assert checks['long_history']['continuousScrollBothDirections'] and checks['long_history']['liveUpdatesKeepHistory']
    elif correction:
        game_proof=checks['packaged_correction'];display=game_proof['display']
        assert display['originalKnightStampRestored'] and display['onlyRookStampUpright'] and len(display['languages'])==8
    else:
        assert len(checks['display']['languages'])==len(checks['packaged_ui']['views'])==8
        game_proof=checks['packaged_games']
    assert game_proof['version']==version
    worker=ROOT/'release/EngineArena/worker/ArenaWorker.exe'
    assert game_proof['worker_sha256']==digest(worker)==digest(payload/'worker/ArenaWorker.exe')
    xml=ET.parse(ROOT/'test-output'/f'{tag}-targeted.xml').getroot()
    suites=xml.findall('testsuite');assert suites
    assert all(int(s.attrib['errors'])==int(s.attrib['failures'])==0 for s in suites)
    python_tests=sum(int(s.attrib['tests']) for s in suites)
    js=(ROOT/'test-output'/f'{tag}-js.log').read_text(encoding='utf-8-sig')
    assert re.search(r'fail 0\b',js);js_tests=int(re.search(r'tests (\d+)',js)[1])
    catalogs=read(ROOT/'test-output/languages-catalogs.json');assert not catalogs['errors']
    installer=ROOT/f'release/EngineArenaSetup-{version}-win-x64.exe'
    report={'version':version,'installer':installer.name,'bytes':installer.stat().st_size,'sha256':digest(installer),
            'created_utc':datetime.now(timezone.utc).isoformat(),'payload_files_verified':len(manifest),
            'python_tests':python_tests,'javascript_tests':js_tests,'catalogs':catalogs,'checks':checks,
            'scope':('Softer 3D lighting, source/packaged visual review, camera controls, crown marks, context-loss fallback and bounded renderer disposal/idle checks. No new real-engine games, crash test, endurance run or clean-machine installation.' if lighting else 'Long synthetic game navigation, bounded rendering, live/replay stability, request races, packaged history and eight languages. No new real-engine games, crash test, endurance run or clean-machine installation.' if moves else 'Rook-only stamp correction, original knight UV/footprint, six saved directions, replay, eight-language packaged UI and idle rendering. No new engine games, crash test, endurance run or clean-machine installation.' if correction else '3D display choices, identity/replay, resource lifetime, six short real-engine games, isolated crash recovery and packaged UI. No new endurance or clean-machine installation test.'),
            'installed_over_owner_copy':False,'published':False}
    for path in (Path(str(installer)+'.validation.json'),ROOT/'test-output'/f'{tag}-validation.json'):
        path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('checks','catalogs')},indent=2))


if __name__=='__main__':main()
