"""Readable PGN rendering from committed records, also used for old tournaments."""
import base64
import json
import re
import time
from functools import lru_cache

import chess
import chess.engine
import chess.pgn

STYLES = ('compact', 'tagged', 'moves', 'archive')


class SafePgnExporter(chess.pgn.StringExporter):
    def visit_header(self, name, value):
        if self.headers:
            self.found_headers = True
            text = re.sub(r'[\x00-\x1f\x7f]', ' ', str(value)).replace('\\', '\\\\').replace('"', '\\"')
            self.write_line(f'[{name} "{text}"]')

    def visit_move(self,board,move):
        if self.variations or not self.variation_depth:
            # Keep the move number attached to its SAN instead of leaving
            # "12..." stranded at the end of a wrapped line.
            prefix=str(board.fullmove_number)+'. ' if board.turn else str(board.fullmove_number)+'... ' if self.force_movenumber else ''
            self.write_token(prefix+board.san(move)+' ')
            self.force_movenumber=False


def number(value):
    return f'{value:.3f}'.rstrip('0').rstrip('.') if isinstance(value, float) else str(value)


def control(tc):
    kind = tc.get('kind', 'fischer')
    seconds = number(tc.get('seconds', 180))
    if kind == 'nodes': return '-', f"{tc['nodes']} nodes/move; no chess clock"
    if kind == 'depth': return '-', f"depth {tc['depth']} plies; no chess clock"
    # PGN's asterisk denotes an hourglass clock, not fixed time per move.
    if kind == 'movetime': return '1/' + seconds, seconds + ' seconds/move'
    if kind == 'fischer': return seconds + '+' + number(tc.get('increment', 0)), 'Fischer'
    if kind in ('delay', 'bronstein'):
        return '?', f"{seconds}s with {number(tc.get('delay', 0))}s {'Bronstein' if kind == 'bronstein' else 'simple'} delay"
    if kind == 'staged':
        stages = [f"{s['moves']}/" if s.get('moves') else '' for s in tc['stages']]
        stages = [prefix + number(s['seconds']) + ('+' + number(s['increment']) if s.get('increment') else '') for prefix, s in zip(stages, tc['stages'])]
        description = ':'.join(stages) + ('; repeat last stage' if tc.get('repeat') else '')
        return ('?' if tc.get('repeat') else ':'.join(stages)), description
    return seconds, 'Sudden death'


def opening_board(opening, chess960):
    """Use only verified recorded history; never invent a route to a FEN."""
    target = chess.Board(opening['fen'], chess960=chess960)
    moves = opening.get('moves') or []
    if not moves: return target, [], ''
    try:
        root = chess.Board(opening.get('start_fen', chess.STARTING_FEN), chess960=chess960)
        board = root.copy()
        for move in moves: board.push_uci(move)
        if board.fen() == target.fen(): return root, list(board.move_stack), ''
    except (ValueError, TypeError):
        pass
    return target, [], 'Recorded opening history could not be verified; game starts from the saved FEN.'


def options(style='compact', perspective='engine', annotations=None):
    if style not in STYLES: raise ValueError('Unknown PGN style')
    if perspective not in ('engine', 'white'): raise ValueError('Unknown score perspective')
    if annotations is not None and set(annotations) - {'eval', 'depth', 'elapsed', 'clock', 'nodes', 'nps', 'seldepth'}:
        raise ValueError('Unknown PGN annotation')
    if style in ('tagged', 'archive'): perspective = 'white'
    return style, perspective, None if annotations is None else set(annotations)


class PgnContext:
    def __init__(self, db, tid):
        self.db = db
        row = db.execute('SELECT name,settings FROM tournaments WHERE id=?', (tid,)).fetchone()
        if row is None: raise ValueError('Tournament not found')
        self.tid, self.name = tid, row[0]
        self.settings = json.loads(row[1])
        self.settings.pop('openings', None)
        # Small cache only; exporting many participants does not retain all profiles.
        self.profile = lru_cache(maxsize=128)(self._profile)

    def _profile(self, slot):
        return json.loads(self.db.execute('SELECT profile FROM participants WHERE tid=? AND slot=?', (self.tid, slot)).fetchone()[0])


