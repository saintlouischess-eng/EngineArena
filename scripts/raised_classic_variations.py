"""Raised Classic-family artwork. Entirely static SVG.

GPL-3.0-or-later. Classic-family design reference: Colin M. L. Burnett.
Original preview silhouettes are preserved. Surface modelling uses layered
Bezier shapes, inset bevels, graduated fills and engraved lines, not filters.
"""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from classic_variations import ART, NAMES, PIECES
from preview_classic_variations import sheet

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'exports' / 'classic-raised-preview'
CAPTIONS = {
    'classic-refined': 'Satin pearl and graphite · soft contours · shallow raised edges',
    'classic-bold': 'Polished porcelain and black lacquer · deeper bevels · strong silhouettes',
    'classic-heritage': 'Warm ivory and ebony · fine engraving · softly rounded relief',
}
# Face: left edge / light crest / mid face / deep face / right rim.
PALETTES = {
    'classic-refined': {
        'w': ('#c8d0ce', '#ffffff', '#f0f3ef', '#b5c0be', '#899796'),
        'b': ('#46515a', '#73818a', '#303b45', '#101921', '#35434d'),
    },
    'classic-bold': {
        'w': ('#c9d1d6', '#ffffff', '#fafcfb', '#b8c4c9', '#8797a1'),
        'b': ('#17212a', '#6a7e8b', '#202e3a', '#060d14', '#293b4b'),
    },
    'classic-heritage': {
        'w': ('#c8bca7', '#fffdf2', '#f1e8d5', '#bcae96', '#95856f'),
        'b': ('#403c37', '#797165', '#35312c', '#141617', '#48443c'),
    },
}


def geometry(node):
    return {key: value for key, value in node.attrib.items()
            if key not in ('fill', 'stroke', 'stroke-width', 'class')}


def element(tag, attrs):
    return ET.tostring(ET.Element(tag, attrs), encoding='unicode', short_empty_elements=True)


def path(d, **attrs):
    return element('path', {'d': d, **{k.replace('_', '-'): str(v) for k, v in attrs.items()}})


def gradient_defs(style, side):
    left, light, middle, deep, rim = PALETTES[style][side]
    white = side == 'w'
    edge = '#364443' if white else '#080e14'
    if style == 'classic-heritage': edge = '#514c42' if white else '#131311'
    peak = '.28' if style != 'classic-bold' else '.23'
    fall = '.61' if style != 'classic-bold' else '.43'
    # Separate gradients keep the crown pearls round and the thin outline lit.
    return f'''<linearGradient id="face" x1="0" y1="0" x2="1" y2=".2">
<stop stop-color="{left}"/><stop offset="{peak}" stop-color="{light}"/><stop offset="{fall}" stop-color="{middle}"/><stop offset=".9" stop-color="{deep}"/><stop offset="1" stop-color="{rim}"/>
</linearGradient>
<radialGradient id="round" cx=".31" cy=".23" r=".78">
<stop stop-color="{light}"/><stop offset=".32" stop-color="{middle}"/><stop offset=".78" stop-color="{deep}"/><stop offset="1" stop-color="{left}"/>
</radialGradient>
<linearGradient id="bevel" x1=".15" y1="0" x2=".8" y2="1">
<stop stop-color="{'#ffffff' if white else '#b1bec6'}"/><stop offset=".36" stop-color="{light}"/><stop offset=".62" stop-color="{middle}"/><stop offset="1" stop-color="{edge}"/>
</linearGradient>
<linearGradient id="engraving" x1="0" y1="0" x2="0" y2="1">
<stop stop-color="{'#7c8985' if white else '#b5c2c7'}"/><stop offset=".5" stop-color="{'#53625e' if white else '#768993'}"/><stop offset="1" stop-color="{'#919c96' if white else '#506571'}"/>
</linearGradient>
<radialGradient id="glaze" cx=".34" cy=".22" r=".73">
<stop stop-color="#ffffff" stop-opacity="{'.62' if white else '.24'}"/><stop offset=".46" stop-color="#ffffff" stop-opacity=".12"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/>
</radialGradient>''', edge


def details(symbol, side):
    """Broad surface highlights follow the carved forms, not the square."""
    glow = '#ffffff' if side == 'w' else '#c5d4da'
    shine = lambda d, width=1.25: path(d, fill='none', stroke=glow, stroke_width=width, opacity='.72')
    if symbol == 'K':
        return '<ellipse cx="29" cy="49" rx="17" ry="15" fill="url(#glaze)"/><ellipse cx="73" cy="48" rx="14" ry="14" fill="url(#glaze)"/>' + shine('M21 40 C29 37 38 43 43 49 M64 42 C69 39 76 38 80 40', 1.2)
    if symbol == 'Q':
        return shine('M17 36 L22 53 M33 29 L39 49 M50 29 L54 48 M73 33 L72 47', 1.05) + shine('M27 66 Q46 63 67 65', 1.15)
    if symbol == 'R':
        return path('M64 52 H70 V71 H64 Z', fill='#000000', opacity='.1') + shine('M34 53 V69 M27 24 H32 M47 24 H53 M68 24 H73 M25 87 H68', 1.15)
    if symbol == 'B':
        return '<ellipse cx="48" cy="43" rx="18" ry="15" fill="url(#glaze)"/>' + shine('M40 36 Q43 33 47 30 M37 66 Q44 64 50 65', 1.25)
    if symbol == 'N':
        return '<ellipse cx="40" cy="40" rx="24" ry="28" fill="url(#glaze)"/>' + path('M63 32 C77 44 82 62 80 83 L84 89 L87 91 C89 66 86 48 75 35 Z', fill='#000000', opacity='.14') + shine('M36 31 Q44 28 48 29 M45 65 Q36 78 36 86 M58 29 C74 33 83 54 83 73', 1.25)
    return '<circle cx="50" cy="39" r="10" fill="url(#round)"/><ellipse cx="50" cy="61" rx="17" ry="14" fill="url(#round)"/>' + shine('M44 33 Q47 31 51 32 M38 54 Q42 51 46 52 M33 87 Q43 83 56 84', 1.1)


