"""Original Engine Arena SVG drawings, GPL-3.0-or-later.

Classic Sculpted is a new Staunton interpretation, not a recolor or tracing of
the bundled Classic assets. Aurora uses flowing profiles; Citadel uses facets.
All shading is static vector geometry. No fonts, images, filters or downloads.
"""
from pathlib import Path

NAMES = {'classic-sculpted': 'Classic Sculpted', 'aurora': 'Aurora', 'citadel': 'Citadel'}
PIECES = {'K': 'king', 'Q': 'queen', 'R': 'rook', 'B': 'bishop', 'N': 'knight', 'P': 'pawn'}

# shadow, lit face, middle, dark face, outline, light engraving, dark engraving
PALETTES = {
    'classic-sculpted': (
        ('#b8ab94', '#fffdf4', '#e8e0ce', '#9c8b72', '#403a32', '#ffffff', '#80705b'),
        ('#10161c', '#63717c', '#25323d', '#0b131b', '#93a0a7', '#bdcbd2', '#080f16')),
    'aurora': (
        ('#b7c6c9', '#ffffff', '#e5eff0', '#96acb5', '#3a5360', '#ffffff', '#7594a2'),
        ('#101b32', '#7187a9', '#293d60', '#111d36', '#9bafc8', '#c0d7f1', '#0c1830')),
    'citadel': (
        ('#b8a88a', '#fff7de', '#e3d4b4', '#a59271', '#493d2d', '#fffbed', '#8b724c'),
        ('#141b20', '#677779', '#2f4045', '#142329', '#a2b0aa', '#cad7cb', '#0b191e')),
}


def line(d, kind='incise', width=1.5, opacity=1):
    return f'<path d="{d}" fill="none" stroke="{{{kind}}}" stroke-width="{width}" opacity="{opacity}"/>'


