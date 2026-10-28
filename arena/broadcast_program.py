"""Scene/event direction and bounded observations for the independent show."""
import time

class Program:
    def init_program(self):
        self.pending=None;self.scene_since=time.time();self.event_since=time.time()
        self.recent=[];self.details={};self.hardware={};self.observations=[];self.folder=None
        self.last_observation=0;self.opponent_key=None;self.opponents=[]

    @staticmethod
    def selected(config):
        d=config['design']
        return next((s for s in d['scenes'] if s['id']==d['active']),d['scenes'][0])

    def apply_program(self, config, cut=False):
        from .broadcast import Headlines
        old=self.director.config
        target=self.selected(config).get('tid') or config['tid']
        config=dict(config,tid=target)
        scene=self.selected(config)
        hides_board=not any(p['type']=='board' and p['visible'] for p in scene['panels'])
        changed_scene=scene['id']!=self.selected(old)['id']
        if self.director.current and not cut and (target!=old['tid'] or hides_board):
            self.pending=config
            return False
        self.pending=None
        if target!=old['tid']:
            self.summary={};self.details={};self.summary_at=0;self.recent=[]
            self.headlines=Headlines();self.event_since=time.time();self.opponents=[];self.opponent_key=None
        if config['category']!=old['category']:
            self.ratings=[];self.ratings_at=0;self.rating_names={};self.rating_entries={}
            self.featured_rating_key=None;self.featured_rating_at=0
        if cut and target==old['tid'] and self.director.current:
            # Explicit Cut only changes the show, never tournament/game state.
            self.director.current=None;self.director.live=None
        self.director.configure(config)
        if changed_scene:self.scene_since=time.time()
        return True

    def advance_program(self, now=None):
        now=time.time() if now is None else now
        if self.pending:
            if not self.director.current:self.apply_program(self.pending)
            return
        c=self.director.config;scene=self.selected(c);d=c['design']
        if d['auto'] and now-self.scene_since>=scene['seconds']:
            scenes=[s for s in d['scenes'] if s['enabled']]
            if len(scenes)>1:
                i=next((i for i,s in enumerate(scenes) if s['id']==scene['id']),-1)
                target=scenes[(i+1)%len(scenes)]
                self.apply_program(c|{'design':d|{'active':target['id']}})
            self.scene_since=now
        c=self.director.config
        if not self.pending and not self.director.current and c['event_rotation'] and now-self.event_since>=c['event_seconds']:
            choices=[t['id'] for t in self.tournaments if t.get('state')=='running' and t['id'] in c['playlist']]
            if choices:
                i=choices.index(c['tid']) if c['tid'] in choices else -1
                # Playlist applies to unassigned scenes. Explicit scene assignment wins.
                if not self.selected(c)['tid']:self.apply_program(c|{'tid':choices[(i+1)%len(choices)]})
            self.event_since=now

    def observe_panels(self, status):
        c=self.director.config;tid=c['tid'];live=status.get('live',[])
        self.status={'active':sum(g.get('tid')==tid for g in live),'all_active':status.get('active_games',len(live))}
        self.recent=[{k:g.get(k) for k in ('game','attempt','result','reason','ended','number')}|
                     {'white':g.get('white',{}).get('name',''),'black':g.get('black',{}).get('name','')}
                     for g in status.get('recent_finished',[]) if g.get('tid')==tid and g.get('official')][:40]
        hw=status.get('hardware') or {}
        self.hardware={'identity':{k:v for k,v in hw.get('identity',{}).items() if k in ('cpu','cpu_name','processor','logical_cpus','physical_cores','ram_total')},
            'metrics':{k:v for k,v in hw.get('metrics',{}).items() if k in ('cpu_percent','ram_used','ram_total','ram_available','cpu_temperature')},
            'stale':hw.get('stale',True)}

    def record_observation(self, now=None):
        now=time.time() if now is None else now
        if not self.summary:return
        if self.summary_at and now-self.summary_at>120:return
        types={p['type'] for s in self.director.config['design']['scenes'] for p in s['panels'] if p['visible']}
        if not types.intersection({'scoregraph','ratinggraph','progress','header'}):return
        previous=next((o for o in reversed(self.observations) if o['tid']==self.director.config['tid']),None)
        boundary=previous is None or previous.get('state')!=self.summary.get('state') or previous.get('total')!=self.summary.get('total') or self.summary.get('completed',0)<previous['completed']
        if not boundary and now-self.last_observation<300:return
        self.last_observation=now
        self.observations.append(dict(time=now,tid=self.director.config['tid'],category=self.director.config['category'],
            completed=self.summary.get('completed',0),state=self.summary.get('state'),total=self.summary.get('total'),
            scores=[{'name':r['name'],'points':r.get('points',0)} for r in self.summary.get('standings',[])[:20]],
            ratings=[{'name':r['name'],'rating':r.get('rating')} for r in self.ratings[:20]],ratings_at=self.ratings_at))
        self.observations=self.observations[-720:]
        if self.folder:
            from .broadcast_server import write_json
            write_json(self.folder/'observations.json',self.observations)
