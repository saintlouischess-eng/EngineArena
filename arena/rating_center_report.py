"""Read-only, bounded-display rating fits; run in the low-priority report process."""

from collections import OrderedDict

from contextlib import closing

import csv

import io

import json

import math

import re

from pathlib import Path

import sqlite3

import time



from .rating_center import CATEGORIES, digest

from .rating_compute import label, compute_summary, device_label, network_label, continuity

from .ratings import fit_pool, estimate, STATUS_LABELS, SCALE

from .stats import confidence_level

from . import rating_range



_cache = OrderedDict()

NOTE = ('Opponent-adjusted logistic score ratings. CPU thread counts and identified GPU model/count/backend configurations are distinct entries. '

        'Ranks follow descending Elo within each category and selected evidence filters, before name search or display sorting. Equal estimates share a rank; unavailable ratings are unranked. '

        'Unverified GPU hardware is not treated as verified; legacy GPU entries retain their original evidence. '

        'Only complete, reversed-color opening pairs enter paired estimates; unpaired games enter individually. '

        'Separated results do not suppress finite ratings within the reference comparison group. '

        'Their games remain recorded but do not add precision to that fit; uncalibrated entries remain unranked. '

        'CPU-only pairs may span Windows build or display-driver updates when engine identities, CPU hardware and playing conditions still match. '

        'Original evidence is preserved; exact hardware and conditions filters still require both legs. '

        'CI and LOS are approximate fixed-sample estimates conditional on the fixed reference, without reference-rating uncertainty. '

        'LOS compares with that reference, not the next row. Adaptive schedules and sequential stopping can affect coverage. '

        'Time categories use nominal 60-move allocations; exact controls and hardware can differ within a list. '

        'Provisional predecessor ratings are displayed separately and never become measured games or confidence.')





def connection(path):

    db=sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True,timeout=30);db.row_factory=sqlite3.Row

    return db





def selection(q,cat=None):

    conditions=['g.pool=?','s.enabled=1','(s.retained=1 OR NOT EXISTS(SELECT 1 FROM event_children ec WHERE ec.tid=g.tid AND ec.valid=0))']

    params=[q.get('pool','main')]

    if cat:conditions.append('g.category=?');params.append(cat)

    for key,clause in (('tid','g.tid=?'),('event',"json_extract(s.context,'$.id')=?"),('hardware','c.hardware=?'),('conditions','g.conditions=?')):

        if q.get(key):conditions.append(clause);params.append(q[key])

    if q.get('season') not in ('',None):conditions.append("json_extract(s.context,'$.season')=?");params.append(int(q['season']))

    if q.get('before') is not None:conditions.append('g.ended<=?');params.append(float(q['before']))

    if q.get('failures','include')=='exclude':conditions.append("g.reason NOT IN ('timeout','crash','hang','illegal_move','interrupted','startup_timeout','readiness_timeout','protocol_error')")

    elif q.get('failures','include')!='include':raise ValueError('Unknown failure filter')

    # A conditions filter always applies to both legs, never half a paired sample.

    return 'WITH selected AS (SELECT g.* FROM rc_games g JOIN rc_sources s ON s.pool=g.pool AND s.tid=g.tid JOIN rc_conditions c ON c.id=g.conditions WHERE '+' AND '.join(conditions)+') ',params





def cpu_pair_conditions(body):

    """Comparison key only; never rewrite recorded conditions or hardware IDs.



    A CPU engine's display driver and Windows maintenance build do not define

    its playing configuration. Keep OS family/kernel, CPU inventory, memory,

    every playing rule and unknown future fields strict. GPU/legacy-GPU pairs

    do not use this key at all.

    """

    value=json.loads(body)

    hardware=value.get('hardware',{})

    if not isinstance(hardware,dict) or not hardware.get('cpu'):return digest(value)

    os=hardware.get('os')

    if isinstance(os,str):

        hardware['os']=re.sub(r'^(Windows-\d+-\d+\.\d+\.)\d+(-.*)?$',r'\1build\2',os)

    for gpu in hardware.get('gpus',[]):

        if isinstance(gpu,dict):gpu.pop('driver',None)

    return digest(value)





