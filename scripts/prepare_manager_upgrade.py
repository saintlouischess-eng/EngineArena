"""Create a disposable predecessor-version workspace before packaging 1.1.0."""
import json,hashlib
from rc_acceptance import Candidate,ROOT

folder=ROOT/'test-output/manager-upgrade'
assert not folder.exists(),'Keep existing upgrade evidence; choose a new folder.'
c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',folder)
try:
    c.launch();profiles=[]
    for name,path in [('Stockfish',ROOT/'validation-engines/stockfish/stockfish/stockfish-windows-x86-64-universal.exe'),('Berserk',ROOT/'validation-engines/berserk-14-avx2.exe')]:
        profiles.append(c.api('profiles',{'name':name,'path':str(path),'threads':1,'hash':16,'discover':True})['id'])
    t=c.tournament('Upgrade preservation',profiles,{'cycles':2,'max_plies':12,'time_control':{'kind':'nodes','nodes':1000}})
    c.action(t['id'],'start');snapshot,_=c.wait(t['id']);assert snapshot['official_games']==4
    waiting=c.tournament('Existing sequential queue',profiles,{'cycles':1,'max_plies':8})
    c.api('tournament-queue',{'action':'add','ids':[waiting['id']]});q=c.api('tournament-queue');assert q['mode']=='paused'
    c.stop()
    evidence={'tid':t['id'],'waiting':waiting['id'],'official':4,'pgn_sha256':hashlib.sha256((folder/'games.pgn').read_bytes()).hexdigest(),'standings':snapshot['standings'],'queue_order':[x['tid'] for x in q['items']]}
    (ROOT/'test-output/manager-upgrade-before.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8');print('Predecessor results and queue saved for upgrade validation.',flush=True)
finally:c.stop()
