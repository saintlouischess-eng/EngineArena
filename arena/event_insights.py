"""Read-only competition views built from official aggregates, never move logs.

Identities are scoped to an event. Version changes retain the saved entrant ID;
new entrants get their own ID even if their display names are identical. Invalid
stages and diagnostic attempts cannot contribute to careers or season summaries.
"""
import copy
import json
import time
from . import events


def _load(value, default):
    return json.loads(value) if value else default


def _stats(row):
    w, d, l = (row.get(k, 0) or 0 for k in ('w', 'd', 'l'))
    games = w + d + l
    return dict(wins=w, draws=d, losses=l, games=games, points=w+d/2,
                score_pct=100*(w+d/2)/games if games else None)


def _identity(body, context, local, slot):
    ids = context.get('identities', [])
    return ids[local] if local < len(ids) else ('legacy:'+str(slot))


def _model(store, eid):
    # A one-event cache bounds memory. Move/telemetry writes do not invalidate a
    # standings view; official results, stage changes and roster edits do.
    event_revision=store.one('SELECT revision FROM events WHERE id=?',(eid,))
    if not event_revision:raise ValueError('Event not found')
    revisions=store.rows('''SELECT c.tid,t.state,coalesce(r.revision,0) revision,
        coalesce((SELECT sum(n) FROM game_counts WHERE tid=c.tid AND invalid=0 AND state='running'),0) active
        FROM event_children c JOIN tournaments t ON t.id=c.tid
        LEFT JOIN report_revisions r ON r.tid=c.tid WHERE c.eid=? AND c.valid=1 ORDER BY c.tid''',(eid,))
    key = (eid,event_revision['revision'],tuple((r['tid'],r['state'],r['revision'],r['active']) for r in revisions))
    cached = getattr(store, '_event_insights_cache', None)
    if cached and cached[0] == key:
        return cached[1]
    event = events.get(store, eid)
    body = event['body']; definition = body['definition']
    stages = store.rows('''SELECT c.tid,c.stage,c.bucket,c.role,t.name,t.state,t.total,
        t.note,t.dependency,json_extract(t.settings,'$.event_context') context,
        json_extract(t.settings,'$.time_control') time_control,
        json_extract(t.settings,'$.tiebreaks') tiebreaks,
        json_extract(t.settings,'$.format') format,
        json_extract(t.settings,'$.opening_source.name') book,
        json_extract(t.settings,'$.opening_policy') opening_policy,
        json_extract(t.settings,'$.seed') seed,
        json_extract(t.settings,'$.tolerance') tolerance,
        coalesce((SELECT sum(n) FROM game_counts WHERE tid=t.id AND invalid=0 AND has_official=1),0) official,
        coalesce((SELECT sum(n) FROM game_counts WHERE tid=t.id AND invalid=0 AND state='running'),0) active
        FROM event_children c JOIN tournaments t ON t.id=c.tid
        WHERE c.eid=? AND c.valid=1 ORDER BY c.stage,c.bucket,c.tid''', (eid,))
    by_tid = {}
    group_counts={}
    for stage in stages:
        if stage['role']!='playoff':group_counts[stage['stage']]=group_counts.get(stage['stage'],0)+1
    for stage in stages:
        ctx = _load(stage.pop('context'), {})
        stage['season'] = ctx.get('season', stage['stage']+1 if definition['kind']=='league' else 1)
        stage['label'] = ctx.get('label', stage['name'])
        if definition['kind']=='circuit':
            from .circuits import child_label
            stage['label']=child_label(ctx,stage['bucket'],definition,group_counts.get(stage['stage']))
        stage['time_control'] = _load(stage['time_control'], {})
        stage['tiebreaks'] = _load(stage['tiebreaks'], ['wins','seed'])
        stage['entries'] = []; stage['context'] = ctx
        by_tid[stage['tid']] = stage
    entrants = {}
    for row in store.rows('''SELECT p.tid,p.slot,p.profile,r.seed,r.bye_points,r.wins ranking_wins,
        r.black_wins,r.buchholz,r.sb,a.w,a.d,a.l
        FROM event_children c JOIN participants p ON p.tid=c.tid
        LEFT JOIN rankings r ON r.tid=p.tid AND r.slot=p.slot
        LEFT JOIN aggregates a ON a.tid=p.tid AND a.a=p.slot AND a.b=-1
        WHERE c.eid=? AND c.valid=1 ORDER BY c.stage,c.bucket,p.slot''', (eid,)):
        stage = by_tid[row['tid']]; ctx = stage['context']; p = json.loads(row['profile'])
        slot = ctx['slots'][row['slot']]
        identity = _identity(body, ctx, row['slot'], slot)
        entry = dict(identity=identity, slot=slot, local_slot=row['slot'], name=p['name'],
                     seed=row['seed'], bye_points=row['bye_points'] or 0,
                     sha256=p.get('sha256'), threads=p.get('threads',1), hash=p.get('hash',1024),
                     time_control=p.get('time_control') or stage['time_control'], **_stats(row))
        entry['points'] += entry['bye_points']
        for field in ('black_wins','buchholz','sb'): entry[field] = row[field] or 0
        stage['entries'].append(entry)
        entrant = entrants.setdefault(identity, dict(identity=identity, name=p['name'], slot=slot,
            active=False, wins=0,draws=0,losses=0,games=0,titles=[], history=[]))
        entrant['name'] = p['name']
        for field in ('wins','draws','losses','games'): entrant[field] += entry[field]
        entrant['history'].append(dict(entry,tid=stage['tid'],season=stage['season'],label=stage['label'],
            role=stage['role'],bucket=stage['bucket'],state=stage['state']))
    for stage in stages:
        columns={'wins':'wins','black_wins':'black_wins','buchholz':'buchholz','sonneborn_berger':'sb','seed':'seed'}
        stage['entries'].sort(key=lambda p:(-p['points'], *[
            p[columns[k]] if k=='seed' else -p[columns[k]] for k in stage['tiebreaks']],p['seed']))
        for i,p in enumerate(stage['entries']):p['rank']=i+1
        if stage['format'] in ('knockout','double_elimination'):
            from .knockout_results import read
            settings=json.loads(store.one('SELECT settings FROM tournaments WHERE id=?',(stage['tid'],))['settings'])
            bracket=read(store,stage['tid'],settings)
            stage['bracket']=bracket
            order={slot:i for i,slot in enumerate(bracket['order'])}
            stage['entries'].sort(key=lambda p:order[p['local_slot']])
            for p in stage['entries']:
                p['rank']=bracket['people'][p['local_slot']]['ko_finish']
    decisions = [json.loads(r['body']) for r in store.rows(
        'SELECT body FROM event_decisions WHERE eid=? ORDER BY stage', (eid,))]
    # Reproduce played placement decisions without adding playoff points to the
    # original division. A subsequent playoff may refine the same tied group.
    for decision in decisions:
        if decision.get('phase')!='playoff':continue
        before=decision['before']['season_state']; resolution=before.get('resolution',{})
        if resolution.get('phase') not in ('division','qualification'):continue
        task=resolution['tasks'][0]
        bucket=before['bucket'] if definition.get('mode')=='progressive' else task['table']
        candidates=[s for s in stages if s['season']==decision['season'] and s['role']==resolution['phase']
                    and (s['bucket']==bucket or resolution['phase']=='qualification') and s['stage']<decision['stage']-1]
        if not candidates:continue
        stage=candidates[-1]; positions={p['slot']:p for p in stage['entries']}
        ordered=[positions[s] for s in decision.get('qualified',[]) if s in positions]
        if len(ordered)==len(task['slots']):
            stage['entries'][task['start']:task['start']+len(ordered)] = ordered
            for i,p in enumerate(stage['entries']):p['rank']=i+1
    for decision in decisions:
        if decision.get('phase')!='circuit':continue
        main=[s for s in stages if s['stage']==decision['stage']-1 and s['role']!='playoff']
        for stage,rows in zip(main,decision['standings']):
            order={row['slot']:i for i,row in enumerate(rows)}
            stage['entries'].sort(key=lambda p:order[p['slot']])
            if stage['format']!='knockout':
                for i,p in enumerate(stage['entries']):p['rank']=i+1
    # Current roster is explicit, including versions which have not played yet.
    runtime=body.get('season_state') or body.get('circuit_state') or {}
    groups=runtime.get('groups') or (decisions[-1].get('next_groups') if decisions else None) or definition.get('groups',[list(range(len(body['profiles'])))])
    for bucket,group in enumerate(groups):
        for slot in group:
            p=body['profiles'][slot]
            identity=body['identities'][slot] if 'identities' in body else 'legacy:'+str(slot)
            entrant=entrants.setdefault(identity,dict(identity=identity,name=p['name'],slot=slot,
                active=False,wins=0,draws=0,losses=0,games=0,titles=[],history=[]))
            entrant.update(active=True,name=p['name'],division=bucket)
    champions=[]
    from . import season_admission
    if season_admission.enabled(definition):
        eligible=set(season_admission.pool(body))
        for slot in eligible:
            p=body['profiles'][slot];identity=body['identities'][slot]
            entrant=entrants.setdefault(identity,dict(identity=identity,name=p['name'],slot=slot,
                active=False,wins=0,draws=0,losses=0,games=0,titles=[],history=[]))
            entrant.update(candidate=True,name=p['name'])
        for entrant in entrants.values():
            if entrant['slot'] not in eligible or (runtime['season']==1 and runtime['phase']=='qualification'):
                entrant['active']=False
    for decision in decisions:
        if not decision.get('champion'):continue
        season=decision.get('season',decision['stage'])
        final=decision.get('championship'); slot=decision.get('champion_slot')
        if slot is None and final:slot=final.get('winner_slot')
        if slot is None and not final:slot=decision.get('regular_winner_slot')
        eligible=[s for s in stages if s['season']==season and s['role']==('championship' if final else 'division')]
        if definition['kind']=='circuit':eligible=[s for s in stages if s['season']==season and s['role']=='championship']
        elif not final:eligible=[s for s in eligible if s['bucket']==0]
        # A played boundary playoff may establish the winner of a league with no final.
        winner=next((p for s in reversed(eligible) for p in s['entries'] if p['slot']==slot),None) if slot is not None else None
        if winner is None and eligible and not final:
            winner=eligible[-1]['entries'][0]
        champions.append(dict(season=season,name=decision['champion'],identity=winner['identity'] if winner else None,
                              final=final,regular_winner=decision.get('regular_winner')))
        if winner:entrants[winner['identity']]['titles'].append(season)
    for stage in stages:
        for p in stage['entries']:
            item=next(h for h in entrants[p['identity']]['history'] if h['tid']==stage['tid'])
            item['rank']=p['rank']
    failures=store.rows('''SELECT f.tid,f.slot,f.reason,f.official FROM engine_failures f
        JOIN event_children c ON c.tid=f.tid WHERE c.eid=? AND c.valid=1 AND f.official>0''',(eid,))
    model=dict(event=event,definition=definition,body=body,stages=stages,by_tid=by_tid,failures=failures,
               entrants=entrants,decisions=decisions,champions=champions,groups=groups)
    store._event_insights_cache=(key,model)
    return model


