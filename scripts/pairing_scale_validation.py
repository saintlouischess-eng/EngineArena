"""Reproduce large second-round Swiss matching without launching engines."""
from collections import Counter,defaultdict
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from arena.rounds import swiss_matches

if __name__=='__main__':
    results=[]
    for n in (1000,3000):
        pool=list(range(n));points={i:float(i<n//2) for i in pool};opponents=defaultdict(set)
        for i in range(n//2):opponents[i].add(i+n//2);opponents[i+n//2].add(i)
        start=time.perf_counter();matches,byes=swiss_matches(pool,points,dict(enumerate(pool)),Counter(),defaultdict(list),opponents,Counter());elapsed=time.perf_counter()-start
        assert len(matches)==n//2 and len({a for pair in matches for a in pair})==n and not byes
        assert all(b not in opponents[a] for a,b in matches)
        results.append({'participants':n,'second_round_seconds':elapsed,'matches':len(matches)})
    path=Path(__file__).resolve().parent.parent/'test-output'/'swiss-large-report.json';path.write_text(json.dumps(results,indent=2));print(json.dumps(results))
