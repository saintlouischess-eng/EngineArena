"""Validated reusable conditions and editable starting positions."""
from dataclasses import asdict
import json
import chess
from .models import TimeControl

def preset_settings(value):
    if not isinstance(value,dict):raise ValueError('Preset settings must be an object')
    result=dict(value);result['time_control']=asdict(TimeControl.parse(value.get('time_control')))
    for key,default in (('threads',1),('hash',1024)):
        n=value.get(key,default)
        if not isinstance(n,int) or isinstance(n,bool) or n<1:raise ValueError(key+' must be a positive integer')
        result[key]=n
    for key,default in (('paired',True),('ponder',False)):
        if not isinstance(value.get(key,default),bool):raise ValueError(key+' must be true or false')
        result[key]=value.get(key,default)
    return result

def save_preset(store,name,value,original=None):
    name=str(name).strip()
    if not name:raise ValueError('Enter a preset name')
    result=preset_settings(value)
    with store.tx():
        if original is not None and not store.one('SELECT name FROM presets WHERE name=?',(original,)):raise ValueError('Original preset no longer exists')
        if name!=original and store.one('SELECT name FROM presets WHERE name=?',(name,)):raise ValueError('That name already exists. Edit that preset or choose another name.')
        store.db.execute('INSERT OR REPLACE INTO presets VALUES(?,?)',(name,json.dumps(result)))
        # Renaming creates a new name while retaining the original as a reusable
        # copy; existing tournament snapshots never change.
    return {'name':name,'settings':result}

def position(value):
    if not isinstance(value,dict):raise ValueError('Position must be an object')
    variant=value.get('chess960',False)
    if not isinstance(variant,bool):raise ValueError('Chess960 must be true or false')
    if 'chess960_index' in value:
        n=value['chess960_index']
        if not isinstance(n,int) or isinstance(n,bool) or not 0<=n<960:raise ValueError('Chess960 start number must be 0–959')
        board=chess.Board.from_chess960_pos(n);variant=True
    else:
        fen=value.get('fen',chess.STARTING_FEN)
        if not isinstance(fen,str):raise ValueError('FEN must be text')
        fields=fen.split()
        if len(fields)!=6:raise ValueError('FEN must contain all six fields')
        if not fields[4].isdigit() or not fields[5].isdigit() or int(fields[5])<1:raise ValueError('Halfmove clock must be non-negative; fullmove number must be positive')
        board=chess.Board(fen,chess960=variant)
    status=board.status()
    errors=[label for flag,label in (
        (chess.STATUS_NO_WHITE_KING,'White king is missing'),(chess.STATUS_NO_BLACK_KING,'Black king is missing'),
        (chess.STATUS_TOO_MANY_KINGS,'Too many kings'),(chess.STATUS_TOO_MANY_WHITE_PAWNS,'Too many White pawns'),
        (chess.STATUS_TOO_MANY_BLACK_PAWNS,'Too many Black pawns'),(chess.STATUS_PAWNS_ON_BACKRANK,'Pawns on a back rank'),
        (chess.STATUS_TOO_MANY_WHITE_PIECES,'Too many White pieces'),(chess.STATUS_TOO_MANY_BLACK_PIECES,'Too many Black pieces'),
        (chess.STATUS_BAD_CASTLING_RIGHTS,'Castling rights do not match the king and rook squares'),
        (chess.STATUS_INVALID_EP_SQUARE,'Invalid en-passant square'),(chess.STATUS_OPPOSITE_CHECK,'The side that just moved is in check'),
        (chess.STATUS_TOO_MANY_CHECKERS,'Too many checking pieces'),(chess.STATUS_IMPOSSIBLE_CHECK,'Impossible check arrangement'),
        (chess.STATUS_EMPTY,'The board is empty')) if status&flag]
    return {'fen':board.fen(shredder=variant,en_passant='fen'),'chess960':variant,'valid':board.is_valid(),'errors':errors,
      'legal_moves':[{'uci':board.uci(m),'san':board.san(m)} for m in board.legal_moves] if board.is_valid() else [],'check':board.is_check()}

def save_position(store,name,value):
    name=str(name).strip()
    if not name:raise ValueError('Enter a position name')
    checked=position(value)
    if not checked['valid']:raise ValueError('; '.join(checked['errors']) or 'Invalid position')
    item={'name':name,'fen':checked['fen'],'chess960':checked['chess960']}
    original=value.get('original_name')
    with store.tx():
        if original is not None and not store.one('SELECT name FROM positions WHERE name=?',(original,)):raise ValueError('Original position no longer exists')
        if name!=original and store.one('SELECT name FROM positions WHERE name=?',(name,)):raise ValueError('That position name already exists. Edit it or choose another name.')
        store.db.execute('INSERT OR REPLACE INTO positions VALUES(?,?)',(name,json.dumps(item)))
    return item
