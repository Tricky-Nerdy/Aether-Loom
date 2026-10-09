# Aether Loom

A public development copy of [AetherBlend](https://github.com/ShinoMythmaker/Aetherblend). The source import targets upstream tag [v0.3.7](https://github.com/ShinoMythmaker/Aetherblend/releases/tag/v0.3.7), commit `90099ab78d1f7032d0af950e6a8158b230600567`, under GPL-3.0-or-later. This repository was created independently and GitHub may not label it a platform fork.

## Use the upstream plugin now

[Download the official v0.3.7 installer ZIP](https://github.com/ShinoMythmaker/Aetherblend/releases/download/v0.3.7/Aetherblend-v0.3.7.zip). Keep it zipped. In Blender **5.2.0 or newer**, open **Preferences → Get Extensions → Install from Disk** and select the ZIP. This is the upstream installer, not a tested custom Aether Loom build. Upstream says pose and animation import is currently nonfunctional.

## Source and validation

The bootstrap workflow imports the upstream v0.3.7 source, preserves its license and README, checks Python syntax, and attaches a ZIP artifact to its run. Passing syntax checks does not prove Blender runtime compatibility or pose import on the user's PC. Inspect the run before using the source tree as a customized installer.

## Custom changes still to recover

The old custom files and bone-rotation fixes are not yet in this repository. Their reported location is Matrix `/run/media/trickynerdy/Matrix/HerOS/Projects/ffxiv-pose-import-research/Aetherblend/`, with possible copies in `_zOLD_HerOS` and 00–03. The proposed `/home/trick/AetherBlendFork/` path is unverified. This cloud workspace cannot read Matrix, so it cannot identify or port those changes yet.

After recovery, compare actual files and Git history with this upstream baseline, port each pose/rotation fix, and validate with representative pose packs and rig versions in Blender. TexTools, Penumbra, Rigify timeline work, drawn body poses, and hand curves remain requested follow-on features.
