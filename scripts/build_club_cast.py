"""Build individually fitted club players and visitors. Blender 5.x, no MakeHuman code.
Pinned graphical sources and fitting data: vendor/MakeHuman/club-cast/provenance.json.
The full original meshes are fitted to different morphs and skinned, not cloned
heads on procedural bodies. Each exported visitor appears only once in a room.
"""
import bpy, json, math, hashlib, sys, random
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]; SRC=ROOT/'vendor/MakeHuman/club-cast'
sys.path.insert(0,str(ROOT/'scripts'))
import club_cast_details as details
import club_shirt_prints
OUT=ROOT/'prototypes/live-club/cast';OUT.mkdir(parents=True,exist_ok=True)
def obj(path):
    verts=[];uv=[];faces=[];coords=[];groups=[];group=''
    for line in path.read_text().splitlines():
        p=line.split()
        if not p:continue
        if p[0]=='v':verts.append(Vector(map(float,p[1:4])))
        elif p[0]=='vt':uv.append(tuple(map(float,p[1:3])))
        elif p[0]=='g':group=' '.join(p[1:])
        elif p[0]=='f':
            refs=[v.split('/') for v in p[1:]];faces.append([int(v[0])-1 for v in refs]);coords.append([uv[int(v[1])-1] if len(v)>1 and v[1] else (0,0) for v in refs]);groups.append(group)
    return verts,faces,coords,groups
base,faces,uv,groups=obj(ROOT/'vendor/MakeHuman/base.obj')
rig=json.loads((SRC/'rigs/default.mhskel').read_text());weights=json.loads((SRC/'rigs/default_weights.mhw').read_text())['weights']
vertex_weights=[{} for _ in base]
for bone,items in weights.items():
    for i,w in items:vertex_weights[i][bone]=w

def fit(path,body):
    points=[];anchors=[];deleted=set();scales=[1,1,1];section=''
    for line in path.read_text().splitlines():
        p=line.split()
        if not p or p[0].startswith('#'):continue
        if p[0] in ['x_scale','y_scale','z_scale']:
            axis='xyz'.index(p[0][0]);scales[axis]=abs(body[int(p[1])][axis]-body[int(p[2])][axis])/float(p[3])
        elif p[0] in ['verts','delete_verts']:section=p[0]
        elif section=='verts' and p[0][0].isdigit():
            ids=list(map(int,p[:3])) if len(p)>1 else [int(p[0])];w=list(map(float,p[3:6])) if len(p)>1 else [1];d=list(map(float,p[6:9])) if len(p)>1 else [0,0,0]
            points.append(Vector([sum(body[i][axis]*v for i,v in zip(ids,w))+d[axis]*scales[axis] for axis in range(3)]));anchors.append(list(zip(ids,w)))
        elif section=='delete_verts' and p[0][0].isdigit():
            i=0
            while i<len(p):
                a=int(p[i]);i+=1
                if i<len(p) and p[i]=='-':deleted.update(range(a,int(p[i+1])+1));i+=2
                else:deleted.add(a)
        elif p[0] in ['weights','faces','texVerts','texFaces']:section=''
    return points,anchors,deleted

def mat(name,diffuse=None,normal=None,alpha=False,color=None):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF');p.inputs['Roughness'].default_value=.72
    if color:p.inputs['Base Color'].default_value=(*color,1)
    for source,normal_map in [(diffuse,False),(normal,True)]:
        if not source or not source.exists():continue
        im=bpy.data.images.load(str(source),check_existing=False);im.scale(1024,1024)
        if normal_map:im.colorspace_settings.name='Non-Color'
        im.pack();t=n.new('ShaderNodeTexImage');t.image=im
        if normal_map:
            bump=n.new('ShaderNodeNormalMap');bump.inputs['Strength'].default_value=.4;l.new(t.outputs['Color'],bump.inputs['Color']);l.new(bump.outputs['Normal'],p.inputs['Normal'])
        else:
            l.new(t.outputs['Color'],p.inputs['Base Color'])
            if alpha:l.new(t.outputs['Alpha'],p.inputs['Alpha']);m.surface_render_method='DITHERED'
    return m

