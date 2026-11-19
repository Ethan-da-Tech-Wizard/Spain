#!/usr/bin/env bash

# ==============================================================================
# Program: setup.sh
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 18, 2026
# Purpose: Prepares the build toolchain: on Linux x86-64 downloads the Eclipse Temurin JDK 25 into
#          .tools/jdk25 (checksum-verified) if it is missing. On other systems it only explains how
#          to provide a JDK 25 through SPAIN_JAVA_HOME. Does not fetch Fabric (build_mod.py does).
# ==============================================================================

# Called by update.sh first. Safe to run repeatedly: when the JDK already exists it does nothing.
# Output: .tools/jdk25 (a full JDK, used by build_mod.py, run_checks.py and install_prism.py).
# Network: one call to Adoptium's API and one JDK download (about 200 MB), only on a fresh Linux x86-64 machine.
# Strict mode: -e stop at the first failing command, -u treat unset variables as errors, -o pipefail make a failing pipe stage fail the pipe.
set -euo pipefail

# Work from the repository root, wherever the script is started from (the script lives in scripts/).
cd "$(dirname "$0")/.."

# Only provision when the bundled JDK is absent (or not executable).
if [[ ! -x .tools/jdk25/bin/java ]]; then

  # The download below is a Linux x64 build, so any other system is told to install JDK 25 itself and point SPAIN_JAVA_HOME at it.
  if [[ $(uname -s) != Linux || $(uname -m) != x86_64 ]]; then
    echo 'For checks on this platform, install JDK 25 and set SPAIN_JAVA_HOME to its folder.' >&2
    exit 1
  fi

  # Target folder; .tools/ is git-ignored.
  mkdir -p .tools/jdk25

  # Ask Adoptium's API for the latest JDK 25 build metadata: -f fail on HTTP errors, -sS quiet but show errors, -L follow redirects.
  curl -fsSL --retry 2 'https://api.adoptium.net/v3/assets/latest/25/hotspot?architecture=x64&image_type=jdk&os=linux&vendor=eclipse' -o .tools/jdk25-assets.json

  # Pull the download link and expected SHA-256 out of the JSON (index 0 = newest build) and save them to files, so the shell can use them for the download and the check.
  python3 - <<'PY'
import json
from pathlib import Path
package = json.loads(Path('.tools/jdk25-assets.json').read_text())[0]['binary']['package']
Path('.tools/jdk25-url.txt').write_text(package['link'])
Path('.tools/jdk25.sha256').write_text(package['checksum'] + '  jdk25.tar.gz\n')
PY

  # Download the archive from the link found above.
  curl -fsSL --retry 2 "$(cat .tools/jdk25-url.txt)" -o .tools/jdk25.tar.gz

  # Verify the archive against the hash Adoptium published; a mismatch fails the script (set -e) before anything is unpacked. The subshell keeps the cd local.
  (cd .tools && sha256sum -c jdk25.sha256)

  # --strip-components=1 removes the archive's top folder so bin/java ends up at .tools/jdk25/bin/java.
  tar -xzf .tools/jdk25.tar.gz -C .tools/jdk25 --strip-components=1

  # Remove the 200 MB archive after a successful unpack.
  rm .tools/jdk25.tar.gz
fi

# Hint for the next manual steps; update.sh performs all of them automatically.
echo 'Ready. Build: ./scripts/build.sh; verify: python3 verification/run_checks.py; install: python3 tools/install_prism.py'
