"""Globally sorted, paged standings from a separate committed read snapshot."""
from functools import lru_cache
import json
from pathlib import Path
import sqlite3
from .stats import summarize, confidence_level
from .rankings import order_sql

SORTS={'rank','name','games','wins','draws','losses','tf','points','score_pct','draw_pct','elo','ci','los','pairs','seed'}

def page(store,tid,settings,offset=0,limit=100,sort='rank',direction='asc',confidence=95,method='normal',competition=None):
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
    if settings['format'] in ('knockout','double_elimination'):
        if competition is None:
            from .knockout_results import read
            competition=read(store,tid,settings)
        positions={slot:i for i,slot in enumerate(competition['order'])}
        store.db.create_function('arena_ko_order',1,lambda slot:positions[slot],deterministic=True)
        rank_order='arena_ko_order(r.slot),r.seed'
    if settings['format']=='ladder':
        saved=store.one('SELECT body FROM round_state WHERE tid=? ORDER BY round DESC LIMIT 1',(tid,))
        if saved:
            state=json.loads(saved['body']);order=state.get('final_ladder_order',state.get('ladder_order',[]))
            if order:
                ladder=json.dumps(order);rank_order='coalesce(l.key,2147483647),r.seed'
    expressions={'rank':'r.rank','name':"json_extract(p.profile,'$.name') COLLATE NOCASE",'seed':'r.seed',
        'games':'a.w+a.d+a.l','wins':'a.w','draws':'a.d','losses':'a.l','tf':'coalesce(tf.attempts,0)','points':'r.points',
        'score_pct':'100.0*(a.w+a.d*.5)/nullif(a.w+a.d+a.l,0)',
        'draw_pct':'100.0*a.d/nullif(a.w+a.d+a.l,0)',
        'pairs':'a.p0+a.p1+a.p2+a.p3+a.p4' if paired else 'NULL'}
    expression=expressions.get(sort,'arena_sort_stat(a.w,a.d,a.l,a.p0,a.p1,a.p2,a.p3,a.p4)')
    from .reliability import tf_source
    sql=f'''WITH ranked AS (
        SELECT r.*,r.score+r.bye_points points,row_number() OVER(ORDER BY {rank_order}) rank
        FROM rankings r LEFT JOIN json_each(?) l ON l.value=r.slot WHERE r.tid=?), explained AS (
        SELECT *,lag(points) OVER(ORDER BY rank) previous_points,lag(wins) OVER(ORDER BY rank) previous_wins,
          lag(black_wins) OVER(ORDER BY rank) previous_black_wins,lag(buchholz) OVER(ORDER BY rank) previous_buchholz,
          lag(sb) OVER(ORDER BY rank) previous_sb,lag(seed) OVER(ORDER BY rank) previous_seed FROM ranked)
        SELECT r.*,a.w,a.d,a.l,a.p0,a.p1,a.p2,a.p3,a.p4,coalesce(tf.attempts,0) tf,coalesce(tf.official,0) tf_official,
            json_extract(p.profile,'$.name') name,{expression} sort_value
        FROM explained r JOIN aggregates a ON a.tid=r.tid AND a.a=r.slot AND a.b=-1
        JOIN participants p ON p.tid=r.tid AND p.slot=r.slot
        LEFT JOIN {tf_source(store.db)} tf ON tf.tid=r.tid AND tf.slot=r.slot
        ORDER BY sort_value IS NULL,sort_value {direction},r.rank ASC LIMIT ? OFFSET ?'''
    output=[]
    try:
        for r in store.rows(sql,(ladder,tid,limit,offset)):
            values=summarize(r['w'],r['d'],r['l'],[r[f'p{i}'] for i in range(5)] if paired else None,confidence)
            if selfplay:values.update(elo=None,ci=None,ci_conservative=None,ci95=None,ci95_conservative=None,los=None,model='Self-play, White perspective; no between-engine inference')
            output.append({'slot':r['slot'],'rank':r['rank'],'name':r['name'],**values,'points':r['points'],
                'tf':r['tf'],'tf_official':r['tf_official'],'bye_points':r['bye_points'],'seed':r['seed']+1,'black_wins':r['black_wins'],
                'buchholz':r['buchholz'],'sonneborn_berger':r['sb']})
            from .rankings import explanation
            output[-1].update(explanation(r,settings))
            if settings.get('rr_withdrawn_retained'):output[-1]['withdrawn']=r['slot'] in settings['rr_withdrawn_retained']
            if competition:output[-1].update({k:v for k,v in competition['people'][r['slot']].items() if k not in ('name','slot')})
            if competition:
                from .knockout import SAMPLE_NOTE
                output[-1]['model']+='; '+SAMPLE_NOTE
        return output
    finally:
        store.db.create_function('arena_sort_stat',8,None)
        if competition:store.db.create_function('arena_ko_order',1,None)

def read_snapshot(path,tid,offset=0,limit=100,sort='rank',direction='asc',confidence=95,method='normal',compact=False):
    from .store import Store
    view=Store.__new__(Store)
    view.db=sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True,timeout=30)
    view.db.row_factory=sqlite3.Row;view.revision=0;view.failure='';view.warning=''
    try:
        view.db.execute('BEGIN')
        result=view.snapshot(tid,offset,limit,sort,direction,confidence,method)
        if compact:
            result['settings']=dict(result['settings'])
            result['opening_count']=len(result['settings'].pop('openings',[]))
        return result
    finally:view.db.close()
