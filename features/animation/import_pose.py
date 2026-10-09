"""Pose import for Anamnesis and CMTool pose files."""

import csv
import json
import re
import struct
from pathlib import Path

import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from mathutils import Matrix, Quaternion, Vector

from .animation_import import RETARGET_MAP


DEFAULT_POSE_LIBRARY = Path.home() / "Documents" / "FFXIV Poses" / "Flat-Pose-Library-2026-08-15"


def _pose_library_path() -> Path:
    """Return the user-configured pose-library directory, with a safe fallback."""
    try:
        from ...preferences import get_preferences

        configured = getattr(get_preferences(), "default_pose_import_path", "")
        if configured:
            return Path(bpy.path.abspath(configured)).expanduser()
    except Exception:
        pass
    return DEFAULT_POSE_LIBRARY


def _pose_library_records():
    """Read the small TSV index instead of constructing a huge Blender Enum."""
    directory = _pose_library_path()
    index = directory / "_pose-library-index.tsv"
    if not index.is_file():
        return []
    with index.open(encoding="utf-8", errors="replace", newline="") as handle:
        return [
            row for row in csv.DictReader(handle, delimiter="\t")
            if row.get("filename") and (directory / row["filename"]).is_file()
        ]


def _branch_values(records, branch):
    filters = dict(item.split("=", 1) for item in branch.split("|") if "=" in item)
    filtered = [row for row in records if all(row.get(key, "") == value for key, value in filters.items())]
    # Keep the browser deliberately shallow.  Author and pack names are useful
    # provenance in the TSV, but make poor navigation categories for a pose
    # library (and were the cause of dozens of one- or two-item branches).
    for field in ("people", "action"):
        if field not in filters:
            return field, filtered, filters
    return None, filtered, filters


def _find_target_armature(context):
    """Find the most likely AetherBlend armature without requiring selection."""
    candidates = [obj for obj in context.view_layer.objects if obj.type == "ARMATURE" and obj.visible_get()]
    if not candidates:
        return None

    active = context.active_object

    def score(armature):
        value = 0
        if armature == active:
            value += 1000
        if armature.select_get():
            value += 100
        if any(bone.name.startswith("LINK-") for bone in armature.data.bones):
            value += 500
        if getattr(armature, "aether_rig", None) is not None:
            value += 250
        if "n_root" in armature.data.bones:
            value += 50
        return value

    return max(candidates, key=lambda armature: (score(armature), armature.name.casefold()))


POSE_RETARGET_MAP = {
    **RETARGET_MAP,
    "j_te_l": {"target": "hand_fk.L", "invert_rot": (False, False, True, False), "invert_loc": (True, False, False)},
    "j_te_r": {"target": "hand_fk.R", "invert_rot": (False, False, True, False), "invert_loc": (True, False, False)},
    "j_kao": {"target": "head", "invert_rot": (True, False, False, False), "invert_loc": (False, False, True)},
    "j_asi_e_l": {"target": "toe.L", "invert_rot": (True, False, False, False), "invert_loc": (False, False, True)},
    "j_asi_e_r": {"target": "toe.R", "invert_rot": (True, False, False, False), "invert_loc": (False, False, True)},
    "j_mune_l": {"target": "Chest.L", "invert_rot": (True, False, False, False), "invert_loc": (False, False, True)},
    "j_mune_r": {"target": "Chest.R", "invert_rot": (True, False, False, False), "invert_loc": (False, False, True)},
    "n_hhiji_l": {"target": "elbow.L", "invert_rot": (False, False, True, False), "invert_loc": (False, False, False)},
    "n_hhiji_r": {"target": "elbow.R", "invert_rot": (False, False, True, False), "invert_loc": (False, False, False)},
    "n_kataarmor_l": {"target": "pauldron.L", "invert_rot": (False, False, True, False), "invert_loc": (False, False, False)},
    "n_kataarmor_r": {"target": "pauldron.R", "invert_rot": (False, False, True, False), "invert_loc": (False, False, False)},
}


