"""Original 1849-style playing models and baked wood materials for Engine Arena.

Run with Blender in background mode. No third-party meshes, photos or textures
are embedded. Historical reference URLs and modeling decisions are documented
in docs/STAUNTON_1849.md. All coordinates below are authored geometry.
"""
import argparse,math,sys,json,shutil
from pathlib import Path
import bpy,bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'ui';WORK=ROOT/'media/staunton1849';WORK.mkdir(parents=True,exist_ok=True)
args=argparse.ArgumentParser();args.add_argument('--no-bake',action='store_true');args.add_argument('--clay-preview',action='store_true');args.add_argument('--queen-preview',action='store_true');args.add_argument('--proportion-preview',action='store_true');args.add_argument('--reuse-other-pieces',action='store_true');args.add_argument('--reuse-pieces',nargs='+',choices=list('kqbnrp'));opts=args.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=False
scene.cycles.device='CPU';scene.render.threads_mode='FIXED';scene.render.threads=8
scene.world.color=(.2,.2,.2)

def activate(o):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def finish(o):
 for f in o.data.polygons:f.use_smooth=True
 return o
def apply(o,modifier):
 activate(o);bpy.ops.object.modifier_apply(modifier=modifier.name)
def bevel(o,width=.003,segments=3):
 m=o.modifiers.new('Hand-finished edges','BEVEL');m.width=width;m.segments=segments;apply(o,m)
 return o
def join(objects,name):
 bpy.ops.object.select_all(action='DESELECT')
 for o in objects:o.select_set(True)
 bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();o=bpy.context.object;o.name=name
 return o
def smooth_profile(points,passes=2):
 for _ in range(passes):
  q=[points[0]]
  for a,b in zip(points,points[1:]):q.extend([tuple(.75*x+.25*y for x,y in zip(a,b)),tuple(.25*x+.75*y for x,y in zip(a,b))])
  q.append(points[-1]);points=q
 return points
def lathe(name,profile,segments=96):
 profile=smooth_profile(profile);verts=[(r*math.cos(i*2*math.pi/segments),r*math.sin(i*2*math.pi/segments),z) for r,z in profile for i in range(segments)]
 faces=[]
 for j in range(len(profile)-1):
  for i in range(segments):a=j*segments+i;b=j*segments+(i+1)%segments;faces.append((a,b,b+segments,a+segments))
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);scene.collection.objects.link(o);return finish(o)
def ellipsoid(name,position,scale):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=32,location=position);o=bpy.context.object;o.name=name;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return finish(o)
def box(name,position,scale):
 bpy.ops.mesh.primitive_cube_add(size=1,location=position);o=bpy.context.object;o.name=name;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return o
