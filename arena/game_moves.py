"""Bounded, committed scoresheets. Never load engine logs or instantiate Store."""
import json
from pathlib import Path
import sqlite3
from functools import lru_cache
import chess
from .telemetry import clean
from .pgn_format import opening_board
from .crown_marks import CrownMarks


@lru_cache(maxsize=64)
def tournament_variant(path,tid):
    # Conditions are immutable once games exist; avoid parsing large opening
    # inventories on every committed-move poll.
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=10)
    try:return bool(db.execute("SELECT json_extract(settings,'$.chess960') FROM tournaments WHERE id=?",(tid,)).fetchone()[0])
    finally:db.close()


def read_moves(path, gid, aid=None, after=0, limit=200):
    after=int(after);limit=int(limit)
    if after < 0 or not 1 <= limit <= 500:raise ValueError('Invalid move page')
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=10)
    db.row_factory=sqlite3.Row
    try:
        db.execute('BEGIN')
        row=db.execute('SELECT * FROM games WHERE id=?',(gid,)).fetchone()
        if not row:raise ValueError('Game no longer exists')
        g=dict(row);opening=json.loads(g.pop('opening'))
        if aid:
            a=db.execute('SELECT * FROM attempts WHERE gid=? AND id=?',(gid,aid)).fetchone()
            if not a:raise ValueError('Attempt does not belong to this game')
        else:
            # The latest attempt can be a diagnostic or replacement. Label it;
            # never silently present an old official attempt as a live replay.
            a=db.execute('SELECT * FROM attempts WHERE gid=? ORDER BY seq DESC LIMIT 1',(gid,)).fetchone()
        attempt=dict(a) if a else None
        if attempt:
            attempt={k:attempt[k] for k in ('id','seq','mode','started','ended','result','reason','clocks')}
            attempt['clocks']=json.loads(attempt['clocks'] or '{}')
            attempt['official']=attempt['id']==g['official'] and not g['invalid']
        variant=tournament_variant(str(path),g['tid'])
        root,history,warning=opening_board(opening,variant)
        marks=CrownMarks(root)
        opening_rows=[]
        for i,move in enumerate(history):
            if after==0:
                item={'ply':i-len(history)+1,'label':str(root.fullmove_number)+('.' if root.turn else '…'),
                      'side':'white' if root.turn else 'black','san':root.san(move),'uci':move.uci(),
                      'elapsed':None,'info':{'source':'opening'},'clocks':{}}
            marks.advance(root,move);root.push(move)
            if after==0:
                item.update(fen=root.fen(),crown_squares=marks.snapshot(),knight_facings=marks.knight_snapshot(),captured=marks.capture_snapshot());opening_rows.append(item)
        initial_marks=marks.snapshot();initial_knights=marks.knight_snapshot();initial_captured=marks.capture_snapshot()
        board=chess.Board(opening['fen'],chess960=variant)
        replay=board.copy(stack=False)
        latest=0;items=[]
        if attempt:
            latest=db.execute('SELECT coalesce(max(ply),0) FROM moves WHERE aid=?',(attempt['id'],)).fetchone()[0]
            # Only this attempt's compact moves are read, never tournament logs.
            # Rebuild identity at page boundaries so late pages and old games work.
            for r in db.execute('SELECT uci FROM moves WHERE aid=? AND ply<=? ORDER BY ply',(attempt['id'],after)):
                try:
                    move=replay.parse_uci(r['uci']);marks.advance(replay,move);replay.push(move)
                except ValueError:
                    marks.clear();break
            for r in db.execute('SELECT ply,uci,san,fen,elapsed,clocks,info FROM moves WHERE aid=? AND ply>? ORDER BY ply LIMIT ?', (attempt['id'],after,limit)):
                item=dict(r);index=(0 if board.turn else 1)+item['ply']-1
                item.update(label=str(board.fullmove_number+index//2)+('.' if index%2==0 else '…'),side='white' if index%2==0 else 'black',clocks=json.loads(item['clocks']),info=clean(json.loads(item['info']),item['elapsed']))
                try:
                    move=replay.parse_uci(item['uci']);marks.advance(replay,move);replay.push(move)
                    if replay.fen()!=item['fen']:marks.clear()
                except ValueError:marks.clear()
                item['crown_squares']=marks.snapshot()
                item['knight_facings']=marks.knight_snapshot()
                item['captured']=marks.capture_snapshot()
                items.append(item)
        profiles={side:{'name':db.execute("SELECT json_extract(profile,'$.name') FROM participants WHERE tid=? AND slot=?",(g['tid'],g[side])).fetchone()[0]} for side in ('white','black')}
        # Return display identity only, not executable paths or full profile options.
        return {'game':g['id'],'tid':g['tid'],'number':g['number'],'state':g['state'],'invalid':bool(g['invalid']),
                'white':{'name':profiles['white']['name']},'black':{'name':profiles['black']['name']},
                'opening':opening,'opening_moves':opening_rows,'opening_crown_squares':initial_marks,'opening_knight_facings':initial_knights,'opening_captured':initial_captured,'warning':warning,'attempt':attempt,
                'latest_ply':latest,'after':after,'items':items,'has_more':bool(items and items[-1]['ply']<latest)}
    finally:db.close()


def completion(path,tid):
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=10);db.row_factory=sqlite3.Row
    try:
        db.execute('BEGIN')
        t=db.execute('SELECT state,total,note FROM tournaments WHERE id=?',(tid,)).fetchone()
        if not t:raise ValueError('Tournament no longer exists')
        result=dict(t)
        result['failures']=[dict(r) for r in db.execute('SELECT reason,sum(attempts) attempts,sum(official) official FROM engine_failures WHERE tid=? GROUP BY reason',(tid,))]
        last=db.execute('SELECT id FROM games WHERE tid=? AND official IS NOT NULL AND invalid=0 ORDER BY number DESC LIMIT 1',(tid,)).fetchone()
        result['last_game']=last[0] if last else None
        return result
    finally:db.close()


def presentation(path, gid):
    """Small read-only nameplate snapshot; no move/log scans or rating writes."""
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=5)
    db.row_factory=sqlite3.Row
    try:
        db.execute('BEGIN')
        g=db.execute('SELECT tid,white,black FROM games WHERE id=?',(gid,)).fetchone()
        if not g:raise ValueError('Game no longer exists')
        t=db.execute('SELECT name FROM tournaments WHERE id=?',(g['tid'],)).fetchone()
        row=db.execute('SELECT w,d,l FROM aggregates WHERE tid=? AND a=? AND b=?',(g['tid'],g['white'],g['black'])).fetchone()
        return {'game':gid,'event':t['name'],'score':None if not row or g['white']==g['black'] else [row['w']+row['d']/2,row['l']+row['d']/2]}
    finally:db.close()
