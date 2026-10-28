import asyncio
import copy
import json
import sqlite3
import time
import pytest
from aiohttp.test_utils import TestClient, TestServer
from arena.broadcast import settings
from arena.broadcast_design import design
from arena.broadcast_server import Hub, make_app
from arena.broadcast_data import read


def test_migration_and_partial_scene_inheritance():
    c=settings({'theme':'charcoal','ticker_seconds':150,'board_light':'ash','board_dark':'rosewood'})
    assert c==settings(c)
    assert c['design']['scenes'][0]['panels'][1]['type']=='board'
    c['design']['scenes'][0]['appearance']={'scene3d':{'environment':'live-club'},'ticker_style':{'score_color':'#ffaabb'}}
    normalized=settings(c)
    assert normalized['design']['scenes'][0]['appearance']==c['design']['scenes'][0]['appearance']
    assert normalized['ticker_seconds']==150


def test_schema_bounds_duplicates_and_graphs():
    scene={'id':'scene-1','panels':[{'id':'p','type':'evalgraph','x':99,'y':-20,'w':900,'h':float('nan'),
        'series_colors':{'Engine':'#ff0077'},'series_styles':{'Engine':'bars'},'metric':'nps'},
        {'id':'p','type':'board'},{'id':'p','type':'board'},{'id':'p-copy','type':'text'}]}
    d=design({'scenes':[scene,scene,{'id':'scene-1-copy'}],'width':float('inf')})
    assert len(set(s['id'] for s in d['scenes']))==3
    ps=d['scenes'][0]['panels'];assert len(set(p['id'] for p in ps))==len(ps)==3
    assert ps[0]['x']==98 and ps[0]['w']==2 and ps[0]['y']==0
    assert ps[0]['series_styles']['Engine']=='bars' and ps[0]['metric']=='nps'
    assert settings({'arrow_color':'url(file:/secret)','board_mode':'bogus','scene3d':{'fps':60}})['scene3d']['fps']==30


def test_typography_migration_bounds_and_roundtrip():
    old = settings({'design': {'scenes': [{'id': 'one', 'panels': [{'type': 'ratings'}]}]}})
    panel = old['design']['scenes'][0]['panels'][0]
    assert (panel['heading_size'], panel['detail_size'], panel['auto_fit']) == (0, 0, True)
    panel.update(heading_size=23, detail_size=19, auto_fit=False)
    assert settings(json.loads(json.dumps(old))) == old
    panel.update(heading_size=float('inf'), detail_size=-5)
    clean = settings(old)['design']['scenes'][0]['panels'][0]
    assert clean['heading_size'] == 0 and clean['detail_size'] == 0
    panel.update(heading_size=999, detail_size=999)
    clean = settings(old)['design']['scenes'][0]['panels'][0]
    assert clean['heading_size'] == 80 and clean['detail_size'] == 80


def test_evaluation_bar_size_bounds_and_scene_inheritance():
    c = settings({})
    assert (c['eval_width'], c['eval_text_size']) == (27, 16)
    c.update(eval_width=48, eval_text_size=24)
    c['design']['scenes'][0]['appearance'] = {'eval_width': 56, 'eval_text_size': 28}
    assert settings(json.loads(json.dumps(c))) == c
    c.update(eval_width=999, eval_text_size=-1)
    c['design']['scenes'][0]['appearance'] = {'eval_width': -1, 'eval_text_size': 999}
    clean = settings(c)
    assert (clean['eval_width'], clean['eval_text_size']) == (80, 10)
    assert clean['design']['scenes'][0]['appearance'] == {'eval_width': 16, 'eval_text_size': 40}
    assert settings({'eval_width': float('inf'), 'eval_text_size': 'bad'})['eval_width'] == 27


def test_program_event_and_hidden_board_wait_until_complete():
    h=Hub(None,{'tid':'one'});h.director.current={'attempt':'keep'}
    other=settings(h.director.config|{'tid':'two'})
    assert not h.apply_program(other)
    assert h.director.config['tid']=='one' and h.director.current['attempt']=='keep'
    h.director.current=None;h.advance_program();assert h.director.config['tid']=='two' and not h.pending
    h.director.current={'attempt':'keep-again'}
    c=copy.deepcopy(h.director.config);c['design']['scenes'][0]['panels'][1]['visible']=False
    assert not h.apply_program(c), 'Even hiding the board in the same scene must wait'
    assert h.director.current['attempt']=='keep-again'
    assert h.apply_program(c,cut=True) and h.director.current is None


