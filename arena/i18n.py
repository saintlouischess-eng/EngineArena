"""Offline presentation catalogs. Stored records and machine protocols stay stable."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache
import html
import json
from pathlib import Path
import re
import sys

LANGUAGES={'en':'English','es':'Español','fr':'Français','de':'Deutsch','pt':'Português','it':'Italiano','nl':'Nederlands','pl':'Polski'}
ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))/'locales'
current=ContextVar('arena_language',default='en')
capture=None

def language(code):return code if isinstance(code,str) and code in LANGUAGES else 'en'

@lru_cache(maxsize=8)
def catalog(code):
    if code=='en':return {}
    try:
        data=json.loads((ROOT/(language(code)+'.json')).read_text(encoding='utf-8'))
        messages=data.get('messages',{}) if isinstance(data,dict) else {}
        if not isinstance(messages,dict):return {}
        return {key:value for key,value in messages.items() if isinstance(value,str) and sorted(re.findall(r'\{\d+\}',key))==sorted(re.findall(r'\{\d+\}',value))}
    except (OSError,ValueError,KeyError):return {}

@contextmanager
def using(code):
    token=current.set(language(code))
    try:yield
    finally:current.reset(token)

def t(source,*values):
    if capture:capture(source)
    translated=catalog(current.get()).get(source,source)
    if sorted(re.findall(r'\{\d+\}',source))!=sorted(re.findall(r'\{\d+\}',translated)):translated=source
    return re.sub(r'\{(\d+)\}',lambda m:str(values[int(m[1])]) if int(m[1])<len(values) else m[0],translated)


@lru_cache(maxsize=8)
def _patterns(code):
    result=[]
    for key in catalog(code):
        if not re.search(r'\{\d+\}',key) or not re.search('[A-Za-z]{3}',key) or '<' in key:continue
        ids=[];parts=[];cursor=0
        for found in re.finditer(r'\{(\d+)\}',key):
            parts.extend((re.escape(key[cursor:found.start()]),'(.*?)'));ids.append(int(found[1]));cursor=found.end()
        parts.append(re.escape(key[cursor:]));result.append((key,ids,re.compile(''.join(parts),re.S)))
    return result


def message(value):
    """Application messages only; never feed engine names or raw diagnostics here."""
    if value is None or current.get()=='en':return value
    source=str(value)
    if source in catalog(current.get()):return t(source)
    for key,ids,pattern in _patterns(current.get()):
        found=pattern.fullmatch(source)
        if found:
            values=['']*(max(ids)+1)
            for index,slot in enumerate(ids,1):values[slot]=found[index]
            return t(key,*values)
    return source

def number(value,digits=1):
    result=f'{value:,.{digits}f}'
    code=current.get()
    if code=='en':return result
    grouping='\u202f' if code=='fr' else '\u00a0' if code=='pl' else '.'
    return result.replace(',','\0').replace('.',',').replace('\0',grouping)

_marker=re.compile('\ue100(\\d+)\ue101')
def _text(source):
    key=re.sub(r'\s+',' ',html.unescape(source)).strip()
    key=_marker.sub(lambda m:'{'+m[1]+'}',key)
    if not re.search('[A-Za-z]',key):return source
    translated=t(key)
    if translated==key:return source
    body=html.escape(translated,quote=True)
    body=re.sub(r'\{(\d+)\}',lambda m:'\ue100'+m[1]+'\ue101',body)
    return re.match(r'^\s*',source)[0]+body+re.search(r'\s*$',source)[0]

def _markup(source):
    result=[];cursor=0;skip=''
    for found in re.finditer(r'<!--[\s\S]*?-->|</?[A-Za-z!][^<>"\']*(?:(?:"[^"]*"|\'[^\']*\')[^<>"\']*)*>',source):
        result.append(source[cursor:found.start()] if skip else _text(source[cursor:found.start()]))
        tag=found[0];name=re.match(r'</?([\w-]+)',tag);name=name[1].lower() if name else ''
        result.append(re.sub(r'\b(title|placeholder|aria-label|aria-description|data-help)=("[^"]*"|\'[^\']*\')',lambda m:m[1]+'='+m[2][0]+_text(m[2][1:-1])+m[2][0],tag))
        if tag.startswith('</') and name==skip:skip=''
        elif name in ('script','style','pre','code','textarea') and not tag.startswith('</'):skip=name
        cursor=found.end()
    result.append(source[cursor:] if skip else _text(source[cursor:]))
    return ''.join(result)

@lru_cache(maxsize=4096)
def _compiled(code,source):
    with using(code):return _markup(source)

def h(source,*values):
    if current.get()=='en' and not capture:
        return re.sub(r'\{(\d+)\}',lambda m:str(values[int(m[1])]) if int(m[1])<len(values) else m[0],source)
    skeleton=re.sub(r'\{(\d+)\}',lambda m:'\ue100'+m[1]+'\ue101',source)
    rendered=_markup(skeleton) if capture else _compiled(current.get(),skeleton)
    return _marker.sub(lambda m:str(values[int(m[1])]) if int(m[1])<len(values) else '{'+m[1]+'}',rendered)

def render_report(path,tid,confidence=95,all_engines=False,technical=True,locale='en'):
    from .tournament_report import render
    with using(locale):return render(path,tid,confidence,all_engines,technical).replace('<html lang="en">','<html lang="'+language(locale)+'">',1)
