#!/usr/bin/env python3
# ==============================================================================
# Program: repair_libraries.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Re-downloads any missing or corrupt Minecraft and Fabric library jars (Linux only)
#          listed in Prism's metadata, checking each file's SHA-1, using 6 worker threads.
# ==============================================================================

"""Fetch missing Linux client libraries using Prism's own version metadata and hashes."""

# Fit in the repo: repair step run by scripts/update.sh. Minecraft's Linux libraries (LWJGL native jars and others)
# are normally downloaded by Prism the first time the game launches; this script makes sure they are all present and
# correct before verification/run_checks.py and build_mod.py rely on them, without having to start the game.
#
# Input : Prism's own metadata files meta/org.lwjgl3/3.4.3.json and meta/net.minecraft/26.3.json (already on
#         disk once Prism has set up Minecraft 26.3), plus .tools/fabric/profile.json when it exists.
# Output: jar files under ~/.local/share/PrismLauncher/libraries; prints each file it downloaded.
# Security: every download is checked against the SHA-1 in the metadata; a mismatch raises and nothing is written.
# Limits: only libraries meant for Linux are considered; library entries without a hash are accepted as downloaded.
import concurrent.futures,hashlib,json,urllib.request
from pathlib import Path

# Prism's data folder (Linux default location).
PRISM=Path.home()/'.local/share/PrismLauncher'

def fetch(job):
    """Download one library if it is missing or corrupt; return its file name when downloaded, else None.

    Args:
        job: tuple (destination Path, URL, expected SHA-1 hex or None).

    Runs in worker threads. Each job writes a different file, so no locking is needed.
    """
    path,url,sha=job

    # Skip files that exist and match their hash (or exist and have no hash to compare), so a second run does almost nothing.
    if path.exists() and (not sha or hashlib.sha1(path.read_bytes()).hexdigest()==sha):return None
    data=urllib.request.urlopen(url,timeout=45).read()
    if sha and hashlib.sha1(data).hexdigest()!=sha:raise ValueError('Checksum mismatch: '+str(path))
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);return path.name

def repair():
    """Collect every needed library from the metadata files and download what is missing."""
    jobs=[]
    for meta in ['org.lwjgl3/3.4.3.json','net.minecraft/26.3.json']:
        value=json.loads((PRISM/'meta'/meta).read_text())
        for item in value['libraries']:
            rules=item.get('rules')

            # Mojang metadata marks platform-specific libraries with `rules`. Keep the entry only if an "allow" rule applies to Linux (a rule without an os name is treated as Linux); anything else (Windows or macOS natives) is skipped.
            if rules and not any(r['action']=='allow' and r.get('os',{}).get('name','linux')=='linux' for r in rules):continue

            # Maven coordinates "group:name:version[:classifier]" become the path group/as/folders/name/version/name-version[-classifier].jar, the layout Prism uses.
            group,name,version,*classifier=item['name'].split(':')
            leaf=name+'-'+version+('-'+classifier[0] if classifier else '')+'.jar'
            relative=group.replace('.','/')+'/'+name+'/'+version+'/'+leaf
            artifact=item.get('downloads',{}).get('artifact',{})

            # Prefer the explicit download URL; otherwise fall back to Mojang's library server plus the Maven path.
            url=artifact.get('url',item.get('url','https://libraries.minecraft.net/')+relative)
            jobs.append((PRISM/'libraries'/relative,url,artifact.get('sha1')))

    # Libraries required by the Fabric loader, from the profile that build_mod.dependencies() saved. Their repository URL is part of each entry.
    # Fabric's loader dependencies are pinned by its official profile.
    profile=Path(__file__).resolve().parents[1]/'.tools/fabric/profile.json'
    if profile.exists():
        for item in json.loads(profile.read_text())['libraries']:
            group,name,version=item['name'].split(':');relative=group.replace('.','/')+'/'+name+'/'+version+'/'+name+'-'+version+'.jar'
            jobs.append((PRISM/'libraries'/relative,item['url']+relative,item.get('sha1')))

    # Network-bound work, so a few threads speed it up; 6 stays polite to the servers. executor.map re-raises any worker exception here, which stops the run.
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        for result in executor.map(fetch,jobs):
            if result:print('Downloaded',result)
    print('Client libraries verified.')
if __name__=='__main__':repair()
