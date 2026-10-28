"""Independent localhost OBS source; only GETs the installed worker API."""
from __future__ import annotations
import argparse
import asyncio
import contextlib
import json
import os
from pathlib import Path
import secrets
import sys
import time
from urllib.parse import quote
from aiohttp import web, ClientSession, ClientTimeout
from .broadcast import DEFAULTS, WOODS, Director, Headlines, settings
from .broadcast_design import CATALOG
from .broadcast_program import Program

ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))
VERSION=7

def write_json(path, value):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2),encoding='utf-8');temp.replace(path)


class Worker:
    def __init__(self, folder): self.folder=Path(folder);self.session=None
    async def get(self, path):
        # Re-read ready file so an intentional future update/restart reconnects.
        ready=json.loads((self.folder/'worker-ready.json').read_text(encoding='utf-8-sig'))
        async with self.session.get(f'http://127.0.0.1:{int(ready["port"])}/api/{path}',
                                    headers={'X-Arena-Token':ready['token']}, timeout=ClientTimeout(total=120 if path.startswith('rating-center') else 20,connect=3)) as r:
            r.raise_for_status(); return await r.json()


class Hub(Program):
    def __init__(self, worker, config):
        self.worker=worker;self.director=Director(config);self.headlines=Headlines()
        self.summary={};self.ratings=[];self.ratings_at=0.;self.rating_meta={}
        self.tournaments=[];self.status={};self.tasks=[];self.error='';self.summary_at=0.
        self.rating_entries={};self.featured_rating_key=None;self.featured_rating_at=0.
        self.init_program()

    def remember_ratings(self, report):
        """Cache exact recorded profile associations, including entries below the top 20."""
        when=report.get('snapshot') or time.time()
        for row in report.get('items',[]):
            self.rating_entries[row['id']]={
                'rating':row.get('rating'),'at':when,
                'profiles':{p['profile_id'] for p in row.get('profiles',[]) if p.get('profile_id')},
                'names':{p['name'] for p in row.get('profiles',[]) if p.get('name')}}

    def player_rating(self, player):
        pid=player.get('id');name=player.get('name')
        matches=[r for r in self.rating_entries.values()
                 if (pid in r['profiles'] if pid else name in r['names'])]
        # An edited profile can have multiple recorded configurations. Do not
        # silently assign its strongest version or another thread configuration.
        if len(matches)!=1:return {'rating':None,'rating_at':None}
        return {'rating':matches[0]['rating'],'rating_at':matches[0]['at']}

    async def run(self):
        while True:
            try:
                s=await self.worker.get('status');now=time.time();self.advance_program(now);self.observe_panels(s)
                ranks={r['name']:r.get('rank',999) for r in self.summary.get('standings',[])}
                scene=self.selected(self.director.config)
                if self.director.current or any(p['type']=='board' and p['visible'] for p in scene['panels']):
                    self.director.observe(s,now,ranks,self.player_rating)
                else:self.director.connected=True
                self.headlines.results(s.get('recent_finished',[]),self.director.config['tid'],now,self.player_rating)
                if self.director.current:
                    d=self.director;c=d.current
                    page=await self.worker.get(f'games/{c["game"]}/moves?attempt={c["attempt"]}&after={d.after}&limit=500')
                    d.ingest(page)
                self.error=''
            except asyncio.CancelledError: raise
            except Exception:
                self.director.connected=False;self.error='Reconnecting to Engine Arena — last saved position retained'
            await asyncio.sleep(1)

    async def metadata(self):
        next_rating=0.;last_category=None
        while True:
            try:
                self.tournaments=await self.worker.get('tournaments')
                tid=self.director.config['tid']
                if tid:
                    captured=tid
                    s=await self.worker.get(f'tournaments/{tid}?compact=1&limit=10000')
                    if captured==self.director.config['tid']:
                        rows=[{k:r.get(k) for k in ('name','rank','slot','games','wins','draws','losses','points','score','score_pct','sonneborn_berger')}
                              for r in s.get('standings',[])]
                        complete=s.get('counts',{}).get('completed',s.get('official_games',0))
                        self.summary={k:s.get(k) for k in ('name','state','total','active_participants','progress')}
                        self.summary.update(completed=complete,standings=rows)
                        tc=s.get('settings',{}).get('time_control',{})
                        self.summary['conditions']=dict(time_control=tc,concurrency=s.get('settings',{}).get('concurrency'))
                        self.summary_at=time.time();self.headlines.standings(rows,complete,self.summary_at)
                        try:
                            details=await self.worker.get(f'tournaments/{tid}/broadcast')
                            if tid==self.director.config['tid']:self.details=details
                        except Exception:pass
                        current=self.director.current
                        if current:
                            slot=next((r['slot'] for r in rows if r['name']==current['white']['name']),None)
                            if slot is not None:
                                try:
                                    comparison=await self.worker.get(f'tournaments/{tid}/h2h/{slot}')
                                    if tid==self.director.config['tid']:
                                        self.opponents=comparison.get('items',[])[:50];self.opponent_key=current['white']['name']
                                except Exception:pass
                if time.time()>=next_rating or last_category!=self.director.config['category']:
                    category=self.director.config['category'];next_rating=time.time()+180;last_category=category
                    r=await self.worker.get('rating-center?pool=main&category='+category+'&view=broadcast&sort=rating&direction=desc')
                    if r.get('items') and category==self.director.config['category']:
                        self.remember_ratings(r)
                        self.ratings=[{k:row.get(k) for k in ('id','name','rank','rating','ci','games','wins','draws','losses')} for row in r['items']]
                        self.ratings_at=time.time()
                        last_category=category
                        self.rating_meta={k:r.get(k) for k in ('category','official_games','counted_games','confidence','anchor')}
                        # Only public anchor identity/rating, never settings or configuration.
                        anchor=self.rating_meta.get('anchor')
                        if isinstance(anchor,dict):self.rating_meta['anchor']={k:anchor.get(k) for k in ('name','rating')}
                # Older installed workers return only their first 50 rows. A
                # bounded name-filtered request supplies the featured players;
                # current workers already return all cheap point estimates.
                current=self.director.current
                if current:
                    featured=tuple(current[side].get('id') or current[side]['name'] for side in ('white','black'))
                    missing=any(self.player_rating(current[side])['rating_at'] is None for side in ('white','black'))
                    stale=any((self.player_rating(current[side])['rating_at'] or 0)<time.time()-180 for side in ('white','black'))
                    if (missing or stale) and (featured!=self.featured_rating_key or time.time()-self.featured_rating_at>=180):
                        self.featured_rating_key=featured;self.featured_rating_at=time.time()
                        category=self.director.config['category']
                        names=';'.join(current[side]['name'] for side in ('white','black'))
                        r=await self.worker.get('rating-center?pool=main&category='+category+'&view=broadcast&q='+quote(names,safe=''))
                        if category==self.director.config['category']:self.remember_ratings(r)
                self.record_observation()
            except asyncio.CancelledError: raise
            except Exception: pass # Keep last good tables; the viewer shows snapshot time.
            await asyncio.sleep(30)

    def feed(self):
        d=self.director
        snapshot=d.snapshot()
        if snapshot['game']:
            for side in ('white','black'):
                player=snapshot['game'][side]
                snapshot['game'][side]=player|self.player_rating(player)
        return snapshot|dict(config=d.config,summary=self.summary,summary_at=self.summary_at,
                                 ratings=self.ratings,ratings_at=self.ratings_at,rating_meta=self.rating_meta,
                                 headlines=[h for h in self.headlines.items if d.config.get(h['kind'],False)],
                                 status=self.status,error=self.error,server_time=time.time(),scene_since=self.scene_since,
                                 pending=bool(self.pending),recent=self.recent,details=self.details,hardware=self.hardware,
                                 observations=[o for o in self.observations if o['tid']==d.config['tid']],
                                 opponents=self.opponents,opponent_name=self.opponent_key,
                                 field_rating_ids=[k for k,r in self.rating_entries.items() if r['profiles'].intersection({p.get('id') for p in self.details.get('people',[])})])


