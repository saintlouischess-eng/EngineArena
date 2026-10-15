from .i18n import t as _t,h as _h,message as _message
"""Concise standalone HTML report from one committed read-only snapshot."""
from datetime import datetime,timezone
import hashlib
import html
import json
from pathlib import Path
import sqlite3
from .stats import summarize
from .rankings import rows as ranked_rows
from .display import los_percent


class Snapshot:
    def __init__(self,db):self.db=db
    def rows(self,sql,args=()):return [dict(r) for r in self.db.execute(sql,args)]
    def one(self,sql,args=()):
        row=self.db.execute(sql,args).fetchone();return dict(row) if row else None
    def participant(self,tid,slot):return json.loads(self.one('SELECT profile FROM participants WHERE tid=? AND slot=?',(tid,slot))['profile'])


def number(value,digits=1):
    if value is None:return '—'
    if value=='+infinity':return '+∞'
    if value=='-infinity':return '−∞'
    from .i18n import number as localized_number
    return localized_number(value,digits) if isinstance(value,(int,float)) else str(value)


def time_description(control):
    kind=control.get('kind','fischer')
    if kind=='nodes':return _t('{0} nodes per move; no chess clock' ,f"{control.get('nodes', 10000):,}")
    if kind=='depth':return _t('Depth {0}; no chess clock' ,f"{control.get('depth', 12)}")
    if kind=='movetime':return _t('{0} seconds per move' ,f"{control.get('seconds', 180)}")
    if kind=='staged':
        stages=[]
        for stage in control.get('stages',[]):
            moves=stage.get('moves',0)
            text=_t('{0} moves in' ,f'{moves}') if moves else _t('Rest of game in')
            text+=_t(' {0} seconds' ,f"{stage.get('seconds', 0):g}")
            if stage.get('increment',0):text+=_t(' + {0} seconds per move' ,f"{stage['increment']:g}")
            stages.append(text)
        return _t('; then ').join(stages)+(_t('; repeat final stage') if control.get('repeat') else '')
    text=_t('{0} seconds' ,f"{control.get('seconds', 180)}")
    if kind=='fischer':text+=_t(' + {0} seconds increment' ,f"{control.get('increment', 2)}")
    if kind in ('delay','bronstein'):text+=_t('; {0} {1} seconds' ,f'{kind}',f"{control.get('delay', 0)}")
    return text


