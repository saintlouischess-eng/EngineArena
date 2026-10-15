import copy
import json
from contextlib import closing
import pytest
from arena.store import Store
from arena import events,circuits


def stage(name='Stage',**kw):
    return dict(id=name,name=name,format='round_robin',groups=1,pairs=1,rounds=3,
                advance_mode='count',advance=1,ties='standings',seeding='balanced',**kw)


def create(s,n=8,stages=None,**kw):
    source=s.create_tournament('Source',[{'name':str(i),'path':'fixture.exe'} for i in range(n)],{'format':'round_robin','cycles':1},backup=False)
    stages=stages or [dict(stage('Qualifier'),format='swiss',advance=4),dict(stage('Groups'),groups=2),dict(stage('Final'),format='knockout')]
    d=dict(kind='circuit',seasons=2,review_policy='automatic',stages=stages,
           resources={'cpu_budget':2,'memory_budget_mb':4096,'concurrency':2,'gpu_limits':{}})|kw
    return events.create(s,'Custom championship',source['id'],d)


def resume(s,eid):
    e=events.detail(s,eid)
    if e['circuit_state']['review']:e=circuits.approve(s,eid,e['revision'])
    events.command(s,eid,'run',e['revision'])


def step(s,eid,tied=False):
    events.tick(s)
    e=events.detail(s,eid,full=True)
    for c in e['children']:
        if not c['valid'] or c['state']!='running':continue
        t=s.tournament(c['tid']);s.fill_queue(t['id'],256)
        while g:=s.claim(t['id']):
            a=int(s.participant(t['id'],g['white'])['name']);b=int(s.participant(t['id'],g['black'])['name'])
            s.finish(g['aid'],'1/2-1/2' if tied else '1-0' if a<b else '0-1','fixture')
        t=s.tournament(t['id'])
        if t['settings']['format']=='round_robin' and t['cursor']*2>=t['total']:
            s.execute("UPDATE tournaments SET state='completed' WHERE id=?",(t['id'],))
    return events.detail(s,eid,full=True)


def drive(s,eid):
    for _ in range(300):
        e=events.detail(s,eid)
        if e['state']=='completed':return events.detail(s,eid,full=True)
        if e['state']=='paused':resume(s,eid)
        step(s,eid)
    raise AssertionError(e)


def test_mixed_formats_two_seasons_insights_and_exact_preview(tmp_path):
    with closing(Store(tmp_path)) as s:
        e=create(s);assert [p['entrants'] for p in e['preview']]==[8,4,2]
        assert [p['output'] for p in e['preview']]==[4,2,1]
        e=drive(s,e['id']);assert e['official_games']==e['scheduled_games']==e['regular_games']==60
        assert [d['champion'] for d in e['decisions'] if 'champion' in d]==['0','0']
        overview=events.insights(s,e['id']);assert overview['current_season']==2 and overview['complete']
        assert overview['champion']['name']=='0'
        career=events.careers(s,e['id'],identity=e['roster'][0]['identity']);assert career['titles']==[1,2]
        for c in e['children']:assert s.snapshot(c['tid'])['complete_pairs']*2==c['total']
        fresh=events.fresh(s,e['id'],'Again');assert fresh['official_games']==fresh['child_count']==0
        assert fresh['circuit_state']['review'] and not fresh['circuit_state']['history']


def test_per_stage_clock_and_new_adjudication_controls_survive_restart(tmp_path):
    configs=[dict(stage('Q'),advance=2,time_control={'kind':'nodes','nodes':500},adjudication={'resign_cp':650,'resign_plies':9,'draw_cp':15,'draw_plies':17,'draw_after':101}),
             dict(stage('Final'),time_control={'kind':'fischer','seconds':180,'increment':.05},adjudication={'resign_cp':700,'resign_plies':11,'draw_cp':10,'draw_plies':21,'draw_after':121})]
    with closing(Store(tmp_path)) as s:
        e=create(s,4,configs,seasons=1);resume(s,e['id']);step(s,e['id']);eid=e['id']
    with closing(Store(tmp_path)) as s:
        e=drive(s,eid)
        for i,c in enumerate(e['children']):
            settings=s.tournament(c['tid'])['settings']
            assert settings['time_control']==configs[i]['time_control']
            assert {k:settings[k] for k in configs[i]['adjudication']}==configs[i]['adjudication']


