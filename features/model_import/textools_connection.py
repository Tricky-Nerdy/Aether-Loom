"""Read-only connection validation for FFXIV and XIVTools export folders.

This module never modifies game data and never executes third-party binaries.
"""
from pathlib import Path

MODEL_SUFFIXES = frozenset({".fbx", ".glb", ".gltf", ".obj", ".dae"})
POSE_SUFFIXES = frozenset({".pose"})
CHARACTER_SUFFIXES = frozenset({".chara"})


def inspect_paths(game_path, xivtools_path, export_path):
    game = Path(game_path).expanduser()
    tool = Path(xivtools_path).expanduser()
    exports = Path(export_path).expanduser()
    problems = []
    if not game.is_dir() or not (game / "sqpack").is_dir():
        problems.append("Game path must point to the FFXIV game directory containing sqpack")
    if not (tool.is_file() or (tool.is_dir() and (tool / "app" / "xivtools-ui").is_file())):
        problems.append("XIVTools path does not exist")
    if not exports.is_dir():
        problems.append("Export directory does not exist")
    files = {"models": [], "poses": [], "characters": []}
    if exports.is_dir():
        for path in exports.rglob("*"):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix in MODEL_SUFFIXES:
                files["models"].append(str(path))
            elif suffix in POSE_SUFFIXES:
                files["poses"].append(str(path))
            elif suffix in CHARACTER_SUFFIXES:
                files["characters"].append(str(path))
    return {"connected": not problems, "problems": problems, "files": files}


def discover_xivtools_settings(config_path=None):
    """Read XIVTools' documented configuration without launching or modifying it."""
    import json
    config = Path(config_path).expanduser() if config_path else Path.home() / ".config/xivtools/settings.json"
    if not config.is_file():
        return {"game": "", "mods": "", "config_found": False}
    try:
        settings = json.loads(config.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"game": "", "mods": "", "config_found": False}
    if not isinstance(settings, dict):
        return {"game": "", "mods": "", "config_found": False}
    return {"game": str(settings.get("GamePath") or ""),
            "mods": str(settings.get("ModsPath") or ""), "config_found": True}


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description="Validate FFXIV, XIVTools, and export paths")
    parser.add_argument("--game", required=True)
    parser.add_argument("--xivtools", required=True)
    parser.add_argument("--exports", required=True)
    args = parser.parse_args()
    print(json.dumps(inspect_paths(args.game, args.xivtools, args.exports), indent=2))
