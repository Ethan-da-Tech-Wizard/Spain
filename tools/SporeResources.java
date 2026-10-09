import sporemodder.MainApp;
import sporemodder.HashManager;
import sporemodder.file.dbpf.*;
import sporemodder.file.filestructures.*;
import sporemodder.file.rw4.*;
import java.nio.file.*;
import java.util.*;
import com.google.gson.*;

/** A CLI adapter to the separately installed SporeModder FX library. No parser copied. */
public final class SporeResources {
    public static void main(String[] args) throws Exception {
        MainApp.testInit();
        try(FileStream input=new FileStream(args[1],"r")) {
            DatabasePackedFile db=new DatabasePackedFile();db.read(input);
            if(args[0].equals("catalog")) {
                for(DBPFItem item:db.index.items) if(item.name.getTypeID()==0x2F4E681B) {
                    String name=HashManager.get().getFileName(item.name.getInstanceID());
                    System.out.printf("%08x:%08x\t%s\t%d%n",item.name.getGroupID(),item.name.getInstanceID(),name,item.memSize);
                }
            } else {
                String[] key=args[2].split(":");int group=(int)Long.parseLong(key[0],16),id=(int)Long.parseLong(key[1],16);
                DBPFItem chosen=db.index.items.stream().filter(i->i.name.getTypeID()==0x2F4E681B&&i.name.getGroupID()==group&&i.name.getInstanceID()==id).findFirst().orElseThrow();
                RenderWare rw=new RenderWare();try(MemoryStream data=chosen.processFile(input)){rw.read(data);}
                JsonObject result=new JsonObject();JsonArray meshes=new JsonArray();
                for(RWMesh mesh:rw.getObjects(RWMesh.class)) {
                    if(mesh.vertexBuffers.isEmpty()||mesh.indexBuffer==null)continue;
                    RWVertexBuffer buffer=mesh.vertexBuffers.get(0);
                    RWVertexElement position=buffer.vertexDescription.elements.stream().filter(e->e.typeCode==0).findFirst().orElseThrow();
                    JsonArray points=new JsonArray(),triangles=new JsonArray();
                    try(MemoryStream data=new MemoryStream(buffer.vertexData.data)) {
                        for(int i=0;i<mesh.vertexCount;i++) {
                            data.seek((mesh.firstVertex+i)*buffer.vertexSize+position.offset);
                            JsonArray point=new JsonArray();point.add(data.readLEFloat());point.add(data.readLEFloat());point.add(data.readLEFloat());points.add(point);
                        }
                    }
                    try(MemoryStream data=new MemoryStream(mesh.indexBuffer.indexData.data)) {
                        boolean wide=mesh.indexBuffer.format==Direct3DEnums.D3DFORMAT.D3DFMT_INDEX32;
                        data.seek((long)mesh.firstIndex*(wide?4:2));
                        for(int i=0;i<mesh.triangleCount;i++) {
                            JsonArray face=new JsonArray();
                            for(int j=0;j<3;j++){int index=wide?data.readLEInt():data.readLEUShort();face.add(index-mesh.firstVertex);}triangles.add(face);
                        }
                    }
                    JsonObject m=new JsonObject();m.add("positions",points);m.add("triangles",triangles);meshes.add(m);
                }
                if(meshes.isEmpty())throw new IllegalArgumentException("Resource has no static triangle mesh; may be a texture or procedural creation");
                result.add("meshes",meshes);result.addProperty("source",args[1]);result.addProperty("key",args[2]);
                Files.writeString(Path.of(args[3]),new Gson().toJson(result));System.out.println("Exported "+meshes.size()+" meshes to "+args[3]);
            }
        }
    }
}