def boolean(o,cutter):
 before=len(o.data.polygons);label=cutter.name;m=o.modifiers.new('Carved detail','BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=cutter;apply(o,m);bpy.data.objects.remove(cutter,do_unlink=True)
 if len(o.data.polygons)<before*.5:raise RuntimeError('Invalid carving removed the piece: '+label)
def tube(name,points,radius):
 c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.resolution_u=16;c.bevel_depth=radius;c.bevel_resolution=3;c.use_fill_caps=True
 s=c.splines.new('BEZIER');s.bezier_points.add(len(points)-1)
 for v,p in zip(s.bezier_points,points):v.co=p;v.handle_left_type='AUTO';v.handle_right_type='AUTO'
 o=bpy.data.objects.new(name,c);scene.collection.objects.link(o);activate(o);bpy.ops.object.convert(target='MESH');return bpy.context.object
def prism(name,outline,depth):
 n=len(outline);verts=[(x,y,z) for y in (-depth/2,depth/2) for x,z in outline]
 faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
 o=bpy.data.objects.new(name,mesh);scene.collection.objects.link(o);return o

# The low torus foot and ogee shoulder are measured as proportions of the
# reference silhouettes. Each piece has its own diameter and stem/collar.
BASE=[(0,.012),(.27,.012),(.347,.012),(.354,.019),(.354,.046),(.350,.053),(.319,.065),(.308,.078),(.307,.089),(.322,.094),(.344,.108),(.350,.124),(.344,.145),(.317,.176),(.282,.202),(.247,.225),(.241,.236),(.249,.240),(.249,.250),(.238,.256),(.231,.267)]
def foot(scale=1):return [(r*scale,z*scale) for r,z in BASE]
models={}
# A slender concave stem opens progressively into the upper collar.
models['k']=lathe('k',foot(1.09)+[(.24,.30),(.202,.39),(.160,.52),(.137,.67),(.132,.78),(.137,.89),(.159,.99),(.199,1.06),(.245,1.080),(.270,1.092),(.276,1.103),(.270,1.117),(.24,1.130),(.202,1.138),(.204,1.168),(.232,1.186),(.232,1.204),(.21,1.224),(.18,1.230),(.18,1.266),(.191,1.277),(.211,1.365),(.248,1.445),(.253,1.464),(.248,1.478),(.229,1.491),(.188,1.517),(.125,1.541),(.066,1.551),(0,1.552)])
cross_outline=[(-.035,-.035),(-.114,-.066),(-.123,-.055),(-.123,.055),(-.114,.066),(-.035,.035),(-.072,.109),(-.062,.119),(.062,.119),(.072,.109),(.035,.035),(.114,.066),(.123,.055),(.123,-.055),(.114,-.066),(.035,-.035),(.066,-.099),(.055,-.109),(-.055,-.109),(-.066,-.099)]
cross=bevel(prism('Maltese cross',[(x*.72,z+1.686) for x,z in cross_outline],.051),.0030,4)
models['k']=join([models['k'],cross,ellipsoid('Turned globe',(0,0,1.565),(.047,.047,.048)),ellipsoid('Cross finial',(0,0,1.821),(.017,.017,.017))],'k')

models['q']=lathe('q',foot()+[(.217,.29),(.174,.38),(.137,.52),(.121,.65),(.119,.76),(.125,.85),(.144,.93),(.177,.984),(.202,1.004),(.245,1.012),(.251,1.026),(.242,1.040),(.20,1.051),(.17,1.059),(.17,1.087),(.205,1.103),(.209,1.118),(.185,1.132),(.167,1.141),(.167,1.166),(.175,1.174),(.175,1.184),(.162,1.187),(0,1.187)])
# Nine shorter, outward-flared points surround the raised central dome.
# The recessed annular channel keeps the dome distinct from the coronet.
def queen_coronet():
 sides=252;v=[];f=[]  # 28 equal angular samples per crown point.
 rings=smooth_profile([
  (.160,1.177,0,0),(.166,1.191,0,0),(.179,1.222,0,0),
  (.203,1.265,.010,.007),(.225,1.295,.049,.019),
  (.226,1.300,.049,.020),(.219,1.302,.048,.019),
  (.209,1.291,.040,.014),(.194,1.263,.016,.004),
  (.180,1.248,.002,0),(.169,1.246,0,0),(.158,1.253,0,0),
  (.148,1.278,0,0),(.135,1.313,0,0),(.117,1.347,0,0),
  (.090,1.377,0,0),(.057,1.395,0,0),(.022,1.404,0,0),(0,1.405,0,0)
 ],passes=1)
 for r,z,h,dr in rings:
  for i in range(sides):
   a=i*math.tau/sides;point=(.5+.5*math.cos(9*a))**3
   v.append(((r+dr*point)*math.cos(a),(r+dr*point)*math.sin(a),z+h*point))
 for j in range(len(rings)-1):
  for i in range(sides):a=j*sides+i;b=j*sides+(i+1)%sides;f.append((a,b,b+sides,a+sides))
 f.append(tuple(reversed(range(sides))))
 d=bpy.data.meshes.new('Recessed coronet and raised dome');d.from_pydata(v,[],f);d.update();o=bpy.data.objects.new('Recessed coronet and raised dome',d);scene.collection.objects.link(o);return finish(o)
models['q']=join([models['q'],queen_coronet(),ellipsoid('Queen finial',(0,0,1.433),(.043,.043,.044))],'q')

models['b']=lathe('b',foot(.94)+[(.212,.27),(.17,.35),(.123,.50),(.112,.69),(.139,.788),(.202,.805),(.214,.822),(.205,.841),(.16,.85),(.14,.863),(.153,.88),(.153,.90),(.124,.907),(.118,.935),(.119,.97),(.146,1.025),(.161,1.097),(.155,1.166),(.12,1.24),(.07,1.293),(.012,1.335),(0,1.335)])
cut=bevel(box('Deep bishop mitre',(-.040,0,1.26),(.095,.5,.45)),.032,8);cut.rotation_euler.y=-.17;boolean(models['b'],cut)
models['b']=join([models['b'],ellipsoid('Mitre knop',(.024,0,1.344),(.038,.038,.039))],'b')
models['b'].scale.z=.972

models['r']=lathe('r',foot(.95)+[(.239,.268),(.233,.282),(.215,.297),(.214,.323),(.228,.330),(.228,.344),(.204,.354),(.194,.47),(.184,.75),(.189,.88),(.214,.89),(.216,.91),(.245,.916),(.268,.92),(.270,.994),(.263,1.006),(.193,1.006),(.178,.993),(.178,.923),(0,.923)])
for i in range(6):
 a=2*math.pi*i/6;c=box('Rook notch',(.251*math.cos(a),.251*math.sin(a),1.001),(.082,.22,.10));c.rotation_euler.z=a-math.pi/2;boolean(models['r'],c)
bevel(models['r'],.0025,3)
models['r'].scale.z=1.04
models['p']=lathe('p',foot(.69)+[(.146,.202),(.118,.255),(.089,.363),(.082,.427),(.095,.465),(.143,.479),(.153,.487),(.153,.498),(.144,.506),(.107,.516),(.078,.525),(0,.526)])
models['p']=join([models['p'],ellipsoid('Pawn sphere',(0,0,.622),(.114,.114,.114))],'p')

# The knight uses a separately reviewable contour-and-surface sculpture.
sys.path.insert(0,str(ROOT/'scripts'))
from sculpt_staunton_knight import build_knight,clay_study
reuse=opts.reuse_pieces or (['k','b','r','p','n'] if opts.reuse_other_pieces else [])
if reuse:
 # Preserve accepted sculptures while revising selected pieces.
 # The shared texture atlas is still repacked and fully rebaked below.
 for key in list(models):
  if key in reuse:bpy.data.objects.remove(models.pop(key),do_unlink=True)
 keys=list(dict.fromkeys(reuse))
 # Blender retains append-library provenance and will refuse to overwrite
 # that source file. Read a separate local snapshot so the master can save.
 source_path=WORK/'reused-pieces-source.blend';shutil.copy2(WORK/'Engine-Arena-1849.blend',source_path)
 with bpy.data.libraries.load(str(source_path),link=False) as (source,loaded):
  if not all(key in source.objects for key in keys):raise RuntimeError('Missing accepted sculptures for selective rebuild')
  loaded.objects=list(keys)
 for key,o in zip(keys,loaded.objects):scene.collection.objects.link(o);o.name=key;models[key]=o
if 'n' not in models:models['n']=build_knight(foot(.94)+[(.232,.260),(.225,.272),(.19,.277),(0,.277)])
if opts.proportion_preview:
 bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'proportion-sculpt-review.blend'))
 from study_staunton_set import render_studies
 render_studies(models,WORK/'review',proportions=True)
 raise SystemExit(0)
