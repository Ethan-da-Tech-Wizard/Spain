#!/usr/bin/env bash
# Program: Spain - play-spain.sh
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Launches the Spain Minecraft instance in Prism Launcher, with an offline test name by default.
# Stop on any error, on unset variables, and on failures inside pipes.
set -euo pipefail
# The local test uses an offline name by default. Pass --profile NAME for an account skin.
# With no arguments, start the Spain world offline as the player "SpainExplorer".
if [[ $# -eq 0 ]]; then
  exec prismlauncher --launch Spain --world Spain --offline SpainExplorer
fi
# With arguments (for example --profile NAME), pass them straight through to Prism.
exec prismlauncher --launch Spain --world Spain "$@"
