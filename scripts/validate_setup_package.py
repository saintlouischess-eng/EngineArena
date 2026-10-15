"""Private 1.4.1 checks in an isolated packaged workspace; no production writes."""
from contextlib import closing
import json,time
from rc_acceptance import Candidate,ROOT


def main():
    c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',ROOT/'test-output'/('setup-package-'+time.strftime('%Y%m%d-%H%M%S')))
    report={'passed':False,'scope':'Short capped workflow checks, not strength tests','cases':[]}
    output=ROOT/'test-output/setup-package.json'
    try:
        c.launch();assert c.api('status')['active_games']==0
        paths=[ROOT/'validation-engines/stockfish/stockfish/stockfish-windows-x86-64-universal.exe',ROOT/'validation-engines/berserk-14-avx2.exe']
        profiles=[c.api('profiles',{'name':f'Package engine {i+1}','path':str(paths[i%2]),'threads':1,'hash':16,'discover':True}) for i in range(3)]
        ids=[p['id'] for p in profiles]
        imported={k:v for k,v in profiles[0].items() if k!='advertised'}
        c.api('profiles',imported|{'discover':False})
        assert c.api('profiles/bulk',{'ids':ids,'catalog':True})['missing']
        c.api('profiles/inspect-options',{'id':ids[0]})
        assert not c.api('profiles/bulk',{'ids':ids,'catalog':True})['missing']
        assert c.api('profiles?limit=3')['items'][0]['options']==imported['options']
        report['imported_profile_discovery']=True
        bookfile=c.folder/'engine-book.pgn';bookfile.write_text('1. e4 e5 2. Nf3 Nc6 *\n\n1. d4 d5 *\n',encoding='utf-8')
        book=c.api('move-books',{'path':str(bookfile)})
        patch={'threads':1,'hash':32,'move_book':{'id':book['id'],'max_plies':2,'policy':'uniform'},'options':{'SyzygyPath':r'C:\Users\Owner\Desktop\New Tablebase'}}
        preview=c.api('profiles/bulk',{'ids':ids,'patch':patch});assert preview['changed']==3 and preview['skipped']==0
        c.api('profiles/bulk',{'ids':ids,'patch':patch,'signature':preview['signature'],'apply':True})
        for p in c.api('profiles?limit=3')['items']:assert p['hash']==32 and p['move_book']['max_plies']==2
        d=c.api('setup-draft');value={'version':1,'fields':{'tname':'Recover setup','ttolerance':'.25'},'selected':ids,'candidates':[ids[2]],'control':{'kind':'nodes','nodes':1000}}
        c.api('setup-draft',{'revision':d['revision'],'value':value});c.kill();c.launch()
        assert c.api('setup-draft')['value']==value
        report['draft_forced_restart']=True
        for kind in ('nodes','movetime'):
            control={'kind':'nodes','nodes':3000} if kind=='nodes' else {'kind':'movetime','seconds':.1}
            t=c.tournament('Named gauntlet '+kind,ids,{'format':'gauntlet','candidates':1,'cycles':2,'paired':True,
                'time_control':control,'cpu_budget':2,'concurrency':2,'memory_budget_mb':4096,'max_plies':24,'tolerance':.25,
                'use_engine_books':True,'schedule_order':'balanced'},candidate_ids=[ids[2]])
            tid=t['id'];roles=c.api('selected-participants',{'recorded_participants':tid});assert roles[0]['id']==ids[2]
            c.action(tid,'start');deadline=time.monotonic()+120
            while time.monotonic()<deadline:
                status=c.api('status');s=c.api('tournaments/'+tid)
                assert not status['error'],status['error']
                assert status['active_games']<=2
                if s['state']=='completed':break
                time.sleep(.1)
            assert s['state']=='completed' and s['official_games']==8 and s['complete_pairs']==4,s
            with closing(c.db()) as db:
                failures=[dict(r) for r in db.execute("SELECT reason,count(*) n FROM attempts WHERE reason IN ('crash','timeout','hang','illegal_move','startup_timeout','protocol_error','readiness_timeout') GROUP BY reason")]
                assert not failures,failures
                assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
            html=c.api('tournaments/'+tid+'/report')['html'];assert 'Package engine 3' in html and '0.25' in html
            report['cases'].append({'control':kind,'games':8,'pairs':4,'pgn':c.pgn(tid,8),'failures':failures})
            print(f'{kind}: 8 official games, no engine failures, report and all PGN presets passed',flush=True)
        before=c.api('selected-participants',{'recorded_participants':tid})
        p=c.api('profiles/bulk',{'ids':ids,'patch':{'hash':64}});c.api('profiles/bulk',{'ids':ids,'patch':{'hash':64},'signature':p['signature'],'apply':True})
        with closing(c.db()) as db:
            assert all(json.loads(r[0])['hash']==32 for r in db.execute('SELECT profile FROM participants'))
        report['snapshot_preserved_after_bulk']=True;report['passed']=True
    finally:
        c.stop();output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'passed':True,'games':16,'forced_draft_recovery':True}),flush=True)


if __name__=='__main__':main()
