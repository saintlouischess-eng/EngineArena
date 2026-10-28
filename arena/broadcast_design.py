"""Bounded, versioned broadcast documents. No tournament access or mutations."""
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
CATALOG = json.loads((ROOT/'ui/broadcast-catalog.json').read_text(encoding='utf-8'))
PANEL_TYPES = set(CATALOG['panels'])
FONTS = ('system','serif','mono')
GRAPH_STYLES = ('line','dots','bars','area','step','scatter')

def number(value, lo, hi, default):
    try:
        n = float(value)
        return max(lo, min(hi, n)) if math.isfinite(n) else default
    except (ValueError, TypeError): return default

def color(value, default=''):
    return value if isinstance(value,str) and re.fullmatch(r'#[0-9a-fA-F]{6}',value) else default

def text(value, maximum=200): return str(value or '')[:maximum]
def choice(value, choices, default): return value if isinstance(value,str) and value in choices else default

def panel(kind, x, y, w, h, **extra):
    return dict(id=kind, type=kind, x=x, y=y, w=w, h=h, visible=True, locked=False,
                font_size=24, heading_size=0, detail_size=0, auto_fit=True, logo_size=96,
                header_progress=True, header_eta=True, padding=extra.pop('padding_override',20), title='', background='', color='', columns=['points','games'],
                rows=10, limit=20, text='', image='', **extra)

def default_scene():
    return dict(id='main', name='Tournament', seconds=60, tid='', enabled=True, panels=[
        panel('header',2,2,96,9,padding_override=8), panel('board',2,12,47,79),
        panel('rotation',51,12,47,46), panel('analysis',51,60,47,31), panel('ticker',0,93,100,7,padding_override=0)])

def camera(value):
    p=value if isinstance(value,dict) else {}
    return {k:number(p.get(k),lo,hi,d) for k,lo,hi,d in [('angle',6,78,50),('orbit',-180,180,0),
        ('zoom',.6,2.4,1),('lift',-.5,.5,0),('tilt',-30,70,0)]}

def scene3d(value):
    p=value if isinstance(value,dict) else {}; out={}
    for k, choices, default in [
        ('board',CATALOG['boards3d'],'classic'),('environment',CATALOG['rooms'],'club'),
        ('surface',('wood','felt','leather'),'wood'),('lighting',('daylight','evening','tournament'),'tournament'),
        ('quality',('low','balanced','high'),'balanced'),('mode',('testing','presentation'),'testing'),
        ('motion',('instant','quick','smooth'),'quick'),('tour',('cinematic','orbit','views'),'cinematic'),
        ('activity',('quiet','social','busy'),'social'),('roomMotion',('system','animate','still'),'animate')]:
        out[k]=choice(p.get(k),choices,default)
    for k,lo,hi,d in [('roomRotation',-180,180,0),('brightness',.6,1.4,1),('warmth',-1,1,0),
        ('tourSpeed',.5,1.5,1),('highlight',.2,.6,.38),('ambienceVolume',0,50,15)]:out[k]=number(p.get(k),lo,hi,d)
    for k,d in [('coordinates',True),('trays',False),('plates',True),('plaque',True),('localTime',True),
        ('live',False),('people',True),('backgroundGames',True),('atmosphere',True),('ambience',False)]:
        out[k]=p.get(k,d) is True
    out['fps']=15 if p.get('fps')==15 else 30
    return out

def ticker_style(value):
    p=value if isinstance(value,dict) else {}
    return dict(label=text(p.get('label','ARENA WIRE'),40),
        separator=choice(p.get('separator'),('diamond','bullet','bar','space'),'diamond'),
        spacing=number(p.get('spacing'),.25,4,1),headline_seconds=number(p.get('headline_seconds'),5,120,14),
        text_color=color(p.get('text_color')),score_color=color(p.get('score_color'),'#dfbb76'),
        outcome_color=color(p.get('outcome_color'),'#dfbb76'),separator_color=color(p.get('separator_color')),
        label_color=color(p.get('label_color')),background=color(p.get('background')),
        custom=text(p.get('custom'),2000))

