#!/usr/bin/env python3
# ==============================================================================
# Program: import_spore.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Uses a locally installed SporeModder FX plus Spore's own game files to export
#          three creature/rocket meshes, then converts each into a Minecraft block structure
#          (.nbt) and a .voxels.json file the Java mod can render. Local only; nothing from
#          Spore is committed.
# ==============================================================================

"""Import selected Spore meshes via SporeModder FX, then remesh into Minecraft blocks."""

# Fit in the repo: optional local-art importer for three Spore models (a UFO used as a rocket, a creature and a
# rocket thruster). scripts/update.sh runs setup_spore.py (installs SporeModder FX) and then this script only if
# Spore is installed through Steam. It produces, all under git-ignored local-assets/:
#   structures/<asset>.nbt           vanilla block structure; build_pack.py/extend_pack.py place it
#   spore/<asset>.voxels.json        list of coloured blocks; build_mod.py bundles it into the mod jar and
#                                    SporeVisuals.java draws it in game
#   spore/provenance.json            where the art came from (EA / Maxis) and with which extractor
# Spore's meshes are extracted by tools/SporeResources.java (run through SporeModder FX), which writes a JSON file of
# positions and triangles; this file turns that into blocks. Spore art is not redistributed by the repository.
#
# Needs: Spore_Graphics.package from the local Steam install, .tools/sporemodder (setup_spore.py),
# .tools/jdk25 (scripts/setup.sh) and Gson from Prism's libraries. Linux paths.
# Limits: three fixed assets; no colour from Spore textures (shapes only, recoloured with Minecraft blocks).
import argparse,hashlib,json,math,os,subprocess,urllib.request,zipfile
from pathlib import Path
from nbt import structure
ROOT=Path(__file__).resolve().parents[1]

# (output name, Spore resource key "group:instance" as hex, size in blocks of the longest side, Spore's own name for the resource). The keys identify files inside Spore_Graphics.package; the sizes used are UFO 9, creature 8 and thruster 5 blocks.
ASSETS=[('spore_rocket','00000000:f651a4d4',9,'loading_placeholder_ufo'),('spore_creature','00000000:62052d87',8,'loading_placeholder_creature'),('spore_thruster','00000000:73db2759',5,'ci_bribe_rocket')]


def voxelize_mesh(document,longest,color='cyan_concrete'):
    """Turn an exported Spore mesh into voxels; return (size, cells, palette).

    Args:
        document: dict from SporeResources.java with `meshes`, each having `positions` and `triangles`.
        longest: block length of the longest axis.
        color: main block colour (the creature uses lime, everything else cyan).

    Returns:
        size: [x, y, z] grid size in blocks; cells: dict {(x, y, z): palette index}; palette: block names
        without the minecraft: prefix.

    Raises:
        ValueError: if a triangle refers to a vertex that does not exist.

    The sampling method is the same as in import_assets.voxelize (points on a half-block grid across each triangle).
    """
    # Rotate from Spore's axes (Z up) to Minecraft's (Y up): (x, y, z) becomes (x, z, -y). Without this the models would lie on their side.
    # Spore uses Z up; Minecraft uses Y up. All materials use Minecraft's native textures.
    meshes=[([[p[0],p[2],-p[1]] for p in mesh['positions']],mesh['triangles']) for mesh in document['meshes']]
    all_points=[p for points,_ in meshes for p in points]
    low=[min(p[i] for p in all_points) for i in range(3)];high=[max(p[i] for p in all_points) for i in range(3)]

    # Scale so the longest side fits `longest` blocks without ever reaching the index `longest` (see import_assets.voxelize).
    scale=(longest-.001)/max(b-a for a,b in zip(low,high));size=[max(1,math.ceil((b-a)*scale)) for a,b in zip(low,high)]
    cells={}
    for points,faces in meshes:
        vertices=[tuple((p[i]-low[i])*scale for i in range(3)) for p in points]
        for face in faces:
            # Validate indices up front: a bad mesh should fail with a clear message instead of an IndexError deep in the loop.
            if any(i<0 or i>=len(vertices) for i in face):raise ValueError('Out-of-range Spore mesh index')
            a,b,c=[vertices[i] for i in face];samples=max(1,math.ceil(max(math.dist(a,b),math.dist(b,c),math.dist(c,a))*2))
            for row in range(samples+1):
                for col in range(samples+1-row):
                    weights=(1-(row+col)/samples,row/samples,col/samples)
                    point=[sum(v[i]*w for v,w in zip((a,b,c),weights)) for i in range(3)]
                    cell=tuple(min(size[i]-1,max(0,math.floor(point[i]))) for i in range(3));cells[cell]=0

    # Colouring: the top layer becomes white concrete (index 2) and every seventh block along the diagonal light blue (index 1), giving a light top and some speckle with only vanilla textures. Index 3 (black) is in the palette but no block uses it.
    # Accent upper surfaces and silhouette edges without introducing a second texture style.
    palette=[color,'light_blue_concrete','white_concrete','black_concrete']
    for x,y,z in list(cells):
        if y==size[1]-1:cells[x,y,z]=2
        elif (x+y+z)%7==0:cells[x,y,z]=1
    return size,cells,palette


