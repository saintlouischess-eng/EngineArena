"""Read-only broadcast state. No Store, Runner or tournament mutations."""
from __future__ import annotations
from collections import deque
import math
import time
import chess
from .broadcast_design import CATALOG, extra_settings

DEFAULTS = dict(tid='', title='Engine Arena • Live', subtitle='Every game. First move to final result.',
                preference='any', follow='', hold=15, move_seconds=.55, panel_seconds=24,
                ticker=True, ticker_mode='scroll', ticker_seconds=55, ticker_size=26,
                results=True, upsets=True, leaders=True, milestones=True, show_ratings=True,
                category='blitz', theme='ocean', pieces='classic', flip=False, sound=False,
                thinking_arrows=True, arrow_delay=1, board_light='theme', board_dark='theme',
                dark_lighten=0, eval_range=5)

WOODS = ('maple','ash','oak','walnut','rosewood','ebony')


def settings(value):
    value = value if isinstance(value,dict) else {}
    out = dict(DEFAULTS)
    for key in ('tid', 'title', 'subtitle', 'follow'):
        out[key] = str(value.get(key, out[key]))[:200]
    for key, choices in dict(preference=('any','leaders','close','follow'), ticker_mode=('scroll','headlines'),
                             category=('bullet','blitz','rapid','classical'), theme=tuple(CATALOG['themes']),
                             board_light=('theme',)+WOODS, board_dark=('theme',)+WOODS,
                             pieces=tuple(CATALOG['pieces'])).items():
        if value.get(key) in choices: out[key] = value[key]
    for key, lo, hi in [('hold',5,60),('move_seconds',.25,2),('panel_seconds',10,120),
                        ('ticker_seconds',20,600),('ticker_size',14,56),('arrow_delay',0,10),
                        ('dark_lighten',0,60),('eval_range',.1,100)]:
        try:
            n = float(value.get(key,out[key]))
            if math.isfinite(n): out[key] = max(lo,min(hi,n))
        except (TypeError,ValueError): pass
    for key in ('ticker','results','upsets','leaders','milestones','show_ratings','flip','sound','thinking_arrows'):
        if isinstance(value.get(key),bool): out[key] = value[key]
    out.update(extra_settings(value))
    return out


def info_public(info, fen=None):
    out = {k:info[k] for k in ('cp','mate','depth','nodes','nps','wdl') if k in info}
    if fen and info.get('pv'):
        try:
            board = chess.Board(fen); san = []
            for raw in str(info['pv']).split()[:12]:
                move = board.parse_uci(raw)
                san.append((str(board.fullmove_number)+'.' if board.turn else ('…' if not san else '')) + board.san(move))
                board.push(move)
            out['pv'] = ' '.join(san)
        except (ValueError,TypeError): pass
    return out


def person(p): return {k:p.get(k,'') for k in ('id','name')}


def thinking_move(live, fen):
    """Expose only the active search's legal first PV move in this exact position."""
    if not live or live.get('ended') or live.get('fen') != fen: return None
    side = live.get('clock_active')
    if side not in ('white', 'black'): return None
    search = live.get('searches', {}).get(side) or {}
    hint = (search.get('info') or {}).get('intention')
    if search.get('complete') or not hint or hint.get('fen') != fen: return None
    try:
        from .search_history import intention
        board = chess.Board(fen)
        if board.turn != (side == 'white'): return None
        checked = intention(board, hint.get('uci'))
        if not checked or checked['from'] == checked['to']: return None
        return checked | {'san': board.san(board.parse_uci(checked['uci'])), 'side': side}
    except (ValueError, TypeError): return None