# Legacy CMTool names used by .cmp files. Based on Anamnesis'
# LegacyBoneNameConverter mapping.
LEGACY_TO_MODERN_BONES = {
    "Root": "n_root",
    "Abdomen": "n_hara",
    "Throw": "n_throw",
    "Waist": "j_kosi",
    "SpineA": "j_sebo_a",
    "LegLeft": "j_asi_a_l",
    "LegRight": "j_asi_a_r",
    "HolsterLeft": "j_buki2_kosi_l",
    "HolsterRight": "j_buki2_kosi_r",
    "SheatheLeft": "j_buki_kosi_l",
    "SheatheRight": "j_buki_kosi_r",
    "SpineB": "j_sebo_b",
    "ClothBackALeft": "j_sk_b_a_l",
    "ClothBackARight": "j_sk_b_a_r",
    "ClothFrontALeft": "j_sk_f_a_l",
    "ClothFrontARight": "j_sk_f_a_r",
    "ClothSideALeft": "j_sk_s_a_l",
    "ClothSideARight": "j_sk_s_a_r",
    "KneeLeft": "j_asi_b_l",
    "KneeRight": "j_asi_b_r",
    "BreastLeft": "j_mune_l",
    "BreastRight": "j_mune_r",
    "SpineC": "j_sebo_c",
    "ClothBackBLeft": "j_sk_b_b_l",
    "ClothBackBRight": "j_sk_b_b_r",
    "ClothFrontBLeft": "j_sk_f_b_l",
    "ClothFrontBRight": "j_sk_f_b_r",
    "ClothSideBLeft": "j_sk_s_b_l",
    "ClothSideBRight": "j_sk_s_b_r",
    "CalfLeft": "j_asi_c_l",
    "CalfRight": "j_asi_c_r",
    "ScabbardLeft": "j_buki_sebo_l",
    "ScabbardRight": "j_buki_sebo_r",
    "Neck": "j_kubi",
    "ClavicleLeft": "j_sako_l",
    "ClavicleRight": "j_sako_r",
    "ClothBackCLeft": "j_sk_b_c_l",
    "ClothBackCRight": "j_sk_b_c_r",
    "ClothFrontCLeft": "j_sk_f_c_l",
    "ClothFrontCRight": "j_sk_f_c_r",
    "ClothSideCLeft": "j_sk_s_c_l",
    "ClothSideCRight": "j_sk_s_c_r",
    "PoleynLeft": "n_hizasoubi_l",
    "PoleynRight": "n_hizasoubi_r",
    "FootLeft": "j_asi_d_l",
    "FootRight": "j_asi_d_r",
    "Head": "j_kao",
    "ArmLeft": "j_ude_a_l",
    "ArmRight": "j_ude_a_r",
    "PauldronLeft": "n_kataarmor_l",
    "PauldronRight": "n_kataarmor_r",
    "ToesLeft": "j_asi_e_l",
    "ToesRight": "j_asi_e_r",
    "HairA": "j_kami_a",
    "HairFrontLeft": "j_kami_f_l",
    "HairFrontRight": "j_kami_f_r",
    "EarLeft": "j_mimi_l",
    "EarRight": "j_mimi_r",
    "ForearmLeft": "j_ude_b_l",
    "ForearmRight": "j_ude_b_r",
    "ShoulderLeft": "n_hkata_l",
    "ShoulderRight": "n_hkata_r",
    "HairB": "j_kami_b",
    "HandLeft": "j_te_l",
    "HandRight": "j_te_r",
    "ShieldLeft": "n_buki_tate_l",
    "ShieldRight": "n_buki_tate_r",
    "EarringALeft": "n_ear_a_l",
    "EarringARight": "n_ear_a_r",
    "ElbowLeft": "n_hhiji_l",
    "ElbowRight": "n_hhiji_r",
    "CouterLeft": "n_hijisoubi_l",
    "CouterRight": "n_hijisoubi_r",
    "WristLeft": "n_hte_l",
    "WristRight": "n_hte_r",
    "IndexALeft": "j_hito_a_l",
    "IndexARight": "j_hito_a_r",
    "PinkyALeft": "j_ko_a_l",
    "PinkyARight": "j_ko_a_r",
    "RingALeft": "j_kusu_a_l",
    "RingARight": "j_kusu_a_r",
    "MiddleALeft": "j_naka_a_l",
    "MiddleARight": "j_naka_a_r",
    "ThumbALeft": "j_oya_a_l",
    "ThumbARight": "j_oya_a_r",
    "WeaponLeft": "n_buki_l",
    "WeaponRight": "n_buki_r",
    "EarringBLeft": "n_ear_b_l",
    "EarringBRight": "n_ear_b_r",
    "IndexBLeft": "j_hito_b_l",
    "IndexBRight": "j_hito_b_r",
    "PinkyBLeft": "j_ko_b_l",
    "PinkyBRight": "j_ko_b_r",
    "RingBLeft": "j_kusu_b_l",
    "RingBRight": "j_kusu_b_r",
    "MiddleBLeft": "j_naka_b_l",
    "MiddleBRight": "j_naka_b_r",
    "ThumbBLeft": "j_oya_b_l",
    "ThumbBRight": "j_oya_b_r",
    "TailA": "n_sippo_a",
    "TailB": "n_sippo_b",
    "TailC": "n_sippo_c",
    "TailD": "n_sippo_d",
    "TailE": "n_sippo_e",
    "RootHead": "j_kao",
    "Jaw": "j_ago",
    "EyelidLowerLeft": "j_f_dmab_l",
    "EyelidLowerRight": "j_f_dmab_r",
    "EyeLeft": "j_f_eye_l",
    "EyeRight": "j_f_eye_r",
    "Nose": "j_f_hana",
    "CheekLeft": "j_f_hoho_l",
    "CheekRight": "j_f_hoho_r",
    "LipsLeft": "j_f_lip_l",
    "LipsRight": "j_f_lip_r",
    "EyebrowLeft": "j_f_mayu_l",
    "EyebrowRight": "j_f_mayu_r",
    "Bridge": "j_f_memoto",
    "BrowLeft": "j_f_miken_l",
    "BrowRight": "j_f_miken_r",
    "LipUpperA": "j_f_ulip_a",
    "EyelidUpperLeft": "j_f_umab_l",
    "EyelidUpperRight": "j_f_umab_r",
    "LipLowerA": "j_f_dlip_a",
    "LipUpperB": "j_f_ulip_b",
    "LipLowerB": "j_f_dlip_b",
    "VieraEar01ALeft": "j_zera_a_l",
    "VieraEar01ARight": "j_zera_a_r",
    "VieraEar01BLeft": "j_zera_b_l",
    "VieraEar01BRight": "j_zera_b_r",
    "VieraEar02ALeft": "j_zerb_a_l",
    "VieraEar02ARight": "j_zerb_a_r",
    "VieraEar02BLeft": "j_zerb_b_l",
    "VieraEar02BRight": "j_zerb_b_r",
    "VieraEar03ALeft": "j_zerc_a_l",
    "VieraEar03ARight": "j_zerc_a_r",
    "VieraEar03BLeft": "j_zerc_b_l",
    "VieraEar03BRight": "j_zerc_b_r",
    "VieraEar04ALeft": "j_zerd_a_l",
    "VieraEar04ARight": "j_zerd_a_r",
    "VieraEar04BLeft": "j_zerd_b_l",
    "VieraEar04BRight": "j_zerd_b_r",
    "VieraLipLowerA": "j_f_dlip_a",
    "VieraLipUpperB": "j_f_ulip_b",
    "VieraLipLowerB": "j_f_dlip_b",
    "HrothWhiskersLeft": "j_f_hige_l",
    "HrothWhiskersRight": "j_f_hige_r",
    "HrothEyebrowLeft": "j_f_mayu_l",
    "HrothEyebrowRight": "j_f_mayu_r",
    "HrothBridge": "j_f_memoto",
    "HrothBrowLeft": "j_f_miken_l",
    "HrothBrowRight": "j_f_miken_r",
    "HrothJawUpper": "j_f_uago",
    "HrothLipUpper": "j_f_ulip",
    "HrothEyelidUpperLeft": "j_f_umab_l",
    "HrothEyelidUpperRight": "j_f_umab_r",
    "HrothLipsLeft": "n_f_lip_l",
    "HrothLipsRight": "n_f_lip_r",
    "HrothLipUpperLeft": "n_f_ulip_l",
    "HrothLipUpperRight": "n_f_ulip_r",
    "HrothLipLower": "j_f_dlip",
}


