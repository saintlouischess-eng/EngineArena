"""Validate the packaged rating correction in an isolated two-game fixture."""
from contextlib import closing
import json,subprocess,sys,time
from pathlib import Path
from rc_acceptance import Candidate,ROOT
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from arena import __version__
from arena.store import Store
from arena.rating_center_report import report
from test_rating_pair_conditions import changed_pair
from validate_rating_rank_package import fingerprints

folder=ROOT/'test-output'/('rating-pair-package-'+time.strftime('%Y%m%d-%H%M%S'))
with closing(Store(folder)) as s:
    tid,keys,_,_=changed_pair(s)
    expected=report(s.path,{'export':'json'})
before,aids,_=fingerprints(folder/'arena.sqlite3')
c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',folder)
try:
    c.launch();r=c.api('rating-center?category=blitz&export=json')
    assert r['official_games']==r['counted_games']==2 and r['pairs']==1
    assert r['sampling']['compatible_update_pairs']==1 and r['sampling']['excluded_games']==0
    assert r['items']==expected['items']
    for key in keys:
        filtered=c.api('rating-center?category=blitz&conditions='+key)
        assert filtered['counted_games']==0 and filtered['sampling']['incomplete_pair_games']==1
    assert b'Included CPU pairs across system updates: 1' in c.api('rating-center?category=blitz&export=txt',raw=True)
    (ROOT/'test-output/rating-pair-ready.json').write_text(json.dumps({'url':f"http://127.0.0.1:{c.info['port']}/?token={c.info['token']}",'conditions':keys}),encoding='utf-8')
    subprocess.run(['node',str(ROOT/'scripts/validate_rating_pairs_ui.cjs')],cwd=ROOT,check=True)
    c.stop();after,_,_=fingerprints(folder/'arena.sqlite3',aids);assert before==after
    c.launch();again=c.api('rating-center?category=blitz&export=json');assert again['items']==r['items'] and again['sampling']==r['sampling']
    c.stop();after,_,_=fingerprints(folder/'arena.sqlite3',aids);assert before==after
    result={'version':__version__,'fixture':str(folder),'official_games':r['official_games'],'counted_games':r['counted_games'],'sampling':r['sampling'],'unchanged_records':before,'restart_passed':True,'startup_seconds':c.timings}
    (ROOT/'test-output/rating-pair-package.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
finally:
    c.stop();(ROOT/'test-output/rating-pair-ready.json').unlink(missing_ok=True)
