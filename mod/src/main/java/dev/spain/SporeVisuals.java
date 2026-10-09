package dev.spain;

import com.google.gson.*;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Display;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.level.block.Block;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.Identifier;
import net.minecraft.nbt.*;
import net.minecraft.world.level.storage.TagValueInput;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.util.ProblemReporter;
import net.minecraft.world.phys.Vec3;
import net.minecraft.network.chat.Component;
import java.nio.file.*;
import java.io.InputStream;
import java.util.*;

/** Spore mesh silhouettes rendered with vanilla block materials over native AI actors. */
public final class SporeVisuals {
    private record Visual(Entity host,List<Display.BlockDisplay> displays,boolean wasInvisible) {}
    private final Map<UUID,Visual> visuals=new HashMap<>();
    private final Map<UUID,List<FlightSystem.Part>> custom=new HashMap<>();
    private List<FlightSystem.Part> creature=List.of();
    private final Gson gson=new GsonBuilder().setPrettyPrinting().create();
    private int ticks;
    public void load(MinecraftServer server) {
        clear();custom.clear();
        try(InputStream input=getClass().getResourceAsStream("/assets/spain/spore_creature.voxels.json")) {
            if(input!=null) {
                JsonObject data=JsonParser.parseString(new String(input.readAllBytes(),java.nio.charset.StandardCharsets.UTF_8)).getAsJsonObject();
                var parts=new ArrayList<FlightSystem.Part>();
                for(JsonElement e:data.getAsJsonArray("parts")) {JsonObject p=e.getAsJsonObject();parts.add(new FlightSystem.Part(p.get("x").getAsInt(),p.get("y").getAsInt(),p.get("z").getAsInt(),BuiltInRegistries.BLOCK.getValue(Identifier.withDefaultNamespace(p.get("block").getAsString())).defaultBlockState()));}
                creature=parts;
            }
            Path file=path(server);
            if(Files.exists(file)) {
                JsonObject data=JsonParser.parseString(Files.readString(file)).getAsJsonObject();
                for(var entry:data.entrySet()) {
                    List<FlightSystem.Part> parts=new ArrayList<>();
                    for(JsonElement e:entry.getValue().getAsJsonArray()) {JsonObject p=e.getAsJsonObject();parts.add(new FlightSystem.Part(p.get("x").getAsInt(),p.get("y").getAsInt(),p.get("z").getAsInt(),net.minecraft.world.level.block.state.BlockState.CODEC.parse(com.mojang.serialization.JsonOps.INSTANCE,p.get("state")).getOrThrow()));}
                    custom.put(UUID.fromString(entry.getKey()),parts);
                }
            }
        } catch(Exception e) {throw new IllegalStateException("Unable to load Spain appearance assets",e);}
    }
    public boolean available() {return !creature.isEmpty();}
    public void select(ServerPlayer p,String mode) {
        p.entityTags().remove("spain.avatar.spore");p.entityTags().remove("spain.avatar.custom");
        Visual old=visuals.remove(p.getUUID());if(old!=null)remove(old);
        if(mode.equals("spore")&&available())p.addTag("spain.avatar.spore");
        if(mode.equals("custom")&&custom.containsKey(p.getUUID()))p.addTag("spain.avatar.custom");
        p.sendSystemMessage(Component.literal(mode.equals("default")?"Minecraft appearance restored. Your normal account skin applies.":"Appearance selected. Press F5 to view your creation."));
    }
    public void custom(ServerPlayer p,List<FlightSystem.Part> parts) {
        custom.put(p.getUUID(),List.copyOf(parts));select(p,"custom");save(p.level().getServer());
    }
    public void tick(MinecraftServer server) {
        ticks++;
        Set<UUID> active=new HashSet<>();
        for(ServerLevel level:server.getAllLevels()) {
            // Only loaded actors participate; chunk streaming stays with Minecraft.
            for(Entity host:java.util.stream.StreamSupport.stream(level.getAllEntities().spliterator(),false).filter(Objects::nonNull).toList()) {
                if(host.isRemoved()||!host.isAlive())continue;
                boolean own=host.entityTags().contains("spain.avatar.custom");
                boolean spore=host.entityTags().contains("spain.alien")||host.entityTags().contains("spain.avatar.spore");
                List<FlightSystem.Part> parts=own?custom.get(host.getUUID()):spore?creature:null;
                if(parts==null||parts.isEmpty())continue;
                active.add(host.getUUID());
                Visual old=visuals.get(host.getUUID());
                if(old!=null&&(old.host.level()!=level||old.displays.stream().anyMatch(Entity::isRemoved))) {remove(old);visuals.remove(host.getUUID());old=null;}
                if(old==null) {
                    int minX=parts.stream().mapToInt(FlightSystem.Part::x).min().orElse(0),maxX=parts.stream().mapToInt(FlightSystem.Part::x).max().orElse(0);
                    int minY=parts.stream().mapToInt(FlightSystem.Part::y).min().orElse(0),maxY=parts.stream().mapToInt(FlightSystem.Part::y).max().orElse(0);
                    int minZ=parts.stream().mapToInt(FlightSystem.Part::z).min().orElse(0),maxZ=parts.stream().mapToInt(FlightSystem.Part::z).max().orElse(0);
                    double scale=1.9/Math.max(Math.max(maxY-minY+1,maxX-minX+1),maxZ-minZ+1);
                    List<Display.BlockDisplay> displays=new ArrayList<>();
                    for(var part:parts) {
                        var display=new Display.BlockDisplay(EntityTypes.BLOCK_DISPLAY,level) {@Override public boolean shouldBeSaved(){return false;}};
                        CompoundTag tag=new CompoundTag();
                        var state=part.state();
                        if(host.entityTags().contains("spain.hostile"))state=BuiltInRegistries.BLOCK.getValue(Identifier.withDefaultNamespace("red_concrete")).defaultBlockState();
                        tag.put("block_state",net.minecraft.world.level.block.state.BlockState.CODEC.encodeStart(NbtOps.INSTANCE,state).getOrThrow());
                        CompoundTag transform=new CompoundTag();ListTag scaling=new ListTag();for(int i=0;i<3;i++)scaling.add(FloatTag.valueOf((float)scale));transform.put("scale",scaling);
                        ListTag translation=new ListTag();translation.add(FloatTag.valueOf((float)((part.x()-(minX+maxX+1)/2.0)*scale)));translation.add(FloatTag.valueOf((float)((part.y()-minY)*scale)));translation.add(FloatTag.valueOf((float)((part.z()-(minZ+maxZ+1)/2.0)*scale)));transform.put("translation",translation);
                        tag.put("transformation",transform);tag.putInt("teleport_duration",1);tag.putFloat("view_range",1);
                        display.load(TagValueInput.create(ProblemReporter.DISCARDING,level.registryAccess(),tag));display.setNoGravity(true);display.addTag("spain.appearance_display");display.setPos(host.position());level.addFreshEntity(display);displays.add(display);
                    }
                    old=new Visual(host,displays,host.isInvisible());visuals.put(host.getUUID(),old);host.setInvisible(true);
                }
                for(var display:old.displays){display.setPos(host.position());display.setYRot(host.getYRot());}
            }
        }
        Iterator<Visual> iterator=visuals.values().iterator();
        while(iterator.hasNext()){Visual v=iterator.next();if(!active.contains(v.host.getUUID())){remove(v);iterator.remove();}}
    }
    private void remove(Visual v){for(var display:v.displays)display.discard();if(!v.host.isRemoved())v.host.setInvisible(v.wasInvisible);}
    public void clear(){for(var v:visuals.values())remove(v);visuals.clear();}
    private Path path(MinecraftServer server){return server.getWorldPath(LevelResource.ROOT).resolve("spain-avatars.json");}
    public void save(MinecraftServer server) {
        JsonObject root=new JsonObject();
        for(var entry:custom.entrySet()){JsonArray array=new JsonArray();for(var p:entry.getValue()){JsonObject value=new JsonObject();value.addProperty("x",p.x());value.addProperty("y",p.y());value.addProperty("z",p.z());value.add("state",net.minecraft.world.level.block.state.BlockState.CODEC.encodeStart(com.mojang.serialization.JsonOps.INSTANCE,p.state()).getOrThrow());array.add(value);}root.add(entry.getKey().toString(),array);}
        try{Path p=path(server),temporary=p.resolveSibling("spain-avatars.json.tmp");Files.writeString(temporary,gson.toJson(root));Files.move(temporary,p,StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);}catch(Exception e){throw new IllegalStateException("Could not save avatar creations",e);}
    }
}