def make_app(hub, folder, viewer, control):
    folder=Path(folder)
    @web.middleware
    async def guard(request, handler):
        # Prevent DNS rebinding and cross-origin control, even on loopback.
        if request.host.split(':')[0] not in ('127.0.0.1','localhost'):raise web.HTTPForbidden()
        private=request.path in ('/control','/config','/validate','/tournaments','/identity','/preview','/preview-feed','/upload','/preferences','/obs')
        required=control if private else viewer
        if request.path not in ('/health',) and not request.path.startswith(('/assets/','/textures/','/scene-assets/','/media/')):
            if not secrets.compare_digest(request.query.get('key',''),required):raise web.HTTPForbidden()
        if request.method!='GET':
            if request.headers.get('Origin')!=f'{request.scheme}://{request.host}':raise web.HTTPForbidden()
        response=await handler(request)
        response.headers['Cache-Control']='no-store'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['X-Content-Type-Options']='nosniff'
        return response
    app=web.Application(middlewares=[guard],client_max_size=12*1024*1024)
    async def health(request):return web.json_response({'service':'Engine Arena Broadcast','version':VERSION})
    async def identity(request):return web.json_response({'version':VERSION,'folder':str(folder.resolve())})
    async def view(request):return web.FileResponse(ROOT/'ui'/'broadcast-view.html')
    async def control_page(request):return web.FileResponse(ROOT/'ui'/'broadcast-designer.html')
    async def feed(request):return web.json_response(hub.feed())
    async def config(request):
        if request.method=='POST':
            value=await request.json();new=settings(value)
            tids={t['id'] for t in hub.tournaments}
            requested={new['tid'],*new['playlist'],*(s['tid'] for s in new['design']['scenes'])}-{''}
            if requested-tids:
                raise web.HTTPBadRequest(text='Select an existing tournament')
            hub.apply_program(new,cut=value.get('cut_now') is True)
            write_json(folder/'config.json',new)
        return web.json_response(dict(config=hub.pending or hub.director.config,pending=bool(hub.pending),viewer_url=f'http://{request.host}/view?key={viewer}'))
    async def tournaments(request):
        return web.json_response([{k:t.get(k) for k in ('id','name','state')} for t in hub.tournaments])
    async def validate(request):return web.json_response(settings(await request.json()))
    async def asset(request):
        name=request.match_info['name'];allowed={'broadcast.css','broadcast.js','broadcast-control.js','engine-arena.svg','player-move.wav',
            'broadcast-catalog.json','broadcast-progress.js','broadcast-model.js','broadcast-designer.js','broadcast-designer.css','broadcast-view.js','broadcast-view.css','broadcast-3d.js','board3d.js','board3d-model.js','i18n.js','clocks.js'}
        allowed.update(p.name for p in (ROOT/'ui').glob('board3d-*.js') if p.name not in ('board3d-ui.js','board3d-presentation.js'))
        allowed.update(p.name for p in (ROOT/'ui').glob('three*.js'))
        allowed.update(p.name for p in (ROOT/'ui').glob('*.glb') if p.name.startswith(('club-','room-head','staunton1849','tal1962')))
        allowed.update('textures/'+wood+'.png' for wood in WOODS)
        if name not in allowed:
            parts=name.split('/')
            if not (len(parts)==3 and parts[0]=='pieces' and parts[1] in CATALOG['pieces']
                    and parts[2] in [c+p+'.svg' for c in 'wb' for p in 'PNBRQK']): raise web.HTTPNotFound()
        return web.FileResponse(ROOT/'ui'/name)
    async def texture(request):
        kind=request.match_info['kind'];name=request.match_info['name']
        if kind not in ('textures','scene-assets') or Path(name).name!=name or name.startswith('.') or Path(name).suffix not in ('.png','.jpg','.hdr'):raise web.HTTPNotFound()
        path=ROOT/'ui'/kind/name
        if not path.is_file():raise web.HTTPNotFound()
        return web.FileResponse(path)
    async def upload(request):
        import io,hashlib
        from PIL import Image
        raw=await request.read()
        if len(raw)>8*1024*1024:raise web.HTTPBadRequest(text='Choose an image under 8 MB')
        try:
            with Image.open(io.BytesIO(raw)) as im:
                if im.width*im.height>16000000:raise ValueError('Image too large')
                im.thumbnail((3840,2160));buf=io.BytesIO();im.convert('RGBA').save(buf,format='PNG');data=buf.getvalue()
        except Exception:raise web.HTTPBadRequest(text='Choose a PNG, JPG or WebP image up to 16 megapixels')
        name=hashlib.sha256(data).hexdigest()+'.png';(folder/'media').mkdir(exist_ok=True)
        (folder/'media'/name).write_bytes(data)
        return web.json_response({'image':name})
    async def media(request):
        import re
        name=request.match_info['name']
        if not re.fullmatch(r'[a-f0-9]{64}\.png',name) or not (folder/'media'/name).is_file():raise web.HTTPNotFound()
        return web.FileResponse(folder/'media'/name)
    async def preferences(request):
        if not hub.worker:raise web.HTTPServiceUnavailable()
        value=await hub.worker.get('preferences')
        return web.json_response(value)
    async def obs(request):
        from . import obs_launch
        if request.method=='GET':
            return web.json_response(await asyncio.to_thread(obs_launch.status,folder))
        body=await request.json()
        if not isinstance(body,dict) or not isinstance(body.get('path',''),str):
            raise web.HTTPBadRequest(text='Enter the path to obs64.exe as text.')
        try:
            return web.json_response(await asyncio.to_thread(obs_launch.launch,folder,body.get('path','')))
        except (ValueError,OSError) as exc:
            raise web.HTTPBadRequest(text=str(exc))
    app.add_routes([web.get('/health',health),web.get('/identity',identity),web.get('/view',view),
                    web.get('/control',control_page),web.get('/feed',feed),web.get('/config',config),web.post('/validate',validate),
                    web.get('/preview',view),web.get('/preview-feed',feed),web.post('/upload',upload),web.get('/preferences',preferences),web.get('/media/{name}',media),
                    web.post('/config',config),web.get('/tournaments',tournaments),web.get('/assets/{name:.+}',asset),
                    web.get('/obs',obs),web.post('/obs',obs),
                    web.get('/{kind:textures|scene-assets}/{name}',texture)])
    return app


