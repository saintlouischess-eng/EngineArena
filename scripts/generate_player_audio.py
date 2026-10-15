"""Original, deterministic chess Foley: damped wood, felt and short room reflections.

Synthesized offline from physical resonances and band-limited contact noise; no
third-party recording, music, sample pack or ongoing audio synthesis is needed.
"""
from pathlib import Path
import math
import random
import struct
import wave

ROOT=Path(__file__).resolve().parents[1]
RATE=44100


def contact(seed,weight=1,soft=False):
    rng=random.Random(seed)
    duration=.27;n=int(RATE*duration);excitation=[];low=0
    for i in range(n):
        t=i/RATE;noise=rng.uniform(-1,1);low+=.22*(noise-low)
        # A rounded strike and friction through felt, rather than a pure tone.
        strike=(1-math.exp(-t/.00032))*math.exp(-t/(.0018 if soft else .0025))
        rub=(1-math.exp(-t/.005))*math.exp(-t/.015)
        excitation.append((low*.9+noise*.12)*strike+low*.016*rub)
    values=[v*.75 for v in excitation]
    for hz,level,decay in [(128,.10,.028),(227,.12,.025),(391,.09,.020),(637,.065,.016),(973,.037,.013),(1571,.024,.009),(2387,.011,.006),(3473,.006,.004)]:
        f=hz*weight*rng.uniform(.94,1.06);radius=math.exp(-1/(RATE*decay));a=2*radius*math.cos(2*math.pi*f/RATE);b=radius*radius;y1=y2=0
        for i,x in enumerate(excitation):
            y=x+a*y1-b*y2;y2=y1;y1=y;values[i]+=y*level*(f/700)
    peak=max(map(abs,values));return [v/peak*(.42 if soft else .64) for v in values]


def board(kind,variant):
    seed=184900+variant*101+{'move':0,'capture':20,'castle':40,'check':60,'promotion':80}[kind]
    rng=random.Random(seed);events=[]
    if kind=='capture':events=[(0,contact(seed,.88,True),.55),(.115,contact(seed+1,.82),1)]
    elif kind=='castle':events=[(0,contact(seed,.84),.88),(.165,contact(seed+1,1.15),.84)]
    else:events=[(0,contact(seed,rng.uniform(.94,1.10)),1)]
    if kind in ('check','promotion'):events.append((.205,contact(seed+2,1.8,True),.36))
    result=[0.]*int(RATE*.65)
    for start,clip,gain in events:
        offset=int(start*RATE)
        for i,v in enumerate(clip):result[offset+i]+=v*gain
    # A faint surface settle avoids identical abrupt tails.
    offset=int(.023*RATE);settle=contact(seed+3,1.23,True)
    for i,v in enumerate(settle):result[offset+i]+=v*.08
    return result


def cue(notes):
    values=[0.]*int(RATE*(len(notes)*.13+.27))
    for number,hz in enumerate(notes):
        offset=int(number*.13*RATE)
        for i in range(int(.27*RATE)):
            t=i/RATE;envelope=(1-math.exp(-t/.006))*math.exp(-t/.055)
            values[offset+i]+=(math.sin(2*math.pi*hz*t)+.12*math.sin(2*math.pi*hz*2.76*t))*envelope*.15
    return values


def write(name,values):
    frames=bytearray()
    for i,v in enumerate(values):
        left=v;right=v*.985
        for seconds,gain in ((.013,.023),(.026,.012),(.041,.006)):
            delay=int(seconds*RATE)
            if i>=delay:left+=values[i-delay]*gain;right+=values[i-delay]*gain*.8
        # Tail taper and a hard headroom bound avoid clicks and clipping.
        fade=min(1,(len(values)-i)/220);left*=fade;right*=fade
        frames.extend(struct.pack('<hh',int(max(-.9,min(.9,left))*32767),int(max(-.9,min(.9,right))*32767)))
    with wave.open(str(ROOT/'ui'/('player-'+name+'.wav')),'wb') as output:
        output.setnchannels(2);output.setsampwidth(2);output.setframerate(RATE);output.writeframes(frames)


if __name__=='__main__':
    for kind in ('move','capture','castle','check','promotion'):
        for variant in range(3):write(kind+('' if not variant else '-'+str(variant+1)),board(kind,variant))
    for name,notes in {'win':[523,659,784],'loss':[392,330,262],'draw':[440,523,440],'low':[740,740]}.items():write(name,cue(notes))
    print('Generated 15 original wooden-piece variations and 4 quiet notification cues.')
