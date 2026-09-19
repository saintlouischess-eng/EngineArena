import asyncio
from collections import Counter,defaultdict
import contextlib
import io
import json
import struct
import chess
import chess.pgn
import chess.polyglot
import pytest
from aiohttp.test_utils import TestClient,TestServer
from arena.models import scheduled_pairs
from arena.openings import inspect_openings,position_key
from arena.opening_policy import capacity,round_pair,select
from arena.store import DEFAULTS,Store
from arena.server import create_app


def pool(count=20):
    board=chess.Board();items=[]
    for move in list(board.legal_moves)[:count]:
        board.push(move);items.append({'fen':board.fen(),'name':move.uci()});board.pop()
    return items


def test_duplicate_fens_and_pgn_transpositions(tmp_path):
    source=tmp_path/'positions.fen';items=pool(2)
    source.write_text(items[0]['fen']+'\n'+items[0]['fen'].rsplit(' ',2)[0]+' 9 17\n'+items[1]['fen']+'\n')
    result=inspect_openings(source)
    assert result['unique_positions']==2 and result['duplicates_removed']==1
    pgn=tmp_path/'transpositions.pgn'
    pgn.write_text('[Event "A"]\n\n1. Nf3 Nf6 2. g3 g6 *\n\n[Event "B"]\n\n1. g3 g6 2. Nf3 Nf6 *\n')
    assert inspect_openings(pgn,4)['unique_positions']==1
    assert inspect_openings(pgn,2)['unique_positions']==2
    with pytest.raises(ValueError,match='depth'):inspect_openings(pgn,-1)


def test_polyglot_complete_inventory_over_100_and_depth(tmp_path):
    path=tmp_path/'full.bin';entries={};board=chess.Board()
    def add(b,m,weight=1):
        raw=m.to_square|(m.from_square<<6);entries[(chess.polyglot.zobrist_hash(b),raw)]=weight
    for white in list(board.legal_moves):
        add(board,white);board.push(white)
        for black in board.legal_moves:add(board,black)
        board.pop()
    path.write_bytes(b''.join(struct.pack('>QHHI',key,move,weight,0) for (key,move),weight in sorted(entries.items())))
    r=inspect_openings(path,2)
    assert r['exact'] and r['unique_positions']==400
    assert len({position_key(chess.Board(x['fen'])) for x in r['items']})==400
    assert inspect_openings(path,1)['unique_positions']==20
    assert inspect_openings(path,0)['unique_positions']==1
    assert inspect_openings(path,8)['unique_positions']==400 # book exits first


