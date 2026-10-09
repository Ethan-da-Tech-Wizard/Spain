#!/usr/bin/env python3
"""Install a pinned, verified SporeModder FX CLI locally; extracted art stays local."""
import hashlib,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
URL='https://github.com/Spore-Community/SporeModder-FX/releases/download/v2.2.27/SporeModder.FX.zip'
# SHA-256 pinned below to the reviewed upstream release archive.
SHA256='bd7908996b8022cd7452edefbdb2d62dbbe626d1e22962e83fe30def215e6669'

def setup():
    target=ROOT/'.tools/sporemodder/SporeModder FX/SporeModderFX.jar'
    if target.exists():return target
    archive=ROOT/'.tools/sporemodder.zip';archive.parent.mkdir(parents=True,exist_ok=True)
    if not archive.exists():archive.write_bytes(urllib.request.urlopen(URL,timeout=90).read())
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=SHA256:raise ValueError('SporeModder FX archive checksum mismatch')
    with zipfile.ZipFile(archive) as zipfile_:zipfile_.extractall(ROOT/'.tools/sporemodder')
    return target
if __name__=='__main__':print(setup())
