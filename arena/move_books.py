"""Immutable, disk-indexed books which choose moves for individual profiles."""
import hashlib
import codecs
import json
from pathlib import Path
import random
import sqlite3
import struct
import tempfile

import chess
import chess.pgn
import chess.polyglot

SCHEMA='CREATE TABLE IF NOT EXISTS book_moves(book_id TEXT,position TEXT,uci TEXT,weight INTEGER,PRIMARY KEY(book_id,position,uci)) WITHOUT ROWID'

def initialize(store):
    store.db.execute('CREATE TABLE IF NOT EXISTS move_books(id TEXT PRIMARY KEY,body TEXT NOT NULL)')
    store.db.execute(SCHEMA)

def key(board):return f'{chess.polyglot.zobrist_hash(board):016x}'

def compile_book(path):
    """Stream input to a temporary index; never retain a whole book in memory."""
    source=Path(path)
    kind=source.suffix.lower()
    if kind not in ('.pgn','.bin'):raise ValueError('Engine move books require a PGN with moves or a Polyglot BIN file')
    before=source.stat();digest=hashlib.sha256();decoder=codecs.getincrementaldecoder('utf-8')();utf8=True
    with source.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            digest.update(chunk)
            if kind=='.pgn' and utf8:
                try:decoder.decode(chunk)
                except UnicodeDecodeError:utf8=False
    if kind=='.pgn' and utf8:
        try:decoder.decode(b'',final=True)
        except UnicodeDecodeError:utf8=False
    bid=digest.hexdigest()
    tmp=tempfile.NamedTemporaryFile(prefix='arena-book-',suffix='.sqlite3',delete=False);tmp.close()
    db=sqlite3.connect(tmp.name)
    games=entries=0
    try:
        db.execute(SCHEMA)
        def add(position,uci,weight):
            nonlocal entries
            if weight<=0:return
            db.execute('INSERT INTO book_moves VALUES(?,?,?,?) ON CONFLICT(book_id,position,uci) DO UPDATE SET weight=weight+excluded.weight',(bid,position,uci,weight))
            entries+=1
        if kind=='.pgn':
            # Traditional PGN uses Latin-1; modern files commonly use UTF-8.
            with source.open(encoding='utf-8-sig' if utf8 else 'latin-1') as f:
                while (game:=chess.pgn.read_game(f)) is not None:
                    if game.errors:raise ValueError('PGN book contains an illegal or unreadable move: '+str(game.errors[0]))
                    board=game.board();moves=0
                    for move in game.mainline_moves():
                        add(key(board),board.uci(move),1);board.push(move);moves+=1
                    games+=bool(moves)
        else:
            if before.st_size%16:raise ValueError('Polyglot book has an incomplete 16-byte entry')
            with source.open('rb') as f:
                for record in iter(lambda:f.read(16),b''):
                    position,raw,weight,_=struct.unpack('>QHHI',record)
                    promotion=(raw>>12)&7
                    if promotion>4:raise ValueError('Polyglot book has an invalid promotion')
                    move=chess.Move((raw>>6)&63,raw&63,promotion+1 if promotion else None)
                    add(f'{position:016x}',move.uci(),weight)
        if not entries:raise ValueError('No playable book moves found. Position-only PGNs belong in the tournament starting-position field.')
        after=source.stat()
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('Book file changed during import; import it again')
        db.commit()
        positions=db.execute('SELECT count(DISTINCT position) FROM book_moves').fetchone()[0]
        moves=db.execute('SELECT count(*) FROM book_moves').fetchone()[0]
        return {'path':tmp.name,'metadata':{'id':bid,'name':source.name,'format':kind[1:],'positions':positions,'moves':moves,'games':games,'bytes':before.st_size}}
    except BaseException:
        db.close();Path(tmp.name).unlink(missing_ok=True);raise
    finally:db.close()

def install(store,compiled):
    metadata=compiled['metadata'];bid=metadata['id']
    old=store.one('SELECT body FROM move_books WHERE id=?',(bid,))
    if old:return json.loads(old['body'])
    store.db.execute('ATTACH DATABASE ? AS imported_book',(compiled['path'],))
    try:
        with store.tx():
            store.db.execute('INSERT INTO move_books VALUES(?,?)',(bid,json.dumps(metadata)))
            store.db.execute('INSERT INTO book_moves SELECT * FROM imported_book.book_moves')
    finally:store.db.execute('DETACH DATABASE imported_book')
    return metadata

def validate(store,value):
    if not value:return None
    if not isinstance(value,dict):raise ValueError('Invalid engine move book settings')
    row=store.one('SELECT body FROM move_books WHERE id=?',(value.get('id'),))
    if not row:raise ValueError('Engine move book is missing from this workspace; import its source file first')
    policy=value.get('policy','weighted');plies=value.get('max_plies',16)
    if policy not in ('weighted','uniform','best'):raise ValueError('Invalid engine book selection policy')
    if isinstance(plies,bool) or not isinstance(plies,int) or plies<0:raise ValueError('Book depth must be a nonnegative whole number of plies')
    return json.loads(row['body'])|{'policy':policy,'max_plies':plies}

def candidates(store,bid,position):
    if not store.one('SELECT 1 FROM move_books WHERE id=?',(bid,)):raise ValueError('Recorded engine move book is missing; restore the tournament backup')
    return store.rows('SELECT uci,weight FROM book_moves WHERE book_id=? AND position=? ORDER BY uci',(bid,position))

def remove(store,bid):
    for table,column in (('profiles','body'),('participants','profile'),('experiments','profiles'),('events','body')):
        if store.one(f'SELECT 1 FROM {table},json_tree({column}) j WHERE j.value=? LIMIT 1',(bid,)):
            raise ValueError('This book is used by a saved profile, tournament or experiment. Remove those references before deleting the book.')
    with store.tx():
        store.db.execute('DELETE FROM book_moves WHERE book_id=?',(bid,))
        store.db.execute('DELETE FROM move_books WHERE id=?',(bid,))
    return {'deleted':bid}

def choose(board,rows,config,seed):
    choices=[]
    for row in rows:
        try:move=board.parse_uci(row['uci'])
        except ValueError:continue
        if row['weight']>0:choices.append((move,row['weight']))
    if not choices:return None
    rng=random.Random(hashlib.sha256(str(seed).encode()).digest())
    if config['policy']=='best':
        maximum=max(w for _,w in choices);return rng.choice([m for m,w in choices if w==maximum])
    if config['policy']=='uniform':return rng.choice([m for m,_ in choices])
    pick=rng.randrange(sum(w for _,w in choices))
    for move,weight in choices:
        if pick<weight:return move
        pick-=weight