def render_attempt(db, aid, style='compact', perspective='engine', annotations=None, context=None, *, export_options=None):
    from .pgn_options import normalize, select_headers
    presentation=normalize(export_options) if export_options is not None else None
    if presentation:
        style,perspective,annotations=(presentation[k] for k in ('style','perspective','annotations'))
    style, perspective, selected = options(style, perspective, annotations)
    def row(sql, args):
        cursor = db.execute(sql, args)
        values = cursor.fetchone()
        if values is None: raise ValueError('Saved game record not found')
        return dict(zip([x[0] for x in cursor.description], values))
    a = row('SELECT * FROM attempts WHERE id=?', (aid,))
    g = row('SELECT * FROM games WHERE id=?', (a['gid'],))
    ctx = context or PgnContext(db, g['tid'])
    s = ctx.settings
    opening = json.loads(g['opening'])
    board, book_moves, history_note = opening_board(opening, s.get('chess960', False))
    pgn = chess.pgn.Game()
    pgn.setup(board)
    white, black = ctx.profile(g['white']), ctx.profile(g['black'])
    identity = json.loads(a['identity'] or '{}')
    reason = a['reason'] or 'unterminated'
    termination = ('unterminated' if (a['result'] or '*') == '*' else
                   'time forfeit' if reason == 'timeout' else
                   'rules infraction' if reason == 'illegal_move' else
                   'adjudication' if 'adjudication' in reason else
                   'abandoned' if reason in ('crash', 'hang', 'startup_timeout', 'readiness_timeout', 'protocol_error') else 'normal')
    date=time.gmtime(a['started']) if presentation and presentation['date_zone']=='utc' else time.localtime(a['started'])
    pgn.headers.update(Event=ctx.name, Site='Engine Arena', Date=time.strftime('%Y.%m.%d', date),
                       Round=str(g['round'] + 1), White=white['name'], Black=black['name'], Result=a['result'] or '*')
    pgn.headers.update({'WhiteEngine': identity.get('white', {}).get('name', white.get('identity', {}).get('name', white['name'])),
        'BlackEngine': identity.get('black', {}).get('name', black.get('identity', {}).get('name', black['name'])),
        'Termination': termination, 'TerminationDetails': reason.replace('_', ' ') + (': ' + a['detail'] if a['detail'] else ''),
        'TournamentId': g['tid'], 'GameId': g['id'], 'AttemptId': aid, 'Attempt': str(a['seq']), 'AttemptMode': a['mode'],
        'OpeningPair': str(g['pair_no']), 'OpeningLeg': str(g['leg']), 'Opening': opening.get('name', 'FEN'),
        'OpeningSeed': str(opening.get('seed', '')), 'BookPlyCount': str(len(book_moves)),
        'CompetitionStage': opening.get('competition_stage', 'regular')})
    if presentation:
        pgn.headers['GameNumber']=str(g['number']+1)
        pgn.headers['UTCDate']=time.strftime('%Y.%m.%d',time.gmtime(a['started']))
        pgn.headers['UTCTime']=time.strftime('%H:%M:%S',time.gmtime(a['started']))
        from .report_evidence import filename
        if s.get('opening_source',{}).get('name'):pgn.headers['OpeningBook']=filename(s['opening_source']['name'])
        if presentation['event']:pgn.headers['Event']=presentation['event']
        if presentation['site']:pgn.headers['Site']=presentation['site']
        if presentation['names']=='engine':
            pgn.headers['White']=pgn.headers['WhiteEngine'];pgn.headers['Black']=pgn.headers['BlackEngine']
    if opening.get('selection') is not None:pgn.headers['OpeningPosition']=str(opening['selection']+1)
    if opening.get('assignment') is not None:pgn.headers['OpeningAssignment']=str(opening['assignment']+1)
    if opening.get('ko_opening_progression'):pgn.headers['OpeningPolicy']='KO shared sequence; new opening per pair' if s['paired'] else 'KO shared sequence; new opening per game'
    if opening.get('eco'): pgn.headers['ECO'] = opening['eco']
    if opening.get('variation'): pgn.headers['Variation'] = opening['variation']
    if opening.get('playoff_stage') is not None:pgn.headers['PlayoffStage']=str(opening['playoff_stage'])
    from .knockout import game_control
    controls = {};raw_controls={}
    for side, profile in (('White', white), ('Black', black)):
        book=profile.get('move_book') if s.get('use_engine_books',True) else None
        if book:
            for key,value in (('Book',book['name']),('BookSHA256',book['id']),('BookPolicy',book['policy']),('BookMaxPly',book['max_plies'])):pgn.headers[side+key]=str(value)
        tc = game_control(s,profile,opening)
        raw_controls[side]=tc
        controls[side] = control(tc)
        pgn.headers[side + 'TimeControl'] = controls[side][0]
        pgn.headers[side + 'SearchControl'] = controls[side][1]
        for option, fallback in (('Threads', 1), ('Hash', 1024)):
            from .report_evidence import configured_option
            value = configured_option(profile,option,fallback)
            pgn.headers[side + ('HashMB' if option == 'Hash' else option)] = str(value)
        if profile.get('gpu_group'):pgn.headers[side+'GPUGroup']=profile['gpu_group']
        cache=next((v for k,v in profile.get('options',{}).items() if k.casefold()=='nncachesize'),None)
        if cache is not None:pgn.headers[side+'NNCachePositions']=str(cache)
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='attempt_engines'").fetchone():
        for side,encoded in db.execute('SELECT x.side,e.body FROM attempt_engines x JOIN engine_evidence e ON e.id=x.evidence WHERE x.aid=?',(aid,)):
            observed=json.loads(encoded);prefix=side.title()
            from .report_evidence import filename
            if observed.get('network_file'):pgn.headers[prefix+'Network']=filename(observed['network_file'])
            if observed.get('network',{}).get('sha256'):pgn.headers[prefix+'NetworkSHA256']=observed['network']['sha256']
            if observed.get('backend'):pgn.headers[prefix+'Backend']=observed['backend']
            if observed.get('gpu'):pgn.headers[prefix+'GPU']=observed['gpu']
    pgn.headers['TimeControl'] = controls['White'][0] if controls['White'] == controls['Black'] else '?'
    pgn.headers['Ponder'] = 'true' if s.get('ponder') else 'false'
    if 'OpeningPolicy' not in pgn.headers:pgn.headers['OpeningPolicy'] = s.get('opening_policy', 'legacy')
    if history_note: pgn.headers['OpeningHistory'] = history_note
    if style != 'moves': pgn.headers['ScorePerspective'] = 'White' if perspective == 'white' else 'Moving engine'
    settings_headers=set(presentation['headers']) if presentation else {'WhiteSettings','BlackSettings','TournamentSettings'} if style=='archive' else set()
    if settings_headers.intersection(('WhiteSettings','BlackSettings','TournamentSettings')):
        pgn.headers['SettingsEncoding'] = 'base64-json-utf8'
        for key, value in (('WhiteSettings', white), ('BlackSettings', black), ('TournamentSettings', s)):
            if key in settings_headers:pgn.headers[key] = base64.b64encode(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()).decode()
    node = pgn
    book_comments=presentation['book_comments'] if presentation else 'all'
    for index,move in enumerate(book_moves):
        node = node.add_variation(move)
        if book_comments=='all':node.comment = 'book'
        elif book_comments=='boundary' and index==len(book_moves)-1:node.comment='End of opening book'
        board.push(move)
    if selected is None:
        selected = ({'eval', 'depth', 'elapsed'} if style == 'compact' else {'eval', 'depth', 'elapsed', 'clock', 'nodes', 'nps', 'seldepth'}) if s.get('annotations', True) else set()
    if style == 'moves': selected = set()
    cursor = db.execute('SELECT uci,elapsed,clocks,info FROM moves WHERE aid=? ORDER BY ply', (aid,))
    for uci, elapsed, clocks_json, info_json in cursor:
        color = board.turn
        move = board.parse_uci(uci)
        node = node.add_variation(move)
        board.push(move)
        from .telemetry import clean
        info, clocks = clean(json.loads(info_json),elapsed), json.loads(clocks_json)
        if info.get('source')=='book':
            if style!='moves' and book_comments!='none':node.comment='Book: '+info.get('book_name','')
            if 'clock' in selected:
                remaining=clocks.get('white' if color else 'black',{}).get('remaining')
                if remaining is not None:node.set_clock(max(0,remaining))
            continue
        if style == 'compact':
            score = ''
            sign = 1 if perspective == 'white' or color else -1
            if 'eval' in selected:
                if 'mate' in info:
                    value = info['mate'] * sign
                    score = ('-' if value < 0 else '+' if value > 0 else '') + 'M' + str(abs(value))
                elif 'cp' in info: score = f"{info['cp'] * sign / 100:+.2f}"
            if 'depth' in selected and 'depth' in info: score = score + '/' + str(info['depth']) if score else 'depth ' + str(info['depth'])
            parts = [score] if score else []
            if 'elapsed' in selected: parts.append(number(round(elapsed, 3)) + 's')
            for key in ('nodes', 'nps', 'seldepth'):
                if key in selected and key in info: parts.append(f'{key} {info[key]}')
            node.comment = ' '.join(parts)
        else:
            if 'eval' in selected:
                score = chess.engine.Mate(info['mate']) if 'mate' in info else chess.engine.Cp(info['cp']) if 'cp' in info else None
                if score is not None: node.set_eval(chess.engine.PovScore(score, chess.WHITE), info.get('depth') if 'depth' in selected else None)
            if 'depth' in selected and 'depth' in info and not node.eval(): node.comment += f" [%depth {info['depth']}]"
            if 'elapsed' in selected: node.set_emt(round(elapsed, 3))
            for key in ('nodes', 'nps', 'seldepth'):
                if key in selected and key in info: node.comment += f' [%{key} {info[key]}]'
        if 'clock' in selected:
            remaining = clocks.get('white' if color else 'black', {}).get('remaining')
            if remaining is not None: node.set_clock(max(0, remaining))
        node.comment = node.comment.strip()
    pgn.headers['PlyCount'] = str(sum(1 for _ in pgn.mainline()))
    if presentation:
        # FEN, variant, exceptional controls and annotation perspective must
        # remain interpretable even with a deliberately small header selection.
        needs_controls=controls['White']!=controls['Black'] or any(tc.get('kind') in ('nodes','depth','movetime','delay','bronstein') or tc.get('repeat') for tc in raw_controls.values())
        kept=select_headers(pgn.headers,presentation,needs_controls=needs_controls,
                            has_evaluation='eval' in selected,has_timing=bool(selected.intersection(('clock','elapsed'))))
        from .pgn_options import REQUIRED
        pgn.headers.clear()
        pgn.headers.update({key:kept[key] for key in (*REQUIRED,*sorted(set(kept)-set(REQUIRED))) if key in kept})
    return pgn.accept(SafePgnExporter(columns=presentation['columns'] if presentation else 100)) + '\n\n'