def _parse_float_tuple(value, expected_size):
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        numbers = [float(part) for part in value]
    else:
        numbers = [float(part.strip()) for part in str(value).split(",")]
    if len(numbers) != expected_size:
        raise ValueError(f"Expected {expected_size} values, got {len(numbers)}")
    return numbers


def _parse_vector(value):
    values = _parse_float_tuple(value, 3)
    return Vector(values) if values is not None else None


def _parse_quaternion_xyzw(value):
    values = _parse_float_tuple(value, 4)
    if values is None:
        return None
    x, y, z, w = values
    return Quaternion((w, x, y, z))


def _parse_cmp_quaternion(hex_string):
    if not hex_string or hex_string == "null":
        return None
    data = bytes(int(part, 16) for part in hex_string.strip().split())
    if len(data) < 16:
        raise ValueError("CMTool quaternion contains fewer than 16 bytes")
    x, y, z, w = struct.unpack("<ffff", data[:16])
    return Quaternion((w, x, y, z))


def _parse_cmp_scale(hex_string):
    if not hex_string or hex_string == "null":
        return None
    data = bytes(int(part, 16) for part in hex_string.strip().split())
    if len(data) < 12:
        raise ValueError("CMTool scale contains fewer than 12 bytes")
    return Vector(struct.unpack("<fff", data[:12]))


def _clean_bone_name(name):
    return re.sub(r"\.\d+$", "", name)


def _load_pose_document(filepath):
    with open(filepath, "r", encoding="utf-8-sig") as file:
        data = json.load(file)

    bones = {}
    if data.get("Bones") is not None:
        for bone_name, bone_data in data["Bones"].items():
            if bone_data is None:
                continue
            bones[_clean_bone_name(bone_name)] = {
                "rotation": _parse_quaternion_xyzw(bone_data.get("Rotation")),
                "location": _parse_vector(bone_data.get("Position")),
                "scale": _parse_vector(bone_data.get("Scale")),
                "depth": int(bone_data.get("BoneDepth", 9999)),
            }
        return {
            "format": "ANAMNESIS",
            "model_space": True,
            "bones": bones,
            "actor_location": _parse_vector(data.get("Position")),
            "actor_rotation": _parse_quaternion_xyzw(data.get("Rotation")),
            "actor_scale": _parse_vector(data.get("Scale")),
        }

    for legacy_name, rotation_value in data.items():
        if legacy_name in {"Race", "Type"} or legacy_name.endswith("Size"):
            continue

        modern_name = LEGACY_TO_MODERN_BONES.get(legacy_name)
        if not modern_name:
            continue

        scale_value = data.get(f"{legacy_name}Size")
        rotation = _parse_cmp_quaternion(rotation_value)
        scale = _parse_cmp_scale(scale_value)
        if rotation or scale:
            bones[modern_name] = {
                "rotation": rotation,
                "location": None,
                "scale": scale,
                "depth": 9999,
            }
    return {
        "format": "CMTOOL",
        "model_space": False,
        "bones": bones,
        "actor_location": None,
        "actor_rotation": None,
        "actor_scale": None,
    }


def _load_pose_file(filepath):
    """Compatibility helper retained for callers that only need bone data."""
    return _load_pose_document(filepath)["bones"]


def _gltf_to_blender_location(value, unit_scale=1.0):
    return unit_scale * Vector((value.x, -value.z, value.y))


def _gltf_to_blender_rotation(value):
    return Quaternion((value.w, value.x, -value.z, value.y)).normalized()


def _gltf_to_blender_scale(value):
    return Vector((value.x, value.z, value.y))


def _converted_model_matrix(location, rotation, scale=None, unit_scale=1.0):
    return Matrix.LocRotScale(
        _gltf_to_blender_location(location, unit_scale),
        _gltf_to_blender_rotation(rotation),
        _gltf_to_blender_scale(scale or Vector((1.0, 1.0, 1.0))),
    )


def _gltf_reference_matrices(filepath, unit_scale=1.0):
    """Return named glTF node matrices in Blender armature coordinates."""
    with open(filepath, "r", encoding="utf-8-sig") as file:
        data = json.load(file)

    nodes = data.get("nodes") or []
    parent_by_index = {}
    for parent_index, node in enumerate(nodes):
        for child_index in node.get("children", []):
            parent_by_index[child_index] = parent_index

    local_matrices = {}
    for index, node in enumerate(nodes):
        values = node.get("matrix")
        if values is not None:
            if len(values) != 16:
                raise ValueError(f"glTF node {index} has an invalid matrix")
            local_matrices[index] = Matrix((
                (values[0], -values[8], values[4], values[12] * unit_scale),
                (-values[2], values[10], -values[6], -values[14] * unit_scale),
                (values[1], -values[9], values[5], values[13] * unit_scale),
                (values[3] / unit_scale, -values[11] / unit_scale, values[7] / unit_scale, values[15]),
            ))
            continue

        location = Vector(node.get("translation", (0.0, 0.0, 0.0)))
        rotation_values = node.get("rotation", (0.0, 0.0, 0.0, 1.0))
        rotation = Quaternion((rotation_values[3], rotation_values[0], rotation_values[1], rotation_values[2]))
        scale = Vector(node.get("scale", (1.0, 1.0, 1.0)))
        local_matrices[index] = _converted_model_matrix(location, rotation, scale, unit_scale)

    world_cache = {}

    def world_matrix(index):
        cached = world_cache.get(index)
        if cached is not None:
            return cached
        local_matrix = local_matrices[index]
        parent_index = parent_by_index.get(index)
        result = world_matrix(parent_index) @ local_matrix if parent_index is not None else local_matrix
        world_cache[index] = result
        return result

    references = {}
    for index, node in enumerate(nodes):
        name = node.get("name")
        if name:
            references[name] = world_matrix(index)
    return references


