#!/usr/bin/env python3
# Program: Spain - asset_status.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Checks Steam download manifests and local build inputs (Spore extractor, converted models, Java, Fabric) and writes a JSON status report.
"""Read Steam download manifests and check the local Minecraft/Spore build inputs."""
# Imports: json for the report, re for reading the manifest text.
import json,re
from pathlib import Path
# ROOT = the project folder (two levels above this file).
ROOT=Path(__file__).resolve().parents[1]

# Steam app ids to check: 17390, 17440 and 24720 (Spore-related Steam apps, as listed in the code).
def status(steam:Path=Path.home()/'.local/share/Steam/steamapps'):
    """Return a dictionary with each Steam game's install progress and whether each local resource file exists."""
    games=[]
    # Look for each app's Steam manifest file.
    for app in ['17390','17440','24720']:
        # Path of the manifest file for this app.
        manifest=steam/f'appmanifest_{app}.acf'
        # Not installed: record that and move on.
        if not manifest.exists():games.append({'app':app,'installed':False});continue
        # Read the quoted "key" "value" pairs from the manifest into a dictionary.
        fields=dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"',manifest.read_text()))
        # Work out the install folder, how many bytes are downloaded, and how many are needed, then record the game's state.
        location=steam/'common'/fields['installdir'];downloaded=int(fields.get('BytesDownloaded',0));total=int(fields.get('BytesToDownload',0))
        games.append({'app':app,'name':fields['name'],'installed':fields.get('StateFlags')=='4' and location.exists(),'downloaded_bytes':downloaded,'total_bytes':total,'progress':1 if total==0 else downloaded/total,'packages':len(list(location.rglob('*.package'))),'location':str(location)})
    # Check that each expected local file exists (extractor, converted structures, Java 25, Fabric API).
    resources={name:(ROOT/path).exists() for name,path in {'Spore extractor':'.tools/sporemodder/SporeModder FX/SporeModderFX.jar','Spore UFO':'local-assets/structures/spore_rocket.nbt','Spore creature':'local-assets/spore/spore_creature.voxels.json','Spore rocket part':'local-assets/structures/spore_thruster.nbt','Melty crate':'local-assets/structures/crate.nbt','Melty pine':'local-assets/structures/pine.nbt','Java 25':'.tools/jdk25/bin/java','Fabric API':'.tools/fabric/fabric-api.jar'}.items()}
    # Return both results.
    return {'games':games,'resources':resources}

# When run directly: write the status to verification/output/asset-status.json.
if __name__=='__main__':
    result=status();output=ROOT/'verification/output/asset-status.json';output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n')
    for game in result['games']:print(game.get('name',game['app']),f'{game.get("progress",0):.0%}',f'{game.get("packages",0)} archives', 'installed' if game['installed'] else 'incomplete')
    for name,present in result['resources'].items():print(name, 'ready' if present else 'missing')
