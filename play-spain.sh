#!/usr/bin/env bash

# ==============================================================================
# Program: play-spain.sh
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 18, 2026
# Purpose: Launches the Spain instance in Prism Launcher. With no arguments it joins the Spain world
#          offline as SpainExplorer; with arguments (for example --profile NAME) they replace that default.
# ==============================================================================

# Run from the Play Spain.desktop launcher (or a terminal) in the repository folder. Does not build or install; run scripts/update.sh first.
# Strict mode: stop on errors and unset variables.
set -euo pipefail

# No argument: start instance "Spain", join the world "Spain" directly, with the offline player name SpainExplorer (no Microsoft login needed for local testing).
# The local test uses an offline name by default. Pass --profile NAME for an account skin.
if [[ $# -eq 0 ]]; then
  exec prismlauncher --launch Spain --world Spain --offline SpainExplorer
fi

# With arguments, pass them through unchanged so a real account profile can be used. `exec` replaces the shell with Prism so the launcher shows as one process.
exec prismlauncher --launch Spain --world Spain "$@"