def piece_svg(style, side, symbol):
    white = side == 'w'
    raw = ART[style][symbol]
    # These flat-design accent loops are replaced by shaped surface highlights.
    raw = re.sub(r'<g class="dark-detail">.*?</g>', '', raw)
    nodes = list(ET.fromstring('<g>'+raw+'</g>'))
    faces = [e for e in nodes if e.get('fill') == '{body}']
    lines = [e for e in nodes if e.get('fill') != '{body}']
    defs, edge = gradient_defs(style, side)
    shape_width = {'classic-refined': 1.85, 'classic-bold': 2.25, 'classic-heritage': 1.65}[style]
    bevel_width = {'classic-refined': 3.1, 'classic-bold': 4.1, 'classic-heritage': 2.6}[style]
    lift = {'classic-refined': (1.0, 1.65), 'classic-bold': (1.2, 2.0), 'classic-heritage': (.85, 1.45)}[style]
    fill_geometries = ''.join(element(e.tag, geometry(e)) for e in faces)
    defs += '<clipPath id="silhouette">'+fill_geometries+'</clipPath>'
    for index, e in enumerate(faces): defs += f'<clipPath id="face-{index}">'+element(e.tag, geometry(e))+'</clipPath>'

    # A small solid extrusion and a thinner contact edge give relief without
    # blur filters or changing the familiar silhouettes.
    shadow = ''.join(element(e.tag, geometry(e)|{'fill':'#071019','stroke':'#071019','stroke-width':str(shape_width)}) for e in faces)
    art = f'<g transform="translate({lift[0]+.5} {lift[1]+.7})" opacity=".14">{shadow}</g>'
    art += f'<g transform="translate({lift[0]} {lift[1]})" opacity="{'.65' if white else '.9'}">{shadow}</g>'
    for index, e in enumerate(faces):
        g = geometry(e)
        fill = 'url(#round)' if e.tag == 'circle' else 'url(#face)'
        art += element(e.tag, g|{'fill':fill,'stroke':edge,'stroke-width':str(shape_width)})
        art += f'<g clip-path="url(#face-{index})">'+element(e.tag, g|{'fill':'none','stroke':'url(#bevel)','stroke-width':str(bevel_width)})+'</g>'
    art += '<g clip-path="url(#silhouette)">'+details(symbol, side)+'</g>'

    for e in lines:
        g = geometry(e)
        if e.tag != 'path':
            art += element(e.tag, g|{'fill':edge if white else '#dce7e9','stroke':'none'})
            continue
        external = e.get('stroke') == '{edge}'
        width = float(e.get('stroke-width', 2.4)) * (.85 if style=='classic-bold' else .71)
        if external: width = 2.8 if style=='classic-bold' else 2.3
        if not external:
            art += element('path',g|{'fill':'none','stroke':'#ffffff' if white else '#bdcbd0',
                                    'stroke-width':str(width+.65),'transform':'translate(0 .68)',
                                    'opacity':'.72' if white else '.23'})
        art += element('path',g|{'fill':'none','stroke':edge if external else 'url(#engraving)','stroke-width':str(width)})
        if external:
            art += element('path',g|{'fill':'none','stroke':'#fffdf3' if white else '#b4c5cb',
                                    'stroke-width':'.65','transform':'translate(-.25 -.28)','opacity':'.72'})
    name = f'{NAMES[style]} Raised — {"White" if white else "Black"} {PIECES[symbol]}'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" role="img" aria-labelledby="title">
<title id="title">{name}</title>
<desc>Raised vector artwork of the Classic family, GPL-3.0-or-later. Burnett design reference. Static gradients, bevels and engraved details; no raster images or filters.</desc>
<defs>{defs}</defs><g stroke-linecap="round" stroke-linejoin="round">{art}</g>
</svg>
'''


def generate(root=OUTPUT, previews=True):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    for style in NAMES:
        folder = root / style
        folder.mkdir(exist_ok=True)
        for side in 'wb':
            for piece in PIECES:
                (folder / f'{side}{piece}.svg').write_text(piece_svg(style,side,piece), encoding='utf-8')
        if previews:
            (root / f'{style}.svg').write_text(sheet(style, source=root, caption=CAPTIONS[style], edition=' · Raised'), encoding='utf-8')


if __name__ == '__main__':
    generate()
