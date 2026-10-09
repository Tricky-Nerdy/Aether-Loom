# Aether Loom

A public development copy of [AetherBlend](https://github.com/ShinoMythmaker/Aetherblend). The source import targets upstream tag [v0.3.7](https://github.com/ShinoMythmaker/Aetherblend/releases/tag/v0.3.7), commit `90099ab78d1f7032d0af950e6a8158b230600567`, under GPL-3.0-or-later. This repository was created independently and GitHub may not label it a platform fork.

## Use the upstream plugin now

[Download the official v0.3.7 installer ZIP](https://github.com/ShinoMythmaker/Aetherblend/releases/download/v0.3.7/Aetherblend-v0.3.7.zip). Keep it zipped. In Blender **5.2.0 or newer**, open **Preferences → Get Extensions → Install from Disk** and select the ZIP. This is the upstream installer, not a tested custom Aether Loom build. Upstream says pose and animation import is currently nonfunctional.

## Source and validation

The upstream v0.3.7 source was imported on `main` in commit `0e428218`. The [bootstrap run](https://github.com/Tricky-Nerdy/Aether-Loom/actions/runs/37968360967) passed Python syntax checks and ZIP integrity checks and attached the official installer ZIP. That run did not test Blender runtime behavior or pose import on the user's PC. The import workflow is now manual and refuses to overwrite the source tree.

## Custom changes still to recover

The old custom files and bone-rotation fixes are not yet in this repository. Their reported location is Matrix `/run/media/trickynerdy/Matrix/HerOS/Projects/ffxiv-pose-import-research/Aetherblend/`, with possible copies in `_zOLD_HerOS` and 00–03. The proposed `/home/trick/AetherBlendFork/` path is unverified. This cloud workspace cannot read Matrix, so it cannot identify or port those changes yet.

After recovery, compare actual files and Git history with this upstream baseline, port each pose/rotation fix, and validate with representative pose packs and rig versions in Blender. TexTools, Penumbra, Rigify timeline work, drawn body poses, and hand curves remain requested follow-on features.
