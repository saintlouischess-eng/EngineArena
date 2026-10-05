"""Install a supplied older beta then upgrade, using only named test paths."""
from contextlib import closing
import argparse
import hashlib
import io
import json
import re
from pathlib import Path
import subprocess
import time
import winreg
import chess.pgn
from rc_acceptance import Candidate,ROOT

APP=ROOT/'test-output/rc-installed-app'
DATA=ROOT/'test-output/rc-installed-data'
SETUP=ROOT/'release/EngineArenaSetup-1.0.0-win-x64.exe'
KEY=r'Software\Microsoft\Windows\CurrentVersion\Uninstall\{579ABF77-881B-49B9-ACE4-E7D302683E37}_is1'


def installer(exe,label):
    log=ROOT/'test-output'/('rc-installer-'+label+'.log')
    start=time.monotonic()
    r=subprocess.run([str(exe),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/NOICONS','/TASKS=',f'/DIR={APP}',f'/LOG={log}'],creationflags=subprocess.CREATE_NO_WINDOW,timeout=240)
    assert r.returncode==0,(r.returncode,log.read_text(errors='replace')[-2000:])
    return time.monotonic()-start


def main():
    global APP,DATA,SETUP
    parser=argparse.ArgumentParser();parser.add_argument('--label',default='first');parser.add_argument('--output',type=Path,default=ROOT/'test-output/rc-installer.json')
    parser.add_argument('--previous-setup',type=Path,default=ROOT/'release/EngineArenaSetup-0.2.0-beta.2-win-x64.exe')
    parser.add_argument('--setup',type=Path,default=SETUP);args=parser.parse_args();SETUP=args.setup.resolve()
    assert re.fullmatch('[a-z0-9-]+',args.label)
    APP=APP.with_name(APP.name+'-'+args.label);DATA=DATA.with_name(DATA.name+'-'+args.label)
    assert APP.resolve().is_relative_to(ROOT/'test-output') and DATA.resolve().is_relative_to(ROOT/'test-output')
    assert not APP.exists() and not DATA.exists(),'Use a fresh acceptance installation'
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,KEY) as k:
            raise RuntimeError('An existing registered installation must be preserved; do not redirect it for testing')
    except FileNotFoundError:pass
    report={'scope':'Actual installer on the development host, not a clean Windows installation'};c=None
    try:
        report['previous_setup']=args.previous_setup.name
        report['old_install_seconds']=installer(args.previous_setup,args.label+'-previous')
        c=Candidate(APP/'EngineArena.exe',DATA);c.launch()
        ids=[]
        for name,p in [('Stockfish',ROOT/'validation-engines/stockfish/stockfish/stockfish-windows-x86-64-universal.exe'),('Berserk',ROOT/'validation-engines/berserk-14-avx2.exe')]:
            ids.append(c.api('profiles',{'name':name+' upgrade','path':str(p),'threads':1,'hash':16,'discover':True})['id'])
        c.api('preferences',{'confidence':99,'fontSize':18,'theme':'light'})
        book=DATA/'upgrade-opening.pgn';book.write_text('1. e4 e5 2. Nf3 Nc6 *',encoding='utf-8')
        t=c.tournament('Existing results retained after upgrade',ids,{'cycles':1,'max_plies':12,'time_control':{'kind':'nodes','nodes':10000}},opening_file=str(book),book_depth=4)
        c.action(t['id'],'start');before,_=c.wait(t['id']);assert before['official_games']==2
        c.stop();pgn=hashlib.sha256((DATA/'games.pgn').read_bytes()).hexdigest()
        # A file not installed by setup must survive both upgrade and uninstall.
        sentinel=APP/'unrelated-user-file.txt';sentinel.write_text('Preserve this unrelated file.')
        report['candidate_upgrade_seconds']=installer(SETUP,args.label+'-upgrade')
        assert sentinel.read_text()=='Preserve this unrelated file.'
        manifest=json.loads((APP/'package-manifest.json').read_text(encoding='utf-8-sig'))
        for row in manifest:
            path=APP/row['path'];assert path.resolve().is_relative_to(APP)
            assert path.stat().st_size==row['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'],row['path']
        report['verified_payload_files']=len(manifest)
        assert not (APP/'docs/HANDOFF.md').exists()
        assert not (APP/'Source/scripts/delete_completed_stress_tournament.py').exists()
        c.launch();after=c.api('tournaments/'+t['id'])
        for key in ('official_games','complete_pairs','settings'):
            assert before[key]==after[key],key
        # Added reliability columns are expected; original numerical values agree.
        for a,b in zip(before['standings'],after['standings']):
            for key in ('wins','draws','losses','score','elo','ci','los'):assert a[key]==b[key],key
        prefs=c.api('preferences');assert prefs['confidence']==99 and prefs['fontSize']==18 and prefs['theme']=='light'
        assert book.read_text(encoding='utf-8')=='1. e4 e5 2. Nf3 Nc6 *'
        assert hashlib.sha256((DATA/'games.pgn').read_bytes()).hexdigest()==pgn
        report['upgrade_retained_results_preferences_exact_pgn']=True
        # Verify new exports and report process in the actual installation.
        report['installed_pgn']=c.pgn(t['id'],2)
        html=c.api('tournaments/'+t['id']+'/report')['html'];assert 'Existing results retained' in html
        report['installed_report_bytes']=len(html.encode())
        c.stop();c.launch();assert c.api('tournaments/'+t['id'])['official_games']==2;c.stop()
        report['restart_passed']=True
        uninstall=APP/'unins000.exe';assert uninstall.is_file()
        r=subprocess.run([str(uninstall),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',f'/LOG={ROOT / "test-output/rc-installer-uninstall.log"}'],timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
        assert r.returncode==0 and not (APP/'EngineArena.exe').exists()
        assert sentinel.read_text()=='Preserve this unrelated file.'
        assert hashlib.sha256((DATA/'games.pgn').read_bytes()).hexdigest()==pgn
        with closing(c.db()) as db:
            assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            assert db.execute('SELECT count(*) FROM games WHERE official IS NOT NULL').fetchone()[0]==2
        report['uninstall_preserved_data_and_unrelated_file']=True
        report['installer_sha256']=hashlib.sha256(SETUP.read_bytes()).hexdigest();report['passed']=True
    except BaseException as exc:report['failure']=repr(exc);raise
    finally:
        if c:c.stop()
        args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
