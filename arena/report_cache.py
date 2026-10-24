"""Small disposable reports keyed by the exact committed workspace revision.

Cache writes never touch tournament records, never enter recovery backups, and
can be discarded at any time. At most four rendered reports are retained.
"""
import hashlib
import json
import os
from pathlib import Path
import uuid

# Numerical-summary version. Bump when measurements or their structure change.
VERSION = 2
# Presentation changes must refresh HTML without forcing another move scan.
RENDER_VERSION = 14


def key(view, tid, confidence, all_engines, technical):
    from .i18n import current
    return snapshot_key(view,[tid,confidence,all_engines,technical,current.get(),RENDER_VERSION])


def snapshot_key(view, options):
    if not view.one("SELECT 1 FROM sqlite_master WHERE name='workspace_version'"):
        return None
    version = view.one('SELECT identity,revision FROM workspace_version WHERE singleton=1')
    return hashlib.sha256(json.dumps([VERSION,version,options],sort_keys=True).encode()).hexdigest()


def read_technical(path, cache_key):
    if not cache_key:return None
    try:
        value=json.loads((Path(path).parent/'report-cache'/(cache_key+'.json')).read_text(encoding='utf-8'))
        return {int(k):v for k,v in value.items()}
    except (OSError,ValueError,TypeError,AttributeError):return None


def write_technical(path, cache_key, value):
    try:encoded=json.dumps(value,ensure_ascii=False,allow_nan=False)
    except (ValueError,TypeError):return
    write(path,cache_key,encoded,suffix='.json')


def read(path, cache_key):
    if not cache_key:
        return None
    try:
        value = (Path(path).parent / 'report-cache' / (cache_key + '.html')).read_text(encoding='utf-8')
        return value if value.endswith('</body></html>') else None
    except (OSError, UnicodeError):
        return None


def write(path, cache_key, value, suffix='.html'):
    if not cache_key or len(value.encode('utf-8')) > 16 * 1024 * 1024:
        return
    folder = Path(path).parent / 'report-cache'
    temporary = folder / (uuid.uuid4().hex + '.tmp')
    try:
        folder.mkdir(exist_ok=True)
        temporary.write_text(value, encoding='utf-8')
        os.replace(temporary, folder / (cache_key + suffix))
        for old in sorted(folder.glob('*'+suffix), key=lambda p: p.stat().st_mtime_ns, reverse=True)[4:]:
            old.unlink(missing_ok=True)
    except OSError:
        pass  # Optional acceleration must never prevent exporting a report.
    finally:
        try:temporary.unlink(missing_ok=True)
        except OSError:pass


def clear(folder):
    for suffix in ('.html','.json'):
        for path in (Path(folder) / 'report-cache').glob('*'+suffix):path.unlink(missing_ok=True)
