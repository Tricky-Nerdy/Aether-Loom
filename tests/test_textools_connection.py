import tempfile
import unittest
from pathlib import Path
import importlib.util

MODULE = Path(__file__).resolve().parents[1] / "features/model_import/textools_connection.py"
spec = importlib.util.spec_from_file_location("textools_connection", MODULE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TexToolsConnectionTests(unittest.TestCase):
    def test_discover_exports(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = root / "game"
            (game / "sqpack").mkdir(parents=True)
            tool = root / "TexTools.exe"
            tool.touch()
            exports = root / "exports"
            exports.mkdir()
            for name in ("body.fbx", "pose.pose", "character.chara", "ignored.txt"):
                (exports / name).touch()
            result = module.inspect_paths(game, tool, exports)
            self.assertTrue(result["connected"])
            self.assertEqual({k: len(v) for k, v in result["files"].items()},
                             {"models": 1, "poses": 1, "characters": 1})

    def test_invalid_paths(self):
        result = module.inspect_paths("/missing/game", "/missing/tool", "/missing/exports")
        self.assertFalse(result["connected"])
        self.assertEqual(len(result["problems"]), 3)


if __name__ == "__main__":
    unittest.main()
