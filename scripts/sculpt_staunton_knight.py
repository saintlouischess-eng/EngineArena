"""Original contour-and-surface sculpture of an early Staunton knight.

The outline, cheek planes and carving paths are authored coordinates, informed
by the original 1849-50 Entered No. 8 photographs. No third-party mesh is used.
Blender module: call build_knight(base_profile) from the complete set recipe.
"""
import math
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def activate(o):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def apply(o,m):
 activate(o);bpy.ops.object.modifier_apply(modifier=m.name)
def smooth(o):
 for p in o.data.polygons:p.use_smooth=True
 return o
def mesh(name,v,f):
 d=bpy.data.meshes.new(name);d.from_pydata(v,[],f);d.update();bm=bmesh.new();bm.from_mesh(d);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(d);bm.free();o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);return o
def join(parts,name):
 activate(parts[0])
 for o in parts:o.select_set(True)
 bpy.ops.object.join();o=bpy.context.object;o.name=name;return o
def bevel(o,width,segments=4):
 m=o.modifiers.new('Carved edge radius','BEVEL');m.width=width;m.segments=segments;apply(o,m);return o
def subtract(o,c):
 before=len(o.data.polygons);label=c.name;m=o.modifiers.new('Incised detail','BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=c;apply(o,m);bpy.data.objects.remove(c,do_unlink=True)
 if len(o.data.polygons)<before*.65:raise RuntimeError('Carving unexpectedly removed the model: '+label)
 print('Carved',label,len(o.data.polygons),flush=True)
def sphere(name,center,scale):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=40,ring_count=28,location=center);o=bpy.context.object;o.name=name;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return smooth(o)
def spline(points,steps=5,closed=False,limited=True):
 # Centripetal-like limited Catmull interpolation, kept inside each segment's
 # bounds to preserve small mouth and jaw features without overshoot.
 out=[];n=len(points)
 for i in range(n if closed else n-1):
  a=Vector(points[(i-1)%n] if closed or i else points[0]);b=Vector(points[i]);c=Vector(points[(i+1)%n]);d=Vector(points[(i+2)%n] if closed else points[min(i+2,n-1)])
  for j in range(steps):
   t=j/steps;q=.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)
   out.append(tuple(max(min(b[k],c[k]),min(max(b[k],c[k]),q[k])) for k in range(len(b))) if limited else tuple(q))
 if not closed:out.append(tuple(points[-1]))
 return out
def prism(name,outline,half=.14):
 n=len(outline);v=[(x,y,z) for y in (-half,half) for x,z in outline];f=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)];return mesh(name,v,f)
def lathe(profile):
 pp=[]
 for i,(r,z) in enumerate(profile):
  if i==0:pp.append((r,z));continue
  a=profile[i-1];pp.extend([(a[0]*.75+r*.25,a[1]*.75+z*.25),(a[0]*.25+r*.75,a[1]*.25+z*.75)])
 pp.append(profile[-1]);s=128;v=[(r*math.cos(i*math.tau/s),r*math.sin(i*math.tau/s),z) for r,z in pp for i in range(s)];f=[]
 for j in range(len(pp)-1):
  for i in range(s):a=j*s+i;b=j*s+(i+1)%s;f.append((a,b,b+s,a+s))
 return smooth(mesh('Turned knight pedestal',v,f))
def gauss(x,z,cx,cz,rx,rz):return math.exp(-2*((x-cx)**2/rx**2+(z-cz)**2/rz**2))

