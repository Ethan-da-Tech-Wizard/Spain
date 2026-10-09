#!/usr/bin/env bash
set -euo pipefail
# The local test uses an offline name by default. Pass --profile NAME for an account skin.
if [[ $# -eq 0 ]]; then
  exec prismlauncher --launch Spain --world Spain --offline SpainExplorer
fi
exec prismlauncher --launch Spain --world Spain "$@"
