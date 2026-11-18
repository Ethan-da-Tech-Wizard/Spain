#!/usr/bin/env python3
# Program: Spain - repair_libraries.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Downloads any missing Linux Minecraft and Fabric library jars using Prism's own metadata, checking their SHA-1 hashes.
"""Fetch missing Linux client libraries using Prism's own version metadata and hashes."""
# Imports for parallel downloads, hashes, JSON and web requests.
import concurrent.futures,hashlib,json,urllib.request
from pathlib import Path
# Prism Launcher's data folder.
PRISM=Path.home()/'.local/share/PrismLauncher'

def fetch(job):
    """Download one library if it is missing or wrong; return its file name if downloaded, else None."""
    # A job is (file path, download address, expected hash).
    path,url,sha=job
    # Already present and correct: nothing to do.
    if path.exists() and (not sha or hashlib.sha1(path.read_bytes()).hexdigest()==sha):return None
    # Download and refuse the file if its hash does not match.
    data=urllib.request.urlopen(url,timeout=45).read()
    if sha and hashlib.sha1(data).hexdigest()!=sha:raise ValueError('Checksum mismatch: '+str(path))
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);return path.name

def repair():
    """Find every needed library jar and download the missing ones."""
    # Build the list of downloads from the LWJGL and Minecraft version files.
    jobs=[]
    for meta in ['org.lwjgl3/3.4.3.json','net.minecraft/26.3.json']:
        value=json.loads((PRISM/'meta'/meta).read_text())
        for item in value['libraries']:
            # Skip libraries that are not allowed on Linux.
            rules=item.get('rules')
            if rules and not any(r['action']=='allow' and r.get('os',{}).get('name','linux')=='linux' for r in rules):continue
            # Turn "group:name:version" into the repository path of the jar.
            group,name,version,*classifier=item['name'].split(':')
            leaf=name+'-'+version+('-'+classifier[0] if classifier else '')+'.jar'
            relative=group.replace('.','/')+'/'+name+'/'+version+'/'+leaf
            # Use the download address and hash from the metadata when present.
            artifact=item.get('downloads',{}).get('artifact',{})
            url=artifact.get('url',item.get('url','https://libraries.minecraft.net/')+relative)
            jobs.append((PRISM/'libraries'/relative,url,artifact.get('sha1')))
    # Also fetch Fabric's libraries.
    # Fabric's loader dependencies are pinned by its official profile.
    profile=Path(__file__).resolve().parents[1]/'.tools/fabric/profile.json'
    if profile.exists():
        for item in json.loads(profile.read_text())['libraries']:
            group,name,version=item['name'].split(':');relative=group.replace('.','/')+'/'+name+'/'+version+'/'+name+'-'+version+'.jar'
            jobs.append((PRISM/'libraries'/relative,item['url']+relative,item.get('sha1')))
    # Download up to six files at a time.
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        for result in executor.map(fetch,jobs):
            if result:print('Downloaded',result)
    print('Client libraries verified.')
# Run repair when executed directly.
if __name__=='__main__':repair()
