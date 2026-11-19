#!/usr/bin/env python3
# ==============================================================================
# Program: asset_status.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Reports whether the Steam games used as optional art sources (Spore and two
#          others, by app id) are fully installed, and whether the locally generated asset
#          files exist. Writes verification/output/asset-status.json.
# ==============================================================================

"""Read Steam download manifests and check the local Minecraft/Spore build inputs."""

# Fit in the repo: a quick status report used by scripts/update.sh. It answers "are the optional art sources
# ready?" for the local, ignored art pipeline (tools/import_spore.py, tools/import_assets.py). Missing art is not
# an error: the pack builds without it. Writes verification/output/asset-status.json and prints one line per item.
#
# How it reads Steam: each installed Steam game has an appmanifest_<id>.acf text file of "key" "value" pairs;
# StateFlags 4 means fully installed. Progress is BytesDownloaded / BytesToDownload.
# Limits: Linux Steam path (~/.local/share/Steam); the app ids (17390, 17440, 24720) are fixed.
import json,re
from pathlib import Path

# Repository root, used to look for the locally generated files.
ROOT=Path(__file__).resolve().parents[1]

def status(steam:Path=Path.home()/'.local/share/Steam/steamapps'):
    """Return {'games': [...], 'resources': {...}} describing Steam installs and local generated assets.

    Args:
        steam: Steam's steamapps folder (parameter so it can be changed for testing).

    games: one dict per app id with name, installed flag, bytes downloaded/total, progress (0..1), the number of
    .package archives found and the install location. A game with no manifest is reported as not installed.
    resources: name -> bool for the extractor, the converted Spore structures and the local Spore voxel files.
    """
    games=[]
    for app in ['17390','17440','24720']:
        manifest=steam/f'appmanifest_{app}.acf'
        if not manifest.exists():games.append({'app':app,'installed':False});continue

        # The .acf format is simple enough to read with a regular expression: lines of "key"  "value". Only the top-level fields are needed, so no full parser is used.
        fields=dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"',manifest.read_text()))
        location=steam/'common'/fields['installdir'];downloaded=int(fields.get('BytesDownloaded',0));total=int(fields.get('BytesToDownload',0))

        # StateFlags 4 = fully installed. A partially downloaded game has another value, so it counts as incomplete.
        games.append({'app':app,'name':fields['name'],'installed':fields.get('StateFlags')=='4' and location.exists(),'downloaded_bytes':downloaded,'total_bytes':total,'progress':1 if total==0 else downloaded/total,'packages':len(list(location.rglob('*.package'))),'location':str(location)})
    resources={name:(ROOT/path).exists() for name,path in {'Spore extractor':'.tools/sporemodder/SporeModder FX/SporeModderFX.jar','Spore UFO':'local-assets/structures/spore_rocket.nbt','Spore creature':'local-assets/spore/spore_creature.voxels.json','Spore rocket part':'local-assets/structures/spore_thruster.nbt','Melty crate':'local-assets/structures/crate.nbt','Melty pine':'local-assets/structures/pine.nbt','Java 25':'.tools/jdk25/bin/java','Fabric API':'.tools/fabric/fabric-api.jar'}.items()}
    return {'games':games,'resources':resources}

# Command-line use: save the machine-readable report, then print a short human summary.
if __name__=='__main__':
    result=status();output=ROOT/'verification/output/asset-status.json';output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n')
    for game in result['games']:print(game.get('name',game['app']),f'{game.get("progress",0):.0%}',f'{game.get("packages",0)} archives', 'installed' if game['installed'] else 'incomplete')
    for name,present in result['resources'].items():print(name, 'ready' if present else 'missing')
