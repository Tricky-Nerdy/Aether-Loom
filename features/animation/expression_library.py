"""Blender operators and scene state for the Aether Loom Expression Library."""

import json
from pathlib import Path

import bpy
from bpy.props import FloatProperty, StringProperty
from bpy.types import Operator

from .expression_presets import is_expression_bone


def _expression_library_path(context):
    raw = context.scene.aether_expression_library_path
    return Path(bpy.path.abspath(raw)).expanduser() if raw else None


def _records(context):
    root = _expression_library_path(context)
    if root is None or not root.is_dir():
        return []
    records = []
    for path in sorted(root.glob("**/*.expression.json")):
        try:
            with path.open("r", encoding="utf-8") as handle:
                preset = json.load(handle)
            if preset.get("schema") == "aether-loom-expression-v1":
                records.append((path, preset))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return records


def _target_armature(context):
    active = context.active_object
    if active and active.type == "ARMATURE":
        return active
    return next((obj for obj in context.view_layer.objects if obj.type == "ARMATURE" and obj.visible_get()), None)


def _capture_face(armature):
    snapshot = {}
    for bone in armature.pose.bones:
        if is_expression_bone(bone.name):
            snapshot[bone.name] = (bone.location.copy(), bone.rotation_quaternion.copy(), bone.scale.copy())
    return snapshot


def _restore_face(armature, snapshot):
    for name, values in snapshot.items():
        bone = armature.pose.bones.get(name)
        if bone:
            bone.rotation_mode = "QUATERNION"
            bone.location, bone.rotation_quaternion, bone.scale = values


def _apply_preset(context, path, preset):
    armature = _target_armature(context)
    if armature is None:
        raise RuntimeError("No visible armature found")
    baseline = getattr(context.scene, "_aether_expression_baseline", None)
    if baseline is None:
        baseline = _capture_face(armature)
        context.scene._aether_expression_baseline = baseline
    _restore_face(armature, baseline)

    strength = context.scene.aether_expression_strength
    for name, transform in preset.get("bones", {}).items():
        bone = armature.pose.bones.get(name) or armature.pose.bones.get(f"LINK-{name}")
        if bone is None:
            continue
        bone.rotation_mode = "QUATERNION"
        rotation = transform.get("Rotation")
        if rotation:
            x, y, z, w = (float(v.strip()) for v in str(rotation).split(","))
            target = bone.rotation_quaternion.__class__((w, x, y, z)).normalized()
            bone.rotation_quaternion = bone.rotation_quaternion.slerp(target, strength)
        position = transform.get("Position")
        if position:
            target = bone.location.__class__(tuple(float(v.strip()) for v in str(position).split(",")))
            bone.location = bone.location.lerp(target, strength)
        scale = transform.get("Scale")
        if scale:
            target = bone.scale.__class__(tuple(float(v.strip()) for v in str(scale).split(",")))
            bone.scale = bone.scale.lerp(target, strength)
    context.scene.aether_expression_current_file = path.name
    context.view_layer.update()


class AETHER_OT_CycleExpression(Operator):
    bl_idname = "aether.cycle_expression"
    bl_label = "Cycle Expression"
    bl_options = {"REGISTER", "UNDO"}

    direction: bpy.props.IntProperty(default=1)  # type: ignore

    def execute(self, context):
        records = _records(context)
        if not records:
            self.report({"WARNING"}, "No expression presets found in the Expression Library")
            return {"CANCELLED"}
        names = [path.name for path, _preset in records]
        current = context.scene.aether_expression_current_file
        index = names.index(current) if current in names else (-1 if self.direction > 0 else 0)
        path, preset = records[(index + self.direction) % len(records)]
        try:
            _apply_preset(context, path, preset)
        except RuntimeError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        return {"FINISHED"}


class AETHER_OT_RefreshExpression(Operator):
    bl_idname = "aether.refresh_expression"
    bl_label = "Refresh Expression"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        current = context.scene.aether_expression_current_file
        match = next(((path, preset) for path, preset in _records(context) if path.name == current), None)
        if match is None:
            return {"CANCELLED"}
        _apply_preset(context, *match)
        return {"FINISHED"}


def _strength_updated(scene, context):
    if scene.aether_expression_current_file:
        try:
            bpy.ops.aether.refresh_expression()
        except RuntimeError:
            pass


def register():
    bpy.utils.register_class(AETHER_OT_CycleExpression)
    bpy.utils.register_class(AETHER_OT_RefreshExpression)
    bpy.types.Scene.aether_expression_library_path = StringProperty(
        name="Expression Library",
        subtype="DIR_PATH",
        default="//expressions/",
    )
    bpy.types.Scene.aether_expression_current_file = StringProperty(default="")
    bpy.types.Scene.aether_expression_strength = FloatProperty(
        name="Blend",
        description="Blend selected expression over the current facial baseline",
        min=0.0,
        max=1.0,
        default=1.0,
        subtype="FACTOR",
        update=_strength_updated,
    )


def unregister():
    for name in ("aether_expression_strength", "aether_expression_current_file", "aether_expression_library_path"):
        if hasattr(bpy.types.Scene, name):
            delattr(bpy.types.Scene, name)
    bpy.utils.unregister_class(AETHER_OT_RefreshExpression)
    bpy.utils.unregister_class(AETHER_OT_CycleExpression)
