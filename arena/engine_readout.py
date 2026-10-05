from .i18n import t as _t,h as _h,number as _number
"""Bounded-memory search summaries from a committed report snapshot.

Read each selected official attempt's moves once, including both engine sides.
Never infer historical hardware or attribute system-wide sensors to a process.
"""
from dataclasses import asdict
import json
import math

from .knockout import game_control
from .models import TimeControl
from .report_evidence import FAILURES, filename

# Installed only in the isolated report worker. Ordinary callers remain pure.
progress = lambda done, total: None


METRICS = (
    ('elapsed', 'Measured thinking time (s)', 4),
    ('time', 'Engine-reported search time (s)', 4),
    ('depth', 'Depth (plies)', 2),
    ('seldepth', 'Selective depth (plies)', 2),
    ('nodes', 'Reported search nodes', 0),
    ('nps', 'Engine-reported NPS', 0),
    ('hashfull', 'Reported hash occupancy (%)', 2),
    ('tbhits', 'Reported tablebase hits', 0),
    ('remaining', 'Clock after move (s)', 4),
)


def numeric(value, minimum=0, maximum=None):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and (minimum is None or value >= minimum)
            and (maximum is None or value <= maximum))


def add(bucket, key, value):
    item = bucket['metrics'].setdefault(key, {'count': 0, 'sum': 0, 'min': value, 'max': value})
    item['count'] += 1
    item['sum'] += value
    item['min'] = min(item['min'], value)
    item['max'] = max(item['max'], value)


