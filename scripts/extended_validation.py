"""Exercise EPD accuracy and scaling jobs using real upstream engines."""
import asyncio
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from arena.runner import Database,Runner

ROOT=Path(__file__).resolve().parent.parent
async def main():
    folder=ROOT/'test-output'/'experiments-real';folder.mkdir(exist_ok=True)
    epd=folder/'fixture.epd';epd.write_text('7k/5Q2/6K1/8/8/8/8/8 w - - bm Qg7# Qh7# Qf8# Qe8#; id "Mate in one";\nrnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - am a3 h3; id "Avoid edge pawn";\n')
    profiles=json.loads((ROOT/'test-output'/'real-validation'/'report.json').read_text())['engines'];report=[]
    db=await Database().open(folder);runner=Runner(db);await runner.start()
    try:
        for kind,settings,path in [('suite',{'time_control':{'kind':'nodes','nodes':10000}},str(epd)),('benchmark',{'time_control':{'kind':'nodes','nodes':100000},'thread_counts':[1,2,4],'repeats':2},None)]:
            job=await db.call('experiment_create','Real engine '+kind,kind,profiles,settings,path);await db.call('experiment_state',job['id'],'running')
            for _ in range(1000):
                result=await db.call('experiment_get',job['id'])
                if result['state']=='completed':break
                if runner.error:raise AssertionError(runner.error)
                await asyncio.sleep(.1)
            assert result['completed']==result['total']
            assert all(r['reason']=='completed' for r in result['results'])
            report.append(result)
    finally:await runner.close()
    (ROOT/'test-output'/'experiments-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps([{'kind':r['kind'],'cases':r['completed'],'accuracy':r['accuracy_pct']} for r in report]))

asyncio.run(main())
