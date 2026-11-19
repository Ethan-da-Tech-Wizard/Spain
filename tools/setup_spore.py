#!/usr/bin/env python3
# ==============================================================================
# Program: setup_spore.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Downloads the pinned SporeModder FX release, checks its SHA-256 against a hash
#          recorded in this file and unpacks it under .tools/ so import_spore.py can run.
# ==============================================================================

"""Install a pinned, verified SporeModder FX CLI locally; extracted art stays local."""

# Fit in the repo: step one of the optional Spore import. scripts/update.sh calls it (only when Spore is
# installed) before tools/import_spore.py, which needs the extractor jar this script places at
# .tools/sporemodder/SporeModder FX/SporeModderFX.jar. SporeModder FX is a separate GPL-3.0 project; it
# is downloaded rather than bundled, so no GPL code becomes part of this repository.
#
# Security: the release archive is only used if its SHA-256 equals the value pinned below, so a changed or
# tampered download is rejected before anything is unpacked.
# Network: one HTTPS download of about the size of the release zip, only if the jar is not already installed.
import hashlib,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

# Exact release (v2.2.27), not "latest", so the checksum below stays valid.
URL='https://github.com/Spore-Community/SporeModder-FX/releases/download/v2.2.27/SporeModder.FX.zip'
# SHA-256 pinned below to the reviewed upstream release archive.
SHA256='bd7908996b8022cd7452edefbdb2d62dbbe626d1e22962e83fe30def215e6669'

def setup():
    """Ensure the SporeModder FX jar is installed and return its path.

    Idempotent: returns immediately if the jar exists. Otherwise downloads the zip (cached as .tools/sporemodder.zip,
    reused if already present), verifies the SHA-256, and extracts it.

    Raises:
        ValueError: if the checksum does not match the pinned value.
        urllib.error.URLError: if the download fails.
    """
    target=ROOT/'.tools/sporemodder/SporeModder FX/SporeModderFX.jar'
    if target.exists():return target
    archive=ROOT/'.tools/sporemodder.zip';archive.parent.mkdir(parents=True,exist_ok=True)
    if not archive.exists():archive.write_bytes(urllib.request.urlopen(URL,timeout=90).read())
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=SHA256:raise ValueError('SporeModder FX archive checksum mismatch')

    # extractall strips absolute paths and ".." parts from member names, so a malicious zip cannot write outside the target folder. The variable is named zipfile_ to avoid shadowing the zipfile module.
    with zipfile.ZipFile(archive) as zipfile_:zipfile_.extractall(ROOT/'.tools/sporemodder')
    return target
if __name__=='__main__':print(setup())
