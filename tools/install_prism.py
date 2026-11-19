#!/usr/bin/env python3
# ==============================================================================
# Program: install_prism.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Installs the Spain game into its own Prism Launcher instance (named Spain): writes
#          the instance config, adds Fabric, copies the mod and Fabric API jars, creates the
#          starter world once from the verified test world and refreshes the data pack in it.
#          Refuses to touch an instance it did not create.
# ==============================================================================

"""Install the verified starter world in a separate, managed Prism instance."""
from __future__ import annotations

# Fit in the repo: the last step of scripts/update.sh. It takes what the earlier steps built (dist/Spain
# data pack, dist/spain-flight-0.1.0.jar, .tools/fabric) and what verification/run_checks.py produced (a generated
# test world) and installs a ready-to-play game in a dedicated Prism Launcher instance. play-spain.sh then launches
# that instance. It never starts the game.
#
# Safety rules, all enforced in install():
#   * the Minecraft checks must have passed (results.json says passed) before anything is installed;
#   * an existing instance is only touched if it carries this tool's marker file (.spain-managed.json); an
#     unmanaged instance of the same name makes the script stop without changing it;
#   * an existing world is never replaced, only its data pack is refreshed, so player progress survives updates.
# Tested by verification/test_tools.py (the unmanaged-instance refusal).
#
# Needs: Prism Launcher's data folder (default ~/.local/share/PrismLauncher) containing a base instance named
# "26.3" with Minecraft 26.3 already set up, since its component list is copied.
# Limits: Linux paths; settings such as memory (384-1536 MB) target a small machine.
import argparse
import gzip
import json
import shutil
from pathlib import Path
from nbt import read, payload

# Repository root; tests replace it with a temporary folder (patch.object) to keep the real project untouched.
ROOT = Path(__file__).resolve().parents[1]


def copy_atomic(source: Path, destination: Path) -> None:
    """Copy `source` over `destination` so a reader never sees a half-written file.

    The copy goes to a temporary neighbour first and is then renamed into place; replace() is atomic on the same
    filesystem. This matters because the jar may be overwritten while a Prism launch is being prepared.
    """
    temporary=destination.with_suffix(destination.suffix+'.spain-update')
    shutil.copy2(source,temporary)
    temporary.replace(destination)


def prepare_level(path: Path) -> None:
    """Rewrite a copied test world's level.dat so it becomes a normal starter save.

    Changes: world name "Spain · Starforge", survival mode, spawn on the Earth launch pad (0, 97, 0 in the
    overworld, matching extend_pack.py), only vanilla features, and the Spain data pack enabled. The file is read
    with typed=True so every value keeps its exact NBT type and is written back unchanged except for these fields.
    """
    level = read(path.read_bytes(), typed=True)
    data = level['Data'][1]
    data['LevelName'] = (8, 'Spain · Starforge')

    # Game mode 0 = survival. Survival keeps hostile mobs and drowning, which the quest design assumes.
    data['GameType'] = (3, 0)  # Survival preserves underwater breath and hostile mobs.
    data['spawn'] = (10, {'pos': (11, [0,97,0]), 'pitch': (5,0.0), 'dimension': (8,'minecraft:overworld'), 'yaw': (5,90.0)})
    data['enabled_features'] = (9, (8, ['minecraft:vanilla']))

    # Enable the pack as "file/Spain" (how Minecraft names a data pack folder in a world's datapacks directory).
    data['DataPacks'][1]['Enabled'] = (9, (8, ['vanilla', 'file/Spain']))
    data['DataPacks'][1]['Disabled'] = (9, (8, []))

    # level.dat is gzip-compressed NBT with an unnamed root compound (the b'\x0a\x00\x00' prefix: type 10 and an empty name).
    path.write_bytes(gzip.compress(b'\x0a\x00\x00' + payload(10, level), mtime=0))


