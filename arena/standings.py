"""Globally sorted, paged standings from a separate committed read snapshot."""
from functools import lru_cache
import json
from pathlib import Path
import sqlite3
from .stats import summarize, confidence_level
from .rankings import order_sql

SORTS={'rank','name','games','wins','draws','losses','points','score_pct','draw_pct','elo','ci','los','pairs','seed'}

def page(store,tid,settings,offset=0,limit=100,sort='rank',direction='asc',confidence=95,method='normal'):
    confidence=confidence_level(confidence)
    if sort not in SORTS or direction not in ('asc','desc') or method not in ('normal','conservative'):
        raise ValueError('Unknown standings sort or interval method')
    if offset<0 or limit<1:raise ValueError('Invalid standings page')
    paired=settings['paired'];selfplay=settings['format']=='self_play'
    @lru_cache(maxsize=256)
    def statistic(w,d,l,*bins):
        if selfplay and sort in ('elo','ci','los'):return None
        value=summarize(w,d,l,list(bins) if paired else None,confidence)
        if sort=='ci':
            interval=value['ci_conservative' if method=='conservative' else 'ci']
            if interval is None:return None
            return float('inf') if any(isinstance(v,str) for v in interval) else interval[1]-interval[0]
        value=value.get(sort)
        return float(value.replace('infinity','inf')) if isinstance(value,str) else value
    store.db.create_function('arena_sort_stat',8,statistic,deterministic=True)
    # Ranking always retains the tournament's official tiebreak/ladder order.
    rank_order=order_sql(settings)
    ladder='[]'
    if settings['format']=='ladder':
        saved=store.one('SELECT body FROM round_state WHERE tid=? ORDER BY round DESC LIMIT 1',(tid,))
        if saved:
            state=json.loads(saved['body']);order=state.get('final_ladder_order',state.get('ladder_order',[]))
            if order:
                ladder=json.dumps(order);rank_order='coalesce(l.key,2147483647),r.seed'
    expressions={'rank':'r.rank','name':"json_extract(p.profile,'$.name') COLLATE NOCASE",'seed':'r.seed',
        'games':'a.w+a.d+a.l','wins':'a.w','draws':'a.d','losses':'a.l','points':'r.points',
        'score_pct':'100.0*(a.w+a.d*.5)/nullif(a.w+a.d+a.l,0)',
        'draw_pct':'100.0*a.d/nullif(a.w+a.d+a.l,0)',
        'pairs':'a.p0+a.p1+a.p2+a.p3+a.p4' if paired else 'NULL'}
    expression=expressions.get(sort,'arena_sort_stat(a.w,a.d,a.l,a.p0,a.p1,a.p2,a.p3,a.p4)')
    sql=f'''WITH ranked AS (
        SELECT r.*,r.score+r.bye_points points,row_number() OVER(ORDER BY {rank_order}) rank
        FROM rankings r LEFT JOIN json_each(?) l ON l.value=r.slot WHERE r.tid=?)
        SELECT r.*,a.w,a.d,a.l,a.p0,a.p1,a.p2,a.p3,a.p4,
            json_extract(p.profile,'$.name') name,{expression} sort_value
        FROM ranked r JOIN aggregates a ON a.tid=r.tid AND a.a=r.slot AND a.b=-1
        JOIN participants p ON p.tid=r.tid AND p.slot=r.slot
        ORDER BY sort_value IS NULL,sort_value {direction},r.rank ASC LIMIT ? OFFSET ?'''
    output=[]
    try:
        for r in store.rows(sql,(ladder,tid,limit,offset)):
            values=summarize(r['w'],r['d'],r['l'],[r[f'p{i}'] for i in range(5)] if paired else None,confidence)
            if selfplay:values.update(elo=None,ci=None,ci_conservative=None,ci95=None,ci95_conservative=None,los=None,model='Self-play, White perspective; no between-engine inference')
            output.append({'slot':r['slot'],'rank':r['rank'],'name':r['name'],**values,'points':r['points'],
                'bye_points':r['bye_points'],'seed':r['seed']+1,'black_wins':r['black_wins'],
                'buchholz':r['buchholz'],'sonneborn_berger':r['sb']})
        return output
    finally:
        store.db.create_function('arena_sort_stat',8,None)

def read_snapshot(path,tid,offset=0,limit=100,sort='rank',direction='asc',confidence=95,method='normal'):
    from .store import Store
    view=Store.__new__(Store)
    view.db=sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True,timeout=30)
    view.db.row_factory=sqlite3.Row;view.revision=0;view.failure='';view.warning=''
    try:
        view.db.execute('BEGIN')
        return view.snapshot(tid,offset,limit,sort,direction,confidence,method)
    finally:view.db.close()
