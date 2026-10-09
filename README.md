# Aether Loom

A public development copy of [AetherBlend](https://github.com/ShinoMythmaker/Aetherblend). The source import targets upstream tag [v0.3.7](https://github.com/ShinoMythmaker/Aetherblend/releases/tag/v0.3.7), commit `90099ab78d1f7032d0af950e6a8158b230600567`, under GPL-3.0-or-later. This repository was created independently and GitHub may not label it a platform fork.

## Install Aether Loom

[Download the Aether Loom v0.4.0 extension ZIP](https://github.com/Tricky-Nerdy/Aether-Loom/releases/download/v0.4.0/AetherBlend-0.4.0.zip). Keep it zipped. In Blender **5.2.0 or newer**, open **Edit → Preferences → Get Extensions → Install from Disk** and select the ZIP.

This build adds Anamnesis `.pose` and CMTool `.cmp` pose import, a browsable pose-library UI, Python 3.14 LZ4 support, and a Rigify leg-generation fix for heel-pivot helper bones. For model-space pose import, select the source character's Meddle `.gltf` in the import options or keep it beside the `.blend` file. Set the pose-library directory under **Edit → Preferences → Add-ons → AetherBlend → Default File Paths**.

The default pose target mode is **AetherBlend Linked Pose**. It needs the original character Meddle `.gltf` rest pose to map Anamnesis model-space transforms onto the rig. **Matching Bone Names** is available for compatible armatures, and the **Legacy Control Map** is retained for development.

To build a local extension package, install `tomli-w`, run `python get_dependencies.py`, then run `blender -c extension build`. Dependency wheels are selected for Python 3.11, 3.13, and 3.14.

## Source and validation

The code is based on upstream AetherBlend v0.3.7, commit `90099ab78d1f7032d0af950e6a8158b230600567`. Run `blender -b --python tests/blender_smoke.py` for smoke tests covering Anamnesis and CMTool import plus successful Rigify leg generation. The importer was also checked against four representative poses on the recovered GraceFullbloom character rig.

## Source and validation

The source baseline is upstream AetherBlend v0.3.7, commit `90099ab78d1f7032d0af950e6a8158b230600567`. Matrix pose-import work was recovered from the local research project and ported onto this baseline. The original official installer does not contain these development changes; build an extension package from this repository to use them.