def path(d, fill='body', **attrs):
    extra = ''.join(f' {k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    return f'<path d="{d}" fill="url(#{fill})"{extra}/>'


def circle(x, y, r, fill='pearl'):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="url(#{fill})"/>'


CLASSIC_HEADS = {
    'K': path('M74 8 H86 V21 H97 V31 H86 V59 H74 V31 H63 V21 H74 Z', 'rim')
         + line('M78 12 V26 H68 M78 26 V39', 'shine', 1.3, .75)
         + path('M80 56 C70 39 48 39 48 54 C47 66 58 71 62 80 H98 C102 71 113 66 112 54 C112 39 90 39 80 56 Z')
         + line('M80 56 V73 M57 51 C53 58 59 65 64 68', 'shine', 2, .7)
         + line('M103 53 Q106 61 97 69 M65 75 Q80 71 95 75'),
    'Q': path('M43 37 L55 62 L62 29 L71 59 L80 20 L89 59 L98 29 L105 62 L117 37 L104 78 Q80 86 56 78 Z')
         + ''.join(circle(x, y, r) for x, y, r in [(41,30,6),(61,23,5.5),(80,14,6),(99,23,5.5),(119,30,6)])
         + path('M56 70 Q80 77 104 70 L102 79 Q80 86 58 79 Z', 'rim')
         + line('M63 39 L68 62 M80 31 V57 M97 39 L92 62', 'shine', 1.8, .85)
         + line('M60 76 Q80 82 100 76'),
    'B': circle(80, 18, 5)
         + path('M80 25 C74 39 51 46 53 62 C54 75 69 83 80 83 C91 83 106 75 107 62 C109 46 86 39 80 25 Z')
         + line('M89 39 L71 61', 'incise', 5)
         + line('M92 40 L74 63', 'shine', 1.7, .9)
         + line('M69 43 C57 52 58 64 64 68', 'shine', 2.2, .85)
         + line('M62 72 Q80 81 98 72'),
    'N': path('M46 117 C45 99 52 86 67 71 L49 78 C41 80 33 75 29 66 L31 59 L48 44 L58 37 L59 20 L71 31 L81 26 L89 32 C108 34 123 54 124 75 C126 94 117 109 113 119 Z')
         + path('M88 34 C108 40 116 57 115 75 C114 92 105 106 97 116 H111 C125 94 129 66 113 46 Q102 33 88 34 Z', 'shade', stroke='none')
         + line('M87 38 C104 45 110 63 103 80 C99 92 88 103 81 110', 'incise', 2.2)
         + line('M94 43 L103 40 M101 51 L111 48 M105 61 L117 59 M105 72 L119 72 M102 83 L116 87 M96 94 L110 101', 'shine', 1.8, .75)
         + line('M68 43 C80 48 78 60 70 69 C58 82 53 99 54 108', 'shine', 2.5, .85)
         + path('M61 49 Q69 44 75 48 L70 55 L64 55 Z', 'shade')
         + line('M64 48 L72 48', 'shine', 1.2)
         + circle(39, 63, 2, 'shade')
         + line('M34 70 Q40 75 48 72 M47 56 L54 52 M62 25 L64 37 M54 88 Q70 90 77 84', 'incise', 1.7),
    'R': path('M42 31 H57 V45 H67 V31 H93 V45 H103 V31 H118 V61 L106 73 H54 L42 61 Z')
         + path('M42 55 H118 V62 L106 73 H54 L42 62 Z', 'rim')
         + line('M48 35 H53 V47 M72 35 H88 M108 35 H113 V47', 'shine', 1.4)
         + line('M48 61 H112 M57 69 H103', 'incise', 1.8),
    'P': circle(80, 58, 19)
         + line('M68 50 Q72 42 83 44', 'shine', 2.5, .85)
         + path('M65 77 Q80 73 95 77 L98 83 Q80 91 62 83 Z', 'rim'),
}

AURORA_HEADS = {
    'K': path('M75 9 Q80 6 85 9 V23 Q92 20 97 24 V32 Q91 35 85 32 V66 H75 V32 Q69 35 63 32 V24 Q69 20 75 23 Z', 'rim')
         + path('M80 63 C71 42 43 37 42 51 C41 65 61 79 80 84 C99 79 119 65 118 51 C117 37 89 42 80 63 Z')
         + line('M50 50 C48 60 66 68 80 77 C94 68 112 60 110 50', 'shine', 2.1, .85)
         + line('M80 63 V78 M69 46 Q73 50 75 56'),
    'Q': path('M80 21 C70 36 70 52 80 69 C64 56 61 36 53 29 C45 45 50 61 59 72 C44 68 41 53 32 49 C31 69 44 84 63 87 H97 C116 84 129 69 128 49 C119 53 116 68 101 72 C110 61 115 45 107 29 C99 36 96 56 80 69 C90 52 90 36 80 21 Z')
         + circle(80, 15, 5) + circle(52, 25, 4) + circle(108, 25, 4)
         + line('M79 32 Q73 46 79 57 M52 42 Q52 58 67 73 M108 42 Q108 58 93 73', 'shine', 1.8, .9)
         + path('M59 78 Q80 85 101 78 L99 87 Q80 93 61 87 Z', 'rim'),
    'B': circle(80, 18, 4.5)
         + path('M80 27 C79 39 52 43 50 60 C48 77 62 87 80 86 C98 87 112 77 110 60 C108 43 81 39 80 27 Z')
         + line('M91 42 Q78 48 71 65', 'incise', 4.8)
         + line('M94 43 Q81 50 74 67', 'shine', 1.6)
         + line('M65 47 C53 56 55 70 65 74', 'shine', 2.2, .85)
         + line('M64 79 Q80 86 96 79'),
    'N': path('M45 120 C41 102 56 83 72 70 C62 72 56 80 47 79 C37 79 28 73 28 65 C28 58 38 52 46 45 L58 38 Q57 23 63 20 L73 33 Q96 24 113 42 C132 62 127 99 110 120 Z')
         + path('M91 37 C112 41 123 60 117 79 C111 99 93 111 79 117 H109 C127 96 131 63 112 43 Q102 35 91 37 Z', 'shade', stroke='none')
         + line('M82 38 C113 45 109 75 91 93 C80 104 69 106 63 114', 'shine', 2.4, .8)
         + line('M88 43 C104 51 106 67 97 81 M105 42 C116 57 117 71 109 87 M67 77 C51 91 48 106 53 113', 'incise', 1.7)
         + path('M63 49 Q72 44 77 50 Q71 56 64 55 Z', 'shade')
         + line('M65 49 L73 49', 'shine', 1.2)
         + circle(38, 64, 1.8, 'shade')
         + line('M33 72 Q42 76 49 72 M61 25 L65 37 M46 56 L52 51', 'incise', 1.6),
    'R': path('M40 34 Q40 29 46 29 H58 V45 H68 V33 H92 V45 H102 V29 H114 Q120 29 120 34 V57 C120 70 102 76 80 76 C58 76 40 70 40 57 Z')
         + path('M40 57 Q80 68 120 57 Q118 72 104 76 H56 Q42 72 40 57 Z', 'rim')
         + line('M46 36 V52 M74 38 H86 M111 36 V51', 'shine', 1.8)
         + line('M51 65 Q80 74 109 65'),
    'P': '<ellipse cx="80" cy="58" rx="19" ry="21" fill="url(#pearl)"/>'
         + line('M68 51 Q71 41 82 43', 'shine', 2.2, .9)
         + path('M64 79 Q80 74 96 79 Q100 86 90 90 H70 Q60 86 64 79 Z', 'rim'),
}

CITADEL_HEADS = {
    'K': path('M74 7 H86 V21 H99 V33 H86 V63 H74 V33 H61 V21 H74 Z')
         + path('M77 10 H83 V24 H95 L91 28 H83 V57 H77 Z', 'rim', stroke='none')
         + path('M43 50 L57 43 L80 60 L103 43 L117 50 L106 80 H54 Z')
         + path('M47 51 L57 48 L80 65 L103 48 L113 51 L102 70 H58 Z', 'rim', stroke='none')
         + line('M80 65 V77 M57 74 H103'),
    'Q': path('M34 36 L50 60 L58 25 L68 55 L80 16 L92 55 L102 25 L110 60 L126 36 L110 81 H50 Z')
         + ''.join(path(f'M{x} {y-5} L{x+5} {y} L{x} {y+5} L{x-5} {y} Z', 'rim') for x,y in [(33,31),(58,20),(80,11),(102,20),(127,31)])
         + path('M50 69 L80 75 L110 69 V81 L80 87 L50 81 Z', 'rim')
         + line('M61 39 L69 62 M99 39 L91 62 M80 26 V50', 'shine', 1.8)
         + line('M55 77 L80 82 L105 77'),
    'B': path('M80 17 L88 25 L84 33 L108 57 L99 76 L80 87 L61 76 L52 57 L76 33 L72 25 Z')
         + path('M80 36 L58 58 L66 71 L80 78 Z', 'rim', stroke='none')
         + path('M83 39 L101 57 L94 71 L83 78 Z', 'shade', stroke='none')
         + line('M90 42 L70 64', 'incise', 4.5)
         + line('M93 44 L73 66', 'shine', 1.4)
         + line('M64 76 L80 83 L96 76'),
    'N': path('M43 118 L48 97 L68 73 L47 80 L28 70 L29 60 L47 42 L58 37 L59 20 L73 31 L85 25 L98 33 L116 48 L127 71 L124 95 L112 120 Z')
         + path('M85 32 L104 49 L113 72 L106 96 L91 117 H111 L120 94 L123 73 L113 52 L96 37 Z', 'shade', stroke='none')
         + path('M61 81 L80 64 L82 50 L73 41 L70 57 L51 70 L42 67 L48 75 L67 68 L48 100 L47 113 L56 112 Z', 'rim', stroke='none')
         + line('M92 37 L87 46 L105 54 L99 64 L115 73 L105 83 L116 94 L104 102 L109 115', 'shine', 1.8, .8)
         + path('M61 49 L76 47 L70 56 H63 Z', 'shade')
         + line('M63 49 H71', 'shine', 1.2)
         + path('M35 61 L41 59 L41 64 L35 65 Z', 'shade')
         + line('M34 71 L44 73 M62 26 L65 37 M55 102 L76 89', 'incise', 1.7),
    'R': path('M37 30 H56 V44 H67 V30 H93 V44 H104 V30 H123 V60 L110 75 H50 L37 60 Z')
         + path('M41 55 H119 V61 L108 72 H52 L41 61 Z', 'rim', stroke='none')
         + line('M43 35 H51 V47 M73 35 H87 M110 35 H117 V47', 'shine', 1.6)
         + line('M46 62 H114 M54 69 H106'),
    'P': path('M80 39 L96 48 L100 64 L89 78 H71 L60 64 L64 48 Z')
         + path('M80 43 L67 50 L64 62 L78 59 Z', 'rim', stroke='none')
         + path('M83 43 L94 51 L96 62 L83 60 Z', 'body', stroke='none')
         + path('M64 65 L79 62 L94 65 L87 74 H73 Z', 'shade', stroke='none')
         + path('M67 80 H93 L98 86 L91 92 H69 L62 86 Z', 'rim'),
}

HEADS = {'classic-sculpted': CLASSIC_HEADS, 'aurora': AURORA_HEADS, 'citadel': CITADEL_HEADS}


def torso(style, symbol):
    if symbol == 'N':
        return path('M48 111 H112 L108 126 H52 Z')
    if style == 'classic-sculpted':
        if symbol == 'R':
            return path('M55 70 H105 L100 109 L109 121 H51 L60 109 Z') + line('M64 78 L66 106', 'shine', 2.3, .7) + line('M96 78 L94 106')
        top = 86 if symbol == 'P' else 79
        return path(f'M64 {top} H96 C90 93 91 106 103 117 L104 122 H56 L57 117 C69 106 70 93 64 {top} Z') + line('M72 91 C76 104 69 113 64 116', 'shine', 2.2, .8) + line('M88 92 Q85 105 94 115', 'incise', 1.4, .6)
    if style == 'aurora':
        if symbol == 'R':
            return path('M55 72 H105 C99 87 96 103 108 119 Q80 127 52 119 C64 103 61 87 55 72 Z') + line('M65 80 C71 95 61 109 61 115', 'shine', 2.1) + line('M96 81 Q89 98 101 115')
        top = 87 if symbol == 'P' else 83
        return path(f'M63 {top} H97 C91 94 88 100 97 109 Q108 119 99 124 H61 Q52 119 63 109 C72 100 69 94 63 {top} Z') + line('M72 94 Q80 102 70 113 Q66 118 71 120', 'shine', 2.5, .8) + line('M89 93 Q81 104 92 116')
    if symbol == 'R':
        return path('M52 73 H108 L102 108 L112 121 H48 L58 108 Z') + path('M57 76 H69 L70 107 L58 116 H54 L63 106 Z', 'rim', stroke='none') + path('M91 76 H103 L97 108 L105 116 H90 Z', 'shade', stroke='none')
    top = 90 if symbol == 'P' else 83
    return path(f'M62 {top} H98 L92 101 L104 120 L99 125 H61 L56 120 L68 101 Z') + path(f'M67 {top+3} H78 L76 102 L65 119 H61 L73 101 Z', 'rim', stroke='none') + path(f'M84 {top+3} H93 L87 102 L97 119 H87 L81 103 Z', 'shade', stroke='none')


def foot(style, symbol):
    if style == 'classic-sculpted':
        art = path('M54 118 Q80 113 106 118 L110 125 Q120 128 124 138 L123 146 Q80 153 37 146 L36 138 Q40 128 50 125 Z')
        art += path('M53 117 Q80 112 107 117 L108 124 Q80 130 52 124 Z', 'rim')
        art += path('M41 133 Q80 140 119 133 L123 139 Q80 148 37 139 Z', 'rim')
        art += line('M43 144 Q80 150 117 144', 'incise', 1.5) + line('M45 135 Q70 139 90 138', 'shine', 1.8, .9)
    elif style == 'aurora':
        art = path('M56 120 Q80 113 104 120 C106 128 124 126 125 138 Q128 150 80 151 Q32 150 35 138 C36 126 54 128 56 120 Z')
        art += path('M56 120 Q80 113 104 120 Q105 125 100 127 Q80 133 60 127 Q55 125 56 120 Z', 'rim')
        art += line('M42 134 C54 129 64 143 80 143 C96 143 106 129 118 134', 'shine', 2, .9)
        art += line('M41 142 Q80 154 119 142', 'incise', 1.6)
        art += line('M52 146 Q76 151 95 146', 'shine', 1.6, .65)
    else:
        art = path('M55 119 H105 L111 126 L123 133 V144 L114 150 H46 L37 144 V133 L49 126 Z')
        art += path('M55 120 H105 L108 125 L99 130 H61 L52 125 Z', 'rim')
        art += path('M49 130 L61 134 H99 L111 130 L120 135 L108 141 H52 L40 135 Z', 'rim', stroke='none')
        art += path('M40 139 L53 145 H107 L120 139 V143 L113 147 H47 L40 143 Z', 'shade', stroke='none')
        art += line('M47 133 L57 137 H101', 'shine', 1.5, .9) + line('M57 145 H103', 'shine', 1.2, .6)
    if symbol != 'N':
        y = 88 if symbol == 'P' else 80 if symbol != 'R' else 73
        if style == 'citadel':
            art += path(f'M56 {y} H104 L106 {y+5} L98 {y+9} H62 L54 {y+5} Z', 'rim')
            art += line(f'M61 {y+4} H99', 'shine', 1.3, .8)
        else:
            art += path(f'M58 {y} Q80 {y-6} 102 {y} L101 {y+6} Q80 {y+12} 59 {y+6} Z', 'rim')
            art += line(f'M64 {y+3} Q80 {y+6} 96 {y+3}', 'shine', 1.3, .8)
    # A pawn's narrower plinth and head make it distinct even in a thumbnail.
    return art


def piece_svg(style, side, symbol):
    low, lit, mid, dark, edge, shine, incise = PALETTES[style][side == 'b']
    defs = f'''<defs>
<linearGradient id="body" x1="0" y1="0" x2="1" y2=".12"><stop stop-color="{low}"/><stop offset=".23" stop-color="{lit}"/><stop offset=".46" stop-color="{mid}"/><stop offset=".78" stop-color="{dark}"/><stop offset="1" stop-color="{low}"/></linearGradient>
<linearGradient id="rim" x1="0" y1="0" x2=".15" y2="1"><stop stop-color="{lit}"/><stop offset=".28" stop-color="{mid}"/><stop offset=".75" stop-color="{low}"/><stop offset="1" stop-color="{dark}"/></linearGradient>
<linearGradient id="shade"><stop stop-color="{mid}"/><stop offset=".6" stop-color="{dark}"/><stop offset="1" stop-color="{low}"/></linearGradient>
<radialGradient id="pearl" cx=".32" cy=".23" r=".8"><stop stop-color="{lit}"/><stop offset=".36" stop-color="{mid}"/><stop offset=".8" stop-color="{dark}"/><stop offset="1" stop-color="{low}"/></radialGradient>
</defs>'''
    artwork = torso(style, symbol) + HEADS[style][symbol] + foot(style, symbol)
    artwork = artwork.replace('{shine}', shine).replace('{incise}', incise)
    # Consistent baseline, deliberately staggered head heights and base widths.
    scale = '.86' if symbol == 'P' else '.94' if symbol == 'B' else '1'
    transform = f'translate(80 150) scale({scale} 1) translate(-80 -150)'
    name = f'{NAMES[style]} — {"White" if side == "w" else "Black"} {PIECES[symbol]}'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 160" role="img" aria-labelledby="title">
<title id="title">{name}</title>
<desc>Original Engine Arena drawing. Self-contained static vector artwork, GPL-3.0-or-later.</desc>
{defs}
<g transform="{transform}"><ellipse cx="80" cy="151" rx="47" ry="4" fill="#000" opacity=".14"/>
<g fill="url(#body)" stroke="{edge}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{artwork}</g></g>
</svg>
'''


def generate(root):
    for style in NAMES:
        folder = Path(root) / style
        folder.mkdir(parents=True, exist_ok=True)
        for side in 'wb':
            for symbol in PIECES:
                (folder / f'{side}{symbol}.svg').write_text(piece_svg(style, side, symbol), encoding='utf-8')


if __name__ == '__main__':
    generate(Path(__file__).resolve().parents[1] / 'ui' / 'pieces')
