"""Small report summaries; all queries stay independent of move-history size."""
from collections import defaultdict
from .i18n import t as _t, h as _h, number


def collect(view, tid, slots=None):
    import json
    selected=set(slots) if slots is not None else None
    colors = defaultdict(lambda: {'white': [0,0,0], 'black': [0,0,0]})
    matchups = []
    # A first-50 report must not allocate a participant-squared matrix.
    scope='' if selected is None else ' AND (g.white IN (SELECT value FROM json_each(?)) OR g.black IN (SELECT value FROM json_each(?)))'
    args=(tid,) if selected is None else (tid,json.dumps(sorted(selected)),json.dumps(sorted(selected)))
    matrix=selected is None or len(selected)<=20
    for row in view.db.execute('''SELECT g.white,g.black,a.result,count(*) n
            FROM games g JOIN attempts a ON a.id=g.official
            WHERE g.tid=? AND g.invalid=0'''+scope+' GROUP BY g.white,g.black,a.result',args):
        if matrix:matchups.append(dict(row))
        outcome = {'1-0':0,'1/2-1/2':1,'0-1':2}[row['result']]
        if selected is None or row['white'] in selected:colors[row['white']]['white'][outcome] += row['n']
        if selected is None or row['black'] in selected:colors[row['black']]['black'][2-outcome] += row['n']
    attempts = view.one('''SELECT count(*) total,
        coalesce(sum(a.id=g.official AND g.invalid=0),0) official,
        coalesce(sum(a.ended IS NULL),0) running,
        coalesce(sum(a.result='*'),0) interrupted,
        coalesce(sum(a.ended IS NOT NULL AND a.result IN ('1-0','0-1','1/2-1/2')
            AND (g.official IS NULL OR a.id<>g.official OR g.invalid<>0)),0) archived
        FROM attempts a JOIN games g ON g.id=a.gid WHERE g.tid=?''', (tid,))
    return {'colors':dict(colors),'matchups':matchups,'attempts':attempts}


def color_section(standings, data, table):
    rows=[]
    for item in standings:
        slot=item['rank']['slot'];profile=item['profile']
        for side in ('white','black'):
            w,d,l=data['colors'].get(slot,{}).get(side,[0,0,0]);n=w+d+l
            rows.append([profile['name'],_t('White') if side=='white' else _t('Black'),n,
                         '–'.join(number(v,0) for v in (w,d,l)),
                         number(100*(w+d/2)/n,2) if n else _t('Unavailable')])
    return _h('<h2>Results by color</h2><p>Each row uses only that engine’s games with the indicated color. These subsets are descriptive and do not form complete opening pairs.</p>')+table(
        [_t('Engine'),_t('Color'),_t('Games'),'W–D–L',_t('Score %')],rows)


def crosstable(standings, participants, data, table):
    # A wide printed matrix has a readability bound, not a participant limit.
    if participants>20 or len(standings)<participants:
        return _h('<p>The full head-to-head crosstable is available in Results &amp; exports.</p>')
    scores=defaultdict(float);games=defaultdict(int)
    for r in data['matchups']:
        score={'1-0':1,'1/2-1/2':.5,'0-1':0}[r['result']];a,b=r['white'],r['black'];n=r['n']
        scores[a,b]+=score*n;games[a,b]+=n
        if a!=b:scores[b,a]+=(1-score)*n;games[b,a]+=n
    slots=[item['rank']['slot'] for item in standings]
    rows=[]
    for i,item in enumerate(standings,1):
        a=item['rank']['slot'];cells=[]
        for b in slots:
            cells.append(number(scores[a,b],1)+' / '+number(games[a,b],0) if games[a,b] else '—')
        rows.append([str(i)+'. '+item['profile']['name'],*cells])
    return _h('<h2>Head-to-head crosstable</h2><p>Cells show points / games from the row engine’s perspective. Column numbers follow the engine order in this table. Self-play is shown from White’s perspective.</p>')+table([_t('Engine'),*[str(i) for i in range(1,len(slots)+1)]],rows).replace('<table>','<table data-report-crosstable>',1)


