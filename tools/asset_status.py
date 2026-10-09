#!/usr/bin/env python3
"""Read Steam download manifests and check the local Minecraft/Spore build inputs."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def status(steam:Path=Path.home()/'.local/share/Steam/steamapps'):
    games=[]
    for app in ['17390','17440','24720']:
        manifest=steam/f'appmanifest_{app}.acf'
        if not manifest.exists():games.append({'app':app,'installed':False});continue
        fields=dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"',manifest.read_text()))
        location=steam/'common'/fields['installdir'];downloaded=int(fields.get('BytesDownloaded',0));total=int(fields.get('BytesToDownload',0))
        games.append({'app':app,'name':fields['name'],'installed':fields.get('StateFlags')=='4' and location.exists(),'downloaded_bytes':downloaded,'total_bytes':total,'progress':1 if total==0 else downloaded/total,'packages':len(list(location.rglob('*.package'))),'location':str(location)})
    resources={name:(ROOT/path).exists() for name,path in {'Spore extractor':'.tools/sporemodder/SporeModder FX/SporeModderFX.jar','Spore UFO':'local-assets/structures/spore_rocket.nbt','Spore creature':'local-assets/spore/spore_creature.voxels.json','Spore rocket part':'local-assets/structures/spore_thruster.nbt','Melty crate':'local-assets/structures/crate.nbt','Melty pine':'local-assets/structures/pine.nbt','Java 25':'.tools/jdk25/bin/java','Fabric API':'.tools/fabric/fabric-api.jar'}.items()}
    return {'games':games,'resources':resources}

if __name__=='__main__':
    result=status();output=ROOT/'verification/output/asset-status.json';output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n')
    for game in result['games']:print(game.get('name',game['app']),f'{game.get("progress",0):.0%}',f'{game.get("packages",0)} archives', 'installed' if game['installed'] else 'incomplete')
    for name,present in result['resources'].items():print(name, 'ready' if present else 'missing')