def _find_reference_gltf(armature, explicit_path=""):
    candidates = []
    if explicit_path:
        candidates.append(Path(bpy.path.abspath(explicit_path)))

    cached_path = armature.get("aether_pose_reference_gltf")
    if cached_path:
        candidates.append(Path(bpy.path.abspath(cached_path)))

    if bpy.data.filepath:
        blend_directory = Path(bpy.data.filepath).resolve().parent
        candidates.extend(sorted(blend_directory.glob("*.gltf")))

    valid_candidates = []
    seen = set()
    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve()
        except (OSError, RuntimeError):
            continue
        if resolved in seen or not resolved.is_file():
            continue
        seen.add(resolved)
        valid_candidates.append(resolved)

    if not valid_candidates:
        return None

    armature_name = armature.name.lower().removeprefix("character-")
    matching = [item for item in valid_candidates if item.stem.lower() in armature_name or armature_name in item.stem.lower()]
    return matching[0] if matching else valid_candidates[0]


def _compose_selected_channels(current_matrix, target_matrix, import_rotation, import_location, import_scale):
    current_location, current_rotation, current_scale = current_matrix.decompose()
    target_location, target_rotation, target_scale = target_matrix.decompose()
    return Matrix.LocRotScale(
        target_location if import_location else current_location,
        target_rotation if import_rotation else current_rotation,
        target_scale if import_scale else current_scale,
    )


_BODY_POSE_BONES = {
    "n_hara",
    "j_kosi",
    "j_sebo_a",
    "j_sebo_b",
    "j_sebo_c",
    "j_kubi",
    "j_kao",
    "j_sako_l",
    "j_sako_r",
    "j_ude_a_l",
    "j_ude_a_r",
    "j_ude_b_l",
    "j_ude_b_r",
    "j_te_l",
    "j_te_r",
    "n_hkata_l",
    "n_hkata_r",
    "n_hhiji_l",
    "n_hhiji_r",
    "n_hte_l",
    "n_hte_r",
    "j_mune_l",
    "j_mune_r",
    "j_asi_a_l",
    "j_asi_a_r",
    "j_asi_b_l",
    "j_asi_b_r",
    "j_asi_c_l",
    "j_asi_c_r",
    "j_asi_d_l",
    "j_asi_d_r",
    "j_asi_e_l",
    "j_asi_e_r",
    "j_mimi_l",
    "j_mimi_r",
    "n_sippo_a",
    "n_sippo_b",
    "n_sippo_c",
    "n_sippo_d",
    "n_sippo_e",
}


def _is_body_pose_bone(name):
    if name in _BODY_POSE_BONES:
        return True
    return re.fullmatch(r"j_(?:oya|hito|naka|kusu|ko)_[ab]_[lr]", name) is not None


def _nearest_targeted_ancestor(armature, source_name, target_matrices):
    source_bone = armature.data.bones.get(source_name)
    parent = source_bone.parent if source_bone else None
    while parent:
        if parent.name in target_matrices:
            return parent.name
        parent = parent.parent
    return None


def _has_source_ancestor(armature, source_name, ancestor_names, include_self=False):
    source_bone = armature.data.bones.get(source_name)
    current = source_bone if include_self else (source_bone.parent if source_bone else None)
    while current:
        if current.name in ancestor_names:
            return True
        current = current.parent
    return False


def _apply_control_from_source_target(
    armature,
    source_name,
    control_name,
    source_target,
    import_rotation,
    import_location,
    keyframe,
):
    source_rest = armature.data.bones.get(f"LINK-{source_name}")
    control_rest = armature.data.bones.get(control_name)
    control = armature.pose.bones.get(control_name)
    if not source_rest or not control_rest or not control:
        return False

    control_target = source_target @ source_rest.matrix_local.inverted_safe() @ control_rest.matrix_local
    control.rotation_mode = "QUATERNION"
    control.matrix = _compose_selected_channels(
        control.matrix,
        control_target,
        import_rotation,
        import_location,
        False,
    )
    if keyframe:
        control.keyframe_insert(data_path="location")
        control.keyframe_insert(data_path="rotation_quaternion")
    bpy.context.view_layer.update()
    return True


def _source_bone_depth(bone):
    depth = 0
    parent = bone.parent
    while parent:
        depth += 1
        parent = parent.parent
    return depth


def _target_bone_for_source(armature, source_name):
    """Prefer a LINK bone, falling back to the original imported bone."""
    return armature.data.bones.get(f"LINK-{source_name}") or armature.data.bones.get(source_name)


def _current_target_matrix_for_source(armature, source_name):
    pose_bone = armature.pose.bones.get(f"LINK-{source_name}") or armature.pose.bones.get(source_name)
    return pose_bone.matrix.copy() if pose_bone else None


