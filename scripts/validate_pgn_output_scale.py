"""50,000 synthetic official records; bounded export and single-game append cost."""
import contextlib,json,sys,time,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from arena.store import Store
from arena.pgn_output import Outputs,configure
import arena.pgn_output as output_module

base=ROOT/'test-output'/('pgn-output-scale-'+str(time.time_ns()));base.mkdir()
store=Store(base/'data');service=Outputs(types.SimpleNamespace(store=store));path=base/'50000.pgn'
try:
    t=store.create_tournament('50,000 synthetic PGNs',[{'name':'A'},{'name':'B'}],{'cycles':25001},backup=False)
    prepared=service.prepare({'enabled':True,'path':str(path),'mode':'new','preset':'clean'});configure(store,t['id'],prepared)
    store.set_state(t['id'],'running');store.fill_queue(t['id'],50002)
    with store.tx():
        store.db.execute("INSERT INTO attempts(id,gid,seq,mode,started,ended,result,reason,identity) SELECT 'a'||id,id,1,'original',1,2,'1/2-1/2','fixture','{}' FROM games")
        store.db.execute("UPDATE games SET official='a'||id,state='completed' WHERE number<50000")
    started=time.perf_counter();passes=0
    while True:
        service.tick();passes+=1;s=next(iter(service.status.values()))
        assert not s.get('error'),s
        if s['state']=='saved':break
    initial=time.perf_counter()-started
    assert s['games']==50000,s
    with path.open('rb') as f:assert sum(line.startswith(b'[GameId ') for line in f)==50000
    count=[0];render=output_module.render_attempt
    def counted(*a,**k):count[0]+=1;return render(*a,**k)
    output_module.render_attempt=counted
    before=path.stat().st_size
    with store.tx():store.db.execute("UPDATE games SET official='a'||id,state='completed' WHERE number=50000")
    started=time.perf_counter();service.tick();append=time.perf_counter()-started
    assert count[0]==1 and next(iter(service.status.values()))['games']==50001
    assert path.stat().st_size>before
    started=time.perf_counter()
    for _ in range(20):service.tick()
    idle=(time.perf_counter()-started)/20
    assert count[0]==1
    result={'synthetic_games':50000,'initial_seconds':initial,'initial_passes':passes,'append_one_seconds':append,'idle_check_seconds':idle,'rendered_for_append':count[0],'pgn_bytes':path.stat().st_size,'index_bytes':Path(str(path)+'.arena-pgn.sqlite3').stat().st_size,'no_real_engine_games':True}
    (ROOT/'test-output/pgn-output-scale.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
finally:
    for target in service.targets.values():target.close()
    service.executor.shutdown();store.close()
