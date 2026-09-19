"""50,000 synthetic one-ply records: deletion and paged-clock smoke, not engine throughput."""
import json
from pathlib import Path
import sqlite3
import sys
import time

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import chess
from arena.store import Store


def main():
    folder=ROOT/'test-output/deletion-scale'
    if (folder/'arena.sqlite3').exists():raise RuntimeError('Preserve existing scale evidence; use a fresh fixture')
    s=Store(folder);profiles=[{'name':'A'},{'name':'B'}]
    try:
        tid=s.create_tournament('Synthetic deletion scale',profiles,{'cycles':25000},backup=False)['id']
        keep=s.create_tournament('Survivor',profiles,{'cycles':1},backup=False)['id']
        board=chess.Board();board.push_uci('e2e4')
        for target in (tid,keep):
            s.set_state(target,'running');s.fill_queue(target,2)
            for _ in range(2):
                g=s.claim(target)
                s.move(g['aid'],1,'e2e4','e4',board.fen(),.1,{'white':{'remaining':179.9},'black':{'remaining':180}},{'nodes':100})
                s.finish(g['aid'],'1/2-1/2','max_plies_adjudication','Synthetic scale fixture')
            s.set_state(target,'paused')
        templates=s.rows('SELECT * FROM games WHERE tid=? ORDER BY number',(tid,))
        attempts=[s.one('SELECT * FROM attempts WHERE id=?',(g['official'],)) for g in templates]
        moves=[s.one('SELECT * FROM moves WHERE aid=?',(g['official'],)) for g in templates]
        pgns=[s.one('SELECT pgn FROM outbox WHERE aid=?',(g['official'],))['pgn'] for g in templates]
        for start in range(2,50000,500):
            with s.tx():
                for n in range(start,min(50000,start+500)):
                    g=dict(templates[n%2]);a=dict(attempts[n%2]);m=dict(moves[n%2])
                    gid=f'{n:032x}';aid='f'+f'{n:031x}';pgn=pgns[n%2].replace(g['id'],gid).replace(a['id'],aid)
                    g.update(id=gid,number=n,pair_no=n//2,official=aid);a.update(id=aid,gid=gid);m.update(aid=aid)
                    s.db.execute('INSERT INTO games VALUES('+','.join('?' for _ in g)+')',tuple(g.values()))
                    s.db.execute('INSERT INTO attempts VALUES('+','.join('?' for _ in a)+')',tuple(a.values()))
                    s.db.execute('INSERT INTO moves VALUES('+','.join('?' for _ in m)+')',tuple(m.values()))
                    s.db.execute('INSERT INTO outbox(aid,stream,pgn) VALUES(?,?,?)',(aid,'games',pgn))
        while (s.one("SELECT last_id FROM exports WHERE stream='games'") or {'last_id':0})['last_id']<s.one('SELECT max(id) n FROM outbox')['n']:s.export_pending()
        s.backup();s.db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        report={'synthetic_games':50000,'plies_per_game':1,'database_bytes':s.path.stat().st_size,'pgn_bytes_before':(folder/'games.pgn').stat().st_size}
        start=time.perf_counter();page=s.games(tid,offset=49950,limit=50)
        report['last_page_with_clocks_ms']=(time.perf_counter()-start)*1000
        assert len(page['items'])==50 and all(g['clocks'] for g in page['items'])
        start=time.perf_counter();s.delete_tournament(tid,'Synthetic deletion scale');report['delete_seconds']=time.perf_counter()-start
        assert s.one('SELECT count(*) n FROM games')['n']==2 and s.one('SELECT count(*) n FROM moves')['n']==2
        assert s.snapshot(keep)['official_games']==2
        assert tid not in (folder/'games.pgn').read_text(encoding='utf-8')
        report.update(surviving_official_games=2,pgn_bytes_after=(folder/'games.pgn').stat().st_size,integrity=s.db.execute('PRAGMA integrity_check').fetchone()[0])
        for path in (folder/'backups').glob('recovery-*.sqlite3'):
            db=sqlite3.connect(path)
            try:assert db.execute('SELECT count(*) FROM games').fetchone()[0]==2
            finally:db.close()
    finally:s.close()
    (ROOT/'test-output/deletion-scale-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