class Director:
    """One shared playout clock for OBS and preview; retain every committed ply."""
    def __init__(self, config=None):
        self.config = settings(config or {})
        self.seen = set(); self.initialized = False
        self.current = None; self.queue = deque(); self.history = []
        self.loaded = False; self.after = 0; self.has_more = False
        self.next_move = 0.; self.final_since = None; self.ending = None
        self.live = None; self.last_good = 0.; self.connected = False
        self.revision = 0

    def configure(self, config):
        new = settings(config)
        if new['tid'] != self.config['tid']:
            self.__init__(new)
        else: self.config = new

    def observe(self, status, now=None, ranks=None, ratings=None):
        now = time.time() if now is None else now
        self.last_good = now; self.connected = True
        games = [g for g in status.get('live',[]) if g.get('tid') == self.config['tid']]
        keys = {g.get('attempt') for g in games if g.get('attempt')}
        fresh = [g for g in games if g.get('attempt') and g['attempt'] not in self.seen
                 and int(g.get('ply',99)) <= 2]
        # At startup only a game still in its book/start position is eligible.
        if not self.initialized: fresh = [g for g in fresh if int(g.get('ply',99)) == 0]
        self.seen = keys; self.initialized = True
        if self.current:
            self.live = next((g for g in games if g.get('attempt') == self.current['attempt']),None)
        elif fresh:
            ranks = ranks or {}
            def priority(g):
                a,b = (ranks.get(g[s].get('name'),9999) for s in ('white','black'))
                p = self.config['preference']
                if p == 'follow': return (0 if self.config['follow'].casefold() in
                    (g['white']['name']+' '+g['black']['name']).casefold() else 1, a+b)
                if p == 'leaders': return (min(a,b),max(a,b))
                if p == 'close':
                    # Prefer real comparable rating estimates. Rank gaps are a
                    # fallback only, never pretend that missing ratings are zero.
                    values=[ratings(g[s]).get('rating') for s in ('white','black')] if ratings else []
                    if len(values)==2 and all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in values):
                        return (0,abs(values[0]-values[1]),-sum(values),g.get('number',0))
                    return (1,abs(a-b),a+b,g.get('number',0))
                return (g.get('number',0),0)
            g = min(fresh,key=priority)
            self.current = dict(game=g['game'],attempt=g['attempt'],number=g.get('number',0),
                                white=person(g['white']),black=person(g['black']),fen=chess.STARTING_FEN,
                                last_move=None,san='',clocks={},info={},phase='Opening',result=None)
            self.live = g; self.loaded = False; self.after = 0; self.history = []
            self.queue.clear(); self.ending = None; self.final_since = None; self.next_move = now+.6
        self.tick(now)

    def ingest(self, page, now=None):
        now = time.time() if now is None else now
        if not self.current or page.get('attempt',{}).get('id') != self.current['attempt']: return
        if not self.loaded:
            self.current['fen'] = page.get('opening',{}).get('start_fen') or chess.STARTING_FEN
            opening=page.get('opening',{})
            self.current['opening']={k:str(opening[k])[:200] for k in ('name','eco') if opening.get(k)}
            if not page.get('opening_moves'):
                self.current['fen'] = page.get('opening',{}).get('fen',chess.STARTING_FEN)
            self.queue.extend(page.get('opening_moves',[])); self.loaded = True
        for item in page.get('items',[]):
            if item['ply'] > self.after:
                self.queue.append(item); self.after = item['ply']
        self.has_more = page.get('has_more',False)
        a = page.get('attempt') or {}
        if a.get('ended') and not self.has_more and self.after >= page.get('latest_ply',0):
            self.ending = dict(result=a.get('result'),reason=a.get('reason'),official=bool(a.get('official')),
                               clocks=a.get('clocks',{}))
        self.tick(now)

    def tick(self, now=None):
        now = time.time() if now is None else now
        if not self.current: return
        if self.queue and now >= self.next_move:
            item = self.queue.popleft()
            self.history.append({k:item.get(k) for k in ('ply','label','san','uci','side')} |
                                {'info':info_public(item.get('info',{})), 'clocks':item.get('clocks',{})})
            self.current.update(fen=item['fen'],last_move=item.get('uci'),san=item.get('san',''),
                                captured=item.get('captured',[]),crown_squares=item.get('crown_squares',[]),knight_facings=item.get('knight_facings',{}),
                                clocks=item.get('clocks',{}),info=info_public(item.get('info',{})),info_side=item.get('side'),
                                phase='Opening replay' if item.get('ply',1)<=0 else 'Catching up')
            self.revision += 1; self.next_move = now+self.config['move_seconds']
        if self.queue or not self.loaded or self.has_more: return
        if self.ending:
            if self.final_since is None:
                self.final_since = now
                self.current.update(phase='Final result' if self.ending['official'] else 'Attempt ended',
                                    result=self.ending['result'] if self.ending['official'] else None,
                                    reason=self.ending['reason'], official=self.ending['official'],
                                    clocks=self.ending['clocks'])
            elif now-self.final_since >= self.config['hold']:
                self.current = None; self.live = None
            return
        if self.live and self.current['fen'].split()[:4] == self.live.get('fen','').split()[:4]:
            self.current.update(phase='Live',clocks=self.live.get('clocks',{}),info_side=self.live.get('clock_active'),
                                info=info_public(self.live.get('info',{}),self.live.get('fen')))
        else: self.current['phase'] = 'Awaiting committed moves'

    def snapshot(self, now=None):
        now = time.time() if now is None else now
        self.tick(now)
        out = dict(self.current) if self.current else None
        good = self.connected and now-self.last_good < 5
        if out:
            out['thinking'] = (thinking_move(self.live, out['fen'])
                               if good and out['phase'] == 'Live' else None)
            out['moves'] = self.history[-400:]; out['revision'] = self.revision
            out['clock_active'] = self.live.get('clock_active') if self.live and out['phase']=='Live' else None
            out['search_elapsed'] = self.live.get('search_elapsed',0) if out['clock_active'] else 0
            out['clock_age'] = min(2.5,max(0,now-self.last_good)) if out['clock_active'] else 0
        return dict(game=out,connected=good,updated=self.last_good)