def build_knight(base_profile):
 # Face points to -X. This continuous contour contains the lips, open mouth,
 # mandibular notch, full cheek, throat and convex breast in one carving.
 outline=[(-.216,.275),(-.250,.309),(-.269,.366),(-.272,.423),(-.247,.494),(-.194,.573),(-.136,.649),(-.091,.717),(-.067,.759),(-.075,.800),
  (-.055,.813),(-.110,.838),(-.153,.875),(-.192,.884),(-.211,.876),(-.232,.900),(-.294,.906),(-.321,.920),(-.357,.922),(-.364,.935),
  (-.328,.946),(-.278,.946),(-.236,.962),(-.247,.978),(-.291,.973),(-.343,.971),(-.372,.985),(-.370,1.007),(-.352,1.017),(-.337,1.039),
  (-.280,1.057),(-.217,1.066),(-.151,1.073),(-.092,1.091),(-.033,1.113),(.032,1.120),(.106,1.110),(.153,1.092),(.191,1.048),(.213,.989),
  (.228,.916),(.233,.833),(.226,.746),(.213,.656),(.197,.572),(.185,.485),(.187,.402),(.202,.330),(.219,.284),(.193,.271),(.10,.267),(-.02,.267),(-.12,.270)]
 # A broad, softly bevelled carving blank retains planes; it is not assembled
 # from balls. The remesh supplies uniform vertices for muscle/face shaping.
 body=prism('Single carved horse blank',spline(outline,4,True),.135)
 bevel(body,.030,6);activate(body);body.data.remesh_voxel_size=.0027;bpy.ops.object.voxel_remesh()
 m=body.modifiers.new('Polish blank','SMOOTH');m.factor=.35;m.iterations=4;apply(body,m)
 boundary=spline(outline[:14]+[(-.290,.912),(-.360,.925),(-.375,.965)]+outline[26:],16,True,False)
 slice_cache={}
 def interval(x,z):
  key=round(z,4)
  if key in slice_cache:return slice_cache[key]
  zz=max(.26701,min(1.11999,z));cross=[]
  for a,b in zip(boundary,boundary[1:]+boundary[:1]):
   if (a[1]<=zz<b[1]) or (b[1]<=zz<a[1]):cross.append(a[0]+(zz-a[1])*(b[0]-a[0])/(b[1]-a[1]))
  cross.sort();pairs=list(zip(cross[::2],cross[1::2]))
  if not pairs:return (-.20,.20)
  slice_cache[key]=min(pairs,key=lambda ab:max(ab[0]-x,x-ab[1],0));return slice_cache[key]
 for vertex in body.data.vertices:
  x,y,z=vertex.co;lo,hi=interval(x,z);cx=(lo+hi)/2;rx=max(.001,(hi-lo)/2)
  # Above the throat, a single smooth head envelope prevents the mouth and
  # jaw contour from imprinting horizontal ridges across the whole cheek.
  blend=max(0,min(1,(z-.76)/.16));blend=blend*blend*(3-2*blend)
  cx=cx*(1-blend)-.069*blend;rx=rx*(1-blend)+.333*blend
  u=max(-1,min(1,(x-cx)/rx));v=max(-1,min(1,y/.135))
  # Map the rounded blank's rectangular sections to full, convex sections.
  # Neck sections are near-elliptical; cheek sections retain broad carved planes.
  head=max(0,min(1,(z-.78)/.17));head=head*head*(3-2*head);power=2.15+.15*head
  xx=cx+rx*u*(max(0,1-abs(v)**power/2))**(1/power)
  depth=.137+.058*gauss(x,z,-.020,.365,.34,.22)-.045*gauss(x,z,-.295,1.024,.16,.12)
  depth+=.027*gauss(x,z,-.055,.905,.14,.13)-.022*gauss(x,z,.140,1.070,.15,.13)
  # Rounded raised cheekbone and muzzle, rather than a broad flat extruded
  # slab. The forehead narrows into the nose in the overhead reference.
  depth+=.015*gauss(x,z,-.225,1.006,.20,.037)+.009*gauss(x,z,-.302,1.024,.08,.055)
  yy=depth*v*(max(0,1-abs(u)**power/2))**(1/power)
  side=1 if y>=0 else -1
  ridge_x=.13-.20*max(0,min(1,(.96-z)/.63))
  relief=.014*math.exp(-((xx-ridge_x)/.065)**2)*math.exp(-((z-.64)/.29)**4)
  vertex.co=(xx,yy+side*relief*abs(v)**2,z)
 body.data.update()
 m=body.modifiers.new('Polished continuous cross-sections','SMOOTH');m.factor=.42;m.iterations=35;apply(body,m)
 smooth(body);bpy.context.view_layer.update()

 def skin(x,z,side,tree=None):
  tree=tree or BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get());hit=tree.ray_cast(Vector((x,side*.6,z)),Vector((0,-side,0)))
  if hit[0] is None:raise ValueError(f'Carving misses the surface at {x:.5f}, {z:.5f}')
  return hit[0].y
 def groove(name,path,width=.006,depth=.003,side=1):
  points=spline(path,6);tree=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get());centers=[Vector((x,skin(x,z,side,tree)+side*(width-depth),z)) for x,z in points]
  v=[];f=[];sides=12
  for j,c in enumerate(centers):
   tangent=(centers[min(j+1,len(centers)-1)]-centers[max(0,j-1)]).normalized();u=Vector((0,1,0));w=tangent.cross(u).normalized();u=w.cross(tangent).normalized()
   taper=math.sin(math.pi*(j+.4)/(len(centers)-.2))**.38;r=width*taper
   c.y-=side*((width-depth)-(r-depth*taper))
   for k in range(sides):a=k*math.tau/sides;v.append(tuple(c+r*(math.cos(a)*u+math.sin(a)*w)))
  for j in range(len(centers)-1):
   for k in range(sides):a=j*sides+k;b=j*sides+(k+1)%sides;f.append((a,b,b+sides,a+sides))
  f.extend([tuple(reversed(range(sides))),tuple(range((len(centers)-1)*sides,len(centers)*sides))]);subtract(body,mesh(name,v,f))
 extras=[]
 for side in (-1,1):
  # Eyelids sit within a carved socket. A small dome remains inside its rim.
  ex,ez=-.074,1.066;sy=skin(ex,ez,side)
  subtract(body,sphere('Recessed almond eye',(ex,sy,ez),(.032,.019,.023)))
  eye=sphere('Inset carved eye',(ex,sy-side*.010,ez),(.018,.010,.013));extras.append(eye)
  groove('Upper eyelid',[(-.111,1.061),(-.099,1.084),(-.068,1.092),(-.041,1.074)],.006,.005,side)
  groove('Lower eyelid',[(-.102,1.052),(-.079,1.043),(-.051,1.050)],.004,.003,side)
  nx,nz=-.315,1.026;ny=skin(nx,nz,side)
  nostril=sphere('Swept nostril',(nx,ny-side*.003,nz),(.029,.022,.014));nostril.rotation_euler.y=-.32;subtract(body,nostril)
  # The elongated cheek, cheekbone and jaw are distinct shallow sculpted planes.
  groove('Mandible sweep',[(.035,1.058),(.035,.994),(.012,.935),(-.025,.891),(-.072,.869),(-.119,.881),(-.159,.911)],.019,.014,side)
  groove('Cheekbone',[(-.263,1.005),(-.218,1.006),(-.165,1.021),(-.122,1.039)],.014,.009,side)
  groove('Masseter crease',[(-.259,.947),(-.216,.936),(-.171,.940),(-.121,.960),(-.083,.977)],.014,.010,side)
  groove('Upper lip',[(-.356,.997),(-.319,.988),(-.276,.990)],.004,.003,side)
  groove('Lower lip',[(-.349,.932),(-.310,.928),(-.278,.933)],.004,.0025,side)
  groove('Throat fold',[(-.008,.807),(.026,.814),(.069,.837),(.092,.865)],.007,.0045,side)
  groove('Neck tendon',[(.126,.979),(.135,.912),(.116,.814),(.082,.702),(.036,.600),(-.022,.492),(-.068,.404)],.018,.013,side)
  groove('Breast carving',[(-.210,.355),(-.211,.401),(-.177,.442),(-.149,.441)],.010,.004,side)
  # Leaf-shaped ears grow from the poll; their rearward sweep follows the
  # original carving instead of the tall upright ears of later knight styles.
  root=Vector((.035,side*.090,1.077));tip=Vector((.107,side*.122,1.150));axis=(tip-root).normalized();u=Vector((0,1,0));w=axis.cross(u).normalized();u=w.cross(axis).normalized();ev=[];ef=[];rings=24;around=24
  for j in range(rings+1):
   t=j/rings;c=root.lerp(tip,t);width=.031*math.sin(math.pi*t)**.8+.001;thick=.012*math.sin(math.pi*t)**.7+.0007
   for k in range(around):
    a=k*math.tau/around;ev.append(tuple(c+w*width*math.cos(a)+u*thick*math.sin(a)))
  for j in range(rings):
   for k in range(around):a=j*around+k;b=j*around+(k+1)%around;ef.append((a,b,b+around,a+around))
  ef.extend([tuple(reversed(range(around))),tuple(range(rings*around,(rings+1)*around))]);ear=mesh('Leaf-shaped carved ear',ev,ef)
  cup=prism('Tapered ear fold',[(.035,1.103),(.092,1.143),(.075,1.111)],.016);cup.location.y=side*.126;bevel(cup,.003,3);subtract(ear,cup);extras.append(smooth(ear))


 # Rebuild a clean, evenly sampled carving surface after the incisions. This
 # removes Boolean slivers and sharp normal seams before the final UV bake.
 activate(body);body.data.remesh_voxel_size=.0018;bpy.ops.object.voxel_remesh()
 m=body.modifiers.new('Final carving polish','SMOOTH');m.factor=.40;m.iterations=12;apply(body,m);smooth(body)
 if len(body.data.polygons)<10000:raise RuntimeError('Invalid polished carving')
 # A small integral upper tooth row sits inside the mouth rather than floating
 # in front of the lips. Its shallow divisions match the carved wooden teeth.
 tooth=bevel(prism('Carved upper tooth row',[(-.347,.960),(-.260,.960),(-.251,.978),(-.346,.980)],.061),.002,3)
 for x in (-.321,-.294,-.270):
  slot=prism('Tooth division',[(x-.0012,.957),(x+.0012,.957),(x+.0012,.969),(x-.0012,.969)],.073);subtract(tooth,slot)
 extras.append(smooth(tooth))

 # A continuous sculpted mane blends into the nape. Grooves run across its
 # curved strip, producing a comb-like carved edge without separate beads.
 spine=spline([(.208,.278),(.213,.330),(.199,.410),(.198,.500),(.217,.600),(.239,.711),(.256,.824),(.251,.929),(.228,1.024),(.190,1.096),(.143,1.125),(.104,1.132),(.067,1.115),(.040,1.090)],10)
 v=[];f=[];sides=24;arc=[0.]
 for a,b in zip(spine,spine[1:]):arc.append(arc[-1]+math.dist(a,b))
 for j,(x,z) in enumerate(spine):
  a=Vector(spine[max(0,j-1)]);b=Vector(spine[min(j+1,len(spine)-1)]);t=(b-a).normalized();rib=(.5+.5*math.cos(arc[j]/arc[-1]*math.tau*37))**.8
  for k in range(sides):
   q=k*math.tau/sides;end=min(1.,(len(spine)-j)/15);y=.057*math.sin(q)*end;crest=max(0,min(1,(z-1.04)/.08));rad=(.035-.013*crest+.006*rib)*end;out=math.cos(q)
   v.append((x-.019+t.y*rad*out,y,z-t.x*rad*out))
 for j in range(len(spine)-1):
  for k in range(sides):a=j*sides+k;b=j*sides+(k+1)%sides;f.append((a,b,b+sides,a+sides))
 f.extend([tuple(reversed(range(sides))),tuple(range((len(spine)-1)*sides,len(spine)*sides))]);mane=smooth(mesh('Continuous comb mane',v,f))
 # Fuse the crest into the carving so the forehead has no separate cap seam.
 body=join([body,mane],'Integral neck and comb');activate(body);body.data.remesh_voxel_size=.0018;bpy.ops.object.voxel_remesh()
 m=body.modifiers.new('Blend mane root','SMOOTH');m.factor=.35;m.iterations=6;apply(body,m)
 result=join([lathe(base_profile),body,*extras],'n');activate(result);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
 # Early Jaques heads are compact, with the muzzle shorter than the base.
 for vertex in result.data.vertices:
  x,y,z=vertex.co
  head=max(0,min(1,(z-.81)/.16));head=head*head*(3-2*head)
  # Every carved component receives the same final proportion correction,
  # including eyes, teeth and ears. This preserves their surface attachment.
  if x<-.07:vertex.co.x=x+(-.07-x)*.13*head
  width_blend=max(0,min(1,(z-.62)/.40));width_blend=width_blend*width_blend*(3-2*width_blend)
  vertex.co.y=y*(1-.31*width_blend)
  # Round the nose/forehead from side to side; do not leave a flat tabletop.
  roof=max(0,min(1,(z-.99)/.08));roof=roof*roof*(3-2*roof)
  vertex.co.z=z-.019*min(1,abs(y)/.12)**2*roof-.020*max(0,min(1,(-x-.05)/.30))*head
 result.data.update()
 m=result.modifiers.new('Interactive carving resolution','DECIMATE');m.ratio=min(1.,125000/sum(len(p.vertices)-2 for p in result.data.polygons));apply(result,m)
 return smooth(result)

