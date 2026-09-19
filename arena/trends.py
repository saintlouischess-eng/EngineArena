"""Read-only, reproducible chart series; original moves/results stay in SQLite."""
from collections import OrderedDict
import json
import math
from pathlib import Path
import sqlite3
from .stats import summarize,sprt_llr

_cache=OrderedDict()


def connect(path):
    db=sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True,timeout=30);db.row_factory=sqlite3.Row;db.execute('BEGIN');return db


def tournament_series(path,tid,slot=0,limit=600,confidence=95):
    from .stats import confidence_level
    confidence=confidence_level(confidence)
    if limit<2:raise ValueError('Chart resolution must be at least two points')
    db=connect(path)
    try:
        t=db.execute('SELECT name,settings FROM tournaments WHERE id=?',(tid,)).fetchone()
        if not t:raise ValueError('Tournament not found')
        profile=db.execute("SELECT json_extract(profile,'$.name') FROM participants WHERE tid=? AND slot=?",(tid,slot)).fetchone()
        if not profile:raise ValueError('Participant not found')
        settings=json.loads(t['settings']);paired=settings['paired'];rev=db.execute('SELECT revision FROM report_revisions WHERE tid=?',(tid,)).fetchone();revision=rev[0] if rev else 0
        seq=db.execute('SELECT body FROM sequential_state WHERE tid=?',(tid,)).fetchone();seq=json.loads(seq[0]) if seq else None
        key=(str(path),tid,slot,limit,revision,json.dumps(seq,sort_keys=True),confidence)
        if key in _cache:_cache.move_to_end(key);return _cache[key]
        clause="FROM games g JOIN attempts a ON a.id=g.official WHERE g.tid=? AND g.invalid=0 AND (g.white=? OR g.black=?) AND a.result IN ('1-0','0-1','1/2-1/2')";args=(tid,slot,slot)
        count=db.execute('SELECT count(*) '+clause,args).fetchone()[0];stride=max(1,math.ceil(count/(limit-1)));bins=[0]*5;w=d=l=0;pairs={};points=[]
        for index,r in enumerate(db.execute('SELECT g.pair_no,g.white,g.black,a.result,a.ended '+clause+' ORDER BY a.ended,g.number',args),1):
            score={'1-0':1.,'0-1':0.,'1/2-1/2':.5}[r['result']]
            if r['white']!=slot:score=1-score
            if score==1:w+=1
            elif score==.5:d+=1
            else:l+=1
            if paired:
                if r['pair_no'] in pairs:bins[round(2*(pairs.pop(r['pair_no'])+score))]+=1
                else:pairs[r['pair_no']]=score
            if index==1 or index%stride==0 or index==count:
                values=summarize(w,d,l,bins.copy() if paired else None,confidence)
                if settings['format']=='self_play':values.update(elo=None,ci=None,ci_conservative=None,ci95=None,ci95_conservative=None,los=None)
                points.append({'x':index,'time':r['ended'],**values})
        sequential=[]
        if settings['format']=='sprt':
            total=db.execute('SELECT count(*) FROM sequential_samples WHERE tid=?',(tid,)).fetchone()[0];step=max(1,math.ceil(total/(limit-1)));hist=[0]*(5 if paired else 3)
            for index,r in enumerate(db.execute("SELECT body FROM sequential_samples WHERE tid=? ORDER BY json_extract(body,'$.completed'),sample",(tid,)),1):
                evidence=json.loads(r[0]);hist[round(2*evidence['score'])]+=1
                if index==1 or index%step==0 or index==total:sequential.append({'x':index,**sprt_llr(hist,**settings['sprt'])})
        result={'name':t['name'],'confidence':confidence,'profile':profile[0],'slot':slot,'revision':revision,'paired':paired,'official_games':count,'stride':stride,'points':points,'sequential':sequential,'sequential_state':seq,
          'perspective':profile[0] if settings['format']!='self_play' else 'White side, self-play',
          'note':'Current official results ordered by completion; replacement and invalidation recompute history. Fixed-sample intervals are not stopping rules.'}
        _cache[key]=result
        while len(_cache)>8:_cache.popitem(last=False)
        return result
    finally:db.close()


def game_series(path,tid,number,limit=600):
    if number<1 or limit<2:raise ValueError('Enter a positive game number')
    db=connect(path)
    try:
        g=db.execute('SELECT * FROM games WHERE tid=? AND number=?',(tid,number-1)).fetchone()
        if not g:raise ValueError('This game has not been scheduled yet')
        a=db.execute('SELECT * FROM attempts WHERE gid=? ORDER BY seq DESC LIMIT 1',(g['id'],)).fetchone()
        if not a:return {'number':number,'points':[],'note':'No attempt has started','stride':1,'moves':0,'names':{}}
        total=db.execute('SELECT count(*) FROM moves WHERE aid=?',(a['id'],)).fetchone()[0];stride=1 if total<=limit else 2*math.ceil(total/max(2,limit-2))
        names={color:json.loads(db.execute('SELECT profile FROM participants WHERE tid=? AND slot=?',(tid,g[color])).fetchone()[0])['name'] for color in ('white','black')};points=[]
        for index,r in enumerate(db.execute('SELECT ply,fen,elapsed,clocks,info FROM moves WHERE aid=? ORDER BY ply',(a['id'],)),1):
            # Keep adjacent White/Black moves in every display bucket; sampling
            # every even ply alone would silently omit one engine's telemetry.
            if stride>1 and index%stride not in (0,1) and index!=total:continue
            info=json.loads(r['info']);clocks=json.loads(r['clocks']);color='black' if r['fen'].split()[1]=='w' else 'white'
            points.append({'x':r['ply'],'color':color,'elapsed':r['elapsed'],'clocks':clocks,**info})
        return {'number':number,'attempt':a['seq'],'mode':a['mode'],'state':g['state'] if a['ended'] is None else 'interrupted' if a['result']=='*' else 'completed','reason':a['reason'],'official':a['id']==g['official'],'invalidated':bool(g['invalid']),
          'names':names,'points':points,'moves':total,'stride':stride,'note':'Latest preserved attempt. Evaluations, mate scores and reported WDL use White perspective; other telemetry belongs to the moving engine.'}
    finally:db.close()
