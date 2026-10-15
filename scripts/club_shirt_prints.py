"""Bake original front-of-shirt artwork into the existing skinned clothing UVs.

No floating decals, added meshes, transparent passes or runtime texture work.
Positive model X is the wearer's left, matching the armature's .L bones.
"""
import bpy
from pathlib import Path


def apply(cast, outfit):
    spec=cast.get('shirt_print')
    if not spec:return
    root=Path(__file__).resolve().parents[1]
    artwork=bpy.data.images.load(str(root/'prototypes/live-club/art'/spec['file']),check_existing=True)
    mesh=outfit.data;original=mesh.uv_layers[0]
    projected=mesh.uv_layers.new(name='Shirt print projection')
    cx=spec['center_x'];cz=spec['center_height']*cast['height'];width=spec['width'];height=spec['height']
    mask=mesh.color_attributes.new(name='Shirt front only',type='FLOAT_COLOR',domain='CORNER')
    for loop in mesh.loops:
        vertex=mesh.vertices[loop.vertex_index];x,y,z=vertex.co
        projected.data[loop.index].uv=((x-cx)/width+.5,(z-cz)/height+.5)
        front=1.0 if y<-.35 and abs(x)<3.7 else 0.0
        mask.data[loop.index].color=(front,front,front,1)
    mesh.uv_layers.active=original;original.active_render=True
    # All clothing slots share this atlas, retaining their original fabric color
    # and normal map. The resulting print deforms with the original skin weights.
    baked=bpy.data.images.new(cast['id']+' printed cloth',width=2048,height=2048,alpha=False)
    slots=[]
    for material in mesh.materials:
        nodes=material.node_tree.nodes;links=material.node_tree.links;p=nodes.get('Principled BSDF')
        initial=set(nodes);base=p.inputs['Base Color'];source=base.links[0].from_socket if base.links else None
        uv=nodes.new('ShaderNodeUVMap');uv.uv_map=projected.name
        texture=nodes.new('ShaderNodeTexImage');texture.image=artwork;texture.extension='CLIP';links.new(uv.outputs['UV'],texture.inputs['Vector'])
        vc=nodes.new('ShaderNodeVertexColor');vc.layer_name=mask.name
        alpha=nodes.new('ShaderNodeMath');alpha.operation='MULTIPLY';links.new(vc.outputs['Color'],alpha.inputs[0]);links.new(texture.outputs['Alpha'],alpha.inputs[1])
        mix=nodes.new('ShaderNodeMixRGB');links.new(alpha.outputs[0],mix.inputs[0]);mix.inputs[1].default_value=base.default_value
        if source:links.new(source,mix.inputs[1])
        links.new(texture.outputs['Color'],mix.inputs[2])
        emit=nodes.new('ShaderNodeEmission');links.new(mix.outputs[0],emit.inputs['Color']);links.new(emit.outputs[0],nodes.get('Material Output').inputs['Surface'])
        target=nodes.new('ShaderNodeTexImage');target.image=baked;nodes.active=target
        slots.append((material,initial,target))
    bpy.ops.object.select_all(action='DESELECT');outfit.select_set(True);bpy.context.view_layer.objects.active=outfit
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=1;scene.render.bake.margin=8
    bpy.ops.object.bake(type='EMIT');baked.pack()
    for material,initial,target in slots:
        nodes=material.node_tree.nodes;links=material.node_tree.links;p=nodes.get('Principled BSDF')
        for node in list(nodes):
            if node not in initial and node!=target:nodes.remove(node)
        links.new(p.outputs['BSDF'],nodes.get('Material Output').inputs['Surface']);links.new(target.outputs['Color'],p.inputs['Base Color'])
        uv=nodes.new('ShaderNodeUVMap');uv.uv_map=original.name;links.new(uv.outputs['UV'],target.inputs['Vector'])
    mesh.uv_layers.remove(projected);mesh.color_attributes.remove(mask)
    print('SHIRT PRINT',cast['id'],spec,flush=True)
