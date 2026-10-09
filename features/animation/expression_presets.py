"""Pure helpers for extracting facial-expression presets from FFXIV pose files."""

import json
import re
from pathlib import Path

_EXPRESSION_BONES = {"j_ago"}
_EXPRESSION_PREFIXES = ("j_f_", "n_f_")


def is_expression_bone(name):
    """Return True for FFXIV facial bones while excluding hair/ears/body bones."""
    clean = re.sub(r"\.\d+$", "", str(name))
    return clean in _EXPRESSION_BONES or clean.startswith(_EXPRESSION_PREFIXES)


def extract_expression_document(document, *, name="", source=""):
    """Build a portable preset containing only facial transforms."""
    source_bones = document.get("Bones")
    if not isinstance(source_bones, dict):
        raise ValueError("Expression extraction currently requires an Anamnesis .pose document")

    bones = {}
    for bone_name, transform in source_bones.items():
        clean = re.sub(r"\.\d+$", "", bone_name)
        if transform is not None and is_expression_bone(clean):
            bones[clean] = transform

    return {
        "schema": "aether-loom-expression-v1",
        "name": name or (Path(source).stem if source else "Expression"),
        "source": source,
        "bones": bones,
    }


def extract_expression_file(source, output=None, *, name=""):
    source_path = Path(source).expanduser().resolve()
    with source_path.open("r", encoding="utf-8-sig") as handle:
        document = json.load(handle)
    preset = extract_expression_document(document, name=name, source=str(source_path))
    if not preset["bones"]:
        raise ValueError(f"No facial-expression bones found in {source_path.name}")
    if output:
        output_path = Path(output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(preset, handle, indent=2, sort_keys=True)
            handle.write("\n")
    return preset


def batch_extract(directory, output_directory, *, recursive=True):
    """Extract named presets from every Anamnesis .pose file in a library."""
    root = Path(directory).expanduser().resolve()
    destination = Path(output_directory).expanduser().resolve()
    pattern = "**/*.pose" if recursive else "*.pose"
    results = []
    for source in sorted(root.glob(pattern)):
        if not source.is_file():
            continue
        relative = source.relative_to(root).with_suffix(".expression.json")
        output = destination / relative
        try:
            preset = extract_expression_file(source, output)
        except (ValueError, json.JSONDecodeError, OSError) as exc:
            results.append({"source": str(source), "ok": False, "error": str(exc)})
            continue
        results.append({
            "source": str(source),
            "output": str(output),
            "name": preset["name"],
            "bones": len(preset["bones"]),
            "ok": True,
        })
    return results
