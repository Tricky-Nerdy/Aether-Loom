"""Blender-side smoke tests for pose import and Rigify heel discovery."""

import importlib.util
import importlib
import json
import os
import struct
import sys
import tempfile
from pathlib import Path

import addon_utils
import bpy


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "AetherBlend"
USING_INSTALLED_ADDON = bool(os.environ.get("AETHER_SMOKE_INSTALLED"))
if USING_INSTALLED_ADDON:
    addon_utils.enable("bl_ext.user_default.AetherBlend", default_set=False, persistent=False)
    importlib.import_module("bl_ext.user_default.AetherBlend")
    PACKAGE_PREFIX = "bl_ext.user_default.AetherBlend"
else:
    enabled, loaded = addon_utils.check("bl_ext.user_default.AetherBlend")
    if enabled or loaded:
        addon_utils.disable("bl_ext.user_default.AetherBlend", default_set=False)
    spec = importlib.util.spec_from_file_location(
        PACKAGE_NAME,
        ROOT / "__init__.py",
        submodule_search_locations=[str(ROOT)],
    )
    package = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE_NAME] = package
    spec.loader.exec_module(package)
    PACKAGE_PREFIX = PACKAGE_NAME
    package.register()


def make_leg_metarig():
    bpy.ops.object.armature_add()
    armature = bpy.context.object
    armature.name = "HeelPivotSmoke"
    bpy.ops.object.mode_set(mode="EDIT")
    bones = armature.data.edit_bones
    thigh = bones[0]
    thigh.name = "thigh.L"
    thigh.head, thigh.tail = (0.1, 0.0, 2.0), (0.1, 0.0, 1.0)

    shin = bones.new("shin.L")
    shin.head, shin.tail = thigh.tail, (0.35, 0.0, 0.4)
    shin.parent, shin.use_connect = thigh, True

    foot = bones.new("foot.L")
    foot.head, foot.tail = shin.tail, (0.45, -0.35, 0.15)
    foot.parent, foot.use_connect = shin, True

    toe = bones.new("toe.L")
    toe.head, toe.tail = foot.tail, (0.1, -0.6, 0.15)
    toe.parent, toe.use_connect = foot, True

    heel = bones.new("heel_pivot.L")
    heel.head, heel.tail = (0.35, 0.05, 0.0), (0.45, 0.05, 0.0)
    heel.parent, heel.use_connect = foot, False
    bpy.ops.object.mode_set(mode="POSE")
    armature.pose.bones["thigh.L"].rigify_type = "limbs.leg"
    armature.pose.bones["heel_pivot.L"].rigify_type = "basic.raw_copy"
    armature.data.collections[0].rigify_ui_row = 1
    return armature


def test_heel_pivot():
    addon_utils.enable("rigify", default_set=False, persistent=False)
    armature = make_leg_metarig()
    AetherRigGenerator = importlib.import_module(
        f"{PACKAGE_PREFIX}.core.aether_rig_generator"
    ).AetherRigGenerator

    generator = AetherRigGenerator.__new__(AetherRigGenerator)
    generator._prepare_leg_heel_pivots(armature)
    assert armature.pose.bones["heel_pivot.L"].rigify_type == " ", (
        "AetherBlend must clear the raw-copy type from the heel pivot so Rigify can discover it"
    )
    result = bpy.ops.pose.rigify_generate()
    assert result == {"FINISHED"}, f"Rigify generation did not finish: {result}"
    bpy.data.objects.remove(armature, do_unlink=True)


def test_pose_import():
    import_pose = importlib.import_module(
        f"{PACKAGE_PREFIX}.features.animation.import_pose"
    )

    try:
        bpy.ops.object.armature_add()
        armature = bpy.context.object
        armature.name = "PoseImportSmoke"
        bpy.ops.object.mode_set(mode="EDIT")
        armature.data.edit_bones[0].name = "j_ude_a_l"
        bpy.ops.object.mode_set(mode="POSE")

        pose = {
            "TypeName": "Anamnesis Pose",
            "Bones": {
                "j_ude_a_l": {
                    "Rotation": "0.1, 0.2, 0.3, 0.9",
                    "Position": "1, 2, 3",
                    "Scale": "1, 1, 1",
                }
            },
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pose", encoding="utf-8") as handle:
            json.dump(pose, handle)
            handle.flush()
            result = bpy.ops.aether.pose_import(
                filepath=handle.name,
                target_mode="MATCHING_BONES",
                import_location=True,
            )

        assert result == {"FINISHED"}, f"Pose import did not finish: {result}"
        imported = armature.pose.bones["j_ude_a_l"]
        assert tuple(round(value, 3) for value in imported.location) == (1.0, 2.0, 3.0)
        assert imported.rotation_quaternion.angle > 0.1

        rotation_hex = " ".join(f"{value:02x}" for value in struct.pack("<ffff", 0.7071, 0.0, 0.0, 0.7071))
        scale_hex = " ".join(f"{value:02x}" for value in struct.pack("<fff", 1.0, 1.0, 1.0))
        cmp_pose = {"Type": "CMTool", "ArmLeft": rotation_hex, "ArmLeftSize": scale_hex}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cmp", encoding="utf-8") as handle:
            json.dump(cmp_pose, handle)
            handle.flush()
            result = bpy.ops.aether.pose_import(
                filepath=handle.name,
                target_mode="MATCHING_BONES",
                import_location=False,
            )
        assert result == {"FINISHED"}, f"CMTool pose import did not finish: {result}"
        assert imported.rotation_quaternion.angle > 0.5
        bpy.data.objects.remove(armature, do_unlink=True)
    finally:
        pass


test_heel_pivot()
test_pose_import()
if not USING_INSTALLED_ADDON:
    package.unregister()
print("AETHER_LOOM_BLENDER_SMOKE_OK")
