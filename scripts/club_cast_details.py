"""Original opaque, skinned grooming and footwear details for the club cast.

No alpha-sorted beard planes or per-frame meshes. Every detail is exported as
ordinary static/skinned glTF geometry, with a bounded polygon budget.
"""
import math, random
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

TAU=math.tau
def clamp(x): return max(0,min(1,x))
def smooth(x): x=clamp(x);return x*x*(3-2*x)

class DetailMesh:
    def __init__(self): self.vertices=[];self.faces=[];self.uvs=[]
    def tube(self,points,radius=.03,sides=5):
        start=len(self.vertices)
        for i,p in enumerate(points):
            tangent=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
            u=tangent.cross(Vector((0,0,1)))
            if u.length<.01:u=tangent.cross(Vector((0,1,0)))
            u.normalize();v=tangent.cross(u);r=radius*(.42+.58*math.sin(math.pi*(i+.5)/len(points)))
            self.vertices.extend(p+r*(u*math.cos(k*TAU/sides)+v*math.sin(k*TAU/sides)) for k in range(sides))
        for i in range(len(points)-1):
            for k in range(sides):self.faces.append([start+i*sides+k,start+i*sides+(k+1)%sides,start+(i+1)*sides+(k+1)%sides,start+(i+1)*sides+k])
        self.faces.extend([[start+k for k in reversed(range(sides))],[start+(len(points)-1)*sides+k for k in range(sides)]])
    def object(self,name,material,arm,bone='head'):
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(self.vertices,[],self.faces);mesh.update()
        if self.uvs:
            layer=mesh.uv_layers.new(name='UVMap')
            for poly,uvs in zip(mesh.polygons,self.uvs):
                for i,uv in zip(poly.loop_indices,uvs):layer.data[i].uv=uv
            bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00005);bm.to_mesh(mesh);bm.free();mesh.update()
        ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob);ob.parent=arm;mesh.materials.append(material)
        for p in mesh.polygons:p.use_smooth=True
        vg=ob.vertex_groups.new(name=bone);vg.add(list(range(len(self.vertices))),1,'REPLACE');mod=ob.modifiers.new('Anatomical attachment','ARMATURE');mod.object=arm
        return ob

