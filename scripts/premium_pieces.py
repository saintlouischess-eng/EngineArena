"""Original Engine Arena vector artwork, GPL-3.0-or-later; no external assets.

Three independently drawn profiles on a 100-unit grid. Static gradients and
engraved lines suggest turned materials without raster images or SVG filters.
"""
from pathlib import Path

NAMES={'regal':'Regal','heirloom':'Heirloom','porcelain':'Porcelain'}
PIECES={'K':'king','Q':'queen','R':'rook','B':'bishop','N':'knight','P':'pawn'}
HEADS={
'regal':{
 'K':'<path d="M46 7 H54 V15 H62 V22 H54 V31 H46 V22 H38 V15 H46 Z"/><path d="M50 35 C40 23 28 28 30 39 C31 46 38 49 40 53 H60 C62 49 69 46 70 39 C72 28 60 23 50 35 Z"/><path class="engrave" d="M50 35 V48 M35 36 Q36 43 42 45"/>',
 'Q':'<path d="M27 23 L37 38 L39 17 L50 36 L61 17 L63 38 L73 23 L65 48 Q50 54 35 48 Z"/><circle cx="26" cy="19" r="4"/><circle cx="39" cy="13" r="4"/><circle cx="50" cy="8" r="4"/><circle cx="61" cy="13" r="4"/><circle cx="74" cy="19" r="4"/><path class="engrave" d="M37 43 Q50 47 63 43 M42 29 L46 39 M58 29 L54 39"/>',
 'B':'<circle cx="50" cy="10" r="4"/><path d="M50 16 C43 23 31 30 34 39 C36 47 45 48 50 51 C55 48 64 47 66 39 C69 30 57 23 50 16 Z"/><path class="cut" d="M56 24 L44 38"/><path class="shine" d="M43 27 Q36 35 40 40"/>',
 'N':'<path d="M29 69 Q29 58 39 47 L30 49 Q25 49 21 43 L20 39 L30 29 L37 24 L39 11 L46 19 L52 15 Q65 17 72 30 C78 42 75 59 70 70 Z"/><path class="engrave" d="M52 22 Q67 28 66 42 Q64 52 54 64 M58 27 L63 25 M61 32 L68 32 M62 38 L70 39 M61 44 L69 46 M58 50 L66 54 M37 36 L31 39 M26 44 L31 45"/><path class="shine" d="M46 27 Q51 34 44 42 Q36 53 36 61"/><path class="feature" d="M40 29 L47 28 L44 33 Z"/><circle class="feature" cx="26" cy="40" r="1.5"/>',
 'R':'<path d="M27 16 H38 V26 H44 V16 H56 V26 H62 V16 H73 V37 L65 44 H35 L27 37 Z"/><path class="engrave" d="M30 35 H70 M37 39 H63"/>',
 'P':'<circle cx="50" cy="28" r="12"/><path class="shine" d="M42 23 Q46 18 51 20"/><path d="M39 42 Q50 38 61 42 L59 48 H41 Z"/>'},
'heirloom':{
 'K':'<path d="M46 7 Q50 4 54 7 V15 H61 Q65 19 61 23 H54 V32 H46 V23 H39 Q35 19 39 15 H46 Z"/><path d="M50 37 C43 25 26 29 31 41 L40 52 H60 L69 41 C74 29 57 25 50 37 Z"/><path class="engrave" d="M50 37 V48 M39 36 L44 45 M61 36 L56 45"/>',
 'Q':'<path d="M25 22 Q31 23 36 34 L40 18 Q44 21 50 34 Q56 21 60 18 L64 34 Q69 23 75 22 L65 47 Q50 53 35 47 Z"/><circle cx="25" cy="18" r="4"/><circle cx="40" cy="14" r="4"/><circle cx="50" cy="8" r="4"/><circle cx="60" cy="14" r="4"/><circle cx="75" cy="18" r="4"/><path class="engrave" d="M38 42 Q50 46 62 42 M43 31 L46 39 M57 31 L54 39"/>',
 'B':'<circle cx="50" cy="9" r="4"/><path d="M50 16 C48 22 31 28 32 38 C33 48 45 52 50 51 C55 52 67 48 68 38 C69 28 52 22 50 16 Z"/><path class="cut" d="M56 26 L44 39"/><path class="shine" d="M42 28 Q36 32 37 39"/>',
 'N':'<path d="M27 70 C27 58 34 52 41 44 L29 48 Q24 48 20 42 L21 37 L32 28 L37 24 L37 11 L44 17 L49 15 L54 19 C69 18 78 35 75 49 Q75 62 68 71 Z"/><path class="engrave" d="M52 24 C66 28 67 44 57 56 L49 64 M56 24 L59 19 M61 28 L67 24 M64 34 L72 32 M64 41 L74 41 M62 48 L73 51 M58 55 L70 61 M35 35 L28 39 M25 44 L30 44"/><path class="shine" d="M42 26 Q48 30 45 37 M42 50 Q34 57 33 65"/><path class="feature" d="M38 30 Q43 26 47 29 L43 34 Z"/><circle class="feature" cx="25" cy="39" r="1.4"/>',
 'R':'<path d="M25 15 H37 V25 H43 V17 H57 V25 H63 V15 H75 V35 Q71 40 65 42 H35 Q29 40 25 35 Z"/><path class="engrave" d="M29 34 Q50 38 71 34 M36 40 H64"/>',
 'P':'<ellipse cx="50" cy="28" rx="12" ry="13"/><path class="shine" d="M43 22 Q47 17 52 20"/><path d="M38 43 Q50 39 62 43 L59 49 H41 Z"/>'},
'porcelain':{
 'K':'<path d="M46 8 Q50 5 54 8 V16 H61 V23 H54 V32 H46 V23 H39 V16 H46 Z"/><path d="M31 36 Q31 27 40 30 L50 38 L60 30 Q69 27 69 36 Q69 45 60 52 H40 Q31 45 31 36 Z"/><path class="engrave" d="M50 38 V48"/>',
 'Q':'<path d="M27 24 Q34 23 38 35 Q40 23 45 23 L50 34 L55 23 Q60 23 62 35 Q66 23 73 24 L65 46 Q50 53 35 46 Z"/><circle cx="27" cy="19" r="4"/><circle cx="43" cy="17" r="4"/><circle cx="50" cy="9" r="4"/><circle cx="57" cy="17" r="4"/><circle cx="73" cy="19" r="4"/><path class="engrave" d="M37 42 Q50 46 63 42"/>',
 'B':'<circle cx="50" cy="9" r="4"/><path d="M50 17 Q70 31 67 39 Q64 49 50 51 Q36 49 33 39 Q30 31 50 17 Z"/><path class="cut" d="M56 26 L44 39"/><path class="shine" d="M43 27 Q36 32 38 39"/>',
 'N':'<path d="M29 70 Q28 57 41 45 L30 48 Q23 49 20 42 Q18 38 23 34 L35 25 L38 12 Q43 12 46 20 Q57 16 66 24 Q78 35 73 53 Q73 65 67 71 Z"/><path class="engrave" d="M54 25 Q67 31 65 44 Q62 56 51 65 M33 36 L27 39 M25 44 H30"/><path class="shine" d="M42 27 Q48 31 44 38 M43 49 Q35 58 36 65"/><ellipse class="feature" cx="42" cy="31" rx="2.8" ry="2"/><circle class="feature" cx="25" cy="39" r="1.2"/>',
 'R':'<path d="M27 17 Q27 14 31 14 H38 V25 H44 V16 H56 V25 H62 V14 H69 Q73 14 73 17 V35 Q71 43 64 44 H36 Q29 43 27 35 Z"/><path class="engrave" d="M31 35 Q50 40 69 35"/>',
 'P':'<circle cx="50" cy="29" r="13"/><path class="shine" d="M42 24 Q46 18 53 21"/><path d="M39 43 Q50 40 61 43 Q64 49 58 51 H42 Q36 49 39 43 Z"/>'}}