def clay_study(knight,folder):
 """Three fixed orthographic views reveal contour, width and cut detail."""
 from pathlib import Path
 folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);scene=bpy.context.scene
 for o in list(scene.objects):o.hide_render=True
 clay=bpy.data.materials.new('Neutral clay inspection');clay.diffuse_color=(.40,.43,.44,1);clay.use_nodes=True;p=clay.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.40,.43,.44,1);p.inputs['Roughness'].default_value=.58
 for i,angle in enumerate([0,math.radians(42),math.pi/2,-math.pi/2]):
  o=knight.copy();o.data=knight.data.copy();scene.collection.objects.link(o);o.hide_render=False;o.location.x=(i-1.5)*1.0;o.rotation_euler.z=angle;o.data.materials.clear();o.data.materials.append(clay)
 bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.006));floor=bpy.context.object;floor.hide_render=False;fm=bpy.data.materials.new('Studio floor');fm.diffuse_color=(.14,.16,.18,1);floor.data.materials.append(fm)
 scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.16,.19,.22,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.25
 for location,energy,size in [((-3,-4,5),450,2.5),((3,-1,3),75,3),((0,3,4),220,3)]:
  bpy.ops.object.light_add(type='AREA',location=location);l=bpy.context.object;l.data.energy=energy;l.data.shape='DISK';l.data.size=size;l.rotation_euler=(Vector((0,0,.65))-l.location).to_track_quat('-Z','Y').to_euler()
 bpy.ops.object.camera_add(location=(0,-6,1.55));cam=bpy.context.object;cam.rotation_euler=(Vector((0,0,.58))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=4.05;scene.camera=cam
 scene.render.engine='CYCLES';scene.cycles.samples=40;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=8
 scene.render.resolution_x=2700;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(folder/'knight-clay-study.png');bpy.ops.render.render(write_still=True)
