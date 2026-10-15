"""Original Tal-pattern 1962 chess sculptures. Review prototype only.

Run in Blender; no Engine Arena runtime files or production data are accessed.
Reference photographs are modeling guides only and are not used as textures.
"""
import argparse, json, math, sys
from pathlib import Path
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from sculpt_staunton_knight import spline
arg=argparse.ArgumentParser();arg.add_argument('--draft',action='store_true');arg.add_argument('--render-only',action='store_true');arg.add_argument('--scene-only',action='store_true');arg.add_argument('--shot',default='all');args=arg.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene

def activate(o):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def apply(o,m):
 activate(o);bpy.ops.object.modifier_apply(modifier=m.name)
def smooth(o):
 for f in o.data.polygons:f.use_smooth=True
 return o
def mesh(name,v,f):
 d=bpy.data.meshes.new(name);d.from_pydata(v,[],f);d.update();bm=bmesh.new();bm.from_mesh(d);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(d);bm.free()
 o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);return o
def bevel(o,w=.13,n=3):
 m=o.modifiers.new('Soft hand-finished edges','BEVEL');m.width=w;m.segments=n;apply(o,m);return o
def lathe(name,profile,n=128):
 pp=spline(profile,4,False,True);v=[(r*math.cos(i*math.tau/n),r*math.sin(i*math.tau/n),z) for r,z in pp for i in range(n)];f=[]
 for j in range(len(pp)-1):
  for i in range(n):a=j*n+i;b=j*n+(i+1)%n;f.append((a,b,b+n,a+n))
 f.extend([tuple(reversed(range(n))),tuple(range((len(pp)-1)*n,len(pp)*n))]);return smooth(mesh(name,v,f))
def sphere(name,co,size):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=64,ring_count=40,location=co);o=bpy.context.object;o.name=name;o.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return smooth(o)
def cube(name,co,size):
 bpy.ops.mesh.primitive_cube_add(size=1,location=co);o=bpy.context.object;o.name=name;o.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return o
def subtract(o,c):
 before=len(o.data.polygons);label=c.name
 m=o.modifiers.new('Carved recess','BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=c;apply(o,m);bpy.data.objects.remove(c,do_unlink=True)
 if len(o.data.polygons)<before*.55:raise RuntimeError('Unexpected carving loss: '+label)
def join(parts,name):
 activate(parts[0])
 for o in parts:o.select_set(True)
 bpy.ops.object.join();o=bpy.context.object;o.name=name;return o
def material(o,m):
 o.data.materials.clear();o.data.materials.append(m)
 for p in o.data.polygons:p.material_index=0
 return o
def solid(name,color,rough):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;return m

def timber(name,dark=False):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF');p.inputs['Roughness'].default_value=.27;p.inputs['Coat Weight'].default_value=.26;p.inputs['Coat Roughness'].default_value=.20
 p.inputs['IOR'].default_value=1.48
 t=n.new('ShaderNodeTexCoord');stretch=n.new('ShaderNodeVectorMath');stretch.operation='MULTIPLY';stretch.inputs[1].default_value=(3.4,3.4,.16);l.new(t.outputs['Generated'],stretch.inputs[0])
 noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=7;noise.inputs['Detail'].default_value=3;noise.inputs['Roughness'].default_value=.62;l.new(stretch.outputs[0],noise.inputs['Vector'])
 color=n.new('ShaderNodeValToRGB');colors=[(.008,.0055,.0038,1),(.023,.015,.009,1)] if dark else [(.47,.285,.105,1),(.70,.48,.23,1)]
 for e,c in zip(color.color_ramp.elements,colors):e.color=c
 color.color_ramp.elements[0].position=.18;color.color_ramp.elements[1].position=.84;l.new(noise.outputs['Fac'],color.inputs[0]);l.new(color.outputs[0],p.inputs['Base Color'])
 fine=n.new('ShaderNodeTexNoise');fine.inputs['Scale'].default_value=82;fine.inputs['Detail'].default_value=2;l.new(stretch.outputs[0],fine.inputs['Vector'])
 bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.00035;l.new(fine.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],p.inputs['Normal'])
 rough=n.new('ShaderNodeMapRange');rough.inputs['To Min'].default_value=.24 if dark else .27;rough.inputs['To Max'].default_value=.31 if dark else .34;l.new(noise.outputs['Fac'],rough.inputs[0]);l.new(rough.outputs[0],p.inputs['Roughness'])
 m.diffuse_color=colors[1];return m

