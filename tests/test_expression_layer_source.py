"""Source-level regression checks for expression layer sequencing.

Blender integration tests are still required to verify evaluated rig behavior.
"""
import ast
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "features/animation/expression_library.py"


class ExpressionLayerSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        cls.functions = {
            node.name: node for node in cls.tree.body
            if isinstance(node, ast.FunctionDef)
        }

    def test_layer_mixer_restores_once_and_does_not_call_preview(self):
        fn = self.functions["_apply_layers"]
        calls = [
            n.func.id for n in ast.walk(fn)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        ]
        self.assertEqual(calls.count("_restore_face"), 1)
        self.assertIn("_blend_preset", calls)
        self.assertNotIn("_apply_preset", calls)

    def test_preview_uses_shared_blend_primitive(self):
        fn = self.functions["_apply_preset"]
        calls = [
            n.func.id for n in ast.walk(fn)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        ]
        self.assertIn("_restore_face", calls)
        self.assertIn("_blend_preset", calls)

    def test_layer_lookup_uses_full_path(self):
        fn = self.functions["_apply_layers"]
        text = ast.unparse(fn)
        self.assertIn("str(path)", text)
        self.assertIn("layer.file", text)


if __name__ == "__main__":
    unittest.main()
