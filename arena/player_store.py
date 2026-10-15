"""Human games live separately from engine-testing evidence, in the same durable DB."""
from __future__ import annotations
import copy
import json
import math
import os
from pathlib import Path
import time
import uuid
import chess
from .models import Clock, TimeControl
from .pgn_options import normalize


def initialize(store):
    store.db.executescript('''
    CREATE TABLE IF NOT EXISTS player_games(id TEXT PRIMARY KEY, series TEXT, number INTEGER,
      state TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL, revision INTEGER NOT NULL, body TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS player_history ON player_games(created DESC);
    CREATE INDEX IF NOT EXISTS player_series_games ON player_games(series,number);
    CREATE UNIQUE INDEX IF NOT EXISTS player_one_active ON player_games((1)) WHERE state IN ('playing','starting','paused');
    CREATE TABLE IF NOT EXISTS player_series(id TEXT PRIMARY KEY,name TEXT NOT NULL,created REAL NOT NULL,body TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS player_ratings(name TEXT,category TEXT,rating REAL NOT NULL,games INTEGER NOT NULL,
      wins INTEGER NOT NULL,draws INTEGER NOT NULL,losses INTEGER NOT NULL,PRIMARY KEY(name,category));
    CREATE TABLE IF NOT EXISTS player_rating_games(gid TEXT PRIMARY KEY,name TEXT,category TEXT,before REAL,after REAL,opponent REAL,score REAL);
    CREATE TABLE IF NOT EXISTS player_exports(gid TEXT PRIMARY KEY,error TEXT NOT NULL DEFAULT '');
    ''')


def call(store, method, *args):
    return {'recover':recover,'create':create,'save':save,'get':get,'overview':overview,'series':series,
            'next':next_game,'settings':settings,'export':export,'reset_ratings':reset_ratings,
            'retry_exports':retry_exports}[method](store,*args)


def positive(value, label):
    if isinstance(value,bool) or not isinstance(value,int) or value<1:raise ValueError(label+' must be a positive integer')
    return value


def finite(value, label, low, high):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not low<=value<=high:raise ValueError('Invalid '+label)
    return value


def settings(store, value=None):
    default={'name':'Player','sound':True,'volume':35,'show_legal':True,'auto_queen':False,
             'pgn_folder':'','pgn_options':normalize(), 'last_setup':{}}
    if value is None:
        row=store.one("SELECT body FROM preferences WHERE name='player'")
        return default | (json.loads(row['body']) if row else {})
    if not isinstance(value,dict) or set(value)-set(default):raise ValueError('Invalid Player Arena settings')
    updated=settings(store)|value
    if not isinstance(updated['name'],str) or not 1<=len(updated['name'].strip())<=80:raise ValueError('Enter a player name (1–80 characters)')
    updated['name']=updated['name'].strip()
    finite(updated['volume'],'sound volume',0,100)
    updated['pgn_options']=normalize(updated['pgn_options'])
    if updated['pgn_folder']:
        path=Path(updated['pgn_folder'])
        if not path.is_absolute() or not path.is_dir():raise ValueError('Select an existing folder for automatic PGNs')
    store.execute("INSERT OR REPLACE INTO preferences VALUES('player',?)",(json.dumps(updated),))
    return updated


def get(store, gid=None):
    row=store.one('SELECT body FROM player_games WHERE id=?',(gid,)) if gid else store.one("SELECT body FROM player_games WHERE state IN ('playing','starting','paused') LIMIT 1")
    if gid and not row:raise ValueError('Player game not found')
    return json.loads(row['body']) if row else None


def recover(store):
    game=get(store)
    if game and game['state'] in ('playing','starting'):
        game['state']='paused';game['rated']=False;game['note']='Recovered saved position. Resume when ready; this interrupted game is now casual.'
        game['sessions'].append({'time':time.time(),'action':'recovered','ply':len(game['moves'])})
        save(store,game,game['revision'])
    return get(store)


