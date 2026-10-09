#!/usr/bin/env bash
# Prepare and verify Spain; deliberately never launch or restart a game window.
set -euo pipefail
cd "$(dirname "$0")/.."
./scripts/setup.sh
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
  .venv/bin/pip install --disable-pip-version-check Pillow==12.0.0
fi
if [[ -f "$HOME/.local/share/Steam/steamapps/common/Spore/Data/Spore_Graphics.package" && ! -f local-assets/spore/spore_creature.voxels.json ]]; then
  python3 tools/setup_spore.py
  python3 tools/import_spore.py
fi
if [[ -f ../meltyblndr/holy-order/assets/waw/models/crate.glb && ! -f local-assets/structures/crate.nbt ]]; then
  .venv/bin/python tools/import_assets.py
fi
python3 tools/asset_status.py
python3 tools/build_mod.py --dependencies-only
python3 tools/repair_libraries.py
python3 verification/run_checks.py
.venv/bin/python -m unittest discover -s verification -p 'test_*.py'
python3 tools/install_prism.py
printf '%s\n' 'Spain updated. Launch or restart it manually when you are ready.'