class Headlines:
    def __init__(self):
        self.seen=set(); self.ready=False; self.items=deque(maxlen=14); self.leader=None; self.milestone=None

    def add(self, text, kind, now):
        self.items.appendleft(dict(text=text,kind=kind,time=now))

    def results(self, games, tid, now, ratings=None):
        ratings=ratings or {}
        def rating(player):
            value=(ratings(player).get('rating') if callable(ratings)
                   else ratings.get(player['name']))
            return value if isinstance(value,(int,float)) and math.isfinite(value) else None

        def label(name, value):
            return f'{name} ({value:.0f} Elo)' if value is not None else f'{name} (Elo pending)'

        for g in reversed(games):
            key=g.get('attempt')
            if key in self.seen: continue
            self.seen.add(key)
            if not self.ready or g.get('tid')!=tid or not g.get('official'): continue
            w,b=g['white']['name'],g['black']['name']; result=g.get('result','*')
            wr,br=rating(g['white']),rating(g['black'])
            gap=(br-wr if result=='1-0' else wr-br) if wr is not None and br is not None else None
            upset=result in ('1-0','0-1') and gap is not None and gap>=200
            text=f'{label(w,wr)}  {result}  {label(b,br)} · {str(g.get("reason","")).replace("_"," ")}'
            if upset: text=f'UPSET · {text} · winner beat an opponent rated approximately {gap:.0f} Elo higher in the latest rating snapshot'
            self.add(text,'upsets' if upset else 'results',now)
        self.ready=True
        if len(self.seen)>2000: self.seen={g.get('attempt') for g in games}

    def standings(self, rows, completed, now):
        leader=rows[0]['name'] if rows else None
        if leader and self.leader and leader!=self.leader:
            self.add(f'STANDINGS LEADER · {leader} moves to first place on points and tournament tiebreaks','leaders',now)
        self.leader=leader
        milestone=int(completed)//1000
        if self.milestone is not None and milestone>self.milestone:
            self.add(f'MILESTONE · {completed:,} counted tournament games completed','milestones',now)
        self.milestone=milestone
