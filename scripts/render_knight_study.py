"""Render the final exported sculpture in neutral clay, without rebaking."""
import sys
from pathlib import Path
import bpy
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'scripts'))
from sculpt_staunton_knight import clay_study
bpy.ops.wm.open_mainfile(filepath=str(root/'media/staunton1849/Engine-Arena-1849.blend'))
clay_study(bpy.data.objects['n'],root/'media/staunton1849/review')
