// ==============================================================================
// Program: SporeVisuals.java
// Programmer: Ethan-da-Tech-Wizard
// Last Modified: November 19, 2026
// Purpose: Gives chosen entities and players a creature look: hides the real entity and makes block-display
//          entities shaped like the Spore creature (or the player's own captured build) follow it.
//          Custom creatures are saved per world.
// ==============================================================================

// Fit in the mod: appearance system. SpainMod creates one instance (VISUALS), calls load() at server start,
// tick() every server tick and save()/clear() on shutdown; /spain avatar <default|spore|custom|capture> reaches select() and
// (through FlightSystem's blueprint scan) custom().
// //
// Idea: instead of changing a model (impossible on a server without a resource pack), an entity that should look like a
// creature is made invisible and a group of Display.BlockDisplay entities, shaped like the creature and rendered with
// ordinary block textures, follows it. Which entities get a look is decided by tags:
//   spain.alien           Earth visitors and NPCs from other worlds (extend_pack.py) -> the Spore creature shape
//   spain.hostile         additionally recoloured to red concrete so a hostile visitor is recognisable
//   spain.avatar.spore    a player who chose /spain avatar spore -> the Spore creature shape
//   spain.avatar.custom   a player who built their own creature -> their captured blocks
// Data: the Spore creature shape is read from the jar resource /assets/spain/spore_creature.voxels.json, which exists
// only if the owner ran the local import (tools/import_spore.py); without it available() is false and nothing
// is drawn. Custom creatures are saved per world in spain-avatars.json (UUID -> list of blocks).
// Display entities are never saved (shouldBeSaved() is false); they are rebuilt on demand every session.
// Runs on the server thread. Cost: tick() looks at every entity in every loaded level each tick, which is fine
// for the small worlds this project targets but would not scale to a large server.
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

// (The comment above explains the whole class; fields follow.)
/** Spore mesh silhouettes rendered with vanilla block materials over native AI actors. */
public final class SporeVisuals {
    // One active appearance: the entity being disguised (host), its display entities, and whether it was invisible before so remove() can restore that.
    private record Visual(Entity host,List<Display.BlockDisplay> displays,boolean wasInvisible) {}

    // Active appearances by host UUID, and custom creatures (player UUID -> blocks).
    private final Map<UUID,Visual> visuals=new HashMap<>();
    private final Map<UUID,List<FlightSystem.Part>> custom=new HashMap<>();

    // The shared Spore creature shape (empty when the local art is not installed).
    private List<FlightSystem.Part> creature=List.of();
    private final Gson gson=new GsonBuilder().setPrettyPrinting().create();
    private int ticks;

    // Reset, then read (1) the optional Spore creature from the mod jar and (2) the world's saved custom creatures. Any
    // read or parse error stops the load with an exception so a damaged save is noticed, not silently ignored.
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

    // True when the Spore creature is installed; /spain avatar spore does nothing otherwise.
    public boolean available() {return !creature.isEmpty();}

    // Switch the player's appearance. Removes the existing tags and disguise first, then adds the tag for the chosen
    // mode (only if that mode is possible: Spore art installed, or the player has a custom creature). tick() sees the
    // tag on its next run and builds the displays. "default" simply leaves the player without any tag.
    public void select(ServerPlayer p,String mode) {
        p.entityTags().remove("spain.avatar.spore");p.entityTags().remove("spain.avatar.custom");
        Visual old=visuals.remove(p.getUUID());if(old!=null)remove(old);
        if(mode.equals("spore")&&available())p.addTag("spain.avatar.spore");
        if(mode.equals("custom")&&custom.containsKey(p.getUUID()))p.addTag("spain.avatar.custom");
        p.sendSystemMessage(Component.literal(mode.equals("default")?"Minecraft appearance restored. Your normal account skin applies.":"Appearance selected. Press F5 to view your creation."));
    }

    // Store a player's captured blocks as their custom creature, select it and save at once so it survives a crash.
    public void custom(ServerPlayer p,List<FlightSystem.Part> parts) {
        custom.put(p.getUUID(),List.copyOf(parts));select(p,"custom");save(p.level().getServer());
    }