def main():
    """Export each asset from the Spore package, voxelize it, and write structure, voxel and provenance files.

    The Java helper is compiled on the fly (javac) against SporeModder FX and Gson, then run once per asset. Each run
    can take a while because Spore's package file is large. Any failing subprocess aborts the script (check=True).
    """
    parser=argparse.ArgumentParser();parser.add_argument('--package',type=Path,default=Path.home()/'.local/share/Steam/steamapps/common/Spore/Data/Spore_Graphics.package');parser.add_argument('--sporemodder',type=Path,default=ROOT/'.tools/sporemodder/SporeModder FX/SporeModderFX.jar');args=parser.parse_args()

    # Use the bundled JDK 25 so the helper is compiled for the same Java version SporeModder FX runs on.
    java=ROOT/'.tools/jdk25/bin';jars=list((Path.home()/'.local/share/PrismLauncher/libraries/com/google/code/gson').rglob('*.jar'))
    cp=os.pathsep.join(map(str,[args.sporemodder,*jars]));classes=ROOT/'.tools/spore-classes';classes.mkdir(parents=True,exist_ok=True)
    subprocess.run([str(java/'javac'),'-cp',cp,'-d',str(classes),str(ROOT/'tools/SporeResources.java')],check=True)
    output=ROOT/'local-assets/spore';output.mkdir(parents=True,exist_ok=True);structures=ROOT/'local-assets/structures';structures.mkdir(parents=True,exist_ok=True)
    records=[]

    # One pass per asset: export mesh JSON, voxelize, write the three local files and remember a record (with the mesh's SHA-256) for provenance.json.
    for asset,key,longest,name in ASSETS:
        raw=output/(asset+'.json')
        subprocess.run([str(java/'java'),'-cp',str(classes)+os.pathsep+cp,'SporeResources','export',str(args.package),key,str(raw)],check=True)
        size,cells,palette=voxelize_mesh(json.loads(raw.read_text()),longest,'lime_concrete' if asset=='spore_creature' else 'cyan_concrete')
        (structures/(asset+'.nbt')).write_bytes(structure(size,cells,palette))
        mesh={'size':size,'parts':[{'x':x,'y':y,'z':z,'block':palette[index]} for (x,y,z),index in sorted(cells.items())]}
        (output/(asset+'.voxels.json')).write_text(json.dumps(mesh)+'\n')
        records.append({'id':asset,'resource':name,'key':key,'source_package':str(args.package),'mesh_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'size':size,'blocks':len(cells),'materials':'Minecraft palette recolor; original Spore mesh geometry'})
        print(asset,size,len(cells),'blocks')

    # Provenance record: upstream owner, the extractor with its version and licence (GPL-3.0, installed separately, none of its source copied), and per-asset details.
    (output/'provenance.json').write_text(json.dumps({'upstream':'Spore (EA / Maxis)','extractor':'SporeModder FX 2.2.27 (GPL-3.0), installed separately; no extractor source copied','assets':records},indent=2)+'\n')
if __name__=='__main__':main()