def hair(cast,arm,skin,old,material):
    """Solid shaped cap, layered tapered locks, individually varied silhouettes."""
    p=material.node_tree.nodes.get('Principled BSDF');p.inputs['Roughness'].default_value=.78
    name=cast['id'];rng=random.Random(sum(map(ord,name))*719)
    eye=arm.data.bones['eye.L'].head_local;top=max(v.co.z for v in skin.data.vertices)
    eyez=eye.z;scalp=BVHTree.FromPolygons([v.co for v in skin.data.vertices],[p.vertices for p in skin.data.polygons])
    center=Vector((0,eye.y+.8,eyez+.55));height=top-center.z
    preserve=not cast.get('cameo') and not cast['hair'].startswith('short') and name!='daniel'
    if preserve:return
    curly=name in ['fabiano','hans','levy','daniel'];extra={'fabiano':.30,'hans':.46,'levy':.36,'magnus':.18,'bobby':.10,'hikaru':.20,'jonas':.15,'arthur':.10,'daniel':.24}.get(name,.008)
    ears=[]
    for sign in [-1,1]:
        region=[v.co for v in skin.data.vertices if eyez-1.10<v.co.z<eyez+.45 and v.co.x*sign>0]
        extreme=max(p.x*sign for p in region)
        rim=[p for p in region if p.x*sign>extreme-.20]
        ears.append(sum(rim,Vector())/len(rim))
    nape={'hans':-1.62,'fabiano':-1.40,'levy':-1.20,'bobby':-1.30}.get(name,-1.25)
    def hair_edge(azimuth):
        # Use each fitted ear's position, not a generic cosine cutoff. That
        # cutoff put the arch over the temple and punched a second bare gap
        # around the actual ear. Sideburn, ear arch and nape are one surface.
        a=math.acos(math.cos(azimuth));e=ears[1 if math.sin(azimuth)>=0 else 0]
        ear_angle=math.atan2(abs(e.x),center.y-e.y)
        arch=e.z-eyez+.73
        bottom=-1.20 if name in ['hikaru','levy'] else -.72 if name=='bobby' else -.62
        contour=[(0,.75 if name=='hans' else 1.00),(.70,.86),
                 (ear_angle-.83,.66),(ear_angle-.56,.12),
                 (ear_angle-.43,bottom),(ear_angle-.29,bottom+.03),
                 (ear_angle-.20,-.10),(ear_angle-.08,arch),
                 (ear_angle+.10,arch+.015),(ear_angle+.22,.06),
                 (ear_angle+.34,-.70),(ear_angle+.48,nape),(math.pi,nape)]
        for (aa,za),(bb,zb) in zip(contour,contour[1:]):
            if aa<=a<=bb:
                return eyez+za+(zb-za)*smooth((a-aa)/(bb-aa))+.008*math.sin(azimuth*19+.3)
        raise ValueError('Hairline outside anatomical contour')
    def surface(theta,azimuth,detail=True):
        edge=hair_edge(azimuth)
        direction=Vector((math.sin(theta)*math.sin(azimuth),-math.sin(theta)*math.cos(azimuth),math.cos(theta)))
        # Cast from inside the skull outward: an inward ray at the nape could
        # hit a shoulder first and stretch hair into long triangular spikes.
        hit,normal,_,_=scalp.ray_cast(center,direction,4)
        if hit is None:hit=center+Vector((direction.x*1.7,direction.y*1.6,direction.z*height));normal=direction
        z=hit.z
        # Taper at the neckline without fading out the actual geometry.
        volume=extra*(.36+.64*smooth((z-eyez+.8)/2.2))*smooth((z-edge)/.55)
        ripple=(math.sin(azimuth*13+theta*19)+math.sin(azimuth*21-theta*11))*.016 if detail else 0
        hit+=normal*((.008 if preserve else .07)+volume+(0 if preserve else ripple))
        return hit,normal,edge
    cap=DetailMesh();rings=42;sectors=192;ring_end=[]
    for j in range(sectors):
        a=j*TAU/sectors;last=.2
        for k in range(240):
            t=.01+k*math.pi/240;p,n,edge=surface(t,a)
            if p.z<edge:
                lo,hi=last,t
                for _ in range(12):
                    mid=(lo+hi)/2;hit,_,bound=surface(mid,a)
                    if hit.z<bound:hi=mid
                    else:lo=mid
                last=(lo+hi)/2;break
            last=t
        ring_end.append(last)
    for i in range(rings+1):
        for j in range(sectors):
            p,_,_=surface(.005+(ring_end[j]-.005)*i/rings,j*TAU/sectors);cap.vertices.append(p)
    for i in range(rings):
        for j in range(sectors):
            face=[i*sectors+j,i*sectors+(j+1)%sectors,(i+1)*sectors+(j+1)%sectors,(i+1)*sectors+j]
            cap.faces.append(face)
    foundation=material.copy();foundation.name='Hair dense undercoat';foundation.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.88
    if cast.get('hair_root_color'):
        foundation.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(*cast['hair_root_color'],1)
    cap.object('Hair sculpted foundation',foundation,arm)
    # Thick, dark locks form volume; fine ribbons follow them rather than wire
    # loops sitting on a featureless helmet. All geometry is opaque.
    locks=DetailMesh();fine=DetailMesh()
    count=1550 if curly else 1100
    for i in range(count):
        a=(i*2.399963229728653+rng.uniform(-.025,.025))%TAU;j=int(a/TAU*sectors)%sectors
        t=math.acos(1-((i+.5)/count)*(1-math.cos(ring_end[j])))
        p,n,edge=surface(t,a)
        edge_taper=smooth((p.z-edge)/.30)
        u=n.cross(Vector((0,1,0)))
        if u.length<.01:u=n.cross(Vector((1,0,0)))
        u.normalize();v=n.cross(u)
        if curly:
            radius=rng.uniform(.09,.17)*({'hans':1.30,'levy':1.15}.get(name,1))*(.20+.80*edge_taper);phase=rng.random()*TAU
            pts=[p+u*(radius*math.cos(phase+k/12*TAU*.65))+v*(radius*math.sin(phase+k/12*TAU*.65))+n*(.03+.05*math.sin(k/12*math.pi)) for k in range(13)]
            locks.tube(pts,(.032 if name=='fabiano' else .038)*(.35+.65*edge_taper),5)
            for strand in [0]:fine.tube([x+n*.017+u*strand*.016 for x in pts],.0055,3)
        else:
            sweep=(.20 if name=='hikaru' else .32 if name=='bobby' else .26)*(.25+.75*edge_taper)
            pts=[]
            for k in range(11):
                aa=a+(k/10-.5)*sweep;limit=ring_end[int((aa%TAU)/TAU*sectors)%sectors]
                pts.append(surface(max(.015,min(limit,t+(k/10-.5)*.23)),aa)[0]+n*(.016+.022*math.sin(k/10*math.pi)))
            locks.tube(pts,.016,5);fine.tube([x+n*.012 for x in pts],.0045,3)
    locks.object('Hair shaped locks',material,arm)
    strand_material=material
    if cast.get('hair_strand_color'):
        strand_material=material.copy();strand_material.name='Hair fine highlights'
        strand_shader=strand_material.node_tree.nodes.get('Principled BSDF')
        strand_shader.inputs['Base Color'].default_value=(*cast['hair_strand_color'],1)
        strand_shader.inputs['Roughness'].default_value=.82
    fine.object('Hair fine strands',strand_material,arm)
    bpy.data.objects.remove(old,do_unlink=True)

