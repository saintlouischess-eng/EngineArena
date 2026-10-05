from .i18n import t as _t,h as _h
"""Readable sections shared by the HTML preview and its plain-text export."""
from datetime import datetime,timezone
import time
from .report_evidence import option_rows,observation_rows


def utc(value):return datetime.fromtimestamp(value,timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC') if value is not None else _t('Not recorded')


def duration(value):
    if value is None:return _t('Not recorded')
    seconds=max(0,round(value));hours,seconds=divmod(seconds,3600);minutes,seconds=divmod(seconds,60)
    return _t('{0} h {1} m {2} s' ,f'{hours}',f'{minutes}',f'{seconds}')


def label(value):return _t(str(value).replace('_',' ').capitalize())


def failures(evidence,total,esc,table):
    if not total:return _h('<p>No timeout, crash, hang, illegal-move, startup, readiness or protocol forfeits in the current official results.</p>')
    body=_h('<h2>Failed games included in official results</h2><p class="notice">')+str(total)+_h(' failure forfeits count in the scores and statistics. They can affect KO advancement. Diagnostic replays do not replace them; an official replacement must handle any dependent rounds.</p>')
    for f in evidence['failures']:
        loser=f['black_name'] if f['result']=='1-0' else f['white_name'] if f['result']=='0-1' else _t('Not identifiable from result')
        stage=_t('Round {0} · ' ,f"{f['round'] + 1}")+(_t('tiebreak {0}' ,f"{f['stage']}") if f['stage'] else _t('regular game'))
        body+=_h('<h3>Game ')+str(f['number']+1)+' · '+esc(label(f['reason']))+'</h3>'
        body+=table([_t('Failure detail'),_t('Value')],[(_t('Recorded loser'),loser),(_t('Match'),f['white_name']+_t(' (White) vs ')+f['black_name']+_t(' (Black)')),
            (_t('Stage / result'),stage+' · '+f['result']),(_t('Reason'),f['detail'] or label(f['reason'])),
            *([(_t('Engine diagnostic'),'; '.join(f['errors']))] if f['errors'] else []),(_t('Game ID'),f['id'])])
    if total>len(evidence['failures']):body+=_h('<p>First {0} of {1} failed games shown; Games &amp; attempt history contains the full list.</p>' ,f"{len(evidence['failures'])}",f'{total}')
    return body


def environment(evidence,settings,esc,table):
    timing=evidence['timing'];start=timing['first_start'];end=time.time() if timing['running'] else timing['last_end']
    rows=[(_t('First game attempt started'),utc(start)),(_t('Last game attempt ended'),utc(timing['last_end'])),
        (_t('Elapsed since first attempt'),duration(end-start if start is not None and end is not None else None)),
        (_t('Current simultaneous-game limit'),settings['concurrency']),(_t('Peak concurrent game attempts'),evidence['peaks'].get('Games',0)),
        (_t('CPU thread budget'),settings.get('cpu_budget') or _t('Automatic; resolved per recorded session')),
        (_t('Memory budget (MB)'),settings.get('memory_budget_mb') or _t('Automatic; resolved per recorded session')),
        (_t('GPU group limits'),'; '.join(_t('{0}: {1} engine instances' ,f'{k}',f'{v}')+(_t(' (implicit legacy default)') if k in evidence['implicit_gpu_groups'] else '') for k,v in evidence['gpu_limits'].items()) or _t('No shared GPU group configured'))]
    rows.extend((_t('Peak {0} reservations' ,f'{group}'),evidence['peaks'].get(group,0)) for group in evidence['gpu_limits'])
    rows.extend((_t('Observed peak ')+group,value) for group,value in evidence['process_peaks'].items())
    body=_h('<h2>Test system and resources</h2>')+table([_t('Measurement'),_t('Value')],rows)
    if evidence.get('concurrency_changes'):
        body+=_h('<h3>Concurrency changes</h3><p>Limits changed during this tournament. Lower limits let existing games finish; CPU, memory and GPU budgets still apply. Performance samples can span different loads.</p>')
        body+=table([_t('Changed at (UTC)'),_t('Previous limit'),_t('New limit'),_t('Active games at change')],
            [(utc(c['created']),c['body']['before'],c['body']['after'],c['body']['active']) for c in evidence['concurrency_changes']])
    body+=_h('<p>Activity includes original, retry, diagnostic and replacement attempts, including invalidated rounds. Attempt intervals bound reservations; recorded process intervals measure engine overlap where available. Interrupted intervals may end at recovery. Elapsed time includes pauses and downtime.</p>')
    body+=_h('<p>Search threads are engine settings, not dedicated physical cores. CPU affinity identifies logical processors; unrestricted engines are scheduled by the operating system.</p>')
    if evidence['implicit_gpu_groups']:body+=_h('<p class="notice">No explicit slot limit was saved for ')+esc(', '.join(evidence['implicit_gpu_groups']))+'. The legacy fallback is two engine instances per group. Set an explicit limit, such as gpu0:1, when a GPU must run one engine at a time.</p>'
    if not evidence['sessions']:body+=_h('<p class="notice">Historical hardware snapshot not recorded. Current computer hardware is not substituted for the machine used during this tournament. Saved engine logs may identify a GPU in the engine details below.</p>')
    for index,session in enumerate(evidence['sessions'],1):
        data=session['body'];h=data.get('hardware',{});r=data.get('resources',{})
        body+=_h('<h3>Run session {0}</h3>' ,f'{index}')+table([_t('Recorded condition'),_t('Value')],[
            (_t('Session started'),utc(session['started'])),(_t('Session state'),label(session['state'])),(_t('Last recorded heartbeat'),utc(session['last_seen'])),
            (_t('Session ended'),utc(session['ended']) if session['ended'] else _t('Not recorded; running or interrupted')),
            (_t('Engine Arena version'),h.get('app_version',_t('Not recorded'))),(_t('Operating system'),h.get('os',_t('Not recorded'))),
            ('CPU',h.get('cpu',_t('Not recorded'))),(_t('Physical cores / logical processors'),f"{h.get('physical_cores','N/A')} / {h.get('logical_processors','N/A')}"),
            (_t('Installed RAM (GiB)'),f"{h['ram_gib']:.1f}" if h.get('ram_gib') is not None else _t('Not recorded')),
            (_t('Effective CPU thread budget'),r.get('cpu_threads',_t('Not recorded'))),(_t('Effective memory budget (MB)'),r.get('memory_mb',_t('Not recorded'))),
            (_t('Effective GPU limits'),'; '.join(f'{k}: {v}' for k,v in r.get('gpu_limits',{}).items()) or _t('None')),
            *([(_t('Hardware reading'),h['unavailable'])] if h.get('unavailable') else [])])
        for gpu in h.get('gpus',[]):
            body+=table([_t('GPU ')+str(gpu['index']),_t('Value')],[(_t('Model'),gpu['name']),(_t('VRAM (GiB)'),f"{gpu['vram_gib']:.1f}" if gpu.get('vram_gib') is not None else _t('Unavailable')),(_t('Driver'),gpu['driver'])])
        if h.get('gpu_note'):body+=_h('<p>')+esc(h['gpu_note'])+'</p>'
        if data.get('shared_scheduler_history'):
            body+=_h('<h3>Shared tournament scheduling</h3><p>This tournament shared the computer with other eligible tournaments. Global budgets and each tournament’s own limits both applied. Priority controls resource-time sharing; allocations and performance may vary as other games start and finish.</p>')
            body+=table([_t('Changed at (UTC)'),_t('CPU threads'),_t('Memory (MB)'),_t('Total simultaneous games'),_t('GPU group limits'),_t('Priority')],
                [(utc(x['at']),x['limits']['cpu_budget'],x['limits']['memory_budget_mb'],x['limits']['concurrency'],
                  '; '.join(f'{k}: {v}' for k,v in x['limits']['gpu_limits'].items()) or _t('Unlisted GPU groups: one process'),
                  {1:_t('Low'),2:_t('Normal'),4:_t('High')}.get(x['priority'],x['priority'])) for x in data['shared_scheduler_history']])
    body+=_h('<section data-report-performance><h2>Observed system performance</h2><p>Optional sampled system-wide readings, not per-engine measurements. Averages are arithmetic means of available samples; peaks are observed samples, not guaranteed instantaneous maxima. Sensor fields depend on enabled hardware monitoring. Missing values are not zero.</p>')
    any_samples=False
    for index,session in enumerate(evidence['sessions'],1):
        data=session['body'];samples=data.get('samples',{})
        if not samples:continue
        any_samples=True
        body+=_h('<h3>Run session {0} samples</h3><p>' ,f'{index}')+esc(utc(data.get('first_sample'))+_t(' to ')+utc(data.get('last_sample')))+'</p>'
        names={'cpu_percent':_t('CPU utilization (%)'),'cpu_temperature':_t('CPU temperature (°C)'),'cpu_fastest_clock':_t('Fastest core (GHz)'),
            'ram_used':_t('System RAM used (GiB)'),'ram_percent':_t('System RAM used (%)'),'gpu_percent':_t('utilization (%)'),
            'gpu_memory':_t('VRAM used (GiB)'),'gpu_temperature':_t('temperature (°C)'),'gpu_clock':_t('clock (MHz)'),'gpu_power':_t('power (W)')}
        def name(k):
            if k.startswith('GPU '):prefix,_,metric=k.rpartition(' ');return prefix+' '+names.get(metric,metric)
            return names.get(k,k)
        body+=table([_t('Sampled measurement'),_t('Samples'),_t('Average'),_t('Minimum'),_t('Maximum')],[
            (name(k),v['count'],f"{v['sum']/v['count']:.2f}",f"{v['min']:.2f}",f"{v['max']:.2f}") for k,v in samples.items() if v['count']])
    if not any_samples:body+=_h('<p>No performance samples were recorded for this tournament.</p>')
    return body+'</section>'


def engine_sections(standings,evidence,settings,time_description,esc,table):
    body=_h('<h2>Displayed engine configurations</h2><p>Saved configuration and observed runtime evidence are distinguished. Network file fingerprints are captured after the engine announces loading; unavailable historical hashes are not reconstructed from today’s files.</p>')
    if 'technical' in evidence:
        body+=_h('<p data-report-technical>Technical readouts use legal engine moves from current completed official attempts, including moves before a failure. Book moves, running games, failed searches without a committed move, diagnostics, superseded attempts and invalidated rounds are excluded. Different time controls, regular/tiebreak phases, recorded hardware sessions and observed engine configurations are kept separate. Self-play contributes two engine appearances per game.</p>')
        body+=_h('<p data-report-technical>Coverage is shown for every metric; missing readings are not zero. Averages are arithmetic means of available final-per-move values. Rate summaries divide summed reported nodes by summed time over the same covered moves. Engine-reported time and GUI-measured thinking time are separate; neither includes startup or saving. Pondering can contribute work outside measured turn time. Hash occupancy converts UCI permille to percent. Nodes, depth, NPS and tablebase hits use engine-specific definitions, may include reused search work, and are not directly comparable between neural and traditional engines or a measure of playing strength. CPU/GPU sensor samples describe the whole system/session; per-engine CPU load, RAM, VRAM, power and temperature were not recorded.</p>')
    for item in standings:
        p=item['profile'];slot=item['rank']['slot'];entry=evidence['engines'][slot]
        body+='<details data-report-details><summary>'+esc(p['name'])+'</summary>'
        body+=table([_t('Engine setting'),_t('Value')],[
            *((_t(k),v) for k,v in option_rows(p)),(_t('Regular time control'),time_description(p.get('time_control') or settings['time_control'])),
            (_t('Executable SHA-256'),p.get('sha256') or p.get('fingerprints',{}).get('executable',{}).get('sha256') or _t('Not recorded')),
            *((_t(k),v) for k,v in observation_rows(entry))])
        book=p.get('move_book')
        if book:
            body+=table([_t('Engine move book'),_t('Value')],[(_t('File'),book['name']),('SHA-256',book['id']),(_t('Move selection'),_t({'weighted':'Weighted by book frequency','uniform':'Equal chance per move','best':'Highest book weight'}[book['policy']])),(_t('Maximum plies from initial position (0 = unlimited)'),book['max_plies']),(_t('Enabled for this tournament'),_t('Yes') if settings.get('use_engine_books',True) else _t('No'))])
            if settings.get('use_engine_books',True):body+=_h('<p>Each profile chooses moves on its own turns; after the first miss or depth limit it searches for the rest of the game. Results measure the engine and book combination. Book moves earn increment without search time or move overhead.</p>')
        for network in p.get('fingerprints',{}).get('networks',[]):
            from .report_evidence import filename
            body+=table([_t('Configured network fingerprint'),_t('Value')],[(_t('File'),filename(network['path'])),('SHA-256',network['sha256'])])
        if 'technical' in evidence:
            from .engine_readout import section
            body+=section(evidence['technical'][slot],evidence,esc,table,time_description)
        body+='</details>'
    return body
