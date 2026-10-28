import copy
import json
import chess
import pytest
from aiohttp.test_utils import TestClient, TestServer
from arena.broadcast import Director, Headlines, settings, thinking_move
from arena.broadcast_server import Hub, make_app


def game(a='a',ply=0):
    return dict(tid='test',game='g'+a,attempt=a,number=1,ply=ply,fen=chess.STARTING_FEN,
                white={'name':'White','id':'w','path':'PRIVATE'},black={'name':'Black','id':'b'},
                clocks={'white':{'remaining':180,'control':{'kind':'fischer','increment':2}}},
                clock_active='white',search_elapsed=2,info={'cp':15,'pv':'e2e4 e7e5','secret':'PRIVATE'})


def page(a='a',end=True):
    b=chess.Board();rows=[]
    for i,san in enumerate(['e4','e5','Qh5','Nc6','Bc4','Nf6','Qxf7#']):
        m=b.parse_san(san);side='white' if b.turn else 'black';label=str(b.fullmove_number)+('.' if b.turn else '…');b.push(m)
        rows.append(dict(ply=i-1 if i<2 else i-1,uci=m.uci(),san=san,fen=b.fen(),label=label,side=side,clocks={},info={}))
    return dict(attempt=dict(id=a,ended=20 if end else None,result='1-0',reason='checkmate',official=end,clocks={}),
                opening={'start_fen':chess.STARTING_FEN,'fen':rows[1]['fen']},opening_moves=rows[:2],
                items=rows[2:],latest_ply=5,has_more=False)


def test_start_to_finish_all_moves_and_no_switch_for_preference():
    d=Director({'tid':'test','hold':5});d.observe({'live':[game('old',40)]},10)
    assert d.current is None
    d.observe({'live':[game('old',42),game()]},11)
    assert d.current['attempt']=='a'
    d.ingest(page(),11)
    d.configure(d.config|{'preference':'follow','follow':'Other','theme':'emerald'})
    for t in range(12,19):
        d.observe({'live':[game('new',0)]},t)
        assert d.current['attempt']=='a'
    assert [m['san'] for m in d.history]==['e4','e5','Qh5','Nc6','Bc4','Nf6','Qxf7#']
    assert d.current['result']=='1-0' and d.current['phase']=='Final result'
    # A browser reload calls snapshot; it must not restart the current game.
    assert d.snapshot(20)['game']['fen']==page()['items'][-1]['fen']
    d.observe({'live':[game('new',30)]},24)
    assert d.current is None
    d.observe({'live':[game('new',30),game('fresh',1)]},25)
    assert d.current['attempt']=='fresh'


def test_ended_page_pagination_and_duplicate_moves():
    d=Director({'tid':'test'});d.observe({'live':[game()]},10)
    p=page();first=copy.deepcopy(p);first['items']=p['items'][:2];first['has_more']=True
    d.ingest(first,11);d.ingest(first,11)
    assert d.ending is None
    second=copy.deepcopy(p);second['items']=p['items'][2:];second['opening_moves']=[]
    d.ingest(second,11)
    for t in range(12,21): d.tick(t)
    assert len(d.history)==7 and d.current['phase']=='Final result'


def test_interrupt_and_reconnect_do_not_fabricate_result_or_reset():
    d=Director({'tid':'test'});g=game();d.observe({'live':[g]},10)
    p=page(end=False);p['opening_moves']=[];p['items']=[];p['latest_ply']=0;p['opening']['fen']=chess.STARTING_FEN
    d.ingest(p,10);before=d.snapshot(11)
    d.connected=False;after=d.snapshot(30)
    assert not after['connected'] and after['game']['attempt']==before['game']['attempt']
    assert after['game']['clock_age']==2.5
    d.observe({'live':[g]},31);assert d.snapshot(31)['connected']
    p['attempt'].update(ended=32,reason='interrupted',official=False,result='*');d.ingest(p,32)
    assert d.current['result'] is None and d.current['phase']=='Attempt ended'


def test_privacy_and_configuration_validation():
    d=Director({'tid':'test'});d.observe({'live':[game()]},10)
    assert 'PRIVATE' not in json.dumps(d.snapshot(10))
    s=settings({'hold':float('nan'),'ticker_size':100,'theme':'<script>','tid':'x'*500,'sound':'false'})
    assert s['hold']==15 and s['ticker_size']==56 and s['theme']=='ocean' and len(s['tid'])==200 and not s['sound']
    assert settings({})['thinking_arrows'] and settings({})['arrow_delay']==1
    assert settings({'thinking_arrows':False,'arrow_delay':99})['arrow_delay']==10
    assert not settings({'thinking_arrows':False})['thinking_arrows']


