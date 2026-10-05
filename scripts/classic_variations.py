"""Three diagram-style redraws of the Classic family, GPL-3.0-or-later.

Design reference: Colin M. L. Burnett's Classic chessmen bundled by python-chess.
These new Bezier drawings retain that family's familiar two-dimensional forms.
Each collection has separate silhouettes, not a palette swap. Flat vector fills,
optically balanced outlines and contrasting inner cuts remain clear on small boards.
No fonts, raster images, filters, external references or runtime dependencies.
"""
from pathlib import Path

NAMES = {'classic-refined': 'Classic Refined', 'classic-bold': 'Classic Bold',
         'classic-heritage': 'Classic Heritage'}
PIECES = {'K': 'king', 'Q': 'queen', 'R': 'rook', 'B': 'bishop', 'N': 'knight', 'P': 'pawn'}


def shape(d):
    return f'<path d="{d}" fill="{{body}}" stroke="{{edge}}"/>'


def cut(d, width=None):
    weight = f' stroke-width="{width}"' if width else ''
    return f'<path d="{d}" fill="none" stroke="{{cut}}"{weight}/>'


def bead(x, y, r):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{{body}}" stroke="{{edge}}"/>'


def eye(x, y, angle=-28):
    return f'<ellipse cx="{x}" cy="{y}" rx="1.8" ry="3.1" transform="rotate({angle} {x} {y})" fill="{{cut}}" stroke="none"/>'


def dot(x, y, r=1.4):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{{cut}}" stroke="none"/>'


REFINED = {
    'K': cut('M50 11 V25 M44 16 H56', 3.2).replace('{cut}', '{edge}')
         + shape('M50 59 C46 52 42 42 43 36 C44 30 47 27 50 27 C53 27 56 30 57 36 C58 42 54 52 50 59 Z')
         + shape('M50 58 C44 42 29 34 19 38 C9 42 9 52 13 59 C16 64 21 68 26 71 V86 C40 94 60 94 74 86 V71 C79 68 84 64 87 59 C91 52 91 42 81 38 C71 34 56 42 50 58 Z')
         + cut('M50 58 V68 M26 71 C40 65 60 65 74 71 M26 78 C40 72 60 72 74 78 M26 85 C40 79 60 79 74 85', 2.7)
         + '<g class="dark-detail">' + cut('M21 43 C13 47 16 58 26 64 M79 43 C87 47 84 58 74 64', 2.4) + '</g>',
    'Q': shape('M19 62 L14 31 L31 56 L30 24 L43 55 L50 20 L57 55 L70 24 L69 56 L86 31 L81 62 C63 67 37 67 19 62 Z')
         + ''.join(bead(x, y, r) for x, y, r in [(13,26,4.5),(30,19,4.4),(50,14,4.7),(70,19,4.4),(87,26,4.5)])
         + shape('M19 62 C38 57 62 57 81 62 C81 67 77 69 75 74 C73 77 73 81 76 85 L78 89 C62 94 38 94 22 89 L24 85 C27 81 27 77 25 74 C23 69 19 67 19 62 Z')
         + cut('M25 73 C41 69 59 69 75 73 M26 81 C42 78 58 78 74 81 M24 87 C41 84 59 84 76 87', 2.6),
    'R': shape('M24 22 H35 V31 H44 V22 H56 V31 H65 V22 H76 V43 L69 50 V72 L74 79 V85 H80 V92 H20 V85 H26 V79 L31 72 V50 L24 43 Z')
         + cut('M24 42 H76 M31 50 H69 M31 72 H69 M26 79 H74 M26 85 H74', 2.6),
    'B': shape('M20 83 C29 81 40 84 50 78 C60 84 71 81 80 83 C85 84 88 87 89 89 C87 92 84 92 79 90 C70 87 61 92 50 87 C39 92 30 87 21 90 C16 92 13 92 11 89 C12 87 15 84 20 83 Z')
         + shape('M34 73 C34 68 37 63 41 60 C34 58 30 52 31 44 C32 36 39 30 50 25 C61 30 68 36 69 44 C70 52 66 58 59 60 C63 63 66 68 66 73 L66 77 C58 82 42 82 34 77 Z')
         + bead(50,18,5.3)
         + cut('M50 36 V48 M44 42 H56 M41 60 H59 M35 71 H65', 2.8),
    'N': shape('M50 25 C73 25 86 43 86 72 L86 92 H33 C33 80 38 74 45 65 C51 58 55 49 53 42 L50 25 Z')
         + shape('M53 42 C53 48 44 55 37 61 C34 64 32 67 28 68 L24 65 C21 68 16 68 14 63 C12 59 15 54 18 49 L27 35 C30 32 32 29 32 25 L30 18 C34 18 38 22 40 25 H44 C45 20 48 17 51 16 L52 25')
         + cut('M57 31 C72 37 79 53 79 78', 2.6)
         + cut('M25 59 L20 61 M34 29 L35 25', 2.3)
         + eye(34,39) + dot(20,55),
    'P': shape('M50 29 C44 29 40 34 40 40 C40 43 41 45 43 47 C35 50 32 56 33 63 C34 68 36 71 41 74 C30 80 26 87 26 92 H74 C74 87 70 80 59 74 C64 71 66 68 67 63 C68 56 65 50 57 47 C59 45 60 43 60 40 C60 34 56 29 50 29 Z')
         + cut('M34 84 Q50 80 66 84', 2.4),
}