def data(db,q,cat):

    cte,params=selection(q,cat)

    stats_sql='''SELECT id,count(*) games,sum(w) wins,sum(d) draws,sum(l) losses,count(DISTINCT opponent) opponents FROM (

      SELECT white id,black opponent,result='1-0' w,result='1/2-1/2' d,result='0-1' l FROM selected

      UNION ALL SELECT black,white,result='0-1',result='1/2-1/2',result='1-0' FROM selected) GROUP BY id'''

    totals={r['id']:dict(r) for r in db.execute(cte+stats_sql,params)}

    # Normalize each distinct condition once, not once per game. JSON tables

    # keep this read-only and avoid SQL parameter limits on large libraries.

    condition_keys={r['id']:cpu_pair_conditions(r['body']) for r in db.execute(

        cte+'SELECT c.id,c.body FROM rc_conditions c WHERE c.id IN (SELECT conditions FROM selected)',params)}

    db.create_function('rc_cpu_pair_condition',1,lambda key:condition_keys.get(key,key),deterministic=True)

    cpu_entries=[r['id'] for r in db.execute('SELECT id,body FROM rc_entries WHERE id IN (SELECT value FROM json_each(?))',

        (json.dumps(list(totals)),)) if compute_summary(json.loads(r['body']))['kind']=='cpu']

    pair_cte=cte.rstrip()+''', pair_keys AS (

      SELECT g.*,CASE WHEN white IN (SELECT value FROM json_each(?))

        AND black IN (SELECT value FROM json_each(?)) THEN rc_cpu_pair_condition(conditions) ELSE conditions END pair_condition

      FROM selected g), pair_groups AS (

      SELECT min(white,black) a,max(white,black) b,count(*) games,

        sum(CASE WHEN result='1/2-1/2' THEN 1 WHEN (result='1-0')=(white<black) THEN 2 ELSE 0 END) bucket,

        count(*)=2 complete,

        count(DISTINCT white)=2 AND count(DISTINCT leg)=2 AND min(leg)=0 AND max(leg)=1

          AND min(min(white,black))=max(min(white,black)) AND min(max(white,black))=max(max(white,black)) identities,

        count(DISTINCT pair_condition)=1 compatible,count(DISTINCT conditions)>1 changed

      FROM pair_keys WHERE paired=1 GROUP BY tid,pair_no) '''

    pair_params=[*params,json.dumps(cpu_entries),json.dumps(cpu_entries)]

    # Stream/group in SQLite. No Python game list or participant² allocation.

    sample_sql='''SELECT a,b,size,bucket,count(*) n FROM (

      SELECT min(white,black) a,max(white,black) b,3 size,

        CASE WHEN result='1/2-1/2' THEN 1 WHEN (result='1-0')=(white<black) THEN 2 ELSE 0 END bucket

      FROM selected WHERE paired=0

      UNION ALL

      SELECT a,b,5 size,bucket FROM pair_groups

      WHERE complete AND identities AND compatible) GROUP BY a,b,size,bucket'''

    hist={};pairs=games=0

    for r in db.execute(pair_cte+sample_sql,pair_params):

        bins=hist.setdefault((r['a'],r['b'],r['size']),[0]*r['size']);bins[r['bucket']]+=r['n']

        if r['size']==5:pairs+=r['n']

        else:games+=r['n']

    sampling={k:0 for k in ('incomplete_pair_games','identity_mismatch_games','incompatible_condition_games','compatible_update_pairs')}

    for r in db.execute(pair_cte+'''SELECT

        CASE WHEN NOT complete THEN 'incomplete_pair_games' WHEN NOT identities THEN 'identity_mismatch_games'

          WHEN NOT compatible THEN 'incompatible_condition_games' ELSE 'compatible_update_pairs' END reason,

        sum(CASE WHEN complete AND identities AND compatible THEN 1 ELSE games END) n

        FROM pair_groups WHERE NOT (complete AND identities AND compatible) OR changed GROUP BY reason''',pair_params):

        sampling[r['reason']]=r['n']

    sampling['excluded_games']=sum(sampling[k] for k in ('incomplete_pair_games','identity_mismatch_games','incompatible_condition_games'))

    pool=q.get('pool','main')

    anchor=db.execute('SELECT * FROM rc_anchors WHERE pool=? AND category=?',(pool,cat)).fetchone()

    if anchor:anchor=dict(anchor)|{'explicit':True}

    else:

        ref=db.execute('SELECT entry FROM rc_refs WHERE pool=? AND category=?',(pool,cat)).fetchone()

        anchor={'entry':ref['entry'] if ref else min(totals,default=None),'rating':0.,'explicit':False}

    entries={}

    # JSON lookup avoids SQLite's host-parameter limit for large libraries.

    keys=set(totals)

    if anchor['entry']:keys.add(anchor['entry'])

    for r in db.execute('SELECT * FROM rc_entries WHERE id IN (SELECT value FROM json_each(?))',(json.dumps(list(keys)),)):

        entries[r['id']]=dict(r)

        entries[r['id']]['name']=label(json.loads(r['body']),r['threads'])

    ordered=sorted(entries);index={key:i for i,key in enumerate(ordered)}

    links={r['entry']:r['predecessor'] for r in db.execute('SELECT * FROM rc_links WHERE pool=?',(pool,))}

    return {'stats':totals,'entries':entries,'ordered':ordered,'index':index,'anchor':anchor,'links':links,

            'observations':[(index[a],index[b],bins) for (a,b,_),bins in hist.items()], 'pairs':pairs,'unpaired':games,'sampling':sampling}