def beard(cast,arm,skin,material):
    if cast['id'] not in ['hikaru','levy']:return
    eye=arm.data.bones['eye.L'].head_local;chin=arm.data.bones['jaw'].tail_local.z
    # Chin-to-eye geometry controls the mask, including a clean opening around
    # the lips and a gradual cheek line. Solid strands wrap around both cheeks.
    span=eye.z-chin;mouth=chin+span*.38;mesh=skin.data;mesh.calc_loop_triangles()
    # A real opaque beard foundation. Reusing the skin texture here left bright
    # skin between dark fibers, producing a translucent/stippled beard.
    shell_material=material.copy();shell_material.name='Beard dense opaque undercoat';shell_material.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.88
    rng=random.Random(412 if cast['id']=='hikaru' else 829);shell=DetailMesh();strands=DetailMesh()
    def coverage(p):
        x,y,z=p;side=abs(x);top=mouth+.10+side*.52
        if cast['id']=='levy':top=mouth-.07+side*.34
        # Connect cheek growth to the sideburn, continuing around the jaw.
        top+=(eye.z-.42-top)*smooth((side-.93)/.48)
        top+=.018*math.sin(x*24+z*17)
        density=smooth((top-z)/.20)*smooth((z-chin+.20)/.22)*smooth((eye.y+1.10-y)/.40)
        lips=(x/.63)**2+((z-mouth)/.17)**2
        moustache=mouth+.18<z<mouth+.38 and .13<side<.63 and y<eye.y-.30
        if moustache:density=max(density,.80)
        if lips<1.25:density=0
        if z>eye.z-.35:density=0
        return density
    # Subdivide only beard-region triangles. Fade shell displacement at the
    # silhouette, rather than exposing the skin mesh's coarse triangle edges.
    for tri in mesh.loop_triangles:
        vs=[mesh.vertices[i] for i in tri.vertices];center=sum((v.co for v in vs),Vector())/3
        if center.z>eye.z-.4 or center.z<chin-.4 or center.y>eye.y+1:continue
        n=tri.normal;divisions=5;uvs=[mesh.uv_layers[0].data[i].uv for i in tri.loops]
        for i in range(divisions):
            for j in range(divisions-i):
                cells=[[(i,j),(i+1,j),(i,j+1)]]
                if j<divisions-i-1:cells.append([(i+1,j),(i+1,j+1),(i,j+1)])
                for coords in cells:
                    points=[vs[0].co*(1-(a+b)/divisions)+vs[1].co*a/divisions+vs[2].co*b/divisions for a,b in coords]
                    ds=[coverage(p) for p in points]
                    if min(ds)<.16:continue
                    # Do not build blocky moustache slabs. Texture and tiny
                    # individual strands carry the upper lip instead.
                    if sum(p.z for p in points)/3>mouth+.08 and abs(sum(p.x for p in points)/3)<.69:continue
                    thickness=.095 if cast['id']=='hikaru' else .06
                    normals=[(vs[0].normal*(1-(a+b)/divisions)+vs[1].normal*a/divisions+vs[2].normal*b/divisions).normalized() for a,b in coords]
                    start=len(shell.vertices);shell.vertices.extend(p+normal*(thickness*d+.004) for p,d,normal in zip(points,ds,normals));shell.faces.append([start,start+1,start+2]);shell.uvs.append([uvs[0]*(1-(a+b)/divisions)+uvs[1]*a/divisions+uvs[2]*b/divisions for a,b in coords])
                    if rng.random()<.48:
                        p=sum(points,Vector())/3+sum(normals,Vector()).normalized()*(thickness*sum(ds)/3+.012)
                        direction=Vector((p.x*.09,-.09,-1)).normalized();length=rng.uniform(.025,.075)
                        strands.tube([p,p+direction*length*.6+n*.01,p+direction*length],.006,3)
    ob=shell.object('Beard opaque fitted volume',shell_material,arm)
    shell_material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.25,.17,.105,1)
    colors=ob.data.color_attributes.new(name='Beard root tone',type='FLOAT_COLOR',domain='CORNER')
    for loop in ob.data.loops:
        point=ob.data.vertices[loop.vertex_index].co;d=coverage(point)
        tone=(.14+.60*(1-d)**2)*(.90+.10*math.sin(point.x*119+point.z*173))
        colors.data[loop.index].color=(tone,tone,tone,1)
    ob.data.color_attributes.active_color=colors
    strands.object('Beard fine growth',material,arm)

