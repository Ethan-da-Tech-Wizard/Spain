// ==============================================================================
// Program: SporeResources.java
// Programmer: Ethan-da-Tech-Wizard
// Last Modified: November 19, 2026
// Purpose: Command-line helper that opens Spore's Spore_Graphics.package with the separately installed
//          SporeModder FX library and exports one model's triangle mesh (positions and triangle
//          indexes) as JSON for tools/import_spore.py. Also has a catalog mode that lists models.
// ==============================================================================

// Fit in the repo: a tiny command-line helper, not part of the mod. tools/import_spore.py compiles it with javac against the
// separately installed SporeModder FX jar (installed by tools/setup_spore.py) and runs it once per asset. It is the only code that
// reads Spore's own game file (Spore_Graphics.package); everything else works with the plain JSON it writes. No SporeModder FX source is copied
// (the library is loaded from its jar, which keeps this repository free of GPL-3.0 code).
//
// Usage:
//   java SporeResources catalog <package>                     list resource keys, names and sizes of every mesh-type resource
//   java SporeResources export  <package> <group:instance> <out.json>   write one mesh as JSON
// Output JSON: {"meshes":[{"positions":[[x,y,z],...],"triangles":[[a,b,c],...]}], "source": ..., "key": ...}
// Triangle indexes are relative to the mesh's own first vertex, so each mesh can be read independently.
// Limits: static triangle meshes only; vertex colours, textures, skeletons and animations are ignored.
import sporemodder.MainApp;
import sporemodder.HashManager;
import sporemodder.file.dbpf.*;
import sporemodder.file.filestructures.*;
import sporemodder.file.rw4.*;
import java.nio.file.*;
import java.util.*;
import com.google.gson.*;

// (Resource type 0x2F4E681B is Spore's RenderWare model type; keys are printed and accepted as hexadecimal group:instance.)
/** A CLI adapter to the separately installed SporeModder FX library. No parser copied. */
public final class SporeResources {
    public static void main(String[] args) throws Exception {
        // SporeModder FX needs its global state (hash tables, settings) initialised before any file is read; testInit() is the headless way.
        MainApp.testInit();

        // Open the package (a DBPF container, Spore's archive format) read-only and parse its index; try-with-resources closes it.
        try(FileStream input=new FileStream(args[1],"r")) {
            DatabasePackedFile db=new DatabasePackedFile();db.read(input);

            // catalog mode: print "group:instance <tab> name <tab> size" for each model resource, to find keys for ASSETS in import_spore.py.
            if(args[0].equals("catalog")) {
                for(DBPFItem item:db.index.items) if(item.name.getTypeID()==0x2F4E681B) {
                    String name=HashManager.get().getFileName(item.name.getInstanceID());
                    System.out.printf("%08x:%08x\t%s\t%d%n",item.name.getGroupID(),item.name.getInstanceID(),name,item.memSize);
                }
            } else {
                // Parse "group:instance" hex into ints. Long.parseLong then a cast is used because hex values above 0x7FFFFFFF do not fit a signed int directly.
                String[] key=args[2].split(":");int group=(int)Long.parseLong(key[0],16),id=(int)Long.parseLong(key[1],16);

                // Find the single matching model resource; orElseThrow gives a clear failure for an unknown key.
                DBPFItem chosen=db.index.items.stream().filter(i->i.name.getTypeID()==0x2F4E681B&&i.name.getGroupID()==group&&i.name.getInstanceID()==id).findFirst().orElseThrow();

                // Decompress the resource and parse it as a RenderWare model (the engine format Spore uses).
                RenderWare rw=new RenderWare();try(MemoryStream data=chosen.processFile(input)){rw.read(data);}
                JsonObject result=new JsonObject();JsonArray meshes=new JsonArray();

                // Export each static mesh; meshes without vertex or index buffers (for example procedural parts) are skipped.
                for(RWMesh mesh:rw.getObjects(RWMesh.class)) {
                    if(mesh.vertexBuffers.isEmpty()||mesh.indexBuffer==null)continue;
                    RWVertexBuffer buffer=mesh.vertexBuffers.get(0);

                    // Vertex layouts vary; find the element whose type code is 0 (position) to know where the x/y/z floats sit within each vertex.
                    RWVertexElement position=buffer.vertexDescription.elements.stream().filter(e->e.typeCode==0).findFirst().orElseThrow();
                    JsonArray points=new JsonArray(),triangles=new JsonArray();
                    try(MemoryStream data=new MemoryStream(buffer.vertexData.data)) {
                        for(int i=0;i<mesh.vertexCount;i++) {
                            // Byte offset of vertex i = (first vertex + i) x bytes per vertex + offset of the position field. Spore stores little-endian floats.
                            data.seek((mesh.firstVertex+i)*buffer.vertexSize+position.offset);
                            JsonArray point=new JsonArray();point.add(data.readLEFloat());point.add(data.readLEFloat());point.add(data.readLEFloat());points.add(point);
                        }
                    }
                    try(MemoryStream data=new MemoryStream(mesh.indexBuffer.indexData.data)) {
                        // Triangles use 32-bit or 16-bit indexes depending on the buffer format.
                        boolean wide=mesh.indexBuffer.format==Direct3DEnums.D3DFORMAT.D3DFMT_INDEX32;
                        data.seek((long)mesh.firstIndex*(wide?4:2));
                        for(int i=0;i<mesh.triangleCount;i++) {
                            JsonArray face=new JsonArray();

                            // Make the index relative to this mesh's first vertex (the index buffer is shared by all meshes of the file).
                            for(int j=0;j<3;j++){int index=wide?data.readLEInt():data.readLEUShort();face.add(index-mesh.firstVertex);}triangles.add(face);
                        }
                    }
                    JsonObject m=new JsonObject();m.add("positions",points);m.add("triangles",triangles);meshes.add(m);
                }

                // Fail clearly when the resource is not a static model, so import_spore.py stops instead of writing an empty asset.
                if(meshes.isEmpty())throw new IllegalArgumentException("Resource has no static triangle mesh; may be a texture or procedural creation");
                result.add("meshes",meshes);result.addProperty("source",args[1]);result.addProperty("key",args[2]);
                Files.writeString(Path.of(args[3]),new Gson().toJson(result));System.out.println("Exported "+meshes.size()+" meshes to "+args[3]);
            }
        }
    }
}
