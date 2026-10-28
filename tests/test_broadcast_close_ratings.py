from arena.broadcast import Director


def game(attempt,number,white,black,ply=0):
    return {'tid':'test','attempt':attempt,'game':attempt,'number':number,'ply':ply,
            'white':{'id':white,'name':white},'black':{'id':black,'name':black}}


def test_close_prefers_known_elo_gap_and_keeps_the_game_until_the_end():
    director=Director({'tid':'test','preference':'close'})
    ranks={'a':1,'b':2,'c':3,'d':10,'e':50}
    estimates={'a':3700,'b':3000,'c':3550,'d':3540}
    rating=lambda p:{'rating':estimates.get(p['id'])}
    games=[game('mismatch',1,'a','b'),game('close',2,'c','d'),game('unknown',3,'e','b')]
    director.observe({'live':games},1,ranks,rating)
    assert director.current['attempt']=='close'
    estimates['a']=3000
    director.observe({'live':[game('new-perfect',4,'a','b'),*games]},2,ranks,rating)
    assert director.current['attempt']=='close'


def test_missing_ratings_fall_back_to_ranks_without_zero_elo_guesses():
    director=Director({'tid':'test','preference':'close'})
    games=[game('gap',1,'a','b'),game('near',2,'c','d'),game('old',3,'c','d',20)]
    director.observe({'live':games},1,{'a':1,'b':40,'c':4,'d':5},lambda p:{'rating':None})
    assert director.current['attempt']=='near'
