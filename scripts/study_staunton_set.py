"""Orthographic geometry reviews, with identical light and no wood distraction."""
import math
from pathlib import Path
import bpy
from mathutils import Vector


def render_studies(models, folder, only_queen=False, proportions=False):
 folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);scene=bpy.context.scene
 clay=bpy.data.materials.new('Set review clay');clay.use_nodes=True
 p=clay.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.36,.39,.40,1);p.inputs['Roughness'].default_value=.52
 def frame(name,keys,angles,camera,target,scale,width=2400,height=1250):
  for o in scene.objects:o.hide_render=True
  spacing=.90 if len(keys)>3 else .82
  for i,key in enumerate(keys):
   o=models[key].copy();o.data=models[key].data.copy();scene.collection.objects.link(o);o.hide_render=False;o.location=(spacing*(i-(len(keys)-1)/2),0,0);o.rotation_euler.z=angles[i];o.data.materials.clear();o.data.materials.append(clay)
  bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.006));floor=bpy.context.object;floor.hide_render=False
  floor.data.materials.append(clay)
  scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.18,.20,.23,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
  for loc,power,size in [((-3,-4,6),620,3),((4,-2,4),150,4),((0,4,5),380,3)]:
   bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(Vector((0,0,.8))-o.location).to_track_quat('-Z','Y').to_euler()
  bpy.ops.object.camera_add(location=camera);cam=bpy.context.object;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=scale;scene.camera=cam
  scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=8
  scene.render.resolution_x=width;scene.render.resolution_y=height;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(folder/name);bpy.ops.render.render(write_still=True)
 if not only_queen:
  frame('set-clay-front.png',['k','q','b','n','r','p'],[0,0,0,math.pi/2,0,0],(0,-8,.91),(0,0,.91),5.7,2700,1150)
  frame('set-clay-three-quarter.png',['k','q','b','n','r','p'],[0,0,0,.60,0,0],(0,-8,3.5),(0,0,.85),5.7,2700,1250)
 if proportions:
  frame('proportions-clay-front.png',['k','q','b'],[0,0,0],(0,-6,.91),(0,0,.91),3.0,2100,1500)
  frame('bishop-clay-finial.png',['b','b'],[0,math.pi/2],(0,-5,1.35),(0,0,1.20),1.4,2100,1250)
  return
 frame('queen-clay-profile.png',['q','q'],[0,.32],(0,-5,1.25),(0,0,1.25),1.7,2100,1150)
 frame('queen-clay-crown.png',['q','q'],[0,.32],(0,-5,3.5),(0,0,1.17),1.7,2100,1150)
 frame('queen-clay-overhead.png',['q'],[0],(0,-.001,5),(0,0,1.30),.80,1200,1200)


if __name__=='__main__':
 root=Path(__file__).resolve().parents[1]
 bpy.ops.wm.open_mainfile(filepath=str(root/'media/staunton1849/Engine-Arena-1849.blend'))
 render_studies({key:bpy.data.objects[key] for key in 'kqbnrp'},root/'media/staunton1849/review')
