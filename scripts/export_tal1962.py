"""Optimize the approved original Tal 1962 sculpture and bake offline materials.

Run in Blender after prototypes/tal1962/build.py --scene-only.
No reference photographs are used by this exporter or embedded in its output.
"""
import json, math
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'media/tal1962';WORK.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'prototypes/tal1962/Tal-1962-Master.blend'))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU'
scene.cycles.samples=8;scene.render.threads_mode='FIXED';scene.render.threads=10
names=dict(zip(['King','Queen','Bishop','Knight','Rook','Pawn'],'kqbnrp'))
models={};slots={};report={}
def activate(o):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
for name,key in names.items():
 o=bpy.data.objects[name];o.hide_set(False);o.hide_render=False;activate(o)
 original=sum(len(p.vertices)-2 for p in o.data.polygons)
 # Retain the approved silhouette and carved knight detail at board zoom.
 mod=o.modifiers.new('Realtime sculpture budget','DECIMATE');mod.ratio=min(1,(60000 if key=='n' else 16000)/original)
 bpy.ops.object.modifier_apply(modifier=mod.name)
 o.name=key;o['design']='Tal 1962';del o['review_only']
 # Match the existing board scale (king 1.84 squares high), preserving ratios.
 for v in o.data.vertices:v.co*=.9
 o.data.update();models[key]=o
 slots[key]=[p.material_index for p in o.data.polygons]
 report[key]={'source_triangles':original,'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),'height':round(max(v.co.z for v in o.data.vertices)-min(v.co.z for v in o.data.vertices),5),'width':round(max(v.co.x for v in o.data.vertices)-min(v.co.x for v in o.data.vertices),5)}
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
 bpy.ops.uv.smart_project(angle_limit=math.radians(78),island_margin=.004)
 bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='DESELECT')
for o in models.values():o.select_set(True)
bpy.context.view_layer.objects.active=models['k'];bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.select_all(action='SELECT');bpy.ops.uv.pack_islands(margin=.004,rotate=True);bpy.ops.object.mode_set(mode='OBJECT')
wood=bpy.data.materials['Natural boxwood — fine longitudinal grain']
ebony=bpy.data.materials['Polished ebony — warm black with restrained luster']
felt=bpy.data.materials['Dark green felt underside']
original_materials={key:list(o.data.materials) for key,o in models.items()}
maps={}
for kind,source in [('boxwood',wood),('ebony',ebony),('normal',wood)]:
 material=source.copy();n=material.node_tree.nodes;l=material.node_tree.links
 p=n.get('Principled BSDF');output=n.get('Material Output')
 if kind!='normal':
  color=p.inputs['Base Color'].links[0].from_socket
  emission=n.new('ShaderNodeEmission');l.new(color,emission.inputs['Color']);l.new(emission.outputs[0],output.inputs[0])
 image=bpy.data.images.new('Tal 1962 '+kind,width=2048,height=2048,alpha=False)
 image.colorspace_settings.name='Non-Color' if kind=='normal' else 'sRGB'
 image.generated_color=(.5,.5,1,1) if kind=='normal' else ((.58,.38,.16,1) if kind=='boxwood' else (.014,.009,.006,1));image.update()
 target=n.new('ShaderNodeTexImage');target.image=image;n.active=target
 for o in models.values():
  o.data.materials.clear();o.data.materials.append(material)
  for p in o.data.polygons:p.material_index=0
 scene.render.bake.margin=12;scene.render.bake.use_clear=False
 print('BAKE',kind,flush=True);bpy.ops.object.bake(type='NORMAL' if kind=='normal' else 'EMIT')
 image.filepath_raw=str(WORK/(kind+'.png'));image.file_format='PNG';image.save();maps[kind]=image
materials={}
for kind in ['boxwood','ebony']:
 m=bpy.data.materials.new('Tal '+kind);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
 p.inputs['Roughness'].default_value=.29 if kind=='boxwood' else .28;p.inputs['Coat Weight'].default_value=.26;p.inputs['Coat Roughness'].default_value=.28
 color=n.new('ShaderNodeTexImage');color.image=maps[kind];l.new(color.outputs['Color'],p.inputs['Base Color'])
 normal=n.new('ShaderNodeTexImage');normal.image=maps['normal'];bump=n.new('ShaderNodeNormalMap');bump.inputs['Strength'].default_value=.5;l.new(normal.outputs['Color'],bump.inputs['Color']);l.new(bump.outputs[0],p.inputs['Normal']);materials[kind]=m
for key,o in models.items():
 o.data.materials.clear()
 for m in original_materials[key]:o.data.materials.append(materials['boxwood'] if m==wood else materials['ebony'] if m==ebony else felt)
 for p,index in zip(o.data.polygons,slots[key]):p.material_index=index
 o.location=(0,0,0)
bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'Tal-1962-Runtime.blend'))
bpy.ops.export_scene.gltf(filepath=str(ROOT/'ui/tal1962.glb'),export_format='GLB',use_selection=True,export_normals=True,export_texcoords=True,export_materials='EXPORT',export_cameras=False,export_lights=False)
report['glb_bytes']=(ROOT/'ui/tal1962.glb').stat().st_size
(WORK/'runtime-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
