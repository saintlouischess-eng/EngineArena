"""Validate measurements at live and historical presentation boundaries."""
import math
import re

METRICS=('depth','seldepth','nodes','nps','hashfull','tbhits','time')
MOVE=re.compile(r'^[a-h][1-8][a-h][1-8][qrbnQRBN]?$')


def clean(info, elapsed=None):
    result=dict(info)
    invalid=dict(result.pop('invalid_metrics',{}))
    for key in METRICS:
        if key not in result:continue
        value=result[key]
        valid=isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>=0 and (key!='hashfull' or value<=1000)
        if not valid:
            invalid[key]=value;result.pop(key)
        elif key=='time' and value==0 and elapsed is not None and elapsed>=.1:
            invalid[key]=value;result.pop(key)
        else:invalid.pop(key,None)
    if 'pv' in result:
        moves=[]
        for move in result['pv'].split()[:64]:
            if not MOVE.fullmatch(move):break
            moves.append(move.lower())
        result['pv']=' '.join(moves)
    if 'wdl' in result:
        wdl=result['wdl']
        if not (isinstance(wdl,list) and len(wdl)==3 and all(type(v) is int and 0<=v<=1000 for v in wdl) and sum(wdl)==1000):
            invalid['wdl']=result.pop('wdl')
        else:invalid.pop('wdl',None)
    if invalid:result['invalid_metrics']=invalid
    return result