def long_hair(cast,arm,skin,old,make_material):
    """Original shoulder-length, center-parted locks for the supplied reference.

    Closed ribbons give the hairstyle depth without alpha sorting. Lower locks
    blend into neck/chest motion rather than behaving like a rigid head helmet.
    """
    eye=arm.data.bones['eye.L'].head_local;top=max(v.co.z for v in skin.data.vertices)
    center=Vector((0,eye.y+.8,eye.z+.55));rng=random.Random(18404)
    scalp=BVHTree.FromPolygons([v.co for v in skin.data.vertices],[p.vertices for p in skin.data.polygons])
    meshes=[DetailMesh() for _ in range(5)];fibers=DetailMesh()
    # A fitted continuous underlayer prevents scalp showing through where the
    # long locks bend over the occipital curve. It follows the head, not cards.
    cap=DetailMesh();rings=24;sectors=112
    for i in range(rings+1):
        for j in range(sectors):
            az=j*TAU/sectors;front=math.cos(az);edge=eye.z+(1.28 if front>.65 else -.65 if front>-.25 else -1.65)
            end=.2
            for k in range(160):
                angle=.005+k*math.pi/160;d=Vector((math.sin(angle)*math.sin(az),-math.sin(angle)*front,math.cos(angle)));hit,normal,_,_=scalp.ray_cast(center,d,4)
                if hit is None or hit.z<edge:break
                end=angle
            angle=.005+end*i/rings;d=Vector((math.sin(angle)*math.sin(az),-math.sin(angle)*front,math.cos(angle)));hit,normal,_,_=scalp.ray_cast(center,d,4)
            cap.vertices.append(hit+normal*.065 if hit is not None else center+d*1.6)
    for i in range(rings):
        for j in range(sectors):cap.faces.append([i*sectors+j,i*sectors+(j+1)%sectors,(i+1)*sectors+(j+1)%sectors,(i+1)*sectors+j])
    cap.object('Hair blonde fitted underlayer',make_material('Hair blonde roots',color=(.22,.157,.092)),arm)
    def catmull(points,t):
        u=min(len(points)-1.00001,max(0,t)*(len(points)-1));i=int(u);u-=i
        a,b,c,d=[points[max(0,min(len(points)-1,k))] for k in [i-1,i,i+1,i+2]]
        return (b*2+(c-a)*u+(a*2-b*5+c*4-d)*u*u+(-a+b*3-c*3+d)*u*u*u)*.5
    for side in [-1,1]:
        for j in range(49):
            a=.90+j/48*(math.pi-.90);front=math.cos(a);span=math.sin(a);cy=center.y-front*(2.85 if front>0 else 1.85)
            points=[Vector((side*.035,center.y-front*(2.3 if front>0 else .9),top+.07-1.4*max(0,front))),
                    Vector((side*1.40*span,center.y-front*(2.5 if front>0 else 1.38),eye.z+1.62-.12*abs(front))),
                    Vector((side*1.98*span,cy,eye.z+.05)),
                    Vector((side*2.22*span,cy+.08,eye.z-2.55)),
                    Vector((side*2.54*span,cy-.95*front,eye.z-3.95)),
                    Vector((side*2.47*span,cy-1.25*front+.08*math.sin(j),eye.z-4.7+rng.uniform(-.23,.23)))]
            for k in range(3):
                direction=(points[k]-center).normalized();hit,normal,_,_=scalp.ray_cast(center,direction,4)
                if hit is not None:points[k]=hit+normal*.085
            mesh=meshes[j%5];start=len(mesh.vertices);count=42;frames=[]
            for k in range(count):
                t=k/(count-1);p=catmull(points,t);tangent=(catmull(points,min(1,t+.01))-catmull(points,max(0,t-.01))).normalized()
                normal=Vector((side*span,-front,.15));normal=(normal-tangent*normal.dot(tangent)).normalized();across=tangent.cross(normal).normalized()
                width=(.035+.095*smooth(t/.30))*(1-.70*smooth((t-.86)/.14));depth=.028+.024*math.sin(t*math.pi)
                p+=normal*(.025*math.sin(t*17+j*.7))
                if p.z>eye.z-1.75:
                    direction=(p-center).normalized();hit,sn,_,_=scalp.ray_cast(center,direction,4)
                    if hit is not None and (p-center).length<(hit-center).length+.105:p=hit+sn*.105
                frames.append((p,across,normal,width,depth))
                for q in range(8):mesh.vertices.append(p+across*(width*math.cos(q*TAU/8))+normal*(depth*math.sin(q*TAU/8)))
            for k in range(count-1):
                for q in range(8):mesh.faces.append([start+k*8+q,start+k*8+(q+1)%8,start+(k+1)*8+(q+1)%8,start+(k+1)*8+q])
            mesh.faces.extend([[start+q for q in reversed(range(8))],[start+(count-1)*8+q for q in range(8)]])
            for s in [-.65,0,.65]:fibers.tube([p+across*(width*s)+normal*(depth+.004) for p,across,normal,width,depth in frames],.0018,3)
    objects=[]
    for i,mesh in enumerate(meshes):
        shade=[.94,.97,1.00,1.04,1.07][i];m=make_material('Hair blonde layered '+str(i),color=(.27*shade,.205*shade,.132*shade));m.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.58
        objects.append(mesh.object('Hair center-parted length '+str(i),m,arm))
    objects.append(fibers.object('Hair blonde fine strands',make_material('Hair soft golden fibers',color=(.26,.195,.12)),arm))
    for ob in objects:
        ob.vertex_groups.clear();head=ob.vertex_groups.new(name='head');neck=ob.vertex_groups.new(name='neck01');chest=ob.vertex_groups.new(name='spine02')
        for vertex in ob.data.vertices:
            blend=smooth((eye.z-2.1-vertex.co.z)/5.0);head.add([vertex.index],1-blend*.68,'REPLACE');neck.add([vertex.index],blend*.30,'REPLACE');chest.add([vertex.index],blend*.38,'REPLACE')
    bpy.data.objects.remove(old,do_unlink=True)