if opts.queen_preview:
 bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'queen-sculpt-review.blend'))
 from study_staunton_set import render_studies
 render_studies(models,WORK/'review',only_queen=True)
 raise SystemExit(0)
if opts.clay_preview:
 bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'knight-sculpt-review.blend'))
 clay_study(models['n'],WORK/'review')
 from study_staunton_set import render_studies
 render_studies(models,WORK/'review')
 raise SystemExit(0)

# A shared original wood shader is baked to an atlas. Grain follows the timber
# through curves and end grain; it is not painted as screen-space stripes.
wood=bpy.data.materials.new('French-polished boxwood');wood.use_nodes=True;n=wood.node_tree.nodes;l=wood.node_tree.links;n.clear()
output=n.new('ShaderNodeOutputMaterial');p=n.new('ShaderNodeBsdfPrincipled');l.new(p.outputs['BSDF'],output.inputs['Surface']);p.inputs['Roughness'].default_value=.24;p.inputs['Coat Weight'].default_value=.27;p.inputs['Coat Roughness'].default_value=.19
coord=n.new('ShaderNodeTexCoord');stretch=n.new('ShaderNodeVectorMath');stretch.operation='MULTIPLY';stretch.inputs[1].default_value=(5.,5.,.28);l.new(coord.outputs['Generated'],stretch.inputs[0])
grain=n.new('ShaderNodeTexNoise');grain.inputs['Scale'].default_value=5.2;grain.inputs['Detail'].default_value=4.;grain.inputs['Roughness'].default_value=.64;l.new(stretch.outputs[0],grain.inputs['Vector'])
fine=n.new('ShaderNodeTexNoise');fine.inputs['Scale'].default_value=42.;fine.inputs['Detail'].default_value=2.;l.new(stretch.outputs[0],fine.inputs['Vector'])
mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=.24;l.new(grain.outputs['Fac'],mix.inputs[1]);l.new(fine.outputs['Fac'],mix.inputs[2])
ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.10;ramp.color_ramp.elements[0].color=(.31,.164,.068,1);ramp.color_ramp.elements[1].position=.78;ramp.color_ramp.elements[1].color=(.48,.302,.142,1);l.new(mix.outputs[0],ramp.inputs[0]);l.new(ramp.outputs[0],p.inputs['Base Color'])
# Bake restrained cavity shading into the wood color so small incisions remain
# legible under the app's broad environment lights, without painted black lines.
ao=n.new('ShaderNodeAmbientOcclusion');ao.inputs['Distance'].default_value=.055;ao.samples=16;ao.only_local=True
cavity=n.new('ShaderNodeMixRGB');cavity.blend_type='MULTIPLY';cavity.inputs[0].default_value=.30;l.new(ramp.outputs[0],cavity.inputs[1]);l.new(ao.outputs['AO'],cavity.inputs[2])
bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.18;bump.inputs['Distance'].default_value=.0006;l.new(fine.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],p.inputs['Normal'])
rough=n.new('ShaderNodeMapRange');rough.inputs['To Min'].default_value=.32;rough.inputs['To Max'].default_value=.41;l.new(grain.outputs['Fac'],rough.inputs[0]);l.new(rough.outputs[0],p.inputs['Roughness'])
for i,(key,o) in enumerate(models.items()):
 activate(o);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);finish(o);o.data.materials.clear();o.data.materials.append(wood)
 o.location.x=i*2
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(78),island_margin=.003);bpy.ops.object.mode_set(mode='OBJECT')
# Pack all piece islands into the same atlas without losing their object space.
bpy.ops.object.select_all(action='DESELECT')
for o in models.values():o.select_set(True)
bpy.context.view_layer.objects.active=models['k'];bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.select_all(action='SELECT');bpy.ops.uv.pack_islands(margin=.003,rotate=True);bpy.ops.object.mode_set(mode='OBJECT')
maps={}
for kind in ('color','normal','roughness'):
 path=WORK/f'wood-{kind}.png'
 if opts.no_bake and path.exists():
  image=bpy.data.images.load(str(path),check_existing=False);image.colorspace_settings.name='sRGB' if kind=='color' else 'Non-Color'
 else:
  image=bpy.data.images.new('1849 wood '+kind,width=4096,height=4096,alpha=False);image.colorspace_settings.name='sRGB' if kind=='color' else 'Non-Color'
  # Neutral material-colored padding prevents black fringes on tiny UV
  # islands and mip levels; every covered texel is still baked from the shader.
  image.generated_color={'color':(.39,.225,.10,1),'normal':(.5,.5,1,1),'roughness':(.365,.365,.365,1)}[kind];image.update()
  target=n.new('ShaderNodeTexImage');target.image=image;n.active=target
  if kind=='normal':l.new(p.outputs[0],output.inputs[0]);bake='NORMAL'
  else:
   emission=n.new('ShaderNodeEmission');l.new(cavity.outputs[0] if kind=='color' else rough.outputs[0],emission.inputs['Color']);l.new(emission.outputs[0],output.inputs[0]);bake='EMIT'
  scene.cycles.samples=64 if kind=='color' else 8
  scene.render.bake.margin=20;scene.render.bake.use_clear=False;bpy.ops.object.bake(type=bake)
  image.filepath_raw=str(path);image.file_format='PNG';image.save();n.remove(target)
 maps[kind]=image
