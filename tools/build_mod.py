#!/usr/bin/env python3
# ==============================================================================
# Program: build_mod.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Downloads (once, checksum-verified) the pinned Fabric loader and API jars, compiles
#          the small Java mod in mod/src/main/java against the local Minecraft libraries with
#          the bundled JDK 25, and zips the classes into dist/spain-flight-0.1.0.jar.
# ==============================================================================

"""Compile the small, unmapped Minecraft 26.3 Fabric module against local game libraries."""

# Fit in the repo: second stage of scripts/build.sh and the first of scripts/update.sh (`--dependencies-only`).
# It turns the Java source in mod/src/main/java into dist/spain-flight-0.1.0.jar, the Fabric mod that
# the game loads together with the data pack. verification/run_checks.py imports compile_mod() and uses the returned
# classpath to run the in-game tests, and tools/install_prism.py copies the finished jar into the game instance.
#
# No Gradle or Maven is used: the code is compiled with plain `javac`, so the only inputs are the Minecraft
# libraries already installed by Prism Launcher and two Fabric jars downloaded once into .tools/fabric.
# The mod is built "unmapped": it uses the game's own class and method names directly, so no mapping tool is needed.
#
# Environment: SPAIN_MC_LIBRARIES (folder of Minecraft library jars, default Prism's) and SPAIN_JAVA_HOME
# (a JDK 25, default .tools/jdk25 from scripts/setup.sh).
# Network: dependencies() downloads from maven.fabricmc.net and meta.fabricmc.net on first use only.
# Limits: the jar is not byte-for-byte reproducible (zip timestamps); the .sha1 check proves the download
# matches what the same server published, so it detects corruption but not a compromised server;
# profile.json (the Fabric launch profile) has no checksum.
import os, subprocess, zipfile, urllib.request, hashlib
from pathlib import Path

# Repository root. All outputs go to ROOT/dist and ROOT/.tools, both build artefacts that are not committed.
ROOT=Path(__file__).resolve().parents[1]

# Minecraft's libraries (client jar, LWJGL, Mojang libs ...). Everything in this folder goes on the compile classpath.
LIBRARIES=Path(os.environ.get('SPAIN_MC_LIBRARIES',str(Path.home()/'.local/share/PrismLauncher/libraries')))

# JDK used for compiling. 25 is what Minecraft 26.3 requires (class files for older JDKs would not load).
JAVA=Path(os.environ.get('SPAIN_JAVA_HOME',str(ROOT/'.tools/jdk25')))

# Where the Fabric loader, Fabric API and its nested module jars are cached.
FABRIC=ROOT/'.tools/fabric'

def dependencies():
    """Download and unpack the pinned Fabric dependencies into .tools/fabric (skips what already exists).

    Fetches fabric-api.jar (0.161.0+26.3) and fabric-loader.jar (0.19.5), checking each against the SHA-1
    published next to it, and the loader's launch profile.json (used by install_prism.py). Fabric API is a
    bundle: its META-INF/jars folder holds the real module jars, which are extracted beside it so the compiler
    can see their classes.

    Raises:
        ValueError: if a downloaded jar does not match its published SHA-1.
        urllib.error.URLError: if the network is unavailable and the files are not cached yet.
    """
    FABRIC.mkdir(parents=True,exist_ok=True)
    for filename,url in [('fabric-api.jar','https://maven.fabricmc.net/net/fabricmc/fabric-api/fabric-api/0.161.0+26.3/fabric-api-0.161.0+26.3.jar'),('fabric-loader.jar','https://maven.fabricmc.net/net/fabricmc/fabric-loader/0.19.5/fabric-loader-0.19.5.jar')]:
        path=FABRIC/filename

        # Download only when missing so repeated builds work offline.
        if not path.exists():
            data=urllib.request.urlopen(url).read();expected=urllib.request.urlopen(url+'.sha1').read().decode().strip()

            # Refuse to write a file whose hash is wrong, so a truncated or tampered download never lands in the cache.
            if hashlib.sha1(data).hexdigest()!=expected:raise ValueError('Fabric checksum mismatch')
            path.write_bytes(data)
    profile=FABRIC/'profile.json'
    if not profile.exists():profile.write_bytes(urllib.request.urlopen('https://meta.fabricmc.net/v2/versions/loader/26.3/0.19.5/profile/json').read())
    with zipfile.ZipFile(FABRIC/'fabric-api.jar') as jar:
        for name in jar.namelist():
            # Nested module jars; Path(name).name drops the folder so they all land directly in .tools/fabric.
            if name.startswith('META-INF/jars/') and name.endswith('.jar'):(FABRIC/Path(name).name).write_bytes(jar.read(name))

def compile_mod():
    """Compile the mod and package it; return (classes_dir, classpath_string).

    Steps: ensure dependencies exist, wipe dist/mod-classes, copy local Spore voxel files into the class
    folder as game assets, run javac, then zip classes plus mod/src/main/resources (fabric.mod.json and the
    mixin config) into dist/spain-flight-0.1.0.jar.

    Returns:
        The classes folder and the classpath string, so verification/run_checks.py can compile and run its
        tests against the same build.

    Raises:
        subprocess.CalledProcessError: if javac reports an error (check=True makes the build fail loudly).
    """
    dependencies()
    classes=ROOT/'dist/mod-classes'
    import shutil

    # Clean build: stale .class files from deleted sources must not end up in the jar.
    if classes.exists():shutil.rmtree(classes)
    classes.mkdir(parents=True,exist_ok=True)

    # Optional local Spore meshes (see import_spore.py) are shipped inside the jar as assets/spain/*.voxels.json for SporeVisuals.java to load. Absent in a fresh clone.
    for source in (ROOT/'local-assets/spore').glob('*.voxels.json'):
        resource=classes/'assets/spain';resource.mkdir(parents=True,exist_ok=True);shutil.copy2(source,resource/source.name)

    # Every library jar plus the Fabric jars, sorted so the compile is deterministic. os.pathsep is ':' or ';' by platform.
    classpath=os.pathsep.join(str(p) for folder in [LIBRARIES,FABRIC] for p in sorted(folder.rglob('*.jar')))
    sources=sorted((ROOT/'mod/src/main/java').rglob('*.java'))

    # -J flags configure the compiler JVM itself: 384 MB heap and 2 CPUs keep the build small on a modest laptop.
    # -proc:none disables annotation processors (not needed, and faster). Output goes to dist/mod-classes.
    subprocess.run([str(JAVA/'bin/javac'),'-J-Xmx384m','-J-XX:ActiveProcessorCount=2','-proc:none','-cp',classpath,'-d',str(classes),*map(str,sources)],check=True)

    # The jar name and version are also used by install_prism.py, so change them in both places.
    target=ROOT/'dist/spain-flight-0.1.0.jar'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as jar:
        for base in [classes,ROOT/'mod/src/main/resources']:
            for p in sorted(base.rglob('*')):
                if p.is_file():jar.write(p,p.relative_to(base))
    print(target)
    return classes,classpath

# `--dependencies-only` is used by scripts/update.sh to prefetch Fabric without compiling.
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--dependencies-only',action='store_true')
    if parser.parse_args().dependencies_only:dependencies()
    else:compile_mod()