def test_playoffs_and_main_result_replacement(tmp_path):
    with closing(Store(tmp_path)) as s:
        e=create(s,4,[dict(stage('Q'),advance=2,ties='playoff'),stage('Final')],seasons=1);resume(s,e['id'])
        for _ in range(30):
            e=step(s,e['id'],tied=True)
            if any(c['role']=='playoff' for c in e['children']):break
        assert any(c['role']=='playoff' for c in e['children'])
        e=drive(s,e['id']);assert e['official_games']==e['scheduled_games']>e['regular_games']
        g=s.one('SELECT id FROM games WHERE tid=? AND official IS NOT NULL',(e['children'][0]['tid'],))
        assert s.requeue(e['children'][0]['tid'],[g['id']],mode='replacement')['dependency']
        attempts=s.one('SELECT count(*) n FROM attempts')['n']
        s.requeue(e['children'][0]['tid'],[g['id']],mode='replacement',invalidate=True)
        assert s.one('SELECT count(*) n FROM attempts')['n']==attempts
        e=drive(s,e['id']);assert e['state']=='completed' and any(not c['valid'] for c in e['children'])


def test_future_edit_locks_past_and_preview_does_not_mutate(tmp_path):
    with closing(Store(tmp_path)) as s:
        e=create(s,4,[dict(stage('Q'),advance=2),stage('Final')],seasons=1,review_policy='stage');resume(s,e['id'])
        for _ in range(30):
            e=step(s,e['id'])
            if e['state']=='paused':break
        assert e['editable_from']==1
        d=copy.deepcopy(e['definition']);d['stages'][1]['pairs']=4;d['stages'][1]['adjudication']={'draw_after':222}
        preview=circuits.edit(s,e['id'],e['revision'],d,True)
        assert events.detail(s,e['id'])['revision']==e['revision']
        updated=circuits.edit(s,e['id'],e['revision'],d);assert updated['regular_games']==preview['regular_games']
        d['stages'][0]['pairs']=7
        with pytest.raises(ValueError,match='locked'):circuits.edit(s,e['id'],updated['revision'],d)
        done=drive(s,e['id']);assert done['official_games']==done['scheduled_games']==20
        assert s.tournament(done['children'][-1]['tid'])['settings']['draw_after']==222


def test_templates_rebind_roster_keep_conditions_and_delete(tmp_path):
    with closing(Store(tmp_path)) as s:
        e=create(s,4,[dict(stage('Q'),advance_mode='percent',advance=50),stage('Final')],seasons=1)
        template=circuits.templates(s,{'action':'save','event_id':e['id'],'name':'Reusable'})
        data=circuits.templates(s,{'action':'load','id':template['id']})
        source=s.create_tournament('Different engines',[{'name':str(i+10),'path':'f.exe'} for i in range(6)],{'format':'round_robin'},backup=False)
        e2=events.create(s,'Reused',source['id'],dict(data['definition'],template_id=template['id']))
        assert e2['participants']==6 and e2['preview'][0]['output']==3
        assert e2['roster'][0]['name']=='10'
        circuits.templates(s,{'action':'delete','id':template['id']});assert not circuits.templates(s)
        assert events.detail(s,e2['id'])['preview']==e2['preview']


@pytest.mark.parametrize('bad',[
 {'groups':5},{'advance':99},{'advance_mode':'percent','advance':101},{'rounds':99,'format':'swiss'},
 {'format':'knockout','advance':2},{'adjudication':{'draw_after':2.5}},
])
def test_impossible_stage_rejected(tmp_path,bad):
    with closing(Store(tmp_path)) as s:
        with pytest.raises(ValueError):create(s,4,[dict(stage('Q'),**bad),stage('Final')])
        assert s.one('SELECT count(*) n FROM events')['n']==0


def test_large_field_incremental_and_opening_warning(tmp_path):
    with closing(Store(tmp_path)) as s:
        e=create(s,1000,[dict(stage('Swiss'),format='swiss',advance=32),dict(stage('Final'),format='knockout')],seasons=1)
        assert e['opening_plan'][0]['needed']>e['opening_plan'][0]['available']
        resume(s,e['id']);events.tick(s);assert s.one('SELECT count(*) n FROM games')['n']==0
        assert len(events.detail(s,e['id'])['children'])==1


