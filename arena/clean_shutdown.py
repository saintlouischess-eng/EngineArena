"""A consumed-on-open receipt for an unchanged, cleanly closed workspace.

This is an optimization hint, never a recovery source. Missing, stale or damaged
receipts fall back to the existing database verification and backup path.
"""
import json
import os
import time
import math
from pathlib import Path

VERSION = 1
CHECK_INTERVAL = 24 * 3600


def signature(path):
    path = Path(path)
    try:
        stat = path.stat()
        # SQLite headers include the change counter / WAL generation. Ignore
        # access time, which changes during ordinary read-only report requests.
        with path.open('rb') as stream:
            header = stream.read(100).hex()
        return [stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_ino, header]
    except FileNotFoundError:
        return None


def database_signature(path):
    wal = Path(str(path) + '-wal')
    return [signature(path), signature(wal) if wal.exists() and wal.stat().st_size else None]


def consume(folder, path):
    receipt = folder / 'clean-shutdown.json'
    try:
        value = json.loads(receipt.read_text(encoding='utf-8'))
        # Remove BEFORE any possible database changes; a crash cannot leave a
        # clean receipt behind, even if Windows delays updating a file timestamp.
        receipt.unlink()
        if (isinstance(value,dict) and value.get('version') == VERSION
                and isinstance(value.get('checked_at'),(int,float)) and math.isfinite(value['checked_at'])
                and value.get('database') == database_signature(path)):
            return value
    except (OSError, ValueError, TypeError):
        # Never trust a hint that could not be consumed.
        pass
    return None


def restore_backup_hint(store, receipt):
    if not receipt or not receipt.get('backup'):
        return
    backup = receipt['backup']
    name = backup.get('name', '')
    if Path(name).name != name or not name.startswith('recovery-') or not name.endswith('.sqlite3'):
        return
    path = store.folder / 'backups' / name
    if not backup.get('signature') or signature(path) != backup.get('signature'):
        return
    stat = path.stat()
    store.backup_file = path
    store.backup_signature = (stat.st_size, stat.st_mtime_ns)
    store.backup_revision = store.revision
    store.backup_state.update(backup.get('state', {}))


def save(store, current_backup):
    if store.failure or store.startup_pending:
        return
    receipt = {'version': VERSION, 'database': database_signature(store.path),
               'checked_at': store.checked_at, 'closed_at': time.time(), 'schema_version': store.schema_version}
    if current_backup and store.backup_file:
        receipt['backup'] = {'name': store.backup_file.name,
                             'signature': signature(store.backup_file), 'state': store.backup_state}
    target = store.folder / 'clean-shutdown.json'
    temporary = target.with_suffix('.tmp')
    try:
        with temporary.open('w', encoding='utf-8') as stream:
            json.dump(receipt, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except OSError:
        # Committed records and verified backups are already durable. Failure
        # to save this optional hint only makes the next launch more expensive.
        try:temporary.unlink(missing_ok=True)
        except OSError:pass
