"""Opening inventories; transpositions and move counters are not new positions."""
from pathlib import Path
import chess
import chess.pgn
import chess.polyglot


def position_key(board):
    return ' '.join(board.fen(en_passant='legal').split()[:4])


def unique_openings(items, chess960=False):
    seen=set(); result=[]
    for item in items:
        board=chess.Board(item['fen'],chess960=chess960)
        if not board.is_valid():raise ValueError('Invalid opening position: '+item['fen'])
        key=position_key(board)
        if key not in seen:seen.add(key);result.append(dict(item))
    if not result:raise ValueError('No opening positions found')
    return result


def inspect_openings(path, depth=16, chess960=False):
    if not isinstance(depth,int) or isinstance(depth,bool) or depth<0:
        raise ValueError('Book depth must be a non-negative whole number of plies')
    p=Path(path); items=[]; source_count=0; visited_count=0
    if p.suffix.lower()=='.bin':
        # Visit every reachable positive-weight legal branch, merging
        # transpositions at the same depth. No random sample or 100-line cap.
        seen=set(); terminal=set(); stack=[(chess.Board(chess960=chess960),0)]
        with chess.polyglot.open_reader(p) as book:
            while stack:
                board,ply=stack.pop();key=position_key(board)
                if (key,ply) in seen:continue
                seen.add((key,ply));visited_count+=1
                moves=sorted({e.move for e in book.find_all(board)},key=lambda m:m.uci()) if ply<depth else []
                if not moves or ply==depth:
                    if ply==0 and depth and not moves:raise ValueError('No playable positive-weight book entries from the initial position')
                    source_count+=1
                    if key not in terminal:
                        terminal.add(key);items.append({'fen':board.fen(),'name':f'{p.name} position {len(items)+1}', 'start_fen':board.root().fen(),'moves':[m.uci() for m in board.move_stack]})
                else:
                    for move in reversed(moves):
                        child=board.copy();child.push(move);stack.append((child,ply+1))
        result=items
    else:
        if p.suffix.lower()=='.pgn':
            with p.open(encoding='utf-8-sig',errors='strict') as f:
                while game:=chess.pgn.read_game(f):
                    if game.errors:raise ValueError('Invalid PGN: '+str(game.errors[0]))
                    board=game.board();board.chess960=chess960 or board.chess960
                    for i,move in enumerate(game.mainline_moves()):
                        if i>=depth:break
                        board.push(move)
                    items.append({'fen':board.fen(),'name':game.headers.get('Opening',p.name),'eco':game.headers.get('ECO',''),'variation':game.headers.get('Variation',''),'start_fen':board.root().fen(),'moves':[m.uci() for m in board.move_stack]})
        else:
            with p.open(encoding='utf-8-sig') as f:
                for line in f:
                    if not line.strip() or line.lstrip().startswith('#'):continue
                    board=chess.Board(chess960=chess960)
                    if p.suffix.lower()=='.epd':name=board.set_epd(line).get('id',p.name)
                    else:board.set_fen(line.strip());name=p.name
                    items.append({'fen':board.fen(),'name':name})
        source_count=len(items);result=unique_openings(items,chess960)
    if not result:raise ValueError('No opening positions found')
    return {'items':result,'unique_positions':len(result),'source_positions':source_count,
            'duplicates_removed':source_count-len(result),'visited_positions':visited_count,
            'kind':'polyglot' if p.suffix.lower()=='.bin' else p.suffix.lower().lstrip('.'),
            'depth':depth,'exact':True}


def load_openings(path,depth=16,seed=7970,chess960=False):
    return inspect_openings(path,depth,chess960)['items']
