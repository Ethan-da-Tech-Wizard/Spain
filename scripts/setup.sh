#!/usr/bin/env bash
# Program: Spain - setup.sh
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Makes sure a local JDK 25 is available under .tools (downloading and checking a Linux x64 build if needed) and prints the next steps.
# Stop on any error, on unset variables, and on failures inside pipes.
set -euo pipefail
# Move to the project root.
cd "$(dirname "$0")/.."
# Only download Java if it is not already installed here.
if [[ ! -x .tools/jdk25/bin/java ]]; then
  # Automatic download only supports 64-bit Linux; other systems must install JDK 25 themselves.
  if [[ $(uname -s) != Linux || $(uname -m) != x86_64 ]]; then
    echo 'For checks on this platform, install JDK 25 and set SPAIN_JAVA_HOME to its folder.' >&2
    exit 1
  fi
  # Ask Adoptium (the JDK vendor) for the latest JDK 25 download details.
  mkdir -p .tools/jdk25
  curl -fsSL --retry 2 'https://api.adoptium.net/v3/assets/latest/25/hotspot?architecture=x64&image_type=jdk&os=linux&vendor=eclipse' -o .tools/jdk25-assets.json
  python3 - <<'PY'
import json
from pathlib import Path
package = json.loads(Path('.tools/jdk25-assets.json').read_text())[0]['binary']['package']
Path('.tools/jdk25-url.txt').write_text(package['link'])
Path('.tools/jdk25.sha256').write_text(package['checksum'] + '  jdk25.tar.gz\n')
PY
  # Download the archive, then check its SHA-256 checksum before unpacking it.
  curl -fsSL --retry 2 "$(cat .tools/jdk25-url.txt)" -o .tools/jdk25.tar.gz
  (cd .tools && sha256sum -c jdk25.sha256)
  # Unpack the JDK and remove the archive.
  tar -xzf .tools/jdk25.tar.gz -C .tools/jdk25 --strip-components=1
  rm .tools/jdk25.tar.gz
fi
# Tell the user what to run next.
echo 'Ready. Build: ./scripts/build.sh; verify: python3 verification/run_checks.py; install: python3 tools/install_prism.py'