def install(prism: Path, name: str = 'Spain') -> Path:
    """Create or update the Prism instance `name` under `prism` and return its folder.

    Args:
        prism: Prism Launcher data folder.
        name: instance folder name; path separators and "." / ".." are rejected so the name cannot point outside instances/.

    Returns:
        The instance directory.

    Raises:
        ValueError: invalid name, checks not passed, or an unmanaged instance already exists.

    Side effects: writes mmc-pack.json, instance.cfg, patches/, mods/, the world (first install only),
    the data pack and options.txt (only if absent), and the marker file.
    """
    if not name or '/' in name or '\\' in name or name in {'.', '..'}:
        raise ValueError('Invalid instance name')

    # Gate: only install a build that passed the in-game checks.
    result_file = ROOT / 'verification/output/results.json'
    if not result_file.exists() or not json.loads(result_file.read_text()).get('passed'):
        raise ValueError('Run the Minecraft checks successfully before preparing a starter world')
    target = prism / 'instances' / name

    # Ownership marker. Its absence on an existing folder means the instance was made by the user or another tool.
    marker = target / '.spain-managed.json'
    if target.exists() and not marker.exists():
        raise ValueError(f'Refusing to overwrite an existing unmanaged instance: {target}')
    target.mkdir(parents=True, exist_ok=True)

    # Reuse the component list (Minecraft, LWJGL, Java ...) of the user's own "26.3" instance, then add the Fabric loader as an extra component.
    base = prism / 'instances/26.3/mmc-pack.json'
    components=json.loads(base.read_text())
    components['components'].append({'uid':'net.fabricmc.fabric-loader','version':'0.19.5','cachedName':'Fabric Loader','cachedVersion':'0.19.5'})
    (target/'mmc-pack.json').write_text(json.dumps(components,indent=2)+'\n')

    # Prism normally downloads Fabric's metadata. A local patch file built from the profile saved by build_mod.dependencies() avoids that network step and pins the exact loader version.
    # A local component patch uses Fabric's official profile, avoiding a metadata-server dependency.
    profile=json.loads((ROOT/'.tools/fabric/profile.json').read_text())
    patches=target/'patches';patches.mkdir(exist_ok=True)
    (patches/'net.fabricmc.fabric-loader.json').write_text(json.dumps({'formatVersion':1,'uid':'net.fabricmc.fabric-loader','name':'Fabric Loader','version':'0.19.5','order':10,'mainClass':profile['mainClass'],'libraries':profile['libraries'],'requires':[{'uid':'net.minecraft','equals':'26.3'}]},indent=2)+'\n')

    # The instance overrides Prism's memory settings: start at 384 MB, at most 1536 MB, a modest footprint for a small machine. The bundled JDK is used if present, else Prism's default Java.
    java = ROOT / '.tools/jdk25/bin/java'
    config = f'[General]\nConfigVersion=1.3\nInstanceType=OneSix\nname={name}\niconKey=default\nOverrideMemory=true\nMinMemAlloc=384\nMaxMemAlloc=1536\n'
    if java.exists():
        config += f'OverrideJavaLocation=true\nJavaPath={java}\n'
    (target/'instance.cfg').write_text(config)
    game = target/'.minecraft'
    mods=game/'mods';mods.mkdir(parents=True,exist_ok=True)

    # The mod and Fabric API go into the instance's mods folder. The API jar is stored under a versioned name, as in a normal mods folder.
    copy_atomic(ROOT/'dist/spain-flight-0.1.0.jar',mods/'spain-flight-0.1.0.jar')
    copy_atomic(ROOT/'.tools/fabric/fabric-api.jar',mods/'fabric-api-0.161.0+26.3.jar')
    world = game/'saves/Spain'

    # First install only: copy the generated test world, leaving out lock files, player data and the mod's per-world save files, so the starter world is clean.
    if not world.exists():
        source = ROOT/'verification/output/universe/gametestworld'
        shutil.copytree(source, world, ignore=shutil.ignore_patterns('session.lock','players','playerdata','advancements','stats','SpainChecks','level.dat_old','spain-ships.json','spain-avatars.json'))
        prepare_level(world/'level.dat')

    # The data pack is replaced on every run (always the latest build); the save itself and its player data are not touched.
    # Updating the pack preserves the user's world and player data.
    destination = world/'datapacks/Spain'
    if destination.exists(): shutil.rmtree(destination)
    shutil.copytree(ROOT/'dist/Spain', destination)

    # Conservative first-run video settings (render distance 6, 45 fps cap), written only if the player has no options file yet. The conditional expression is used as a statement.
    (game/'options.txt').write_text('renderDistance:6\nsimulationDistance:4\nmaxFps:45\nguiScale:3\nautoJump:false\n') if not (game/'options.txt').exists() else None

    # Record that this instance is managed by this project, enabling later updates.
    marker.write_text(json.dumps({'project':'Spain','source':str(ROOT),'minecraft':'26.3'},indent=2)+'\n')
    print(f'Installed {target}\nPlay: ./play-spain.sh')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prism', type=Path, default=Path.home()/'.local/share/PrismLauncher')
    parser.add_argument('--name', default='Spain')
    args = parser.parse_args()
    install(args.prism, args.name)