def _rebuild_target_hierarchy(
    armature,
    reference_matrices,
    direct_targets,
    import_rotation,
    import_source_positions,
    import_scale,
):
    """Retarget model rotations while retaining this rig's local bone lengths.

    Anamnesis stores character-space transforms.  Its normal cross-race import
    deliberately restores each target bone's parent-relative position after
    loading rotations.  Reconstructing the hierarchy here provides the same
    protection for Blender rigs while still yielding model-space LINK targets.
    """
    source_bones = [
        bone
        for name in reference_matrices
        if (bone := armature.data.bones.get(name)) is not None
    ]
    source_bones.sort(key=lambda bone: (_source_bone_depth(bone), bone.name))

    current_matrices = {
        bone.name: matrix
        for bone in source_bones
        if (matrix := _current_target_matrix_for_source(armature, bone.name)) is not None
    }
    rebuilt = {}
    has_posed_ancestor = {}

    for bone in source_bones:
        source_name = bone.name
        current_matrix = current_matrices.get(source_name)
        if current_matrix is None:
            continue

        parent_name = bone.parent.name if bone.parent else None
        parent_current = current_matrices.get(parent_name) if parent_name else None
        parent_target = rebuilt.get(parent_name) if parent_name else None
        if parent_current is not None and parent_target is not None:
            current_local = parent_current.inverted_safe() @ current_matrix
            carried_matrix = parent_target @ current_local
        else:
            carried_matrix = current_matrix.copy()

        direct_target = direct_targets.get(source_name)
        if direct_target is None:
            rebuilt[source_name] = carried_matrix
            has_posed_ancestor[source_name] = bool(
                parent_name and has_posed_ancestor.get(parent_name, False)
            )
            continue

        carried_location, carried_rotation, carried_scale = carried_matrix.decompose()
        source_location, source_rotation, source_scale = direct_target.decompose()
        rebuilt[source_name] = Matrix.LocRotScale(
            source_location if import_source_positions else carried_location,
            source_rotation if import_rotation else carried_rotation,
            source_scale if import_scale else carried_scale,
        )
        has_posed_ancestor[source_name] = True

    return rebuilt, has_posed_ancestor


def _apply_actor_world_rotation(armature, actor_rotation, keyframe):
    if actor_rotation is None:
        return False

    location, _rotation, scale = armature.matrix_world.decompose()
    armature.rotation_mode = "QUATERNION"
    armature.matrix_world = Matrix.LocRotScale(
        location,
        _gltf_to_blender_rotation(actor_rotation),
        scale,
    )
    if keyframe:
        armature.keyframe_insert(data_path="rotation_quaternion")
    bpy.context.view_layer.update()
    return True


def _apply_procedural_knee_support(armature, posed_source_names, keyframe):
    """Aim unlinked weighted knee helpers down the posed lower leg.

    The FFXIV leg template is designed to drive j_asi_b through a generated
    knee mechanism. Older generated rigs can be missing that mechanism while
    retaining weights on j_asi_b. Copying the pose-file transform directly is
    unstable because this is a corrective joint, not an independent limb.
    Tracking the posed calf reproduces the intended procedural behavior while
    preserving the helper's inherited location, scale, and roll.
    """
    applied = 0
    bpy.context.view_layer.update()
    for side in ("l", "r"):
        helper_name = f"j_asi_b_{side}"
        calf_name = f"j_asi_c_{side}"
        if helper_name not in posed_source_names or calf_name not in posed_source_names:
            continue
        if armature.pose.bones.get(f"LINK-{helper_name}"):
            continue

        helper = armature.pose.bones.get(helper_name)
        calf = armature.pose.bones.get(f"LINK-{calf_name}")
        if helper is None or calf is None or helper.constraints:
            continue

        current_location, current_rotation, current_scale = helper.matrix.decompose()
        target_direction = calf.matrix.translation - current_location
        if target_direction.length_squared < 1e-12:
            continue

        current_axis = current_rotation @ Vector((0.0, 1.0, 0.0))
        if current_axis.length_squared < 1e-12:
            continue
        correction = current_axis.normalized().rotation_difference(target_direction.normalized())

        helper.rotation_mode = "QUATERNION"
        helper.matrix = Matrix.LocRotScale(
            current_location,
            (correction @ current_rotation).normalized(),
            current_scale,
        )
        if keyframe:
            helper.keyframe_insert(data_path="location")
            helper.keyframe_insert(data_path="rotation_quaternion")
        applied += 1

    bpy.context.view_layer.update()
    return applied


def _apply_model_space_link_pose(
    armature,
    pose_data,
    reference_matrices,
    import_rotation,
    import_source_positions,
    import_scale,
    keyframe,
    preserve_face,
    unit_scale=1.0,
):
    direct_targets = {}
    skipped = 0
    ordered_bones = sorted(pose_data.items(), key=lambda item: (item[1].get("depth", 9999), item[0]))

    for source_bone_name, transform in ordered_bones:
        if preserve_face and not _is_body_pose_bone(source_bone_name):
            continue
        target_bone = _target_bone_for_source(armature, source_bone_name)
        reference_matrix = reference_matrices.get(source_bone_name)
        location = transform.get("location")
        rotation = transform.get("rotation")
        if not target_bone or reference_matrix is None or location is None or rotation is None:
            skipped += 1
            continue

        source_scale = transform.get("scale") if import_scale else Vector((1.0, 1.0, 1.0))
        pose_matrix = _converted_model_matrix(location, rotation, source_scale, unit_scale)
        rest_offset = reference_matrix.inverted_safe() @ target_bone.matrix_local
        target_matrix = pose_matrix @ rest_offset
        direct_targets[source_bone_name] = target_matrix

    rebuilt_targets, has_posed_ancestor = _rebuild_target_hierarchy(
        armature,
        reference_matrices,
        direct_targets,
        import_rotation,
        import_source_positions,
        import_scale,
    )

    control_count = 0
    if preserve_face:
        # Moving the generated neck/head controls carries the entire facial rig,
        # eyes, hair, and head attachments without importing incompatible face bones.
        for source_name, control_name in (("j_kubi", "neck"), ("j_kao", "head")):
            source_target = rebuilt_targets.get(source_name)
            if source_target is not None and _apply_control_from_source_target(
                armature,
                source_name,
                control_name,
                source_target,
                import_rotation,
                True,
                keyframe,
            ):
                control_count += 1

    target_matrices = {}
    for pose_bone in armature.pose.bones:
        if not pose_bone.name.startswith("LINK-"):
            continue
        source_bone_name = pose_bone.name[5:]
        if not has_posed_ancestor.get(source_bone_name, False):
            continue
        if preserve_face and _has_source_ancestor(
                armature,
                source_bone_name,
                {"j_kubi", "j_kao"},
                include_self=True,
        ):
            continue
        target_matrix = rebuilt_targets.get(source_bone_name)
        if target_matrix is not None:
            target_matrices[source_bone_name] = target_matrix

    applied = control_count
    ordered_targets = sorted(
        target_matrices.items(),
        key=lambda item: (
            _source_bone_depth(armature.data.bones[item[0]])
            if armature.data.bones.get(item[0])
            else 9999,
            item[0],
        ),
    )
    for source_bone_name, target_matrix in ordered_targets:
        pose_bone = armature.pose.bones.get(f"LINK-{source_bone_name}")
        if not pose_bone:
            continue
        pose_bone.rotation_mode = "QUATERNION"
        pose_bone.matrix = _compose_selected_channels(
            pose_bone.matrix,
            target_matrix,
            import_rotation,
            True,
            import_scale,
        )
        if keyframe:
            pose_bone.keyframe_insert(data_path="location")
            pose_bone.keyframe_insert(data_path="rotation_quaternion")
            if import_scale:
                pose_bone.keyframe_insert(data_path="scale")
        applied += 1

    bpy.context.view_layer.update()
    applied += _apply_procedural_knee_support(armature, direct_targets, keyframe)
    return applied, skipped