def collect(view, tid, settings, displayed, sessions):
    profiles = {x['rank']['slot']: x['profile'] for x in displayed}
    output = {slot: [] for slot in profiles}
    if not profiles:
        return output
    tables = {r['name'] for r in view.rows("SELECT name FROM sqlite_master WHERE type='table'")}
    linked = {'run_attempts', 'attempt_engines', 'engine_evidence'} <= tables
    fields = 'ra.sid,ew.body white_evidence,eb.body black_evidence' if linked else 'NULL sid,NULL white_evidence,NULL black_evidence'
    joins = '''LEFT JOIN run_attempts ra ON ra.aid=a.id
        LEFT JOIN attempt_engines xw ON xw.aid=a.id AND xw.side='white'
        LEFT JOIN attempt_engines xb ON xb.aid=a.id AND xb.side='black'
        LEFT JOIN engine_evidence ew ON ew.id=xw.evidence
        LEFT JOIN engine_evidence eb ON eb.id=xb.evidence''' if linked else ''
    query = '''SELECT g.white,g.black,g.opening,a.id aid,a.result,a.reason,'''+fields+'''
        FROM games g JOIN attempts a ON a.id=g.official '''+joins+'''
        WHERE g.tid=? AND g.invalid=0 AND
        (g.white IN (SELECT value FROM json_each(?)) OR g.black IN (SELECT value FROM json_each(?)))
        ORDER BY g.number'''
    slots = json.dumps(list(profiles))
    grouped = {}
    session_map = {s['id']: i for i, s in enumerate(sessions, 1)}
    total=view.one('SELECT coalesce(sum(n),0) n FROM game_counts WHERE tid=? AND invalid=0 AND has_official=1',(tid,))['n']
    done=0
    progress(done,total)
    for row in view.db.execute(query, (tid, slots, slots)):
        opening = json.loads(row['opening'])
        first_white = opening['fen'].split()[1] == 'w'
        sides = {}
        for side in ('white', 'black'):
            slot = row[side]
            if slot not in profiles:
                continue
            control = asdict(TimeControl.parse(game_control(settings, profiles[slot], opening)))
            phase = 'Tiebreaks' if opening.get('competition_stage') == 'playoff' else 'Regular games'
            # Keep different observed configurations/networks separate, even
            # when the saved profile, time control and machine are unchanged.
            observation = row[side+'_evidence'] or '{}'
            key = (slot, row['sid'], phase, json.dumps(control, sort_keys=True), observation)
            if key not in grouped:
                b = {'control': control, 'clocked': TimeControl.parse(control).clocked, 'phase': phase, 'session': session_map.get(row['sid']),
                     'observation': json.loads(observation), 'games': 0, 'white': 0, 'black': 0,
                     'wins': 0, 'draws': 0, 'losses': 0, 'moves': 0, 'metrics': {},
                     'failures': {}, 'timed_nodes': 0, 'timed_seconds': 0, 'timed_moves': 0,
                     'reported_nodes': 0, 'reported_seconds': 0, 'reported_moves': 0,
                     'low_clock': 0, 'negative_clock': 0, 'cp_moves': 0, 'mate_moves': 0,
                     'wdl_moves': 0, 'invalid_values': 0}
                grouped[key] = b
                output[slot].append(b)
            b = sides[side] = grouped[key]
            b['games'] += 1
            b[side] += 1
            won = row['result'] == ('1-0' if side == 'white' else '0-1')
            lost = row['result'] == ('0-1' if side == 'white' else '1-0')
            b['wins' if won else 'losses' if lost else 'draws'] += 1
            if lost and row['reason'] in FAILURES:
                b['failures'][row['reason']] = b['failures'].get(row['reason'], 0) + 1
        for m in view.db.execute('SELECT ply,elapsed,clocks,info FROM moves WHERE aid=? ORDER BY ply', (row['aid'],)):
            side = 'white' if (m['ply'] % 2 == 1) == first_white else 'black'
            if side not in sides:
                continue
            b = sides[side]
            from .telemetry import clean
            info = clean(json.loads(m['info'] or '{}'),m['elapsed'])
            b['invalid_values'] += len(info.get('invalid_metrics',{}))
            if info.get('source')=='book':
                b['book_moves']=b.get('book_moves',0)+1;continue
            b['moves'] += 1
            elapsed = m['elapsed']
            if numeric(elapsed):
                add(b, 'elapsed', elapsed)
            for key in ('depth', 'seldepth', 'nodes', 'nps', 'time', 'hashfull', 'tbhits'):
                value = info.get(key)
                if numeric(value, maximum=1000 if key == 'hashfull' else None):
                    add(b, key, value / 1000 if key == 'time' else value / 10 if key == 'hashfull' else value)
                elif key in info:
                    b['invalid_values'] += 1
            nodes = info.get('nodes')
            if numeric(nodes) and numeric(elapsed) and elapsed > 0:
                b['timed_nodes'] += nodes
                b['timed_seconds'] += elapsed
                b['timed_moves'] += 1
            reported = info.get('time')
            if numeric(nodes) and numeric(reported) and reported > 0:
                b['reported_nodes'] += nodes
                b['reported_seconds'] += reported / 1000
                b['reported_moves'] += 1
            clock = json.loads(m['clocks'] or '{}').get(side, {}) if b['clocked'] else {}
            remaining = clock.get('remaining')
            if b['clocked'] and numeric(remaining, minimum=None):
                add(b, 'remaining', remaining)
                b['low_clock'] += remaining <= 1
                b['negative_clock'] += remaining < 0
            b['cp_moves'] += numeric(info.get('cp'), minimum=None)
            b['mate_moves'] += numeric(info.get('mate'), minimum=None)
            wdl = info.get('wdl')
            b['wdl_moves'] += (isinstance(wdl, list) and len(wdl) == 3
                               and all(numeric(v, maximum=1000) for v in wdl) and sum(wdl) == 1000)
        done+=1
        if done%128==0:progress(done,total)
    progress(done,done)
    return output


def formatted(value, digits=2):
    return _number(value,digits) if value is not None else _t('Not reported')