def render(path,tid,confidence=95,all_engines=False,technical=True):
    from .stats import confidence_level
    confidence=confidence_level(confidence)
    db=sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True,timeout=30);db.row_factory=sqlite3.Row;view=Snapshot(db)
    try:
        db.execute('BEGIN');t=view.one('SELECT * FROM tournaments WHERE id=?',(tid,))
        if not t:raise ValueError(_t('Tournament not found'))
        from . import report_cache
        cache_key=report_cache.key(view,tid,confidence,all_engines,technical) if t['state']=='completed' else None
        cached=report_cache.read(path,cache_key)
        if cached is not None:return cached
        settings=json.loads(t['settings']);participants=view.one('SELECT count(*) n FROM participants WHERE tid=?',(tid,))['n']
        event_context=settings.get('event_context')
        event_member=view.one('SELECT valid FROM event_children WHERE tid=?',(tid,)) if event_context else None
        custom_rows=[]
        if settings['format']=='custom':
            names={r['slot']:json.loads(r['profile'])['name'] for r in view.rows('SELECT slot,profile FROM participants WHERE tid=?',(tid,))}
            custom_rows=[(names[v['a']],names[v['b']],v['count'],v['count']*(2 if settings['paired'] else 1)) for v in settings['custom_matchups']]
        competition=None
        if settings['format'] in ('knockout','double_elimination'):
            from .knockout_results import read
            competition=read(view,tid,settings)
        revision=view.one('SELECT revision FROM report_revisions WHERE tid=?',(tid,));revision=revision['revision'] if revision else 0
        ranked=ranked_rows(view,tid,settings,0,participants if all_engines else 50);standings=[]
        from .reliability import tf_source
        failures={r['slot']:r for r in view.rows('SELECT * FROM '+tf_source(view.db)+' WHERE tid=?',(tid,))}
        for rank in ranked:
            profile=json.loads(view.one('SELECT profile FROM participants WHERE tid=? AND slot=?',(tid,rank['slot']))['profile'])
            agg=view.one('SELECT * FROM aggregates WHERE tid=? AND a=? AND b=-1',(tid,rank['slot']))
            summary=summarize(agg['w'],agg['d'],agg['l'],[agg[f'p{i}'] for i in range(5)] if settings['paired'] else None,confidence)
            if settings['format']=='self_play':summary.update(elo=None,ci=None,ci_conservative=None,ci95=None,ci95_conservative=None,los=None)
            failure=failures.get(rank['slot'],{});summary.update(tf=failure.get('attempts',0),tf_official=failure.get('official',0))
            standings.append({'rank':rank,'profile':profile,'summary':summary})
        source='FROM games g JOIN attempts a ON a.id=g.official WHERE g.tid=? AND g.invalid=0'
        results=view.rows('SELECT a.result,count(*) n '+source+' GROUP BY a.result',(tid,));terminations=view.rows('SELECT a.reason,count(*) n '+source+' GROUP BY a.reason ORDER BY n DESC,a.reason',(tid,))
        attempts=view.rows('SELECT a.mode,count(*) n FROM attempts a JOIN games g ON g.id=a.gid WHERE g.tid=? GROUP BY a.mode',(tid,))
        interrupted=view.one("SELECT count(*) n FROM attempts a JOIN games g ON g.id=a.gid WHERE g.tid=? AND a.result='*'",(tid,))['n']
        counts=view.rows('SELECT state,count(*) n FROM games WHERE tid=? AND invalid=0 GROUP BY state',(tid,))
        complete_pairs=view.one('SELECT coalesce(sum(p0+p1+p2+p3+p4),0) n FROM aggregates WHERE tid=? AND b=-1',(tid,))['n']//(1 if settings['format']=='self_play' else 2) if settings['paired'] else None
        seq=view.one('SELECT body FROM sequential_state WHERE tid=?',(tid,));anchor=view.one("SELECT a.slot,a.rating,json_extract(p.profile,'$.name') name FROM rating_anchors a JOIN participants p ON p.tid=a.tid AND p.slot=a.slot WHERE a.tid=?",(tid,))
        if settings['format']=='sprt':
            from .sequential import presentation
            from .stats import sprt_llr
            sequential=json.loads(seq['body']) if seq else sprt_llr([0]*(5 if settings['paired'] else 3),**settings['sprt'])
            sprt_status=presentation(view,t|{'settings':settings},sequential)
        from .report_evidence import collect
        evidence=collect(view,tid,settings,standings)
        from .report_overview import collect as overview
        evidence['overview']=overview(view,tid,[item['rank']['slot'] for item in standings])
        if technical:
            from .engine_readout import collect as technical_readouts
            # Numerical measurements do not depend on language or confidence.
            # Reuse the expensive scan when only report presentation changes.
            technical_key=report_cache.snapshot_key(view,['technical',tid,sorted(x['rank']['slot'] for x in standings)]) if t['state']=='completed' else None
            data=report_cache.read_technical(path,technical_key)
            if data is None:
                data=technical_readouts(view,tid,settings,standings,evidence['sessions'])
                report_cache.write_technical(path,technical_key,data)
            evidence['technical']=data
    finally:db.close()
    from .report_sections import label,failures,environment,engine_sections
    esc=lambda v:html.escape(str(v),quote=True)
    total=sum(r['n'] for r in results);timestamp=datetime.now(timezone.utc).isoformat(timespec='seconds');settings_hash=hashlib.sha256(t['settings'].encode()).hexdigest()
    def table(headers,rows):return '<div class="report-table" tabindex="0" role="region" aria-label="'+esc(' / '.join(headers[:2]))+_h('"><table><thead><tr>')+''.join(_h('<th scope="col">')+esc(h)+'</th>' for h in headers)+_h('</tr></thead><tbody>')+''.join(_h('<tr>')+''.join(_h('<td>')+esc(number(v,0) if isinstance(v,int) and not isinstance(v,bool) else v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
    def interval(value):return _t(' to ').join(number(v) for v in value) if value else _t('Unavailable')
    summary=_h('<div class="metrics"><b>{0}<small>official games / {1} scheduled</small></b><b>{2}<small>participants</small></b><b>{3}<small>completed opening pairs</small></b><b>{4}<small>tournament state</small></b></div>' ,number(total,0),number(t['total'],0),number(participants,0),number(complete_pairs,0) if complete_pairs is not None else _t('Unpaired'),esc(label(t['state'])))
    condition_rows=[(_t('Format'),settings['format']),(_t('Time control'),time_description(settings['time_control'])),(_t('Concurrency'),settings['concurrency']),(_t('Ponder'),settings['ponder']),(_t('Paired openings'),settings['paired']),(_t('Opening book file'),settings.get('opening_source',{}).get('name') or _t('Not recorded')),(_t('Opening positions'),len(settings.get('openings',[]))),(_t('Opening order / seed'),f"{settings['opening_order']} / {settings['seed']}"),(_t('Variant'),'Chess960' if settings['chess960'] else _t('Standard chess')),(_t('Tiebreaks'),', '.join(settings['tiebreaks'])),(_t('Automatic retry limit'),settings['retry_limit']),(_t('Watchdogs, seconds'),_t('Startup {0}; readiness {1}; search {2}; stop {3}' ,f"{settings['startup_timeout']}",f"{settings['readiness_timeout']}",f"{settings['hang_timeout']}",f"{settings['stop_timeout']}"))]
    from .knockout import format_name,round_title
    if event_context:
        condition_rows.extend([(_t('Event'),event_context['name']),(_t('Event stage'),event_context['label']),(_t('Event status'),_t('Current stage') if event_member and event_member['valid'] else _t('Archived / superseded'))])
    if settings.get('rr_extensions'):
        condition_rows.append((_t('Round-robin extensions'),len(settings['rr_extensions'])))
        condition_rows.append((_t('Retained original games'),settings['rr_extensions'][0]['start']*(2 if settings['paired'] else 1)))
    condition_rows[0]=(_t('Format'),_t(format_name(settings['format'])))
    condition_rows=[(_t('Opening positions available'),value) if key==_t('Opening positions') else (key,value) for key,value in condition_rows]
    from .schedule_order import LABELS
    condition_rows.extend([(_t('Game scheduling'),_t(LABELS[settings.get('schedule_order','legacy')])),
        (_t('Scheduling seed'),settings.get('schedule_seed',7970) if settings.get('schedule_order')=='shuffle' else _t('Not applicable')),
        (_t('Unique starting positions used'),evidence['openings']['used']),
        (_t('Opening assignment'),{'pair':_t('Fresh position per reversed opening pair') if settings['paired'] else _t('Fresh position per game'),'round':_t('One shared position per round'),'cycle':_t('Shared ordered opening suite'),'fixed':_t('One fixed position throughout'),'legacy':_t('Legacy sequential assignment')}.get(settings.get('opening_policy','legacy'))),
        (_t('Book import depth'),str(settings.get('opening_source',{}).get('depth',_t('Not recorded')))+_t(' plies (half-moves)')),
        (_t('Initial seeding'),settings.get('seeding',_t('Not recorded'))),(_t('Clock tolerance'),_t('{0} seconds' ,f"{settings.get('tolerance', 0):g}")),
        (_t('GUI move overhead'),_t('{0} seconds' ,f"{settings.get('overhead', 0):g}")),
        (_t('Draw claims'),_t('Enabled') if settings['claim_draws'] else _t('Disabled')),
        (_t('Resign adjudication'),_t('{0} cp for {1} plies' ,f"{settings['resign_cp']}",f"{settings['resign_plies']}") if settings['resign_cp'] else _t('Disabled')),
        (_t('Draw adjudication'),_t('Within {0} cp for {1} plies, after {2} played plies from the starting position' ,f"{settings['draw_cp']}",f"{settings['draw_plies']}",f"{settings['draw_after']}") if settings['draw_cp'] else _t('Disabled')),
        (_t('Maximum played plies'),settings['max_plies'] or _t('No adjudication limit')),
        (_t('GUI tablebase adjudication'),_t('Configured') if settings.get('syzygy_path') else _t('Disabled'))])
    if competition:
        from .opening_policy import shared_ko
        if shared_ko(settings):
            advancing=evidence['openings']['advancing_shared'] or 0
            assignment=(_t('Shared sequence across KO matches; new position per ')+(_t('reversed-color pair') if settings['paired'] else _t('game'))+_t(', including tiebreaks and later rounds')) if advancing or not total else _t('Legacy shared round/suite in recorded games')+(_t('; newly scheduled KO stages advance to fresh positions') if t['state']!='completed' else '')
            if advancing and advancing<total:assignment+=_t('; earlier recorded stages retain their legacy openings')
            condition_rows=[(key,assignment if key==_t('Opening assignment') else value) for key,value in condition_rows]
        condition_rows=[r for r in condition_rows if r[0]!=_t('Tiebreaks')]
        condition_rows.append((_t('KO results order'),_t('Surviving engines, then latest elimination round; initial seed orders engines with the same elimination status')))
        condition_rows.append((_t('KO tied matches'),_t('Keep playing until a match winner') if settings.get('knockout_tiebreak')=='continuous' else _t('Recorded policy: ')+settings.get('knockout_tiebreak','seed')))
        condition_rows.append((_t('Games per tiebreak stage'),settings.get('playoff_cycles',1)*(2 if settings['paired'] else 1)))
        if settings.get('ko_round_games'):condition_rows.append((_t('Games per match by round'),'; '.join(_t('Round {0}: {1}' ,f'{i + 1}',f'{games}') for i,games in enumerate(settings['ko_round_games']))))
        controls=settings.get('playoff_controls',[])
        condition_rows.append((_t('Tiebreak time controls'),_t('; then ').join(time_description(c) for c in controls)+_t('; repeat final control while tied') if controls else _t('Keep each engine’s normal control, including handicaps')))
        if controls:condition_rows.append((_t('Tiebreak override'),_t('Listed controls replace normal controls for both engines during tiebreaks; clocks restart for every game')))
        if settings.get('knockout_tiebreak')=='continuous':condition_rows.append((_t('Total game limit'),_t('Regular games plus added tiebreaks; no finite maximum while matches remain tied')))
    rows=[];statistics=[]
    for i,item in enumerate(standings,1):
        rank,p,s=item['rank'],item['profile'],item['summary']
        rows.append([rank['seed']+1 if competition else i,p['name'],s['games'],'–'.join(number(s[k],0) for k in ('wins','draws','losses')),number(rank['points']),number(s['score_pct'],2),number(s['draw_pct'],2),s['tf'],s['tf_official']])
        if competition:rows[-1][2:2]=[rank.get('ko_finish',rank['ko_status']),f"{rank['match_wins']}–{rank['match_losses']}"]
        if settings['format']=='swiss':rows[-1].insert(5,number(rank['bye_points']))
        statistics.append([p['name'],s['pairs'] if settings['paired'] else s['games'],number(s['elo']),interval(s['ci']),interval(s['ci_conservative']),los_percent(s['los'])])
    body=_h('<h1>{0}</h1><p class="muted">Engine Arena tournament report · {1} · committed result revision {2}</p>' ,f"{esc(t['name'])}",f'{esc(timestamp)}',f'{revision}')+summary
    playoffs=evidence['openings']['playoffs'] or 0
    body+=_h('<p>')+_t('{0} regular games + {1} tiebreak games = {2} official games. ' ,f'{total - playoffs:,}',f'{playoffs:,}',f'{total:,}')+(_t('{0}% of the current schedule complete.' ,f"{100 * total / t['total']:.1f}") if t['total'] else _t('No games scheduled.'))+'</p>'
    if t['dependency'] or (t['state']!='completed' and t['note'] and not (competition and t['note'].startswith('Winner:'))):body+=_h('<p class="notice">')+esc(_message(t['dependency'] or t['note']))+'</p>'
    from .report_evidence import FAILURES
    failure_total=sum(r['n'] for r in terminations if r['reason'] in FAILURES)
    if failure_total:body+=_h('<p class="notice">')+str(failure_total)+_h(' failure forfeits are included in the official results and can affect advancement. See Failed games included in official results below.</p>')
    if competition:
        body+=_h('<h2>Knockout (KO) results</h2><p class="notice">')+esc(_t('Champion: ')+competition['champion'] if competition['champion'] else _t('Round {0} · {1} engines still in the KO' ,f"{competition['round']}",f"{competition['remaining']}"))+_h('</p><p>')+esc(_message(competition['note']))+'</p>'
        fault_map={}
        for f in evidence['failures']:fault_map.setdefault((f['round']+1,min(f['white'],f['black']),max(f['white'],f['black'])),[]).append(f)
        impact_map={(f['round']+1,f['a'],f['b']):f for f in evidence['failure_matches']}
        for r in competition['rounds']:
            body+=_h('<h3>')+esc(_message(round_title(settings,participants,r['round'])))+'</h3>'
            for m in r['matches']:
                body+=_h('<h4>')+esc(m['a_name']+_t(' vs ')+m['b_name'])+'</h4>'
                body+=_h('<p>')+esc(_t('Overall score: {0}–{1}. ' ,f"{m['a_score']:g}",f"{m['b_score']:g}")+_message(m['status']))+'</p>'
                match_rows=[]
                for stage in m['stages']:
                    latest=stage is m['stages'][-1]
                    match_rows.append([_t('Tiebreak ')+str(stage['stage']) if stage['stage'] else _t('Regular match'),
                        f"{stage['a_score']:g} – {stage['b_score']:g}",f"{stage['completed']} / {stage['games']}",
                        time_description(stage['time_control']) if stage['time_control'] else time_description(settings['time_control'])+_t(' (engine overrides below)'),
                        _message(m['decision_basis']) if latest and m['winner'] is not None else _t('In progress') if not stage['finished'] else _t('Tied; continued') if not latest else m['status']])
                body+=table([_t('Stage'),_t('A – B score'),_t('Games done / scheduled'),_t('Time control'),_t('Outcome')],match_rows)
                key=(r['round'],min(m['a'],m['b']),max(m['a'],m['b']))
                faults=fault_map.get(key,[])
                if faults:body+=_h('<p class="notice">Failure forfeits in this match: ')+esc(', '.join(_t('game {0} ({1})' ,f"{f['number'] + 1}",f"{f['reason'].replace('_', ' ')}") for f in faults))+'. These results count toward the displayed score.</p>'
                impact=impact_map.get(key)
                if impact:
                    score=impact['score'] if impact['a']==m['a'] else impact['games']-impact['score']
                    remaining=sum(v['completed'] for v in m['stages'])-impact['games']
                    body+=_h('<p>')+esc(_t('{0} failure forfeits included. The other {1} completed games scored {2}–{3}. This does not predict replay outcomes.' ,f"{impact['games']}",f'{remaining}',f"{m['a_score'] - score:g}",f"{m['b_score'] - (impact['games'] - score):g}"))+'</p>'
            if r['byes']:body+=_h('<p>Byes: ')+esc(', '.join(p['name'] for p in r['byes']))+'. No played game or match win is awarded.</p>'
        if not competition['rounds']:body+=_h('<p>No round has started.</p>')
    body+=_h('<h2>Standings</h2><p>')+(_t('All ')+str(participants)+_t(' participants') if len(rows)==participants else _t('First ')+str(len(rows))+_t(' of ')+str(participants)+_t(' participants'))+_t(' in tournament order. Standings CSV/JSON/Text exports contain the full standings.')+(_t(' Choose All engines in the report controls to include every engine’s configuration and technical readout.') if len(rows)<participants else '')+'</p>'
    body+=_h('<p>TF counts time forfeits in all competition attempts, including retries and replaced results. Diagnostics are excluded. Official TF counts only current official losses.</p>')
    headers=[_t('Seed') if competition else '#',_t('Engine profile'),_t('Games'),_t('Game W–D–L') if competition else 'W–D–L',_t('Game points') if competition else _t('Points'),_t('Score %'),_t('Draw %'),'TF',_t('Official TF')]
    if competition:headers[2:2]=[_t('KO finish / status'),_t('Match W–L')]
    if settings['format']=='swiss':
        headers.insert(5,_t('Bye points'))
        body+=_h('<p>Points include bye awards. Bye points do not count as played games or enter Elo, CI or LOS.</p>')
    body+=table(headers,rows)
    body+=_h('<h2>Descriptive game statistics</h2>')+table([_t('Engine'),_t('Complete pairs') if settings['paired'] else _t('Games'),_t('Δ Elo vs own opponents'),_t('Normal {0}% CI' ,f'{confidence:g}'),_t('Conservative {0}% CI' ,f'{confidence:g}'),_t('LOS %')],statistics)
    body+=_h('<p class="muted">Logistic Elo relative to each engine’s sampled opposition, not an opponent-adjusted common pool rating. ')+(_t('Paired estimates use only complete opening pairs.') if settings['paired'] else _t('Unpaired estimates use individual games.'))+_h(' Normal intervals and LOS are approximate; conservative intervals use Hoeffding bounds. Both require independent fixed samples and are not sequential stopping rules. LOS is not the probability of being the strongest engine in the field.</p>')
    if settings['paired']:
        body+=_h('<p>{0} official games are included in complete opening pairs; {1} await a matching result. W–D–L and points include all official games.</p>',number(2*complete_pairs,0),number(total-2*complete_pairs,0))
    if competition:body+=_h('<p class="notice">KO opponents and sample sizes depend on earlier results. These fixed-sample estimates are descriptive approximations; the nominal confidence level is not a calibrated guarantee for this adaptive tournament. Different time controls are pooled.</p>')
    if competition and playoffs:
        names={x['rank']['slot']:x['profile']['name'] for x in standings}
        order={slot:index for index,slot in enumerate(names)}
        body+=_h('<h3>Regular games and tiebreaks separately</h3>')+table([_t('Engine'),_t('Stage'),_t('Games'),'W–D–L',_t('Points')],[
            (names[r['slot']],_t('Tiebreaks') if r['stage']=='playoff' else _t('Regular'),r['games'],f"{r['wins']}–{r['draws']}–{r['losses']}",number(r['wins']+r['draws']/2)) for r in sorted(evidence['phase_rows'],key=lambda r:(order[r['slot']],r['stage']=='playoff'))])
        body+=_h('<p>These are descriptive game totals. Individual tiebreak time controls and head-to-head stage scores are listed in the KO matches above.</p>')
    if settings['format']=='self_play':body+=_h('<p>Self-play does not infer between-engine strength.</p>')
    from .report_overview import color_section,crosstable,technical_overview,conditions_changed
    body+=crosstable(standings,participants,evidence['overview'],table)+color_section(standings,evidence['overview'],table)
    body+=failures(evidence,failure_total,esc,table)
    body+=_h('<h2>Results and attempts</h2>')+table([_t('Official result'),_t('Games'),'%'],[[r['result'],r['n'],number(100*r['n']/total,2)] for r in results])+table([_t('Termination reason'),_t('Official games')],[[label(r['reason']),r['n']] for r in terminations])
    audit=evidence['overview']['attempts']
    body+=table([_t('Attempt accounting'),_t('Attempts')],[(_t('Total preserved attempts'),audit['total']),(_t('Current official attempts'),audit['official']),(_t('Archived completed attempts'),audit['archived']),(_t('Interrupted attempts'),audit['interrupted']),(_t('Running attempts'),audit['running'])])
    if t['state']=='completed' and t['note'] and not (competition and t['note'].startswith('Winner:')):
        body+='<p>'+esc(_t('Recorded tournament note')+': '+_message(t['note']))+'</p>'
    body+=table([_t('Preserved attempt mode'),_t('Attempts')],[[r['mode'],r['n']] for r in attempts])+_h('<p>{0} interrupted attempts retained separately. Diagnostics do not enter official standings; replacements retain the original attempts.</p>' ,f'{interrupted:,}')
    body+=table([_t('Scheduled game state'),_t('Materialized games')],[[label(r['state']),r['n']] for r in counts])
    if t['state']!='completed':body+=_h('<p class="muted">Future games may remain in the incremental schedule until needed; materialized rows do not represent the whole scheduled total.</p>')
    if settings['format']=='sprt':
        decision=sprt_status['status']
        labels={'continue':_t('Test continuing'),'H0':_t('Lower hypothesis selected (H0)'),'H1':_t('Upper hypothesis selected (H1)'),'invalidated':_t('Sequential decision invalidated by result replacement')}
        labels.update(inconclusive=_t('Inconclusive — game limit reached'),paused=_t('Paused — no SPRT decision'),running=_t('Test continuing'),draining=_t('Draining — no SPRT decision'),invalidated=_t('Sequential inference invalidated'))
        if sequential.get('reason','').startswith('Official results were selected for manual replacement.'):
            labels['invalidated']=_t('Sequential decision invalidated by result replacement')
        body+=_h('<h2>Sequential test</h2><p class="notice">')+esc(labels.get(decision,decision))+'</p>'
        body+=table([_t('Measurement'),_t('Value')],[[_t('Tested engine'),sprt_status['candidate']],[_t('Reference engine'),sprt_status['reference']],[_t('Statistical model'),_t('Logistic Elo')],[_t('Sampling unit'),_t('Completed opening pairs') if settings['paired'] else _t('Individual games')],[_t('Sample order'),_t('Scheduled order') if sprt_status['order']=='scheduled' else _t('Legacy completion order')]])
        body+=_h('<p>Positive Elo favors the tested engine. H0 and H1 are test hypotheses, not confidence limits or probabilities of superiority.</p>')
        if decision=='invalidated':body+=_h('<p>')+esc(sequential.get('reason',_t('Start a new test for a new sequential decision.')))+'</p>'
        else:
            body+=table([_t('Measurement'),_t('Value')],[[_t('Independent samples'),sequential.get('samples',0)],[_t('Log likelihood ratio'),number(sequential.get('llr'),4)],[_t('Lower / upper stopping boundaries'),interval([sequential.get('lower'),sequential.get('upper')])],[_t('Hypotheses, Elo'),f"{settings['sprt']['elo0']:g} / {settings['sprt']['elo1']:g}"],[_t('False positive / false negative targets'),f"{100*settings['sprt']['alpha']:g}% / {100*settings['sprt']['beta']:g}%"],[_t('Games outside frozen stopping evidence'),sprt_status['post_stop_games']]])
            body+=_h('<p>Already-running games may finish after a stopping boundary. Their descriptive results do not change the recorded sequential decision.</p>')
        body+=_h('<details><summary>Full recorded sequential evidence</summary><pre>')+esc(json.dumps(sequential,indent=2))+'</pre></details>'
    if anchor:body+=_h('<p>Pool rating reference: ')+esc(anchor['name'])+' = '+esc(number(anchor['rating']))+'. Pool ratings and their conditional uncertainty are available in the separate rating export.</p>'
    body+=_h('<h2>Test conditions</h2>')+table([_t('Setting'),_t('Value')],[(k,_t('Yes') if v is True else _t('No') if v is False else v) for k,v in condition_rows])
    if custom_rows:
        body+=_h('<h2>Custom matchups</h2>')+table([_t('First engine'),_t('Second engine'),_t('Pairs / games'),_t('Scheduled games')],custom_rows if all_engines else custom_rows[:50])
        body+=_h('<p>Opponent lists and game counts can differ. Raw points and Elo relative to sampled opposition do not constitute a common-strength ranking.</p>')
        if not all_engines and len(custom_rows)>50:body+=_h('<p>First 50 matchups shown. Select all engines for the complete schedule.</p>')
    if conditions_changed(evidence['sessions']):
        body+=_h('<p class="notice">Recorded hardware or resource limits changed between sessions. Consult the session details when interpreting pooled results and engine speeds.</p>')
    body+=technical_overview(standings,evidence,table)+environment(evidence,settings,esc,table)+engine_sections(standings,evidence,settings,time_description,esc,table)
    compact=dict(settings);compact['openings']={'count':len(settings.get('openings',[])),'preview':settings.get('openings',[])[:3]}
    body+=_h('<details><summary>Recorded settings (first three opening records)</summary><pre>')+esc(json.dumps(compact,indent=2,ensure_ascii=False))+'</pre></details>'
    body+=_h('<p class="muted">Tournament ID ')+esc(tid)+_h('<br>Full settings SHA-256 ')+settings_hash+_h('<br>Saved settings, available fingerprints, runtime evidence and moves remain in the tournament database. This is a committed snapshot.')+(_t(' Ongoing play may add newer results.') if t['state']!='completed' else '')+'</p>'
    rendered=_h('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'"><title>')+esc(t['name'])+_h(' — Engine Arena</title><style>.report-table{overflow:auto;border:1px solid #dce4e8;border-radius:8px;margin:12px 0}.report-table table{margin:0}th{white-space:nowrap}td{font-variant-numeric:tabular-nums}td:first-child,td:nth-child(2){overflow-wrap:anywhere}details{margin:18px 0}summary{cursor:pointer;font-weight:600}.report-table:focus-visible{outline:2px solid #347567;outline-offset:2px}@media print{.report-table{overflow:visible;border:0}table{font-size:9px!important}td,th{padding:5px 3px!important}}body{font:14px/1.5 Segoe UI,Arial,sans-serif;color:#152636;background:#fff;max-width:1400px;margin:36px auto;padding:0 24px}h1{font-size:30px}h2{font-size:19px;margin-top:30px}.muted{color:#536575;font-size:12px}.metrics{display:flex;flex-wrap:wrap;gap:28px;padding:20px;background:#eef5f3}.metrics b{font-size:25px}.metrics small{display:block;font-size:12px;font-weight:400}table{border-collapse:collapse;width:100%;margin:12px 0;font-size:12px}td,th{text-align:left;border-bottom:1px solid #dce4e8;padding:9px 7px}th{background:#eef2f5}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f6f8;padding:16px;font-size:11px}.notice{border-left:4px solid #567f71;padding:12px}@media print{body{margin:0;padding:0}thead{display:table-header-group}tr{break-inside:avoid}details{display:none}}</style></head><body>')+body+'</body></html>'
    from .report_overview import decorate
    rendered=decorate(rendered)
    report_cache.write(path,cache_key,rendered)
    return rendered
