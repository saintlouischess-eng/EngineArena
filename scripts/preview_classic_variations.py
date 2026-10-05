"""Build review sheets directly from the proposed SVGs, without installing sets."""
from pathlib import Path
import re
from classic_variations import NAMES, generate

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'exports' / 'classic-variations-preview'
CAPTIONS = {'classic-refined': 'Clean contours · balanced detail · closest to the reference',
            'classic-bold': 'Stronger silhouettes · wider forms · fewer internal lines',
            'classic-heritage': 'Sweeping curves · fine engraving · traditional character'}


def embed(style, side, piece, x, y, size, small=False, source=OUTPUT):
    text = (source / style / f'{side}{piece}.svg').read_text(encoding='utf-8')
    key = style + side + piece + ('-small' if small else '')
    text = re.sub(r'id="([^"]+)"', lambda m: f'id="{key}-{m[1]}"', text)
    text = re.sub(r'url\(#([^)]+)\)', lambda m: f'url(#{key}-{m[1]})', text)
    text = text.replace('aria-labelledby="title"', f'aria-labelledby="{key}-title"')
    return text.replace('<svg ', f'<svg x="{x}" y="{y}" width="{size}" height="{size}" ', 1)


def sheet(style, source=OUTPUT, caption=None, edition=''):
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="464" viewBox="0 0 1120 464">',
             '<rect width="1120" height="464" rx="18" fill="#17232a"/>',
             '<g font-family="Segoe UI,Arial,sans-serif" fill="#f2f6f5">',
             '<text x="36" y="30" font-size="11" letter-spacing="2.5" fill="#99beb2">ENGINE ARENA / DESIGN PREVIEW</text>',
             f'<text x="36" y="68" font-size="30" font-weight="600">{NAMES[style]}{edition}</text>',
             f'<text x="36" y="95" font-size="15" fill="#afc3c7">{caption or CAPTIONS[style]}</text>',
             '<text x="1080" y="32" text-anchor="end" font-size="12" fill="#afc3c7">NOT ADDED TO THE PROGRAM</text>']
    size = 140
    for row, side in enumerate('wb'):
        y = 113 + row * size
        parts.append(f'<text x="44" y="{y+74}" font-size="13" fill="#afc3c7">{"WHITE" if side=="w" else "BLACK"}</text>')
        for col, piece in enumerate('KQRBNP'):
            x = 140 + col * size
            color = '#dbe3d8' if (row+col)%2==0 else '#80978c'
            parts.append(f'<rect x="{x}" y="{y}" width="{size}" height="{size}" fill="{color}"/>')
            parts.append(embed(style, side, piece, x, y, size, source=source))
    parts.append('<text x="44" y="436" font-size="12" fill="#afc3c7">32 PX</text>')
    for index, (side, piece) in enumerate((s,p) for s in 'wb' for p in 'KQRBNP'):
        x, y = 140 + index * 38, 414
        parts.append(f'<rect x="{x}" y="{y}" width="32" height="32" fill="{"#dbe3d8" if index%2 else "#80978c"}"/>')
        parts.append(embed(style, side, piece, x, y, 32, True, source=source))
    parts.append('<text x="980" y="436" text-anchor="end" font-size="12" fill="#afc3c7">100% vector · both colors · all six pieces</text></g></svg>')
    return '\n'.join(parts)


if __name__ == '__main__':
    generate(OUTPUT)
    for style in NAMES:
        (OUTPUT / (style+'.svg')).write_text(sheet(style), encoding='utf-8')