def test_thinking_arrow_uses_only_active_legal_position_and_clears_when_stale():
    g=game();fen=g['fen']
    g['searches']={'white':{'complete':False,'info':{'intention':{'fen':fen,'uci':'e2e4'}}}}
    hint=thinking_move(g,fen)
    assert (hint['from'],hint['to'],hint['san'],hint['side'])==('e2','e4','e4','white')
    for change in ({'clock_active':None},{'clock_active':'black'},{'ended':10},{'fen':'other'},
                   {'searches':{'white':{'complete':True,'info':g['searches']['white']['info']}}},
                   {'searches':{'white':{'info':{'intention':{'fen':fen,'uci':'e2e5'}}}}},
                   {'searches':{'white':{'info':{'intention':{'fen':'old','uci':'e2e4'}}}}}):
        assert thinking_move(g|change,fen) is None
    d=Director({'tid':'test'});d.observe({'live':[g]},10)
    d.loaded=True;d.tick(11)
    assert d.snapshot(11)['game']['thinking']['uci']=='e2e4'
    assert d.snapshot(20)['game']['thinking'] is None
    d.connected=False
    assert d.snapshot(11)['game']['thinking'] is None
    d.connected=True;d.queue.append(page()['items'][0]);d.next_move=100
    d.current['phase']='Catching up'
    assert d.snapshot(11)['game']['thinking'] is None
    d.queue.clear();d.ending={'official':True,'result':'1-0','reason':'test','clocks':{}}
    assert d.snapshot(12)['game']['thinking'] is None


@pytest.mark.parametrize('fen,uci,source,target,san',[
    ('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1','e1g1','e1','g1','O-O'),
    ('7k/P7/8/8/8/8/8/7K w - - 0 1','a7a8q','a7','a8','a8=Q+'),
    ('7k/8/8/3pP3/8/8/8/7K w - d6 0 1','e5d6','e5','d6','exd6')])
def test_thinking_arrow_special_moves(fen,uci,source,target,san):
    g={'fen':fen,'clock_active':'white','searches':{'white':{'info':{'intention':{'fen':fen,'uci':uci}}}}}
    hint=thinking_move(g,fen)
    assert (hint['from'],hint['to'],hint['san'])==(source,target,san)


def test_ticker_only_confirmed_official_new_results_and_upsets():
    h=Headlines();g=game()|dict(result='1-0',reason='checkmate',official=True)
    h.results([g],'test',1);assert not h.items
    h.results([g|{'attempt':'b','official':False}],'test',2);assert not h.items
    h.results([g|{'attempt':'c'}],'test',3,{'White':2000,'Black':2300})
    assert len(h.items)==1 and h.items[0]['kind']=='upsets'
    assert 'White (2000 Elo)  1-0  Black (2300 Elo) · checkmate' in h.items[0]['text']
    assert 'winner beat an opponent rated approximately 300 Elo higher in the latest rating snapshot' in h.items[0]['text']
    h.results([g|{'attempt':'c'}],'test',4);assert len(h.items)==1


@pytest.mark.parametrize('result,ratings,expected,kind',[
    ('0-1',{'White':2500.2,'Black':2200.1},'White (2500 Elo)  0-1  Black (2200 Elo)','upsets'),
    ('1/2-1/2',{'White':0,'Black':2500},'White (0 Elo)  1/2-1/2  Black (2500 Elo)','results'),
    ('1-0',{'White':None,'Black':2300},'White (Elo pending)  1-0  Black (2300 Elo)','results'),
    ('0-1',{'White':float('nan'),'Black':float('inf')},'White (Elo pending)  0-1  Black (Elo pending)','results'),
])
def test_ticker_ratings_for_each_result_and_missing_estimates(result,ratings,expected,kind):
    h=Headlines();h.results([],'test',1)
    h.results([game()|dict(result=result,reason='fixture',official=True)],'test',2,ratings)
    assert expected in h.items[0]['text']
    assert h.items[0]['kind']==kind