def fitted(values):

    if values.get('fit') is None and values['ordered']:

        values['fit']=fit_pool(len(values['ordered']),values['observations'],values['index'][values['anchor']['entry']])

    return values





def rating(values,key,confidence,full=True):

    if key not in values['index'] or not values.get('fit'):return {'rating':None,'ci':None,'los':None,'samples':0,'status':'no_comparisons'}

    slot=values['index'][key];anchor=values['anchor'];fit=values['fit']

    if not full:

        samples=fit['participant_samples'][slot];amount=None;status=fit['status']

        if samples:

            if key==anchor['entry']:amount=anchor['rating'];status='fixed_anchor'

            elif slot not in fit['index']:status='no_finite_fit' if slot in fit['connected_index'] else 'disconnected'

            elif fit['status']=='ok':amount=anchor['rating']+SCALE*fit['theta'][fit['index'][slot]];status='estimated'

        else:status='no_comparisons'

        return {'rating':amount,'ci':None,'los':None,'samples':samples,'status':status}

    cached=values.setdefault('estimates',{});signature=(key,confidence)

    if signature in cached:return dict(cached[signature])

    row=estimate(fit,slot,values['index'][anchor['entry']],anchor['rating'],confidence)

    if not row['samples']:row.update(rating=None,delta=None,ci=None,ci95=None,los=None,status='no_comparisons')

    cached[signature]=row

    return row





def catalog(db,pool):

    conditions=[]

    for r in db.execute('SELECT c.* FROM rc_conditions c WHERE EXISTS(SELECT 1 FROM rc_games g WHERE g.pool=? AND g.conditions=c.id) ORDER BY c.id',(pool,)):

        conditions.append(dict(r)|{'body':json.loads(r['body'])})

    return conditions





def entry_details(entry):

    body=json.loads(entry['body']);compatible=continuity(body,entry['threads'])

    return {'name':entry['name'],'threads':entry['threads'],'configuration':body,

            'compute':compute_summary(body),'continuity':digest(compatible) if compatible else None}





