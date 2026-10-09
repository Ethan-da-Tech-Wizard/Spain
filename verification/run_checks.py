#!/usr/bin/env python3
"""Compile a small probe against the user's Minecraft and run Mojang's GameTest server."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from build_pack import build, write_json


def main():
    libraries = Path(os.environ.get('SPAIN_MC_LIBRARIES', str(Path.home()/'.local/share/PrismLauncher/libraries')))
    java_home = Path(os.environ.get('SPAIN_JAVA_HOME', str(ROOT/'.tools/jdk25')))
    jars = sorted(libraries.rglob('*.jar'))
    if not jars: raise SystemExit('Minecraft libraries are missing. Launch Minecraft 26.3 in Prism first.')
    output = ROOT/'verification/output'
    classes = output/'classes'
    classes.mkdir(parents=True, exist_ok=True)
    (output/'results.json').unlink(missing_ok=True)
    from build_mod import compile_mod
    mod_classes, dependencies = compile_mod()
    classpath = str(mod_classes) + os.pathsep + dependencies
    build(libraries/'com/mojang/minecraft/26.3/minecraft-26.3-client.jar')
    # --packs copies only unpacked folders. Keep the test definitions separate from the game pack.
    packs = output/'packs'
    packs.mkdir(parents=True, exist_ok=True)
    import shutil
    universe = output/'universe'
    if universe.exists(): shutil.rmtree(universe)  # Generated checks only; never a player save.
    shutil.copytree(ROOT/'dist/Spain', packs/'Spain', dirs_exist_ok=True)
    write_json(packs/'SpainChecks/pack.mcmeta', {'pack': {'description':'Spain runtime checks', 'min_format':[121,0], 'max_format':[121,0]}})
    write_json(packs/'SpainChecks/data/spain/test_instance/core.json', {'type':'minecraft:function','environment':'minecraft:default','function':'spain:core','max_ticks':300,'setup_ticks':5,'required':True,'structure':'minecraft:empty'})
    import zipfile
    with zipfile.ZipFile(libraries/'com/mojang/minecraft/26.3/minecraft-26.3-client.jar') as archive:
        preset = json.loads(archive.read('data/minecraft/worldgen/world_preset/flat_all_dimensions.json'))
        normal = json.loads(archive.read('data/minecraft/worldgen/world_preset/normal.json'))
    preset['dimensions']['minecraft:overworld'] = normal['dimensions']['minecraft:overworld']
    for path in (ROOT/'dist/Spain/data/spain/dimension').glob('*.json'):
        preset['dimensions']['spain:'+path.stem] = json.loads(path.read_text())
    write_json(packs/'SpainChecks/data/minecraft/worldgen/world_preset/flat_all_dimensions.json', preset)
    compile_result = subprocess.run([str(java_home/'bin/javac'), '-J-Xmx384m', '-J-XX:ActiveProcessorCount=2', '-cp', classpath, '-d', str(classes), str(ROOT/'verification/MinecraftChecks.java')])
    if compile_result.returncode: raise SystemExit(compile_result.returncode)
    imported = (ROOT/'local-assets/structures/crate.nbt').exists()
    command = [str(java_home/'bin/java'), '-Xmx768m', '-XX:ActiveProcessorCount=2', '--enable-native-access=ALL-UNNAMED', '-Djava.awt.headless=true', '-Dspain.imported='+str(imported).lower(), '-Dspain.report='+str(output/'results.json'), '-cp', str(classes)+os.pathsep+classpath, 'MinecraftChecks', '--universe', str(output/'universe'), '--packs', str(packs), '--tests', 'spain:core', '--report', str(output/'gametest.xml')]
    with (output/'minecraft.log').open('w') as log:
        result = subprocess.run(command, cwd=output, stdout=log, stderr=subprocess.STDOUT, timeout=180)
    print((output/'minecraft.log').read_text()[-7000:])
    if result.returncode: raise SystemExit(result.returncode)
    # Inspect the save Minecraft wrote, rather than relying only on in-memory values.
    from nbt import read
    scoreboard = read((output/'universe/gametestworld/data/minecraft/scoreboard.dat').read_bytes())
    scores = scoreboard['data']['PlayerScores']
    if not any(s['Objective'] == 'spain.quest' and s['Score'] == 2 for s in scores):
        raise SystemExit('Completed quest was not persisted in the Minecraft save')
    print((output/'results.json').read_text())


if __name__ == '__main__': main()
