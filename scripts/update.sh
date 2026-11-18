#!/usr/bin/env bash
# Program: Spain - update.sh
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Prepares and verifies the whole Spain project (tools, assets, mod build, checks, Prism install) without ever launching the game.
# Prepare and verify Spain; deliberately never launch or restart a game window.
# Stop on any error, on unset variables, and on failures inside pipes.
set -euo pipefail
# Move to the project root.
cd "$(dirname "$0")/.."
# Make sure Java is available.
./scripts/setup.sh
# Create a Python virtual environment with Pillow (needed for converting art) if missing.
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
  .venv/bin/pip install --disable-pip-version-check Pillow==12.0.0
fi
# If Spore is installed through Steam and its art has not been converted yet, install the extractor and convert it.
if [[ -f "$HOME/.local/share/Steam/steamapps/common/Spore/Data/Spore_Graphics.package" && ! -f local-assets/spore/spore_creature.voxels.json ]]; then
  python3 tools/setup_spore.py
  python3 tools/import_spore.py
fi
# If the local Melty crate model exists and has not been converted yet, convert it to Minecraft blocks.
if [[ -f ../meltyblndr/holy-order/assets/waw/models/crate.glb && ! -f local-assets/structures/crate.nbt ]]; then
  .venv/bin/python tools/import_assets.py
fi
# Report which tools and assets are present.
python3 tools/asset_status.py
# Download the Fabric dependencies and repair any missing game libraries.
python3 tools/build_mod.py --dependencies-only
python3 tools/repair_libraries.py
# Run the real Minecraft server checks, then the Python unit tests.
python3 verification/run_checks.py
.venv/bin/python -m unittest discover -s verification -p 'test_*.py'
# Install the checked build into the Prism instance.
python3 tools/install_prism.py
# Remind the user to start the game themselves.
printf '%s\n' 'Spain updated. Launch or restart it manually when you are ready.'
