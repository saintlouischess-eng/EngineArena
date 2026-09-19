"""Concise standalone HTML report from one committed read-only snapshot."""
from datetime import datetime,timezone
import hashlib
import html
import json
from pathlib import Path
import sqlite3
from .stats import summarize
from .rankings import rows as ranked_rows
from .resources import option


class Snapshot:
    def __init__(self,db):self.db=db
    def rows(self,sql,args=()):return [dict(r) for r in self.db.execute(sql,args)]
    def one(self,sql,args=()):
        row=self.db.execute(sql,args).fetchone();return dict(row) if row else None


def number(value):
    if value is None:return '—'
    if value=='+infinity':return '+∞'
    if value=='-infinity':return '−∞'
    return f'{value:,.1f}' if isinstance(value,(int,float)) else str(value)


def time_description(control):
    kind=control.get('kind','fischer')
    if kind=='nodes':return f"{control.get('nodes',10000):,} nodes per move; no chess clock"
    if kind=='depth':return f"Depth {control.get('depth',12)}; no chess clock"
    if kind=='movetime':return f"{control.get('seconds',180)} seconds per move"
    if kind=='staged':
        stages=[]
        for stage in control.get('stages',[]):
            moves=stage.get('moves',0)
            text=f"{moves} moves in" if moves else 'Rest of game in'
            text+=f" {stage.get('seconds',0):g} seconds"
            if stage.get('increment',0):text+=f" + {stage['increment']:g} seconds per move"
            stages.append(text)
        return '; then '.join(stages)+('; repeat final stage' if control.get('repeat') else '')
    text=f"{control.get('seconds',180)} seconds"
    if kind=='fischer':text+=f" + {control.get('increment',2)} seconds increment"
    if kind in ('delay','bronstein'):text+=f"; {kind} {control.get('delay',0)} seconds"
    return text


