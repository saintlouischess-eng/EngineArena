"""Bounded live search history, captured before UI polling can miss a PV change."""
from collections import deque
import re

LIMIT=128
FIELDS={'depth','seldepth','nodes','nps','hashfull','tbhits','time','cp','mate','score_bound','wdl','pv'}
MOVE=re.compile(r'^[a-h][1-8][a-h][1-8][qrbn]?$')


def intention(board,pv):
    """First legal primary-PV move, validated in the exact current position."""
    import chess
    tokens=pv.split() if isinstance(pv,str) else pv if isinstance(pv,list) else []
    if not tokens:return None
    try:move=board.parse_uci(tokens[0])
    except (ValueError,TypeError,AttributeError):return None
    if not move or move not in board.legal_moves:return None
    target=move.to_square
    if board.is_castling(move):target=chess.square(6 if board.is_kingside_castling(move) else 2,chess.square_rank(move.from_square))
    return {'fen':board.fen(),'uci':board.uci(move),'from':chess.square_name(move.from_square),'to':chess.square_name(target)}


def white_info(info,color):
    result={k:list(v) if isinstance(v,list) else v for k,v in info.items()}
    if not color:
        for key in ('cp','mate'):
            if key in result:result[key]=-result[key]
        if 'wdl' in result:result['wdl'].reverse()
        if result.get('score_bound') in ('lowerbound','upperbound'):
            result['score_bound']='upperbound' if result['score_bound']=='lowerbound' else 'lowerbound'
    return result


def merge(old,update):
    result=dict(old)
    if 'cp' in update or 'mate' in update:
        result.pop('cp',None);result.pop('mate',None);result.pop('score_bound',None)
    result.update(update)
    return result


class SearchHistory:
    def __init__(self,limit=LIMIT):
        self.limit=limit;self.current=None;self.pv_current=None
        self.past=deque(maxlen=limit)
        self.changes=0;self.revision=0;self.selected=None

    def record(self,update):
        data={k:list(v) if isinstance(v,list) else v for k,v in update.items() if k in FIELDS}
        if not data:return
        pv=data.get('pv',self.pv_current['info']['pv'] if self.pv_current else '')
        if not pv:return
        changed=not self.pv_current or pv!=self.pv_current['info']['pv']
        if changed and not all(MOVE.fullmatch(m) for m in pv.split()):return
        move=pv.split(' ',1)[0]
        info=data|{'pv':pv} if changed else merge(self.pv_current['info'],data)
        self.pv_current={'info':info}
        if not self.current or move!=self.current['move']:
            if self.current:self.past.append(self.current);self.changes+=1
            self.current={'number':self.changes+1,'move':move,'first_time':info.get('time'),'info':info}
        else:self.current=self.current|{'info':info}
        self.revision+=1

    def finish(self,move,info):
        # A final bestmove may differ from the last reported PV. Its evaluation
        # is unknown unless the engine supplied a matching line.
        if not self.current or self.current['move']!=move:
            matching=info.get('pv','').split()[:1]==[move]
            self.record(info if matching else {'pv':move})
        self.selected=move;self.revision+=1

    def snapshot(self):
        return {'current':self.current,'history':list(reversed(self.past)),
                'changes':self.changes,'omitted':max(0,self.changes-len(self.past)),
                'limit':self.limit,'revision':self.revision,'selected':self.selected}