async def serve(args):
    folder=Path(args.config);folder.mkdir(parents=True,exist_ok=True)
    secret_file=folder/'keys.json'
    if secret_file.exists():keys=json.loads(secret_file.read_text())
    else:
        keys=dict(viewer=secrets.token_urlsafe(32),control=secrets.token_urlsafe(32));write_json(secret_file,keys)
    cfg=settings(json.loads((folder/'config.json').read_text()) if (folder/'config.json').exists() else DEFAULTS)
    worker=Worker(args.data);hub=Hub(worker,cfg)
    async with ClientSession(timeout=ClientTimeout(total=20,connect=3)) as session:
        worker.session=session
        hub.folder=folder
        try:
            history=json.loads((folder/'observations.json').read_text())
            hub.observations=history[-720:] if isinstance(history,list) else []
        except (OSError,ValueError):pass
        app=make_app(hub,folder,keys['viewer'],keys['control']);runner=web.AppRunner(app,access_log=None)
        await runner.setup();site=web.TCPSite(runner,'127.0.0.1',args.port);await site.start()
        write_json(folder/'ready.json',dict(pid=os.getpid(),port=args.port,version=VERSION,
                   control_url=f'http://127.0.0.1:{args.port}/control?key={keys["control"]}',
                   viewer_url=f'http://127.0.0.1:{args.port}/view?key={keys["viewer"]}'))
        hub.tasks=[asyncio.create_task(hub.run()),asyncio.create_task(hub.metadata())]
        try:await asyncio.Event().wait()
        finally:
            for task in hub.tasks: task.cancel()
            await asyncio.gather(*hub.tasks,return_exceptions=True);await runner.cleanup()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--data',required=True);parser.add_argument('--config',required=True)
    parser.add_argument('--port',type=int,default=8768);args=parser.parse_args();asyncio.run(serve(args))

if __name__=='__main__':main()