def config(value):
    c={'human_control':{'kind':'fischer','seconds':300,'increment':3},'engine_control':{'kind':'fischer','seconds':300,'increment':3},
       'untimed':False,'color':'white','rated':False,'opponent_rating':1500,'threads':1,'hash':256,
       'tolerance':1,'hang_timeout':300,'draw_policy':'balanced','draw_cp':30,'draw_min_moves':20,
       'chess960':False,'fen':chess.STARTING_FEN,'strength':None,'book_mode':'profile',**value}
    if c['book_mode'] not in ('profile','none','custom'):raise ValueError('Invalid player opening book mode')
    if c['book_mode']=='custom' and not c.get('move_book'):raise ValueError('Choose an engine opening book')
    if c['color'] not in ('white','black','random'):raise ValueError('Choose White, Black or Random')
    for name in ('human_control','engine_control'):
        tc=TimeControl.parse(c[name]);c[name]=copy.deepcopy(c[name])
        if name=='human_control' and tc.kind in ('nodes','depth'):raise ValueError('A human clock cannot use nodes or depth; select untimed practice instead')
    for key in ('threads','hash'):positive(c[key],key)
    finite(c['tolerance'],'clock tolerance',0,60);finite(c['hang_timeout'],'hang watchdog',1,86400)
    finite(c['opponent_rating'],'opponent rating',0,5000);finite(c['draw_cp'],'draw threshold',0,300)
    positive(c['draw_min_moves'],'minimum moves before a draw offer')
    if c['draw_policy'] not in ('balanced','always','never'):raise ValueError('Unknown draw offer policy')
    board=chess.Board(c['fen'],chess960=bool(c['chess960']))
    if not board.is_valid() or board.is_game_over():raise ValueError('Choose a legal, unfinished starting position')
    if c['rated'] and (c['untimed'] or c['fen']!=chess.STARTING_FEN or c['chess960'] or c['draw_policy']=='always'):
        raise ValueError('Rated games require standard starting chess, a human clock and a balanced or disabled draw policy')
    return c


def category(c):
    a,b=c['human_control'],c['engine_control']
    if c['untimed'] or a!=b or a['kind'] in ('nodes','depth','movetime'):return 'handicap'
    tc=TimeControl.parse(a)
    seconds=sum(s['seconds'] for s in tc.stages) if tc.kind=='staged' else tc.seconds+40*(tc.increment if tc.kind=='fischer' else tc.delay if tc.kind in ('delay','bronstein') else 0)
    return 'bullet' if seconds<180 else 'blitz' if seconds<600 else 'rapid' if seconds<3600 else 'classical'


def profile(store, pid, c):
    row=store.one('SELECT body FROM profiles WHERE id=?',(pid,))
    if not row:raise ValueError('Engine profile no longer exists')
    p=json.loads(row['body']);p['threads']=c['threads'];p['hash']=c['hash'];p['options']=dict(p.get('options',{}))
    from .engine_options import find_name
    for key,value in [('Threads',c['threads']),('Hash',c['hash'])]:
        old=find_name(p['options'],key)
        if old:p['options'][old]=value
    if c['strength'] is not None:
        advertised=p.get('advertised',{});elo=find_name(advertised,'UCI_Elo');limit=find_name(advertised,'UCI_LimitStrength')
        if not elo or not limit:raise ValueError('This engine does not advertise UCI strength limiting; use its saved profile options')
        finite(c['strength'],'engine strength',advertised[elo]['min'],advertised[elo]['max'])
        p['options'][elo]=int(c['strength']);p['options'][limit]=True
    from .move_books import validate
    p['move_book']=validate(store,c.get('move_book') if c['book_mode']=='custom' else p.get('move_book') if c['book_mode']=='profile' else None)
    return p


def create(store, body, *, snapshot=None, sid=None, number=1):
    if get(store):raise ValueError('Finish or abandon your current Player Arena game first')
    c=config(body.get('config',{}));name=str(body.get('name') or settings(store)['name']).strip()
    if not 1<=len(name)<=80:raise ValueError('Enter a player name (1–80 characters)')
    p=copy.deepcopy(snapshot) if snapshot else profile(store,body['engine'],c)
    if c['color']=='random':
        import secrets
        c['color']=secrets.choice(('white','black'))
    clocks={s:Clock(TimeControl.parse(c['human_control'] if s==c['color'] else c['engine_control'])).snapshot() for s in ('white','black')}
    if c['untimed']:clocks[c['color']]=Clock(TimeControl.parse({'kind':'nodes','nodes':1})).snapshot()
    gid=uuid.uuid4().hex;now=time.time()
    game={'id':gid,'series':sid,'number':number,'name':name,'engine':p,'config':c,'category':category(c),
          'state':'paused','revision':0,'created':now,'updated':now,'fen':c['fen'],'moves':[],'clocks':clocks,
          'turn_elapsed':0,'rated':bool(c['rated']),'result':'*','reason':'','note':'Ready to play.','sessions':[],
          'variations':[],'draw_offer':False,'rating_change':None}
    with store.tx():store.db.execute('INSERT INTO player_games VALUES(?,?,?,?,?,?,?,?)',(gid,sid,number,'paused',now,now,0,json.dumps(game)))
    return game