if not args.render_only:
 WOOD=timber('Natural boxwood — fine longitudinal grain')
 EBONY=timber('Polished ebony — warm black with restrained luster',True)
 FELT=solid('Dark green felt underside',(.014,.055,.028),.95)
 base=[(0,.7),(18.9,.7),(20.5,.7),(20.95,.95),(21,1.3),(21,3),(20.7,3.2),(20.4,3.35),(20.65,3.65),(20.65,6.9),(20.4,9.3),(19.7,11.2),(18.3,12.6),(16.3,13.35),(13.5,13.6)]
 def foot(scale=1):return [(r*scale,z*scale) for r,z in base]
 def collar(z,r=11):
  return [(6.1,z-1.6),(9.8,z-1.1),(r,z-.75),(r+.35,z),(r+.2,z+1.2),(r-.1,z+1.8),(9.2,z+2),(9.2,z+2.2),(9.5,z+2.6),(9.5,z+3.8),(9.15,z+4.1),(6.6,z+4.3),(6.6,z+6),(7.1,z+6.3),(7.3,z+6.6),(7.2,z+7),(6.7,z+7.3)]
 parts={}
 parts['King']=[lathe('King turned body',foot()+[(11.8,14),(10.8,15.5),(9.5,19),(8.2,24),(6.9,32),(6.25,40),(6.1,49),(6.1,60)]+collar(61.7,11.1)+[(6.8,69.4),(7.3,71),(8.2,75),(9.2,80),(10,85),(10.2,86.3),(9.7,87.4),(8.1,88.6),(5.3,89.6),(3.6,90),(0,90)])]
 # Flat, double-notched cross: broad faces, thin edge and softly rounded cuts.
 # This silhouette is extruded, never revolved around the king's axis.
 cross_side=[(2.7,89.7),(3.9,90.3),(4.05,90.8),(3.9,91.4),(1.85,92.35),(1.85,92.65),(3.6,93.3),(3.75,93.8),(3.6,94.15),(1.8,95.0),(1.8,95.45),(4.15,95.45),(4.15,98.8),(1.8,98.8),(1.8,99.35),(3.7,100.3),(3.85,100.85),(3.55,101.55),(2.6,102)]
 cross_outline=cross_side+[(-x,z) for x,z in reversed(cross_side)]
 nn=len(cross_outline);cv=[(x,y,z) for y in [-1.35,1.35] for x,z in cross_outline]
 cf=[tuple(reversed(range(nn))),tuple(range(nn,2*nn))]+[(i,(i+1)%nn,(i+1)%nn+nn,i+nn) for i in range(nn)]
 cross=bevel(mesh('King flat carved cross',cv,cf),.16,4)
 # Broad faces stay planar; the small bevel alone catches the edge light.
 parts['King'].append(cross)
 parts['Queen']=[lathe('Queen turned body',foot()+[(11.9,14),(10.6,16),(9.2,20),(8,25),(6.6,32),(6,40),(6,47),(6.1,52.3)]+collar(53.4,10.8)+[(6.7,60.7),(0,60.7)])]
 # Eight shallow scallops around a raised center, measured from the listing.
 def coronet():
  n=192;v=[];f=[]
  rings=[(6.7,60.7,0),(7.1,64,0),(8.5,69,0),(10.4,74,0),(11.1,77,.9),(10.9,77.6,.9),(10.2,77.7,.85),(9.5,76.7,.8),(8.5,76,.6),(7.3,76.2,.2),(5.7,78.3,0),(4,79.3,0),(2.3,80,0),(0,80,0)]
  for r,z,h in spline(rings,4,False,True):
   for i in range(n):a=i*math.tau/n;v.append((r*math.cos(a),r*math.sin(a),z+h*math.cos(8*a)))
  for j in range(len(v)//n-1):
   for i in range(n):a=j*n+i;b=j*n+(i+1)%n;f.append((a,b,b+n,a+n))
  return smooth(mesh('Queen scalloped coronet',v,f))
 parts['Queen'][0]=join([parts['Queen'][0],coronet(),lathe('Queen ball socket',[(0,79.4),(2.2,79.4),(2.5,80.1),(2.4,82),(0,82)])],'Queen turned body and coronet')
 parts['Queen'].append(sphere('Queen contrasting ball',(0,0,85.5),(3.7,3.7,4.5)))
 parts['Bishop']=[lathe('Bishop turned body',foot()+[(11.7,14.1),(10,16),(8.6,19.5),(7,24),(6.2,29),(5.8,35),(5.8,41.5)]+collar(43.2,11.4)+[(6.9,51),(7.5,53),(8.6,57),(9.2,61),(9,64),(8.2,67),(6.5,70),(4.1,72.4),(1.8,73.5),(0,73.6)])]
 cut=bevel(cube('Bishop diagonal cut',(-2.35,0,70.5),(1.25,28,16)),.13,3);cut.rotation_euler.y=math.radians(-30);subtract(parts['Bishop'][0],cut)
 parts['Bishop'].append(sphere('Bishop contrasting ball',(0,0,76.6),(3.25,3.25,3.4)))
 parts['Rook']=[lathe('Rook tower',foot()+[(13.2,14),(13.1,16.7),(13.2,17),(12.4,17.5),(12,18),(12.1,18.5),(12.5,18.9),(12.5,19.4),(12.2,19.7),(11.8,25),(11.15,34),(10.7,43),(10.8,52.2),(11.1,53),(12.2,53.3),(12.4,54),(12.5,55),(13.4,55.5),(13.7,56.1),(13.7,56.8),(12.9,57.4),(13.3,58),(14.4,65.8),(14.2,67),(10.4,67),(10.2,66.6),(10.1,61.4),(9.8,61),(0,61)])]
 for i in range(6):
  a=i*math.tau/6;c=cube('Six rook battlement gaps',(12.8*math.cos(a),12.8*math.sin(a),65.4),(4,10,5.8));c.rotation_euler.z=a-math.pi/2;subtract(parts['Rook'][0],c)
 bevel(parts['Rook'][0],.17,3)
 # Spread the already-carved crown outward, preserving clean notch walls.
 for v in parts['Rook'][0].data.vertices:
  flare=1+.09*max(0,min(1,(v.co.z-57.5)/9.5))
  v.co.x*=flare;v.co.y*=flare
 parts['Rook'][0].data.update()
 parts['Pawn']=[lathe('Pawn turned body',foot(38/42)+[(10.5,12.7),(8.7,14.4),(7,17),(5.5,21),(4.8,25),(4.9,27.4),(7.6,27.8),(9.6,28.6),(9.8,29.15),(9.3,29.65),(6.2,30),(4.2,30.2),(0,30.2)]),sphere('Pawn broad round head',(0,0,39),(9,9,9))]
 
 def knight():
  pedestal=lathe('Knight spool pedestal',foot()+[(10.8,13.7),(10.5,14.3),(11,15.1),(11,15.9),(10.35,17),(10.1,19),(10.4,21.2),(11,22),(11,22.7),(10.7,23.1),(0,23.1)])
  # Face toward -X. Full chest sweeps left, nape curves right: Tal's S shape.
  outline=[(-10.3,22.7),(-12.4,24.4),(-12.3,27),(-10.8,30.7),(-8.2,34.3),(-4.5,37.9),(.3,41.7),(6.2,45.7),(8.2,47.8),(6.5,48.3),(3.3,48.3),(-1,48.9),(-4.8,50),(-8.6,51.3),(-11.8,52.8),(-14.9,52.4),(-16.4,50.7),(-18.5,50.9),(-19.7,52),(-19.7,53.1),(-18.3,54.1),(-16.5,54.35),(-17,55.25),(-20.0,55.2),(-21.0,56.4),(-21.0,58.5),(-20.1,60.6),(-18.2,62.0),(-13.5,63.0),(-8,63.8),(-2,64.2),(3.2,64.2),(7.1,65.4),(9.5,67.7),(12,66.2),(14.7,62.6),(17,58.1),(18.1,53.6),(18.3,48.5),(17.6,43.2),(16.1,38.7),(14.4,34.8),(12.1,31.3),(10.5,27),(9.8,23),(5,22.7)]
  pp=spline(outline,5,True);n=len(pp);v=[(x,y,z) for y in [-7.4,7.4] for x,z in pp];f=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
  body=bevel(mesh('Tal continuous S carving',v,f),1.25,6);activate(body);body.data.remesh_voxel_size=.18;bpy.ops.object.voxel_remesh();m=body.modifiers.new('Polished carving','SMOOTH');m.factor=.35;m.iterations=6;apply(body,m)
  def interval(z):
   cross=[]
   for a,b in zip(pp,pp[1:]+pp[:1]):
    if a[1]<=z<b[1] or b[1]<=z<a[1]:cross.append(a[0]+(z-a[1])*(b[0]-a[0])/(b[1]-a[1]))
   return (min(cross),max(cross)) if cross else (-10,10)
  cache={}
  for vert in body.data.vertices:
   x,y,z=vert.co;k=round(z,2)
   if k not in cache:cache[k]=interval(z)
   lo,hi=cache[k];cx=(lo+hi)/2;rx=max(1,(hi-lo)/2)
   h=max(0,min(1,(z-40)/16));h=h*h*(3-2*h);cx=cx*(1-h)-1.5*h;rx=rx*(1-h)+20*h
   u=max(-1,min(1,(x-cx)/rx));w=max(-1,min(1,y/7.4));power=2.2+.45*h
   depth=8.8-2.1*h+.8*math.exp(-((z-28)/9)**2)
   # The nose narrows in front view, with broad rounded carved cheeks.
   depth-=1.1*max(0,min(1,(-x-10)/11))*h
   # Keep the photographed silhouette; changing X with the cheek envelope
   # creates a false ledge where the head joins the curved neck.
   neck_mix=max(0,min(1,(52-z)/20));neck_mix=neck_mix*neck_mix*(3-2*neck_mix)
   rounded_x=cx+rx*u*(max(0,1-abs(w)**power/2))**(1/power)
   vert.co.x=x+(rounded_x-x)*neck_mix
   # One continuous cheek surface. A local muscle bulge plus a short vertical
   # blend previously made a raised horizontal ridge across the cheek.
   yy=depth*w*(max(0,1-abs(u)**power/2))**(1/power)
   # Roll the forehead, cheeks and muzzle through their Y/Z section. The
   # earlier extrusion kept a flat roof and straight slab-like cheek edges.
   head_mix=max(0,min(1,(z-45)/3))*max(0,min(1,(13-x)/8))
   head_mix=head_mix*head_mix*(3-2*head_mix)
   cz=56.6;tz=max(-1,min(1,(z-cz)/8.1))
   yy*=1-head_mix*(1-math.sqrt(max(.08,1-.72*tz*tz)))
   zz=cz+(z-cz)*math.sqrt(max(.1,1-.72*w*w))
   # Keep the jaw's depth while smoothly rolling the upper forehead; applying
   # the same vertical compression below the eye makes the head too shallow.
   roll=max(0,min(1,(z-54)/5));roll=.25+.75*roll*roll*(3-2*roll)
   vert.co.y=yy;vert.co.z=z+head_mix*roll*(zz-z)
  body.data.update();m=body.modifiers.new('Continuous muscle surface','SMOOTH');m.factor=.38;m.iterations=28;apply(body,m);smooth(body)
  def skin(x,z,side,tree=None):
   tree=tree or BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get());hit=tree.ray_cast(Vector((x,side*30,z)),Vector((0,-side,0)));return hit[0].y if hit[0] is not None else side*5
  def groove(name,coords,r=.4,depth=.22,side=1):
   pts=spline(coords,5);tree=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get());centers=[Vector((x,skin(x,z,side,tree)+side*(r-depth),z)) for x,z in pts];vv=[];ff=[];sn=12
   for j,c in enumerate(centers):
    tangent=(centers[min(j+1,len(centers)-1)]-centers[max(0,j-1)]).normalized();u=Vector((0,1,0));w=tangent.cross(u).normalized();u=w.cross(tangent).normalized()
    taper=math.sin(math.pi*(j+.35)/(len(centers)-.3))**.4;rad=r*taper;c.y-=side*((r-depth)-(rad-depth*taper))
    for i in range(sn):a=i*math.tau/sn;vv.append(tuple(c+rad*(math.cos(a)*u+math.sin(a)*w)))
   for j in range(len(centers)-1):
    for i in range(sn):a=j*sn+i;b=j*sn+(i+1)%sn;ff.append((a,b,b+sn,a+sn))
   ff.extend([tuple(reversed(range(sn))),tuple(range((len(centers)-1)*sn,len(centers)*sn))]);subtract(body,mesh(name,vv,ff))
  extras=[]
  for s in [-1,1]:
   ex,ez=-6.7,60.25;sy=skin(ex,ez,s);subtract(body,sphere('Recessed circular eye',(ex,sy+s*.08,ez),(1.6,1.4,1.6)));extras.append(sphere('Carved eye bead',(ex,sy-s*.75,ez),(.82,.68,.82)))
   nx,nz=-18.1,58.9;ny=skin(nx,nz,s);subtract(body,sphere('Small nostril',(nx,ny,nz),(.85,1.25,1.0)))
   groove('Rounded jaw carving',[(6.9,62.5),(7.2,59.8),(7.1,56.8),(6.1,53.2),(3.8,50.8),(.4,49.8),(-3.2,50.1),(-7.3,51.1)],.70,.58,s)
   groove('Sculpted brow',[(-8.4,60.8),(-7.8,61.9),(-6.4,62.2),(-5.0,61.5)],.30,.22,s)
   groove('Upper lip crease',[(-19.5,56.3),(-17.9,56),(-16.4,55.9),(-14.8,56.2)],.26,.18,s)
   # Broad, oblique gouges cut across the nape, rather than dashed scratches.
   for i in range(8):
    z=44.0+i*2.8
    groove('Deep combed mane',[(interval(z-2.5)[1]-6.2,z-2.5),(interval(z-.4)[1]-3.8,z-.4),(interval(z+1.5)[1]-1.25,z+1.5)],.58,.68,s)
   # Short pointed paired ears, integrated at the poll.
   ep=[(2.8,63),(2.8,69.8),(3.8,70),(6.1,63.5)];ev=[(x,y+s*3.6,z) for y in [-1.2,1.2] for x,z in ep];ef=[(3,2,1,0),(4,5,6,7)]+[(i,(i+1)%4,(i+1)%4+4,i+4) for i in range(4)];ear=bevel(mesh('Short pointed carved ear',ev,ef),.25,4);extras.append(smooth(ear))
  activate(body);body.data.remesh_voxel_size=.12;bpy.ops.object.voxel_remesh();m=body.modifiers.new('Final carving polish','SMOOTH');m.factor=.28;m.iterations=5;apply(body,m);smooth(body)
  m=body.modifiers.new('Review mesh efficiency','DECIMATE');m.ratio=min(1,125000/max(1,sum(len(p.vertices)-2 for p in body.data.polygons)));apply(body,m)
  carving=join([body,*extras],'Compact Tal head and full chest')
  for v in carving.data.vertices:
   x,y,z=v.co;head=max(0,min(1,(z-47)/7));head=head*head*(3-2*head)
   if x<0:v.co.x=x*(1-.13*head)
   chest=math.exp(-((z-31)/10)**2);v.co.x-=3.1*chest*(1-max(0,min(1,(x+10)/27)))
  carving.data.update();return [pedestal,carving]
 parts['Knight']=knight()
 
 models={};heights={'King':102,'Queen':90,'Bishop':80,'Knight':70,'Rook':67,'Pawn':48}
 for name in ['King','Queen','Bishop','Knight','Rook','Pawn']:
  # The contrasting bishop/queen/king finials are modeled as separate material slots.
  for i,o in enumerate(parts[name]):material(o,EBONY if name in ['King','Queen','Bishop'] and i==1 else WOOD)
  felt=lathe(name+' felt',[(0,0),(20.1 if name!='Pawn' else 18.2,0),(20.1 if name!='Pawn' else 18.2,.7),(0,.7)],96);material(felt,FELT)
  o=join(parts[name]+[felt],name);activate(o);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
  for v in o.data.vertices:v.co*=.02
  o.data.update();models[name]=o;o['height_mm']=heights[name];o['design']='Tal-pattern 1962 prototype';o['review_only']=True
  o.hide_render=True;o.hide_set(True)
  # Inspectable mesh: no camera-dependent details and no borrowed product textures.
  print(name,'triangles',sum(len(f.vertices)-2 for f in o.data.polygons),flush=True)
 
 master=bpy.data.collections.new('MASTER SCULPTURES — review only');scene.collection.children.link(master)
 for o in models.values():
  for c in list(o.users_collection):c.objects.unlink(o)
  master.objects.link(o)
 bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'Tal-1962-Master.blend'))