def assign_ranks(rows):

    """Competition ranks, independent of page/search/order; ignore solver roundoff."""

    for row in rows:row['rank']=None

    rated=sorted((r for r in rows if r.get('rating') is not None and math.isfinite(r['rating'])),key=lambda r:r['rating'],reverse=True)

    previous=None;rank=None

    for position,row in enumerate(rated,1):

        value=round(row['rating'],9)

        if previous is None or value!=previous:rank=position

        row['rank']=rank;previous=value





def report(path,q=None):

    q=dict(q or {});pool=q.get('pool','main');cat=q.get('category','blitz');confidence=confidence_level(q.get('confidence',95))

    if cat not in (*CATEGORIES,'all'):raise ValueError('Unknown rating category')

    limit=rating_range.width(q.get('opponent_range'))

    if limit and cat=='all':raise ValueError('Choose one time category for opponent-range ratings')

    versions=q.get('versions','all')

    if versions not in ('all','best'):raise ValueError('Unknown version display')

    if versions=='best' and cat=='all':raise ValueError('Choose one time category for best-version ratings')

    offset=int(q.get('offset',0))

    if offset<0:raise ValueError('Invalid rating page')

    started=time.monotonic()

    with closing(connection(path)) as db:

        db.execute('BEGIN');p=db.execute('SELECT * FROM rc_pools WHERE id=?',(pool,)).fetchone()

        if not p:raise ValueError('Rating list not found')

        p=dict(p);p['rules']=json.loads(p['rules']);conditions=catalog(db,pool)

        from . import rating_families

        families=rating_families.read(db,pool)

        from .rating_aliases import read as read_aliases,decorate

        aliases,short_ids=read_aliases(db)

        workspace=db.execute('SELECT identity FROM workspace_version WHERE singleton=1').fetchone()[0]

        sig=(str(path),workspace,pool,p['revision'],tuple((k,str(q.get(k,''))) for k in ('tid','event','season','hardware','conditions','failures','before')))

        selected=CATEGORIES if cat=='all' else (cat,)

        values={}

        for c in selected:

            key=sig+(c,);v=_cache.get(key)

            if v is None:v=data(db,q,c);_cache[key]=v

            else:_cache.move_to_end(key)

            values[c]=v

    # Explicit close: sqlite context managers commit but do not close connections.

    db.close()

    for v in values.values():fitted(v)

    if limit:

        full=values[cat];key=sig+(cat,'opponent_range',limit);v=_cache.get(key)

        if v is None:

            baseline={key:rating(full,key,confidence,False) for key in full['ordered']}

            assign_ranks(list(baseline.values()))

            v=fitted(rating_range.restrict(full,limit,baseline));_cache[key]=v

        else:_cache.move_to_end(key)

        values[cat]=v

    while len(_cache)>12:_cache.popitem(last=False)

    rows=[]

    if cat=='all':

        identities=sorted(set().union(*(v['stats'] for v in values.values())))

        for identity in identities:

            entry=next(v['entries'][identity] for v in values.values() if identity in v['entries'])

            rows.append({'id':identity,**entry_details(entry),

                'categories':{c:{k:r for k,r in rating(v,identity,confidence,False).items() if k in ('rating','ci','samples','status')} for c,v in values.items()},

                'games':sum(v['stats'].get(identity,{}).get('games',0) for v in values.values())})

    else:

        v=values[cat]

        for key,stats in v['stats'].items():

            entry=v['entries'][key];r=rating(v,key,confidence,q.get('sort')=='los');predecessor=v['links'].get(key)

            seed=rating(v,predecessor,confidence,False).get('rating') if predecessor else None

            rows.append({**stats,**entry_details(entry),

                **r,'points':stats['wins']+.5*stats['draws'],'score':100*(stats['wins']+.5*stats['draws'])/stats['games'],

                'predecessor':predecessor,'provisional_seed':seed})

            if limit:

                baseline=v['baseline'][key]

                rows[-1].update(full_rating=baseline['rating'],full_rank=baseline['rank'],full_status=baseline['status'],

                    rating_change=r['rating']-baseline['rating'] if r['rating'] is not None and baseline['rating'] is not None else None,

                    **v['coverage'][key])

    for row in rows:

        rating_families.describe(row,families)

        decorate(row,aliases,short_ids)

    if versions=='best':rows=rating_families.select(rows)

    if cat=='all':

        for c in CATEGORIES:assign_ranks([row['categories'][c] for row in rows])

    else:assign_ranks(rows)

    # Search is a display-only union, after fitting and ranking, before paging/export.
    queries=tuple(dict.fromkeys(term.strip().casefold() for term in re.split(r'[,;\n]+',str(q.get('q',''))) if term.strip()))
    if queries:
        rows=[r for r in rows if any(term in field.casefold() for field in [r['name'],r['id'],r['family'],*r['profile_names']] for term in queries)]

    sort=q.get('sort','rating' if cat!='all' else 'name');direction=q.get('direction','desc' if cat!='all' else 'asc')

    if sort not in ('rank','name','rating','games','wins','draws','losses','score','opponents','samples','los',

                    'full_rating','full_rank','rating_change','included_games','included_pairs','included_opponents') or direction not in ('asc','desc'):raise ValueError('Invalid rating sort')

    rows.sort(key=lambda r:(r['name'].casefold(),r['id']))

    valid=[r for r in rows if r.get(sort) is not None];missing=[r for r in rows if r.get(sort) is None]

    valid.sort(key=lambda r:r[sort].casefold() if sort=='name' else r[sort],reverse=direction=='desc');rows=valid+missing

    # Broadcast needs point estimates, not hundreds of individual covariance solves.
    broadcast=q.get('view')=='broadcast'
    shown=rows if q.get('export') or broadcast else rows[offset:offset+50]

    for row in ([] if broadcast else shown):

        if cat=='all':

            for c,v in values.items():row['categories'][c].update(rating(v,row['id'],confidence))

        else:row.update(rating(values[cat],row['id'],confidence))

    result={'pool':p,'category':cat,'total':len(rows),'offset':offset,'items':shown,

        'conditions':conditions,'confidence':confidence,'note':NOTE,'sort':sort,'direction':direction,'snapshot':time.time(),'versions':versions}

    if limit:

        result['opponent_range']=values[cat]['opponent_range']|{'baseline_revision':p['revision'],

            'evidence_filters':{k:q.get(k) for k in ('tid','event','season','hardware','conditions','failures','before')}}

        result['note']+=' '+rating_range.NOTE

    if versions=='best':result['note']+=' Best-version view selects the highest current point estimate per family, CPU threads or verified GPU hardware/backend, and fixed limit. It does not prove superiority. Ties use samples, games, then name/ID. Unavailable estimates use one representative, not a rated winner. All versions remain in the fit; ranks describe the selected view.'

    if cat!='all':

        v=values[cat];a=v['anchor'];result.update(anchor=a|{'name':v['entries'].get(a['entry'],{}).get('name','No reference yet')},pairs=v['pairs'],

          unpaired=v['unpaired'],official_games=sum(s['games'] for s in v['stats'].values())//2,

          counted_games=2*v['pairs']+v['unpaired'],sampling=v['sampling'],status=v.get('fit',{}).get('status','no_comparisons'))

        fit=v.get('fit',{});result['fit_summary']={

            'finite_configurations':len(fit.get('members',[])) if fit.get('status')=='ok' else 0,

            'separated_configurations':len(fit.get('separated_members',[])),

            'disconnected_configurations':sum(1 for key in v['stats'] if v['index'][key] not in fit.get('connected_index',{})),

            'samples':fit.get('fit_samples',0)}

    else:result['anchors']={c:v['anchor']|{'name':v['entries'].get(v['anchor']['entry'],{}).get('name','No reference yet')} for c,v in values.items()}

    result['elapsed_ms']=1000*(time.monotonic()-started)

    for anchor in ([result['anchor']] if 'anchor' in result else list(result.get('anchors',{}).values())):

        if anchor.get('entry'):

            details=decorate({'id':anchor['entry']},aliases,short_ids)

            anchor.update(short_id=details['short_id'],profile_names=details['profile_names'])

    if q.get('export')=='csv':return csv_export(result)

    if q.get('export')=='txt':return text_export(result)

    return result