def save(store, game, expected, checkpoint=False):
    updated=copy.deepcopy(game);updated['updated']=time.time();updated['revision']=expected+(not checkpoint)
    with store.tx():
        row=store.one('SELECT revision,state FROM player_games WHERE id=?',(game['id'],))
        if not row or row['revision']!=expected:raise ValueError('The game changed. Refresh before trying again.')
        if row['state'] in ('completed','abandoned') and game['state']!=row['state']:raise ValueError('Finished games cannot be reopened')
        if game['state']=='completed' and game['rated'] and not store.one('SELECT 1 FROM player_rating_games WHERE gid=?',(game['id'],)):
            score=.5 if game['result']=='1/2-1/2' else float(game['result']==('1-0' if game['config']['color']=='white' else '0-1'))
            name,cat=game['name'],game['category'];r=store.one('SELECT * FROM player_ratings WHERE name=? AND category=?',(name,cat))
            before=r['rating'] if r else 1500.;opponent=game['config']['opponent_rating'];expected_score=1/(1+10**((opponent-before)/400))
            after=before+32*(score-expected_score)
            store.db.execute('INSERT INTO player_rating_games VALUES(?,?,?,?,?,?,?)',(game['id'],name,cat,before,after,opponent,score))
            store.db.execute('''INSERT INTO player_ratings VALUES(?,?,?,1,?,?,?) ON CONFLICT(name,category) DO UPDATE SET
              rating=excluded.rating,games=games+1,wins=wins+excluded.wins,draws=draws+excluded.draws,losses=losses+excluded.losses''',
              (name,cat,after,int(score==1),int(score==.5),int(score==0)))
            updated['rating_change']={'before':before,'after':after,'opponent':opponent,'score':score,'k':32}
        store.db.execute('UPDATE player_games SET state=?,updated=?,revision=?,body=? WHERE id=?',
                         (updated['state'],updated['updated'],updated['revision'],json.dumps(updated),updated['id']))
        store.db.execute('INSERT OR IGNORE INTO player_exports(gid) VALUES(?)',(updated['id'],))
    # Failure of the derivative PGN must not roll back an already committed move.
    # Retain the visible error and offer retry; replaying a final save is idempotent.
    if game['state'] in ('completed','abandoned','paused') or checkpoint:
        write_pgn(store,updated)
    return updated


def overview(store, offset=0):
    offset=max(0,int(offset));result=[]
    for r in store.rows('SELECT id,body FROM player_games ORDER BY created DESC LIMIT 30 OFFSET ?',(offset,)):
        g=json.loads(r['body']);result.append({k:g[k] for k in ('id','series','number','name','state','created','result','reason','rated','category','rating_change')}|{'opponent':g['engine']['name'],'plies':len(g['moves'])})
    return {'games':result,'total':store.one('SELECT count(*) n FROM player_games')['n'],
            'ratings':store.rows('SELECT * FROM player_ratings ORDER BY name,category'),
            'series':[series_detail(store,r) for r in store.rows('SELECT * FROM player_series ORDER BY created DESC LIMIT 30')],
            'settings':settings(store),'pgn_folder':str(store.folder/'PlayerArena'/'PGN'),
            'export_error':(store.one("SELECT error FROM player_exports WHERE error<>'' LIMIT 1") or {}).get('error','')}