@pytest.mark.parametrize('n',range(2,20))
def test_round_robin_rounds_have_one_opponent_and_cover_all_pairs(n):
    by_round=defaultdict(list);pairs=Counter()
    for i in range(n*(n-1)):
        a,b,r=round_pair(i,n,'round_robin',2);assert a!=b and 0<=a<n and 0<=b<n
        by_round[r]+=[a,b];pairs[tuple(sorted((a,b)))]+=1
    assert len(pairs)==n*(n-1)//2 and set(pairs.values())=={2}
    assert all(len(v)==len(set(v))==2*(n//2) for v in by_round.values())


def test_gauntlet_rounds_cover_rectangular_fields():
    for n in range(3,15):
        for c in range(1,n):
            rounds=defaultdict(list);pairs=[]
            for i in range(c*(n-c)):
                a,b,r=round_pair(i,n,'gauntlet',1,c);pairs.append((a,b));rounds[r]+=[a,b]
            assert set(pairs)=={(a,b) for a in range(c) for b in range(c,n)}
            assert all(len(v)==len(set(v)) for v in rounds.values())


def test_pair_shuffle_recovery_replacement_and_pgn_keep_opening(tmp_path):
    s=Store(tmp_path);settings={'cycles':8,'opening_policy':'pair','opening_order':'shuffle','seed':121}
    t=s.create_tournament('Pool',[{'name':'A'},{'name':'B'}],settings,pool(8));tid=t['id']
    recorded=t['settings']['openings'];s.set_state(tid,'running');s.fill_queue(tid,4)
    first=s.claim(tid);other=s.claim(tid);assert first['opening']==other['opening']
    s.finish(first['aid'],'0-1','timeout');s.finish(other['aid'],'1-0','fixture');s.set_state(tid,'paused')
    s.requeue(tid,[first['id']],mode='replacement');s.close();s=Store(tmp_path)
    assert s.tournament(tid)['settings']['openings']==recorded
    s.set_state(tid,'running');replay=s.claim(tid);assert replay['opening']==first['opening']
    s.finish(replay['aid'],'1-0','fixture');s.fill_queue(tid,40)
    rows=s.rows('SELECT pair_no,opening FROM games ORDER BY number')
    assert len({json.loads(g['opening'])['fen'] for g in rows})==8
    assert all(json.loads(rows[i]['opening'])==json.loads(rows[i+1]['opening']) for i in range(0,16,2))
    while g:=s.claim(tid):s.finish(g['aid'],'1/2-1/2','fixture')
    s.export_pending();stream=io.StringIO(s.export_official(tid));games=[]
    while g:=chess.pgn.read_game(stream):assert not g.errors;games.append(g)
    assert len(games)==16 and len({g.headers['GameId'] for g in games})==16
    assert s.snapshot(tid)['complete_pairs']==8
    s.close()


@pytest.mark.parametrize('policy',['round','cycle','fixed','pair'])
def test_assignment_policies_persist_for_all_matchups(tmp_path,policy):
    s=Store(tmp_path);t=s.create_tournament('Shared',[{'name':str(i)} for i in range(4)],{'format':'round_robin','cycles':2,'opening_policy':policy},pool())
    s.set_state(t['id'],'running');s.fill_queue(t['id'],100)
    games=s.rows('SELECT * FROM games ORDER BY number');assert len(games)==24
    selected={json.loads(g['opening'])['selection'] for g in games}
    assert len(selected)=={'round':6,'cycle':2,'fixed':1,'pair':12}[policy]
    if policy=='round':
        for r in range(6):
            group=[g for g in games if g['round']==r];assert len(group)==4
            assert {g['white'] for g in group}==set(range(4))
            assert {json.loads(g['opening'])['selection'] for g in group}=={r}
    s.close()


def test_swiss_shared_cycles_and_capacity():
    s=DEFAULTS|{'format':'swiss','cycles':3,'rounds':5,'opening_policy':'cycle','openings':pool()}
    assert [select(s,99,2,i)['selection'] for i in range(3)]==[6,7,8]
    s['opening_policy']='round';assert {select(s,99,2,i)['selection'] for i in range(3)}=={2}
    assert capacity(10,8,s)['games_before_reuse']=='240'
    for policy,want in [('pair','20'),('round','40'),('cycle','120')]:
        c=capacity(10,4,DEFAULTS|{'format':'round_robin','cycles':2,'opening_policy':policy});assert c['games_before_reuse']==want
    assert capacity(5,4,DEFAULTS|{'opening_policy':'pair','format':'round_robin','opening_order':'random'})['games_before_reuse'] is None


def test_large_field_round_schedule_stays_incremental(tmp_path):
    s=Store(tmp_path);t=s.create_tournament('Large',[{'name':str(i)} for i in range(10000)],{'format':'round_robin','cycles':1,'opening_policy':'round'},pool(),backup=False)
    assert t['total']==99_990_000;s.set_state(t['id'],'running');s.fill_queue(t['id'],64)
    assert s.one('SELECT count(*) n FROM games')['n']==64
    assert {json.loads(r['opening'])['selection'] for r in s.rows('SELECT opening FROM games')}=={0}
    s.close()


def test_inventory_route_cache_invalidates_changed_file_and_assets(tmp_path):
    async def run():
        app=await create_app(tmp_path/'data','token');app['runner'].scheduler.cancel()
        with contextlib.suppress(asyncio.CancelledError):await app['runner'].scheduler
        source=tmp_path/'openings.fen';source.write_text(pool(1)[0]['fen'])
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'token'}) as client:
            body={'opening_file':str(source),'book_depth':4,'participants':4,'settings':{'format':'round_robin','cycles':2,'opening_policy':'round'}}
            r=await client.post('/api/opening-preview',json=body);assert r.status==200
            v=await r.json();assert v['unique_positions']==1 and v['games_before_reuse']=='4' and v['required_positions']=='6'
            source.write_text('\n'.join(x['fen'] for x in pool(3)))
            r=await client.post('/api/opening-preview',json=body);assert (await r.json())['unique_positions']==3
            for name in ('opening-presets.js','evaluation.js','evaluation-ui.js','evaluation.css'):
                assert (await client.get('/assets/'+name)).status==200
    asyncio.run(run())
