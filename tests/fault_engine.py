"""Deliberately faulty UCI peer for acceptance fault injection, never a benchmark."""
import argparse
import os
import random
import sys
import time
from pathlib import Path
import chess

p=argparse.ArgumentParser();p.add_argument('--mode',default='normal');p.add_argument('--wait',type=float,default=0);p.add_argument('--transcript');p.add_argument('--marker');p.add_argument('--bestmove');p.add_argument('--ponder-move');args=p.parse_args()
board=chess.Board();rng=random.Random(7970);pending_ponder=None
def say(line):print(line,flush=True)
for raw in sys.stdin:
    line=raw.strip()
    if args.transcript:
        with open(args.transcript,'a',encoding='utf-8') as f:f.write(line+'\n');f.flush()
    if line=='uci':
        if args.mode=='startup':time.sleep(120)
        say('id name FaultFixture 1.0');say('id author Engine Arena tests')
        for s in ('Threads type spin default 1 min 1 max 256','Hash type spin default 16 min 1 max 65536','Ponder type check default false','UCI_Chess960 type check default false','Style type combo default Normal var Normal var Very Aggressive','Network File type string default <empty>','Clear Hash type button'):
            if args.mode=='no_threads' and s.startswith('Threads '):continue
            say('option name '+s)
        say('uciok')
    elif line=='isready':
        if args.mode=='readiness':time.sleep(120)
        say('readyok')
    elif line.startswith('position '):
        parts=line.split(' moves ');fen=parts[0].removeprefix('position fen ')
        board=chess.Board(fen,chess960=True)
        if len(parts)>1:
            for move in parts[1].split():board.push_uci(move)
    elif line.startswith('go '):
        if args.mode in ('network','network_crash'):
            print('Loading weights file from: '+args.marker,file=sys.stderr,flush=True)
            print('Switching to [cuda-fp16]...',file=sys.stderr,flush=True)
            print('GPU: Synthetic GPU',file=sys.stderr,flush=True)
            if args.mode=='network_crash':
                print('Unhandled exception: CUBLAS_STATUS_INTERNAL_ERROR',file=sys.stderr,flush=True);time.sleep(.05);os._exit(17)
        if args.mode=='strict_nodes' and (not line.startswith('go nodes ') or len(line.split())!=3):say('bestmove a1a1');continue
        if args.mode=='crash':os._exit(17)
        if args.mode=='crash_once' and args.marker and not Path(args.marker).exists():Path(args.marker).write_text('crashed');os._exit(17)
        if args.mode=='timeout_once' and args.marker and not Path(args.marker).exists():Path(args.marker).write_text('timed out');time.sleep(120)
        if args.mode in ('hang','timeout'):time.sleep(120)
        if args.wait:time.sleep(args.wait)
        if args.mode=='recover_gate' and args.marker and Path(args.marker).exists():
            Path(args.marker+'.waiting').write_text('search blocked for forced termination')
            while Path(args.marker).exists():time.sleep(.02)
        if args.mode=='illegal':say('bestmove a1a1');continue
        moves=list(board.legal_moves)
        move=args.bestmove or (rng.choice(moves).uci() if moves else '0000')
        if args.mode=='search_changes' and len(moves)>1:
            move=moves[0].uci();other=moves[1].uci();continuation=board.copy();continuation.push(moves[0])
            reply=next(iter(continuation.legal_moves),None)
            pvs=[move,move+(' '+reply.uci() if reply else ''),other,move]
            for depth,pv in enumerate(pvs,1):
                say(f'info depth {depth} seldepth {depth+2} score cp {depth*10} nodes {depth*100} nps 1000 time {depth*10} hashfull 5 tbhits 2 wdl 300 500 200 pv {pv}')
            say('info string depth 999 score cp 999 pv '+other)
            say('info multipv 2 depth 99 score cp 888 pv '+other)
            if args.wait:time.sleep(args.wait)
        else:say('info depth 7 seldepth 9 score cp 14 nodes 100 nps 10000 hashfull 3 tbhits 0 wdl 320 410 270 pv '+move)
        suffix=''
        if args.ponder_move:suffix=' ponder '+args.ponder_move
        elif args.mode=='ponder' and moves:
            prediction=board.copy();prediction.push_uci(move)
            if not prediction.is_game_over():suffix=' ponder '+list(prediction.legal_moves)[0].uci()
        if 'ponder' in line.split() and args.mode=='ponder':pending_ponder='bestmove '+move+suffix
        else:say('bestmove '+move+suffix)
    elif line in ('ponderhit','stop') and pending_ponder:
        say(pending_ponder);pending_ponder=None
    elif line=='quit':break
