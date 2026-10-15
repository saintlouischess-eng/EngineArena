"""Blender: reuse the accepted sculptures at lower detail on distant tables."""
from pathlib import Path
import bpy, hashlib, json
ROOT=Path(__file__).resolve().parents[2]
bpy.ops.wm.read_factory_settings(use_empty=True)
source=ROOT/'ui/staunton1849.glb'
bpy.ops.import_scene.gltf(filepath=str(source))
before=after=0
for obj in list(bpy.data.objects):
    if obj.type!='MESH':continue
    before+=len(obj.data.polygons)
    bpy.context.view_layer.objects.active=obj
    decimate=obj.modifiers.new('Distant table detail','DECIMATE');decimate.ratio=.065
    bpy.ops.object.modifier_apply(modifier=decimate.name)
    after+=len(obj.data.polygons)
    obj.data.materials.clear()
destination=Path(__file__).resolve().parent/'distant-staunton.glb'
bpy.ops.export_scene.gltf(filepath=str(destination),export_format='GLB',export_yup=True)
(destination.with_suffix('.json')).write_text(json.dumps({'source':'ui/staunton1849.glb','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'polygons_before':before,'polygons_after':after,'purpose':'Only background chess tables in the standalone room prototype','output_sha256':hashlib.sha256(destination.read_bytes()).hexdigest()},indent=2),encoding='utf-8')
print(f'Distant pieces: {before} -> {after} polygons')