BOLD = {
    'K': cut('M50 10 V24 M43 16 H57', 4).replace('{cut}', '{edge}')
         + shape('M50 57 C43 46 41 36 44 30 Q50 23 56 30 C59 36 57 46 50 57 Z')
         + shape('M50 57 C43 38 28 32 18 37 C7 42 8 55 14 62 L24 72 V86 Q50 97 76 86 V72 L86 62 C92 55 93 42 82 37 C72 32 57 38 50 57 Z')
         + cut('M50 57 V68 M24 72 Q50 62 76 72 M24 81 Q50 71 76 81', 3.4)
         + '<g class="dark-detail">' + cut('M20 43 Q10 51 25 65 M80 43 Q90 51 75 65', 2.9) + '</g>',
    'Q': shape('M17 63 L13 32 L30 53 L29 25 L42 52 L50 19 L58 52 L71 25 L70 53 L87 32 L83 63 Q50 71 17 63 Z')
         + ''.join(bead(x, y, 4.8) for x, y in [(12,26),(29,19),(50,13),(71,19),(88,26)])
         + shape('M17 63 Q50 56 83 63 Q84 67 77 74 L75 81 L79 90 Q50 97 21 90 L25 81 L23 74 Q16 67 17 63 Z')
         + cut('M24 74 Q50 68 76 74 M25 83 Q50 78 75 83', 3.2),
    'R': shape('M20 21 H34 V31 H43 V21 H57 V31 H66 V21 H80 V44 L71 52 V73 L77 80 V84 H82 V92 H18 V84 H23 V80 L29 73 V52 L20 44 Z')
         + cut('M21 44 H79 M29 52 H71 M29 73 H71 M24 81 H76', 3.3),
    'B': shape('M20 83 C34 80 42 83 50 79 C58 83 66 80 80 83 L87 90 C74 95 63 87 50 92 C37 87 26 95 13 90 Z')
         + shape('M31 75 C31 69 35 64 40 61 C31 58 27 51 29 43 C31 35 40 29 50 24 C60 29 69 35 71 43 C73 51 69 58 60 61 C65 64 69 69 69 75 V79 Q50 85 31 79 Z')
         + bead(50,17,5.6)
         + cut('M58 35 L43 50 M40 61 H60 M33 73 H67', 3.6),
    'N': shape('M49 24 C76 23 87 43 88 69 L89 92 H30 C30 79 36 69 44 61 Q55 49 51 40 Z')
         + shape('M51 41 C51 49 41 54 35 61 L29 69 L23 65 C16 70 11 65 12 59 L18 47 L28 32 Q32 29 31 24 L29 16 Q37 18 40 24 H43 Q46 16 52 15 L53 24')
         + cut('M60 31 C77 38 81 56 81 80', 3.1)
         + cut('M24 59 L18 62 M33 29 L34 25', 2.7)
         + eye(34,38,-35) + dot(19,54,1.7),
    'P': shape('M50 27 C43 27 38 32 38 39 Q38 44 42 47 C34 50 30 56 31 63 Q32 70 40 74 C29 79 23 85 23 92 H77 C77 85 71 79 60 74 Q68 70 69 63 C70 56 66 50 58 47 Q62 44 62 39 C62 32 57 27 50 27 Z')
         + cut('M32 84 Q50 79 68 84', 3),
}

