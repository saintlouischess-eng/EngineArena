"""Alternating frozen-worker baseline / live-dashboard throughput comparisons."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import statistics
import subprocess
import time
import uuid
import psutil
from rc_acceptance import Candidate, ROOT


def workspace_bytes(folder):
    size=0
    for path in folder.rglob('*'):
        try:
            if path.is_file():size+=path.stat().st_size
        except FileNotFoundError:pass  # backup rotation can rename files during a sample
    return size


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--cycles',type=int,default=128)
    parser.add_argument('--node',type=Path,required=True);parser.add_argument('--data',type=Path,default=ROOT/'test-output/rc-load')
    parser.add_argument('--exercise-exports',action='store_true');args=parser.parse_args()
    folder=args.data.resolve();assert folder.is_relative_to(ROOT/'test-output') and not (folder/'arena.sqlite3').exists()
    folder.mkdir(exist_ok=True);c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',folder)
    output=folder.with_suffix('.json');result={'scope':'Full legal real-engine games; headless Edge with 32 boards and 16 graphs versus frozen worker without a UI','runs':[]}
    log=(folder/'worker.log').open('w')
    worker=subprocess.Popen([str(ROOT/'release/EngineArena/worker/ArenaWorker.exe'),'--data',str(folder),'--ready',str(c.ready)],stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        deadline=time.monotonic()+60
        while not c.ready.exists():
            assert worker.poll() is None and time.monotonic()<deadline;time.sleep(.1)
        c.info=json.loads(c.ready.read_text())
        c.api('storage',{'action':'settings','settings':{'backup_copies':2,'backup_minutes':1}})
        profiles=[]
        for name,path in [('Stockfish',ROOT/'validation-engines/stockfish/stockfish/stockfish-windows-x86-64-universal.exe'),('Berserk',ROOT/'validation-engines/berserk-14-avx2.exe')]:
            profiles.append(c.api('profiles',{'name':name+' load','path':str(path),'threads':1,'hash':32,'discover':True})['id'])
        for phase in ('baseline1','live1','live2','baseline2'):
            t=c.tournament('RC load '+phase,profiles,{'cycles':args.cycles,'concurrency':32,'cpu_budget':32,'memory_budget_mb':24576,'time_control':{'kind':'nodes','nodes':100000},'max_plies':0})
            graphs=[{'id':'graph-'+str(uuid.uuid4()),'kind':kind,'game':0,'slot':0,'ci':'conservative'} for kind in ['evaluation','mate','wdl','depth','nodes','nps','moveTime','clock','hash','tablebase','cpu','memory','score','draw','elo','sprt']]
            c.api('preferences',{'theme':'dark','pieceSet':'classic','boardCount':32,'fontSize':14,'graphs':graphs,'panels':{g['id']:{'column':'right','visible':True,'height':320} for g in graphs}})
            phase_file=folder/(phase+'.json');phase_file.write_text(json.dumps(c.info|{'tid':t['id'],'phase':phase}))
            ui=None;ui_log=None
            if phase.startswith('live'):
                ui_log=(folder/(phase+'-ui.log')).open('w')
                ui=subprocess.Popen([str(args.node),str(ROOT/'scripts/rc_load_ui.cjs'),str(phase_file)],stdout=ui_log,stderr=ui_log,creationflags=subprocess.CREATE_NO_WINDOW)
                deadline=time.monotonic()+60
                while not phase_file.with_suffix('.ready').exists():
                    assert ui.poll() is None and time.monotonic()<deadline;time.sleep(.1)
            samples=[];backup_seen=False;observations=[];last_observation=0;last_export=0
            def sample(snapshot,status):
                nonlocal backup_seen,last_observation,last_export
                samples.append({'games':snapshot['official_games'],'active':status['active_games'],'cpu':status['cpu_percent'],'memory':status['memory_used_gb'],'ui':status.get('ui_metrics')})
                backup_seen |= status['backup']['phase'] in ('copying','verifying','flushing')
                now=time.monotonic()
                if now-last_observation>=5:
                    last_observation=now;process=psutil.Process(worker.pid);memory=process.memory_info()
                    row={'seconds':now,'games':snapshot['official_games'],'worker_rss':memory.rss,'worker_private':getattr(memory,'private',None),
                         'test_workspace_file_bytes':workspace_bytes(folder)}
                    observations.append(row)
                if args.exercise_exports and snapshot['state']=='running' and snapshot['official_games'] and now-last_export>=30:
                    last_export=now;before=time.perf_counter()
                    html=c.api('tournaments/'+snapshot['id']+'/report?technical=0')['html'];assert '<table' in html
                    report_seconds=time.perf_counter()-before;before=time.perf_counter()
                    raw=c.api('export/'+snapshot['id']+'/pgn?preset=clean',raw=True);assert raw.startswith(b'[Event ')
                    observations.append({'games':snapshot['official_games'],'live_report_seconds':report_seconds,'live_export_seconds':time.perf_counter()-before,'export_bytes':len(raw)})
            try:
                c.action(t['id'],'start');snapshot,measure=c.wait(t['id'],timeout=1200,hook=sample)
                if ui:
                    assert ui.wait(60)==0,(folder/(phase+'-ui.log')).read_text()
                assert snapshot['official_games']==args.cycles*2 and measure['peak_games']==32
                with closing(c.db()) as db:
                    reasons=dict(db.execute('SELECT a.reason,count(*) FROM attempts a JOIN games g ON g.id=a.gid WHERE g.tid=? GROUP BY a.reason',(t['id'],)))
                    assert not set(reasons).intersection(('timeout','crash','hang','illegal_move','startup_timeout','readiness_timeout','max_plies_adjudication')),reasons
                pgn=c.pgn(t['id'],snapshot['official_games'])
                run={'phase':phase,'games':snapshot['official_games'],'pairs':snapshot['complete_pairs'],**measure,
                     'terminations':reasons,'pgn':pgn,'backup_seen':backup_seen,'samples':samples,
                     'storage':c.api('storage'),'observations':observations}
                result['runs'].append(run);output.write_text(json.dumps(result,indent=2))
                print(json.dumps({k:v for k,v in run.items() if k not in ('samples','storage','pgn','observations')}),flush=True)
            finally:
                if ui and ui.poll() is None:ui.kill();ui.wait()
                if ui_log:ui_log.close()
        baseline=statistics.mean(r['seconds'] for r in result['runs'] if r['phase'].startswith('baseline'))
        live=statistics.mean(r['seconds'] for r in result['runs'] if r['phase'].startswith('live'))
        result['mean_elapsed_change_percent']=(live/baseline-1)*100
        result['total_games']=sum(r['games'] for r in result['runs']);result['live_exports_exercised']=args.exercise_exports;result['passed']=True
        output.write_text(json.dumps(result,indent=2));print('Comparison complete',flush=True)
    finally:
        try:c.api('shutdown',{});worker.wait(120)
        finally:
            if worker.poll() is None:worker.kill();worker.wait()
            log.close()


if __name__=='__main__':main()
