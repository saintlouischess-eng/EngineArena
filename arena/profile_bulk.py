"""Previewed, transactional library changes. Tournament snapshots are untouched."""
import copy
import hashlib
import json
import chess.engine

from .engine_options import find_name
from .uci import validated_options


def bulk(store, body):
    ids = body.get('ids', [])
    if not isinstance(ids, list) or not ids or any(not isinstance(p, str) for p in ids):
        raise ValueError('Select engine profiles first.')
    ids = sorted(set(ids))
    if body.get('catalog'):
        counts = {};missing=[]
        for row in store.rows('SELECT body FROM profiles WHERE id IN (SELECT value FROM json_each(?))', (json.dumps(ids),)):
            p=json.loads(row['body'])
            if 'advertised' not in p:missing.append({'id':p['id'],'name':p['name']})
            for name, opt in p.get('advertised', {}).items():
                if opt['type'] != 'button':counts[name] = counts.get(name, 0)+1
        return {'options': sorted(counts), 'counts': counts,'missing':missing}
    patch = body.get('patch', {})
    if not isinstance(patch, dict) or not patch or set(patch) - {'threads', 'hash', 'options', 'move_book', 'time_control'}:
        raise ValueError('Select at least one supported bulk change.')
    options = patch.get('options', {})
    if not isinstance(options, dict):raise ValueError('UCI options must be a name/value object.')
    for key in options:
        if key.casefold() in ('ponder', 'uci_chess960', 'uci_variant'):
            raise ValueError('Ponder and variant are controlled by the tournament.')
        if find_name([key], 'threads') or key.casefold() == 'hash':
            raise ValueError('Use the Threads and Hash fields for resource options.')
    prepared = []; entries = []; originals = []; changed = skipped = 0
    # The preview and commit share the same validation, including engine ranges.
    with store.tx(report_change=False):
        for pid in ids:
            row = store.one('SELECT body FROM profiles WHERE id=?', (pid,))
            if not row:raise ValueError('An engine profile no longer exists; refresh the library')
            originals.append([pid, row['body']])
            old = json.loads(row['body']); p = copy.deepcopy(old)
            changes = []; warnings = []
            def option(name, value, resource=None):
                nonlocal skipped
                advertised = p.get('advertised', {})
                actual = find_name(advertised, name)
                # Resource budgets can be set even for an undiscovered profile,
                # but cannot claim to configure an unadvertised UCI option.
                if actual is None:
                    skipped += 1;warnings.append(f'{name}: discover options first' if 'advertised' not in p else f'{name}: not advertised')
                    return
                if advertised[actual]['type'] == 'button':
                    skipped += 1;warnings.append(f'{name}: button options cannot be saved');return
                try:
                    kind=advertised[actual]['type']
                    if kind=='check' and value not in (True,False,'true','false'):raise ValueError('Use true or false for a checkbox option.')
                    if kind=='spin' and (isinstance(value,bool) or str(value).strip().lstrip('-').isdigit() is False):raise ValueError('Use a whole number for a numeric option.')
                    value = validated_options({actual: value}, advertised)[actual]
                    if resource and (isinstance(value, bool) or int(value) < 1):raise ValueError('Use a positive whole number')
                except (ValueError, TypeError, chess.engine.EngineError) as e:
                    skipped += 1;warnings.append(f'{name}: {e}');return
                p.setdefault('options', {})
                for alias in list(p['options']):
                    if find_name([alias], name):p['options'].pop(alias)
                p['options'][actual] = value
                if resource:p[resource] = int(value)
                old_key=find_name(old.get('options',{}),name)
                changes.append({'field': actual, 'before': old.get('options', {}).get(old_key, advertised[actual].get('default')), 'after': value})
            for resource in ('threads', 'hash'):
                if resource in patch:
                    value = patch[resource]
                    if isinstance(value, bool) or not isinstance(value, int) or value < 1:raise ValueError('Use positive whole resource values.')
                    option(resource, value, resource)
            for key, value in options.items():option(key, value)
            if 'time_control' in patch:
                if patch['time_control'] is None:p.pop('time_control', None)
                else:p['time_control'] = copy.deepcopy(patch['time_control'])
                changes.append({'field': 'time_control', 'before': old.get('time_control'), 'after': p.get('time_control')})
            if 'move_book' in patch:
                book = patch['move_book']
                if book is None:p['move_book'] = None
                elif isinstance(book, dict) and not set(book) - {'id', 'policy', 'max_plies'}:
                    if not book.get('id') and not p.get('move_book'):
                        warnings.append('move_book: no existing book');skipped += 1
                    else:p['move_book'] = {**(p.get('move_book') or {}), **book}
                else:raise ValueError('Invalid engine move book change.')
                changes.append({'field': 'move_book', 'before': old.get('move_book'), 'after': p.get('move_book')})
            p = store.validate_profile(p)
            changes = [c for c in changes if c['before'] != c['after']]
            if p != old:prepared.append(p);changed += 1
            entries.append({'id': pid, 'name': p['name'], 'changes': changes, 'warnings': warnings})
        signature = hashlib.sha256(json.dumps([originals, patch], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        if body.get('apply'):
            if body.get('signature') != signature:raise ValueError('Profiles changed after preview. Review the changes again.')
            store.db.executemany('UPDATE profiles SET name=?,body=? WHERE id=?',
                ((p['name'], json.dumps(p, ensure_ascii=False, allow_nan=False), p['id']) for p in prepared))
            store.audit(None, 'bulk_profiles', {'ids': [p['id'] for p in prepared], 'fields': list(patch)})
    offset = max(0, int(body.get('offset', 0)))
    return {'signature': signature, 'total': len(ids), 'changed': changed, 'skipped': skipped,
            'items': entries[offset:offset+50], 'offset': offset, 'applied': bool(body.get('apply'))}
