"""Delete only the four completed rc_load_acceptance fixture tournaments.

Checks actual disk reclamation, every recovery copy, profiles, PGNs and restart.
Never accepts a personal workspace or an unverified/non-load fixture.
"""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import time
from rc_acceptance import Candidate, ROOT


def managed_bytes(folder):
    paths=[folder/n for n in ('arena.sqlite3','arena.sqlite3-wal','arena.sqlite3-shm','deletions.sqlite3','games.pgn','interrupted.pgn')]
    for directory in ('backups','report-cache'):
        paths.extend(p for p in (folder/directory).rglob('*') if p.is_file())
    return sum(p.stat().st_size for p in paths if p.is_file())


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--data',type=Path,required=True);args=parser.parse_args()
    folder=args.data.resolve();assert folder.is_relative_to(ROOT/'test-output')
    prior=json.loads(folder.with_suffix('.json').read_text());assert prior['passed'] and len(prior['runs'])==4
    expected={'RC load '+r['phase'] for r in prior['runs']}
    c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',folder);report={}
    try:
        before=managed_bytes(folder);c.launch();tourneys=c.api('tournaments')
        assert len(tourneys)==4 and {t['name'] for t in tourneys}==expected
        assert all(t['state']=='completed' for t in tourneys)
        report_path='tournaments/'+tourneys[0]['id']+'/report?all_engines=1'
        started=time.perf_counter();html=c.api(report_path)['html'];report['technical_report_seconds']=time.perf_counter()-started
        started=time.perf_counter();cached=c.api(report_path)['html'];report['cached_report_seconds']=time.perf_counter()-started
        assert html==cached;report['technical_report_bytes']=len(html.encode('utf-8'))
        profiles=c.api('profiles');preferences=c.api('preferences');started=time.perf_counter()
        for t in tourneys:
            preview=c.api('tournaments/'+t['id']+'/delete');assert preview['official']>0
            c.api('tournaments/'+t['id']+'/delete',{'name':t['name'],'confirmed':True})
            print('Deleted test tournament:',t['name'],flush=True)
        assert c.api('tournaments')==[] and c.api('profiles')==profiles and c.api('preferences')==preferences
        assert not c.api('status')['error'];report['delete_seconds']=time.perf_counter()-started;c.stop()
        report['databases']=[]
        for path in [folder/'arena.sqlite3',*(folder/'backups').glob('recovery-*.sqlite3')]:
            with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
                assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
                for table in ('tournaments','games','attempts','moves','logs','log_blocks','outbox','participants'):
                    assert db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]==0,(path.name,table)
                assert db.execute('PRAGMA freelist_count').fetchone()[0]==0
                report['databases'].append({'name':path.name,'bytes':path.stat().st_size})
        assert len(report['databases'])>=2
        assert not (folder/'games.pgn').read_bytes() and not (folder/'interrupted.pgn').read_bytes()
        after=managed_bytes(folder);assert after<before*.1,(before,after)
        c.launch();assert c.api('tournaments')==[] and c.api('profiles')==profiles;c.stop()
        report.update(before_bytes=before,after_bytes=after,reclaimed_bytes=before-after,profiles_preserved=profiles['total'],
            startup_seconds=c.timings,passed=True)
    except BaseException as exc:report['failure']=repr(exc);raise
    finally:
        c.stop();folder.with_name(folder.name+'-deletion.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
