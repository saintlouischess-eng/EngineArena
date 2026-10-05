"""Bind the local 3D review evidence to the exact tested installer payload."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    version = re.search(r'__version__ = "([^"]+)"', (ROOT / 'arena/__init__.py').read_text(encoding='utf-8'))[1]
    payload = ROOT / 'build/installer-payload'
    manifest = read(payload / 'package-manifest.json')
    for item in manifest:
        target = (payload / item['path']).resolve()
        assert target.is_relative_to(payload.resolve()), item['path']
        assert target.stat().st_size == item['bytes'], item['path']
        assert digest(target) == item['sha256'], item['path']
    for source in [*(ROOT / 'ui').rglob('*'), *(ROOT / 'locales').rglob('*')]:
        if not source.is_file():
            continue
        relative = source.relative_to(ROOT)
        for base in (ROOT / 'release/EngineArena', payload):
            assert digest(source) == digest(base / 'worker/_internal' / relative), str(relative)
    worker = ROOT / 'release/EngineArena/worker/ArenaWorker.exe'
    assert digest(worker) == digest(payload / 'worker/ArenaWorker.exe')
    checks = {}
    latest_ui_change = max(path.stat().st_mtime for path in (ROOT / 'ui').rglob('*') if path.is_file())
    for key, relative in (
        ('source_workflow', 'test-output/workflow-ui/result.json'),
        ('display_visibility', 'test-output/display-visibility/result.json'),
        ('hover_help_regressions', 'test-output/hover-help-fixed/result.json'),
        ('visual_checks', 'test-output/staunton1849-quality/result.json'),
        ('packaged_ui', 'test-output/workflow-packaged-ui/result.json'),
    ):
        path = ROOT / relative
        checks[key] = read(path)
        assert checks[key]['passed'], key
        assert path.stat().st_mtime > latest_ui_change, 'Stale UI evidence: ' + key
    assert len(checks['packaged_ui']['views']) == 8
    validation = dict(
        version=version, worker_sha256=digest(worker), model_sha256=digest(ROOT / 'ui/staunton1849.glb'),
        python_targeted_tests=20, javascript_tests=48, catalogs=8, messages_per_catalog=3383,
        **checks,
        scope='Saved hover help and 3D-control visibility, 3D framing, crown identity and surrounding workflows. Software WebGL validation; no new hardware benchmark, endurance run or clean-machine installation.',
    )
    (ROOT / 'test-output/staunton1849-validation.json').write_text(json.dumps(validation, indent=2) + '\n', encoding='utf-8')
    installer = ROOT / f'release/EngineArenaSetup-{version}-win-x64.exe'
    report = dict(
        version=version, installer=installer.name, bytes=installer.stat().st_size,
        sha256=digest(installer), created_utc=datetime.now(timezone.utc).isoformat(),
        payload=dict(files_verified=len(manifest), errors=[], ui_and_catalogs_match_source=True, tested_worker_matches_payload=True),
        validation=validation, installed_over_owner_copy=False, published=False,
    )
    Path(str(installer) + '.validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('version', 'installer', 'bytes', 'sha256', 'payload')}, indent=2))


if __name__ == '__main__':
    main()
