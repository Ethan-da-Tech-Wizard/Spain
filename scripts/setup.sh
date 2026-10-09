#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .tools/jdk25/bin/java ]]; then
  if [[ $(uname -s) != Linux || $(uname -m) != x86_64 ]]; then
    echo 'For checks on this platform, install JDK 25 and set SPAIN_JAVA_HOME to its folder.' >&2
    exit 1
  fi
  mkdir -p .tools/jdk25
  curl -fsSL --retry 2 'https://api.adoptium.net/v3/assets/latest/25/hotspot?architecture=x64&image_type=jdk&os=linux&vendor=eclipse' -o .tools/jdk25-assets.json
  python3 - <<'PY'
import json
from pathlib import Path
package = json.loads(Path('.tools/jdk25-assets.json').read_text())[0]['binary']['package']
Path('.tools/jdk25-url.txt').write_text(package['link'])
Path('.tools/jdk25.sha256').write_text(package['checksum'] + '  jdk25.tar.gz\n')
PY
  curl -fsSL --retry 2 "$(cat .tools/jdk25-url.txt)" -o .tools/jdk25.tar.gz
  (cd .tools && sha256sum -c jdk25.sha256)
  tar -xzf .tools/jdk25.tar.gz -C .tools/jdk25 --strip-components=1
  rm .tools/jdk25.tar.gz
fi
echo 'Ready. Build: ./scripts/build.sh; verify: python3 verification/run_checks.py; install: python3 tools/install_prism.py'