def appearance(value):
    """Only explicit scene overrides; unspecified values inherit the show."""
    p=value if isinstance(value,dict) else {};out={}
    for k,values,d in [('theme',CATALOG['themes'],'charcoal'),('pieces',CATALOG['pieces'],'classic-bold'),
        ('board_mode',('2d','3d'),'2d'),('pieces3d',CATALOG['pieces3d'],'staunton1849'),
        ('knights3d',('inward','outward','forward','backward','left','right'),'inward'),
        ('board_light',CATALOG['woods'],'ash'),('board_dark',CATALOG['woods'],'rosewood'),
        ('ticker_mode',('scroll','headlines'),'scroll')]:
        if k in p:out[k]=choice(p[k],values,d)
    for k,d in [('board_light_color','#ead8ae'),('board_dark_color','#70503a'),('arrow_color','#35b9f3')]:
        if k in p:out[k]=color(p[k],d)
    for k,lo,hi,d in [('dark_lighten',0,60,0),('eval_range',.1,100,5),
        ('eval_width',16,80,27),('eval_text_size',10,40,16),('arrow_delay',0,10,1),
        ('ticker_seconds',20,600,150),('ticker_size',14,56,26)]:
        if k in p:out[k]=number(p[k],lo,hi,d)
    for k in ('flip','thinking_arrows','crown_marks','ticker'):
        if k in p:out[k]=p[k] is True
    for k,fn in [('scene3d',scene3d),('camera3d',camera),('ticker_style',ticker_style)]:
        if isinstance(p.get(k),dict):out[k]={a:b for a,b in fn(p[k]).items() if a in p[k]}
    if isinstance(p.get('saved_cameras'),list):out['saved_cameras']=[camera(c) for c in p['saved_cameras'][:8]]
    return out