FOOTWEAR={
 'arthur':('penny-loafers',(.13,.055,.022)), 'mei':('court-sneakers',(.68,.63,.52)),
 'daniel':('sport-trainers',(.025,.055,.10)), 'elena':('leather-flats',(.15,.025,.045)),
 'jonas':('oxfords',(.020,.021,.023)), 'nora':('sport-trainers',(.09,.095,.10)),
 'magnus':('court-sneakers',(.72,.70,.64)), 'fabiano':('oxfords',(.055,.025,.012)),
 'hans':('ankle-boots',(.23,.12,.05)), 'bobby':('derbies',(.020,.018,.017)),
 'hikaru':('sport-trainers',(.16,.18,.19)), 'levy':('chelsea-boots',(.105,.055,.03)),
}
def footwear(cast,arm,shoe,make_material):
    style,color=FOOTWEAR[cast['id']];cast['footwear']=style
    mat=make_material('Footwear '+style,color=color);mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.48 if style not in ['sport-trainers','court-sneakers'] else .79
    sole=make_material('Footwear sole',color=(.65,.62,.54) if style=='court-sneakers' else (.033,.032,.029))
    trim=make_material('Footwear stitching',color=tuple(min(1,c*1.4+.015) for c in color))
    lace=make_material('Footwear laces',color=(.52,.52,.48) if style in ['court-sneakers','sport-trainers'] else tuple(c*.6 for c in color))
    shoe.data.materials.clear();shoe.data.materials.append(mat);shoe.data.materials.append(sole)
    lo=min(v.co.z for v in shoe.data.vertices);heel=.26 if style=='ankle-boots' else .17 if style=='court-sneakers' else .12
    for p in shoe.data.polygons:p.material_index=0
    # Deliberately different toe proportions, not just twelve color swaps.
    for sign,side in [(1,'L'),(-1,'R')]:
        verts=[v for v in shoe.data.vertices if v.co.x*sign>0];cx=sum(v.co.x for v in verts)/len(verts);miny=min(v.co.y for v in verts);maxy=max(v.co.y for v in verts);length=maxy-miny;front=miny+length*.40
        for v in verts:
            f=smooth((front-v.co.y)/(length*.35));v.co.x=cx+(v.co.x-cx)*(1+f*(.10 if 'sneaker' in style or 'trainer' in style else -.1 if style=='leather-flats' else 0))
            if style=='leather-flats' and v.co.z<arm.data.bones['foot.'+side].head_local.z-.35:v.co.z=lo+(v.co.z-lo)*.94
        shoe.data.update()
        points=sorted(set((round(v.co.x,5),round(v.co.y,5)) for v in verts if v.co.z<lo+.45))
        def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
        halves=[]
        for seq in [points,list(reversed(points))]:
            half=[]
            for xy in seq:
                while len(half)>=2 and cross(half[-2],half[-1],xy)<=0:half.pop()
                half.append(xy)
            halves.extend(half[:-1])
        solemesh=DetailMesh();count=len(halves)
        for z,spread in [(lo-.015,1.0),(lo+heel*.8,1.025),(lo+heel,1.0)]:
            solemesh.vertices.extend(Vector((cx+(x-cx)*spread,y,z)) for x,y in halves)
        for j in range(2):
            for k in range(count):solemesh.faces.append([j*count+k,j*count+(k+1)%count,(j+1)*count+(k+1)%count,(j+1)*count+k])
        if count:
            solemesh.faces.extend([list(reversed(range(count))),list(range(count*2,count*3))]);solemesh.object('Footwear fitted sole '+side,sole,arm,'foot.'+side)
        bvh=BVHTree.FromPolygons([v.co for v in shoe.data.vertices],[p.vertices for p in shoe.data.polygons])
        def top(x,y,offset=.025):
            p,n,_,_=bvh.ray_cast(Vector((x,y,lo+8)),Vector((0,0,-1)),12)
            return p+Vector((0,0,offset)) if p else Vector((x,y,lo+.5))
        seams=DetailMesh();laces=DetailMesh();width=max(abs(v.co.x-cx) for v in verts)
        if style in ['penny-loafers','leather-flats','chelsea-boots']:
            y=miny+length*.53
            seams.tube([top(cx+width*.76*(2*k/20-1),y+.15*math.cos(k/20*math.pi)) for k in range(21)],.040 if style=='penny-loafers' else .022,5)
        else:
            for j in range(4 if style=='oxfords' else 5):
                y=miny+length*(.28+j*.045)
                laces.tube([top(cx-width*.27+width*.54*k/8,y+(k/8-.5)*.12,.065) for k in range(9)],.028 if 'trainer' in style else .022,5)
            y=miny+length*.28;seams.tube([top(cx+width*.80*(2*k/20-1),y+.12*math.cos(k/20*math.pi)) for k in range(21)],.014,4)
        if seams.vertices:seams.object('Footwear welt '+side,trim,arm,'foot.'+side)
        if laces.vertices:laces.object('Footwear lacing '+side,lace,arm,'foot.'+side)
        if style in ['ankle-boots','chelsea-boots']:
            ankle=arm.data.bones['foot.'+side].head_local;boot=DetailMesh()
            for h,r in [(lo+.5,.70),(lo+1.3,.61),(lo+1.9,.56)]:
                boot.vertices.extend(Vector((ankle.x+math.cos(k*TAU/24)*r,ankle.y+math.sin(k*TAU/24)*r*.85,h)) for k in range(24))
            for j in range(2):
                for k in range(24):boot.faces.append([j*24+k,j*24+(k+1)%24,(j+1)*24+(k+1)%24,(j+1)*24+k])
            boot.object('Footwear boot shaft '+side,mat,arm,'foot.'+side)
    sock=make_material('Footwear soft socks',color=(.13,.14,.16));shoe.data.materials.append(sock)
    for sign,side in [(1,'L'),(-1,'R')]:
        ankle=arm.data.bones['foot.'+side].head_local.z
        footgroup=shoe.vertex_groups.get('foot.'+side) or shoe.vertex_groups.new(name='foot.'+side)
        for vertex in shoe.data.vertices:
            if vertex.co.x*sign<=0:continue
            amount=1-smooth((vertex.co.z-ankle-.10)/.85)
            if amount<=0:continue
            old={g.group:g.weight for g in vertex.groups};total=sum(old.values()) or 1
            for group in shoe.vertex_groups:
                weight=old.get(group.index,0)/total*(1-amount)+(amount if group==footgroup else 0)
                if weight>1e-6:group.add([vertex.index],weight,'REPLACE')
                else:group.remove([vertex.index])
        for poly in shoe.data.polygons:
            if poly.center.x*sign>0 and poly.center.z>ankle+.35:poly.material_index=2
    shoe.name='Footwear '+style
