#!/usr/bin/env python3
# ==============================================================================
# Program: run_checks.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Builds the mod and data pack, runs Mojang's headless GameTest server against them
#          with the MinecraftChecks.java probe, and verifies the saved world. Writes the report
#          verification/output/results.json that install_prism.py requires.
# ==============================================================================

"""Compile a small probe against the user's Minecraft and run Mojang's GameTest server."""

# Fit in the repo: the in-game test runner. scripts/update.sh runs it (and refuses to install the game if it
# fails), tools/install_prism.py checks that its report says "passed", and the world it generates becomes the
# starter world. It proves the pack and mod work in the real game, not just that the Python builds files.
#
# What it does, in order:
#   1. build the mod (build_mod.compile_mod) and the data pack (build_pack.build) from the current sources;
#   2. assemble a temporary test layout under verification/output: the Spain pack, plus a small "SpainChecks"
#      pack that registers one GameTest (spain:core);
#   3. compile verification/MinecraftChecks.java, a tiny launcher that starts Mojang's headless game-test
#      server with those packs and runs the checks (it calls into the mod classes and inspects the world);
#   4. start that server (180 s time limit), print the log, and fail on a non-zero exit;
#   5. read the world the game just saved and confirm that the quest score persisted (completed quest = 2).
# Inputs : Prism's Minecraft libraries (env SPAIN_MC_LIBRARIES), JDK 25 (env SPAIN_JAVA_HOME). Run it
#          after the Minecraft client has been launched once so its libraries exist.
# Outputs: verification/output/{results.json, minecraft.log, universe/, classes/, packs/} (all generated).
# Run    : python3 verification/run_checks.py
# Limits : Linux layout; needs about 768 MB for the test JVM; the 180 s timeout kills a hung server (raises subprocess.TimeoutExpired).
import json
import os
from pathlib import Path
import subprocess
import sys

# Repository root.
ROOT = Path(__file__).resolve().parents[1]

# tools/ holds scripts, not a package: put it on the import path so build_pack, build_mod and nbt can be imported.
sys.path.insert(0, str(ROOT / 'tools'))
from build_pack import build, write_json


