"""Catalog application messages without changing saved diagnostic data."""
import ast,csv,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT))
from arena import i18n
target=ROOT/'locales/sources.json';messages=json.loads(target.read_text(encoding='utf-8'))
def add(text,path):
    messages.setdefault(text,[])
    if path not in messages[text]:messages[text].append(path)
def human(text):
    if not re.search('[A-Za-z]',text) or not (' ' in text or re.fullmatch('[A-Z][a-z]+',text)):return False
    if re.search(r'\b(?:SELECT|INSERT|UPDATE|DELETE|CREATE|FROM|JOIN|CASE|ALTER|BEGIN|END|PRAGMA|ATTACH|DETACH|GROUP BY|ORDER BY)\b|[<>]|https?://|(?:\w|\})=|^\s*(?:#|/|\.|--|\^|data-)|^json_\w+\(',text):return False
    if '\n' in text or re.match(r'^[rnbqkpRNBQKP\d/]+ [wb] ',text):return False
    return True
def walk(node,path,parent=None):
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in ('_t','_h') and node.args and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str):
        source=node.args[0].value
        if node.func.id=='_h':
            i18n.capture=lambda key:add(key,path)
            try:i18n.h(source)
            finally:i18n.capture=None
        else:add(source,path)
        for child in node.args[1:]:walk(child,path,node)
        return
    if isinstance(node,ast.JoinedStr):
        text='';i=0
        for part in node.values:
            if isinstance(part,ast.Constant):text+=part.value
            else:text+='{'+str(i)+'}';i+=1
        if human(text):add(text,path)
        return
    if isinstance(node,ast.Constant) and isinstance(node.value,str) and not isinstance(parent,(ast.Expr,ast.Dict,ast.Subscript,ast.Compare)) and human(node.value):add(node.value,path)
    for child in ast.iter_child_nodes(node):walk(child,path,node)
for path in (ROOT/'arena').glob('*.py'):
    if path.name!='i18n.py':walk(ast.parse(path.read_text(encoding='utf-8')),str(path.relative_to(ROOT)))
for path in (ROOT/'desktop').glob('*.cs'):
    for match in re.finditer(r'L\.T\(("(?:[^"\\]|\\.)*")\)',path.read_text(encoding='utf-8')):
        add(json.loads(match[1]),str(path.relative_to(ROOT)))
for row in list(csv.reader((ROOT/'locales/glossary.tsv').read_text(encoding='utf-8').splitlines(),delimiter='\t'))[1:]:add(row[0],'locales/glossary.tsv')
for text in ['Failed','Timeout','Crash','Hang','Illegal move','Startup timeout','Readiness timeout','Protocol error','Original','Creating the recovery copy…','Executables','All files','Files']:
    add(text,'application labels')
for key in list(messages):
    if re.search(r'GROUP BY|ORDER BY|%Y-%m-%d|<div class="report-table"|^json_\w+\(|^(?:ATTACH|DETACH) DATABASE|^\^|^\s+data-',key) or '</p>' in key:del messages[key]
target.write_text(json.dumps(messages,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(len(messages),'messages')