def technical_overview(standings,evidence,table):
    if 'technical' not in evidence:return ''
    rows=[]
    for item in standings:
        groups=evidence['technical'][item['rank']['slot']]
        moves=sum(b['moves'] for b in groups)
        def avg(metric):
            values=[b['metrics'][metric] for b in groups if metric in b['metrics']]
            count=sum(v['count'] for v in values)
            return number(sum(v['sum'] for v in values)/count,2) if count else _t('Not reported')
        nodes=sum(b['timed_nodes'] for b in groups);seconds=sum(b['timed_seconds'] for b in groups)
        covered=sum(b['timed_moves'] for b in groups)
        rows.append([item['profile']['name'],moves,avg('depth'),avg('elapsed'),
            number(nodes/seconds,0) if seconds else _t('Unavailable'),
            number(100*covered/moves,2)+'%' if moves else _t('Unavailable')])
    return _h('<section data-report-technical><h2>Engine technical overview</h2><p>All recorded sessions are pooled in this overview. Averages are weighted by moves with data; node rates divide summed nodes by summed measured time over the same moves. Rate coverage is the percentage of legal engine moves included. Expand each engine below for separate session, control and configuration measurements. Search speed and depth are not measures of playing strength.</p>')+table(
        [_t('Engine'),_t('Legal engine moves sampled'),_t('Average depth'),_t('Average thinking time (s)'),_t('Nodes / measured search second'),_t('Rate coverage')],rows).replace('<table>','<table data-report-tech-overview>',1)+'</section>'


def conditions_changed(sessions):
    import json
    signatures=set()
    for session in sessions:
        body=session['body'];h=body.get('hardware',{});r=body.get('resources',{})
        signatures.add(json.dumps([h.get('cpu'),h.get('physical_cores'),h.get('logical_processors'),h.get('gpus'),
                                   r.get('cpu_threads'),r.get('game_limit'),r.get('gpu_limits')],sort_keys=True))
    return len(signatures)>1


def decorate(document):
    """Static navigation and printable, expandable engine details; no scripts."""
    import html
    import re
    links=[]
    def heading(match):
        anchor='report-section-'+str(len(links)+1)
        performance=' data-report-performance' if html.unescape(match[1])==_t('Observed system performance') else ''
        links.append('<a'+performance+' href="#'+anchor+'">'+match[1]+'</a>')
        return '<h2 id="'+anchor+'">'+match[1]+'</h2>'
    document=re.sub(r'<h2>(.*?)</h2>',heading,document)
    navigation='<nav class="report-nav" aria-label="'+html.escape(_t('Report sections'),quote=True)+'">'+''.join(links)+'</nav>'
    document=document.replace('<div class="metrics">',navigation+'<div class="metrics">',1)
    style='''<style>
      .report-nav{display:flex;flex-wrap:wrap;gap:7px 15px;margin:20px 0;font-size:12px}
      .report-nav a{color:#236b59;text-decoration:none;border-bottom:1px solid #a5c9bc}
      h2{scroll-margin-top:20px;border-bottom:2px solid #dce9e4;padding-bottom:7px}
      details[data-report-details]{border:1px solid #c9dbd3;border-radius:8px;padding:12px 16px}
      details[data-report-details]>summary{color:#205947;font-size:16px}
      details[data-report-details][open]>summary{margin-bottom:15px}
      @media print{
        .report-nav{display:none}
        details[data-report-details]{display:block!important;border:0;padding:0}
        details[data-report-details]::details-content{content-visibility:visible!important;height:auto!important}
        details[data-report-details]>:not(summary){display:block!important}
        h2,h3,h4,summary{break-after:avoid}
      }
    </style>'''
    return document.replace('</head>',style+'</head>',1)
