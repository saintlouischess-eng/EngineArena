"""Isolated real broadcast HTTP service with synthetic data, never a Store/Runner."""
import argparse
import asyncio
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from aiohttp import web
from arena.broadcast_server import Hub,make_app

async def main(folder):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=True)
    source=json.loads((folder/'fixture.json').read_text(encoding='utf-8'))
    class Worker:
        async def get(self,path):
            assert path=='preferences',path
            return {'display':{'theme':'charcoal','pieceSet':'classic-bold','light':'#f0dfb8','dark':'#703f29','boardMaterials':{'light':'ash','dark':'rosewood'},'focus3d':False}}
    h=Hub(Worker(),source['config']);h.folder=folder
    h.tournaments=[{'id':'test','name':'QA 400-engine marathon','state':'running'},{'id':'match','name':'QA two-engine match','state':'running'},{'id':'paused','name':'QA paused event','state':'paused'}]
    connected=True
    time_offset=0
    def feed():
        data={**source,'config':h.director.config,'server_time':time.time()+time_offset,'pending':bool(h.pending),'connected':connected,'scene_since':h.scene_since}
        if h.director.config['tid']=='match':
            data['summary']={**source['summary'],'name':'QA two-engine match','active_participants':2,'standings':source['summary']['standings'][:2]}
        return data
    h.feed=feed
    app=make_app(h,folder,'fixture-view','fixture-control')
    async def action(request):
        nonlocal connected,time_offset
        value=await request.json()
        if value.get('action')=='playing':h.director.current={'attempt':'fixture-attempt'}
        elif value.get('action')=='finish':h.director.current=None;h.advance_program()
        elif value.get('action')=='page':time_offset+=source['config']['panel_seconds']
        elif value.get('action')=='move':source['game']['revision']+=1
        elif value.get('action')=='disconnect':connected=False
        elif value.get('action')=='connect':connected=True
        elif value.get('action')=='advance':h.advance_program(time.time()+86401)
        elif value.get('action')=='summary':source['summary'].update(value['summary']);source['summary_at']=time.time()
        elif value.get('action')=='result':source['game'].update(value['game'])
        elif value.get('action')=='game':source['game']=value.get('game')
        else:raise web.HTTPBadRequest()
        return web.json_response({'pending':bool(h.pending),'tid':h.director.config['tid'],'active':h.director.config['design']['active']})
    app.router.add_post('/qa-action',action)
    runner=web.AppRunner(app,access_log=None);await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
    port=site._server.sockets[0].getsockname()[1]
    (folder/'ready.json').write_text(json.dumps({'port':port,'control':f'http://127.0.0.1:{port}/control?key=fixture-control','view':f'http://127.0.0.1:{port}/view?key=fixture-view'}))
    try:await asyncio.Event().wait()
    finally:await runner.cleanup()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--folder',required=True);args=p.parse_args();asyncio.run(main(args.folder))
