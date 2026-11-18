#!/usr/bin/env python3
# Program: Spain - run_checks.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Builds the pack and mod, then runs the MinecraftChecks test on a real Minecraft GameTest server and inspects the saved world.
"""Compile a small probe against the user's Minecraft and run Mojang's GameTest server."""
# Imports for JSON, environment variables, paths, running programs and the system path.
import json
import os
from pathlib import Path
import subprocess
import sys

# ROOT = project folder; also make the tools folder importable.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
# Reuse the pack builder and JSON writer from the tools folder.
from build_pack import build, write_json


def main():
    """Prepare everything, run the Minecraft checks and verify the saved results."""
    # Find Minecraft libraries and Java (overridable by environment variables).
    libraries = Path(os.environ.get('SPAIN_MC_LIBRARIES', str(Path.home()/'.local/share/PrismLauncher/libraries')))
    java_home = Path(os.environ.get('SPAIN_JAVA_HOME', str(ROOT/'.tools/jdk25')))
    # Stop with a clear message if Minecraft has never been launched in Prism.
    jars = sorted(libraries.rglob('*.jar'))
    if not jars: raise SystemExit('Minecraft libraries are missing. Launch Minecraft 26.3 in Prism first.')
    # Output folders; remove the old result so a stale pass cannot be mistaken for a new one.
    output = ROOT/'verification/output'
    classes = output/'classes'
    classes.mkdir(parents=True, exist_ok=True)
    (output/'results.json').unlink(missing_ok=True)
    # Compile the mod and build the data pack.
    from build_mod import compile_mod
    mod_classes, dependencies = compile_mod()
    classpath = str(mod_classes) + os.pathsep + dependencies
    build(libraries/'com/mojang/minecraft/26.3/minecraft-26.3-client.jar')
    # Prepare the pack folders for the server.
    # --packs copies only unpacked folders. Keep the test definitions separate from the game pack.
    packs = output/'packs'
    packs.mkdir(parents=True, exist_ok=True)
    import shutil
    # Delete the previous generated test world (never a real save) and copy in the pack.
    universe = output/'universe'
    if universe.exists(): shutil.rmtree(universe)  # Generated checks only; never a player save.
    shutil.copytree(ROOT/'dist/Spain', packs/'Spain', dirs_exist_ok=True)
    # Write the extra test pack: its info file and the test definition for spain:core.
    write_json(packs/'SpainChecks/pack.mcmeta', {'pack': {'description':'Spain runtime checks', 'min_format':[121,0], 'max_format':[121,0]}})
    write_json(packs/'SpainChecks/data/spain/test_instance/core.json', {'type':'minecraft:function','environment':'minecraft:default','function':'spain:core','max_ticks':300,'setup_ticks':5,'required':True,'structure':'minecraft:empty'})
    # Read Minecraft's own world presets and add the Spain dimensions to the flat all-dimensions preset used by the test.
    import zipfile
    with zipfile.ZipFile(libraries/'com/mojang/minecraft/26.3/minecraft-26.3-client.jar') as archive:
        preset = json.loads(archive.read('data/minecraft/worldgen/world_preset/flat_all_dimensions.json'))
        normal = json.loads(archive.read('data/minecraft/worldgen/world_preset/normal.json'))
    preset['dimensions']['minecraft:overworld'] = normal['dimensions']['minecraft:overworld']
    for path in (ROOT/'dist/Spain/data/spain/dimension').glob('*.json'):
        preset['dimensions']['spain:'+path.stem] = json.loads(path.read_text())
    write_json(packs/'SpainChecks/data/minecraft/worldgen/world_preset/flat_all_dimensions.json', preset)
    # Compile the check program.
    compile_result = subprocess.run([str(java_home/'bin/javac'), '-J-Xmx384m', '-J-XX:ActiveProcessorCount=2', '-cp', classpath, '-d', str(classes), str(ROOT/'verification/MinecraftChecks.java')])
    if compile_result.returncode: raise SystemExit(compile_result.returncode)
    # Tell the test whether local imported assets exist.
    imported = (ROOT/'local-assets/structures/crate.nbt').exists()
    # Java command that starts the test with limited memory.
    command = [str(java_home/'bin/java'), '-Xmx768m', '-XX:ActiveProcessorCount=2', '--enable-native-access=ALL-UNNAMED', '-Djava.awt.headless=true', '-Dspain.imported='+str(imported).lower(), '-Dspain.report='+str(output/'results.json'), '-cp', str(classes)+os.pathsep+classpath, 'MinecraftChecks', '--universe', str(output/'universe'), '--packs', str(packs), '--tests', 'spain:core', '--report', str(output/'gametest.xml')]
    # Run it with a 180 second limit, saving the log, and show the end of the log.
    with (output/'minecraft.log').open('w') as log:
        result = subprocess.run(command, cwd=output, stdout=log, stderr=subprocess.STDOUT, timeout=180)
    print((output/'minecraft.log').read_text()[-7000:])
    if result.returncode: raise SystemExit(result.returncode)
    # Read the scoreboard file the game wrote and confirm the quest completion was saved.
    # Inspect the save Minecraft wrote, rather than relying only on in-memory values.
    from nbt import read
    scoreboard = read((output/'universe/gametestworld/data/minecraft/scoreboard.dat').read_bytes())
    scores = scoreboard['data']['PlayerScores']
    if not any(s['Objective'] == 'spain.quest' and s['Score'] == 2 for s in scores):
        raise SystemExit('Completed quest was not persisted in the Minecraft save')
    print((output/'results.json').read_text())


# Run main when executed directly.
if __name__ == '__main__': main()