def render(path,tid,confidence=95):
    from .stats import confidence_level
    confidence=confidence_level(confidence)
    db=sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True,timeout=30);db.row_factory=sqlite3.Row;view=Snapshot(db)
    try:
        db.execute('BEGIN');t=view.one('SELECT * FROM tournaments WHERE id=?',(tid,))
        if not t:raise ValueError('Tournament not found')
        settings=json.loads(t['settings']);participants=view.one('SELECT count(*) n FROM participants WHERE tid=?',(tid,))['n']
        revision=view.one('SELECT revision FROM report_revisions WHERE tid=?',(tid,));revision=revision['revision'] if revision else 0
        ranked=ranked_rows(view,tid,settings,0,50);standings=[]
        for rank in ranked:
            profile=json.loads(view.one('SELECT profile FROM participants WHERE tid=? AND slot=?',(tid,rank['slot']))['profile'])
            agg=view.one('SELECT * FROM aggregates WHERE tid=? AND a=? AND b=-1',(tid,rank['slot']))
            summary=summarize(agg['w'],agg['d'],agg['l'],[agg[f'p{i}'] for i in range(5)] if settings['paired'] else None,confidence)
            if settings['format']=='self_play':summary.update(elo=None,ci=None,ci_conservative=None,ci95=None,ci95_conservative=None,los=None)
            standings.append({'rank':rank,'profile':profile,'summary':summary})
        source='FROM games g JOIN attempts a ON a.id=g.official WHERE g.tid=? AND g.invalid=0'
        results=view.rows('SELECT a.result,count(*) n '+source+' GROUP BY a.result',(tid,));terminations=view.rows('SELECT a.reason,count(*) n '+source+' GROUP BY a.reason ORDER BY n DESC,a.reason',(tid,))
        attempts=view.rows('SELECT a.mode,count(*) n FROM attempts a JOIN games g ON g.id=a.gid WHERE g.tid=? GROUP BY a.mode',(tid,))
        interrupted=view.one("SELECT count(*) n FROM attempts a JOIN games g ON g.id=a.gid WHERE g.tid=? AND a.result='*'",(tid,))['n']
        counts=view.rows('SELECT state,count(*) n FROM games WHERE tid=? AND invalid=0 GROUP BY state',(tid,))
        complete_pairs=view.one('SELECT coalesce(sum(p0+p1+p2+p3+p4),0) n FROM aggregates WHERE tid=? AND b=-1',(tid,))['n']//(1 if settings['format']=='self_play' else 2) if settings['paired'] else None
        seq=view.one('SELECT body FROM sequential_state WHERE tid=?',(tid,));anchor=view.one("SELECT a.slot,a.rating,json_extract(p.profile,'$.name') name FROM rating_anchors a JOIN participants p ON p.tid=a.tid AND p.slot=a.slot WHERE a.tid=?",(tid,))
    finally:db.close()
    esc=lambda v:html.escape(str(v),quote=True)
    total=sum(r['n'] for r in results);timestamp=datetime.now(timezone.utc).isoformat(timespec='seconds');settings_hash=hashlib.sha256(t['settings'].encode()).hexdigest()
    def table(headers,rows):return '<div class="report-table" tabindex="0" role="region" aria-label="'+esc(' / '.join(headers[:2]))+'"><table><thead><tr>'+''.join('<th scope="col">'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
    def interval(value):return ' to '.join(number(v) for v in value) if value else 'Unavailable'
    summary=f'<div class="metrics"><b>{total:,}<small>official games / {t["total"]:,} scheduled</small></b><b>{participants:,}<small>participants</small></b><b>{complete_pairs if complete_pairs is not None else "Unpaired"}<small>completed opening pairs</small></b><b>{esc(t["state"])}<small>tournament state</small></b></div>'
    condition_rows=[('Format',settings['format']),('Time control',time_description(settings['time_control'])),('Concurrency',settings['concurrency']),('Ponder',settings['ponder']),('Paired openings',settings['paired']),('Opening positions',len(settings.get('openings',[]))),('Opening order / seed',f"{settings['opening_order']} / {settings['seed']}"),('Variant','Chess960' if settings['chess960'] else 'Standard chess'),('Tiebreaks',', '.join(settings['tiebreaks'])),('Automatic retry limit',settings['retry_limit']),('Watchdogs, seconds',f"Startup {settings['startup_timeout']}; readiness {settings['readiness_timeout']}; search {settings['hang_timeout']}; stop {settings['stop_timeout']}")]
    rows=[];profiles=[]
    for i,item in enumerate(standings,1):
        rank,p,s=item['rank'],item['profile'],item['summary'];rows.append([i,p['name'],f"{s['wins']}–{s['draws']}–{s['losses']}",number(rank['points']),number(s['score_pct']),number(s['draw_pct']),number(s['elo']),interval(s['ci']),interval(s['ci_conservative']),number(s['los'])])
        profiles.append([p['name'],p.get('identity',{}).get('name',p.get('name','')),option(p,'Threads',1),option(p,'Hash',1024),time_description(p.get('time_control') or settings['time_control'])])
    body=f'<h1>{esc(t["name"])}</h1><p class="muted">Engine Arena tournament report · {esc(timestamp)} · committed result revision {revision}</p>'+summary
    if t['dependency'] or t['note']:body+='<p class="notice">'+esc(t['dependency'] or t['note'])+'</p>'
    body+='<h2>Standings</h2><p>First '+str(len(rows))+' of '+str(participants)+' participants in tournament order. CSV/JSON exports contain the full standings.</p>'
    body+=table(['#','Engine profile','W–D–L','Points','Score %','Draw %','Δ Elo',f'Normal {confidence:g}% CI',f'Conservative {confidence:g}% CI','LOS %'],rows)
    body+='<p class="muted">Logistic Elo relative to sampled opposition. '+('Paired estimates use only complete opening pairs.' if settings['paired'] else 'Unpaired estimates use individual games.')+' Normal intervals and LOS are approximate; conservative intervals use Hoeffding bounds. Both require independent fixed samples and are not sequential stopping rules. Byes contribute points only. Self-play does not infer between-engine strength.</p>'
    body+='<h2>Results and attempts</h2>'+table(['Official result','Games'],[[r['result'],r['n']] for r in results])+table(['Termination reason','Official games'],[[r['reason'],r['n']] for r in terminations])
    body+=table(['Preserved attempt mode','Attempts'],[[r['mode'],r['n']] for r in attempts])+f'<p>{interrupted:,} interrupted attempts retained separately. Diagnostics do not enter official standings; replacements retain the original attempts.</p>'
    body+=table(['Scheduled game state','Materialized games'],[[r['state'],r['n']] for r in counts])+'<p class="muted">Future games may remain in the incremental schedule until needed; materialized rows do not represent the whole scheduled total.</p>'
    if seq:
        evidence=json.loads(seq['body']);decision=evidence.get('decision','continue')
        labels={'continue':'Test continuing','H0':'Lower hypothesis selected (H0)','H1':'Upper hypothesis selected (H1)','invalidated':'Sequential decision invalidated by result replacement'}
        body+='<h2>Sequential test</h2><p class="notice">'+esc(labels.get(decision,decision))+'</p>'
        if decision=='invalidated':body+='<p>'+esc(evidence.get('reason','Start a new test for a new sequential decision.'))+'</p>'
        else:
            body+=table(['Measurement','Value'],[['Independent samples',evidence.get('samples',0)],['Log likelihood ratio',number(evidence.get('llr'))],['Lower / upper stopping boundaries',interval([evidence.get('lower'),evidence.get('upper')])],['Hypotheses, Elo',f"{settings['sprt']['elo0']:g} / {settings['sprt']['elo1']:g}"],['False positive / false negative targets',f"{100*settings['sprt']['alpha']:g}% / {100*settings['sprt']['beta']:g}%"]])
            body+='<p>Already-running games may finish after a stopping boundary. Their descriptive results do not change the recorded sequential decision.</p>'
        body+='<details><summary>Full recorded sequential evidence</summary><pre>'+esc(json.dumps(evidence,indent=2))+'</pre></details>'
    if anchor:body+='<p>Pool rating reference: '+esc(anchor['name'])+' = '+esc(number(anchor['rating']))+'. Pool ratings and their conditional uncertainty are available in the separate rating export.</p>'
    body+='<h2>Test conditions</h2>'+table(['Setting','Value'],condition_rows)+'<h2>Displayed engine configurations</h2>'+table(['Profile','Reported identity','Threads','Hash MB','Time control'],profiles)
    compact=dict(settings);compact['openings']={'count':len(settings.get('openings',[])),'preview':settings.get('openings',[])[:3]}
    body+='<details><summary>Recorded settings (first three opening records)</summary><pre>'+esc(json.dumps(compact,indent=2,ensure_ascii=False))+'</pre></details>'
    body+='<p class="muted">Tournament ID '+esc(tid)+'<br>Full settings SHA-256 '+settings_hash+'<br>Exact settings, engine fingerprints and all moves remain in the saved tournament and annotated PGNs. This report is a snapshot; ongoing play may add newer results.</p>'
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'"><title>'+esc(t['name'])+' — Engine Arena</title><style>.report-table{overflow:auto;border:1px solid #dce4e8;border-radius:8px;margin:12px 0}.report-table table{margin:0}th{white-space:nowrap}td{font-variant-numeric:tabular-nums}td:first-child,td:nth-child(2){overflow-wrap:anywhere}details{margin:18px 0}summary{cursor:pointer;font-weight:600}.report-table:focus-visible{outline:2px solid #347567;outline-offset:2px}@media print{.report-table{overflow:visible;border:0}table{font-size:9px!important}td,th{padding:5px 3px!important}}body{font:14px/1.5 Segoe UI,Arial,sans-serif;color:#152636;background:#fff;max-width:1400px;margin:36px auto;padding:0 24px}h1{font-size:30px}h2{font-size:19px;margin-top:30px}.muted{color:#536575;font-size:12px}.metrics{display:flex;flex-wrap:wrap;gap:28px;padding:20px;background:#eef5f3}.metrics b{font-size:25px}.metrics small{display:block;font-size:12px;font-weight:400}table{border-collapse:collapse;width:100%;margin:12px 0;font-size:12px}td,th{text-align:left;border-bottom:1px solid #dce4e8;padding:9px 7px}th{background:#eef2f5}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f6f8;padding:16px;font-size:11px}.notice{border-left:4px solid #567f71;padding:12px}@media print{body{margin:0;padding:0}thead{display:table-header-group}tr{break-inside:avoid}details{display:none}}</style></head><body>'+body+'</body></html>'
