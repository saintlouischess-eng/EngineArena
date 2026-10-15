"""Build compact CC0 background head from MakeHuman sources (see vendor/MakeHuman).
Run with Blender --background --python scripts/build_room_characters.py.
Only the clothed scene uses this head. No full body or helpers are exported.
"""
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'vendor/MakeHuman'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
def read_obj(name,keep=lambda group,verts:True):
    vertices=[];uv=[];faces=[];faceuv=[];group='';
    for line in (SRC/name).read_text().splitlines():
        parts=line.split()
        if not parts:continue
        if parts[0]=='v':vertices.append(tuple(map(float,parts[1:4])))
        elif parts[0]=='vt':uv.append(tuple(map(float,parts[1:3])))
        elif parts[0]=='g':group=' '.join(parts[1:])
        elif parts[0]=='f':
            refs=[part.split('/') for part in parts[1:]];ids=[int(p[0])-1 for p in refs]
            if keep(group,[vertices[i] for i in ids]):faces.append(ids);faceuv.append([uv[int(p[1])-1] if len(p)>1 and p[1] else (0,0) for p in refs])
    if name=='short02.obj':
        # MHCLO fits the authored hairstyle to the neutral base mesh using
        # barycentric anchors, rather than guessing an offset from its OBJ.
        base=[tuple(map(float,l.split()[1:4])) for l in (SRC/'base.obj').read_text().splitlines() if l.startswith('v ')]
        lines=(SRC/'short02.mhclo').read_text().splitlines();scale=[1.,1.,1.];fitting=False;fitted=[]
        for line in lines:
            parts=line.split()
            if not parts or parts[0].startswith('#'):continue
            if parts[0] in ('x_scale','y_scale','z_scale'):
                axis='xyz'.index(parts[0][0]);scale[axis]=abs(base[int(parts[1])][axis]-base[int(parts[2])][axis])/float(parts[3])
            elif parts[0]=='verts':fitting=True
            elif fitting:
                if len(parts)!=9:break
                ids=list(map(int,parts[:3]));weights=list(map(float,parts[3:6]));delta=list(map(float,parts[6:9]));fitted.append(tuple(sum(base[ids[i]][axis]*weights[i] for i in range(3))+delta[axis]*scale[axis] for axis in range(3)))
        assert len(fitted)==len(vertices),(len(fitted),len(vertices))
        vertices=fitted
    used=sorted(set(i for f in faces for i in f));mapping={i:j for j,i in enumerate(used)}
    # Blender Z-up, Three's glTF importer converts back to Y-up. Head center 7.2.
    points=[(vertices[i][0]*1.65,-(vertices[i][2]-.35)*1.65,(vertices[i][1]-7.2)*1.65) for i in used]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(points,[],[[mapping[i] for i in f] for f in faces]);mesh.update();layer=mesh.uv_layers.new()
    for poly,coords in zip(mesh.polygons,faceuv):
        poly.use_smooth=True
        for loop,xy in zip(poly.loop_indices,coords):layer.data[loop].uv=xy
    ob=bpy.data.objects.new(name[:-4],mesh);bpy.context.collection.objects.link(ob);return ob

def material(name,texture=None,color=(1,1,1,1),alpha=False):
    m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=color;p.inputs['Roughness'].default_value=.80
    if texture:
        im=bpy.data.images.load(str(SRC/texture));im.scale(1024,1024);im.pack();t=m.node_tree.nodes.new('ShaderNodeTexImage');t.image=im;m.node_tree.links.new(t.outputs['Color'],p.inputs['Base Color'])
        if alpha:m.node_tree.links.new(t.outputs['Alpha'],p.inputs['Alpha']);m.surface_render_method='DITHERED'
    return m
head=read_obj('base.obj',lambda group,v:group=='body' and min(p[1] for p in v)>5.82);head.name='head';head.data.materials.append(material('Skin','skin.png'))
# Close-cropped hair under the fine alpha strands, following the actual scalp.
scalp=read_obj('base.obj',lambda group,v:group=='body' and all(p[1] > (7.68 if p[2]>.65 else 6.94 if p[2]<.05 else 7.38) for p in v));scalp.name='scalp';scalp.scale=(1.017,1.017,1.017);scalp.data.materials.append(material('Crop',color=(.075,.05,.032,1)))
hair=read_obj('short02.obj');hair.name='hair';hair.data.materials.append(material('Hair','short02_diffuse.png',alpha=True))
# Small inset eyes, with iris layered on the positive facing side.
for side in [-1,1]:
    x=side*.308*1.65;z=(7.284-7.2)*1.65;y=-(1.245-.35)*1.65
    for name,scale,center,col in [('eye',(.22,.215,.21),(x,y,z),(.80,.77,.70,1)),('iris',(.097,.035,.098),(x,y-.205,z),(.14,.19,.13,1)),('pupil',(.046,.015,.053),(x,y-.235,z),(.008,.007,.006,1))]:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,location=center);o=bpy.context.object;o.name=name;o.scale=scale;o.data.materials.append(material(name,color=col))
        for poly in o.data.polygons:poly.use_smooth=True
bpy.ops.export_scene.gltf(filepath=str(ROOT/'ui/room-head.glb'),export_format='GLB',export_yup=True,export_animations=False,export_materials='EXPORT',export_image_format='AUTO')
print('Built',ROOT/'ui/room-head.glb')
