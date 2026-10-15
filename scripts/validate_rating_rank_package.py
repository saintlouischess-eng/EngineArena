"""Upgrade a read-only backup copy; never open production with Store or the app."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import time

from rc_acceptance import Candidate,ROOT
sys.path.insert(0,str(ROOT))
from arena.rating_center_report import report
from arena import __version__


def fingerprints(path,attempt_ids=None):
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
        queries={
            'official_results':'SELECT g.id,g.official,a.result,a.reason FROM games g JOIN attempts a ON a.id=g.official ORDER BY g.id',
            'rating_ledger':'SELECT * FROM rc_games ORDER BY pool,gid',
            'entries':'SELECT * FROM rc_entries ORDER BY id',
            'anchors':'SELECT * FROM rc_anchors ORDER BY pool,category',
            'collection_settings':'SELECT id,name,automatic,epoch,rules FROM rc_pools ORDER BY id',
            'settings':'SELECT id,settings FROM tournaments ORDER BY id',
            'participants':'SELECT * FROM participants ORDER BY tid,slot',
            'event_rules':"SELECT id,json_extract(body,'$.definition'),json_extract(body,'$.settings'),json_extract(body,'$.profiles') FROM events ORDER BY id",
        }
        raw={k:db.execute(sql).fetchall() for k,sql in queries.items()}
        attempts=db.execute('SELECT * FROM attempts WHERE ended IS NOT NULL ORDER BY id').fetchall()
        if attempt_ids is not None:attempts=[r for r in attempts if r[0] in attempt_ids]
        raw['original_completed_attempts']=attempts
        digest={k:hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True).encode()).hexdigest() for k,v in raw.items()}
        return digest,{r[0] for r in attempts},len(raw['official_results'])


def main():
    source=Path(sys.argv[1]).resolve();assert source.is_file()
    label='v'+__version__.replace('.','')
    folder=ROOT/'test-output'/(label+'-upgrade-'+time.strftime('%Y%m%d-%H%M%S'));folder.mkdir()
    target=folder/'arena.sqlite3'
    with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(target)) as dst:
        # Pin one committed snapshot so UI telemetry commits cannot repeatedly
        # restart an online backup while the source application remains open.
        src.execute('BEGIN');src.execute('SELECT count(*) FROM sqlite_master').fetchone()
        src.backup(dst,pages=256,sleep=.01)
    before,attempt_ids,count=fingerprints(target)
    expected=report(target,{'category':'blitz','export':'json'})
    c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',folder)
    proof={'passed':False,'scope':'Packaged desktop using a disposable online database copy; no production writes','folder':str(folder),'before':before}
    try:
        c.launch();status=c.api('status');assert status['active_games']==0 and not status['error']
        got=c.api('rating-center?category=blitz&export=json')
        assert got['anchor']==expected['anchor']
        def measured(rows):return {r['id']:{k:r[k] for k in ('rank','rating','ci','los','games','wins','draws','losses','samples')} for r in rows}
        assert measured(got['items'])==measured(expected['items'])
        assert got['total']==expected['total']
        assert c.api('rating-center?category=blitz&offset=50')['items']==got['items'][50:]
        assert 'Rank' in c.api('rating-center?category=blitz&export=txt',raw=True).decode()
        assert c.api('rating-center?category=blitz&export=csv',raw=True).startswith(b'Rank,Engine,')
        c.stop()
        after,_,_=fingerprints(target,attempt_ids);assert after==before
        with closing(sqlite3.connect(target.as_uri()+'?mode=ro',uri=True)) as db:
            assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        c.launch();again=c.api('rating-center?category=blitz&export=json')
        assert again['anchor']==got['anchor'] and measured(again['items'])==measured(got['items'])
        proof.update(passed=True,after=after,official_games_preserved=count,completed_attempts_preserved=len(attempt_ids),rated_entries=got['total'],anchor=got['anchor'],restart_preserved=True)
    finally:
        c.stop();(ROOT/'test-output'/(label+'-package.json')).write_text(json.dumps(proof,indent=2),encoding='utf-8')
    print(json.dumps(proof,indent=2))


if __name__=='__main__':main()
