"""Isolated deterministic UI rehearsal, no engines or production data access."""
import asyncio
import json
import time
from pathlib import Path
from aiohttp import web
import chess
from arena.broadcast_server import Hub, make_app
from arena.broadcast import DEFAULTS

OUT=Path('test-output/broadcast-20261025/fixture');OUT.mkdir(parents=True,exist_ok=True)


class Fixture:
    def __init__(self):self.start=time.time()
    async def get(self,path):
        elapsed=time.time()-self.start;cycle=int(elapsed//32);age=elapsed%32;aid='fixture-'+str(cycle)
        board=chess.Board();rows=[]
        for i,san in enumerate(['e4','e5','Qh5','Nc6','Bc4','Nf6','Qxf7#']):
            move=board.parse_san(san);side='white' if board.turn else 'black';label=str(board.fullmove_number)+('.' if board.turn else '…');board.push(move)
            rows.append(dict(ply=i-1,uci=move.uci(),san=san,fen=board.fen(),label=label,side=side,clocks={},info={}))
        clocks={s:dict(remaining=180,control={'kind':'fischer','seconds':180,'increment':2}) for s in ('white','black')}
        p=max(0,min(5,int((age-3)/2)));fen=rows[p+1]['fen']
        g=dict(tid='fixture',attempt=aid,game='fixture-game',number=cycle,ply=p,fen=fen,
               white={'name':'Cyrus IS Chess 1.0.0'},black={'name':'apexUCI'},clocks=clocks,clock_active='white',search_elapsed=age%2,
               info={'cp':48,'depth':18,'nps':452000,'pv':''})
        if path=='status':return {'active_games':28,'live':[g] if age<15 else [],'recent_finished':[]}
        if path.startswith('games/'):
            requested=path.split('attempt=')[1].split('&')[0];old=requested!=aid
            after=int(path.split('after=')[1].split('&')[0]);n=5 if old else p
            return dict(attempt=dict(id=requested,ended=1 if old or age>=15 else None,result='1-0',reason='checkmate',official=old or age>=15,clocks=clocks),
                        opening={'start_fen':chess.STARTING_FEN,'fen':rows[1]['fen']},opening_moves=rows[:2],
                        items=[r|{'clocks':clocks} for r in rows[2:] if after<r['ply']<=n],latest_ply=n,has_more=False)
        if path=='tournaments':return [dict(id='fixture',name='Broadcast rehearsal',state='running')]
        if path.startswith('tournaments/'):
            names=['Stockfish 19','PlentyChess 7.0.0','Reckless 0.9.0','Coda 0.9.5','Berserk 14','Stash 37.0','Chess System Tal Assassin','Rebel 17','Cyrus IS Chess 1.0.0','OliThink 5.11.9']
            return dict(name='The 400-engine marathon',total=159600,active_participants=400,state='running',counts={'completed':35890+cycle},
                        standings=[dict(name=n,rank=i+1,games=178,points=145-i*2) for i,n in enumerate(names)],settings={'time_control':{'seconds':180,'increment':2}})
        return {'items':[]}


async def main():
    hub=Hub(Fixture(),DEFAULTS|{'tid':'fixture','title':'The 400-engine marathon','subtitle':'Broadcast rehearsal • synthetic game • not official results','hold':6})
    app=make_app(hub,OUT,'fixture','control');runner=web.AppRunner(app,access_log=None);await runner.setup();await web.TCPSite(runner,'127.0.0.1',8767).start()
    tasks=[asyncio.create_task(hub.run()),asyncio.create_task(hub.metadata())]
    (OUT/'ready.json').write_text(json.dumps({'viewer_url':'http://127.0.0.1:8767/view?key=fixture','control_url':'http://127.0.0.1:8767/control?key=control'}))
    try:await asyncio.Event().wait()
    finally:
        for t in tasks:t.cancel()
        await asyncio.gather(*tasks,return_exceptions=True);await runner.cleanup()

if __name__=='__main__':asyncio.run(main())