else:
 bpy.ops.wm.open_mainfile(filepath=str(HERE/'Tal-1962-Master.blend'))
 scene=bpy.context.scene;models={name:bpy.data.objects[name] for name in ['King','Queen','Bishop','Knight','Rook','Pawn']};heights={name:int(o['height_mm']) for name,o in models.items()}
 WOOD=bpy.data.materials['Natural boxwood — fine longitudinal grain'];EBONY=bpy.data.materials['Polished ebony — warm black with restrained luster'];FELT=bpy.data.materials['Dark green felt underside']

stage=bpy.data.collections.new('Review photography');scene.collection.children.link(stage)
def stage_object(o):
 for c in list(o.users_collection):c.objects.unlink(o)
 stage.objects.link(o);return o
floor=stage_object(cube('Studio plinth',(0,0,-.12),(200,200,.23)));material(floor,solid('Slate studio',(.048,.061,.071),.68))
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.27,.32,.38,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.32
def light(name,co,power,size,target,shape='DISK',size_y=None):
 bpy.ops.object.light_add(type='AREA',location=co);o=stage_object(bpy.context.object);o.name=name;o.data.energy=power;o.data.shape=shape;o.data.size=size
 if size_y is not None:o.data.size_y=size_y
 o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();return o
light('Large warm key',(-4,-5,8),950,5,(0,0,.8),'RECTANGLE',7)
light('Soft frontal fill',(5,-2,5),450,5,(0,0,1))
light('Long edge reflection',(-2,5,7),1100,3,(0,0,1),'RECTANGLE',7)
light('Ebony detail fill',(0,-7,3),160,6,(0,0,1),'RECTANGLE',3)
bpy.ops.object.camera_add();camera=stage_object(bpy.context.object);scene.camera=camera;camera.data.type='ORTHO';camera.data.lens=70
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24 if args.draft else 96;scene.cycles.use_denoising=True;scene.cycles.adaptive_threshold=.025 if args.draft else .012
scene.render.threads_mode='FIXED';scene.render.threads=10;scene.cycles.max_bounces=8
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.1
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.resolution_percentage=100
photo=[]
def clear():
 for o in photo:bpy.data.objects.remove(o,do_unlink=True)
 photo.clear()