def csv_export(result):

    stream=io.StringIO();w=csv.writer(stream)

    extra=['Opponent range Elo','Full rating','Full rank','Full rating status','Rating change','Included games','Included opening pairs','Included opponents'] if result.get('opponent_range') else []

    w.writerow(['Rank','Engine','Configuration ID','Category','Threads','Games','Wins','Draws','Losses','Rating','CI lower','CI upper','Confidence','LOS vs reference','Samples','Status','Reference','Reference rating','Compute type','GPU models/count','Backend','Network','Hardware evidence','Engine family','Version view','Profile names','Profile provenance','Recorded configuration']+extra)

    for row in result['items']:

        categories=row.get('categories') or {result['category']:row}

        for cat,r in categories.items():

            ci=r.get('ci') or [None,None];a=result.get('anchor') or result.get('anchors',{}).get(cat,{})

            c=row['compute']

            comparison=([result['opponent_range']['elo'],*[row.get(k) for k in ('full_rating','full_rank','full_status','rating_change','included_games','included_pairs','included_opponents')]] if extra else [])

            w.writerow([r.get('rank'),row['name'],row['id'],cat,row['threads'],row['games'] if 'categories' not in row else '',r.get('wins'),r.get('draws'),r.get('losses'),r['rating'],*ci,result['confidence'],r.get('los'),r['samples'],r['status'],a.get('name'),a.get('rating'),c['kind'],device_label(c) if c['kind']!='cpu' else '',c['backend'],network_label(row['configuration']) if c['kind']!='cpu' else '',c['status'],row.get('family',''),result.get('versions','all'),' | '.join(row.get('profile_names',[])),row.get('provenance',''),json.dumps(row['configuration'],ensure_ascii=False,sort_keys=True)]+comparison)

    return stream.getvalue()





