"""A durable unsaved setup, independent of browser origin and workspace prefs."""
import json


def draft(store, body=None):
    with store.tx(report_change=False):
        row = store.one("SELECT body FROM preferences WHERE name='tournament_draft'")
        current = json.loads(row['body']) if row else {'revision': 0, 'value': None}
        if body is None:return current
        if body.get('revision') != current['revision']:
            raise ValueError('The setup draft changed in another window. Reopen tournament setup before editing it.')
        value = body.get('value')
        if value is not None and (not isinstance(value, dict) or value.get('version') != 1):raise ValueError('Invalid tournament draft.')
        current = {'revision': current['revision']+1, 'value': value}
        store.db.execute("INSERT INTO preferences VALUES('tournament_draft',?) ON CONFLICT(name) DO UPDATE SET body=excluded.body", (json.dumps(current, ensure_ascii=False, allow_nan=False),))
        return current


def gauntlet_profiles(profiles, candidate_ids, settings):
    if candidate_ids is None or settings.get('format') != 'gauntlet':return profiles
    if not isinstance(candidate_ids, list) or any(not isinstance(i, str) for i in candidate_ids):raise ValueError('Choose named gauntlet candidates.')
    chosen = set(candidate_ids); known = {p['id'] for p in profiles}
    if (not chosen or len(chosen) != len(candidate_ids) or not chosen < known or
            len(chosen) != settings.get('candidates') or len(known) != len(profiles)):
        raise ValueError('Choose at least one candidate and one opponent from the tournament participants.')
    return [p for p in profiles if p['id'] in chosen] + [p for p in profiles if p['id'] not in chosen]
