import bpy
from ...properties.tab_prop import get_active_tab
from ...utils.ui_visibility import visible_in_current_area

class AETHER_PT_ExportPanel(bpy.types.Panel):
    bl_label = "Export"
    bl_idname = "AETHER_PT_export_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'  
    bl_category = 'AetherBlend'
    bl_order = 3 
    
    @classmethod
    def poll(cls, context):
        return visible_in_current_area(context) and get_active_tab(context) == 'IMPORT_EXPORT'

    def draw(self, context):
        layout = self.layout

        pose_box = layout.box()
        pose_box.label(text="Pose Library Browser", icon="POSE_HLT")
        current_pose = context.scene.aether_pose_current_file or "Choose a pose…"
        if len(current_pose) > 52:
            current_pose = current_pose[:49] + "…"
        row = pose_box.row(align=True)
        previous = row.operator("aether.cycle_pose", text="", icon="TRIA_LEFT")
        previous.direction = -1
        row.label(text=current_pose, icon="POSE_HLT")
        following = row.operator("aether.cycle_pose", text="", icon="TRIA_RIGHT")
        following.direction = 1
        pose_box.operator("aether.open_root_pose_menu", text="Browse by People / Action...", icon="VIEWZOOM")
        pose_box.operator("aether.pose_import", text="Open Pose File Browser...", icon="FILE_FOLDER")

        row = layout.row(align=True)
        row.operator("aether.anim_import", text="Anim Import", icon="IMPORT")

        # Export Operators
        row = layout.row(align=True)
        row.operator("aether.pose_export", text="Pose Export", icon = "EXPORT")
        row = layout.row(align=True)
        row.operator("aether.anim_export", text="Anim Export", icon = "EXPORT")
        

def menu_func_export(self, context):
    """Add the export operator to the File > Export menu"""
    self.layout.operator("aether.pose_export", text="AB Pose")
    self.layout.operator("aether.anim_export", text="AB Animation")

def register():
    bpy.utils.register_class(AETHER_PT_ExportPanel)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_class(AETHER_PT_ExportPanel)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
