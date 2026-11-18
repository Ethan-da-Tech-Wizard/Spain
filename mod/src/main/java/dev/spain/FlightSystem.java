// Program: Spain - FlightSystem.java
// Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
// Last Modified: 2026-11-18
// Purpose: Server-side logic for the block-display rocket ships: designing, scanning a blueprint, boarding, flying, landing, physics settling and saving.
// Everything in this file lives in the dev.spain package.
package dev.spain;

// Imports: Gson reads/writes JSON, and the net.minecraft classes are the game objects this mod controls.
import com.google.gson.*;
import com.mojang.serialization.JsonOps;
import com.mojang.serialization.Dynamic;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.Display;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.level.storage.TagValueInput;
import net.minecraft.util.ProblemReporter;
import net.minecraft.nbt.*;
import net.minecraft.tags.FluidTags;
import net.minecraft.world.phys.Vec3;
import java.nio.file.*;
import java.util.*;

// FlightSystem keeps one Ship per player and moves it each server tick.
// A ship is drawn with block display entities, so no custom entity type is needed.
/** Native block-display ships. Minecraft remains responsible for player movement and terrain. */
public final class FlightSystem {
    /** One block of a ship: its offset from the ship center (x, y, z) and which block state it is. */
    public record Part(int x,int y,int z,BlockState state) {}
    /** A player's whole ship: its parts, the display entities that draw it, and its flight state. */
    public static final class Ship {
        // The blocks that make up the ship.
        public final List<Part> parts=new ArrayList<>();
        // The visible display entities, one per part (rebuilt when needed, never saved).
        public final List<Display.BlockDisplay> displays=new ArrayList<>();
        // Which world (dimension) the ship is in.
        public String dimension="minecraft:overworld";
        // Position of the ship center in the world.
        public Vec3 anchor=new Vec3(9,97,1);
        // True while the player is flying this ship.
        public boolean piloting;
        // Facing direction in degrees.
        public float yaw;
        // Remember the player's normal flying speed and flight permission so they can be restored on landing.
        float originalSpeed=.05f;
        boolean originalMayfly;
        // Current falling speed used when the parked ship settles.
        double velocity;
    }
    // A box in the world picked by two corner positions (used to capture a blueprint).
    private record Selection(String dimension,BlockPos a,BlockPos b) {}
    // Per-player data, keyed by player id: ships, selected boxes, running scans, and undo history.
    private final Map<UUID,Ship> ships=new HashMap<>();
    private final Map<UUID,Selection> selections=new HashMap<>();
    private final Map<UUID,Scan> scans=new HashMap<>();
    // Players seen online so far, used to clean up leftover flight tags after a restart.
    private final Set<UUID> connected=new HashSet<>();
    private final Map<UUID,Deque<List<Part>>> history=new HashMap<>();
    // Callback that tells a player's client to change camera; SpainMod sets the real one, the default does nothing.
    public java.util.function.BiConsumer<ServerPlayer,FlightView> view=(player,payload)->{};
    // The running server, and a tick counter used to save every 100 ticks.
    private MinecraftServer server;
    private int ticks;
    // Gson object that writes nicely indented JSON for the save file.
    private final Gson gson=new GsonBuilder().setPrettyPrinting().create();
    /** A blueprint scan that reads the selected box in small slices over several ticks so the server does not freeze. */
    private class Scan {
        // The player scanning, the ship being built, and the box being scanned.
        final ServerPlayer player; final Ship ship=new Ship(); final Selection selection;
        // True when the scan is for a player avatar (a block creature) instead of a ship.
        boolean avatar;
        // Walks over every block position inside the box.
        final Iterator<BlockPos> positions;
        // Start a scan: remember the player and box, and set the ship world and anchor.
        Scan(ServerPlayer p,Selection s) {
            player=p;selection=s;positions=BlockPos.betweenClosed(s.a,s.b).iterator();
            ship.dimension=s.dimension;ship.anchor=new Vec3(s.a.getX(),s.a.getY(),s.a.getZ());
        }
        /** Scan up to 1024 blocks. Returns true when the scan is finished (done or failed), false when more work remains. */
        boolean step() {
            // Look up the world being scanned.
            ServerLevel level=world(selection.dimension);
            // Handle at most 1024 blocks per tick.
            for(int i=0;i<1024&&positions.hasNext();i++) {
                // Keep only solid blocks (not air, not water or lava), stored relative to the box corner.
                BlockPos p=positions.next(); BlockState state=level.getBlockState(p);
                if(!state.isAir()&&state.getFluidState().isEmpty()) ship.parts.add(new Part(p.getX()-selection.a.getX(),p.getY()-selection.a.getY(),p.getZ()-selection.a.getZ(),state));
            }
            // Not done yet: come back next tick.
            if(positions.hasNext()) return false;
            // Nothing was found in the box, so tell the player and stop.
            if(ship.parts.isEmpty()) {message(player,"The selection is empty. Build your rocket first.");return true;}
            // Avatar scans turn the blocks into the player's custom appearance instead of a ship.
            if(avatar) {SpainMod.VISUALS.custom(player,ship.parts);message(player,"Created your own block creature. Press F5 to preview it.");return true;}
            // Replace any older ship: get the pilot out and remove its display entities.
            Ship previous=ships.get(player.getUUID());
            if(previous!=null) {if(previous.piloting) unboard(player,previous);clearDisplays(previous);}
            // The next lines center the parts and register the new ship.
            // Blueprints leave the workshop intact. A landed craft is an invulnerable projection.
            // Shift the parts so the ship is centered on x and z.
            center(ship);
            ships.put(player.getUUID(),ship);
            // Park the ship 4 blocks east of the player.
            ship.anchor=player.position().add(4,0,0);
            // Mark the launch quest step as done for this player.
            command(player,"scoreboard players set @s spain.launch 3");
            // Save the ships file and tell the player the capture worked.
            save(server);message(player,"Captured "+ship.parts.size()+" parts. Board to fly. Your workshop remains editable.");
            return true;
        }
    }
    /** Returns this player's ship, or null if they have none. */
    public Ship ship(ServerPlayer player) {return ships.get(player.getUUID());}
    /** Re-centers a ship horizontally so its middle is at x=0, z=0 (y is unchanged). */
    private void center(Ship ship) {
        // Middle x = halfway between the smallest and largest x.
        int x=(ship.parts.stream().mapToInt(Part::x).min().orElse(0)+ship.parts.stream().mapToInt(Part::x).max().orElse(0))/2;
        // Same for z.
        int z=(ship.parts.stream().mapToInt(Part::z).min().orElse(0)+ship.parts.stream().mapToInt(Part::z).max().orElse(0))/2;
        // Make shifted copies of every part, then replace the old list with them.
        var copy=ship.parts.stream().map(p->new Part(p.x-x,p.y,p.z-z,p.state)).toList();ship.parts.clear();ship.parts.addAll(copy);
    }
    /** Loads a premade part list (like the Spore rocket hull) from a .voxels.json file inside the mod jar. Returns an empty list if the file is missing. */
    private List<Part> model(String name) {
        // Open the resource file; try-with-resources closes it automatically.
        try(var input=getClass().getResourceAsStream("/assets/spain/"+name+".voxels.json")) {
            // No such model packaged: return nothing so callers can use a fallback shape.
            if(input==null)return List.of();
            // Read the whole file as text and parse it as a JSON object.
            var json=JsonParser.parseString(new String(input.readAllBytes(),java.nio.charset.StandardCharsets.UTF_8)).getAsJsonObject();
            // Build a temporary ship just to reuse the centering code.
            Ship s=new Ship();
            // Each JSON entry has x, y, z and a block name; look the block up in Minecraft's block registry.
            for(var element:json.getAsJsonArray("parts")) {var p=element.getAsJsonObject();s.parts.add(new Part(p.get("x").getAsInt(),p.get("y").getAsInt(),p.get("z").getAsInt(),net.minecraft.core.registries.BuiltInRegistries.BLOCK.getValue(Identifier.withDefaultNamespace(p.get("block").getAsString())).defaultBlockState()));}
            // Center the model and hand back its parts.
            center(s);return s.parts;
        // Any failure becomes a clear error message.
        } catch(Exception e) {throw new IllegalStateException("Cannot load rocket creator part "+name,e);}
    }
    /** Turns a block name like "cyan_concrete" into Minecraft's default block state. */
    private BlockState block(String id){return net.minecraft.core.registries.BuiltInRegistries.BLOCK.getValue(Identifier.withDefaultNamespace(id)).defaultBlockState();}
    /** Clears a small 3x3 column in the middle of the ship so the pilot has room. */
    private void cockpit(Ship s) {s.parts.removeIf(p->Math.abs(p.x)<=1&&Math.abs(p.z)<=1&&p.y>=0&&p.y<=2);}
    /** Handles one button of the rocket creator (hull, wings, engine, cabin, stretch, rotate, undo, clear). Returns 1 for the command system. */
    public int design(ServerPlayer p,String choice) {
        // Get (or create) the ship, leaving the cockpit first if the player was flying.
        server=p.level().getServer();Ship s=ships.computeIfAbsent(p.getUUID(),id->new Ship());
        if(s.piloting)unboard(p,s);
        // Remove old displays and put the preview 7 blocks in front of the player.
        clearDisplays(s);s.dimension=dimension(p);s.anchor=p.position().add(0,0,7);
        // Each player has a stack of earlier designs for the undo button.
        var undo=history.computeIfAbsent(p.getUUID(),id->new ArrayDeque<>());
        // Undo: restore the most recent saved design.
        if(choice.equals("undo")) {if(!undo.isEmpty()){s.parts.clear();s.parts.addAll(undo.pop());}}
        // Any other choice: save the current design for undo, then change it.
        else {
            undo.push(List.copyOf(s.parts));
            // reach = how far out the ship extends sideways; front = the frontmost z. Used to place new parts.
            int reach=s.parts.stream().mapToInt(part->Math.abs(part.x)).max().orElse(3);
            int front=s.parts.stream().mapToInt(Part::z).max().orElse(0);
            // Each case below adds or changes parts.
            switch(choice) {
                // Remove everything.
                case "clear" -> s.parts.clear();
                // Turn the preview 90 degrees.
                case "rotate" -> s.yaw+=90;
                // Add the Spore rocket hull (or a simple cyan diamond-shaped floor if the model is missing).
                case "hull" -> {
                    var hull=model("spore_rocket");int offset=s.parts.isEmpty()?0:front+5;
                    if(hull.isEmpty()) {
                        for(int x=-3;x<=3;x++)for(int z=-4;z<=4;z++)if(Math.abs(x)+Math.abs(z)<=6)s.parts.add(new Part(x,0,z+offset,block("cyan_concrete")));
                    } else {
                        // Use the real hull model.
                        for(Part part:hull)s.parts.add(new Part(part.x,part.y,part.z+offset,part.state));
                    }
                }
                // Add a thruster behind the ship, plus a magma block as the flame.
                case "engine" -> {
                    int back=s.parts.stream().mapToInt(Part::z).min().orElse(0)-3;
                    var engine=model("spore_thruster");
                    if(engine.isEmpty())s.parts.add(new Part(0,0,back,block("magma_block")));
                    else for(Part part:engine)s.parts.add(new Part(part.x,part.y,part.z+back,part.state));
                    s.parts.add(new Part(0,1,back-3,block("magma_block")));
                }
                // Add symmetric wings on both sides (side is -1 and 1).
                case "wings" -> {
                    for(int side:new int[]{-1,1})for(int x=1;x<=4;x++)for(int z=-2;z<=2;z++)if(x+Math.abs(z)<=5)s.parts.add(new Part(side*(reach+x),0,z,block(x==4?"cyan_concrete":"white_concrete")));
                }
                // Add a glass cabin: glass walls and a white roof.
                case "cabin" -> {
                    for(int x=-2;x<=2;x++)for(int z=-2;z<=2;z++)for(int y=1;y<=3;y++)if(Math.abs(x)==2||Math.abs(z)==2||y==3)s.parts.add(new Part(x,y,z,block(y==3?"white_concrete":"light_blue_stained_glass")));
                }
                // Make the ship twice as long by doubling every z position.
                case "stretch" -> {
                    var old=List.copyOf(s.parts);s.parts.clear();for(Part part:old)for(int z=0;z<2;z++)s.parts.add(new Part(part.x,part.y,part.z*2+z,part.state));
                }
            }
        }
        // Always keep the cockpit area clear.
        cockpit(s);
        // A map keyed by position keeps only one part per cell.
        // Merge shared cells while retaining unrestricted addition of distinct components.
        Map<BlockPos,Part> merged=new LinkedHashMap<>();for(Part part:s.parts)merged.put(new BlockPos(part.x,part.y,part.z),part);s.parts.clear();s.parts.addAll(merged.values());
        // Give the spacesuit tag, set the quest step, and save.
        p.addTag("spain.suit");command(p,"scoreboard players set @s spain.launch 3");save(server);
        // Tell the player the block count.
        message(p,"Rocket creator: "+s.parts.size()+" blocks. Add parts as often as you like. Board when ready.");
        // Reopen the creator menu.
        command(p,"dialog show @s spain:creator");return 1;
    }
    /** How far the chase camera sits behind the ship: at least 10 blocks, more for wide ships. */
    private float cameraDistance(Ship s) {return (float)Math.max(10,s.parts.stream().mapToDouble(part->Math.sqrt(part.x*part.x+part.z*part.z)).max().orElse(4)+7);}
    /** Starts an avatar scan of the player's selected box. Returns 1 if started, 0 if no valid selection. */
    public int captureAvatar(ServerPlayer p) {
        server=p.level().getServer();Selection sel=selections.get(p.getUUID());
        if(sel==null||!dimension(p).equals(sel.dimension)) {message(p,"Select your creation with /spain corner1 and corner2 first.");return 0;}
        // Queue the scan; tick() will run it a slice at a time.
        Scan scan=new Scan(p,sel);scan.avatar=true;scans.put(p.getUUID(),scan);return 1;
    }
    /** Finds a world by name, e.g. "spain:orbit". */
    private ServerLevel world(String id) {return server.getLevel(ResourceKey.create(Registries.DIMENSION,Identifier.parse(id)));}
    /** The name of the world the player is currently in. */
    private String dimension(ServerPlayer p) {return p.level().dimension().identifier().toString();}
    /** Sends a chat message to one player. */
    private void message(ServerPlayer p,String text) {p.sendSystemMessage(Component.literal(text));}
    /** Runs a Minecraft command as the given player, with its output hidden. */
    private void command(ServerPlayer p,String text) {server.getCommands().performPrefixedCommand(server.createCommandSourceStack().withEntity(p).withLevel(p.level()).withPosition(p.position()).withSuppressedOutput(),text);}
    /** Remembers corner 1 or 2 of the blueprint box for this player. */
    public void corner(ServerPlayer p,int n,BlockPos pos) {
        Selection old=selections.get(p.getUUID());
        if(old==null||!old.dimension.equals(dimension(p))) old=new Selection(dimension(p),pos,pos);
        selections.put(p.getUUID(),new Selection(dimension(p),n==1?pos:old.a,n==2?pos:old.b));
        message(p,"Blueprint corner "+n+": "+pos.toShortString()+". /spain capture scans without a part-count cap.");
    }
    /** Handles /spain actions: capture, board, land, help, create, recall, spore. Returns 1 for the command system. */
    public int action(ServerPlayer p,String action) {
        server=p.level().getServer();
        Ship ship=ships.get(p.getUUID());
        switch(action) {
            // Start scanning the selected box into a ship.
            case "capture" -> {
                // Only one scan at a time per player.
                if(scans.containsKey(p.getUUID())) {message(p,"Blueprint scan is already running.");break;}
                // Use the player's box, or the default workshop area if none was chosen.
                Selection sel=selections.getOrDefault(p.getUUID(),new Selection("minecraft:overworld",new BlockPos(8,97,-8),new BlockPos(20,103,7)));
                // The box must be in the world the player is standing in.
                if(!dimension(p).equals(sel.dimension)) {message(p,"Visit your workshop or select two corners in this world.");break;}
                // Sort the corners into a minimum and maximum corner.
                // Coordinate range is vanilla's world boundary; there is no design part budget.
                BlockPos a=new BlockPos(Math.min(sel.a.getX(),sel.b.getX()),Math.min(sel.a.getY(),sel.b.getY()),Math.min(sel.a.getZ(),sel.b.getZ()));
                BlockPos b=new BlockPos(Math.max(sel.a.getX(),sel.b.getX()),Math.max(sel.a.getY(),sel.b.getY()),Math.max(sel.a.getZ(),sel.b.getZ()));
                // Reject boxes outside the world height or the world border.
                if(a.getY()<p.level().getMinY()||b.getY()>=p.level().getMaxY()||Math.abs((long)a.getX())>29999984||Math.abs((long)b.getX())>29999984||Math.abs((long)a.getZ())>29999984||Math.abs((long)b.getZ())>29999984) {message(p,"Selection exceeds Minecraft's world boundary.");break;}
                // Begin the scan.
                scans.put(p.getUUID(),new Scan(p,new Selection(sel.dimension,a,b)));message(p,"Scanning your design…");
            }
            // Get into the ship and start flying.
            case "board" -> {
                if(ship==null||ship.parts.isEmpty()) {message(p,"Open /spain create or capture a design first.");break;}
                if(ship.piloting) break;
                // Lift the player slightly so they do not start inside blocks.
                p.teleportTo(p.getX(),p.getY()+2,p.getZ());
                // The ship now follows the player.
                ship.dimension=dimension(p);ship.anchor=p.position();ship.piloting=true;
                // Remember normal flight settings to restore on landing.
                ship.originalMayfly=p.getAbilities().mayfly;ship.originalSpeed=p.getAbilities().getFlyingSpeed();
                // Tag the player as a pilot and turn on flight.
                p.addTag("spain.pilot");p.addTag("spain.suit");enableFlight(p);
                // Tell the client to switch to the chase camera.
                view.accept(p,new FlightView(true,cameraDistance(ship)));
                message(p,"Freeflight: WASD, Space up, Shift down. /spain land disembarks. Galaxy Guide switches to quick travel anytime.");
            }
            // Leave the ship and restore normal abilities.
            case "land" -> {if(ship!=null&&ship.piloting) {unboard(p,ship);message(p,"Disembarked. Your ship settles without damage and floats on water.");save(server);}}
            // Show the help dialog.
            case "help" -> command(p,"dialog show @s spain:rocket");
            // Show the rocket creator dialog.
            case "create" -> command(p,"dialog show @s spain:creator");
            // Teleport the player next to their parked ship.
            case "recall" -> {if(ship!=null){p.teleportTo(world(ship.dimension),ship.anchor.x,ship.anchor.y+1,ship.anchor.z,Set.of(),p.getYRot(),p.getXRot(),false);message(p,"You are beside your rocket. Board whenever you like.");}}
            // Place the imported Spore hull structure beside the workshop (Earth only).
            case "spore" -> {
                if(!dimension(p).equals("minecraft:overworld")) {message(p,"Return to the Earth workshop to add parts.");break;}
                command(p,"place template spain:imported/spore_rocket 14 97 -5");
                message(p,"The local imported hull appears beside the workshop when installed. Select its corners to include it in your blueprint.");
            }
        }
        return 1;
    }
    /** Reads a player's scoreboard value, or 0 if the objective does not exist. */
    private int score(ServerPlayer p,String objective) {
        var obj=server.getScoreboard().getObjective(objective);if(obj==null)return 0;
        var s=server.getScoreboard().getPlayerScoreInfo(p,obj);return s==null?0:s.value();
    }
    /** Lets the player fly at the ship's speed and cancels fall damage. */
    private void enableFlight(ServerPlayer p) {
        p.getAbilities().mayfly=true;p.getAbilities().flying=true;p.getAbilities().setFlyingSpeed(.13f);p.onUpdateAbilities();p.resetFallDistance();
    }
    /** Stops piloting: restores the player's old flight settings and the normal camera. */
    private void unboard(ServerPlayer p,Ship s) {
        s.piloting=false;p.entityTags().remove("spain.pilot");
        p.getAbilities().mayfly=s.originalMayfly||p.gameMode().isCreative();
        p.getAbilities().flying=p.gameMode().isCreative();p.getAbilities().setFlyingSpeed(s.originalSpeed);p.onUpdateAbilities();p.resetFallDistance();
        view.accept(p,new FlightView(false,4));
    }
    /** Runs every server tick: advances scans, handles requests and flight, settles parked ships and saves periodically. */
    public void tick(MinecraftServer server) {
        this.server=server;ticks++;
        // Run one slice of every scan; remove finished ones.
        scans.entrySet().removeIf(e -> e.getValue().step());
        // Handle each online player.
        for(ServerPlayer p:server.getPlayerList().getPlayers()) {
            // First time we see a player after startup: clear a stale pilot tag from a previous session.
            if(connected.add(p.getUUID())&&p.entityTags().contains("spain.pilot")) {
                p.entityTags().remove("spain.pilot");
                p.getAbilities().mayfly=p.gameMode().isCreative();p.getAbilities().flying=false;
                p.getAbilities().setFlyingSpeed(.05f);p.onUpdateAbilities();
            }
            // Menu buttons set tags like spain.request.board; turn each tag into the real action.
            for(String action:new String[]{"capture","board","land","spore","recall","create"}) if(p.entityTags().remove("spain.request."+action)) action(p,action);
            // The spacesuit refills air except underwater.
            if(p.entityTags().contains("spain.suit")&&!p.isUnderWater()) p.setAirSupply(p.getMaxAirSupply());
            // Arriving at the station dock the first time completes the flight test.
            if(dimension(p).equals("spain:orbit")&&p.getY()>=64&&p.getY()<72&&Math.abs(p.getX())<17&&Math.abs(p.getZ())<17&&score(p,"spain.launch")>=3&&!p.entityTags().contains("spain.test_complete")) {
                message(p,"Dock workers: Welcome to the world of endless possibility!");command(p,"function spain:quest/arrival");
            }
            // Skip players without a ship.
            Ship s=ships.get(p.getUUID());if(s==null)continue;
            // Flying: keep flight on and handle leaving or entering space.
            if(s.piloting) {
                // If the pilot died, drop out of the ship.
                if(!p.isAlive()) {unboard(p,s);continue;}
                enableFlight(p);
                // Above Y 280 on Earth you go to orbit; below Y 40 in orbit you return to Earth.
                boolean inOrbit=dimension(p).equals("spain:orbit");
                if(!inOrbit&&p.getY()>280) {
                    ServerLevel orbit=world("spain:orbit");
                    if(orbit!=null) p.teleportTo(orbit,0.5,95,30.5,Set.of(),180,0,false);
                    message(p,"Gravity fades. Space is yours. Fly to the station at X 0, Y 65, Z 0, or open the Galaxy Guide.");
                } else if(inOrbit&&p.getY()<40) {
                    ServerLevel earth=world("minecraft:overworld");p.teleportTo(earth,.5,265,.5,Set.of(),p.getYRot(),p.getXRot(),false);
                    message(p,"Entering Earth's gravity field.");
                }
                // If the player changed worlds (for example by quick travel), rebuild the displays there.
                String now=dimension(p);
                if(!now.equals(s.dimension)) {clearDisplays(s);s.dimension=now;}
                // The ship follows the pilot.
                // Cockpit sits above the lower hull; one Minecraft block remains one part.
                s.anchor=p.position();s.yaw=p.getYRot();s.velocity=0;
            } else {
                // Parked (not piloting): only handle ships in the player's current world, then apply gravity and buoyancy.
                if(!dimension(p).equals(s.dimension)) continue;
                settle(s);
            }
            // Only draw ships within 256 blocks.
            if(p.position().distanceToSqr(s.anchor)<256*256) render(s);
        }
        // Forget players who went offline.
        connected.removeIf(id -> server.getPlayerList().getPlayer(id)==null);
        // Loop over ships whose owners are offline.
        // Offline ships also settle. No damage system or health pool exists for ships.
        for(var e:ships.entrySet()) if(server.getPlayerList().getPlayer(e.getKey())==null) {
            Ship s=e.getValue();s.piloting=false;ServerLevel level=world(s.dimension);
            if(level!=null&&level.hasChunkAt(BlockPos.containing(s.anchor))) {settle(s);render(s);}
        }
        // Autosave about every 5 seconds (100 ticks).
        if(ticks%100==0)save(server);
    }
    /** Moves a parked ship one tick: it falls, or floats up in water, stopping at solid blocks. */
    public void settle(Ship s) {
        ServerLevel level=world(s.dimension);if(level==null||!level.hasChunkAt(BlockPos.containing(s.anchor)))return;
        // First check whether any part is in water.
        // Every occupied cell participates, allowing tree tips, mountain peaks and ceilings.
        double move=0;boolean water=false;
        for(Part part:s.parts) if(level.getFluidState(BlockPos.containing(partPosition(s,part))).is(FluidTags.WATER)) {water=true;break;}
        // In water the ship rises at a steady speed; otherwise gravity speeds up the fall to a limit.
        if(water) {s.velocity=0;move=.20;}
        else {s.velocity=Math.max(-.8,s.velocity-.04);move=s.velocity;}
        // allowed = how far the ship may move before a part hits a block.
        double allowed=move;
        // Half the width of a part cell, adjusted for rotation.
        double half=(Math.abs(Math.cos(Math.toRadians(s.yaw)))+Math.abs(Math.sin(Math.toRadians(s.yaw))))*.5;
        for(Part part:s.parts) {
            // Check each part's box against the terrain and take the strictest limit.
            Vec3 position=partPosition(s,part);
            var cell=new net.minecraft.world.phys.AABB(position.x+.5-half+.01,position.y,position.z+.5-half+.01,position.x+.5+half-.01,position.y+1,position.z+.5+half-.01);
            Vec3 clipped=net.minecraft.world.entity.Entity.collideBoundingBox(net.minecraft.world.phys.shapes.CollisionContext.empty(),new Vec3(0,move,0),cell,level,List.of());
            allowed=move<0?Math.max(allowed,clipped.y):Math.min(allowed,clipped.y);
        }
        // Stopped by something solid: reset speed.
        if(Math.abs(allowed)<.0001)s.velocity=0;
        // Apply the allowed movement.
        s.anchor=s.anchor.add(0,allowed,0);
    }
    /** World position of one part: rotate its offset by the ship yaw, then add the anchor. */
    private Vec3 partPosition(Ship ship,Part part) {
        double angle=Math.toRadians(ship.yaw),c=Math.cos(angle),s=Math.sin(angle);
        return ship.anchor.add(c*part.x-s*part.z,part.y,s*part.x+c*part.z);
    }
    /** Creates or updates the block display entities that draw the ship. */
    private void render(Ship s) {
        ServerLevel level=world(s.dimension);if(level==null)return;
        // Rebuild all displays if the count changed or any was removed.
        if(s.displays.size()!=s.parts.size()||s.displays.stream().anyMatch(e -> e.isRemoved())) {
            clearDisplays(s);
            for(Part part:s.parts) {
                // Anonymous subclass that refuses to be saved, so displays never persist in the world.
                Display.BlockDisplay display=new Display.BlockDisplay(EntityTypes.BLOCK_DISPLAY,level) {
                    @Override public boolean shouldBeSaved() {return false;}
                };
                // Build the entity data: block type, smooth movement time and view range.
                CompoundTag tag=new CompoundTag();
                tag.put("block_state",BlockState.CODEC.encodeStart(NbtOps.INSTANCE,part.state).getOrThrow());
                tag.putInt("teleport_duration",1);tag.putFloat("view_range",4);
                // Apply the data to the entity.
                display.load(TagValueInput.create(ProblemReporter.DISCARDING,level.registryAccess(),tag));
                // Tag it so it can be found and removed later, then place and spawn it.
                display.addTag("spain.ship_display");display.setNoGravity(true);display.setPos(partPosition(s,part));display.setYRot(s.yaw);
                level.addFreshEntity(display);s.displays.add(display);
            }
        }
        // Move every display to match the ship's current position and facing.
        for(int i=0;i<s.parts.size();i++) {Part part=s.parts.get(i);s.displays.get(i).setPos(partPosition(s,part));s.displays.get(i).setYRot(s.yaw);}
    }
    /** Removes all of a ship's display entities. */
    private void clearDisplays(Ship s) {for(var e:s.displays)e.discard();s.displays.clear();}
    /** Location of the ship save file inside the world folder. */
    private Path path(MinecraftServer server) {return server.getWorldPath(LevelResource.ROOT).resolve("spain-ships.json");}
    /** Writes every ship to spain-ships.json (via a temp file so a crash cannot leave a half-written save). */
    public void save(MinecraftServer server) {
        if(server==null)return;
        // Top-level JSON object with a version number and an array of ships.
        JsonObject root=new JsonObject();root.addProperty("version",1);
        JsonArray array=new JsonArray();
        // Write each ship: owner id, world, facing, anchor and parts.
        for(var e:ships.entrySet()) {
            Ship s=e.getValue();JsonObject ship=new JsonObject();ship.addProperty("owner",e.getKey().toString());ship.addProperty("dimension",s.dimension);
            ship.addProperty("yaw",s.yaw);
            ship.add("anchor",gson.toJsonTree(new double[]{s.anchor.x,s.anchor.y,s.anchor.z}));
            JsonArray parts=new JsonArray();
            for(Part p:s.parts) {JsonObject part=new JsonObject();part.addProperty("x",p.x);part.addProperty("y",p.y);part.addProperty("z",p.z);part.add("state",BlockState.CODEC.encodeStart(JsonOps.INSTANCE,p.state).getOrThrow());parts.add(part);}ship.add("parts",parts);array.add(ship);
        }
        // Write to a temp file, then move it over the real file in one step.
        root.add("ships",array);
        try {Path file=path(server),temp=file.resolveSibling("spain-ships.json.tmp");Files.writeString(temp,gson.toJson(root));Files.move(temp,file,StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);}
        catch(Exception e) {throw new IllegalStateException("Could not save Spain ships",e);}
    }
    /** Reads the ships save file when the server starts. */
    public void load(MinecraftServer server) {
        // Start from a clean state.
        this.server=server;ships.clear();scans.clear();selections.clear();connected.clear();
        // Remove any leftover display entities from earlier runs.
        // Displays are disposable render proxies; blueprints are the authoritative save.
        for(ServerLevel level:server.getAllLevels()) for(var e:java.util.stream.StreamSupport.stream(level.getAllEntities().spliterator(),false).filter(Objects::nonNull).toList()) if(e.entityTags().contains("spain.ship_display"))e.discard();
        // No save yet: nothing to load.
        Path file=path(server);if(!Files.exists(file))return;
        try {
            // Read each saved ship back into memory.
            JsonObject root=JsonParser.parseString(Files.readString(file)).getAsJsonObject();
            for(JsonElement item:root.getAsJsonArray("ships")) {
                JsonObject value=item.getAsJsonObject();Ship s=new Ship();s.dimension=value.get("dimension").getAsString();
                s.yaw=value.has("yaw")?value.get("yaw").getAsFloat():0;
                JsonArray anchor=value.getAsJsonArray("anchor");s.anchor=new Vec3(anchor.get(0).getAsDouble(),anchor.get(1).getAsDouble(),anchor.get(2).getAsDouble());
                for(JsonElement element:value.getAsJsonArray("parts")) {JsonObject p=element.getAsJsonObject();s.parts.add(new Part(p.get("x").getAsInt(),p.get("y").getAsInt(),p.get("z").getAsInt(),BlockState.CODEC.parse(JsonOps.INSTANCE,p.get("state")).getOrThrow()));}
                ships.put(UUID.fromString(value.get("owner").getAsString()),s);
            }
        // On a bad file, fail loudly instead of overwriting it.
        } catch(Exception e) {throw new IllegalStateException("Could not read Spain ship save; preserved original file",e);}
    }
}
