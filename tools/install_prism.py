#!/usr/bin/env python3
# Program: Spain - install_prism.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Installs the checked Spain data pack, mod jar and starter world into a separate managed Prism Launcher instance.
"""Install the verified starter world in a separate, managed Prism instance."""
# Lets type hints use the newer style.
from __future__ import annotations

# Imports for options, gzip, JSON, file copying and paths; nbt reads and writes Minecraft save data.
import argparse
import gzip
import json
import shutil
from pathlib import Path
from nbt import read, payload

# ROOT = project folder.
ROOT = Path(__file__).resolve().parents[1]


def copy_atomic(source: Path, destination: Path) -> None:
    """Copy a file in a way that never leaves a partial file at the destination."""
    # Copy to a temporary name first, then rename, so a half-copied file never replaces the real one.
    temporary=destination.with_suffix(destination.suffix+'.spain-update')
    shutil.copy2(source,temporary)
    temporary.replace(destination)


def prepare_level(path: Path) -> None:
    """Edit a world's level.dat for the Spain starter world."""
    # Read level.dat and edit the world settings: name, game mode (survival), spawn point, enabled features and data packs.
    level = read(path.read_bytes(), typed=True)
    data = level['Data'][1]
    data['LevelName'] = (8, 'Spain · Starforge')
    data['GameType'] = (3, 0)  # Survival preserves underwater breath and hostile mobs.
    data['spawn'] = (10, {'pos': (11, [0,97,0]), 'pitch': (5,0.0), 'dimension': (8,'minecraft:overworld'), 'yaw': (5,90.0)})
    data['enabled_features'] = (9, (8, ['minecraft:vanilla']))
    data['DataPacks'][1]['Enabled'] = (9, (8, ['vanilla', 'file/Spain']))
    data['DataPacks'][1]['Disabled'] = (9, (8, []))
    # Write the changed level.dat back, compressed.
    path.write_bytes(gzip.compress(b'\x0a\x00\x00' + payload(10, level), mtime=0))


def install(prism: Path, name: str = 'Spain') -> Path:
    """Create or update the Spain Prism instance and return its folder."""
    # Reject names that could point outside the instances folder.
    if not name or '/' in name or '\\' in name or name in {'.', '..'}:
        raise ValueError('Invalid instance name')
    # Only install if the Minecraft checks passed.
    result_file = ROOT / 'verification/output/results.json'
    if not result_file.exists() or not json.loads(result_file.read_text()).get('passed'):
        raise ValueError('Run the Minecraft checks successfully before preparing a starter world')
    # Never overwrite an instance that this project did not create (it has no marker file).
    target = prism / 'instances' / name
    marker = target / '.spain-managed.json'
    if target.exists() and not marker.exists():
        raise ValueError(f'Refusing to overwrite an existing unmanaged instance: {target}')
    target.mkdir(parents=True, exist_ok=True)
    # Copy the base 26.3 component list and add Fabric Loader.
    base = prism / 'instances/26.3/mmc-pack.json'
    components=json.loads(base.read_text())
    components['components'].append({'uid':'net.fabricmc.fabric-loader','version':'0.19.5','cachedName':'Fabric Loader','cachedVersion':'0.19.5'})
    (target/'mmc-pack.json').write_text(json.dumps(components,indent=2)+'\n')
    # Write the Fabric patch file.
    # A local component patch uses Fabric's official profile, avoiding a metadata-server dependency.
    profile=json.loads((ROOT/'.tools/fabric/profile.json').read_text())
    patches=target/'patches';patches.mkdir(exist_ok=True)
    (patches/'net.fabricmc.fabric-loader.json').write_text(json.dumps({'formatVersion':1,'uid':'net.fabricmc.fabric-loader','name':'Fabric Loader','version':'0.19.5','order':10,'mainClass':profile['mainClass'],'libraries':profile['libraries'],'requires':[{'uid':'net.minecraft','equals':'26.3'}]},indent=2)+'\n')
    # Instance settings: memory limits and, if present, the local Java.
    java = ROOT / '.tools/jdk25/bin/java'
    config = f'[General]\nConfigVersion=1.3\nInstanceType=OneSix\nname={name}\niconKey=default\nOverrideMemory=true\nMinMemAlloc=384\nMaxMemAlloc=1536\n'
    if java.exists():
        config += f'OverrideJavaLocation=true\nJavaPath={java}\n'
    (target/'instance.cfg').write_text(config)
    # Install the mod and Fabric API jars into the mods folder.
    game = target/'.minecraft'
    mods=game/'mods';mods.mkdir(parents=True,exist_ok=True)
    copy_atomic(ROOT/'dist/spain-flight-0.1.0.jar',mods/'spain-flight-0.1.0.jar')
    copy_atomic(ROOT/'.tools/fabric/fabric-api.jar',mods/'fabric-api-0.161.0+26.3.jar')
    # Create the world once from the checked test world, leaving out player data and locks.
    world = game/'saves/Spain'
    if not world.exists():
        source = ROOT/'verification/output/universe/gametestworld'
        shutil.copytree(source, world, ignore=shutil.ignore_patterns('session.lock','players','playerdata','advancements','stats','SpainChecks','level.dat_old','spain-ships.json','spain-avatars.json'))
        prepare_level(world/'level.dat')
    # Replace only the data pack.
    # Updating the pack preserves the user's world and player data.
    destination = world/'datapacks/Spain'
    if destination.exists(): shutil.rmtree(destination)
    shutil.copytree(ROOT/'dist/Spain', destination)
    # Write default game options only if the player has none.
    (game/'options.txt').write_text('renderDistance:6\nsimulationDistance:4\nmaxFps:45\nguiScale:3\nautoJump:false\n') if not (game/'options.txt').exists() else None
    # Write the marker file so later runs know this instance is ours.
    marker.write_text(json.dumps({'project':'Spain','source':str(ROOT),'minecraft':'26.3'},indent=2)+'\n')
    print(f'Installed {target}\nPlay: ./play-spain.sh')
    return target


# Command line: --prism (Prism folder) and --name (instance name).
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prism', type=Path, default=Path.home()/'.local/share/PrismLauncher')
    parser.add_argument('--name', default='Spain')
    args = parser.parse_args()
    install(args.prism, args.name)
