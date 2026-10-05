"""Knockout match lengths and replayable playoff controls, without game expansion."""
from .models import TimeControl, scheduled_pairs

SAMPLE_NOTE=('KO game statistics include regular matches and tiebreaks. Each engine is measured against its own sampled opposition, not a common rating reference. '
    'Opponents and sample sizes depend on prior results; fixed-sample CI and LOS are descriptive approximations here, not calibrated confidence in overall superiority or sequential stopping rules.')


def round_title(settings,n,round_no):
    if settings['format']!='knockout':return f'KO round {round_no}'
    remaining=len(round_matches(n))-round_no
    return {0:'Final',1:'Semifinals',2:'Quarterfinals'}.get(remaining,f'Round of {2**(remaining+1)}')+f' (KO round {round_no})'

def sample_note(s):return SAMPLE_NOTE if s['format'] in ('knockout','double_elimination') else ''


def round_matches(n):
    """Seeded bracket counts, including first-round byes, in O(log n) space."""
    if n < 2:return []
    size=1 << (n-1).bit_length()
    counts=[n-size//2]
    size//=4
    while size:
        counts.append(size);size//=2
    return counts


def round_cycles(s,round_no):
    games=s.get('ko_round_games') if s['format']=='knockout' else None
    return games[round_no]//(2 if s['paired'] else 1) if games else s['cycles']


def validate(s,n):
    games=s.get('ko_round_games',[])
    if not isinstance(games,list):raise ValueError('KO round game counts must be a list')
    if games:
        if s['format']!='knockout':raise ValueError('Per-round match lengths require Knockout (KO — single elimination)')
        if len(games)!=len(round_matches(n)):raise ValueError('Enter a game count for every KO round')
        for value in games:
            if not isinstance(value,int) or isinstance(value,bool) or value<1:raise ValueError('Games per KO match must be positive whole numbers')
            if s['paired'] and value%2:raise ValueError('KO matches need an even number of games when openings are played with both colors')
    controls=s.get('playoff_controls',[])
    if not isinstance(controls,list):raise ValueError('Playoff controls must be a list')
    for control in controls:
        if not isinstance(control,dict) or not control:raise ValueError('Each playoff stage needs a time control')
        TimeControl.parse(control)


def base_pairs(n,s):
    if s['format']=='custom':
        from .custom_matchups import validate as validate_custom
        return validate_custom(n,s.get('custom_matchups'))[1]
    base=scheduled_pairs(n,s['format'],s['cycles'],s['candidates'],s['rounds'],s.get('ladder_distance',1))
    validate(s,n)
    if s['format']=='knockout' and s.get('ko_round_games'):
        return sum(matches*round_cycles(s,r) for r,matches in enumerate(round_matches(n)))
    return base


def playoff_control(s,stage):
    """Zero-based stage; the final configured control repeats indefinitely."""
    controls=s.get('playoff_controls',[])
    return controls[min(stage,len(controls)-1)] if controls else None


def game_control(s,profile,opening):
    return opening.get('playoff_time_control') or profile.get('time_control') or s['time_control']


def game_label(s,round_no,opening):
    if s['format'] not in ('knockout','double_elimination'):return ''
    stage=opening.get('playoff_stage')
    return f'KO round {round_no+1} · '+(f'Tiebreak {stage}' if stage else 'Tiebreak' if opening.get('competition_stage')=='playoff' else 'Regular match')


def format_name(value):
    return {'custom':'Custom matchups','knockout':'Knockout (KO — single elimination)','double_elimination':'Knockout (KO — double elimination)'}.get(value,value.replace('_',' '))
