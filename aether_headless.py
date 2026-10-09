"""Headless command entry point for AetherBlend pose workflows.

Usage:
    blender --background character.blend --python aether_headless.py -- \
        pose-import --pose /path/to/file.pose --reference-gltf /path/to/character.gltf \
        --output /path/to/posed.blend

This script intentionally drives AetherBlend through its registered Blender
operator so headless and interactive imports share the same implementation.
"""

import argparse
import json
import sys
from pathlib import Path

import bpy


def _argv():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def _parser():
    parser = argparse.ArgumentParser(prog="aether-headless")
    sub = parser.add_subparsers(dest="command", required=True)
    pose = sub.add_parser("pose-import", help="Apply an Anamnesis .pose or CMTool .cmp")
    pose.add_argument("--pose", required=True)
    pose.add_argument("--output", required=True)
    pose.add_argument("--reference-gltf", default="")
    pose.add_argument(
        "--target-mode",
        choices=("LINKED_BONES", "MATCHING_BONES", "AETHER_CONTROLS"),
        default="LINKED_BONES",
    )
    pose.add_argument("--position", action="store_true", help="Import bone positions")
    pose.add_argument("--scale", action="store_true", help="Import bone scales")
    pose.add_argument("--no-world-rotation", action="store_true")
    pose.add_argument("--no-preserve-face", action="store_true")
    pose.add_argument("--keyframes", action="store_true")
    return parser


def _ensure_addon():
    if hasattr(bpy.ops, "aether") and hasattr(bpy.ops.aether, "pose_import"):
        return
    try:
        bpy.ops.preferences.addon_enable(module="AetherBlend")
    except Exception as exc:
        raise RuntimeError(
            "AetherBlend is not registered. Install/enable the extension before running headless jobs."
        ) from exc
    if not hasattr(bpy.ops, "aether") or not hasattr(bpy.ops.aether, "pose_import"):
        raise RuntimeError("AetherBlend pose importer is unavailable after enabling the extension")


def _pose_import(args):
    pose = Path(args.pose).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if not pose.is_file():
        raise FileNotFoundError(f"Pose file does not exist: {pose}")
    if pose.suffix.lower() not in {".pose", ".cmp"}:
        raise ValueError("Pose input must be an Anamnesis .pose or CMTool .cmp file")
    output.parent.mkdir(parents=True, exist_ok=True)

    _ensure_addon()
    result = bpy.ops.aether.pose_import(
        "EXEC_DEFAULT",
        filepath=str(pose),
        target_mode=args.target_mode,
        reference_gltf=args.reference_gltf,
        import_rotation=True,
        import_location=args.position,
        import_world_rotation=not args.no_world_rotation,
        import_scale=args.scale,
        preserve_face=not args.no_preserve_face,
        keyframe_pose=args.keyframes,
    )
    if "FINISHED" not in result:
        raise RuntimeError(f"Pose import failed: {sorted(result)}")

    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    return {
        "ok": True,
        "command": "pose-import",
        "pose": str(pose),
        "output": str(output),
        "target_mode": args.target_mode,
    }


def main():
    args = _parser().parse_args(_argv())
    try:
        result = _pose_import(args)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        raise
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