def test_ticker_ratings_use_exact_profiles_below_top_twenty_and_freeze_with_result():
    hub=Hub(None,{})
    hub.remember_ratings({'snapshot':100,'items':[
        {'id':f'entry-{i}','rating':3000-i,'profiles':[{'profile_id':f'p{i}','name':'Same name'}]}
        for i in range(30)]})
    g=game()|dict(result='1-0',reason='checkmate',official=True,
                 white={'id':'p28','name':'Renamed'},black={'id':'p29','name':'Same name'})
    h=hub.headlines;h.results([],'test',1)
    h.results([g],'test',2,hub.player_rating)
    original=h.items[0]['text']
    assert 'Renamed (2972 Elo)  1-0  Same name (2971 Elo)' in original
    hub.remember_ratings({'snapshot':200,'items':[
        {'id':'entry-28','rating':2999,'profiles':[{'profile_id':'p28','name':'Renamed'}]}]})
    h.results([g],'test',3,hub.player_rating)
    assert len(h.items)==1 and h.items[0]['text']==original
    # Another recorded configuration for that profile must not be guessed.
    hub.remember_ratings({'snapshot':200,'items':[
        {'id':'other-threads','rating':3300,'profiles':[{'profile_id':'p28','name':'Renamed'}]}]})
    h.results([g|{'attempt':'b'}],'test',4,hub.player_rating)
    assert 'Renamed (Elo pending)' in h.items[0]['text']


def test_appearance_settings_preserve_old_defaults_and_validate_new_fields():
    from arena.broadcast import WOODS
    old=settings({'tid':'test','theme':'emerald','pieces':'nordic','ticker_seconds':150})
    assert (old['board_light'],old['board_dark'],old['dark_lighten'],old['eval_range'])==('theme','theme',0,5)
    for wood in WOODS:
        assert settings({'board_light':wood,'board_dark':wood})['board_dark']==wood
    c=settings(old|{'theme':'charcoal','board_light':'ash','board_dark':'rosewood','dark_lighten':28,'eval_range':4,'ticker_seconds':600})
    assert (c['theme'],c['board_light'],c['board_dark'],c['dark_lighten'],c['eval_range'],c['ticker_seconds'])==('charcoal','ash','rosewood',28,4,600)
    bad=settings({'board_light':'../../secret','board_dark':'https://example.invalid/x','dark_lighten':float('nan'),'eval_range':float('inf')})
    assert (bad['board_light'],bad['board_dark'],bad['dark_lighten'],bad['eval_range'])==('theme','theme',0,5)
    bounds=settings({'dark_lighten':99,'eval_range':-1,'ticker_seconds':9999})
    assert (bounds['dark_lighten'],bounds['eval_range'],bounds['ticker_seconds'])==(60,.1,600)


def test_http_viewer_cannot_control_or_escape_assets(tmp_path):
    import asyncio
    asyncio.run(check_http(tmp_path))


async def check_http(tmp_path):
    hub=Hub(None,{'tid':'test'});hub.tournaments=[{'id':'test','name':'Test','state':'running'}]
    async with TestClient(TestServer(make_app(hub,tmp_path,'viewer','controller'))) as client:
        assert (await client.get('/feed?key=viewer')).status==200
        assert (await client.get('/config?key=viewer')).status==403
        assert (await client.post('/config?key=viewer',json={'tid':'test'})).status==403
        assert (await client.post('/config?key=controller',json={'tid':'test'},headers={'Origin':'https://evil.invalid'})).status==403
        assert (await client.get('/assets/worker-ready.json')).status==404
        origin=str(client.make_url('')).rstrip('/')
        r=await client.post('/config?key=controller',json={'tid':'test','title':'Live'},headers={'Origin':origin})
        assert r.status==200 and (await r.json())['config']['title']=='Live'
        assert (tmp_path/'config.json').exists()
        # Saving appearance neither changes the featured game nor exposes arbitrary files.
        hub.director.current={'attempt':'keep-current'}
        appearance={'tid':'test','theme':'charcoal','board_light':'ash','board_dark':'rosewood','dark_lighten':28,'eval_range':4,'ticker_seconds':150}
        r=await client.post('/config?key=controller',json=appearance,headers={'Origin':origin})
        assert r.status==200
        saved=(await r.json())['config']
        assert all(saved[k]==v for k,v in appearance.items())
        assert hub.director.current['attempt']=='keep-current'
        assert json.loads((tmp_path/'config.json').read_text())==saved
        assert settings(json.loads((tmp_path/'config.json').read_text()))==saved
        for wood in ('maple','ash','oak','walnut','rosewood','ebony'):
            r=await client.get('/assets/textures/'+wood+'.png')
            assert r.status==200 and (await r.read()).startswith(b'\x89PNG')
        for path in ('textures/ash.svg','textures/worker-ready.json','textures/../broadcast.py','textures/../../worker.py'):
            # HTTP clients normalize ../ before sending; either auth rejection
            # or the asset allowlist must prevent file disclosure.
            assert (await client.get('/assets/'+path)).status in (403,404)
