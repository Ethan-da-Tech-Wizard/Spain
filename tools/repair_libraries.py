#!/usr/bin/env python3
"""Fetch missing Linux client libraries using Prism's own version metadata and hashes."""
import concurrent.futures,hashlib,json,urllib.request
from pathlib import Path
PRISM=Path.home()/'.local/share/PrismLauncher'

def fetch(job):
    path,url,sha=job
    if path.exists() and (not sha or hashlib.sha1(path.read_bytes()).hexdigest()==sha):return None
    data=urllib.request.urlopen(url,timeout=45).read()
    if sha and hashlib.sha1(data).hexdigest()!=sha:raise ValueError('Checksum mismatch: '+str(path))
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);return path.name

def repair():
    jobs=[]
    for meta in ['org.lwjgl3/3.4.3.json','net.minecraft/26.3.json']:
        value=json.loads((PRISM/'meta'/meta).read_text())
        for item in value['libraries']:
            rules=item.get('rules')
            if rules and not any(r['action']=='allow' and r.get('os',{}).get('name','linux')=='linux' for r in rules):continue
            group,name,version,*classifier=item['name'].split(':')
            leaf=name+'-'+version+('-'+classifier[0] if classifier else '')+'.jar'
            relative=group.replace('.','/')+'/'+name+'/'+version+'/'+leaf
            artifact=item.get('downloads',{}).get('artifact',{})
            url=artifact.get('url',item.get('url','https://libraries.minecraft.net/')+relative)
            jobs.append((PRISM/'libraries'/relative,url,artifact.get('sha1')))
    # Fabric's loader dependencies are pinned by its official profile.
    profile=Path(__file__).resolve().parents[1]/'.tools/fabric/profile.json'
    if profile.exists():
        for item in json.loads(profile.read_text())['libraries']:
            group,name,version=item['name'].split(':');relative=group.replace('.','/')+'/'+name+'/'+version+'/'+name+'-'+version+'.jar'
            jobs.append((PRISM/'libraries'/relative,item['url']+relative,item.get('sha1')))
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        for result in executor.map(fetch,jobs):
            if result:print('Downloaded',result)
    print('Client libraries verified.')
if __name__=='__main__':repair()