def design(value):
    p=value if isinstance(value,dict) else {}; scenes=[]; used=set()
    for i,s in enumerate((p.get('scenes') if isinstance(p.get('scenes'),list) else [default_scene()])[:30]):
        if not isinstance(s,dict):continue
        sid=text(s.get('id') or f'scene-{i}',60)
        while sid in used:sid+='-copy'
        used.add(sid); panels=[]; ids=set(); board=False
        for j,v in enumerate((s.get('panels') if isinstance(s.get('panels'),list) else [])[:24]):
            if not isinstance(v,dict) or not isinstance(v.get('type'),str) or v.get('type') not in PANEL_TYPES:continue
            kind=v['type']
            if kind=='board' and board:continue
            if kind=='board':board=True
            pid=text(v.get('id') or f'panel-{j}',60)
            while pid in ids:pid+='-copy'
            ids.add(pid)
            x=number(v.get('x'),0,98,2);y=number(v.get('y'),0,98,2)
            cols=[c for c in v.get('columns',[]) if c in ('points','games','wins','draws','losses','sonneborn_berger','rating','ci','score_pct')][:8] if isinstance(v.get('columns'),list) else ['points','games']
            image=text(v.get('image'),80)
            panels.append(dict(id=pid,type=kind,x=x,y=y,w=number(v.get('w'),2,100-x,40),h=number(v.get('h'),2,100-y,30),
                visible=v.get('visible',True) is True,locked=v.get('locked') is True,
                font_size=number(v.get('font_size'),12,80,24),
                heading_size=number(v.get('heading_size'),0,80,0),detail_size=number(v.get('detail_size'),0,80,0),
                logo_size=number(v.get('logo_size'),32,180,96),
                header_progress=v.get('header_progress',True) is True,header_eta=v.get('header_eta',True) is True,
                auto_fit=v.get('auto_fit',True) is not False,padding=number(v.get('padding'),0,60,20),
                title=text(v.get('title')),background=color(v.get('background')),color=color(v.get('color')),
                columns=cols,rows=int(number(v.get('rows'),1,40,10)),limit=int(number(v.get('limit'),0,10000,20)),
                inherit_counts=v.get('inherit_counts',True) is True,
                text=text(v.get('text'),2000),image=image if re.fullmatch(r'[a-f0-9]{64}\.(png|jpg|webp)',image) else '',
                graph_style=choice(v.get('graph_style'),GRAPH_STYLES,'line'),
                metric=choice(v.get('metric'),('evaluation','depth','nps','nodes','clock'),'evaluation'),
                engines=choice(v.get('engines'),('both','white','black'),'both'),
                white_color=color(v.get('white_color'),'#dfbb76'),black_color=color(v.get('black_color'),'#56bed9'),
                legend=v.get('legend',True) is True,grid=v.get('grid',True) is True,
                series_colors={text(k,200):color(c,'#dfbb76') for k,c in list(v.get('series_colors',{}).items())[:50]} if isinstance(v.get('series_colors'),dict) else {},
                series_styles={text(k,200):choice(c,GRAPH_STYLES,'line') for k,c in list(v.get('series_styles',{}).items())[:50]} if isinstance(v.get('series_styles'),dict) else {}))
        scenes.append(dict(id=sid,name=text(s.get('name') or 'Scene',80),seconds=number(s.get('seconds'),10,3600,60),
                           tid=text(s.get('tid'),80),enabled=s.get('enabled',True) is True,panels=panels,appearance=appearance(s.get('appearance'))))
    if not scenes:scenes=[default_scene()]
    active=choice(p.get('active'),[s['id'] for s in scenes],scenes[0]['id'])
    return dict(version=1,width=int(number(p.get('width'),640,3840,1920)),height=int(number(p.get('height'),360,2160,1080)),
        active=active,scenes=scenes,auto=p.get('auto') is True,transition=choice(p.get('transition'),('cut','fade'),'fade'),
        font=choice(p.get('font'),FONTS,'system'),accent=color(p.get('accent')),background=color(p.get('background')),
        text_color=color(p.get('text_color')),snap=number(p.get('snap'),0,5,1),safe=number(p.get('safe'),0,10,2))

def extra_settings(value):
    p=value if isinstance(value,dict) else {}
    return dict(design=design(p.get('design')),ticker_style=ticker_style(p.get('ticker_style')),arrow_color=color(p.get('arrow_color'),'#35b9f3'),
        board_mode=choice(p.get('board_mode'),('2d','3d'),'2d'),
        eval_width=number(p.get('eval_width'),16,80,27),eval_text_size=number(p.get('eval_text_size'),10,40,16),
        pieces3d=choice(p.get('pieces3d'),CATALOG['pieces3d'],'staunton1849'),
        knights3d=choice(p.get('knights3d'),('inward','outward','forward','backward','left','right'),'inward'),
        camera3d=camera(p.get('camera3d')),scene3d=scene3d(p.get('scene3d')),
        saved_cameras=[camera(c) for c in p.get('saved_cameras',[])[:8]] if isinstance(p.get('saved_cameras'),list) else [],
        standings_limit=int(number(p.get('standings_limit'),0,10000,20)),ratings_limit=int(number(p.get('ratings_limit'),0,10000,20)),
        rows=int(number(p.get('rows'),1,40,10)),rating_scope=choice(p.get('rating_scope'),('all','field'),'all'),
        board_light_color=color(p.get('board_light_color'),'#ead8ae'),board_dark_color=color(p.get('board_dark_color'),'#70503a'),
        crown_marks=p.get('crown_marks') is True,
        playlist=list(dict.fromkeys(text(t,80) for t in p.get('playlist',[]) if isinstance(t,str)))[:100] if isinstance(p.get('playlist'),list) else [],
        event_rotation=p.get('event_rotation') is True,event_seconds=number(p.get('event_seconds'),30,86400,600))
