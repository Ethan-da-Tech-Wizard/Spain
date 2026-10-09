#!/usr/bin/env python3
"""Import selected Spore meshes via SporeModder FX, then remesh into Minecraft blocks."""
import argparse,hashlib,json,math,os,subprocess,urllib.request,zipfile
from pathlib import Path
from nbt import structure
ROOT=Path(__file__).resolve().parents[1]
ASSETS=[('spore_rocket','00000000:f651a4d4',9,'loading_placeholder_ufo'),('spore_creature','00000000:62052d87',8,'loading_placeholder_creature'),('spore_thruster','00000000:73db2759',5,'ci_bribe_rocket')]


def voxelize_mesh(document,longest,color='cyan_concrete'):
    # Spore uses Z up; Minecraft uses Y up. All materials use Minecraft's native textures.
    meshes=[([[p[0],p[2],-p[1]] for p in mesh['positions']],mesh['triangles']) for mesh in document['meshes']]
    all_points=[p for points,_ in meshes for p in points]
    low=[min(p[i] for p in all_points) for i in range(3)];high=[max(p[i] for p in all_points) for i in range(3)]
    scale=(longest-.001)/max(b-a for a,b in zip(low,high));size=[max(1,math.ceil((b-a)*scale)) for a,b in zip(low,high)]
    cells={}
    for points,faces in meshes:
        vertices=[tuple((p[i]-low[i])*scale for i in range(3)) for p in points]
        for face in faces:
            if any(i<0 or i>=len(vertices) for i in face):raise ValueError('Out-of-range Spore mesh index')
            a,b,c=[vertices[i] for i in face];samples=max(1,math.ceil(max(math.dist(a,b),math.dist(b,c),math.dist(c,a))*2))
            for row in range(samples+1):
                for col in range(samples+1-row):
                    weights=(1-(row+col)/samples,row/samples,col/samples)
                    point=[sum(v[i]*w for v,w in zip((a,b,c),weights)) for i in range(3)]
                    cell=tuple(min(size[i]-1,max(0,math.floor(point[i]))) for i in range(3));cells[cell]=0
    # Accent upper surfaces and silhouette edges without introducing a second texture style.
    palette=[color,'light_blue_concrete','white_concrete','black_concrete']
    for x,y,z in list(cells):
        if y==size[1]-1:cells[x,y,z]=2
        elif (x+y+z)%7==0:cells[x,y,z]=1
    return size,cells,palette


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--package',type=Path,default=Path.home()/'.local/share/Steam/steamapps/common/Spore/Data/Spore_Graphics.package');parser.add_argument('--sporemodder',type=Path,default=ROOT/'.tools/sporemodder/SporeModder FX/SporeModderFX.jar');args=parser.parse_args()
    java=ROOT/'.tools/jdk25/bin';jars=list((Path.home()/'.local/share/PrismLauncher/libraries/com/google/code/gson').rglob('*.jar'))
    cp=os.pathsep.join(map(str,[args.sporemodder,*jars]));classes=ROOT/'.tools/spore-classes';classes.mkdir(parents=True,exist_ok=True)
    subprocess.run([str(java/'javac'),'-cp',cp,'-d',str(classes),str(ROOT/'tools/SporeResources.java')],check=True)
    output=ROOT/'local-assets/spore';output.mkdir(parents=True,exist_ok=True);structures=ROOT/'local-assets/structures';structures.mkdir(parents=True,exist_ok=True)
    records=[]
    for asset,key,longest,name in ASSETS:
        raw=output/(asset+'.json')
        subprocess.run([str(java/'java'),'-cp',str(classes)+os.pathsep+cp,'SporeResources','export',str(args.package),key,str(raw)],check=True)
        size,cells,palette=voxelize_mesh(json.loads(raw.read_text()),longest,'lime_concrete' if asset=='spore_creature' else 'cyan_concrete')
        (structures/(asset+'.nbt')).write_bytes(structure(size,cells,palette))
        mesh={'size':size,'parts':[{'x':x,'y':y,'z':z,'block':palette[index]} for (x,y,z),index in sorted(cells.items())]}
        (output/(asset+'.voxels.json')).write_text(json.dumps(mesh)+'\n')
        records.append({'id':asset,'resource':name,'key':key,'source_package':str(args.package),'mesh_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'size':size,'blocks':len(cells),'materials':'Minecraft palette recolor; original Spore mesh geometry'})
        print(asset,size,len(cells),'blocks')
    (output/'provenance.json').write_text(json.dumps({'upstream':'Spore (EA / Maxis)','extractor':'SporeModder FX 2.2.27 (GPL-3.0), installed separately; no extractor source copied','assets':records},indent=2)+'\n')
if __name__=='__main__':main()
