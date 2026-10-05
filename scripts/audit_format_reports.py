"""Reconcile final reports with raw committed games and recorded Swiss byes."""
import json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from arena.standings import read_snapshot
from arena.tournament_report import render


def main():
    evidence=json.loads((ROOT/'test-output/all-formats-real.json').read_text());folder=Path(evidence['folder']);snapshots=[];checked=0
    with sqlite3.connect((folder/'arena.sqlite3').as_uri()+'?mode=ro',uri=True) as con:
        con.row_factory=sqlite3.Row
        for t in evidence['tournaments']:
            tid=Path(t['report']).stem;snap=read_snapshot(folder/'arena.sqlite3',tid);snapshots.append(snap)
            games=list(con.execute('SELECT g.white,g.black,a.result FROM games g JOIN attempts a ON a.id=g.official WHERE g.tid=? AND g.invalid=0',(tid,)))
            rounds=[json.loads(r[0]) for r in con.execute('SELECT body FROM round_state WHERE tid=?',(tid,))]
            byes={}
            for r in rounds:
                for slot,points in r.get('bye_awards',[]):byes[slot]=byes.get(slot,0)+points
            for row in snap['standings']:
                w=d=l=0;slot=row['slot']
                for g in games:
                    if slot not in (g['white'],g['black']):continue
                    if g['result']=='1/2-1/2':d+=1
                    elif (g['result']=='1-0')==(slot==g['white']):w+=1
                    else:l+=1
                assert (row['wins'],row['draws'],row['losses'],row['games'])==(w,d,l,w+d+l),(t,row,w,d,l)
                assert row['bye_points']==byes.get(slot,0)
                assert row['points']==w+d/2+byes.get(slot,0)
                if w+d+l:assert abs(row['score_pct']-100*(w+d/2)/(w+d+l))<1e-8
                if t['format']=='self_play':assert row['elo'] is None and row['los'] is None
                checked+=1
            html=render(folder/'arena.sqlite3',tid,95,True,True)
            if t['format']=='swiss':assert 'Bye points do not count as played games' in html
            (folder/t['report']).write_text(html,encoding='utf-8')
    (ROOT/'test-output/all-formats-final-snapshots.json').write_text(json.dumps(snapshots),encoding='utf-8')
    output={'reports':len(snapshots),'engine_rows_reconciled':checked,'checks':['W/D/L','game counts','game score percentages','points including recorded byes','self-play inference suppressed'],'source':str(folder)}
    (ROOT/'test-output/all-formats-report-audit.json').write_text(json.dumps(output,indent=2),encoding='utf-8');print(json.dumps(output))


if __name__=='__main__':main()