def main():
    """Run the whole verification procedure described at the top of the file; exits non-zero on any failure."""
    libraries = Path(os.environ.get('SPAIN_MC_LIBRARIES', str(Path.home()/'.local/share/PrismLauncher/libraries')))
    java_home = Path(os.environ.get('SPAIN_JAVA_HOME', str(ROOT/'.tools/jdk25')))

    # Fail early with advice if Minecraft was never launched (its libraries would not exist yet).
    jars = sorted(libraries.rglob('*.jar'))
    if not jars: raise SystemExit('Minecraft libraries are missing. Launch Minecraft 26.3 in Prism first.')
    output = ROOT/'verification/output'
    classes = output/'classes'
    classes.mkdir(parents=True, exist_ok=True)

    # Delete the old report: a stale "passed" must never be mistaken for the result of this run.
    (output/'results.json').unlink(missing_ok=True)
    from build_mod import compile_mod
    mod_classes, dependencies = compile_mod()

    # Mod classes first, then the dependency classpath returned by compile_mod().
    classpath = str(mod_classes) + os.pathsep + dependencies

    # Build the data pack from the same Minecraft version jar the tests will run against.
    build(libraries/'com/mojang/minecraft/26.3/minecraft-26.3-client.jar')
    # --packs copies only unpacked folders. Keep the test definitions separate from the game pack.
    packs = output/'packs'

    # --packs on the game-test server only picks up unpacked folders, so the pack under test and the test-definition pack are separate folders here.
    packs.mkdir(parents=True, exist_ok=True)
    import shutil

    # The generated world folder. Deleted at each run so every test starts from a fresh world; it is a test world, never a player save.
    universe = output/'universe'
    if universe.exists(): shutil.rmtree(universe)  # Generated checks only; never a player save.
    shutil.copytree(ROOT/'dist/Spain', packs/'Spain', dirs_exist_ok=True)

    # Test pack: one GameTest instance running spain:core (a function in the pack) with a 300-tick limit after 5 setup ticks; `required` makes a failure fail the whole run.
    write_json(packs/'SpainChecks/pack.mcmeta', {'pack': {'description':'Spain runtime checks', 'min_format':[121,0], 'max_format':[121,0]}})
    write_json(packs/'SpainChecks/data/spain/test_instance/core.json', {'type':'minecraft:function','environment':'minecraft:default','function':'spain:core','max_ticks':300,'setup_ticks':5,'required':True,'structure':'minecraft:empty'})
    import zipfile

    # Build a world preset that contains the vanilla overworld plus every Spain dimension, so the test world has the same dimensions as a real Spain world. Vanilla's "flat_all_dimensions" preset is overwritten with that mix for this test pack only.
    with zipfile.ZipFile(libraries/'com/mojang/minecraft/26.3/minecraft-26.3-client.jar') as archive:
        preset = json.loads(archive.read('data/minecraft/worldgen/world_preset/flat_all_dimensions.json'))
        normal = json.loads(archive.read('data/minecraft/worldgen/world_preset/normal.json'))
    preset['dimensions']['minecraft:overworld'] = normal['dimensions']['minecraft:overworld']
    for path in (ROOT/'dist/Spain/data/spain/dimension').glob('*.json'):
        preset['dimensions']['spain:'+path.stem] = json.loads(path.read_text())
    write_json(packs/'SpainChecks/data/minecraft/worldgen/world_preset/flat_all_dimensions.json', preset)

    # Compile the Java test launcher with the same small-memory settings as the mod build.
    compile_result = subprocess.run([str(java_home/'bin/javac'), '-J-Xmx384m', '-J-XX:ActiveProcessorCount=2', '-cp', classpath, '-d', str(classes), str(ROOT/'verification/MinecraftChecks.java')])
    if compile_result.returncode: raise SystemExit(compile_result.returncode)

    # Tell the test whether local imported art exists, so it only expects imported structures when they were built.
    imported = (ROOT/'local-assets/structures/crate.nbt').exists()

    # -Xmx768m and two CPUs keep the test server light. --enable-native-access allows the game's native libraries
    # on JDK 25; headless=true because there is no display. The two -D properties pass the report location and the imported-art flag to MinecraftChecks.
    command = [str(java_home/'bin/java'), '-Xmx768m', '-XX:ActiveProcessorCount=2', '--enable-native-access=ALL-UNNAMED', '-Djava.awt.headless=true', '-Dspain.imported='+str(imported).lower(), '-Dspain.report='+str(output/'results.json'), '-cp', str(classes)+os.pathsep+classpath, 'MinecraftChecks', '--universe', str(output/'universe'), '--packs', str(packs), '--tests', 'spain:core', '--report', str(output/'gametest.xml')]

    # Server output goes to a log file; the last 7000 characters are printed below so failures are visible
    # without flooding the terminal. timeout=180 stops a deadlocked test from hanging forever.
    with (output/'minecraft.log').open('w') as log:
        result = subprocess.run(command, cwd=output, stdout=log, stderr=subprocess.STDOUT, timeout=180)
    print((output/'minecraft.log').read_text()[-7000:])
    if result.returncode: raise SystemExit(result.returncode)

    # Independent check: read the on-disk world (scoreboard.dat), not just values from memory. Proves the quest state is really persisted when the world is saved.
    # Inspect the save Minecraft wrote, rather than relying only on in-memory values.
    from nbt import read
    scoreboard = read((output/'universe/gametestworld/data/minecraft/scoreboard.dat').read_bytes())
    scores = scoreboard['data']['PlayerScores']
    if not any(s['Objective'] == 'spain.quest' and s['Score'] == 2 for s in scores):
        raise SystemExit('Completed quest was not persisted in the Minecraft save')
    print((output/'results.json').read_text())


# Entry point.
if __name__ == '__main__': main()
