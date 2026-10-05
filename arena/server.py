from __future__ import annotations
import argparse
import asyncio
from concurrent.futures import ProcessPoolExecutor
import csv
import io
import json
import multiprocessing
import os
from pathlib import Path
import secrets
import sys
from aiohttp import web
import chess
from .store import DEFAULTS,encode
from .runner import Database,Runner
from .uci import discover,validated_options
from .openings import inspect_openings
from .models import scheduled_pairs

ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))

async def create_app(folder,token):
    db=await Database().open(folder,defer_maintenance=True);runner=Runner(db)
    @web.middleware
    async def guard(request,handler):
        if request.path.startswith('/api/'):
            provided=request.headers.get('X-Arena-Token',request.query.get('token',''))
            if not secrets.compare_digest(provided,token):raise web.HTTPForbidden(text='Local session token required')
            origin=request.headers.get('Origin')
            if origin and origin!=f'{request.scheme}://{request.host}':raise web.HTTPForbidden(text='Foreign origin rejected')
        try:
            if (request.method=='POST' and (runner.maintenance or db.store.maintenance_state.get('busy')) and
                request.path not in ('/api/storage','/api/shutdown','/api/ui-metrics')):
                raise ValueError('Storage maintenance is in progress. Wait for cleanup to finish before changing data or starting games.')
            return await handler(request)
        except web.HTTPException:raise
        except (ValueError,KeyError,TypeError) as e:return web.json_response({'error':str(e)},status=400)
        except Exception as e:return web.json_response({'error':str(e)},status=500)
    app=web.Application(middlewares=[guard],client_max_size=64*1024*1024)
    app['db']=db;app['runner']=runner
    from .report_jobs import ReportJobs
    report_jobs=ReportJobs()
    from .stats import confidence_level
    from .progress import Progress
    progress=Progress()
    def confidence(request):return confidence_level(request.query.get('confidence',95))
    from .hardware import HardwareMonitor,settings as hardware_settings
    saved_preferences=await db.call('one',"SELECT body FROM preferences WHERE name='ui'")
    try:hardware_config=hardware_settings(json.loads(saved_preferences['body']).get('hardware')) if saved_preferences else None
    except (ValueError,TypeError,AttributeError):hardware_config=None
    from .i18n import language
    try:saved_language=language(json.loads(saved_preferences['body']).get('language','en')) if saved_preferences else 'en'
    except (ValueError,AttributeError):saved_language='en'
    app['presentation']={'language':saved_language}
    hardware=HardwareMonitor(db.store.folder,hardware_config)
    runner.runtime.monitor=hardware

    opening_lock=asyncio.Lock();opening_cache_key=None;opening_cache=None
    async def opening_inventory(path,depth,chess960):
        nonlocal opening_cache_key,opening_cache
        p=Path(path).resolve();st=p.stat();key=(str(p),st.st_size,st.st_mtime_ns,depth,chess960)
        # One inventory in memory; parsing never runs on the asyncio/clock loop.
        async with opening_lock:
            if key!=opening_cache_key:
                result=await asyncio.to_thread(inspect_openings,p,depth,chess960)
                after=p.stat()
                if (st.st_size,st.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('Opening file changed while reading; analyze it again')
                opening_cache_key=key;opening_cache=result
            return opening_cache

    async def opening_preview(request):
        from .opening_policy import capacity,POLICIES
        b=await request.json();s=DEFAULTS|b['settings'];n=int(b['participants'])
        if s['opening_policy'] not in POLICIES:raise ValueError('Unknown opening preset')
        if s['opening_order'] not in ('sequential','shuffle','random'):raise ValueError('Unknown opening order')
        if b.get('recorded_tournament'):
            t=await db.call('tournament',b['recorded_tournament'])
            from .openings import unique_openings
            count=len(unique_openings(t['settings']['openings'],t['settings']['chess960']))
            info={**t['settings'].get('opening_inventory',{}),'unique_positions':count,'kind':'recorded','exact':True,'duplicates_removed':len(t['settings']['openings'])-count}
        elif b.get('opening_file'):
            inventory=await opening_inventory(b['opening_file'],b.get('book_depth',16),s['chess960'])
            info={k:v for k,v in inventory.items() if k!='items'}
        elif b.get('all960'):info={'unique_positions':960,'kind':'chess960','exact':True,'duplicates_removed':0}
        else:
            if b.get('saved_position') and not await db.call('one','SELECT name FROM positions WHERE name=?',(b['saved_position'],)):raise ValueError('Saved starting position no longer exists')
            info={'unique_positions':1,'kind':'saved' if b.get('saved_position') else 'initial','exact':True,'duplicates_removed':0}
        return web.json_response(info|capacity(info['unique_positions'],n,s))

    async def index(request):
        from .i18n import language,catalog
        code=language(request.query.get('lang',app['presentation']['language']))
        boot='window.ARENA_LANGUAGE='+json.dumps(code)+';window.ARENA_MESSAGES='+json.dumps(catalog(code),ensure_ascii=False).replace('<','\\u003c')+';'
        source=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        source=source.replace('<head>','<head><script>'+boot+'</script><script src="/assets/i18n.js"></script>',1)
        return web.Response(text=source,content_type='text/html',headers={'Cache-Control':'no-cache'})
    async def static(request):
        name=request.match_info['name']
        if name not in ('workflow.css','workflow.js','board3d.js','board3d-studio.js','board3d-crowns.js','staunton1849.glb','three.core.js','three.module.js','three-gltf.js','three-geometry-utils.js','three-room.js','three-skeleton-utils.js','board3d-ui.js','game-moves.js','studio.css','studio.js','engine-arena.svg','sprt.js','events.css','events.js','custom-matchups.js','tournament-queue.js','tournament-queue.css','tournament-edit.js','engine-books.js','reliability.js','focus-layout.js','focus-layout.css','concurrency.js','i18n.js','language.js','storage.js','knockout.js','text-format.js','text-exports.js','text-exports.css','search.js','board-materials.js','board-materials.css','adjudication.js','table-controls.css','format.js','review.js','review.css','hardware.js','hardware-model.js','hardware.css','results.js','results-model.js','pgn.js','pgn.css','evaluation.js','evaluation-ui.js','evaluation.css','opening-presets.js','focus.js','focus.css','polish.js','help.js','polish.css','clocks.js','app.js','workspace.js','formats.js','conditions.js','reports.js','ratings.js','comparisons.js','graphs.js','style.css'):raise web.HTTPNotFound()
        return web.FileResponse(ROOT/'ui'/name,headers={'Cache-Control':'no-cache'})
    async def status(request):
        hardware.request()
        return web.json_response(runner.status()|{'hardware':hardware.snapshot(),'data_folder':str(db.store.folder),'warning':db.store.warning,'ui_metrics':app.get('ui_metrics'),'tournament_queue':db.store.queue_status})
    async def search_detail(request):
        return web.json_response(runner.search_detail(request.match_info['aid'],request.query.get('side','white')))
    async def hardware_probe(request):return web.json_response(await hardware.probe())
    async def profiles(request):
        if request.method=='GET':return web.json_response(await db.call('profiles',request.query.get('q',''),int(request.query.get('offset',0)),int(request.query.get('limit',100))))
        body=await request.json()
        if body.get('discover',True):body=await discover(body,DEFAULTS)
        if body.get('advertised'):validated_options(body.get('options',{}),body['advertised'])
        return web.json_response(await db.call('save_profile',body))
    async def move_books(request):
        if request.method=='GET':
            return web.json_response([json.loads(r['body']) for r in await db.call('rows','SELECT body FROM move_books ORDER BY json_extract(body,\'$.name\')')])
        from .move_books import compile_book
        body=await request.json()
        # Compilation is streamed off the event loop. Install only while idle:
        # a large index transaction must not hold up committed game moves.
        async with runner.lifecycle_lock:
            if runner.tasks or runner.experiment_task and not runner.experiment_task.done():raise ValueError('Pause and drain games before importing an engine move book')
            if body.get('delete'):return web.json_response(await db.call('remove_move_book',body['delete']))
            compiled=await asyncio.to_thread(compile_book,body['path'])
            try:return web.json_response(await db.call('install_move_book',compiled))
            finally:Path(compiled['path']).unlink(missing_ok=True)
    async def import_profiles(request):
        body=await request.json();result=[]
        for p in body['profiles']:result.append(await db.call('save_profile',p))
        return web.json_response({'count':len(result)})
    async def external_profiles(request):
        from .profile_import import read_preview
        body=await request.json();checked=await asyncio.to_thread(read_preview,db.store.path,body)
        return web.json_response(checked if body.get('preview',True) else await db.call('commit_profile_import',checked,body.get('selected')))
    async def game_moves(request):
        from .game_moves import read_moves
        return web.json_response(await asyncio.to_thread(read_moves,db.store.path,request.match_info['gid'],request.query.get('attempt'),request.query.get('after',0),request.query.get('limit',200)))
    async def completed_tournament(request):
        from .game_moves import completion
        return web.json_response(await asyncio.to_thread(completion,db.store.path,request.match_info['tid']))
    async def discover_profile(request):
        body=await request.json()
        result=await discover(body,DEFAULTS)
        if result.get('advertised'):validated_options(result.get('options',{}),result['advertised'])
        return web.json_response(result)
    async def delete_profiles(request):
        body=await request.json()
        if body.get('preview') is True:return web.json_response(await db.call('profile_deletion_preview',body.get('ids')))
        if body.get('confirmed') is not True:raise ValueError('Confirm engine profile deletion first')
        return web.json_response(await db.call('delete_profiles',body.get('ids')))
    async def scan(request):
        body=await request.json();paths=body.get('paths')
        if paths is None:paths=[str(p) for p in Path(body['folder']).glob('**/*.exe' if body.get('recursive') else '*.exe')]
        result=[]
        # Bounded discovery: unknown executables never launch all at once.
        for path in paths:
            try:p=await discover({'path':path,'name':''},DEFAULTS);result.append({'profile':await db.call('save_profile',p)})
            except Exception as e:result.append({'path':path,'error':str(e)})
        return web.json_response({'items':result})
    async def tournaments(request):
        if request.method=='GET':return web.json_response(await db.call('rows','SELECT id,name,state,total,created,note FROM tournaments ORDER BY created DESC'))
        body=await request.json();profiles=[]
        tid=request.match_info.get('tid');old=await db.call('tournament_setup',tid) if tid else None
        if tid:
            body['settings']={**old['settings'],**body.get('settings',{})}
            if not body.get('keep_openings',True):
                body['settings'].pop('opening_inventory',None);body['settings'].pop('opening_source',None)
        if tid and body.get('keep_participants',True):
            profiles=[json.loads(r['profile']) for r in await db.call('rows','SELECT profile FROM participants WHERE tid=? ORDER BY slot',(tid,))]
        elif body.get('all_profiles'):
            profiles=[json.loads(r['body']) for r in await db.call('rows','SELECT body FROM profiles ORDER BY name,id')]
        else:
            for pid in body['profiles']:
                p=await db.call('one','SELECT body FROM profiles WHERE id=?',(pid,))
                if not p:raise ValueError('Profile no longer exists')
                profiles.append(json.loads(p['body']))
        openings=body.get('openings')
        if body.get('common_control') is True:
            for p in profiles:p.pop('time_control',None)
        if tid and body.get('keep_openings',True) and any(body.get(k) for k in ('openings','opening_file','saved_position','all960')):
            raise ValueError('Select only one opening source')
        if body.get('saved_position'):
            if openings or body.get('opening_file') or body.get('all960'):raise ValueError('Select only one opening source')
            row=await db.call('one','SELECT body FROM positions WHERE name=?',(body['saved_position'],))
            if not row:raise ValueError('Saved starting position no longer exists')
            saved=json.loads(row['body']);openings=[saved]
            body['settings']['chess960']=saved['chess960']
        if body.get('resource_preset'):
            from .conditions import preset_settings
            preset=preset_settings(body['resource_preset'])
            for p in profiles:
                p['threads']=int(preset.get('threads',1));p['hash']=int(preset.get('hash',1024))
                from .engine_options import find_name
                for resource in ('threads','hash'):
                    key=find_name(p.get('options',{}),resource)
                    if key:p['options'][key]=p[resource]
        if body.get('opening_file'):
            inventory=await opening_inventory(body['opening_file'],body.get('book_depth',16),body['settings'].get('chess960',False));openings=inventory['items']
            body['settings']['opening_inventory']={k:v for k,v in inventory.items() if k!='items'}
            body['settings']['opening_source']={'name':Path(body['opening_file']).name,'depth':body.get('book_depth',16)}
        if body.get('all960'):openings=[{'fen':chess.Board.from_chess960_pos(i).fen(),'name':f'Chess960 #{i}'} for i in range(960)];body['settings']['chess960']=True
        from .fingerprints import capture,verify
        if not tid or not body.get('keep_participants',True):
            for p in profiles:
                await asyncio.to_thread(verify,p)
                p['fingerprints']=await asyncio.to_thread(capture,p)
        if tid:
            async with runner.lifecycle_lock:
                result=await db.call('edit_tournament',tid,body['name'],body['settings'],body.get('setup_revision'),profiles,openings,keep_openings=body.get('keep_openings',True),backup=False)
                progress.reset(tid);runner.memory_budgets.pop(tid,None)
        else:
            result=await db.call('create_tournament',body['name'],profiles,body['settings'],openings,backup=False)
        runner.request_backup()
        return web.json_response(result)
    async def tournament_setup(request):
        if request.method=='GET':return web.json_response(await db.call('tournament_setup',request.match_info['tid']))
        return await tournaments(request)
    async def tournament(request):
        from .standings import read_snapshot
        tid=request.match_info['tid']
        result=await asyncio.to_thread(read_snapshot,db.store.path,tid,int(request.query.get('offset',0)),int(request.query.get('limit',100)),request.query.get('sort','rank'),request.query.get('direction','asc'),confidence(request),request.query.get('method','normal'),request.query.get('compact')=='1')
        result.update(revision=db.store.revision,saving_error=db.store.failure,warning=db.store.warning)
        result['progress']=progress.observe(result,sum(g['tid']==tid for g in runner.live.values()))
        return web.json_response(result)
    async def action(request):
        body=await request.json();tid=request.match_info['tid'];action=body['action']
        async with runner.lifecycle_lock:
            progress.reset(tid)
            await db.call('queue_call','manual_action',tid,action)
            if action=='start':await db.call('set_state',tid,'running')
            elif action in ('pause','cancel'):await runner.pause(tid,action=='cancel')
            elif action=='requeue':return web.json_response(await db.call('requeue',tid,body.get('ids'),body.get('reason'),body.get('mode','diagnostic'),body.get('invalidate',False)))
            else:raise ValueError('Unknown action')
        return web.json_response({'ok':True})
    async def events_api(request):
        eid=request.match_info.get('eid')
        if request.method=='GET':
            offset=int(request.query.get('offset',0))
            return web.json_response(await db.call('event_call','detail',eid,offset,request.query.get('export')=='1') if eid else await db.call('event_call','listing',offset))
        b=await request.json()
        async with runner.lifecycle_lock:
            if eid:
                if b['action']=='run' and (runner.error or db.store.failure):raise ValueError(runner.error or db.store.failure)
                result=await db.call('event_call','command',eid,b['action'],b.get('revision'))
            elif b.get('preview'):
                body,total=await db.call('event_call','prepare',b['source_tid'],b['definition'])
                return web.json_response({'regular_games':total,'participants':len(body['profiles'])})
            else:result=await db.call('event_call','create',b['name'],b['source_tid'],b['definition'])
        if not eid:await db.call('backup')
        return web.json_response(result)
    async def tournament_queue(request):
        if request.method=='GET':
            if request.query.get('configuration')=='1':return web.json_response(await db.call('queue_call','configuration'))
            return web.json_response(await db.call('queue_call','page',int(request.query.get('offset',0)),request.query.get('search',''),request.query.get('filter',''),request.query.get('sort','position'),request.query.get('direction','asc')))
        b=await request.json();action=b['action']
        async with runner.lifecycle_lock:
            if action in ('run','resume_selected') and (runner.error or db.store.failure):raise ValueError(runner.error or db.store.failure)
            if action=='add':
                result=await db.call('queue_call','add',b.get('ids'),b.get('all_ready',False))
            elif action=='configure':
                result=await db.call('queue_call','configure',b.get('revision'),b.get('execution_mode'),b.get('resources'))
                runner.fair_share.reservation=None
            elif action in ('pause_selected','resume_selected','set_limits'):
                result=await db.call('queue_call','manage',b.get('revision'),action,b.get('ids'),b.get('priority'),b.get('concurrency'))
            else:
                if action=='run' and (runner.error or db.store.failure):raise ValueError(runner.error or db.store.failure)
                result=await db.call('queue_call','command',action,b.get('revision'),b.get('tid'),b.get('not_before',0))
                if action=='pause' and result['active_tid']:
                    t=await db.call('tournament',result['active_tid'])
                    if t['state'] in ('running','draining'):await runner.pause(t['id'])
            if action in ('configure','set_limits') and db.store.queue_status['execution_mode']=='parallel':
                for tid in list(runner.runtime.sessions):
                    priority=await db.call('one','SELECT priority FROM tournament_queue WHERE tid=?',(tid,))
                    await runner.runtime.shared_changed(tid,db.store.queue_status['resources']|{'gpu_default_limit':1},priority['priority'] if priority else 2)
        return web.json_response(result)
    async def concurrency(request):
        body=await request.json();tid=request.match_info['tid']
        result=await runner.set_concurrency(tid,body.get('concurrency'))
        if result['previous']!=result['concurrency']:progress.reset(tid)
        return web.json_response(result)

    async def delete_tournament(request):
        tid=request.match_info['tid']
        if request.method=='GET':return web.json_response(await db.call('deletion_preview',tid))
        body=await request.json()
        if body.get('confirmed') is not True:raise ValueError('Confirm tournament deletion first')
        async with report_lock:
            async with rating_lock:
                result=await runner.delete_tournament(tid,body.get('name'))
                report_cache.clear()
        return web.json_response(result)
    async def engine_failures(request):
        return web.json_response(await db.call('engine_failures',request.match_info['tid'],int(request.match_info['slot']),request.query.get('reason','timeout'),int(request.query.get('offset',0))))

    async def games(request):
        from .history import read_game_page
        return web.json_response(await asyncio.to_thread(read_game_page,db.store.path,request.match_info['tid'],request.query.get('reason',''),int(request.query.get('offset',0)),int(request.query.get('limit',100))))
    async def game(request):return web.json_response(await db.call('game_detail',request.match_info['gid']))
    async def adjudicate(request):
        body=await request.json()
        if body.get('confirmed') is not True:raise ValueError('Confirm the game and adjudication result first')
        return web.json_response(await runner.adjudicate(request.match_info['tid'],request.match_info['gid'],body.get('attempt'),body.get('result'),body.get('note')))
    async def numbered_game(request):
        number=int(request.match_info['number'])
        if number<1:raise ValueError('Enter a positive game number')
        row=await db.call('one','SELECT id FROM games WHERE tid=? AND number=?',(request.match_info['tid'],number-1))
        if not row:raise ValueError('This game has not been scheduled yet')
        return web.json_response({'id':row['id']})
    async def h2h(request):return web.json_response(await db.call('h2h_page',request.match_info['tid'],int(request.match_info['slot']),int(request.query.get('offset',0)),request.query.get('q',''),confidence(request)))
    async def crosstable(request):
        from .reports import crosstable as calculate
        return web.json_response(await asyncio.to_thread(calculate,db.store.path,request.match_info['tid'],int(request.query.get('row',0)),int(request.query.get('column',0)),request.query.get('q',''),confidence(request)))
    async def participants(request):
        tid=request.match_info['tid'];search='%'+request.query.get('q','')+'%';offset=max(0,int(request.query.get('offset',0)))
        clause="tid=? AND json_extract(profile,'$.name') LIKE ?"
        total=await db.call('one','SELECT count(*) n FROM participants WHERE '+clause,(tid,search))
        rows=await db.call('rows','SELECT slot,profile FROM participants WHERE '+clause+' ORDER BY slot LIMIT 50 OFFSET ?',(tid,search,offset))
        return web.json_response({'total':total['n'],'items':[{'slot':r['slot'],'name':json.loads(r['profile'])['name']} for r in rows]})
    from collections import OrderedDict
    report_cache=OrderedDict();report_lock=asyncio.Lock()
    rating_executor=None;rating_lock=asyncio.Lock()
    async def calculate_in_background(function,*args):
        nonlocal rating_executor
        from .ratings import background_priority
        async with rating_lock:
            if rating_executor is None:rating_executor=ProcessPoolExecutor(max_workers=1,mp_context=multiprocessing.get_context('spawn'),initializer=background_priority)
            return await asyncio.get_running_loop().run_in_executor(rating_executor,function,*args)
    async def pool_ratings(request):
        tid=request.match_info['tid']
        if request.method=='POST':
            body=await request.json();return web.json_response(await db.call('save_rating_anchor',tid,body['slot'],body['rating']))
        from .ratings import pool_report
        offset=int(request.query.get('offset',0));search=request.query.get('q','');export=request.query.get('export','')
        if export not in ('','csv','json'):raise ValueError('Unknown rating export')
        result=await calculate_in_background(pool_report,str(db.store.path),tid,offset,50,search,export,confidence(request),request.query.get('sort','slot'),request.query.get('direction','asc'))
        if export=='csv':return web.Response(text=result,content_type='text/csv',headers={'Content-Disposition':'attachment; filename="pool-ratings.csv"'})
        return web.json_response(result,headers={'Content-Disposition':'attachment; filename="pool-ratings.json"'} if export else None)
    async def chart_series(request):
        from .trends import tournament_series,game_series
        tid=request.match_info['tid']
        if 'game' in request.query:result=await calculate_in_background(game_series,str(db.store.path),tid,int(request.query['game']))
        else:result=await calculate_in_background(tournament_series,str(db.store.path),tid,int(request.query.get('slot',0)),600,confidence(request))
        return web.json_response(result)
    async def tournament_report(request):
        from .i18n import render_report,language
        code=language(request.query.get('language',request.headers.get('X-Arena-Language',app['presentation']['language'])))
        return web.json_response({'html':await report_jobs.render(str(db.store.path),request.match_info['tid'],confidence(request),request.query.get('all_engines')=='1',request.query.get('technical','1')!='0',code),'language':code})
    async def start_report(request):
        from .i18n import language
        body=await request.json()
        code=language(request.headers.get('X-Arena-Language',app['presentation']['language']))
        # Validate before launching a process; report reads one committed snapshot.
        tid=request.match_info['tid']
        if not await db.call('one','SELECT 1 FROM tournaments WHERE id=?',(tid,)):raise ValueError('Tournament not found')
        return web.json_response(await report_jobs.start(str(db.store.path),tid,confidence_level(body.get('confidence',95)),bool(body.get('all_engines')),bool(body.get('technical')),code))
    async def report_job(request):
        ident=request.match_info['job']
        if request.method=='DELETE':await report_jobs.cancel(ident)
        return web.json_response(report_jobs.status(ident))
    async def opening_report(request):
        from .reports import opening_report as calculate
        tid=request.match_info['tid'];slot=int(request.query.get('slot',-1));offset=int(request.query.get('offset',0));export=request.query.get('export','')
        if export not in ('','csv','json'):raise ValueError('Unknown opening export')
        async with report_lock:
            rev=await db.call('one','SELECT revision FROM report_revisions WHERE tid=?',(tid,));key=(tid,slot,offset,rev['revision'] if rev else 0)
            if not export and key in report_cache:
                result=report_cache[key];report_cache.move_to_end(key)
            else:
                result=await asyncio.to_thread(calculate,db.store.path,tid,slot,offset,50,export)
                if not export:
                    key=(tid,slot,offset,result['revision']);report_cache[key]=result;report_cache.move_to_end(key)
                    while len(report_cache)>8:report_cache.popitem(last=False)
        if export=='csv':return web.Response(text=result,content_type='text/csv',headers={'Content-Disposition':'attachment; filename="opening-results.csv"'})
        return web.json_response(result)
    async def selected_participants(request):
        b=await request.json();offset=max(0,int(b.get('offset',0)))
        if b.get('recorded_participants'):
            rows=await db.call('rows',"SELECT slot,json_extract(profile,'$.name') name FROM participants WHERE tid=? ORDER BY slot LIMIT 50 OFFSET ?",(b['recorded_participants'],offset))
        elif b.get('all_profiles'):
            rows=await db.call('rows','SELECT name FROM profiles ORDER BY name,id LIMIT 50 OFFSET ?',(offset,))
            rows=[dict(r,slot=i+offset) for i,r in enumerate(rows)]
        else:
            ids=b.get('profiles',[])
            rows=await db.call('rows',"SELECT CAST(j.key AS INTEGER) slot,p.name FROM json_each(?) j JOIN profiles p ON p.id=j.value ORDER BY CAST(j.key AS INTEGER) LIMIT 50 OFFSET ?",(encode(ids),offset))
        return web.json_response(rows)
    async def schedule_preview(request):
        b=await request.json();s=DEFAULTS|b['settings'];n=int(b['participants']);legs=2 if s['paired'] else 1
        for key in ('cycles','rounds','playoff_limit','playoff_cycles','ladder_distance'):
            if not isinstance(s[key],int) or isinstance(s[key],bool) or s[key]<1:raise ValueError(key+' must be a positive integer')
        if s['format']=='ladder' and s['ladder_distance']>=n:raise ValueError('Ladder distance must be smaller than the participant count')
        from .knockout import base_pairs
        base=await asyncio.to_thread(base_pairs,n,s);maximum=base
        if s['format']=='double_elimination':maximum+=s['cycles']
        if s['format'] in ('knockout','double_elimination') and s.get('knockout_tiebreak')=='playoff':maximum+=(n-1 if s['format']=='knockout' else 2*n-1)*s['playoff_limit']*s['playoff_cycles']
        unbounded=s['format'] in ('knockout','double_elimination') and s.get('knockout_tiebreak')=='continuous'
        return web.json_response({'scheduled_games':str(base*legs),'maximum_games':None if unbounded else str(maximum*legs),'conditional':unbounded or maximum!=base}|({'unbounded':True} if unbounded else {}))
    async def resource_preview(request):
        from .resources import recommend
        b=await request.json();selected=set(b.get('profiles',[]));profiles=[json.loads(r['body']) for r in await db.call('rows','SELECT id,body FROM profiles') if b.get('all_profiles') or r['id'] in selected]
        if b.get('recorded_participants'):
            profiles=[json.loads(r['profile']) for r in await db.call('rows','SELECT profile FROM participants WHERE tid=? ORDER BY slot',(b['recorded_participants'],))]
        preset=b.get('resource_preset')
        if preset:
            for p in profiles:
                for name,default in [('threads',1),('hash',1024)]:
                    p[name]=int(preset.get(name,default))
                    for key in p.get('options',{}):
                        if key.casefold()==name:p['options'][key]=p[name]
        return web.json_response(recommend(profiles,DEFAULTS|b['settings']))
    async def pairing_review(request):
        from .rounds import build_plan,match_key
        tid=request.match_info['tid'];t=await db.call('tournament',tid);offset=int(request.query.get('offset',0));limit=50
        participants=await db.call('rows','SELECT p.slot,p.profile,r.seed FROM participants p JOIN rankings r ON p.tid=r.tid AND p.slot=r.slot WHERE p.tid=? ORDER BY p.slot LIMIT ? OFFSET ?',(tid,limit,offset))
        participants=[{'slot':r['slot'],'seed':r['seed']+1,'name':json.loads(r['profile'])['name']} for r in participants]
        records=await db.call('rows','SELECT round,body FROM round_state WHERE tid=? ORDER BY round DESC LIMIT 1',(tid,));saved=json.loads(records[0]['body']) if records else None
        ctx=await db.call('pairing_context',tid);plan=await asyncio.to_thread(build_plan,ctx) if ctx else None
        summary=[]
        for a,b in (saved or {}).get('matches',[])[offset:offset+limit]:
            ap=await db.call('participant',tid,a);bp=await db.call('participant',tid,b);key=match_key(a,b)
            summary.append({'a':a,'b':b,'a_name':ap['name'],'b_name':bp['name'],'playoff_stages':len(saved.get('playoffs',{}).get(key,[])),'manual_winner':saved.get('manual_winners',{}).get(key)})
        return web.json_response({'format':t['settings']['format'],'state':t['state'],'round':t['round'],'participants':participants,'participant_count':t['participants'],'matches':summary,'match_count':len((saved or {}).get('matches',[])),'byes':(saved or {}).get('byes',[]),'ladder_order':(saved or {}).get('final_ladder_order',(saved or {}).get('ladder_order')),
          'signature':ctx['signature'] if ctx else None,'next_kind':plan['kind'] if plan else None,'next_round':plan['round'] if plan else None,'next_matches':plan.get('matches') if plan and t['settings']['format']=='swiss' else None,'next_byes':plan.get('byes',[]) if plan else [],'manual_ties':plan.get('manual',[])[offset:offset+limit] if plan else [],'manual_tie_count':len(plan.get('manual',[])) if plan else 0,'attention':t['dependency'] or (plan or {}).get('note',''),'ready':ctx is not None})
    async def pairing_action(request):
        b=await request.json();tid=request.match_info['tid']
        if b['action']=='manual_round':value=await db.call('manual_pairings',tid,b['matches'],b.get('byes',[]),b.get('allow_rematches',False),b.get('signature'))
        elif b['action']=='manual_winner':value=await db.call('manual_tiebreak',tid,int(b['a']),int(b['b']),int(b['winner']))
        else:raise ValueError('Unknown pairing action')
        return web.json_response(value)
    async def export(request):
        tid=request.match_info['tid'];fmt=request.match_info['fmt']
        if fmt=='pgn':
            from .pgn_export import stream_official
            return await stream_official(request,db.store.path,tid)
        elif fmt=='html':
            from .i18n import render_report,language
            code=language(request.query.get('language',request.headers.get('X-Arena-Language',app['presentation']['language'])))
            data=await report_jobs.render(str(db.store.path),tid,confidence(request),request.query.get('all_engines')=='1',request.query.get('technical','1')!='0',code);ctype='text/html'
        elif fmt in ('json','csv'):
            from .standings import read_snapshot
            t=await db.call('tournament',tid);s=await asyncio.to_thread(read_snapshot,db.store.path,tid,0,t['participants'],request.query.get('sort','rank'),request.query.get('direction','asc'),confidence(request),request.query.get('method','normal'))
            if fmt=='json':data=json.dumps(s,indent=2);ctype='application/json'
            else:
                from .stat_exports import standings_csv
                data=standings_csv(s['standings'],request.query.get('method','normal'));ctype='text/csv'
        else:raise ValueError('Unknown export type')
        return web.Response(text=data,content_type=ctype,headers={'Content-Disposition':f'attachment; filename="official-{tid}.{fmt}"'})
    async def presets(request):
        if request.method=='GET':return web.json_response([{'name':r['name'],'settings':json.loads(r['body'])} for r in await db.call('rows','SELECT * FROM presets ORDER BY name')])
        b=await request.json();return web.json_response(await db.call('save_preset',b['name'],b['settings'],b.get('original_name')))
    async def positions(request):
        if request.method=='GET':return web.json_response([json.loads(r['body']) for r in await db.call('rows','SELECT body FROM positions ORDER BY name')])
        b=await request.json();return web.json_response(await db.call('save_position',b['name'],b))
    async def position_preview(request):
        from .conditions import position
        return web.json_response(position(await request.json()))
    async def experiments(request):
        if request.method=='GET':return web.json_response(await db.call('rows','SELECT id,name,kind,state,total,cursor,created FROM experiments ORDER BY created DESC'))
        b=await request.json();profiles=[]
        for pid in b['profiles']:
            row=await db.call('one','SELECT body FROM profiles WHERE id=?',(pid,))
            if not row:raise ValueError('Profile not found')
            profiles.append(json.loads(row['body']))
        return web.json_response(await db.call('experiment_create',b['name'],b['kind'],profiles,b['settings'],b.get('path')))
    async def experiment(request):
        return web.json_response(await db.call('experiment_get',request.match_info['eid'],int(request.query.get('offset',0)),None if request.query.get('all')=='1' else 50))
    async def experiment_action(request):
        b=await request.json();eid=request.match_info['eid'];action=b['action']
        async with runner.lifecycle_lock:
            if action=='start':await db.call('experiment_state',eid,'running')
            elif action in ('pause','cancel'):
                await db.call('experiment_state',eid,'paused')
                if action=='cancel' and runner.experiment_id==eid and runner.experiment_task:
                    runner.experiment_task.cancel();await asyncio.gather(runner.experiment_task,return_exceptions=True)
            else:raise ValueError('Unknown experiment action')
        return web.json_response({'ok':True})
    async def retry_saving(request):
        if runner.tasks or (runner.experiment_task and not runner.experiment_task.done()):raise ValueError('Stop active games and experiments before retrying storage recovery')
        await db.call('retry_saving');runner.error='';return web.json_response({'ok':True})
    async def shutdown(request):
        asyncio.get_running_loop().call_later(.5,lambda:app['stop'].set());return web.json_response({'ok':True})
    async def preferences(request):
        if request.method=='GET':
            row=await db.call('one',"SELECT body FROM preferences WHERE name='ui'")
            return web.json_response(json.loads(row['body']) if row else {})
        value=await request.json()
        if not isinstance(value,dict):raise ValueError('Invalid workspace preferences')
        config=hardware_settings(value.get('hardware'))
        await db.call('execute',"INSERT INTO preferences VALUES('ui',?) ON CONFLICT(name) DO UPDATE SET body=excluded.body WHERE body<>excluded.body",(encode(value),),report_change=False)
        from .i18n import language
        app['presentation']['language']=language(value.get('language','en'))
        if config!=hardware.config:hardware.configure(config)
        return web.json_response({'ok':True})
    async def ui_metrics(request):
        metrics=await request.json();app['ui_metrics']=metrics
        return web.json_response({'ok':True})
    async def storage(request):
        from .storage import inventory,ensure_idle
        if request.method=='GET':return web.json_response(await asyncio.to_thread(inventory,db.store))
        if runner.storage_task and not runner.storage_task.done():raise ValueError('Storage cleanup is already in progress')
        body=await request.json()
        if body.get('action')=='optimize':
            async with runner.lifecycle_lock:
                if runner.tasks or (runner.experiment_task and not runner.experiment_task.done()):raise ValueError('Stop or pause and drain all games and experiments first')
                await asyncio.get_running_loop().run_in_executor(db.executor,ensure_idle,db.store)
                from .storage import progress as storage_progress
                storage_progress(db.store,busy=True,phase='Preparing storage cleanup',error='')
                runner.storage_task=asyncio.create_task(runner.optimize_storage())
                # The progress endpoint reports failures; retrieve the exception too.
                def storage_done(task):
                    if task.cancelled():storage_progress(db.store,busy=False,phase='Interrupted',error='Reopen the program or retry cleanup to continue.')
                    elif (error:=task.exception()) is not None:storage_progress(db.store,busy=False,phase='Failed',error=str(error))
                runner.storage_task.add_done_callback(storage_done)
            return web.json_response({'started':True})
        if body.get('action')=='settings':
            return web.json_response(await db.call('save_storage_settings',body['settings']))
        raise ValueError('Unknown storage action')
    async def pieces(request):
        from .pieces import list_sets,import_set
        if request.method=='GET':return web.json_response(list_sets(db.store.folder))
        b=await request.json();return web.json_response(await asyncio.to_thread(import_set,db.store.folder,b['folder'],b.get('name','')))
    async def piece_file(request):
        from .pieces import FILES,BUILTIN_SETS
        group=request.match_info['group'];file=request.match_info['file']
        if file not in FILES or (group not in dict(BUILTIN_SETS) and not __import__('re').fullmatch(r'custom-[a-f0-9]{32}',group)):raise web.HTTPNotFound()
        path=(ROOT/'ui'/'pieces' if not group.startswith('custom-') else db.store.folder/'pieces')/group/file
        if not path.is_file():raise web.HTTPNotFound()
        return web.FileResponse(path,headers={'Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'"})
    async def texture_file(request):
        file=request.match_info['file']
        if file not in {name+ext for name in ('maple','ash','oak','walnut','rosewood','ebony') for ext in ('.svg','.png')}:raise web.HTTPNotFound()
        return web.FileResponse(ROOT/'ui'/'textures'/file)
    app.router.add_get('/textures/{file}',texture_file)
    app.router.add_get('/',index);app.router.add_get('/assets/{name}',static)
    app.router.add_route('*','/api/move-books',move_books);app.router.add_get('/api/status',status);app.router.add_route('*','/api/profiles',profiles)
    app.router.add_get('/api/search/{aid}',search_detail)
    app.router.add_get('/api/hardware',hardware_probe)
    app.router.add_post('/api/profiles/import',import_profiles);app.router.add_post('/api/scan',scan)
    app.router.add_post('/api/profiles/import-preview',external_profiles)
    app.router.add_get('/api/games/{gid}/moves',game_moves)
    app.router.add_get('/api/tournaments/{tid}/completion',completed_tournament)
    app.router.add_post('/api/profiles/discover',discover_profile)
    app.router.add_post('/api/profiles/delete',delete_profiles)
    app.router.add_route('*','/api/tournaments',tournaments);app.router.add_get('/api/tournaments/{tid}',tournament)
    app.router.add_get('/api/events',events_api);app.router.add_post('/api/events',events_api)
    app.router.add_get('/api/events/{eid}',events_api);app.router.add_post('/api/events/{eid}',events_api)
    app.router.add_get('/api/tournament-queue',tournament_queue);app.router.add_post('/api/tournament-queue',tournament_queue)
    app.router.add_route('*','/api/tournaments/{tid}/delete',delete_tournament)
    app.router.add_get('/api/tournaments/{tid}/setup',tournament_setup);app.router.add_post('/api/tournaments/{tid}/setup',tournament_setup)
    app.router.add_post('/api/tournaments/{tid}/action',action);app.router.add_get('/api/tournaments/{tid}/games',games)
    app.router.add_get('/api/games/{gid}',game);app.router.add_get('/api/tournaments/{tid}/h2h/{slot}',h2h)
    app.router.add_get('/api/tournaments/{tid}/game-number/{number}',numbered_game)
    app.router.add_post('/api/schedule-preview',schedule_preview)
    app.router.add_post('/api/selected-participants',selected_participants)
    app.router.add_post('/api/opening-preview',opening_preview)
    app.router.add_post('/api/resource-preview',resource_preview)
    app.router.add_get('/api/tournaments/{tid}/participants',participants);app.router.add_get('/api/tournaments/{tid}/openings',opening_report)
    app.router.add_route('*','/api/tournaments/{tid}/ratings',pool_ratings)
    app.router.add_post('/api/tournaments/{tid}/games/{gid}/adjudicate',adjudicate)
    app.router.add_get('/api/tournaments/{tid}/crosstable',crosstable)
    app.router.add_get('/api/tournaments/{tid}/series',chart_series)
    app.router.add_get('/api/tournaments/{tid}/report',tournament_report)
    app.router.add_post('/api/tournaments/{tid}/report-jobs',start_report)
    app.router.add_route('*','/api/report-jobs/{job}',report_job)
    app.router.add_get('/api/tournaments/{tid}/pairings',pairing_review);app.router.add_post('/api/tournaments/{tid}/pairings',pairing_action)
    async def pgn_options(request):
        from .pgn_options import schema
        return web.json_response(schema())
    async def pgn_preview(request):
        from .pgn_export import preview
        settings=await request.json()
        return web.json_response(await asyncio.to_thread(preview,db.store.path,request.match_info['tid'],settings))
    app.router.add_post('/api/tournaments/{tid}/concurrency',concurrency)
    app.router.add_get('/api/tournaments/{tid}/failures/{slot}',engine_failures)
    app.router.add_get('/api/pgn-options',pgn_options)
    app.router.add_post('/api/tournaments/{tid}/pgn-preview',pgn_preview)
    app.router.add_get('/api/export/{tid}/{fmt}',export);app.router.add_route('*','/api/presets',presets)
    app.router.add_route('*','/api/positions',positions);app.router.add_post('/api/position-preview',position_preview)
    app.router.add_post('/api/retry-saving',retry_saving);app.router.add_post('/api/shutdown',shutdown)
    app.router.add_route('*','/api/experiments',experiments);app.router.add_get('/api/experiments/{eid}',experiment)
    app.router.add_post('/api/experiments/{eid}/action',experiment_action)
    app.router.add_route('*','/api/preferences',preferences);app.router.add_post('/api/ui-metrics',ui_metrics)
    app.router.add_route('*','/api/storage',storage)
    app.router.add_route('*','/api/pieces',pieces);app.router.add_get('/pieces/{group}/{file}',piece_file)
    async def shutdown_reports(app):await report_jobs.close()
    app.on_shutdown.append(shutdown_reports)
    async def cleanup(app):
        await report_jobs.close()
        await hardware.close()
        await runner.close()
        if rating_executor is not None:await asyncio.to_thread(rating_executor.shutdown,wait=True,cancel_futures=True)
    app.on_cleanup.append(cleanup)
    await runner.start()
    return app

async def main_async(args):
    token=args.token or secrets.token_urlsafe(32);app=await create_app(args.data,token);app['stop']=asyncio.Event()
    app['db'].store.progress_callback=lambda value:print('ARENA_BACKUP '+json.dumps(value),flush=True)
    server=web.AppRunner(app);await server.setup();site=web.TCPSite(server,'127.0.0.1',args.port);await site.start()
    port=site._server.sockets[0].getsockname()[1]
    info={'port':port,'token':token,'pid':os.getpid()}
    if args.ready:Path(args.ready).write_text(json.dumps(info),encoding='utf-8')
    print(f'Engine Arena ready on 127.0.0.1:{port}',flush=True)
    try:await app['stop'].wait()
    finally:await server.cleanup()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--data',default='data');parser.add_argument('--port',type=int,default=0);parser.add_argument('--token');parser.add_argument('--ready');args=parser.parse_args()
    try:asyncio.run(main_async(args))
    except KeyboardInterrupt:pass

if __name__=='__main__':main()
