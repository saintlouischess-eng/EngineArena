"""Generate bundled SVG assets from source; Studio/Outline paths are original."""
from pathlib import Path
import chess
import chess.svg

root=Path(__file__).resolve().parent.parent/'ui'/'pieces'
shapes={
'P':'<circle cx="22.5" cy="10" r="6"/><path d="M18 16 Q22.5 18 27 16 L29 30 H16 Z"/><path d="M14 31 H31 L33 37 H12 Z"/>',
'R':'<path d="M11 7 H16 V12 H20 V7 H25 V12 H29 V7 H34 V18 L30 21 V31 H15 V21 L11 18 Z"/><path d="M13 32 H32 L34 38 H11 Z"/><path d="M15 20 H30 M15 28 H30" fill="none"/>',
'N':'<path d="M12 33 Q12 23 22 18 L15 21 L9 17 L17 7 L26 6 L29 11 Q37 19 32 32 Z"/><path d="M13 33 H32 L34 38 H11 Z"/><path d="M17 7 L20 3 L22 7 M27 12 Q22 15 21 23" fill="none"/><circle cx="20" cy="12" r="1.2" fill="currentColor"/>',
'B':'<path d="M22.5 5 Q35 15 26 23 L29 31 H16 L19 23 Q10 15 22.5 5 Z"/><path d="M24 10 L20 17" fill="none"/><circle cx="22.5" cy="4" r="2"/><path d="M13 32 H32 L34 38 H11 Z"/>',
'Q':'<path d="M11 13 L17 23 L22.5 10 L28 23 L34 13 L30 31 H15 Z"/><circle cx="10" cy="11" r="2.5"/><circle cx="22.5" cy="7" r="2.5"/><circle cx="35" cy="11" r="2.5"/><path d="M14 32 H31 L34 38 H11 Z M15 27 H30"/>',
'K':'<path d="M20 4 H25 V8 H29 V12 H25 V17 H20 V12 H16 V8 H20 Z"/><path d="M22.5 18 Q11 12 10 22 Q10 28 16 31 H29 Q35 28 35 22 Q34 12 22.5 18 Z"/><path d="M14 32 H31 L34 38 H11 Z M22.5 18 V29"/>'
}
geometric={
'P':'<circle cx="22.5" cy="11" r="6"/><path d="M19 19 H26 L29 31 H16 Z"/><rect x="12" y="34" width="21" height="4" rx="2"/>',
'R':'<path d="M12 7 H17 V12 H20 V7 H25 V12 H28 V7 H33 V19 H29 V31 H16 V19 H12 Z"/><rect x="12" y="34" width="21" height="4" rx="1"/>',
'N':'<path d="M13 31 L19 22 L10 19 L18 8 L25 5 L30 12 L33 31 Z"/><path d="M18 8 L18 4 L23 7 M27 16 L24 29" fill="none"/><circle cx="21" cy="13" r="1.2" fill="currentColor"/><rect x="12" y="34" width="21" height="4" rx="1"/>',
'B':'<path d="M22.5 5 L31 16 L25 24 L29 31 H16 L20 24 L14 16 Z"/><path d="M25 11 L20 18" fill="none"/><rect x="12" y="34" width="21" height="4" rx="1"/>',
'Q':'<path d="M10 12 L17 20 L22.5 8 L28 20 L35 12 L29 31 H16 Z"/><circle cx="10" cy="9" r="2"/><circle cx="22.5" cy="5" r="2"/><circle cx="35" cy="9" r="2"/><rect x="12" y="34" width="21" height="4" rx="1"/>',
'K':'<path d="M20 4 H25 V9 H30 V13 H25 V18 H20 V13 H15 V9 H20 Z"/><path d="M14 21 H31 L27 31 H18 Z"/><rect x="12" y="34" width="21" height="4" rx="1"/>'}
modern={
'P':'<circle cx="22.5" cy="10" r="5.5"/><path d="M18 17 H27 Q24 25 30 32 H15 Q21 25 18 17 Z"/><path d="M12 36 Q22.5 31 33 36 V39 H12 Z"/>',
'R':'<path d="M11 7 H16 V11 H20 V7 H25 V11 H29 V7 H34 V17 H29 Q25 23 30 32 H15 Q20 23 16 17 H11 Z"/><path d="M12 36 Q22.5 31 33 36 V39 H12 Z M16 17 H29"/>',
'N':'<path d="M13 32 Q14 24 23 21 L13 24 L9 19 L17 10 L19 5 L24 9 Q36 13 32 32 Z"/><path d="M25 12 Q30 21 24 29" fill="none"/><circle cx="21" cy="15" r="1.1" fill="currentColor"/><path d="M12 36 Q22.5 31 33 36 V39 H12 Z"/>',
'B':'<circle cx="22.5" cy="4.5" r="2"/><path d="M22.5 7 Q35 17 25 23 Q25 28 30 32 H15 Q20 28 20 23 Q10 17 22.5 7 Z"/><path d="M25 11 L20 18" fill="none"/><path d="M12 36 Q22.5 31 33 36 V39 H12 Z"/>',
'Q':'<path d="M10 13 Q16 20 17 13 L22.5 20 L28 13 Q29 20 35 13 L28 25 Q27 29 30 32 H15 Q18 29 17 25 Z"/><circle cx="10" cy="10" r="2"/><circle cx="17" cy="10" r="2"/><circle cx="22.5" cy="6" r="2"/><circle cx="28" cy="10" r="2"/><circle cx="35" cy="10" r="2"/><path d="M12 36 Q22.5 31 33 36 V39 H12 Z"/>',
'K':'<path d="M22.5 3 V15 M17 8 H28" fill="none" stroke-width="3"/><path d="M22.5 19 Q14 10 11 18 Q8 25 18 27 L15 32 H30 L27 27 Q37 25 34 18 Q31 10 22.5 19 Z"/><path d="M22.5 19 V27" fill="none"/><path d="M12 36 Q22.5 31 33 36 V39 H12 Z"/>'}
for style in ('classic','studio','outline','geometric','modern','walnut'):
    directory=root/style;directory.mkdir(parents=True,exist_ok=True)
    for side,color in (('w',chess.WHITE),('b',chess.BLACK)):
        for symbol in 'KQRBNP':
            if style in ('classic','walnut'):
                svg=chess.svg.piece(chess.Piece.from_symbol(symbol if color else symbol.lower()))
                if style=='walnut':
                    svg=svg.replace('#ffffff','#f0ddba').replace('#000000','#633c28').replace('fill="#fff"','fill="#f0ddba"').replace('fill="#000"','fill="#633c28"').replace('stroke="#000"','stroke="#38251d"').replace('stroke="#fff"','stroke="#f0ddba"')
            else:
                fill='#f7f4e9' if color else '#17252c';stroke='#243c42' if color else '#e9f0ed'
                if style=='outline':fill='#f5edcc' if color else '#415c69';stroke='#1f3540' if color else '#b1d0da'
                paths=geometric if style=='geometric' else modern if style=='modern' else shapes
                svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 45 45"><g fill="{fill}" stroke="{stroke}" color="{stroke}" stroke-width="{1.6 if style!="outline" else 2.4}" stroke-linejoin="round" stroke-linecap="round">{paths[symbol]}</g></svg>'
            (directory/(side+symbol+'.svg')).write_text(svg,encoding='utf-8')