def section(groups, evidence, esc, table, time_description):
    body = _h('<section data-report-technical><h4>Engine technical readout</h4>')
    if not groups:
        return body+_h('<p>No completed official games for this engine yet.</p></section>')
    for index, b in enumerate(groups, 1):
        sid = b['session']
        session = evidence['sessions'][sid-1] if sid else None
        data = session['body'] if session else {}
        hardware = data.get('hardware', {})
        resources = data.get('resources', {})
        observation = b['observation']
        rows = [(_t('Time control'), time_description(b['control'])),
                (_t('Hardware session'), _t('Run session {0}' ,f'{sid}') if sid else _t('Not recorded; current hardware is not substituted')),
                ('CPU', hardware.get('cpu', _t('Not recorded'))),
                (_t('Physical cores / logical processors'), f"{hardware.get('physical_cores', 'N/A')} / {hardware.get('logical_processors', 'N/A')}"),
                (_t('Installed RAM (GiB)'), formatted(hardware.get('ram_gib'), 1)),
                (_t('Session CPU thread budget'), resources.get('cpu_threads', _t('Not recorded'))),
                (_t('Initial session game limit'), resources.get('game_limit', _t('Not recorded'))),
                (_t('GPU reported by engine'), observation.get('gpu', _t('Not identified'))),
                (_t('Engine configuration'), _t('Observed settings shown below') if observation.get('options') else _t('No per-attempt options recorded; saved profile above')),
                (_t('Game appearances (White / Black)'), f"{b['games']:,} ({b['white']:,} / {b['black']:,})"),
                (_t('W-D-L in this group'), f"{b['wins']}–{b['draws']}–{b['losses']}"),
                (_t('Legal engine moves sampled'), f"{b['moves']:,}"),
                (_t('Profile book moves (excluded from search metrics)'),b.get('book_moves',0)),
                (_t('Engine-attributed forfeits'), '; '.join(f'{k.replace("_", " ")}: {v}' for k, v in sorted(b['failures'].items())) or _t('None'))]
        for key in ('Threads', 'Hash', 'MultiPV', 'NNCacheSize'):
            value = next((v for k, v in observation.get('options', {}).items() if k.casefold() == key.casefold()), None)
            if value is not None:
                rows.append((_t('Observed ')+key+(_t(' (MB)') if key == 'Hash' else _t(' (positions)') if key == 'NNCacheSize' else ''), value))
        for key, label in (('network_file', _t('Loaded network')), ('backend', _t('Backend'))):
            if observation.get(key):
                rows.append((label, filename(observation[key]) if key == 'network_file' else observation[key]))
        if observation.get('network', {}).get('sha256'):
            rows.append((_t('Network SHA-256'), observation['network']['sha256']))
        body += _h('<h5>')+esc(_t('Readout {0} · {1}' ,f'{index}',f"{_t(b['phase'])}"))+'</h5>'+table([_t('Readout condition'), _t('Value')], rows)
        metric_rows = []
        for key, name, digits in METRICS:
            m = b['metrics'].get(key)
            metric_rows.append((_t(name), f"{m['count'] if m else 0:,} / {b['moves']:,}",
                                *([formatted(m['sum']/m['count'], digits), formatted(m['min'], digits), formatted(m['max'], digits)] if m else [_t('Not reported')]*3)))
        body += table([_t('Search measurement'), _t('Moves with data'), _t('Average'), _t('Minimum'), _t('Maximum')], metric_rows)
        totals = [(_t('Measured thinking time, summed (s)'), formatted(b['metrics'].get('elapsed', {}).get('sum'), 4)),
                  (_t('Reported search nodes, summed'), formatted(b['metrics'].get('nodes', {}).get('sum'), 0)),
                  (_t('Nodes / measured search second'), formatted(b['timed_nodes']/b['timed_seconds'], 0) if b['timed_seconds'] else _t('Unavailable')),
                  (_t('Moves in measured-rate calculation'), f"{b['timed_moves']:,} / {b['moves']:,}"),
                  (_t('Nodes / engine-reported second'), formatted(b['reported_nodes']/b['reported_seconds'], 0) if b['reported_seconds'] else _t('Unavailable')),
                  (_t('Moves in reported-rate calculation'), f"{b['reported_moves']:,} / {b['moves']:,}"),
                  (_t('Clock at or below 1 s after move'), b['low_clock'] if b['metrics'].get('remaining') else _t('No clock readings')),
                  (_t('Negative clock after move'), b['negative_clock'] if b['metrics'].get('remaining') else _t('No clock readings')),
                  (_t('Evaluation coverage (cp / mate / WDL)'), _t('{0} / {1} / {2} moves' ,f"{b['cp_moves']:,}",f"{b['mate_moves']:,}",f"{b['wdl_moves']:,}"))]
        if b['invalid_values']:
            totals.append((_t('Malformed metric values excluded'), b['invalid_values']))
        body += table([_t('Search summary'), _t('Value')], totals)
    return body+'</section>'