def piece(name,dark,pos,angle=0):
 src=models[name];o=src.copy();o.data=src.data.copy();stage.objects.link(o);o.hide_render=False;o.hide_set(False);o.location=pos;o.rotation_euler.z=angle
 if dark:
  for i,m in enumerate(o.data.materials):
   if m==WOOD:o.data.materials[i]=EBONY
   elif m==EBONY:o.data.materials[i]=WOOD
 photo.append(o);return o
def render(name,co,target,scale,size):
 camera.location=co;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
 scene.render.resolution_x=size[0]//(2 if args.draft else 1);scene.render.resolution_y=size[1]//(2 if args.draft else 1);scene.render.filepath=str(HERE/'renders'/((name+'-draft' if args.draft else name)+'.png'))
 if args.scene_only:
  for screen in bpy.data.screens:
   for area in screen.areas:
    if area.type=='VIEW_3D':
     area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.shading.type='SOLID';area.spaces.active.shading.color_type='MATERIAL'
  bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'Tal-1962-Review-Scene.blend'));return
 print('RENDER',name,flush=True);bpy.ops.render.render(write_still=True)
order=['King','Queen','Bishop','Knight','Rook','Pawn']
if args.shot in ['all','revised','knight-review','collection']:
 for dark,y in [(True,2.35),(False,-2.35)]:
  for i,name in enumerate(order):piece(name,dark,((i-2.5)*1.24,y,0),math.radians(-12 if name=='Knight' else 0))
 render('Tal-1962-Collection-4K',(0,-17,9),(0,0,.82),8.6,(3840,2160));clear()
