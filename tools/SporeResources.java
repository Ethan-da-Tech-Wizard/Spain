// Program: Spain - SporeResources.java
// Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
// Last Modified: 2026-11-18
// Purpose: Command-line helper that uses the separately installed SporeModder FX library to list Spore models or export one model's triangle mesh as JSON.
// Imports: SporeModder FX classes for reading Spore data files, plus Java file tools and Gson for JSON.
import sporemodder.MainApp;
import sporemodder.HashManager;
import sporemodder.file.dbpf.*;
import sporemodder.file.filestructures.*;
import sporemodder.file.rw4.*;
import java.nio.file.*;
import java.util.*;
import com.google.gson.*;

// Usage: "catalog <package>" lists models; "export <package> <group:id> <output.json>" writes one model's mesh.
/** A CLI adapter to the separately installed SporeModder FX library. No parser copied. */
public final class SporeResources {
    /** Reads args[0] (the mode) and args[1] (the Spore .package file) and runs catalog or export. */
    public static void main(String[] args) throws Exception {
        // Start SporeModder's internal systems without a window.
        MainApp.testInit();
        // Open the Spore package file for reading (closed automatically).
        try(FileStream input=new FileStream(args[1],"r")) {
            // Read the package's index of stored files.
            DatabasePackedFile db=new DatabasePackedFile();db.read(input);
            // Catalog mode: print one line per model (type id 0x2F4E681B) with its key, name and size.
            if(args[0].equals("catalog")) {
                for(DBPFItem item:db.index.items) if(item.name.getTypeID()==0x2F4E681B) {
                    // Look up a readable name for the model id.
                    String name=HashManager.get().getFileName(item.name.getInstanceID());
                    System.out.printf("%08x:%08x\t%s\t%d%n",item.name.getGroupID(),item.name.getInstanceID(),name,item.memSize);
                }
            // Export mode: args[2] is "group:instance" in hex, args[3] is the output file.
            } else {
                // Split the key and parse each hex part into a number.
                String[] key=args[2].split(":");int group=(int)Long.parseLong(key[0],16),id=(int)Long.parseLong(key[1],16);
                // Find the one model in the package that matches the key (error if none).
                DBPFItem chosen=db.index.items.stream().filter(i->i.name.getTypeID()==0x2F4E681B&&i.name.getGroupID()==group&&i.name.getInstanceID()==id).findFirst().orElseThrow();
                // Decode the model data into RenderWare mesh objects.
                RenderWare rw=new RenderWare();try(MemoryStream data=chosen.processFile(input)){rw.read(data);}
                // Build the JSON result: a list of meshes.
                JsonObject result=new JsonObject();JsonArray meshes=new JsonArray();
                // Go through each mesh that has vertices and an index buffer.
                for(RWMesh mesh:rw.getObjects(RWMesh.class)) {
                    if(mesh.vertexBuffers.isEmpty()||mesh.indexBuffer==null)continue;
                    RWVertexBuffer buffer=mesh.vertexBuffers.get(0);
                    // Find the part of each vertex that holds its x, y, z position.
                    RWVertexElement position=buffer.vertexDescription.elements.stream().filter(e->e.typeCode==0).findFirst().orElseThrow();
                    JsonArray points=new JsonArray(),triangles=new JsonArray();
                    // Read every vertex position as three little-endian floats.
                    try(MemoryStream data=new MemoryStream(buffer.vertexData.data)) {
                        for(int i=0;i<mesh.vertexCount;i++) {
                            data.seek((mesh.firstVertex+i)*buffer.vertexSize+position.offset);
                            JsonArray point=new JsonArray();point.add(data.readLEFloat());point.add(data.readLEFloat());point.add(data.readLEFloat());points.add(point);
                        }
                    }
                    // Read triangle corner indexes (32-bit or 16-bit) and shift them so they start at this mesh's first vertex.
                    try(MemoryStream data=new MemoryStream(mesh.indexBuffer.indexData.data)) {
                        boolean wide=mesh.indexBuffer.format==Direct3DEnums.D3DFORMAT.D3DFMT_INDEX32;
                        data.seek((long)mesh.firstIndex*(wide?4:2));
                        for(int i=0;i<mesh.triangleCount;i++) {
                            JsonArray face=new JsonArray();
                            for(int j=0;j<3;j++){int index=wide?data.readLEInt():data.readLEUShort();face.add(index-mesh.firstVertex);}triangles.add(face);
                        }
                    }
                    // Store positions and triangles for this mesh.
                    JsonObject m=new JsonObject();m.add("positions",points);m.add("triangles",triangles);meshes.add(m);
                }
                // Some resources (textures, procedural creatures) have no static mesh, so report that clearly.
                if(meshes.isEmpty())throw new IllegalArgumentException("Resource has no static triangle mesh; may be a texture or procedural creation");
                // Write the JSON file and say how many meshes were exported.
                result.add("meshes",meshes);result.addProperty("source",args[1]);result.addProperty("key",args[2]);
                Files.writeString(Path.of(args[3]),new Gson().toJson(result));System.out.println("Exported "+meshes.size()+" meshes to "+args[3]);
            }
        }
    }
}