def test_layout_change_preserves_game_and_playlist_skips_paused():
    h=Hub(None,{'tid':'one','event_rotation':True,'playlist':['one','paused','two'],'event_seconds':30})
    h.tournaments=[{'id':'one','state':'running'},{'id':'paused','state':'paused'},{'id':'two','state':'running'}]
    h.director.current={'attempt':'keep'}
    c=copy.deepcopy(h.director.config);c['design']['scenes'][0]['id']='new';c['design']['active']='new'
    assert h.apply_program(c) and h.director.current['attempt']=='keep'
    h.event_since=0;h.advance_program(100);assert h.director.config['tid']=='one'
    h.director.current=None;h.advance_program(101);assert h.director.config['tid']=='two'


def test_data_read_is_current_field_bounded_and_private(tmp_path):
    file=tmp_path/'fixture.sqlite'
    with sqlite3.connect(file) as db:
        db.executescript('CREATE TABLE tournaments(id,settings);CREATE TABLE participants(tid,slot,profile);CREATE TABLE games(tid,number,white,black,state,invalid);')
        db.execute('INSERT INTO tournaments VALUES(?,?)',('one',json.dumps({'rr_withdrawn_excluded':[2],'paired':True,'secret':'PRIVATE'})))
        for slot in range(3):db.execute('INSERT INTO participants VALUES(?,?,?)',('one',slot,json.dumps({'id':str(slot),'name':'Engine '+str(slot),'threads':1,'path':'PRIVATE'})))
        for n in range(30):db.execute('INSERT INTO games VALUES(?,?,?,?,?,?)',('one',n,0,1,'pending',0))
    before=file.read_bytes();result=read(file,'one')
    assert len(result['people'])==2 and len(result['upcoming'])==20 and 'PRIVATE' not in json.dumps(result)
    assert file.read_bytes()==before


def test_selected_event_counts_and_real_observations(tmp_path):
    h=Hub(None,{'tid':'one'});h.folder=tmp_path
    h.observe_panels({'live':[{'tid':'one'},{'tid':'two'}],'active_games':2,'hardware':{'identity':{'cpu_name':'Fixture','hostname':'PRIVATE'},'metrics':{'cpu_percent':30}}})
    assert h.status=={'active':1,'all_active':2} and 'PRIVATE' not in json.dumps(h.hardware)
    h.summary={'completed':10,'standings':[{'name':'A','points':7}]}
    h.director.config['design']['scenes'][0]['panels'].append({'type':'scoregraph','visible':True})
    h.record_observation(1000);h.record_observation(1001)
    assert len(h.observations)==1 and h.observations[0]['scores']==[{'name':'A','points':7}]
    assert json.loads((tmp_path/'observations.json').read_text())==h.observations


def test_header_observations_mark_pause_and_schedule_boundaries(tmp_path):
    h=Hub(None,{'tid':'one'});h.folder=tmp_path
    h.summary={'completed':10,'total':100,'state':'running'}
    h.record_observation(1000);h.record_observation(1001)
    assert len(h.observations)==1 and h.observations[0]['state']=='running'
    h.summary['state']='paused';h.record_observation(1002)
    h.summary['state']='running';h.record_observation(1003)
    h.summary['total']=120;h.record_observation(1004)
    h.summary['completed']=9;h.record_observation(1005)
    assert len(h.observations)==5
    h.summary_at=1000;h.record_observation(1400)
    assert len(h.observations)==5, 'Do not sample stale metadata'


def test_header_options_migrate_and_roundtrip():
    c=settings({});p=c['design']['scenes'][0]['panels'][0]
    assert p['logo_size']==96 and p['header_progress'] and p['header_eta']
    p.update(logo_size=130,header_progress=False,header_eta=False)
    assert settings(json.loads(json.dumps(c)))==c
    p['logo_size']=999
    assert settings(c)['design']['scenes'][0]['panels'][0]['logo_size']==180


def test_private_validation_and_image_staging(tmp_path):
    async def run():
        import io
        from PIL import Image
        h=Hub(None,{'tid':'one'});h.tournaments=[{'id':'one'}]
        async with TestClient(TestServer(make_app(h,tmp_path,'view','control'))) as client:
            origin=str(client.make_url('')).rstrip('/');headers={'Origin':origin}
            assert (await client.post('/validate?key=view',json={},headers=headers)).status==403
            r=await client.post('/validate?key=control',json={'design':{'width':9000}},headers=headers)
            assert (await r.json())['design']['width']==3840 and not (tmp_path/'config.json').exists()
            assert (await client.get('/preview?key=view')).status==403
            assert (await client.get('/assets/broadcast-designer.js')).status==200
            assert (await client.get('/assets/app.js')).status==404
            assert (await client.post('/upload?key=control',data=b'not an image',headers=headers)).status==400
            b=io.BytesIO();Image.new('RGB',(40,40),'red').save(b,'PNG')
            r=await client.post('/upload?key=control',data=b.getvalue(),headers=headers);name=(await r.json())['image']
            assert (await client.get('/media/'+name)).status==200
            assert (await client.get('/media/config.json')).status==404
            assert (await client.get('/assets/board3d-studio.js')).status==200
    asyncio.run(run())
