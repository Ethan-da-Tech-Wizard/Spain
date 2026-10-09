#!/usr/bin/env python3
"""Compile the small, unmapped Minecraft 26.3 Fabric module against local game libraries."""
import os, subprocess, zipfile, urllib.request, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LIBRARIES=Path(os.environ.get('SPAIN_MC_LIBRARIES',str(Path.home()/'.local/share/PrismLauncher/libraries')))
JAVA=Path(os.environ.get('SPAIN_JAVA_HOME',str(ROOT/'.tools/jdk25')))
FABRIC=ROOT/'.tools/fabric'

def dependencies():
    FABRIC.mkdir(parents=True,exist_ok=True)
    for filename,url in [('fabric-api.jar','https://maven.fabricmc.net/net/fabricmc/fabric-api/fabric-api/0.161.0+26.3/fabric-api-0.161.0+26.3.jar'),('fabric-loader.jar','https://maven.fabricmc.net/net/fabricmc/fabric-loader/0.19.5/fabric-loader-0.19.5.jar')]:
        path=FABRIC/filename
        if not path.exists():
            data=urllib.request.urlopen(url).read();expected=urllib.request.urlopen(url+'.sha1').read().decode().strip()
            if hashlib.sha1(data).hexdigest()!=expected:raise ValueError('Fabric checksum mismatch')
            path.write_bytes(data)
    profile=FABRIC/'profile.json'
    if not profile.exists():profile.write_bytes(urllib.request.urlopen('https://meta.fabricmc.net/v2/versions/loader/26.3/0.19.5/profile/json').read())
    with zipfile.ZipFile(FABRIC/'fabric-api.jar') as jar:
        for name in jar.namelist():
            if name.startswith('META-INF/jars/') and name.endswith('.jar'):(FABRIC/Path(name).name).write_bytes(jar.read(name))

def compile_mod():
    dependencies()
    classes=ROOT/'dist/mod-classes'
    import shutil
    if classes.exists():shutil.rmtree(classes)
    classes.mkdir(parents=True,exist_ok=True)
    for source in (ROOT/'local-assets/spore').glob('*.voxels.json'):
        resource=classes/'assets/spain';resource.mkdir(parents=True,exist_ok=True);shutil.copy2(source,resource/source.name)
    classpath=os.pathsep.join(str(p) for folder in [LIBRARIES,FABRIC] for p in sorted(folder.rglob('*.jar')))
    sources=sorted((ROOT/'mod/src/main/java').rglob('*.java'))
    subprocess.run([str(JAVA/'bin/javac'),'-J-Xmx384m','-J-XX:ActiveProcessorCount=2','-proc:none','-cp',classpath,'-d',str(classes),*map(str,sources)],check=True)
    target=ROOT/'dist/spain-flight-0.1.0.jar'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as jar:
        for base in [classes,ROOT/'mod/src/main/resources']:
            for p in sorted(base.rglob('*')):
                if p.is_file():jar.write(p,p.relative_to(base))
    print(target)
    return classes,classpath
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--dependencies-only',action='store_true')
    if parser.parse_args().dependencies_only:dependencies()
    else:compile_mod()
