"""Disposable UI evidence: authentic views, synthetic telemetry, no engines run."""
import asyncio
import contextlib
import json
import os
from pathlib import Path
import secrets
import sys
import time
import chess
from aiohttp import web
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from arena.server import create_app

async def main():
    folder=ROOT/'test-output'/'opening-eval-ui';folder.mkdir(exist_ok=True)
    token=secrets.token_urlsafe(32);app=await create_app(folder,token);db=app['db'];runner=app['runner']
    runner.scheduler.cancel()
    with contextlib.suppress(asyncio.CancelledError):await runner.scheduler
    existing=await db.call('rows','SELECT id FROM tournaments')
    if not existing:
        profiles=[await db.call('save_profile',{'name':'Fixture '+str(i+1),'path':sys.executable,'threads':1,'hash':1}) for i in range(4)]
        t=await db.call('create_tournament','Opening & evaluation UI fixture',profiles,{'format':'round_robin','cycles':16,'opening_policy':'pair'})
        prefs={'fontSize':14,'boardCount':4,'split':50,'panels':{'focus':{'visible':True,'height':720},'live':{'visible':True,'height':680},'search':{'visible':False}}}
        await db.call('execute','INSERT OR REPLACE INTO preferences VALUES(?,?)',('ui',json.dumps(prefs)))
    else:t=await db.call('tournament',existing[0]['id'])
    await db.call('set_state',t['id'],'running');await db.call('fill_queue',t['id'],128);await db.call('set_state',t['id'],'paused')
    games=await db.call('rows','SELECT id,number FROM games WHERE tid=? ORDER BY number',(t['id'],));original=runner.status
    b=chess.Board();positions=[]
    for move in ('e2e4','e7e5','g1f3','b8c6'):b.push_uci(move);positions.append(b.fen())
    opening_file=folder/'sample-openings.fen';board=chess.Board();fens=[]
    for move in list(board.legal_moves)[:6]:board.push(move);fens.append(board.fen());board.pop()
    opening_file.write_text('\n'.join(fens+[fens[0]]),encoding='utf-8')
    def status():
        live=[];tick=int(time.monotonic()/3)
        for i,g in enumerate(games):
            side='white' if (tick+i)%2==0 else 'black';info=[{'cp':125},{'cp':-240},{'mate':5},{},{'cp':1800},{'mate':-4}][i%6]
            live.append({'tid':t['id'],'game':g['id'],'number':g['number'],'fen':positions[(i+tick)%4],'ply':8,'white':{'name':'Fixture White '+str(i+1)},'black':{'name':'Fixture Black '+str(i+1)},'status':side.title()+' thinking','clock_active':side,'info_side':side,'info':info,'searches':{side:{'info':info,'move_number':5,'complete':False}},'search_elapsed':time.monotonic()%3,'clocks':{s:{'control':{'kind':'nodes','nodes':10000},'remaining':None,'elapsed':1} for s in ('white','black')}})
        return original()|{'live':live,'active_games':len(live)}
    runner.status=status;app['stop']=asyncio.Event();server=web.AppRunner(app);await server.setup();site=web.TCPSite(server,'127.0.0.1',0);await site.start()
    ready={'port':site._server.sockets[0].getsockname()[1],'token':token,'pid':os.getpid()};(folder/'worker-ready.json').write_text(json.dumps(ready));print(json.dumps(ready),flush=True)
    try:await app['stop'].wait()
    finally:await server.cleanup()

if __name__=='__main__':asyncio.run(main())
