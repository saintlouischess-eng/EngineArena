"""Durable, attempt-specific manual decisions; recovery honors accepted requests."""
import json


def initialize(store):
    if 'adjudication' not in {r['name'] for r in store.rows('PRAGMA table_info(attempts)')}:
        with store.tx():store.db.execute('ALTER TABLE attempts ADD COLUMN adjudication TEXT')


def request(store,tid,gid,aid,result,note):
    if result not in ('1-0','0-1','1/2-1/2'):raise ValueError('Choose White wins, Draw or Black wins')
    if not isinstance(note,str) or not note.strip() or len(note)>1000:raise ValueError('Enter an adjudication reason (1–1000 characters)')
    note=' '.join(note.split())
    if any(ord(c)<32 for c in note):raise ValueError('Adjudication reason must be readable text')
    with store.tx():
        attempt=store.one('SELECT a.*,g.tid,g.state,g.invalid FROM attempts a JOIN games g ON g.id=a.gid WHERE a.id=? AND g.id=? AND g.tid=?',(aid,gid,tid))
        if not attempt or attempt['ended'] is not None or attempt['state']!='running' or attempt['invalid']:
            raise ValueError('This attempt is no longer running. Refresh the game before adjudicating.')
        decision={'result':result,'note':note}
        if attempt['adjudication']:
            if json.loads(attempt['adjudication'])!=decision:raise ValueError('An adjudication decision is already being saved for this attempt')
            return decision
        store.db.execute('UPDATE attempts SET adjudication=? WHERE id=?',(json.dumps(decision),aid))
        if attempt['mode']!='diagnostic' and store.tournament(tid)['settings']['format']=='sprt':
            from .sequential import frozen,invalidate
            if not frozen(store,tid):
                invalidate(store,tid,'A game was manually adjudicated. Descriptive results remain available; start a new test for valid sequential inference.')
        store.audit(tid,'manual_adjudication_requested',{'game':gid,'attempt':aid,**decision})
    return decision
