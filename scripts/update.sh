#!/usr/bin/env bash

# ==============================================================================
# Program: update.sh
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 18, 2026
# Purpose: One-command refresh of the whole project: toolchain, optional local art, Fabric
#          dependencies, library repair, in-game checks, unit tests, and installation into the Spain
#          Prism instance. Never launches or restarts the game.
# ==============================================================================

# Steps (each stops the script on failure because of `set -e`):
#   1 toolchain  2 Python venv with Pillow  3 optional local art  4 asset status  5 Fabric dependencies
#   6 Minecraft libraries  7 in-game checks  8 unit tests  9 install into Prism
# Run it whenever sources change; it is repeatable. Needs network for the first Fabric/JDK downloads.
# Prepare and verify Spain; deliberately never launch or restart a game window.

# Strict mode: abort on any error, unset variable or failed pipe stage.
set -euo pipefail

# Always work from the repository root.
cd "$(dirname "$0")/.."

# 1. JDK 25 (downloaded on Linux x86-64 only, otherwise SPAIN_JAVA_HOME must point to one).
./scripts/setup.sh

# 2. A private Python environment with Pillow, which import_assets.py needs to read model textures. Pinned to 12.0.0 so builds are repeatable.
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
  .venv/bin/pip install --disable-pip-version-check Pillow==12.0.0
fi

# 3a. Optional Spore art: only if Spore is installed through Steam and the converted files do not exist yet, install SporeModder FX and convert the three models. Skipped silently otherwise.
if [[ -f "$HOME/.local/share/Steam/steamapps/common/Spore/Data/Spore_Graphics.package" && ! -f local-assets/spore/spore_creature.voxels.json ]]; then
  python3 tools/setup_spore.py
  python3 tools/import_spore.py
fi

# 3b. Optional crate/pine art from a sibling project, converted once if present and not yet done.
if [[ -f ../meltyblndr/holy-order/assets/waw/models/crate.glb && ! -f local-assets/structures/crate.nbt ]]; then
  .venv/bin/python tools/import_assets.py
fi

# 4. Report which optional art sources are ready (information only; missing art does not stop the update).
python3 tools/asset_status.py

# 5. Fetch and verify Fabric loader and API (cached after the first run).
python3 tools/build_mod.py --dependencies-only

# 6. Make sure all Minecraft and Fabric library jars exist and match their hashes.
python3 tools/repair_libraries.py

# 7. Build everything and run the in-game test suite; a failure here stops the script before anything is installed.
python3 verification/run_checks.py

# 8. Unit tests of the helper tools; run in the venv so Pillow is available.
.venv/bin/python -m unittest discover -s verification -p 'test_*.py'

# 9. Copy the mod, Fabric API and the data pack into the Spain Prism instance (creating the starter world on first use).
python3 tools/install_prism.py

# The game is never started automatically, so an open game window is not disturbed.
printf '%s\n' 'Spain updated. Launch or restart it manually when you are ready.'