STEMS={
'regal':'M40 51 H60 C56 57 55 63 60 69 L65 74 H35 L40 69 C45 63 44 57 40 51 Z',
'heirloom':'M39 50 H61 Q58 56 58 60 Q58 66 65 72 L64 75 H36 L35 72 Q42 66 42 60 Q42 56 39 50 Z',
'porcelain':'M41 50 H59 Q54 56 59 63 Q66 70 61 75 H39 Q34 70 41 63 Q46 56 41 50 Z'}

PALETTES={
 'regal':(('#bba786','#fff9e5','#eee2c7','#9c8564','#463c2c','#fffef3','#816b47'),('#080f17','#526272','#202e3c','#0a141e','#c0cbd0','#c5d7df','#728fa2')),
 'heirloom':(('#ad7139','#ffe1a1','#deb574','#975e30','#54321d','#fff0c8','#9b6031'),('#24120f','#93604a','#512d23','#21120e','#d4b797','#e3b98c','#b58352')),
 'porcelain':(('#abbfc9','#ffffff','#eaf2f1','#8da8b7','#3a596e','#ffffff','#557b9a'),('#081b3b','#6382a9','#24446c','#0a1d3e','#c6d8e6','#c7e2f4','#8eafd1'))}

def piece_svg(style,side,symbol):
    low,lit,body,shade,edge,shine,accent=PALETTES[style][0 if side=='w' else 1]
    title=f'{NAMES[style]} — {"White" if side=="w" else "Black"} {PIECES[symbol]}'
    defs=f'''<defs><linearGradient id="body" x1="0" y1="0" x2="1" y2=".15"><stop stop-color="{low}"/><stop offset=".29" stop-color="{lit}"/><stop offset=".54" stop-color="{body}"/><stop offset=".83" stop-color="{shade}"/><stop offset="1" stop-color="{body}"/></linearGradient><linearGradient id="rim" x2="0" y2="1"><stop stop-color="{lit}"/><stop offset=".4" stop-color="{body}"/><stop offset="1" stop-color="{shade}"/></linearGradient></defs>'''
    stem=STEMS[style]
    if symbol=='R':stem={'regal':'M36 42 H64 L61 69 L66 74 H34 L39 69 Z','heirloom':'M36 42 H64 Q58 58 63 69 L66 74 H34 L37 69 Q42 58 36 42 Z','porcelain':'M37 43 H63 L61 66 Q66 72 62 75 H38 Q34 72 39 66 Z'}[style]
    if symbol=='P':stem=stem.replace('51','48').replace('50','49')
    body_path=f'<path d="{stem}"/>' if symbol!='N' else '<path d="M31 66 H69 L66 76 H34 Z"/>'
    fluting=''
    if symbol not in ('N','R'):
        fluting='<path class="shine" d="M45 55 Q49 64 42 69"/>'
        if style=='heirloom':fluting+='<path class="engrave" d="M49 56 V67 M55 56 Q53 63 57 68"/>'
    if symbol=='R':fluting='<path class="shine" d="M42 46 L43 65"/><path class="engrave" d="M58 46 L57 65"/>'
    # Heirloom has a curved ogee base; Porcelain a rounded glazed foot.
    base={'regal':'M32 76 Q50 72 68 76 L72 82 L75 86 V91 H25 V86 L28 82 Z','heirloom':'M33 75 Q50 71 67 75 Q66 79 71 81 Q77 84 76 90 Q50 95 24 90 Q23 84 29 81 Q34 79 33 75 Z','porcelain':'M35 75 Q50 72 65 75 Q65 79 72 82 Q78 90 71 92 H29 Q22 90 28 82 Q35 79 35 75 Z'}[style]
    # Inline attributes keep all twelve files compatible with the static importer.
    artwork=f'<ellipse cx="50" cy="93" rx="29" ry="3" fill="#000" opacity=".13"/><g fill="url(#body)" stroke="{edge}" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round">{body_path}{HEADS[style][symbol]}{fluting}<path d="{base}"/><path d="M33 75 Q50 71 67 75 L66 79 Q50 76 34 79 Z" fill="url(#rim)"/><path class="engrave" d="M29 85 Q50 89 71 85"/><path class="shine" d="M29 89 Q44 92 57 91"/>'
    if symbol!='N':artwork+='<path d="M37 49 Q50 46 63 49 L61 53 Q50 55 39 53 Z" fill="url(#rim)"/>'
    if style=='porcelain':artwork+=f'<path d="M33 81 Q50 84 67 81" fill="none" stroke="{accent}" stroke-width="2.3"/><path d="M42 72 Q50 74 58 72" fill="none" stroke="{accent}" stroke-width="1.7"/>'
    artwork+='</g>'
    for name,attrs in {
        'engrave':f'fill="none" stroke="{edge}" stroke-width="1.3" opacity=".72"',
        'shine':f'fill="none" stroke="{shine}" stroke-width="1.8" opacity=".65"',
        'cut':f'fill="none" stroke="{edge}" stroke-width="3.5"',
        'feature':f'fill="{edge}" stroke="none"'}.items():artwork=artwork.replace(f'class="{name}"',attrs)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><title>{title}</title>{defs}{artwork}</svg>\n'

def generate(root):
    for style in NAMES:
        folder=Path(root)/style;folder.mkdir(parents=True,exist_ok=True)
        for side in 'wb':
            for symbol in PIECES:(folder/f'{side}{symbol}.svg').write_text(piece_svg(style,side,symbol),encoding='utf-8')

if __name__=='__main__':generate(Path(__file__).resolve().parents[1]/'ui'/'pieces')
