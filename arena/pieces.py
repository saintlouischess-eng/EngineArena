"""Import static SVG piece sets without executable or external SVG content."""
from pathlib import Path
import re
import uuid
import xml.etree.ElementTree as ET

FILES=[side+piece+'.svg' for side in ('w','b') for piece in 'KQRBNP']
ALLOWED={'svg','g','path','circle','ellipse','rect','polygon','polyline','line','defs','linearGradient','radialGradient','stop','use','clipPath','title','desc'}

def sanitize_svg(text):
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():raise ValueError('SVG entities and document types are not supported')
    root=ET.fromstring(text)
    if root.tag.rsplit('}',1)[-1]!='svg':raise ValueError('Expected SVG root')
    for e in root.iter():
        if e.tag.rsplit('}',1)[-1] not in ALLOWED:raise ValueError('Piece SVG contains an unsupported element')
        for key,value in e.attrib.items():
            name=key.rsplit('}',1)[-1].lower();lower=value.lower()
            if name.startswith('on') or any(v in lower for v in ('javascript:','file:','http:','https:','@import','expression(')):raise ValueError('Only self-contained static piece SVGs are supported')
            if name=='href' and not value.startswith('#'):raise ValueError('External SVG references are not supported')
            for url in re.findall(r'url\((.*?)\)',value,flags=re.I):
                if not url.strip(' \"\'').startswith('#'):raise ValueError('External SVG URLs are not supported')
    return ET.tostring(root,encoding='unicode')

def import_set(data_folder,source,name):
    source=Path(source);assets={}
    for file in FILES:
        path=source/file
        if not path.is_file():raise ValueError(f'Piece set needs {file}; use wK.svg, wQ.svg, wR.svg, wB.svg, wN.svg, wP.svg and corresponding b files')
        assets[file]=sanitize_svg(path.read_text(encoding='utf-8-sig'))
    key='custom-'+uuid.uuid4().hex;directory=Path(data_folder)/'pieces'/key;directory.mkdir(parents=True)
    for file,text in assets.items():(directory/file).write_text(text,encoding='utf-8')
    (directory/'name.txt').write_text(name or source.name,encoding='utf-8')
    return {'id':key,'name':name or source.name}

def list_sets(data_folder):
    sets=[{'id':key,'name':name} for key,name in [('classic','Classic'),('studio','Studio'),('outline','Outline'),('geometric','Geometric'),('modern','Modern'),('walnut','Walnut')]]
    root=Path(data_folder)/'pieces'
    if root.exists():
        for path in root.iterdir():
            if path.is_dir() and all((path/f).exists() for f in FILES) and (path/'name.txt').exists():sets.append({'id':path.name,'name':(path/'name.txt').read_text(encoding='utf-8')})
    return sets