HERITAGE = {
    'K': cut('M50 10 V25 M43.5 16.5 H56.5', 3).replace('{cut}', '{edge}')
         + shape('M50 58 C46 51 41 39 43 33 C45 29 47 26 50 26 C53 26 55 29 57 33 C59 39 54 51 50 58 Z')
         + shape('M50 58 C46 42 33 34 23 35 C10 36 8 47 12 55 C15 62 20 66 25 70 L26 86 C39 94 61 94 74 86 L75 70 C80 66 85 62 88 55 C92 47 90 36 77 35 C67 34 54 42 50 58 Z')
         + cut('M50 58 V67 M25 70 C37 64 63 64 75 70 M26 77 C38 71 62 71 74 77 M27 84 C39 78 61 78 73 84', 2.4)
         + cut('M22 42 C15 43 15 52 21 58 M78 42 C85 43 85 52 79 58', 1.9),
    'Q': shape('M20 63 L13 30 L31 56 L30 22 L43 55 L50 19 L57 55 L70 22 L69 56 L87 30 L80 63 Q50 69 20 63 Z')
         + ''.join(bead(x, y, r) for x, y, r in [(12,25,4),(30,17,4),(50,13,4.5),(70,17,4),(88,25,4)])
         + shape('M20 63 Q50 57 80 63 C81 67 76 70 73 75 Q70 80 75 86 L77 90 Q50 95 23 90 L25 86 Q30 80 27 75 C24 70 19 67 20 63 Z')
         + cut('M26 73 Q50 69 74 73 M28 80 Q50 77 72 80 M25 87 Q50 83 75 87', 2.35)
         + cut('M48 29 L46 43 M33 34 L36 44 M78 44 L75 53', 1.7),
    'R': shape('M24 21 H35 V29 H44 V21 H56 V29 H65 V21 H76 V40 L69 47 V72 L74 78 V84 H80 V92 H20 V84 H26 V78 L31 72 V47 L24 40 Z')
         + cut('M24 40 H76 M31 47 H69 M31 72 H69 M26 79 H74 M26 85 H74', 2.35)
         + cut('M37 53 V66 M63 53 V66', 1.7),
    'B': shape('M20 83 C30 80 40 84 50 78 C60 84 70 80 80 83 L88 89 C82 95 71 86 62 89 L50 91 L38 89 C29 86 18 95 12 89 Z')
         + shape('M34 73 C34 67 37 64 41 61 C32 57 30 51 32 44 C34 36 42 32 50 24 C58 32 66 36 68 44 C70 51 68 57 59 61 C63 64 66 67 66 73 V78 Q50 83 34 78 Z')
         + bead(50,17,5)
         + cut('M50 37 V50 M44 43 H56 M41 61 H59 M35 72 H65', 2.4)
         + cut('M39 44 Q36 50 41 54', 1.7),
    'N': shape('M49 25 C68 23 81 36 85 53 C89 66 87 82 87 92 H33 C33 79 40 71 46 62 C51 54 54 45 51 39 Z')
         + shape('M52 41 C53 48 44 53 38 59 C34 62 31 67 27 68 L23 64 C18 68 13 65 13 60 C13 56 19 48 23 43 L29 34 C32 31 33 28 33 25 L30 17 Q37 18 40 25 H44 C45 20 49 17 52 16 L53 25')
         + cut('M58 30 C76 36 82 53 81 77 M57 38 C67 46 70 58 66 71', 2.25)
         + cut('M41 69 Q46 63 49 56 M24 59 L18 61 M33 29 L35 25', 2)
         + eye(35,39,-24) + dot(19,55,1.35),
    'P': shape('M50 29 C44 29 40 33 40 39 C40 42 41 45 43 47 C36 50 32 56 33 62 C33 68 37 72 41 74 C32 80 27 85 26 92 H74 C73 85 68 80 59 74 C63 72 67 68 67 62 C68 56 64 50 57 47 C59 45 60 42 60 39 C60 33 56 29 50 29 Z')
         + cut('M35 83 Q50 79 65 83 M31 88 Q50 84 69 88', 2.25)
         + cut('M40 55 Q36 60 40 65', 1.7),
}

ART = {'classic-refined': REFINED, 'classic-bold': BOLD, 'classic-heritage': HERITAGE}


def piece_svg(style, side, symbol):
    white = side == 'w'
    edge = '#111318'
    body = '#ffffff' if white else '#111318'
    incision = edge if white else '#ffffff'
    width = {'classic-refined': 3.05, 'classic-bold': 3.7, 'classic-heritage': 2.8}[style]
    artwork = ART[style][symbol]
    if white:
        # White crowns get their shape from the outline; black crowns need an
        # inner light cut so each lobe remains separate on a dark square.
        import re
        artwork = re.sub(r'<g class="dark-detail">.*?</g>', '', artwork)
    artwork = artwork.replace('{body}', body).replace('{edge}', edge).replace('{cut}', incision)
    name = f'{NAMES[style]} — {"White" if white else "Black"} {PIECES[symbol]}'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" role="img" aria-labelledby="title">
<title id="title">{name}</title>
<desc>Engine Arena redraw of the Classic chessmen family. Design reference: Colin M. L. Burnett. GPL-3.0-or-later. Self-contained vector paths.</desc>
<g stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round">{artwork}</g>
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
    # Review-only until the user chooses which designs to install.
    generate(Path(__file__).resolve().parents[1] / 'exports' / 'classic-variations-preview')