def series_detail(store, row):
    b=json.loads(row['body']);games=store.rows('SELECT number,state,body FROM player_games WHERE series=? ORDER BY number',(row['id'],))
    rows=[];score=0;finished=0
    for g in games:
        v=json.loads(g['body']);s=.5 if v['result']=='1/2-1/2' else 1 if v['result']==('1-0' if v['config']['color']=='white' else '0-1') else 0
        score+=s;finished+=g['state'] in ('completed','abandoned');rows.append({'id':v['id'],'number':g['number'],'opponent':v['engine']['name'],'result':v['result'],'score':s,'state':v['state']})
    return {'id':row['id'],'name':row['name'],'total':len(b['profiles'])*b['games_each'],'played':finished,'points':score,'games':rows,'complete':finished==len(b['profiles'])*b['games_each']}


def series(store, body):
    c=config(body.get('config',{}));ids=list(dict.fromkeys(body.get('engines',[])))
    if not ids:raise ValueError('Select at least one engine')
    count=positive(body.get('games_each',2),'Games per engine')
    b={'config':c,'profiles':[profile(store,pid,c) for pid in ids],'games_each':count,'name':body.get('name') or settings(store)['name']}
    title=str(body.get('title') or 'Player challenge').strip()
    if not 1<=len(title)<=120:raise ValueError('Enter a series name (1–120 characters)')
    sid=uuid.uuid4().hex;store.execute('INSERT INTO player_series VALUES(?,?,?,?)',(sid,title,time.time(),json.dumps(b)))
    return series_detail(store,store.one('SELECT * FROM player_series WHERE id=?',(sid,)))


def next_game(store, sid):
    row=store.one('SELECT * FROM player_series WHERE id=?',(sid,))
    if not row:raise ValueError('Player series not found')
    if get(store):raise ValueError('Finish your current game before starting the next round')
    b=json.loads(row['body']);n=store.one('SELECT count(*) n FROM player_games WHERE series=?',(sid,))['n']
    if n>=len(b['profiles'])*b['games_each']:raise ValueError('This series is complete')
    c=copy.deepcopy(b['config']);cycle,index=divmod(n,len(b['profiles']))
    if c['color']!='random' and cycle%2:c['color']='black' if c['color']=='white' else 'white'
    return create(store,{'config':c,'name':b['name']},snapshot=b['profiles'][index],sid=sid,number=n+1)


def export(store, gid, options=None):
    from .player_pgn import render
    game=get(store,gid);title=store.one('SELECT name FROM player_series WHERE id=?',(game['series'],)) if game['series'] else None
    return render(game,normalize(options),title['name'] if title else 'Player Arena')


def atomic_write(path, text):
    path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix(path.suffix+'.tmp')
    with temp.open('w',encoding='utf-8',newline='\n') as stream:
        stream.write(text);stream.flush();os.fsync(stream.fileno())
    os.replace(temp,path)


def write_pgn(store, game):
    try:
        cfg=settings(store);finished=game['state'] in ('completed','abandoned')
        root=store.folder/'PlayerArena';folder=root/('PGN' if finished else 'In progress')
        text=export(store,game['id'],{'preset':'archive'})
        atomic_write(folder/(game['id']+'.pgn'),text)
        if finished and cfg['pgn_folder']:atomic_write(Path(cfg['pgn_folder'])/('EngineArena-player-'+game['id']+'.pgn'),export(store,game['id'],cfg['pgn_options']))
        store.execute('DELETE FROM player_exports WHERE gid=?',(game['id'],))
    except (OSError,ValueError) as e:
        store.execute('INSERT OR REPLACE INTO player_exports VALUES(?,?)',(game['id'],'Player PGN saving failed: '+str(e)))
    store.player_export_error=(store.one("SELECT error FROM player_exports WHERE error<>'' LIMIT 1") or {}).get('error','')


def retry_exports(store):
    for row in store.rows('SELECT gid FROM player_exports LIMIT 32'):
        game=get(store,row['gid']);write_pgn(store,game)
        if getattr(store,'player_export_error',''):break
    return {'error_message':getattr(store,'player_export_error','')}


def reset_ratings(store, name):
    if get(store):raise ValueError('Finish your current game before resetting ratings')
    with store.tx():
        store.db.execute('DELETE FROM player_ratings WHERE name=?',(name,))
        # Keep result IDs so old games cannot silently be rated again.
    return {'ok':True}


