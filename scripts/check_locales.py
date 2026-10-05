"""Validate offline catalogs; --sync writes English and removes obsolete keys."""
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'locales'
sources=json.loads((folder/'sources.json').read_text(encoding='utf-8'))
codes=('en','es','fr','de','pt','it','nl','pl')
errors=[];counts={}
for code in codes:
    file=folder/(code+'.json')
    if code=='en' and '--sync' in sys.argv:
        file.write_text(json.dumps({'language':'en','status':'source','messages':{key:key for key in sources}},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    data=json.loads(file.read_text(encoding='utf-8'));messages=data['messages']
    for key in sources:
        value=messages.get(key)
        if not isinstance(value,str) or not value.strip():errors.append((code,key,'missing'));continue
        if sorted(re.findall(r'\{\d+\}',key))!=sorted(re.findall(r'\{\d+\}',value)):errors.append((code,key,'placeholders'))
        if re.search(r'▁|9817\d{5}|[\ue100\ue101]',value):errors.append((code,key,'translation artifact'))
        for version in re.findall(r'\b\d+\.\d+\.\d+ (?:Beta|RC) \d+(?: RC \d+)?',key):
            if version not in value:errors.append((code,key,'version identifier changed'))
        for filename in ('games.pgn','interrupted.pgn'):
            if filename in key and filename not in value:errors.append((code,key,'filename changed: '+filename))
    if '--sync' in sys.argv:
        data['messages']={key:messages[key] for key in sources if key in messages}
        file.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    counts[code]=len(data['messages'])
result={'messages':len(sources),'catalogs':counts,'errors':errors}
(ROOT/'test-output/languages-catalogs.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
raise SystemExit(bool(errors))