CAST=[
 dict(id='arthur',macro='caucasian-male-old',body='male-old',face=[('head/head-rectangular',.5),('nose/nose-curve-convex',.3)],clothes='male_casualsuit01',hair='short02',skin='old_lightskinned_male',height=32.4),
 dict(id='mei',macro='caucasian-female-young',body='female-young',face=[('head/head-oval',.45),('head/head-round',.13),('chin/chin-triangle',.12),('nose/nose-scale-horiz-decr',.22),('nose/nose-scale-vert-decr',.12),('mouth/mouth-angles-up',.20),('mouth/mouth-scale-horiz-incr',.12)],clothes='female_casualsuit01',hair='bob02',skin='young_lightskinned_female',height=30.2,hair_color=(.19,.135,.075),portrait='younger-player-reference.png'),
 dict(id='daniel',macro='african-male-young',body='male-young',face=[('chin/chin-width-incr',.35),('nose/nose-scale-horiz-incr',.2)],clothes='male_casualsuit04',hair='afro01',skin='middleage_darkskinned_male',height=33.2),
 dict(id='elena',macro='caucasian-female-old',body='female-old',face=[('head/head-oval',.65),('nose/nose-curve-convex',.25)],clothes='female_elegantsuit01',hair='ponytail01',skin='old_lightskinned_female',height=31.0,hair_tint=(.64,.58,.50),glasses=True),
 dict(id='jonas',macro='caucasian-male-young',body='male-young',weight=.7,face=[('head/head-rectangular',.8),('chin/chin-width-incr',.7),('head/head-fat-incr',.30)],clothes='male_elegantsuit01',hair='short03',skin='middleage_lightskinned_male',height=34.3,standing=True,glasses=True),
 dict(id='nora',macro='african-female-young',body='female-young',weight=.4,face=[('head/head-round',.65),('nose/nose-scale-horiz-incr',.35)],clothes='female_sportsuit01',hair='braid01',skin='middleage_darkskinned_female',height=31.8,standing=True),
]
CAST+=json.loads((ROOT/'scripts/club-cameos.json').read_text(encoding='utf-8'))
PORTRAITS={
 'mei':(632,409,159,674),
 'magnus':(265,244,104,450),'fabiano':(776,244,108,453),
 'hans':(1285,232,120,459),'levy':(.4984,.4944,.2026,.8876),'bobby':(260,729,109,957),'hikaru':(776,750,114,986),
}
records=[]
for cast in CAST:
    if '--only' in sys.argv and cast['id'] not in sys.argv[sys.argv.index('--only')+1].split(','):
        records.append(next(c for c in json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))['cast'] if c['id']==cast['id']));continue
    if '--cameos-only' in sys.argv and not cast.get('cameo'):
        records.append(next(c for c in json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))['cast'] if c['id']==cast['id']));continue
    if '--visitors-only' in sys.argv and not cast.get('standing'):
        records.append(next(c for c in json.loads((OUT/'manifest.json').read_text())['cast'] if c['id']==cast['id']));continue
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    # Each GLB carries only its own rest pose. Blender otherwise exports older
    # compatible armature actions too, so a loader can select somebody else's
    # seated pose for a standing visitor.
    for action in list(bpy.data.actions):bpy.data.actions.remove(action)
    body=[v.copy() for v in base]
    targets=[('macrodetails/'+cast['macro'],1-cast.get('mix',0)),('macrodetails/universal-'+cast['body']+'-averagemuscle-averageweight',1-cast.get('weight',0))]+cast['face']
    if cast.get('weight'):targets.append(('macrodetails/universal-'+cast['body']+'-averagemuscle-maxweight',cast['weight']))
    if cast.get('macro_mix'):targets.append(('macrodetails/'+cast['macro_mix'],cast['mix']))
    for name,amount in targets:
        for line in (SRC/'targets'/f'{name}.target').read_text().splitlines():
            p=line.split()
            if len(p)==4 and p[0].isdigit():body[int(p[0])]+=Vector(map(float,p[1:4]))*amount
    body_ids=set(i for f,g in zip(faces,groups) if g=='body' for i in f);lo=min(body[i].y for i in body_ids);hi=max(body[i].y for i in body_ids);scale=cast['height']/(hi-lo)
    convert=lambda v:Vector((v.x*scale,-v.z*scale,(v.y-lo)*scale))
    if cast.get('portrait'):
        # Widen the eye spacing gently through the eye sockets and helpers.
        # All fitted eye geometry and rig joints then share the same anatomy.
        eye_ids=rig['joints'][rig['bones']['eye.L']['head']]
        eye_level=convert(sum((body[i] for i in eye_ids),Vector())/len(eye_ids)).z
        for v in body:
            p=convert(v);x=abs(p.x)
            falloff=math.exp(-((p.z-eye_level)/.55)**2)*details.smooth(x/.38)*details.smooth((1.50-x)/.45)*details.smooth((-p.y-.65)/.8)
            v.x+=math.copysign(.08/scale*falloff,p.x)
    armdata=bpy.data.armatures.new('Club visitor skeleton');arm=bpy.data.objects.new(cast['id'],armdata);bpy.context.collection.objects.link(arm);bpy.context.view_layer.objects.active=arm;arm.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    for name,b in rig['bones'].items():
        bone=armdata.edit_bones.new(name)
        for attr in ['head','tail']:
            ids=rig['joints'][b[attr]];v=sum((body[i] for i in ids),Vector())/len(ids);setattr(bone,attr,convert(v))
        # The anatomical plane is essential: zero-roll bones make elbows and
        # finger curls bend around arbitrary axes. Local X is the hinge axis.
        plane=rig['planes'].get(b.get('rotation_plane'))
        if plane:
            points=[convert(sum((body[i] for i in rig['joints'][j]),Vector())/len(rig['joints'][j])) for j in plane]
            normal=(points[2]-points[1]).cross(points[1]-points[0])
            if normal.length>1e-8:bone.align_roll(normal.cross(bone.tail-bone.head).normalized())
    for name,b in rig['bones'].items():
        if b.get('parent'):armdata.edit_bones[name].parent=armdata.edit_bones[b['parent']]
    bpy.ops.object.mode_set(mode='OBJECT')
    clothing=SRC/'base/clothes'/cast['clothes']/cast['clothes'];cv,ca,mask=fit(clothing.with_suffix('.mhclo'),body)
    shoe_name='shoes02' if cast['id'] in ['mei','daniel','nora','magnus','hikaru'] else 'shoes01'
    shoes=SRC/'base/clothes'/shoe_name/shoe_name;sv,sa,shoe_mask=fit(shoes.with_suffix('.mhclo'),body);mask|=shoe_mask
    def build(name,verts,fs,uvs,anchors,material):
        used=sorted(set(i for f in fs for i in f));mapping={i:j for j,i in enumerate(used)};mesh=bpy.data.meshes.new(name);mesh.from_pydata([convert(verts[i]) for i in used],[],[[mapping[i] for i in f] for f in fs]);mesh.update();layer=mesh.uv_layers.new()
        for polygon,coords in zip(mesh.polygons,uvs):
            polygon.use_smooth=True
            for loop,xy in zip(polygon.loop_indices,coords):layer.data[loop].uv=xy
        ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob);ob.data.materials.append(material);ob.parent=arm
        vg={n:ob.vertex_groups.new(name=n) for n in weights}
        for orig,idx in mapping.items():
            vw={}
            for anchor,amount in anchors[orig]:
                for bone,w in vertex_weights[anchor].items():vw[bone]=vw.get(bone,0)+amount*w
            vw=sorted(((n,w) for n,w in vw.items() if w>1e-5),key=lambda v:-v[1])[:4];total=sum(w for n,w in vw)
            for n,w in vw:vg[n].add([idx],w/total,'REPLACE')
        mod=ob.modifiers.new('Skin','ARMATURE');mod.object=arm
        return ob
    selected=[i for i,(f,g) in enumerate(zip(faces,groups)) if g=='body' and not any(v in mask for v in f)]
    skin=build('Skin',body,[faces[i] for i in selected],[uv[i] for i in selected],[[(i,1)] for i in range(len(body))],mat('Skin',SRC/'base/skins/textures'/f'{cast["skin"]}_diffuse.png'))
    if cast.get('beard') and not cast.get('cameo'):
        # Original, face-conforming stubble coloring. No downloaded portrait is
        # pasted onto the model or redistributed with the app.
        eyes=[armdata.bones['eye.'+s].head_local for s in ['L','R']];ez=sum(p.z for p in eyes)/2;ey=sum(p.y for p in eyes)/2
        chin=armdata.bones['head'].head_local.z+.1;mouth=chin+.83
        layer=skin.data.color_attributes.new(name='Stubble',type='FLOAT_COLOR',domain='CORNER')
        for loop in skin.data.loops:
            vertex=skin.data.vertices[loop.vertex_index];x,y,z=vertex.co;amount=0
            if chin-.20<z<ez-.65 and y<ey+.45:
                cheek=mouth+.38+abs(x)*.46
                edge=min(1,max(0,(cheek-z)*5))*min(1,max(0,(z-chin+.2)*4))
                lip=((x/.64)**2+((z-mouth)/.19)**2)<1
                if not lip:amount=edge*cast['beard']*(.60+.27*random.Random(loop.vertex_index*173).random())
            layer.data[loop.index].color=(1-amount*.82,1-amount*.87,1-amount*.9,1)
        material=skin.data.materials[0];nodes=material.node_tree.nodes;links=material.node_tree.links;p=nodes.get('Principled BSDF');source=p.inputs['Base Color'].links[0].from_socket
        vc=nodes.new('ShaderNodeVertexColor');vc.layer_name='Stubble';mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;links.new(source,mix.inputs[1]);links.new(vc.outputs['Color'],mix.inputs[2]);links.new(mix.outputs[0],p.inputs['Base Color'])
    _,cf,cu,_=obj(clothing.with_suffix('.obj'));assert len(cv)>max(i for f in cf for i in f)
    outfit=build('Complete outfit',cv,cf,cu,ca,mat('Clothing',clothing.parent/f'{cast["clothes"]}_diffuse.png',clothing.parent/f'{cast["clothes"]}_normal.png'))
    # A small real cloth thickness prevents shoulder/neck skin from poking
    # through the fitted garment when the runtime bends the spine and arms.
    for vertex in outfit.data.vertices:vertex.co+=vertex.normal*.085
    outfit.data.update()
    if cast.get('jacket'):
        material=outfit.data.materials[0];image=next(n.image for n in material.node_tree.nodes if n.type=='TEX_IMAGE' and n.image.colorspace_settings.name!='Non-Color');pixels=list(image.pixels)
        for i in range(0,len(pixels),4):
            lum=sum(pixels[i+c]*w for c,w in enumerate([.2126,.7152,.0722]))
            if lum<.72:
                for c in range(3):pixels[i+c]=cast['jacket'][c]*(.55+lum*2.4)
        image.pixels[:]=pixels;image.pack()
    if cast['id']=='elena':
        # A quiet woven jacket: retain the original seam/fold texture while
        # reducing the loud red stripes to a subtle slate pinstripe.
        image=next(n.image for n in outfit.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE' and n.image.colorspace_settings.name!='Non-Color')
        pixels=list(image.pixels)
        for i in range(0,len(pixels),4):
            lum=sum(pixels[i+c]*w for c,w in enumerate([.2126,.7152,.0722]));value=.10+lum*.20
            pixels[i:i+3]=[value*.72,value*.86,value]
        image.pixels[:]=pixels;image.pack()
    if cast['id']=='nora':
        # Fitted navy underlayer underneath the short sports top: a complete
        # layered outfit, not an exposed midriff in the club.
        low=armdata.bones['upperleg01.L'].head_local.z+.3;high=armdata.bones['spine02'].head_local.z+1.8
        selected_under=[i for i,(f,group) in enumerate(zip(faces,groups)) if group=='body' and all(low<convert(body[j]).z<high and abs(convert(body[j]).x)<4.0 for j in f)]
        under=build('Navy underlayer',body,[faces[i] for i in selected_under],[uv[i] for i in selected_under],[[(i,1)] for i in range(len(body))],mat('Soft navy knit',color=(.025,.055,.12)))
        for vertex in under.data.vertices:vertex.co+=vertex.normal*.08
    if cast['id'] in ['mei','daniel','levy']:
        # Authored fabric material, instead of repeating the source logo jersey.
        colors={'mei':(.13,.24,.19),'daniel':(.27,.17,.10),'levy':(.055,.09,.075),'elena':(.30,.08,.095)}
        fabric=mat('Plain woven fabric',color=cast.get('fabric',colors.get(cast['id'])),normal=clothing.parent/f'{cast["clothes"]}_normal.png');outfit.data.materials.append(fabric)
        waist=armdata.bones['upperleg01.L'].head_local.z+1.0
        for poly in outfit.data.polygons:
            if sum(outfit.data.vertices[i].co.z for i in poly.vertices)/len(poly.vertices)>waist:poly.material_index=1
    club_shirt_prints.apply(cast,outfit)
    _,sf,su,_=obj(shoes.with_suffix('.obj'));shoe=build('Shoes',sv,sf,su,sa,mat('Shoes',shoes.parent/f'{shoe_name}_diffuse.png',shoes.parent/f'{shoe_name}_normal.png'));details.footwear(cast,arm,shoe,mat)
    hair=SRC/'base/hair'/cast['hair']/cast['hair'];hv,ha,_=fit(hair.with_suffix('.mhclo'),body);_,hf,hu,_=obj(hair.with_suffix('.obj'))
    hairmat=mat('Hair',hair.parent/('afro_diffuse.png' if cast['hair']=='afro01' else f'{cast["hair"]}_diffuse.png'),hair.parent/f'{cast["hair"]}_normal.png',True)
    if cast.get('curls'):
        # Short04 supplies a fitted cap under our individual curls. Keep the
        # underlayer opaque; strand cutouts alone leave a visibly bald scalp.
        alpha=hairmat.node_tree.nodes.get('Principled BSDF').inputs['Alpha']
        for link in list(alpha.links):hairmat.node_tree.links.remove(link)
        alpha.default_value=1
    if cast.get('hair_tint'):
        n=hairmat.node_tree.nodes;l=hairmat.node_tree.links;p=n.get('Principled BSDF');source=p.inputs['Base Color'].links[0].from_socket
        tint=n.new('ShaderNodeMixRGB');tint.blend_type='SCREEN';tint.inputs[0].default_value=.8;tint.inputs[2].default_value=(*cast['hair_tint'],1);l.new(source,tint.inputs[1]);l.new(tint.outputs[0],p.inputs['Base Color'])
        # Bake this simple color change into the source image for portable glTF.
        image=source.node.image;pixels=list(image.pixels)
        for i in range(0,len(pixels),4):
            for c in range(3):pixels[i+c]=pixels[i+c]+(1-pixels[i+c])*cast['hair_tint'][c]*.8
        image.pixels[:]=pixels;image.pack();l.new(source,p.inputs['Base Color'])
    if cast.get('hair_dark'):
        image=next(n.image for n in hairmat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image.colorspace_settings.name!='Non-Color');pixels=list(image.pixels)
        for i in range(0,len(pixels),4):
            for c in range(3):pixels[i+c]=.012+pixels[i+c]*[.055,.042,.035][c]
        image.pixels[:]=pixels;image.pack()
    if cast.get('hair_color'):
        image=next(n.image for n in hairmat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image.colorspace_settings.name!='Non-Color');pixels=list(image.pixels)
        for i in range(0,len(pixels),4):
            lum=sum(pixels[i:i+3])/3
            for c in range(3):pixels[i+c]=cast['hair_color'][c]*(.5+lum*1.8)
        image.pixels[:]=pixels;image.pack()
    hairmesh=build('Hair',hv,hf,hu,ha,hairmat)
    # Fitted hair can sit inside a differently morphed forehead. Project any
    # buried vertices beyond the actual scalp, retaining the authored style.
    scalp=BVHTree.FromPolygons([convert(p) for p in body],[f for f,g in zip(faces,groups) if g=='body'])
    eyes=[armdata.bones['eye.'+s].head_local for s in ['L','R']]
    center=sum(eyes,Vector())/2+Vector((0,.9,.7))
    for vertex in hairmesh.data.vertices:
        direction=vertex.co-center;distance=direction.length
        if distance<1e-6:continue
        direction.normalize();hit,_,_,length=scalp.ray_cast(center,direction,10)
        if hit is not None and distance<length+.10:vertex.co=center+direction*(length+.10)
    hairmesh.data.update()
    # Hair follows the skull rigidly. Proxy anchors can reference unweighted
    # helper vertices; inheriting those weights leaves patches behind when
    # the character nods, exposing a false bald area.
    hairmesh.vertex_groups.clear()
    scalp_group=hairmesh.vertex_groups.new(name='head')
    scalp_group.add(list(range(len(hairmesh.data.vertices))),1,'REPLACE')
    if cast.get('curls') and not cast.get('cameo'):
        rng=random.Random(181 if cast['id']=='hans' else 74);vertices=[];polygons=[]
        # Individually laid curls follow the fitted scalp, with a taller crown
        # and looser curls for Hans, a shorter dense cap for Fabiano.
        eyez=armdata.bones['eye.L'].head_local.z
        candidates=[p for p in hairmesh.data.polygons if p.center.z>eyez+.15 and p.normal.z>-.3]
        for _ in range(460):
            poly=rng.choice(candidates);center=sum((hairmesh.data.vertices[i].co for i in poly.vertices),Vector())/len(poly.vertices);normal=poly.normal.normalized();u=normal.cross(Vector((0,1,0)))
            if u.length<.1:u=normal.cross(Vector((1,0,0)))
            u.normalize();v=normal.cross(u);radius=cast['curls']*(.30+rng.random()*.25);center+=u*rng.uniform(-.14,.14)+v*rng.uniform(-.14,.14)+normal*radius*.35;start=len(vertices)
            for j in range(12):
                a=j/11*math.tau*1.3;p=center+u*(math.cos(a)*radius)+v*(math.sin(a)*radius)+normal*(j/11*.09)
                radial=(u*math.cos(a)+v*math.sin(a));vertices.extend(p+(radial*math.cos(k*math.tau/5)+normal*math.sin(k*math.tau/5))*.012 for k in range(5))
            for j in range(11):
                for k in range(5):polygons.append([start+j*5+k,start+j*5+(k+1)%5,start+(j+1)*5+(k+1)%5,start+(j+1)*5+k])
        mesh=bpy.data.meshes.new('Individual curls');mesh.from_pydata(vertices,[],polygons);mesh.update();ob=bpy.data.objects.new('Individual curls',mesh);bpy.context.collection.objects.link(ob);ob.parent=arm;mesh.materials.append(mat('Hair curls',color=cast['hair_color']))
        for p in mesh.polygons:p.use_smooth=True
        vg=ob.vertex_groups.new(name='head');vg.add(list(range(len(vertices))),1,'REPLACE');mod=ob.modifiers.new('Head attachment','ARMATURE');mod.object=arm
    grooming_color=cast.get('hair_color',{'arthur':(.19,.17,.15),'mei':(.012,.009,.007),'daniel':(.012,.009,.007),'elena':(.29,.25,.20),'jonas':(.035,.019,.012),'nora':(.012,.008,.006)}.get(cast['id']))
    if cast.get('portrait'):details.long_hair(cast,arm,skin,hairmesh,mat)
    else:details.hair(cast,arm,skin,hairmesh,mat('Hair natural locks',color=grooming_color))
    # Eye surfaces fitted to each face. The mesh UVs place a painted iris on the
    # front; one original procedural texture avoids glass-marble eyes.
    ev,ea,_=fit(SRC/'eyes/low-poly/low-poly.mhclo',body);_,ef,eu,_=obj(SRC/'eyes/low-poly/low-poly.obj')
    eyesmesh=build('Eyes',ev,ef,eu,ea,mat('Eyes',SRC/'eyes/materials/brown_eye.png'))
    if cast.get('cameo') or cast.get('portrait'):
        # Project the corresponding reference onto the sculpted surface,
        # then bake to the existing skin UVs. This keeps a normal portable PBR
        # material, with actual geometric facial features and no runtime trick.
        px,py,pdist,pchin=PORTRAITS[cast['id']];left=armdata.bones['eye.L'].head_local;right=armdata.bones['eye.R'].head_local;eyez=(left.z+right.z)/2;eyex=(left.x+right.x)/2;ey=(left.y+right.y)/2;chin=armdata.bones['jaw'].tail_local.z
        atlas=bpy.data.images.load(str(ROOT/'prototypes/live-club/art'/cast.get('portrait',('levy-face.png' if cast['id']=='levy' else 'guest-face-atlas.png'))),check_existing=True)
        width,height=atlas.size
        if cast['id']=='levy':px*=width;py*=height;pdist*=width;pchin*=height
        if cast.get('portrait'):
            # Lower-lip cleft and nose tip, derived once from the fitted face.
            mouth=armdata.bones['oris01'].tail_local.z+.025
            nose=min((v.co for v in skin.data.vertices if abs(v.co.x)<.10 and mouth+.25<v.co.z<eyez-.1),key=lambda v:v.y).z
        def projected(ob,uvlayer):
            for loop in ob.data.loops:
                x,y,z=ob.data.vertices[loop.vertex_index].co
                u=(px+(x-eyex)*pdist/abs(left.x-right.x))/width;v=1-(py+(eyez-z)*(pchin-py)/(eyez-chin))/height
                if cast.get('portrait'):
                    pixel_y=py+(eyez-z)*(493-py)/(eyez-nose) if z>=nose else 493+(nose-z)*(559-493)/(nose-mouth) if z>=mouth else 559+(mouth-z)*(pchin-559)/(mouth-chin)
                    v=1-pixel_y/height
                uvlayer.data[loop.index].uv=(u,v)
        for ob in ([skin,eyesmesh] if cast.get('portrait') else [skin]):
            mesh=ob.data;original=mesh.uv_layers[0];projected(ob,mesh.uv_layers.new(name='Portrait'));mesh.uv_layers.active=original
            mask=mesh.color_attributes.new(name='Portrait blend',type='FLOAT_COLOR',domain='CORNER')
            for loop in mesh.loops:
                vert=mesh.vertices[loop.vertex_index];x,y,z=vert.co
                front=max(0,min(1,(ey+.5-y)/.7));low=max(0,min(1,(z-chin+.15)/.45));side=max(0,min(1,(1.85-abs(x))/0.5))
                a=front*low*side;mask.data[loop.index].color=(a,a,a,1)
            material=ob.data.materials[0];nodes=material.node_tree.nodes;links=material.node_tree.links;p=nodes.get('Principled BSDF');base_socket=p.inputs['Base Color'].links[0].from_socket
            uvnode=nodes.new('ShaderNodeUVMap');uvnode.uv_map='Portrait';photo=nodes.new('ShaderNodeTexImage');photo.image=atlas;links.new(uvnode.outputs['UV'],photo.inputs['Vector'])
            portrait_color=photo.outputs['Color']
            if cast.get('portrait') and ob==skin:
                # Match the body skin instead of inheriting photographic shadows.
                # Preserve the reference's brows and lips locally; cheeks, forehead
                # and jaw use the same skin albedo as the neck and arms.
                gamma=nodes.new('ShaderNodeGamma');gamma.inputs['Gamma'].default_value=.80;links.new(portrait_color,gamma.inputs['Color'])
                exposure=nodes.new('ShaderNodeMixRGB');exposure.blend_type='MULTIPLY';exposure.inputs[0].default_value=1;exposure.inputs[2].default_value=(1.4,1.4,1.4,1);links.new(gamma.outputs['Color'],exposure.inputs[1])
                features=mesh.color_attributes.new(name='Portrait features',type='FLOAT_COLOR',domain='CORNER')
                for loop in mesh.loops:
                    u,v=mesh.uv_layers['Portrait'].data[loop.index].uv;ix,iy=u*width,(1-v)*height
                    brow=max(math.exp(-(((ix-cx)/65)**4+((iy-367)/22)**4)) for cx in (551,706))
                    lips=math.exp(-(((ix-638)/85)**4+((iy-548)/25)**4))
                    retained=.06+.84*max(brow,lips)
                    features.data[loop.index].color=(retained,retained,retained,1)
                detail=nodes.new('ShaderNodeVertexColor');detail.layer_name=features.name
                albedo=nodes.new('ShaderNodeMixRGB');links.new(detail.outputs['Color'],albedo.inputs[0]);links.new(base_socket,albedo.inputs[1]);links.new(exposure.outputs[0],albedo.inputs[2]);portrait_color=albedo.outputs[0]
            vc=nodes.new('ShaderNodeVertexColor');vc.layer_name=mask.name;mix=nodes.new('ShaderNodeMixRGB');links.new(vc.outputs['Color'],mix.inputs[0]);links.new(base_socket,mix.inputs[1]);links.new(portrait_color,mix.inputs[2]);emit=nodes.new('ShaderNodeEmission');links.new(mix.outputs[0],emit.inputs[0]);links.new(emit.outputs[0],nodes.get('Material Output').inputs['Surface'])
            baked=bpy.data.images.new(cast['id']+' '+ob.name+' portrait bake',width=2048 if ob==skin else 1024,height=2048 if ob==skin else 1024,alpha=False);target=nodes.new('ShaderNodeTexImage');target.image=baked;nodes.active=target
            bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.context.scene.render.engine='CYCLES';bpy.context.scene.cycles.samples=1;bpy.context.scene.render.bake.margin=8;bpy.ops.object.bake(type='EMIT');baked.pack()
            # Return to a standard lit material and remove baking-only masks.
            links.new(p.outputs['BSDF'],nodes.get('Material Output').inputs['Surface']);links.new(target.outputs['Color'],p.inputs['Base Color']);uvbase=nodes.new('ShaderNodeUVMap');uvbase.uv_map=original.name;links.new(uvbase.outputs['UV'],target.inputs['Vector']);p.inputs['Roughness'].default_value=.70
            for attr in list(mesh.color_attributes):mesh.color_attributes.remove(attr)
        if not cast.get('portrait'):
            projected(eyesmesh,eyesmesh.data.uv_layers[0]);eyeMat=eyesmesh.data.materials[0];eyeTex=next(n for n in eyeMat.node_tree.nodes if n.type=='TEX_IMAGE');eyeTex.image=atlas
    if cast.get('cameo'):
        details.beard(cast,arm,skin,mat('Beard solid fibers',color=(.035,.022,.014) if cast['id']=='levy' else (.028,.020,.014)))
    if cast.get('glasses'):
        vertices=[];polygons=[]
        def tube(points,r=.045,closed=False):
            start=len(vertices)
            for k,p in enumerate(points):
                tangent=(points[(k+1)%len(points)]-points[k-1] if closed else points[min(k+1,len(points)-1)]-points[max(0,k-1)]).normalized();u=tangent.cross(Vector((0,1,0))).normalized();v=tangent.cross(u)
                vertices.extend(p+r*(math.cos(j*math.tau/8)*u+math.sin(j*math.tau/8)*v) for j in range(8))
            for k in range(len(points) if closed else len(points)-1):
                for j in range(8):polygons.append([start+k*8+j,start+k*8+(j+1)%8,start+((k+1)%len(points))*8+(j+1)%8,start+((k+1)%len(points))*8+j])
        eyes=[armdata.bones['eye.'+s].head_local.copy() for s in ['L','R']]
        for eye,sign in zip(eyes,[1,-1]):
            eye.y-=.72
            rx=.48 if cast['id']=='fabiano' else .50;rz=.30 if cast['id'] in ['jonas','fabiano'] else .33 if cast['id']=='levy' else .42
            tube([eye+Vector(((1 if math.cos(a)>=0 else -1)*abs(math.cos(a))**(.45 if cast['id']=='fabiano' else .68 if cast['id']=='levy' else 1)*rx,0,(1 if math.sin(a)>=0 else -1)*abs(math.sin(a))**(.45 if cast['id']=='fabiano' else .68 if cast['id']=='levy' else 1)*rz)) for a in [i*math.tau/48 for i in range(48)]],r=.027 if cast['id']=='fabiano' else .030,closed=True)
            tube([eye+Vector((sign*.59,0,.06)),eye+Vector((sign*.70,.6,.03)),eye+Vector((sign*.65,1.35,-.1))])
        tube([Vector((eyes[0].x-rx+.04,eyes[0].y,eyes[0].z+.07)),Vector((0,min(e.y for e in eyes)-.08,eyes[0].z+.13)),Vector((eyes[1].x+rx-.04,eyes[1].y,eyes[1].z+.07))],.028)
        mesh=bpy.data.meshes.new('Spectacle frames');mesh.from_pydata(vertices,[],polygons);mesh.update();ob=bpy.data.objects.new('Spectacle frames',mesh);bpy.context.collection.objects.link(ob);ob.parent=arm;mesh.materials.append(mat('Brushed spectacle metal',color=(.16,.11,.065) if cast['id']=='elena' else (.35,.32,.28) if cast['id']=='levy' else (.025,.029,.035)))
        for p in mesh.polygons:p.use_smooth=True
        group=ob.vertex_groups.new(name='head');group.add(list(range(len(vertices))),1,'REPLACE');mod=ob.modifiers.new('Head attachment','ARMATURE');mod.object=arm
    # Seated pose, with bone directions solved in world space. Each two-part
    # limb retains the source rig's split/twist joints, preventing joint spikes.
    def aim(name,direction,normal=None):
        pb=arm.pose.bones[name];bpy.context.view_layer.update();m=pb.matrix.copy();current=m.to_3x3()@Vector((0,1,0));rot=current.rotation_difference(Vector(direction).normalized()).to_matrix().to_4x4();loc=m.translation.copy();m.translation=Vector();m=rot@m;m.translation=loc;pb.matrix=m;bpy.context.view_layer.update()
        if normal:
            y=Vector(direction).normalized();x=Vector(normal);x=(x-y*x.dot(y)).normalized();z=x.cross(y);matrix=Matrix((x,y,z)).transposed().to_4x4();matrix.translation=loc;pb.matrix=matrix;bpy.context.view_layer.update()
    for side,sgn in [('L',1),('R',-1)]:
        if cast.get('standing'):
            aim('upperarm01.'+side,(sgn*.12,-.02,-1),(-1,0,0));aim('lowerarm01.'+side,(sgn*-.08,-.12,-1),(-1,0,0));aim('wrist.'+side,(0,-.1,-1))
            # Palms face the thighs, not forward like a mannequin. Spread the
            # rotation along the forearm rather than twisting only the wrist.
            for bone,angle in [('lowerarm01.',.78),('lowerarm02.',.72),('wrist.',.07)]:
                pb=arm.pose.bones[bone+side];m=pb.matrix.copy();pb.rotation_mode='QUATERNION';pb.matrix=m;pb.rotation_quaternion=pb.rotation_quaternion @ __import__('mathutils').Quaternion((0,1,0),sgn*angle);bpy.context.view_layer.update()
            continue
        aim('upperleg01.'+side,(sgn*.08,-1,-.06));aim('lowerleg01.'+side,(sgn*.04,.10,-1));aim('foot.'+side,(0,-1,-.05))
        rest=cast['id']=='arthur' or (cast['id']=='mei' and side=='L') or (cast['id']=='elena' and side=='R')
        aim('upperarm01.'+side,(sgn*.12,-.14,-1),(-1,0,0));aim('lowerarm01.'+side,(sgn*-.12,-1,.08),(-1,0,0));aim('wrist.'+side,(0,-1,0))
    # Hips rest on chair cushion ~8.25 units above the floor; soles follow pose.
    bpy.context.view_layer.update();pelvis=arm.pose.bones['upperleg01.L'].head.z
    arm.location.z=.12 if cast.get('standing') else 9.6-pelvis
    # Curl fingers a little rather than holding the neutral spread-hand pose.
    for pb in arm.pose.bones:
        if pb.name.startswith('finger') and not pb.name.startswith('finger1-'):
            m=pb.matrix.copy();pb.rotation_mode='QUATERNION';pb.matrix=m;pb.rotation_quaternion=pb.rotation_quaternion @ __import__('mathutils').Quaternion((1,0,0),(.20 if '-1.' in pb.name else .32) if cast.get('standing') else (.12 if '-1.' in pb.name else .22))
    for pb in arm.pose.bones:
        m=pb.matrix.copy();pb.rotation_mode='QUATERNION';pb.matrix=m;pb.keyframe_insert('location',frame=1);pb.keyframe_insert('rotation_quaternion',frame=1);pb.keyframe_insert('scale',frame=1)
    if arm.animation_data:arm.animation_data.action.name='Standing rest' if cast.get('standing') else 'Seated rest'
    path=OUT/(cast['id']+'.glb')
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',export_yup=True,export_animations=True,export_materials='EXPORT',export_image_format='AUTO',export_force_sampling=True,export_vertex_color='ACTIVE')
    records.append({**cast,'file':path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(OUT/'manifest.json').write_text(json.dumps({'license':'CC0-1.0 base assets; GPL-3.0-or-later original project artwork','source':'MakeHuman graphical data; see vendor/MakeHuman/club-cast/provenance.json; generated cameo artwork and owner-supplied younger-player reference; see prototypes/live-club/art/PROVENANCE.md','cast':records},indent=2),encoding='utf-8')
print('CLUB CAST COMPLETE',[(r['id'],r['bytes']) for r in records])