def text_export(result):

    def n(v):return '—' if v is None else f'{v:.1f}'

    lines=[result['pool']['name']+' — '+result['category'].title(),'Engine Arena · '+time.strftime('%Y-%m-%d %H:%M UTC',time.gmtime(result['snapshot'])),'']

    lines.append('Version view: '+('Best version per family and configuration' if result.get('versions')=='best' else 'All versions'))

    a=result.get('anchor')

    if a:lines.append(f"Reference: {a['name']} = {n(a['rating'])} ({'user anchor' if a['explicit'] else 'internal scale; not an external rating'})")

    comparison=result.get('opponent_range')

    if comparison:

        lines.append(f"Opponent range: +/-{comparison['elo']:g} Elo from all-opponent baseline; evidence revision {comparison['baseline_revision']}")

        lines.append(f"Eligible games: {comparison['included_games']:,}; excluded by range: {comparison['outside_range_games']:,}; no finite baseline: {comparison['unrated_baseline_games']:,}")

        lines.append('Games / W-D-L below are all official results in this scope. Elo / CI / LOS use the range selection.')

    rows=[]

    if result['category']=='all':

        heads=['Engine','Games',*[c+' (rank / Elo)' for c in CATEGORIES]]

        rows=[[r['name'],str(r['games']),*[f"{r['categories'][c]['rank'] or '—'} / {n(r['categories'][c]['rating'])}" for c in CATEGORIES]] for r in result['items']]

        lines += [f"{c}: {a['name']} = {n(a['rating'])} ({'user anchor' if a['explicit'] else 'internal scale'})" for c,a in result['anchors'].items()]

    else:

        heads=['Rank','Engine','Games','W','D','L','Elo',f"CI {result['confidence']:g}%",'LOS %','Samples','Status']

        from .display import los_percent

        for r in result['items']:

            rows.append([str(r['rank']) if r['rank'] is not None else '—',r['name'],str(r['games']),str(r['wins']),str(r['draws']),str(r['losses']),n(r['rating']), ' to '.join(map(n,r['ci'])) if r['ci'] else '—',los_percent(r['los']),str(r['samples']),STATUS_LABELS.get(r['status'],r['status'])])

        if comparison:

            heads+=['Full Elo','Full rank','Change','Included games','Pairs','Opponents']

            for cells,r in zip(rows,result['items']):

                cells += [n(r['full_rating']),str(r['full_rank'] or '—'),n(r['rating_change']),str(r['included_games']),str(r['included_pairs']),str(r['included_opponents'])]

        lines.append(f"Official games: {result['official_games']:,}; games in rating samples: {result['counted_games']:,}; completed pairs: {result['pairs']:,}")

        sample=result.get('sampling',{})

        if sample.get('compatible_update_pairs'):lines.append(f"Included CPU pairs across system updates: {sample['compatible_update_pairs']:,}")

        if sample.get('excluded_games'):lines.append(f"Games outside rating samples: {sample['excluded_games']:,}; partner missing from this view: {sample['incomplete_pair_games']:,}; identity/color mismatch: {sample['identity_mismatch_games']:,}; incompatible conditions: {sample['incompatible_condition_games']:,}")

        fit=result.get('fit_summary',{})

        if fit.get('separated_configurations') or fit.get('disconnected_configurations'):

            lines.append(f"Finite reference group: {fit['finite_configurations']:,} configurations from {fit['samples']:,} independent samples; separated results: {fit['separated_configurations']:,}; no completed reference path: {fit['disconnected_configurations']:,}.")

    widths=[max(len(h),*(len(r[i]) for r in rows)) if rows else len(h) for i,h in enumerate(heads)]

    lines+=['','  '.join(h.ljust(w) for h,w in zip(heads,widths)),'  '.join('-'*w for w in widths)]

    lines+=['  '.join(v.ljust(w) for v,w in zip(r,widths)) for r in rows]

    lines+=['','Profile/configuration references:']

    for r in result['items']:

        lines.append(f"{r.get('short_id',r['id'])} · {r['name']} · {' | '.join(r.get('profile_names',[])) or r.get('provenance','Unavailable')} · full ID {r['id']}")

    lines+=['',result['note'],'','Conditions:']

    for c in result['conditions']:

        b=c['body'];gpu='; '.join(g.get('name','GPU unrecorded') for g in b['hardware'].get('gpus',[]))

        lines.append(f"{c['id'][:10]} · {b['hardware'].get('cpu','Hardware unrecorded')}"+(f' · available GPUs: {gpu}' if gpu else '')+f" · controls: {json.dumps(b['controls'])}")

    return '\n'.join(lines)+'\n'





def history(path,q):

    """Paginated season/tournament endpoints, reconstructed without new game data."""

    key=q['entry'];offset=max(0,int(q.get('offset',0)));cte,params=selection(q,q.get('category','blitz'))

    with closing(connection(path)) as db:

        stages=[dict(r) for r in db.execute(cte+'''SELECT g.tid,s.name,s.context,max(g.ended) ended,count(*) games

          FROM selected g JOIN rc_sources s ON s.pool=g.pool AND s.tid=g.tid WHERE g.white=? OR g.black=?

          GROUP BY g.tid ORDER BY ended DESC LIMIT 10 OFFSET ?''',(*params,key,key,offset))]

        total=db.execute(cte+'SELECT count(DISTINCT tid) FROM selected WHERE white=? OR black=?',(*params,key,key)).fetchone()[0]

    db.close()

    for stage in stages:

        snapshot=report(path,{**q,'before':stage['ended'],'offset':0,'export':'json','q':key})

        stage['rating']=next((r for r in snapshot['items'] if r['id']==key),None)

        stage['context']=json.loads(stage['context'])

    return {'items':stages,'offset':offset,'total':total,'note':'Cumulative current official results through each stage end; later replacements revise history. Provisional seeds are not measured evidence.'}

