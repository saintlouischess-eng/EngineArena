"""Export the saved original Blender model without repeating the texture bake."""
from pathlib import Path
import bpy,json
root=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(root/'media/staunton1849/Engine-Arena-1849.blend'))
bpy.ops.export_scene.gltf(filepath=str(root/'ui/staunton1849.glb'),export_format='GLB',use_selection=True,export_normals=True,export_texcoords=True,export_materials='EXPORT',export_cameras=False,export_lights=False)
report={o.name:{'vertices':len(o.data.vertices),'faces':len(o.data.polygons),'height':round(o.dimensions.z,4),'width':round(o.dimensions.x,4)} for o in bpy.context.selected_objects}
(root/'media/staunton1849/model-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