    // Per tick: for every entity that should have a disguise, create the displays once and then move them to the
    // entity each tick; afterwards remove disguises of entities that no longer qualify (tag removed, entity gone or dead).
    public void tick(MinecraftServer server) {
        ticks++;
        Set<UUID> active=new HashSet<>();
        for(ServerLevel level:server.getAllLevels()) {
            // Only entities in loaded chunks are visited; Minecraft decides which chunks are loaded.
            // Only loaded actors participate; chunk streaming stays with Minecraft.
            for(Entity host:java.util.stream.StreamSupport.stream(level.getAllEntities().spliterator(),false).filter(Objects::nonNull).toList()) {
                if(host.isRemoved()||!host.isAlive())continue;

                // Pick the shape: a custom avatar uses that player's own blocks; Spore-tagged entities use the shared creature; others get nothing.
                boolean own=host.entityTags().contains("spain.avatar.custom");
                boolean spore=host.entityTags().contains("spain.alien")||host.entityTags().contains("spain.avatar.spore");
                List<FlightSystem.Part> parts=own?custom.get(host.getUUID()):spore?creature:null;
                if(parts==null||parts.isEmpty())continue;
                active.add(host.getUUID());
                Visual old=visuals.get(host.getUUID());

                // Rebuild the displays if the entity changed dimension (the displays belong to the old level) or any display was removed (for example chunk unload).
                if(old!=null&&(old.host.level()!=level||old.displays.stream().anyMatch(Entity::isRemoved))) {remove(old);visuals.remove(host.getUUID());old=null;}
                if(old==null) {
                    // Bounding box of the shape, used to scale it to fit and to centre it on the entity.
                    int minX=parts.stream().mapToInt(FlightSystem.Part::x).min().orElse(0),maxX=parts.stream().mapToInt(FlightSystem.Part::x).max().orElse(0);
                    int minY=parts.stream().mapToInt(FlightSystem.Part::y).min().orElse(0),maxY=parts.stream().mapToInt(FlightSystem.Part::y).max().orElse(0);
                    int minZ=parts.stream().mapToInt(FlightSystem.Part::z).min().orElse(0),maxZ=parts.stream().mapToInt(FlightSystem.Part::z).max().orElse(0);

                    // Uniform scale so the longest side of the shape is 1.9 blocks, roughly the height of a player (1.8), whatever size it was built.
                    double scale=1.9/Math.max(Math.max(maxY-minY+1,maxX-minX+1),maxZ-minZ+1);
                    List<Display.BlockDisplay> displays=new ArrayList<>();
                    for(var part:parts) {
                        // shouldBeSaved() returns false: displays are temporary, never written into the world.
                        var display=new Display.BlockDisplay(EntityTypes.BLOCK_DISPLAY,level) {@Override public boolean shouldBeSaved(){return false;}};
                        CompoundTag tag=new CompoundTag();
                        var state=part.state();

                        // Hostile visitors are painted red so players can tell them from friendly ones.
                        if(host.entityTags().contains("spain.hostile"))state=BuiltInRegistries.BLOCK.getValue(Identifier.withDefaultNamespace("red_concrete")).defaultBlockState();
                        tag.put("block_state",net.minecraft.world.level.block.state.BlockState.CODEC.encodeStart(NbtOps.INSTANCE,state).getOrThrow());

                        // Display transformation: scale all three axes, then translate each block so the shape is centred on x/z and stands
                        // on the entity's feet (y minimum maps to 0), each offset multiplied by the same scale.
                        CompoundTag transform=new CompoundTag();ListTag scaling=new ListTag();for(int i=0;i<3;i++)scaling.add(FloatTag.valueOf((float)scale));transform.put("scale",scaling);
                        ListTag translation=new ListTag();translation.add(FloatTag.valueOf((float)((part.x()-(minX+maxX+1)/2.0)*scale)));translation.add(FloatTag.valueOf((float)((part.y()-minY)*scale)));translation.add(FloatTag.valueOf((float)((part.z()-(minZ+maxZ+1)/2.0)*scale)));transform.put("translation",translation);

                        // teleport_duration 1 smooths movement over a tick; view_range 1 means the default draw distance.
                        tag.put("transformation",transform);tag.putInt("teleport_duration",1);tag.putFloat("view_range",1);
                        display.load(TagValueInput.create(ProblemReporter.DISCARDING,level.registryAccess(),tag));display.setNoGravity(true);display.addTag("spain.appearance_display");display.setPos(host.position());level.addFreshEntity(display);displays.add(display);
                    }

                    // Hide the real entity (and remember its previous state) so only the block shape is seen. The host keeps its hitbox, AI and name.
                    old=new Visual(host,displays,host.isInvisible());visuals.put(host.getUUID(),old);host.setInvisible(true);
                }

                // Every tick: follow the host's position and facing.
                for(var display:old.displays){display.setPos(host.position());display.setYRot(host.getYRot());}
            }
        }

        // Clean up disguises whose host no longer qualifies (or is gone) using an explicit iterator so entries can be removed during the loop.
        Iterator<Visual> iterator=visuals.values().iterator();
        while(iterator.hasNext()){Visual v=iterator.next();if(!active.contains(v.host.getUUID())){remove(v);iterator.remove();}}
    }

    // Discard the displays and restore the host's original visibility unless the host itself was removed.
    private void remove(Visual v){for(var display:v.displays)display.discard();if(!v.host.isRemoved())v.host.setInvisible(v.wasInvisible);}

    // Remove every active disguise; called on load and on shutdown so no display entities are left in the world.
    public void clear(){for(var v:visuals.values())remove(v);visuals.clear();}

    // Per-world save file next to level.dat.
    private Path path(MinecraftServer server){return server.getWorldPath(LevelResource.ROOT).resolve("spain-avatars.json");}

    // Write every custom creature as JSON ({player UUID: [parts]}), using a temporary file and an atomic move so a crash cannot leave a half-written file.
    public void save(MinecraftServer server) {
        JsonObject root=new JsonObject();
        for(var entry:custom.entrySet()){JsonArray array=new JsonArray();for(var p:entry.getValue()){JsonObject value=new JsonObject();value.addProperty("x",p.x());value.addProperty("y",p.y());value.addProperty("z",p.z());value.add("state",net.minecraft.world.level.block.state.BlockState.CODEC.encodeStart(com.mojang.serialization.JsonOps.INSTANCE,p.state()).getOrThrow());array.add(value);}root.add(entry.getKey().toString(),array);}
        try{Path p=path(server),temporary=p.resolveSibling("spain-avatars.json.tmp");Files.writeString(temporary,gson.toJson(root));Files.move(temporary,p,StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);}catch(Exception e){throw new IllegalStateException("Could not save avatar creations",e);}
    }
}