def _resolve_pose_bone(armature, preferred_name):
    if not preferred_name:
        return None
    pose_bones = armature.pose.bones
    candidates = [
        preferred_name,
        preferred_name[:1].upper() + preferred_name[1:],
        preferred_name.replace("Spine_fk", "FK-Spine"),
        preferred_name.replace("upper_arm_fk", "FK-upper_arm"),
        preferred_name.replace("forearm_fk", "FK-forearm"),
        preferred_name.replace("thigh_fk", "FK-upper_leg"),
        preferred_name.replace("shin_fk", "FK-lower_leg"),
        preferred_name.replace("foot_fk", "FK-foot"),
        preferred_name.replace("thumb.", "thumb.01."),
        preferred_name.replace("index.", "f_index.01."),
        preferred_name.replace("middle.", "f_middle.01."),
        preferred_name.replace("ring.", "f_ring.01."),
        preferred_name.replace("pinky.", "f_pinky.01."),
    ]
    for candidate in candidates:
        pose_bone = pose_bones.get(candidate)
        if pose_bone:
            return pose_bone
    return None


def _retarget_quaternion(quaternion, invert_rot):
    w = -quaternion.w if invert_rot[3] else quaternion.w
    x = -quaternion.z if invert_rot[0] else quaternion.z
    y = -quaternion.y if invert_rot[1] else quaternion.y
    z = -quaternion.x if invert_rot[2] else quaternion.x
    return Quaternion((w, x, y, z))


def _retarget_location(location, invert_loc):
    x = -location.z if invert_loc[0] else location.z
    y = -location.y if invert_loc[1] else location.y
    z = -location.x if invert_loc[2] else location.x
    return Vector((x, y, z))


def _apply_transform(pose_bone, transform, import_rotation, import_location, import_scale, keyframe):
    pose_bone.rotation_mode = "QUATERNION"
    if import_rotation and transform.get("rotation") is not None:
        pose_bone.rotation_quaternion = transform["rotation"]
        if keyframe:
            pose_bone.keyframe_insert(data_path="rotation_quaternion")
    if import_location and transform.get("location") is not None:
        pose_bone.location = transform["location"]
        if keyframe:
            pose_bone.keyframe_insert(data_path="location")
    if import_scale and transform.get("scale") is not None:
        pose_bone.scale = transform["scale"]
        if keyframe:
            pose_bone.keyframe_insert(data_path="scale")


class AETHER_OT_OpenPoseMenu(Operator):
    """Open a fast, progressively narrowed pose-library context menu."""

    bl_idname = "aether.open_pose_menu"
    bl_label = "Choose Library Pose"

    branch: StringProperty(default="", options={"HIDDEN"})  # type: ignore

    def execute(self, context):
        records = _pose_library_records()
        field, filtered, filters = _branch_values(records, self.branch)

        def draw(menu, _context):
            layout = menu.layout
            if not filtered:
                layout.label(text="No matching pose files", icon="ERROR")
                return
            if field is None:
                for row in sorted(filtered, key=lambda item: item["filename"].casefold()):
                    # Invoke the actual undoable pose operator directly.  A
                    # wrapper operator here would make the pose import nested
                    # and can prevent Blender from recording one clean undo.
                    apply = layout.operator("aether.pose_import", text=row["filename"], icon="POSE_HLT")
                    apply.filepath = str(_pose_library_path() / row["filename"])
                    apply.library_people = filters.get("people", "")
                    apply.library_action = filters.get("action", "")
                return
            values = sorted({row.get(field, "Unknown") or "Unknown" for row in filtered}, key=str.casefold)
            for value in values:
                count = sum(1 for row in filtered if (row.get(field, "Unknown") or "Unknown") == value)
                next_filters = {**filters, field: value}
                nested = layout.operator("aether.open_pose_menu", text=f"{value} ({count})", icon="RIGHTARROW_THIN")
                nested.branch = "|".join(f"{key}={item}" for key, item in next_filters.items())

        title = "Pose Library" if not self.branch else "Pose Library: " + self.branch.replace("|", " / ").replace("=", " ")
        context.window_manager.popup_menu(draw, title=title, icon="POSE_HLT")
        return {"FINISHED"}


class AETHER_OT_OpenRootPoseMenu(Operator):
    """Always open the pose browser at its top-level People categories."""

    bl_idname = "aether.open_root_pose_menu"
    bl_label = "Browse Library Poses"

    def execute(self, _context):
        # Do not rely on Blender's remembered operator properties here.  The
        # branch menu intentionally carries its branch forward, whereas this
        # panel action is always the entry point to the browser.
        return bpy.ops.aether.open_pose_menu("EXEC_DEFAULT", branch="")


