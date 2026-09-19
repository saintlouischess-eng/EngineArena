"""Create isolated, deterministic round-review fixtures for native GUI QA."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from arena.store import Store

def main():
    folder=ROOT/'test-output'/'format-ui';s=Store(folder)
    if s.rows('SELECT id FROM tournaments'):raise SystemExit('Use the existing format-ui fixtures; refusing to overwrite history.')
    profiles=[]
    for name,path in [('Stockfish',next((ROOT/'validation-engines'/'stockfish').glob('**/*.exe'))),('Berserk',ROOT/'validation-engines'/'berserk-14-avx2.exe')]:
        p={'name':name,'path':str(path),'threads':1,'hash':32};s.save_profile(p);profiles.append(p)
    for name,settings in [('Swiss needs pairing approval',{'format':'swiss','rounds':2}),('Knockout needs manual winner',{'format':'knockout','knockout_tiebreak':'manual'}),('Completed ladder',{'format':'ladder','rounds':1,'paired':False})]:
        t=s.create_tournament(name,profiles,{'cycles':1,'time_control':{'kind':'nodes','nodes':1000}}|settings);tid=t['id'];s.set_state(tid,'running');s.fill_queue(tid,8)
        while g:=s.claim(tid):s.finish(g['aid'],'1/2-1/2' if settings['format']!='ladder' else ('1-0' if g['white']==1 else '0-1'),'fixture')
        s.fill_queue(tid,8)
    s.close();print(folder)

if __name__=='__main__':main()
