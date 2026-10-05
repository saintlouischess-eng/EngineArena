import asyncio
from types import SimpleNamespace
from arena.uci import UciEngine
from arena.store import DEFAULTS


def test_bestmove_receipt_precedes_fairness_yield(monkeypatch):
    async def run():
        stamp=[100.0];original_sleep=asyncio.sleep
        async def delayed_yield(delay):
            stamp[0]+=1
            await original_sleep(0)
        monkeypatch.setattr('arena.uci.time.perf_counter',lambda:stamp[0])
        monkeypatch.setattr('arena.uci.asyncio.sleep',delayed_yield)
        lines=[b'info string fixture\n']*63+[b'bestmove e2e4\n',b'']
        async def readline():return lines.pop(0)
        engine=UciEngine({},DEFAULTS)
        engine.process=SimpleNamespace(stdout=SimpleNamespace(readline=readline),returncode=0)
        engine.search=asyncio.get_running_loop().create_future()
        await engine._read()
        assert engine.search.result()==('e2e4',100.0,None)
        assert stamp[0]==101.0  # the fairness yield actually ran
    asyncio.run(run())
