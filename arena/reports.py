"""Opening/color reports from a consistent read-only WAL snapshot.

Queries run outside the tournament writer. Only current official attempts count;
replacement, diagnostic replay and round invalidation need no copied game data.
"""
import csv
import io
import json
from pathlib import Path
import sqlite3
from .stats import summarize


def crosstable(path,tid,row=0,column=0,search='',confidence=95):
    if row<0 or column<0:raise ValueError('Invalid crosstable page')
    db=sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True,timeout=30);db.row_factory=sqlite3.Row
    try:
        db.execute('BEGIN')
        tournament=db.execute('SELECT settings FROM tournaments WHERE id=?',(tid,)).fetchone()
        if not tournament:raise ValueError('Tournament not found')
        settings=json.loads(tournament['settings']);where="FROM participants WHERE tid=? AND json_extract(profile,'$.name') LIKE ?";args=(tid,'%'+search+'%')
        total=db.execute('SELECT count(*) '+where,args).fetchone()[0]
        def page(offset):return [dict(r) for r in db.execute("SELECT slot,json_extract(profile,'$.name') name "+where+' ORDER BY slot LIMIT 20 OFFSET ?',(*args,offset))]
        rows=page(row);columns=page(column);cells=[]
        if rows and columns:
            sql='SELECT * FROM aggregates WHERE tid=? AND a IN ('+','.join('?' for _ in rows)+') AND b IN ('+','.join('?' for _ in columns)+') AND w+d+l>0'
            for r in db.execute(sql,(tid,*(p['slot'] for p in rows),*(p['slot'] for p in columns))):
                values=summarize(r['w'],r['d'],r['l'],[r[f'p{i}'] for i in range(5)] if settings['paired'] else None,confidence)
                if r['a']==r['b']:values.update(elo=None,ci=None,ci_conservative=None,ci95=None,ci95_conservative=None,los=None,model='Self-play, White perspective; no between-engine inference')
                cells.append({'a':r['a'],'b':r['b'],**values})
        return {'total':total,'rows':rows,'columns':columns,'cells':cells,'paired':settings['paired']}
    finally:db.close()


def counts(w,d,l):
    n=w+d+l
    return {'games':n,'wins':w,'draws':d,'losses':l,'score_pct':100*(w+d/2)/n if n else None,'draw_pct':100*d/n if n else None}


def opening_report(path,tid,slot=-1,offset=0,limit=50,export=False):
    if slot<-1 or offset<0 or limit<1:raise ValueError('Invalid report page or participant')
    db=sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True,timeout=30);db.row_factory=sqlite3.Row
    try:
        db.execute('BEGIN')
        tournament=db.execute('SELECT name,settings FROM tournaments WHERE id=?',(tid,)).fetchone()
        if not tournament:raise ValueError('Tournament not found')
        settings=json.loads(tournament['settings']);profile=None
        if slot>=0:
            p=db.execute('SELECT profile FROM participants WHERE tid=? AND slot=?',(tid,slot)).fetchone()
            if not p:raise ValueError('Participant not found')
            profile=json.loads(p[0])['name']
        revision=db.execute('SELECT revision FROM report_revisions WHERE tid=?',(tid,)).fetchone()
        cte='''WITH scored AS (
          SELECT g.pair_no,coalesce(json_extract(g.opening,'$.selection'),0) opening_index,
            json_extract(g.opening,'$.name') opening_name,json_extract(g.opening,'$.fen') fen,
            CASE WHEN ?<0 OR g.white=? THEN 'White' ELSE 'Black' END color,
            CASE WHEN a.result='1/2-1/2' THEN 1
                 WHEN (a.result='1-0')=(?<0 OR g.white=?) THEN 2 ELSE 0 END score
          FROM games g JOIN attempts a ON a.id=g.official
          WHERE g.tid=? AND g.invalid=0 AND a.result IN ('1-0','0-1','1/2-1/2')
            AND (?<0 OR g.white=? OR g.black=?)
        ) '''
        args=(slot,slot,slot,slot,tid,slot,slot,slot)
        groups='sum(score=2) w,sum(score=1) d,sum(score=0) l'
        overall=db.execute(cte+'SELECT '+groups+' FROM scored',args).fetchone()
        colors=[{'color':r['color'],**counts(r['w'],r['d'],r['l'])} for r in db.execute(cte+'SELECT color,'+groups+' FROM scored GROUP BY color ORDER BY color DESC',args)]
        total=db.execute(cte+'SELECT count(DISTINCT opening_index) FROM scored',args).fetchone()[0]
        sql=cte+''', pairs AS (SELECT opening_index,count(*) pairs FROM
            (SELECT opening_index,pair_no FROM scored GROUP BY opening_index,pair_no HAVING count(*)=2)
            GROUP BY opening_index)
          SELECT s.opening_index,s.opening_name,s.fen,'''+groups+''',coalesce(p.pairs,0) pairs
          FROM scored s LEFT JOIN pairs p ON p.opening_index=s.opening_index
          GROUP BY s.opening_index ORDER BY s.opening_index'''
        page_args=args
        if not export:sql+=' LIMIT ? OFFSET ?';page_args=(*args,limit,offset)
        base={'tournament':tid,'name':tournament['name'],'slot':slot,'profile':profile,
          'perspective':profile or 'White side across the tournament','revision':revision[0] if revision else 0,
          'total_openings':total,'offset':offset,'paired':settings['paired'],
          'summary':counts(*(overall[k] or 0 for k in ('w','d','l'))),'colors':colors,
          'model':'Descriptive official results. Color subsets are not independent opening pairs. No rating inference is made.'}
        rows=({'opening_index':r['opening_index'],'name':r['opening_name'] or 'Opening','fen':r['fen'],
              **counts(r['w'],r['d'],r['l']),'complete_pairs':r['pairs'] if settings['paired'] else None} for r in db.execute(sql,page_args))
        if export:
            output=io.StringIO();writer=csv.DictWriter(output,fieldnames=['perspective','opening_index','name','fen','games','wins','draws','losses','score_pct','draw_pct','complete_pairs']);writer.writeheader()
            for r in rows:writer.writerow({'perspective':base['perspective'],**r})
            return output.getvalue()
        return base|{'openings':list(rows)}
    finally:db.close()