class AETHER_OT_ApplyLibraryPose(Operator):
    """Apply one chosen flat-library pose as a normal undoable import."""

    bl_idname = "aether.apply_library_pose"
    bl_label = "Apply Library Pose"

    filepath: StringProperty(subtype="FILE_PATH", options={"HIDDEN"})  # type: ignore
    people: StringProperty(options={"HIDDEN"})  # type: ignore
    action: StringProperty(options={"HIDDEN"})  # type: ignore

    def execute(self, context):
        if not Path(self.filepath).is_file():
            self.report({"ERROR"}, "The selected pose file no longer exists")
            return {"CANCELLED"}
        context.scene.aether_pose_current_file = Path(self.filepath).name
        context.scene.aether_pose_branch_people = self.people
        context.scene.aether_pose_branch_action = self.action
        # Do not reopen a popup after applying a pose.  It steals focus at the
        # cursor and interferes with continuing to pose the character; a new
        # click on the library button always starts at the root branch.
        return bpy.ops.aether.pose_import(
            "EXEC_DEFAULT",
            filepath=self.filepath,
            library_people=self.people,
            library_action=self.action,
        )


class AETHER_OT_CyclePose(Operator):
    """Apply the previous or next pose from the currently selected menu branch."""

    bl_idname = "aether.cycle_pose"
    bl_label = "Cycle Library Pose"
    bl_options = {"REGISTER"}

    direction: IntProperty(default=1, options={"HIDDEN"})  # type: ignore

    def execute(self, context):
        people = context.scene.aether_pose_branch_people
        action = context.scene.aether_pose_branch_action
        if not people or not action:
            self.report({"INFO"}, "Choose a pose first; arrows stay within that People / Action branch")
            return {"CANCELLED"}

        rows = [
            row for row in _pose_library_records()
            if row.get("people") == people and row.get("action") == action
        ]
        rows.sort(key=lambda row: row["filename"].casefold())
        if not rows:
            self.report({"ERROR"}, "The selected pose branch is empty")
            return {"CANCELLED"}

        names = [row["filename"] for row in rows]
        current = context.scene.aether_pose_current_file
        try:
            index = names.index(current)
        except ValueError:
            index = 0 if self.direction > 0 else len(names) - 1
        else:
            index = (index + self.direction) % len(names)

        filename = names[index]
        return bpy.ops.aether.pose_import(
            "EXEC_DEFAULT",
            filepath=str(_pose_library_path() / filename),
            library_people=people,
            library_action=action,
        )


