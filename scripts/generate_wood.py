"""Original static vector wood grain; deterministic, filter-free and offline."""
from pathlib import Path
import math
import random
import re
import xml.etree.ElementTree as ET

WOODS={
 'maple':('#ead8ae','#ac8049','#fff2cf',11,.7),
 'ash':('#ddd5be','#91836c','#fff6df',17,1.4),
 'oak':('#bd915c','#6e4927','#edc58c',23,2.1),
 'walnut':('#70503a','#382416','#ad855b',31,1.9),
 'rosewood':('#713e32','#301c1a','#bc8062',41,2.5),
 'ebony':('#343538','#101317','#77716a',53,.85)}

def wood_svg(name):
    base,dark,light,seed,spread=WOODS[name];rng=random.Random(seed)
    paths=[f'<rect width="512" height="256" fill="{base}"/>']
    # Broad ribbons establish growth rings; fine parallel pores follow the same flow.
    for i in range(-8,145):
        y=i*2.05+rng.uniform(-1,1)
        amplitude=rng.uniform(1.5,4.5)*spread
        phase=rng.uniform(-.25,.25)
        points=[]
        for x in range(-16,545,16):
            arch=math.exp(-((x-265)/116)**2)*math.sin(y/26)*amplitude*2
            yy=y+math.sin(x/102+phase+y/43)*amplitude+arch
            points.append(f'{x},{yy:.2f}')
        color=dark if i%4 else light
        width=rng.uniform(.35,1.15) if i%9 else rng.uniform(2.2,4)
        opacity=rng.uniform(.08,.23) if i%9 else .12
        paths.append(f'<path d="M'+ ' L'.join(points)+f'" fill="none" stroke="{color}" stroke-width="{width:.2f}" opacity="{opacity:.2f}"/>')
    if name in ('oak','ash','walnut','rosewood'):
        for i in range(25):
            x=rng.uniform(0,512);y=rng.uniform(0,256);length=rng.uniform(4,26)
            paths.append(f'<path d="M{x:.1f},{y:.1f} q{length/2:.1f},-1 {length:.1f},0" fill="none" stroke="{dark}" stroke-width=".6" opacity=".22"/>')
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 256" preserveAspectRatio="none"><title>'+name.title()+' wood — original Engine Arena grain</title>'+''.join(paths)+'</svg>\n'

def rasterize(svg,path):
    # SVG backgrounds repeat thousands of times in a multiboard view. Bake the
    # grain once for inexpensive image-cache reuse; keep the vector source too.
    # Pillow is a development-only asset-generation dependency, never a runtime one.
    from PIL import Image,ImageDraw
    root=ET.fromstring(svg);scale=2
    image=Image.new('RGBA',(512*scale,256*scale),root[1].get('fill'))
    for element in root:
        if element.tag.rsplit('}',1)[-1]!='path':continue
        data=element.get('d');values=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',data)))
        if 'q' in data:
            x,y,cx,cy,dx,dy=values
            points=[(x+2*(1-t)*t*cx+t*t*dx,y+2*(1-t)*t*cy+t*t*dy) for t in [n/12 for n in range(13)]]
        else:points=list(zip(values[::2],values[1::2]))
        color=element.get('stroke');rgb=tuple(int(color[n:n+2],16) for n in (1,3,5))
        layer=Image.new('RGBA',image.size)
        ImageDraw.Draw(layer).line([(round(x*scale),round(y*scale)) for x,y in points],fill=rgb+(round(float(element.get('opacity'))*255),),width=max(1,round(float(element.get('stroke-width'))*scale)),joint='curve')
        image=Image.alpha_composite(image,layer)
    image.resize((512,256),Image.Resampling.LANCZOS).convert('RGB').save(path,optimize=True)

def generate(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    for name in WOODS:
        svg=wood_svg(name)
        (root/f'{name}.svg').write_text(svg,encoding='utf-8')
        rasterize(svg,root/f'{name}.png')

if __name__=='__main__':generate(Path(__file__).resolve().parents[1]/'ui'/'textures')
