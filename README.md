# Aether Loom

Aether Loom is a Blender extension for FFXIV character posing, rigging, expressions, and artist workflow tools. It began from the GPL-3.0-or-later AetherBlend v0.3.7 source baseline by Shino Mythmaker and Oats (upstream commit `90099ab78d1f7032d0af950e6a8158b230600567`) and is being developed independently.

## Current release: v0.7.4

[Download Aether Loom v0.7.4](https://github.com/Tricky-Nerdy/Aether-Loom/releases/tag/v0.7.4).

Keep the extension ZIP zipped. In Blender **5.2.0 or newer**, open **Edit → Preferences → Get Extensions → Install from Disk** and select `Aether-Loom-0.7.4.zip`.

### What v0.7.4 contains

- Anamnesis `.pose` and CMTool `.cmp` pose import.
- A browsable pose-library workflow.
- A dedicated Expression Library with expression extraction, blending, and multi-expression layers.
- XIVTools-oriented connection and path discovery, including one-click settings autodetection.
- Python 3.14 LZ4 support.
- Rigify leg-generation handling for heel-pivot helper bones.

XIVTools integration currently discovers configured paths and existing exports. Fully unattended character extraction is still future work and should not be treated as complete in v0.7.4.

For model-space pose import, select the source character's Meddle `.gltf` in the import options or keep it beside the `.blend` file. Set the pose-library directory under **Edit → Preferences → Add-ons → Aether Loom → Default File Paths**.

The default pose target mode is **AetherBlend Linked Pose**. It needs the original character Meddle `.gltf` rest pose to map Anamnesis model-space transforms onto the rig. **Matching Bone Names** is available for compatible armatures, and the **Legacy Control Map** is retained for development.

## Versioning policy

Aether Loom uses semantic versioning while it is pre-1.0:

- **0.MINOR.0** — a meaningful new capability or workflow milestone.
- **0.MINOR.PATCH** — fixes, polish, tests, documentation, or small compatible improvements to that milestone.
- **1.0.0** — the first stable release whose core artist workflow is considered dependable and documented.

Development commits do not require a version bump. A version changes only when a tested release is intentionally cut.

## Commit policy

Commits should describe one logical change using a consistent prefix:

- `feat:` new user-facing capability
- `fix:` bug correction
- `test:` tests or validation
- `docs:` documentation only
- `build:` packaging, dependencies, or release automation
- `refactor:` internal restructuring without intended behavior change
- `release:` final version metadata and release preparation

Several commits in the same hour are normal. Prefer small, understandable commits over artificially spacing them out.

## Source and validation

Run `blender -b --python tests/blender_smoke.py` for Blender smoke tests covering pose import and Rigify generation. Automated validation also runs on GitHub before release packaging.

Historical releases and commits are intentionally retained. They document how Aether Loom evolved; cleanup should correct current documentation and future conventions rather than rewrite published history.

## Build locally

Install `tomli-w`, run `python get_dependencies.py`, then run `blender -c extension build`. Dependency wheels are selected for Python 3.11, 3.13, and 3.14.