def test_playoff_result_replacement_and_repeated_ties_keep_official_counts(tmp_path):
    with closing(Store(tmp_path)) as s:
        e=create(s,4,[dict(stage('Q'),advance=2,ties='playoff',tiebreak_control={'kind':'nodes','nodes':123}),stage('Final')],seasons=1);resume(s,e['id'])
        for _ in range(40):
            e=step(s,e['id'],tied=True)
            if sum(c['role']=='playoff' for c in e['children'])>=2:break
        e=drive(s,e['id']);playoffs=[c for c in e['children'] if c['role']=='playoff']
        assert len(playoffs)>=2
        assert all(s.tournament(c['tid'])['settings']['time_control']=={'kind':'nodes','nodes':123} for c in playoffs)
        g=s.one('SELECT id FROM games WHERE tid=? AND official IS NOT NULL',(playoffs[0]['tid'],))
        assert s.requeue(playoffs[0]['tid'],[g['id']],mode='replacement')['dependency']
        s.requeue(playoffs[0]['tid'],[g['id']],mode='replacement',invalidate=True)
        e=drive(s,e['id']);assert e['official_games']==e['scheduled_games']
        assert sum(c['valid'] and c['role']=='playoff' for c in e['children'])>=1
        overview=events.insights(s,e['id'],full=True)
        q=next(c for c in overview['stages'] if c['role']=='circuit')
        assert [p['slot'] for p in q['entries']][:2]==e['decisions'][0]['qualified']


def test_group_opening_cursor_advances_past_all_groups_and_playoffs(tmp_path):
    import chess
    with closing(Store(tmp_path)) as s:
        e=create(s,8,[dict(stage('Groups'),groups=2),stage('Final')],seasons=2)
        b=events.get(s,e['id'])['body'];ops=[{'fen':chess.Board.from_chess960_pos(i).fen()} for i in range(100)]
        # Distinct fixture inventory verifies cursor arithmetic independent of
        # the standard-start fixture used in other event simulations.
        for settings in b['conditions'].values():settings['openings']=ops;settings['chess960']=True
        s.execute('UPDATE events SET body=? WHERE id=?',(json.dumps(b),e['id']))
        e=drive(s,e['id']);starts=[]
        for c in e['children']:
            t=s.tournament(c['tid']);starts.append(t['settings']['event_opening_offset'])
        assert starts==[0,0,6,7,7,13]  # offsets count opening pairs, not games
        assert all(s.snapshot(c['tid'])['complete_pairs']*2==c['total'] for c in e['children'])


@pytest.mark.parametrize('n,groups',[(8,2),(5,2),(5,3),(17,4)])
def test_seeding_assigns_every_entrant_once(tmp_path,n,groups):
    with closing(Store(tmp_path)) as s:
        if groups>n//2:
            with pytest.raises(ValueError):create(s,n,[dict(stage('Groups'),groups=groups),stage('Final')])
            return
        e=create(s,n,[dict(stage('Groups'),groups=groups),stage('Final')])
        b=events.get(s,e['id'])['body'];assigned=circuits.groups_for(b)
        assert sorted(v for g in assigned for v in g)==list(range(n))
        assert [len(g) for g in assigned]==circuits.group_sizes(n,groups)
        if n==8:assert assigned==[[0,3,4,7],[1,2,5,6]]


def test_next_season_edit_preserves_previous_conditions_and_stale_revision(tmp_path):
    with closing(Store(tmp_path)) as s:
        e=create(s,4,[stage('Final')],review_policy='season');resume(s,e['id'])
        for _ in range(40):
            e=step(s,e['id'])
            if e['state']=='paused':break
        assert e['circuit_state']['season']==2 and e['editable_from']==0
        original=s.tournament(e['children'][0]['tid']);d=copy.deepcopy(e['definition']);d['stages'][0]['pairs']=2
        edited=circuits.edit(s,e['id'],e['revision'],d)
        with pytest.raises(ValueError,match='changed'):circuits.edit(s,e['id'],e['revision'],d)
        e=drive(s,e['id']);assert e['official_games']==e['scheduled_games']==36
        after=s.tournament(original['id'])
        assert {k:v for k,v in after.items() if k!='event'}=={k:v for k,v in original.items() if k!='event'}
        assert e['decisions'][0]['config']['pairs']==1 and e['decisions'][1]['config']['pairs']==2


def test_parallel_group_creation_rolls_back_atomically(tmp_path,monkeypatch):
    with closing(Store(tmp_path)) as s:
        e=create(s,8,[dict(stage('Groups'),groups=2),stage('Final')]);resume(s,e['id'])
        before=events.get(s,e['id']);original=s.insert_tournament;calls=0
        def fail(name,prepared):
            nonlocal calls
            calls+=1
            if calls==2:raise RuntimeError('Injected interrupted write')
            return original(name,prepared)
        monkeypatch.setattr(s,'insert_tournament',fail)
        with pytest.raises(RuntimeError):events.tick(s)
        assert not events.detail(s,e['id'])['children']
        assert events.get(s,e['id'])==before
        monkeypatch.setattr(s,'insert_tournament',original)
        events.tick(s);assert len(events.detail(s,e['id'])['children'])==2
