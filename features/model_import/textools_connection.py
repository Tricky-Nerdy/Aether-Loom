"""Read-only connection validation for FFXIV and TexTools export folders.

This module never modifies game data and never executes third-party binaries.
"""
from pathlib import Path

MODEL_SUFFIXES = frozenset({".fbx", ".glb", ".gltf", ".obj", ".dae"})
POSE_SUFFIXES = frozenset({".pose"})
CHARACTER_SUFFIXES = frozenset({".chara"})


def inspect_paths(game_path, textools_path, export_path):
    game = Path(game_path).expanduser()
    tool = Path(textools_path).expanduser()
    exports = Path(export_path).expanduser()
    problems = []
    if not game.is_dir() or not (game / "sqpack").is_dir():
        problems.append("Game path must point to the FFXIV game directory containing sqpack")
    if not tool.exists():
        problems.append("TexTools path does not exist")
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


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description="Validate FFXIV, TexTools, and export paths")
    parser.add_argument("--game", required=True)
    parser.add_argument("--textools", required=True)
    parser.add_argument("--exports", required=True)
    args = parser.parse_args()
    print(json.dumps(inspect_paths(args.game, args.textools, args.exports), indent=2))