if args.shot in ['all','revised','knight-review','knight']:
 for x,a,dark in [(-2.15,0,False),(-.72,math.pi/2,False),(.72,-.6,False),(2.15,-.6,True)]:piece('Knight',dark,(x,0,0),a)
 render('Tal-1962-Knight-Study-4K',(0,-12,4),(0,0,.72),6.2,(3840,2160));clear()
if args.shot in ['all','revised','details']:
 # Cropped head studies show the flat finial's edge and the tower's flare.
 floor.hide_render=True
 for x,a,dark in [(-2.0,0,True),(-.72,math.radians(72),False)]:piece('King',dark,(x,0,-2.6),a).scale=(2,2,2)
 for x,dark in [(.72,False),(2.05,True)]:piece('Rook',dark,(x,0,-1.2),math.radians(15)).scale=(2,2,2)
 render('Tal-1962-Crown-Details-4K',(0,-15,4.5),(0,0,.73),5.55,(3840,2160));clear();floor.hide_render=False
for name in order:
 if args.shot not in ['all',name.lower()] and not (args.shot=='revised' and name in ['King','Knight','Rook']) and not (args.shot=='knight-review' and name=='Knight'):continue
 for x,dark in [(-.68,False),(.68,True)]:piece(name,dark,(x,0,0),-.45 if name=='Knight' else 0)
 h=heights[name]*.02;render('Tal-1962-'+name,(0,-12,5.4),(0,0,h*.47),max(2.55,h*1.4),(2160,2160));clear()
(HERE/'geometry.json').write_text(json.dumps({name:{'height_mm':heights[name],'triangles':sum(len(p.vertices)-2 for p in o.data.polygons)} for name,o in models.items()},indent=2))
print('REVIEW PROTOTYPE COMPLETE — not installed in Engine Arena',flush=True)
