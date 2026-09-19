"""Measured real-engine smoke/load/recovery run; writes a durable JSON report."""
import asyncio
import io
import json
import os
from pathlib import Path
import statistics
import sys
import time
import chess.pgn
from arena.store import DEFAULTS
from arena.runner import Database,Runner
from arena.uci import discover

ROOT=Path(__file__).resolve().parent.parent
async def run():
    out=ROOT/'test-output'/'real-validation';out.mkdir(parents=True,exist_ok=True)
    sf=next((ROOT/'validation-engines'/'stockfish').glob('**/*.exe'))
    be=ROOT/'validation-engines'/'berserk-14-avx2.exe'
    profiles=[]
    for path in (sf,be):
        p=await discover({'path':str(path),'hash':32,'threads':1},DEFAULTS)
        p['hash']=32;p['threads']=1;profiles.append(p)
    db=await Database().open(out/'data');r=Runner(db);report={'engines':profiles,'runs':[]}
    try:
        await r.start()
        for kind,cycles,concurrency in [('nodes',64,32),('depth',2,2),('movetime',2,2),('fischer',2,2)]:
            settings={'cycles':cycles,'concurrency':concurrency,'time_control':{'kind':kind,'nodes':10000,'depth':8,'seconds':.02 if kind=='movetime' else 3,'increment':.03},'max_plies':40,'hang_timeout':30}
            t=await db.call('create_tournament',f'Real {kind} validation',profiles,settings)
            start=time.perf_counter();await db.call('set_state',t['id'],'running');latencies=[];peak=0
            while time.perf_counter()-start<240:
                before=time.perf_counter();snap=await db.call('snapshot',t['id']);latencies.append((time.perf_counter()-before)*1000);peak=max(peak,len(r.tasks))
                if snap['state']=='completed':break
                if r.error:raise RuntimeError(r.error)
                await asyncio.sleep(.1)
            games=await db.call('games',t['id'],limit=100000)
            official=await db.call('export_official',t['id']);f=io.StringIO(official);count=0;errors=[]
            while g:=chess.pgn.read_game(f):count+=1;errors.extend(str(e) for e in g.errors)
            reasons={}
            for g in games['items']:reasons[g['reason']]=reasons.get(g['reason'],0)+1
            report['runs'].append({'control':kind,'settings':settings,'tournament':t['id'],'state':snap['state'],'official_games':snap['official_games'],'pgn_games':count,'pgn_errors':errors,'termination_counts':reasons,'seconds':time.perf_counter()-start,'peak_concurrency':peak,'snapshot_ms_median':statistics.median(latencies),'snapshot_ms_p95':sorted(latencies)[int((len(latencies)-1)*.95)]})
            (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(json.dumps(report['runs'][-1]),flush=True)
            if snap['state']!='completed':raise AssertionError('Real engine run did not complete')
    finally:await r.close()

if __name__=='__main__':asyncio.run(run())
