#!/usr/bin/env bash

# ==============================================================================
# Program: play-spain.sh
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 18, 2026
# Purpose: Main shell launch script for Spain Starforge Minecraft instance.
#          Verifies Prism launcher paths, initializes game profile, and boots client.
# ==============================================================================
set -euo pipefail
# The local test uses an offline name by default. Pass --profile NAME for an account skin.
if [[ $# -eq 0 ]]; then
  exec prismlauncher --launch Spain --world Spain --offline SpainExplorer
fi
exec prismlauncher --launch Spain --world Spain "$@"
