"""Blender UI for connecting to existing XIVTools exports (read-only)."""
import bpy
from bpy.props import StringProperty
from bpy.types import Operator, Panel

from .xivtools_connection import inspect_paths


class AETHER_OT_ScanXIVToolsExports(Operator):
    bl_idname = "aether.scan_xivtools_exports"
    bl_label = "Scan FFXIV Exports"
    bl_description = "Validate paths and discover already exported models, poses and character presets"

    def execute(self, context):
        scene = context.scene
        result = inspect_paths(scene.aether_ffxiv_game_path,
                               scene.aether_xivtools_path,
                               scene.aether_xivtools_export_path)
        for problem in result["problems"]:
            self.report({"WARNING"}, problem)
        counts = {key: len(value) for key, value in result["files"].items()}
        scene.aether_xivtools_scan_summary = (
            f'Models: {counts["models"]} | Poses: {counts["poses"]} | Characters: {counts["characters"]}'
        )
        self.report({"INFO"}, scene.aether_xivtools_scan_summary)
        return {"FINISHED"} if result["connected"] else {"CANCELLED"}


class AETHER_OT_DetectXIVTools(Operator):
    bl_idname = "aether.detect_xivtools"
    bl_label = "Detect XIVTools Paths"

    def execute(self, context):
        settings = discover_xivtools_settings()
        if not settings["config_found"]:
            self.report({"WARNING"}, "XIVTools settings.json not found")
            return {"CANCELLED"}
        if settings["game"]:
            context.scene.aether_ffxiv_game_path = settings["game"]
        if settings["mods"] and not context.scene.aether_xivtools_export_path:
            context.scene.aether_xivtools_export_path = settings["mods"]
        self.report({"INFO"}, "Detected XIVTools game and mods paths")
        return {"FINISHED"}


class AETHER_PT_XIVToolsConnection(Panel):
    bl_label = "FFXIV / XIVTools Connection"
    bl_idname = "AETHER_PT_xivtools_connection"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Aether Loom"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.prop(scene, "aether_ffxiv_game_path")
        layout.prop(scene, "aether_xivtools_path")
        layout.prop(scene, "aether_xivtools_export_path")
        layout.operator("aether.detect_xivtools", icon="FILE_FOLDER")
        layout.operator("aether.scan_xivtools_exports", icon="FILE_REFRESH")
        layout.label(text=scene.aether_xivtools_scan_summary)
        layout.label(text="Read-only scan; automatic export not yet supported")


CLASSES = (AETHER_OT_ScanXIVToolsExports, AETHER_OT_DetectXIVTools, AETHER_PT_XIVToolsConnection)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.aether_ffxiv_game_path = StringProperty(name="FFXIV Game", subtype="DIR_PATH")
    bpy.types.Scene.aether_xivtools_path = StringProperty(name="XIVTools Path", subtype="FILE_PATH")
    bpy.types.Scene.aether_xivtools_export_path = StringProperty(name="Export Folder", subtype="DIR_PATH")
    bpy.types.Scene.aether_xivtools_scan_summary = StringProperty(default="Not scanned")


def unregister():
    for name in ("aether_ffxiv_game_path", "aether_xivtools_path",
                 "aether_xivtools_export_path", "aether_xivtools_scan_summary"):
        if hasattr(bpy.types.Scene, name):
            delattr(bpy.types.Scene, name)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