class AETHER_OT_PoseImport(Operator, ImportHelper):
    """Imports Anamnesis .pose or legacy CMTool .cmp files."""

    bl_idname = "aether.pose_import"
    bl_label = "Import Pose File"
    # Let Blender capture the state before the pose writes occur.  An explicit
    # post-import undo_push is too late and makes Ctrl+Z appear ineffective.
    bl_options = {"REGISTER", "UNDO"}

    filepath: StringProperty(
        subtype="FILE_PATH",
        default=str(DEFAULT_POSE_LIBRARY) + "/",
    )  # type: ignore
    filename_ext = ""
    filter_glob: StringProperty(default="*.pose;*.cmp", options={"HIDDEN"})  # type: ignore
    library_people: StringProperty(options={"HIDDEN"})  # type: ignore
    library_action: StringProperty(options={"HIDDEN"})  # type: ignore

    def invoke(self, context, event):
        self.filepath = str(_pose_library_path()) + "/"
        return ImportHelper.invoke(self, context, event)

    target_mode: EnumProperty(
        name="Target",
        description="Choose how the pose is applied",
        items=(
            (
                "LINKED_BONES",
                "AetherBlend Linked Pose (Recommended)",
                "Convert Anamnesis model-space transforms onto LINK-* bones using the source glTF rest pose",
            ),
            ("MATCHING_BONES", "Matching Bone Names (Advanced)", "Apply values directly to matching pose-bone channels"),
            (
                "AETHER_CONTROLS",
                "Legacy Control Map (Unsafe)",
                "Old direct axis mapping; retained for development and may distort generated rigs",
            ),
        ),
        default="LINKED_BONES",
    )  # type: ignore

    reference_gltf: StringProperty(
        name="Reference glTF",
        description="Original Meddle .gltf used to create this character; auto-detected beside the saved .blend when blank",
        subtype="FILE_PATH",
        default="",
    )  # type: ignore

    import_rotation: BoolProperty(
        name="Rotation",
        description="Import bone rotations",
        default=True,
    )  # type: ignore

    import_location: BoolProperty(
        name="Position",
        description="Import source bone positions (full-transform mode); leave disabled for safe cross-race retargeting that preserves this rig's limb lengths",
        default=False,
    )  # type: ignore

    import_world_rotation: BoolProperty(
        name="World Rotation / Floor Orientation",
        description="Apply the pose file's actor rotation, including floor, wall, and tilted pose orientation",
        default=True,
    )  # type: ignore

    import_scale: BoolProperty(
        name="Scale",
        description="Import bone scale",
        default=False,
    )  # type: ignore

    preserve_face: BoolProperty(
        name="Preserve Face / Hair / Attachments",
        description="Import the body, fingers, Miqo'te ears and tail while carrying the existing face, eyes, hair and attachments with their posed parent",
        default=True,
    )  # type: ignore

    keyframe_pose: BoolProperty(
        name="Insert Keyframes",
        description="Insert keyframes for imported transforms at the current frame",
        default=False,
    )  # type: ignore

    def draw(self, _context):
        layout = self.layout
        layout.prop(self, "target_mode")
        if self.target_mode == "LINKED_BONES":
            layout.prop(self, "reference_gltf")
        row = layout.row(align=True)
        row.prop(self, "import_rotation")
        row.prop(self, "import_location")
        row.prop(self, "import_scale")
        if self.target_mode == "LINKED_BONES":
            layout.prop(self, "preserve_face")
            layout.prop(self, "import_world_rotation")
        layout.prop(self, "keyframe_pose")

    def execute(self, context):
        armature = _find_target_armature(context)
        if armature is None:
            self.report({"ERROR"}, "No visible armature found in this scene")
            return {"CANCELLED"}

        try:
            pose_document = _load_pose_document(self.filepath)
            pose_data = pose_document["bones"]
        except Exception as ex:
            self.report({"ERROR"}, f"Could not read pose file: {ex}")
            return {"CANCELLED"}

        if not pose_data:
            self.report({"ERROR"}, "Pose file did not contain readable bone transforms")
            return {"CANCELLED"}

        # Library selections enter through this undoable operator directly,
        # keeping the browser's last pose metadata without reopening its menu.
        if self.library_people or self.library_action:
            context.scene.aether_pose_current_file = Path(self.filepath).name
            context.scene.aether_pose_branch_people = self.library_people
            context.scene.aether_pose_branch_action = self.library_action

        applied = 0
        skipped = 0
        previous_mode = armature.mode
        for obj in context.selected_objects:
            obj.select_set(False)
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature

        try:
            if armature.mode != "POSE":
                bpy.ops.object.mode_set(mode="POSE")

            if self.target_mode == "LINKED_BONES" and pose_document.get("model_space"):
                reference_path = _find_reference_gltf(armature, self.reference_gltf)
                if reference_path is None:
                    self.report(
                        {"ERROR"},
                        "Could not find the original Meddle .gltf; set Reference glTF in the import options",
                    )
                    return {"CANCELLED"}
                try:
                    unit_scale = 1.0 / context.scene.unit_settings.scale_length
                    reference_matrices = _gltf_reference_matrices(reference_path, unit_scale)
                except Exception as ex:
                    self.report({"ERROR"}, f"Could not read reference glTF: {ex}")
                    return {"CANCELLED"}

                armature["aether_pose_reference_gltf"] = str(reference_path)
                applied, skipped = _apply_model_space_link_pose(
                    armature,
                    pose_data,
                    reference_matrices,
                    self.import_rotation,
                    self.import_location,
                    self.import_scale,
                    self.keyframe_pose,
                    self.preserve_face,
                    unit_scale,
                )
                world_rotation_applied = False
                if self.import_world_rotation:
                    world_rotation_applied = _apply_actor_world_rotation(
                        armature,
                        pose_document.get("actor_rotation"),
                        self.keyframe_pose,
                    )
                self.report(
                    {"INFO"},
                    f"Linked pose applied {applied} bone(s), skipped {skipped}; "
                    f"world rotation {'applied' if world_rotation_applied else 'not present'}",
                )
                return {"FINISHED"} if applied else {"CANCELLED"}

            for source_bone_name, transform in pose_data.items():
                pose_bone = None
                resolved_transform = dict(transform)

                if self.target_mode == "LINKED_BONES":
                    pose_bone = _resolve_pose_bone(armature, f"LINK-{source_bone_name}")
                    if not pose_bone:
                        pose_bone = _resolve_pose_bone(armature, source_bone_name)
                elif self.target_mode == "AETHER_CONTROLS":
                    mapping = POSE_RETARGET_MAP.get(source_bone_name)
                    if mapping:
                        pose_bone = _resolve_pose_bone(armature, mapping.get("target"))
                        if transform.get("rotation") is not None:
                            resolved_transform["rotation"] = _retarget_quaternion(
                                transform["rotation"],
                                mapping.get("invert_rot", (False, False, False, False)),
                            )
                        if transform.get("location") is not None:
                            resolved_transform["location"] = _retarget_location(
                                transform["location"],
                                mapping.get("invert_loc", (False, False, False)),
                            )
                else:
                    pose_bone = _resolve_pose_bone(armature, source_bone_name)

                if not pose_bone:
                    skipped += 1
                    continue

                _apply_transform(
                    pose_bone,
                    resolved_transform,
                    self.import_rotation,
                    self.import_location,
                    self.import_scale,
                    self.keyframe_pose,
                )
                applied += 1
        finally:
            if previous_mode != armature.mode:
                try:
                    bpy.ops.object.mode_set(mode=previous_mode)
                except RuntimeError:
                    pass

        self.report({"INFO"}, f"Pose import applied {applied} bone(s), skipped {skipped}")
        return {"FINISHED"} if applied else {"CANCELLED"}


def menu_func_import(self, _context):
    self.layout.operator("aether.pose_import", text="FFXIV Pose (.pose/.cmp)")


def register():
    bpy.utils.register_class(AETHER_OT_PoseImport)
    bpy.utils.register_class(AETHER_OT_OpenPoseMenu)
    bpy.utils.register_class(AETHER_OT_OpenRootPoseMenu)
    bpy.utils.register_class(AETHER_OT_ApplyLibraryPose)
    bpy.utils.register_class(AETHER_OT_CyclePose)
    bpy.types.Scene.aether_pose_current_file = StringProperty(default="")
    bpy.types.Scene.aether_pose_branch_people = StringProperty(default="")
    bpy.types.Scene.aether_pose_branch_action = StringProperty(default="")
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    for property_name in (
        "aether_pose_current_file",
        "aether_pose_branch_people",
        "aether_pose_branch_action",
    ):
        if hasattr(bpy.types.Scene, property_name):
            delattr(bpy.types.Scene, property_name)
    bpy.utils.unregister_class(AETHER_OT_CyclePose)
    bpy.utils.unregister_class(AETHER_OT_ApplyLibraryPose)
    bpy.utils.unregister_class(AETHER_OT_OpenRootPoseMenu)
    bpy.utils.unregister_class(AETHER_OT_OpenPoseMenu)
    bpy.utils.unregister_class(AETHER_OT_PoseImport)
