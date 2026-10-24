"""Validated presentation choices, independent of saved games and recovery."""
from copy import deepcopy

REQUIRED=('Event','Site','Date','Round','White','Black','Result')
STRUCTURAL=('SetUp','FEN','Variant','OpeningHistory')
GROUPS=(
    ('Game and result',('TimeControl','Termination','TerminationDetails','PlyCount','UTCDate','UTCTime')),
    ('Opening information',('ECO','Opening','Variation','OpeningBook','BookPlyCount','OpeningPosition','OpeningSeed','OpeningPolicy','OpeningAssignment',*(side+key for side in ('White','Black') for key in ('Book','BookSHA256','BookPolicy','BookMaxPly')))),
    ('Engine identities and resources',('WhiteEngine','BlackEngine','WhiteThreads','BlackThreads','WhiteHashMB','BlackHashMB','Ponder')),
    ('Independent engine controls',('WhiteTimeControl','BlackTimeControl','WhiteSearchControl','BlackSearchControl')),
    ('Networks and GPU',tuple(side+key for side in ('White','Black') for key in ('Network','NetworkSHA256','Backend','GPU','GPUGroup','NNCachePositions'))),
    ('Game and attempt tracking',('TournamentId','GameId','GameNumber','AttemptId','Attempt','AttemptMode','OpeningPair','OpeningLeg','CompetitionStage','PlayoffStage','EventId','EventStage','LeagueSeason')),
    ('Rating configuration references',('WhiteRatingConfiguration','BlackRatingConfiguration','WhiteProfileId','BlackProfileId')),
    ('Complete encoded settings',('SettingsEncoding','WhiteSettings','BlackSettings','TournamentSettings')),
)
HEADERS=tuple(key for _,keys in GROUPS for key in keys)
ANNOTATIONS=('eval','depth','elapsed','clock','nodes','nps','seldepth')
CLEAN=('TimeControl','Termination','ECO','Opening','Variation')
SHARING=(*CLEAN,'OpeningBook','PlyCount','WhiteEngine','BlackEngine','WhiteBook','BlackBook')
TESTING=tuple(key for key in HEADERS if key not in GROUPS[-1][1])
PRESETS={
    'clean':{'label':'Clean games','description':'Essential headers and moves, ready to share or import.',
             'headers':list(CLEAN),'style':'moves','annotations':[],'book_comments':'none'},
    'annotated':{'label':'Annotated games','description':'Readable evaluations, depth and move time with useful game headers.',
                 'headers':list(SHARING),'style':'compact','annotations':['eval','depth','elapsed'],'book_comments':'boundary'},
    'testing':{'label':'Engine testing','description':'Tagged measurements, engine resources and traceable game identifiers.',
               'headers':list(TESTING),'style':'tagged','annotations':list(ANNOTATIONS),'book_comments':'boundary'},
    'archive':{'label':'Complete archive','description':'All headers and measurements, including large encoded settings and local paths.',
               'headers':list(HEADERS),'style':'tagged','annotations':list(ANNOTATIONS),'book_comments':'all'},
}


def normalize(value=None):
    value={} if value is None else value
    if not isinstance(value,dict):raise ValueError('PGN options must be an object')
    allowed={'preset','headers','style','perspective','annotations','book_comments','columns','event','site','names','date_zone'}
    if set(value)-allowed:raise ValueError('Unknown PGN option')
    preset=value.get('preset','annotated')
    if preset not in (*PRESETS,'custom'):raise ValueError('Unknown PGN preset')
    base=deepcopy(PRESETS.get(preset,PRESETS['annotated']))
    base.pop('label');base.pop('description')
    result={'preset':preset,'perspective':'white' if base['style']=='tagged' else 'engine',
            'columns':80,'event':'','site':'','names':'profile','date_zone':'utc',**base,**value}
    if result['style'] not in ('compact','tagged','moves'):raise ValueError('Unknown PGN style')
    if result['perspective'] not in ('engine','white'):raise ValueError('Unknown score perspective')
    if result['style']=='tagged':result['perspective']='white'
    for key,choices in (('headers',HEADERS),('annotations',ANNOTATIONS)):
        items=result[key]
        # None lets the automatic journal respect the tournament's annotation setting.
        if key=='annotations' and items is None:continue
        if not isinstance(items,list) or any(not isinstance(v,str) or v not in choices for v in items):raise ValueError('Unknown PGN '+key)
        result[key]=list(dict.fromkeys(items))
    if result['book_comments'] not in ('none','boundary','all'):raise ValueError('Unknown book comment style')
    columns=result['columns']
    if isinstance(columns,bool) or not isinstance(columns,int) or not 40<=columns<=160:raise ValueError('PGN line width must be between 40 and 160')
    if result['names'] not in ('profile','engine'):raise ValueError('Unknown PGN engine name choice')
    if result['date_zone'] not in ('utc','local'):raise ValueError('Unknown PGN date zone')
    for key in ('event','site'):
        text=result[key]
        if not isinstance(text,str) or len(text)>200:raise ValueError('PGN event and site must contain at most 200 characters')
        result[key]=' '.join(text.split())
    return result


def from_query(query):
    if 'preset' not in query:return None  # Preserve existing API integrations.
    data={key:query[key] for key in ('preset','style','perspective','book_comments','event','site','names','date_zone') if key in query}
    for key in ('headers','annotations'):
        if key in query:data[key]=[v for v in query[key].split(',') if v]
    if 'columns' in query:data['columns']=int(query['columns'])
    return normalize(data)


def schema():
    return {'presets':{key:{**deepcopy(value),'options':normalize({'preset':key})} for key,value in PRESETS.items()},
            'groups':[{'label':label,'headers':keys} for label,keys in GROUPS],
            'required':REQUIRED,'structural':STRUCTURAL,'default':normalize()}


def select_headers(headers,options,*,needs_controls=False,has_evaluation=False,has_timing=False):
    selected=set(options['headers'])|set(REQUIRED)|set(STRUCTURAL)
    # Essential interpretation cannot be removed by a cosmetic header switch.
    if has_evaluation:selected.add('ScorePerspective')
    if has_timing:selected.add('TimeControl')
    if needs_controls:selected.update(('TimeControl',*GROUPS[3][1]))
    encoded=selected.intersection(('WhiteSettings','BlackSettings','TournamentSettings'))
    if encoded:selected.add('SettingsEncoding')
    else:selected.discard('SettingsEncoding')
    return {key:value for key,value in headers.items() if key in selected and str(value).strip()}