def _season(model, season):
    latest=(model['body'].get('season_state') or model['body'].get('circuit_state') or {}).get('season') or max([s['season'] for s in model['stages']],default=1)
    latest=min(latest,model['definition'].get('seasons',1))
    value=int(season) if season else latest
    if not 1<=value<=max(latest,model['definition'].get('seasons',1)):
        raise ValueError('Choose a scheduled season.')
    return value


def _outcomes(model,season):
    movements=[]; placements={}; resolved=set()
    for d in model['decisions']:
        if d.get('season',d['stage'])!=season:continue
        movements.extend(d.get('movement',[]))
        if model['definition'].get('mode')=='progressive' and d.get('phase') in ('division','playoff'):
            before=d['before']['season_state']; after=d['after']['season_state']
            if d.get('phase')=='playoff' and after.get('resolution'):continue
            bucket=before['bucket'];resolved.add(bucket)
            for slot in d.get('qualified',[]):
                movements.append(dict(slot=slot,from_division=bucket,to=bucket-1,outcome='Promoted'))
            # The checkpoint records actual relegated places, including tied playoffs.
            if bucket<len(before['groups'])-1:
                for slot in d.get('next_groups',after['next_groups'])[bucket+1]:
                    if slot not in before['next_groups'][bucket+1]:
                        movements.append(dict(slot=slot,from_division=bucket,to=bucket+1,outcome='Relegated'))
        if d.get('movement') is not None:resolved.update(range(len(model['groups'])))
        if d.get('next_groups') is not None:
            placements={slot:i for i,g in enumerate(d['next_groups']) for slot in g}
    for m in movements:
        m.setdefault('from_division',m.get('from'))
    return movements,placements,resolved


