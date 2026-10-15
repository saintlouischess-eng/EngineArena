"""Reuse the tournament PGN formatter and every existing export preset."""
import json
import sqlite3
from types import SimpleNamespace
import chess
from .pgn_format import render_attempt,control


def selection(scope):
    if scope=='all':return '',()
    if scope.startswith('series:'):return 'WHERE g.series=?',(scope[7:],)
    return 'WHERE g.id=?',(scope,)


async def stream(request,path):
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from pathlib import Path
    from aiohttp import web
    from .pgn_options import from_query,normalize
    executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='PlayerPgnExport');loop=asyncio.get_running_loop();reader={}
    options=normalize(from_query(request.query));where,args=selection(request.query['id'])
    def start():
        db=sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True);reader['db']=db;db.execute('BEGIN')
        reader['cursor']=db.execute('SELECT g.body,s.name FROM player_games g LEFT JOIN player_series s ON s.id=g.series '+where+' ORDER BY g.created',args)
    def chunk():return ''.join(render(json.loads(body),options,name or 'Player Arena') for body,name in reader['cursor'].fetchmany(8)).encode('utf-8')
    try:
        await loop.run_in_executor(executor,start)
        response=web.StreamResponse(headers={'Content-Type':'text/plain; charset=utf-8' if request.query.get('filetype')=='txt' else 'application/x-chess-pgn; charset=utf-8',
                                           'Content-Disposition':'attachment; filename="PlayerArena.pgn"'})
        await response.prepare(request)
        while data:=await loop.run_in_executor(executor,chunk):await response.write(data)
        await response.write_eof();return response
    finally:
        await loop.run_in_executor(executor,lambda:reader['db'].close() if reader.get('db') else None)
        executor.shutdown(wait=False,cancel_futures=True)


def render(game, options, title='Player Arena'):
    c=game['config'];human=c['color'];engine='black' if human=='white' else 'white'
    people={human:{'name':game['name'],'time_control':c['human_control']},engine:game['engine']|{'time_control':c['engine_control']}}
    # Older Player Arena games did not use profile books. Preserve that fact.
    if 'book_mode' not in c:people[engine].pop('move_book',None)
    # There is no search control for a human. Untimed is represented by '-' below.
    ctx=SimpleNamespace(tid=game['series'] or 'player',name=title,settings={'time_control':c['human_control'],'chess960':c['chess960'],
       'ponder':False,'annotations':True,'opening_policy':'Player starting position'},profile=lambda slot:people['white' if slot==0 else 'black'])
    db=sqlite3.connect(':memory:')
    try:
        db.executescript('''CREATE TABLE attempts(id, gid, started, result, reason, detail, identity, seq, mode);
        CREATE TABLE games(id,tid,opening,white,black,round,number,pair_no,leg);
        CREATE TABLE moves(aid,ply,uci,elapsed,clocks,info);''')
        identity={engine:game.get('identity',game['engine'].get('identity',{})),human:{'name':game['name']}}
        db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?,?)',(game['id'],game['id'],game['created'],game['result'],game['reason'],game.get('note',''),json.dumps(identity),1,'human_play'))
        db.execute('INSERT INTO games VALUES(?,?,?,?,?,?,?,?,?)',(game['id'],ctx.tid,json.dumps({'fen':c['fen'],'name':'Initial position' if c['fen']==chess.STARTING_FEN else 'Custom position'}),0,1,game['number']-1,game['number']-1,0,0))
        db.executemany('INSERT INTO moves VALUES(?,?,?,?,?,?)',[(game['id'],i,m['uci'],m['elapsed'],json.dumps(m['clocks']),json.dumps(m['info'])) for i,m in enumerate(game['moves'],1)])
        text=render_attempt(db,game['id'],context=ctx,export_options=options)
        prefix=human.title();removed={prefix+k for k in ('Engine','Threads','HashMB','SearchControl')}
        removed.update(('OpeningPair','OpeningLeg','OpeningSeed','OpeningPosition','AttemptMode'))
        lines=[line for line in text.splitlines() if not any(line.startswith('['+key+' ') for key in removed)]
        # Role and local rating metadata cannot be confused with engine-pool ratings.
        index=next(i for i,line in enumerate(lines) if not line)
        extra=['[WhiteType "'+('human' if human=='white' else 'program')+'"]','[BlackType "'+('human' if human=='black' else 'program')+'"]',
               '[Rated "'+('Local Elo' if game['rated'] else 'No')+'"]']
        if game.get('rating_change'):
            extra+=['['+prefix+'Elo "'+str(round(game['rating_change']['before']))+'"]',
                    '['+engine.title()+'Elo "'+str(round(c['opponent_rating']))+'"]','[RatingCategory "'+game['category']+'"]']
        if c['untimed']:
            lines=[line for line in lines if not any(line.startswith('['+tag+' ') for tag in ('TimeControl',prefix+'TimeControl',engine.title()+'TimeControl',engine.title()+'SearchControl'))]
            clock,search=control(c['engine_control'])
            extra+=['[TimeControl "?"]','['+prefix+'TimeControl "-"]','['+engine.title()+'TimeControl "'+clock+'"]',
                    '['+engine.title()+'SearchControl "'+search+'"]','[HumanTimeControl "Untimed practice"]']
            index=next(i for i,line in enumerate(lines) if not line)
        lines[index:index]=extra
        return '\n'.join(lines).rstrip()+'\n\n'
    finally:db.close()