# Export standard material textures so the app uses the same baked surfaces.
n.clear();output=n.new('ShaderNodeOutputMaterial');p=n.new('ShaderNodeBsdfPrincipled');l.new(p.outputs[0],output.inputs[0]);p.inputs['Coat Weight'].default_value=.27;p.inputs['Coat Roughness'].default_value=.18
for kind in maps:
 tex=n.new('ShaderNodeTexImage');tex.image=maps[kind]
 if kind=='color':l.new(tex.outputs['Color'],p.inputs['Base Color'])
 elif kind=='normal':normal=n.new('ShaderNodeNormalMap');l.new(tex.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs[0],p.inputs['Normal'])
 else:l.new(tex.outputs['Color'],p.inputs['Roughness'])
for o in models.values():o.location=(0,0,0)
bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'Engine-Arena-1849.blend'))
bpy.ops.export_scene.gltf(filepath=str(OUT/'staunton1849.glb'),export_format='GLB',use_selection=True,export_normals=True,export_texcoords=True,export_materials='EXPORT',export_cameras=False,export_lights=False)
report={key:{'vertices':len(o.data.vertices),'faces':len(o.data.polygons),'height':round(o.dimensions.z,4),'width':round(o.dimensions.x,4)} for key,o in models.items()}
(WORK/'model-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