def _stage_view(model,stage,movements,resolved,limit,offset=0):
    result={k:v for k,v in stage.items() if k not in ('context','entries','tiebreaks','bracket')}
    result['field']=len(stage['entries']);rows=[];d=model['definition'];bucket=stage['bucket']
    result['profile_controls']=any(p['time_control']!=stage['time_control'] for p in stage['entries'])
    admission=next((v['admission'] for v in reversed(model['decisions']) if v.get('season')==stage['season'] and 'admission' in v),None)
    plan=model['body'].get('season_state',{}).get('admission_plan')
    for index,p in enumerate(stage['entries']):
        row=copy.deepcopy(p);row['outcome']='';row['provisional']=True
        if stage['role']=='qualification' and (admission or plan):
            row['outcome']='Qualified' if (p['slot'] in admission['qualified'] if admission else index<plan['places']) else 'Not qualified'
            row['provisional']=admission is None
        if stage['role']=='division' and d['kind'] in ('league','season'):
            movement=next((m for m in movements if m['slot']==p['slot'] and m['from_division']==bucket),None)
            up=d['movement'][bucket-1] if bucket else 0
            down=d['movement'][bucket] if bucket<len(d['movement']) else 0
            row['outcome']='Promoted' if index<up else 'Relegated' if down and index>=len(stage['entries'])-down else 'Retained'
            if bucket==0 and index<2 and d.get('championship',{}).get('enabled'):row['outcome']='Championship place'
            row['provisional']=bucket not in resolved
            if movement:row['outcome']=movement['outcome'];row['provisional']=False
        if d['kind']=='circuit' and stage['role']!='playoff':
            decision=next((v for v in model['decisions'] if v['stage']==stage['stage']+1),None)
            if decision:
                row['outcome']='Champion' if decision.get('champion_slot')==p['slot'] else 'Qualified' if p['slot'] in decision['qualified'] else 'Eliminated'
                row['provisional']=False
        rows.append(row)
    offset=0 if limit is None else min(max(0,int(offset)),max(0,(len(rows)-1)//limit*limit))
    result['entries']=rows if limit is None else rows[offset:offset+limit]
    result['entry_offset']=offset
    result['entry_limit']=limit
    result['more']=len(rows)-offset-len(result['entries'])
    return result


def overview(store,eid,season=None,offset=0,full=False,entry_offsets=None):
    entry_offsets={} if entry_offsets is None else entry_offsets
    if not isinstance(entry_offsets,dict) or any(type(v) is not int or v<0 for v in entry_offsets.values()):
        raise ValueError('Choose a valid standings page.')
    model=_model(store,eid);season=_season(model,season);e=model['event'];d=model['definition']
    selected=[s for s in model['stages'] if s['season']==season]
    movements,placements,resolved=_outcomes(model,season)
    champion=next((c for c in model['champions'] if c['season']==season),None)
    runtime=model['body'].get('season_state') or model['body'].get('circuit_state') or {}
    finals=[s for s in selected if s['role']=='championship']
    final=None
    if finals:
        s=finals[-1];final=dict(tid=s['tid'],state=s['state'],games=s['official'],scheduled=s['total'],
                              players=copy.deepcopy(s['entries']),format=s['format'],label=s['label'])
        # Stage totals are not the score of the last match in a multi-engine KO.
        bracket=s.get('bracket')
        if bracket and bracket['champion_slot'] is not None and bracket['rounds']:
            last=bracket['rounds'][-1]
            if len(last['matches'])==1:
                match=last['matches'][0]
                final['deciding_match']={k:match[k] for k in ('a_name','b_name','a_score','b_score','decision_basis')}
                final['deciding_match']['round']=last['round']
                final['deciding_match']['games']=sum(v['completed'] for v in match['stages'])
                final['deciding_match']['tiebreaks']=max(0,len(match['stages'])-1)
    all_official=sum(s['official'] for s in model['stages'])
    offset=max(0,int(offset));page=selected if full else selected[offset:offset+8]
    current=min(runtime.get('season') or max([s['season'] for s in model['stages']],default=1),d.get('seasons',1))
    latest=[s for s in model['stages'] if s['stage']==e['stage']]
    phase=runtime.get('phase') or ('completed' if e['state']=='completed' else 'championship' if any(s['role']=='championship' for s in latest) else 'division')
    upcoming=[]
    if e['state'] not in ('completed','retired'):
        if runtime.get('review'):upcoming.append('Roster review')
        if phase=='qualification':upcoming+=d.get('division_names',['Divisions'])
        elif phase=='division' and d.get('mode')=='progressive':upcoming+=list(reversed(d['division_names'][:runtime['bucket']]))
        elif phase=='playoff':upcoming.append('Placement playoff')
        if phase!='championship' and d.get('championship',{}).get('enabled'):upcoming.append('Championship final')
        if current<d.get('seasons',1):upcoming.append('Next season')
    if d['kind']=='circuit':
        phase='completed' if e['state']=='completed' else d['stages'][runtime['index']]['name']
        upcoming=[] if e['state'] in ('completed','retired') else [v['name'] for v in d['stages'][runtime['index']+1:]]
        if runtime.get('review'):upcoming.insert(0,'Review competition plan')
    # Honest, deterministic highlights: actual movement and observed ranks, no
    # inferred strength or combined Elo across incompatible stage conditions.
    movers=[]
    for stage in selected:
        if stage['role']!='division' or stage['state']!='completed' or stage['format'] not in ('round_robin','swiss'):continue
        for p in stage['entries']:
            gained=p['seed']+1-p['rank']
            if gained>0:movers.append(dict(name=p['name'],identity=p['identity'],label=stage['label'],
                                         gained=gained,seed=p['seed']+1,rank=p['rank']))
    movers.sort(key=lambda p:(-p['gained'],p['name']))
    names={p['slot']:p['name'] for s in selected for p in s['entries']}
    failures=[]
    for f in model['failures']:
        stage=model['by_tid'][f['tid']]
        if stage['season']==season:
            entry=next(p for p in stage['entries'] if p['local_slot']==f['slot'])
            failures.append(dict(name=entry['name'],reason=f['reason'],games=f['official'],label=stage['label']))
    admission_result=next((v['admission'] for v in reversed(model['decisions']) if v.get('season')==season and 'admission' in v),None)
    from . import season_admission
    admission_summary=None
    if season_admission.enabled(d):
        if season==current:admission_summary=season_admission.summary(model['body'])
        elif admission_result:
            a=admission_result
            admission_summary=dict(policy=a['policy'],field_size=a['field_size'],candidate_count=a['candidates'],
                qualification_count=a['candidates']-len(a['protected']),protected_count=len(a['protected']),places=len(a['qualified']))
    return dict(id=eid,name=e['name'],state=e['state'],season=season,current_season=current,
        admission=admission_summary,admission_result=admission_result,
        seasons=d.get('seasons',1),kind=d['kind'],mode=d.get('mode','divisions'),
        division_names=d.get('division_names',[]),phase=phase,review=runtime.get('review',False),
        official=sum(s['official'] for s in selected),scheduled=sum(s['total'] for s in selected),
        all_official=all_official,active=sum(s['active'] for s in model['stages']),
        complete=champion is not None or (d['kind']=='multistage' and e['state']=='completed'),
        champion=champion,champions=model['champions'],final=final,upcoming=upcoming,
        stages=[_stage_view(model,s,movements,resolved,None if full else 50,entry_offsets.get(s['tid'],0)) for s in page],
        stage_count=len(selected),offset=offset,
        movements=[dict(m,name=m.get('name') or names.get(m['slot'],'—')) for m in movements],
        highlights=movers[:5],failures=failures,resources=_load(e['resources'],{}),
        updates=[dict(season=u['season'],stage=u['stage'],previous=u['from']['name'],name=u['to']['name'],
                      new_entry=u.get('new_entry',False)) for u in model['body'].get('updates',[]) if u['season']==season],
        generated_at=time.time())


def careers(store,eid,search='',offset=0,identity=None,rival_offset=0):
    model=_model(store,eid);offset=max(0,int(offset));rival_offset=max(0,int(rival_offset))
    if identity is None:
        entries=sorted(model['entrants'].values(),key=lambda p:(-len(p['titles']),-p['games'],p['name'].casefold(),p['identity']))
        entries=[p for p in entries if search.casefold() in p['name'].casefold() or any(search.casefold() in h['name'].casefold() for h in p['history'])]
        return dict(total=len(entries),offset=offset,items=[{k:v for k,v in p.items() if k!='history'} for p in entries[offset:offset+50]])
    if identity not in model['entrants']:raise ValueError('Choose an entrant from this competition.')
    entrant=model['entrants'][identity];rivals={};versions={}
    for h in entrant['history']:
        key=(h['name'],h['sha256'])
        v=versions.setdefault(key,dict(name=h['name'],sha256=h['sha256'],games=0,first_season=h['season'],last_season=h['season']))
        v['games']+=h['games'];v['last_season']=max(v['last_season'],h['season'])
        stage=model['by_tid'][h['tid']];lookup={p['local_slot']:p for p in stage['entries']}
        for a in store.rows('SELECT b,w,d,l FROM aggregates WHERE tid=? AND a=? AND b>=0 AND b<>a',(h['tid'],h['local_slot'])):
            opponent=lookup[a['b']];rid=opponent['identity'];stats=_stats(a)
            r=rivals.setdefault(rid,dict(identity=rid,name=model['entrants'][rid]['name'],wins=0,draws=0,losses=0,games=0))
            for k in ('wins','draws','losses','games'):r[k]+=stats[k]
    rivalry=sorted(rivals.values(),key=lambda r:(-r['games'],r['name']))
    result={k:v for k,v in entrant.items() if k!='history'}
    result.update(history=list(reversed(entrant['history']))[offset:offset+50],history_count=len(entrant['history']),
                  offset=offset,versions=list(versions.values()),rivals=rivalry[rival_offset:rival_offset+50],rival_count=len(rivalry),rival_offset=rival_offset)
    return result
