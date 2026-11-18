#!/usr/bin/env python3
# Program: Spain - setup_spore.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Downloads a pinned release of the SporeModder FX tool, verifies its SHA-256 checksum and unpacks it into .tools.
"""Install a pinned, verified SporeModder FX CLI locally; extracted art stays local."""
# Imports for hashes, downloads and zip files.
import hashlib,urllib.request,zipfile
from pathlib import Path
# ROOT = project folder.
ROOT=Path(__file__).resolve().parents[1]
# Official release download address (version 2.2.27).
URL='https://github.com/Spore-Community/SporeModder-FX/releases/download/v2.2.27/SporeModder.FX.zip'
# The expected checksum.
# SHA-256 pinned below to the reviewed upstream release archive.
SHA256='bd7908996b8022cd7452edefbdb2d62dbbe626d1e22962e83fe30def215e6669'

def setup():
    """Install SporeModder FX locally if needed and return the path to its jar."""
    # Where the tool's jar will be; if it exists, nothing more to do.
    target=ROOT/'.tools/sporemodder/SporeModder FX/SporeModderFX.jar'
    if target.exists():return target
    # Download the archive if not already downloaded.
    archive=ROOT/'.tools/sporemodder.zip';archive.parent.mkdir(parents=True,exist_ok=True)
    if not archive.exists():archive.write_bytes(urllib.request.urlopen(URL,timeout=90).read())
    # Refuse to continue if the checksum does not match.
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=SHA256:raise ValueError('SporeModder FX archive checksum mismatch')
    # Unpack and return the jar path.
    with zipfile.ZipFile(archive) as zipfile_:zipfile_.extractall(ROOT/'.tools/sporemodder')
    return target
# Run setup and print the jar path.
if __name__=='__main__':print(setup())
