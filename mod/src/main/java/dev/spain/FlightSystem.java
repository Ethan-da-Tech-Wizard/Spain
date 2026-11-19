// ==============================================================================
// Program: FlightSystem.java
// Programmer: Ethan-da-Tech-Wizard
// Last Modified: November 19, 2026
// Purpose: Rocket ships for the Spain mod: captures player-built blocks (or assembles prefab
//          parts in the rocket creator) into a ship, shows it as block-display entities,
//          lets the owner fly it with creative-style flight, moves pilots between Earth and
//          space, settles parked ships onto terrain or water, and saves ships per world.
// ==============================================================================

// Fit in the mod: the heart of the mod, one instance shared through SpainMod.FLIGHT. SpainMod calls load() when
// the server starts, tick() after every server tick and save() on shutdown, and the /spain commands call design(),
// action(), corner() and captureAvatar(). The data pack (tools/extend_pack.py) triggers the same actions by giving a
// player tags named "spain.request.<action>", which tick() consumes. verification/MinecraftChecks.java drives this
// class directly in a real server to prove each behaviour listed below.
// //
// What a "ship" is: a list of blocks (Part: offset x,y,z from the ship's anchor plus a BlockState) owned by one player.
// It is shown to everybody as Display.BlockDisplay entities (render()), not as real blocks, so it can move
// without touching the world. A ship is created either by scanning blocks the player built (capture, with a
// per-tick budget, see Scan) or by assembling prefab parts in the rocket creator (design). While the player
// is "piloting", they simply use Minecraft's creative-style flight (WASD, Space, Shift); the ship follows
// the player's position and yaw. This is intentionally NOT a physics simulation: there is no thrust, drag or
// orbital mechanics. Only a parked ship uses a tiny physics step (settle): gravity, water buoyancy and
// collision against blocks, so ships rest on the ground and float on water.
// //
// Planet and space transitions: a piloting player above y=280 on Earth is moved to the spain:orbit
// dimension, and a player below y=40 in orbit is moved back to Earth (see tick).
// //
// Persistence: ships are stored as JSON in <world>/spain-ships.json (save/load), written atomically, saved
// every 100 ticks (5 s) and on shutdown. Display entities are never saved; they are discarded on load and
// rebuilt from the blueprint. The blueprint (parts), not the entities, is the source of truth.
// //
// Threading: everything runs on the server thread (tick and command handlers), so no locking is used.
// Limits: one ship per player; the `server` field is set from whichever entry point is called first.
package dev.spain;

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

// (Class-level notes are in the header comment above; fields below explain the per-player state.)
/** Native block-display ships. Minecraft remains responsible for player movement and terrain. */
public final class FlightSystem {
    // One block of a ship: integer offset from the ship's anchor (x east, y up, z south, before yaw) and the block it looks like.
    public record Part(int x,int y,int z,BlockState state) {}

    // /** All state of one player's ship. Public so MinecraftChecks can build one for physics tests. */
    public static final class Ship {
        // The blueprint: authoritative and saved to disk.
        public final List<Part> parts=new ArrayList<>();

        // Live render entities, one per part, in the same order as `parts`. Never saved.
        public final List<Display.BlockDisplay> displays=new ArrayList<>();

        // Dimension id where the ship currently is, as text ("minecraft:overworld", "spain:orbit" ...).
        public String dimension="minecraft:overworld";

        // World position of the ship's origin; parts are placed relative to it. Default is the Earth launch pad.
        public Vec3 anchor=new Vec3(9,97,1);

        // True while the owner is flying it. A piloted ship follows the player; a parked one settles to the ground.
        public boolean piloting;

        // Heading in degrees. The creator's "rotate" adds 90; while piloting it copies the player's yaw.
        public float yaw;

        // The player's own flying speed and fly permission before boarding, restored by unboard() so survival players do not keep flight afterwards.
        float originalSpeed=.05f;
        boolean originalMayfly;

        // Vertical speed of a parked ship in blocks per tick (negative = falling); used only by settle().
        double velocity;
    }

    // A blueprint box chosen with /spain corner1 and corner2 (two opposite corners, in one dimension).
    private record Selection(String dimension,BlockPos a,BlockPos b) {}

    // Per-player state, keyed by player UUID: ships, chosen blueprint boxes, running scans, players seen
    // since the last tick (to clean up a pilot tag left over from a crash) and undo history for the creator.
    private final Map<UUID,Ship> ships=new HashMap<>();
    private final Map<UUID,Selection> selections=new HashMap<>();
    private final Map<UUID,Scan> scans=new HashMap<>();
    private final Set<UUID> connected=new HashSet<>();
    private final Map<UUID,Deque<List<Part>>> history=new HashMap<>();

    // Hook to send the camera packet; replaced by SpainMod. The default does nothing, so the class also works without networking (as in the test probe).
    public java.util.function.BiConsumer<ServerPlayer,FlightView> view=(player,payload)->{};
    private MinecraftServer server;

    // Counts server ticks; used to save every 100 ticks.
    private int ticks;

    // Gson writes the save file; pretty printing keeps it readable and diff-able.
    private final Gson gson=new GsonBuilder().setPrettyPrinting().create();

    // A blueprint scan that runs over several ticks. Scanning a big box in one tick would freeze the
    // server, so step() reads up to 1024 blocks per tick. The scan has no part limit, only that budget.
    private class Scan {
        final ServerPlayer player; final Ship ship=new Ship(); final Selection selection;
        boolean avatar;
        final Iterator<BlockPos> positions;
        Scan(ServerPlayer p,Selection s) {
            player=p;selection=s;positions=BlockPos.betweenClosed(s.a,s.b).iterator();
            ship.dimension=s.dimension;ship.anchor=new Vec3(s.a.getX(),s.a.getY(),s.a.getZ());
        }

        // Returns true when finished (removed from `scans` by tick()). Collects every non-air, non-fluid block as a
        // Part relative to the box's minimum corner a. On finish: either save the result as the player's block-creature
        // avatar, or replace the player's ship with it.
        boolean step() {
            ServerLevel level=world(selection.dimension);

            // The 1024 blocks-per-tick budget (about 20,000 blocks per second).
            for(int i=0;i<1024&&positions.hasNext();i++) {
                BlockPos p=positions.next(); BlockState state=level.getBlockState(p);

                // Air and fluids are skipped, so water or lava in the box does not become part of the rocket.
                if(!state.isAir()&&state.getFluidState().isEmpty()) ship.parts.add(new Part(p.getX()-selection.a.getX(),p.getY()-selection.a.getY(),p.getZ()-selection.a.getZ(),state));
            }
            if(positions.hasNext()) return false;
            if(ship.parts.isEmpty()) {message(player,"The selection is empty. Build your rocket first.");return true;}
            if(avatar) {SpainMod.VISUALS.custom(player,ship.parts);message(player,"Created your own block creature. Press F5 to preview it.");return true;}
            Ship previous=ships.get(player.getUUID());
            if(previous!=null) {if(previous.piloting) unboard(player,previous);clearDisplays(previous);}

            // The scan copies; the original build stays in the world so the player can keep editing it and capture again.
            // Blueprints leave the workshop intact. A landed craft is an invulnerable projection.
            center(ship);
            ships.put(player.getUUID(),ship);

            // Place the captured ship 4 blocks east of the player, beside the workshop.
            ship.anchor=player.position().add(4,0,0);

            // Launch score 3 means "has a ship"; the arrival check in tick() requires it, and the quest functions in the pack read it.
            command(player,"scoreboard players set @s spain.launch 3");
            save(server);message(player,"Captured "+ship.parts.size()+" parts. Board to fly. Your workshop remains editable.");
            return true;
        }
    }

    // Accessor for the player's ship (null if none); used by tests.
    public Ship ship(ServerPlayer player) {return ships.get(player.getUUID());}

    // Shift all parts so the ship is centred on the x/z axes (y stays), using the middle of the min and max. After this the anchor is the middle of the ship, which keeps rotation about the centre.
    private void center(Ship ship) {
        int x=(ship.parts.stream().mapToInt(Part::x).min().orElse(0)+ship.parts.stream().mapToInt(Part::x).max().orElse(0))/2;
        int z=(ship.parts.stream().mapToInt(Part::z).min().orElse(0)+ship.parts.stream().mapToInt(Part::z).max().orElse(0))/2;
        var copy=ship.parts.stream().map(p->new Part(p.x-x,p.y,p.z-z,p.state)).toList();ship.parts.clear();ship.parts.addAll(copy);
    }

    // Load a prefab part (spore_rocket or spore_thruster) from the mod's own resources: /assets/spain/<name>.voxels.json is written by
    // tools/import_spore.py and bundled by tools/build_mod.py. Returns an empty list if the file is not
    // installed (local-only art); callers then fall back to simple built-in shapes. A corrupt file is a bug, so it throws.
    private List<Part> model(String name) {
        try(var input=getClass().getResourceAsStream("/assets/spain/"+name+".voxels.json")) {
            if(input==null)return List.of();
            var json=JsonParser.parseString(new String(input.readAllBytes(),java.nio.charset.StandardCharsets.UTF_8)).getAsJsonObject();
            Ship s=new Ship();
            for(var element:json.getAsJsonArray("parts")) {var p=element.getAsJsonObject();s.parts.add(new Part(p.get("x").getAsInt(),p.get("y").getAsInt(),p.get("z").getAsInt(),net.minecraft.core.registries.BuiltInRegistries.BLOCK.getValue(Identifier.withDefaultNamespace(p.get("block").getAsString())).defaultBlockState()));}
            center(s);return s.parts;
        } catch(Exception e) {throw new IllegalStateException("Cannot load rocket creator part "+name,e);}
    }

    // Look up a vanilla block by name (without "minecraft:") and return its default state.
    private BlockState block(String id){return net.minecraft.core.registries.BuiltInRegistries.BLOCK.getValue(Identifier.withDefaultNamespace(id)).defaultBlockState();}

    // Remove the 3x3 column x,z in -1..1 and y 0..2 so the player always has an empty cockpit space at the ship's centre.
    private void cockpit(Ship s) {s.parts.removeIf(p->Math.abs(p.x)<=1&&Math.abs(p.z)<=1&&p.y>=0&&p.y<=2);}

    // The rocket creator: apply one editing action to the player's ship and re-show the creator dialog.
    // choice is one of hull, wings, engine, cabin, stretch, rotate, undo, clear (the same list /spain design offers).
    // Returns 1 for the command system. Every edit first pushes the old parts on an undo stack.
    public int design(ServerPlayer p,String choice) {
        server=p.level().getServer();Ship s=ships.computeIfAbsent(p.getUUID(),id->new Ship());
        if(s.piloting)unboard(p,s);
        clearDisplays(s);s.dimension=dimension(p);s.anchor=p.position().add(0,0,7);
        var undo=history.computeIfAbsent(p.getUUID(),id->new ArrayDeque<>());

        // Undo restores the previous part list (unbounded history for this session; it is not saved).
        if(choice.equals("undo")) {if(!undo.isEmpty()){s.parts.clear();s.parts.addAll(undo.pop());}}
        else {
            undo.push(List.copyOf(s.parts));

            // reach = widest x so far, front = highest z so far; new wings and hulls are placed relative to these so parts attach next to what exists instead of overlapping.
            int reach=s.parts.stream().mapToInt(part->Math.abs(part.x)).max().orElse(3);
            int front=s.parts.stream().mapToInt(Part::z).max().orElse(0);
            switch(choice) {
                case "clear" -> s.parts.clear();
                case "rotate" -> s.yaw+=90;

                // Hull: the imported Spore rocket mesh if installed, else a flat cyan plate. A second hull is put 5 blocks in front of the existing ones.
                case "hull" -> {
                    var hull=model("spore_rocket");int offset=s.parts.isEmpty()?0:front+5;
                    if(hull.isEmpty()) {
                        for(int x=-3;x<=3;x++)for(int z=-4;z<=4;z++)if(Math.abs(x)+Math.abs(z)<=6)s.parts.add(new Part(x,0,z+offset,block("cyan_concrete")));
                    } else {
                        for(Part part:hull)s.parts.add(new Part(part.x,part.y,part.z+offset,part.state));
                    }
                }

                // Engine: placed behind the last part (z minimum minus 3), using the Spore thruster if present, else a magma block, plus one magma block exhaust.
                case "engine" -> {
                    int back=s.parts.stream().mapToInt(Part::z).min().orElse(0)-3;
                    var engine=model("spore_thruster");
                    if(engine.isEmpty())s.parts.add(new Part(0,0,back,block("magma_block")));
                    else for(Part part:engine)s.parts.add(new Part(part.x,part.y,part.z+back,part.state));
                    s.parts.add(new Part(0,1,back-3,block("magma_block")));
                }

                // Wings: two symmetric triangular slabs (mirror via side = -1 and +1), 4 blocks out from the current widest point; the outer edge is cyan.
                case "wings" -> {
                    for(int side:new int[]{-1,1})for(int x=1;x<=4;x++)for(int z=-2;z<=2;z++)if(x+Math.abs(z)<=5)s.parts.add(new Part(side*(reach+x),0,z,block(x==4?"cyan_concrete":"white_concrete")));
                }

                // Cabin: a 5x5 room, 3 blocks tall, with light-blue glass walls and a white-concrete roof, centred on the ship.
                case "cabin" -> {
                    for(int x=-2;x<=2;x++)for(int z=-2;z<=2;z++)for(int y=1;y<=3;y++)if(Math.abs(x)==2||Math.abs(z)==2||y==3)s.parts.add(new Part(x,y,z,block(y==3?"white_concrete":"light_blue_stained_glass")));
                }

                // Stretch: double the length by duplicating each block along z, keeping the shape (every old block becomes two).
                case "stretch" -> {
                    var old=List.copyOf(s.parts);s.parts.clear();for(Part part:old)for(int z=0;z<2;z++)s.parts.add(new Part(part.x,part.y,part.z*2+z,part.state));
                }
            }
        }

        // Always clear the cockpit after an edit, even if a new part overlapped it.
        cockpit(s);

        // Parts that landed in the same cell collapse to one (the last wins); different cells are unlimited.
        // Merge shared cells while retaining unrestricted addition of distinct components.
        Map<BlockPos,Part> merged=new LinkedHashMap<>();for(Part part:s.parts)merged.put(new BlockPos(part.x,part.y,part.z),part);s.parts.clear();s.parts.addAll(merged.values());

        // Using the creator grants the spacesuit tag (infinite air outside water, see tick) and marks the player as having a ship.
        p.addTag("spain.suit");command(p,"scoreboard players set @s spain.launch 3");save(server);
        message(p,"Rocket creator: "+s.parts.size()+" blocks. Add parts as often as you like. Board when ready.");
        command(p,"dialog show @s spain:creator");return 1;
    }

    // Chase-camera distance: the ship's radius in the horizontal plane plus 7 blocks, never below 10, so large rockets stay in view.
    private float cameraDistance(Ship s) {return (float)Math.max(10,s.parts.stream().mapToDouble(part->Math.sqrt(part.x*part.x+part.z*part.z)).max().orElse(4)+7);}

    // /spain avatar capture: scan the selected box into a creature avatar instead of a ship. Needs both corners first.
    public int captureAvatar(ServerPlayer p) {
        server=p.level().getServer();Selection sel=selections.get(p.getUUID());
        if(sel==null||!dimension(p).equals(sel.dimension)) {message(p,"Select your creation with /spain corner1 and corner2 first.");return 0;}
        Scan scan=new Scan(p,sel);scan.avatar=true;scans.put(p.getUUID(),scan);return 1;
    }

    // Helpers: dimension id -> level, current dimension id, chat message to one player, run a command as the player with output suppressed.
    private ServerLevel world(String id) {return server.getLevel(ResourceKey.create(Registries.DIMENSION,Identifier.parse(id)));}
    private String dimension(ServerPlayer p) {return p.level().dimension().identifier().toString();}
    private void message(ServerPlayer p,String text) {p.sendSystemMessage(Component.literal(text));}
    private void command(ServerPlayer p,String text) {server.getCommands().performPrefixedCommand(server.createCommandSourceStack().withEntity(p).withLevel(p.level()).withPosition(p.position()).withSuppressedOutput(),text);}

    // Remember corner n (1 or 2) of the blueprint box. A selection from another dimension is dropped and restarted.
    public void corner(ServerPlayer p,int n,BlockPos pos) {
        Selection old=selections.get(p.getUUID());
        if(old==null||!old.dimension.equals(dimension(p))) old=new Selection(dimension(p),pos,pos);
        selections.put(p.getUUID(),new Selection(dimension(p),n==1?pos:old.a,n==2?pos:old.b));
        message(p,"Blueprint corner "+n+": "+pos.toShortString()+". /spain capture scans without a part-count cap.");
    }

    // Perform one player action; this is the single place both commands and pack-set request tags end up. Actions:
    // capture (scan the blueprint), board, land, help, create (dialogs), recall (teleport the player to their ship) and spore (place the imported hull template).
    public int action(ServerPlayer p,String action) {
        server=p.level().getServer();
        Ship ship=ships.get(p.getUUID());
        switch(action) {
            // Capture scans the chosen box, or the default workshop box on Earth's east pad (x 8..20, y 97..103, z -8..7). Corners
            // are sorted into min/max, then checked against the world's height limits and the 30,000,000 block border before a scan starts.
            case "capture" -> {
                if(scans.containsKey(p.getUUID())) {message(p,"Blueprint scan is already running.");break;}
                Selection sel=selections.getOrDefault(p.getUUID(),new Selection("minecraft:overworld",new BlockPos(8,97,-8),new BlockPos(20,103,7)));
                if(!dimension(p).equals(sel.dimension)) {message(p,"Visit your workshop or select two corners in this world.");break;}
                // Coordinate range is vanilla's world boundary; there is no design part budget.
                BlockPos a=new BlockPos(Math.min(sel.a.getX(),sel.b.getX()),Math.min(sel.a.getY(),sel.b.getY()),Math.min(sel.a.getZ(),sel.b.getZ()));
                BlockPos b=new BlockPos(Math.max(sel.a.getX(),sel.b.getX()),Math.max(sel.a.getY(),sel.b.getY()),Math.max(sel.a.getZ(),sel.b.getZ()));
                if(a.getY()<p.level().getMinY()||b.getY()>=p.level().getMaxY()||Math.abs((long)a.getX())>29999984||Math.abs((long)b.getX())>29999984||Math.abs((long)a.getZ())>29999984||Math.abs((long)b.getZ())>29999984) {message(p,"Selection exceeds Minecraft's world boundary.");break;}
                scans.put(p.getUUID(),new Scan(p,new Selection(sel.dimension,a,b)));message(p,"Scanning your design…");
            }

            // Board: lift the player 2 blocks (so they are not stuck on the ground), remember their original flight permissions, enable flight, tag them as pilot and suit-wearer, and send the chase-camera packet.
            case "board" -> {
                if(ship==null||ship.parts.isEmpty()) {message(p,"Open /spain create or capture a design first.");break;}
                if(ship.piloting) break;
                p.teleportTo(p.getX(),p.getY()+2,p.getZ());
                ship.dimension=dimension(p);ship.anchor=p.position();ship.piloting=true;
                ship.originalMayfly=p.getAbilities().mayfly;ship.originalSpeed=p.getAbilities().getFlyingSpeed();
                p.addTag("spain.pilot");p.addTag("spain.suit");enableFlight(p);
                view.accept(p,new FlightView(true,cameraDistance(ship)));
                message(p,"Freeflight: WASD, Space up, Shift down. /spain land disembarks. Galaxy Guide switches to quick travel anytime.");
            }

            // Land: leave the cockpit; the ship stays where it is and will settle.
            case "land" -> {if(ship!=null&&ship.piloting) {unboard(p,ship);message(p,"Disembarked. Your ship settles without damage and floats on water.");save(server);}}
            case "help" -> command(p,"dialog show @s spain:rocket");
            case "create" -> command(p,"dialog show @s spain:creator");

            // Recall: teleport the player next to their ship, even across dimensions.
            case "recall" -> {if(ship!=null){p.teleportTo(world(ship.dimension),ship.anchor.x,ship.anchor.y+1,ship.anchor.z,Set.of(),p.getYRot(),p.getXRot(),false);message(p,"You are beside your rocket. Board whenever you like.");}}
            case "spore" -> {
                if(!dimension(p).equals("minecraft:overworld")) {message(p,"Return to the Earth workshop to add parts.");break;}
                command(p,"place template spain:imported/spore_rocket 14 97 -5");
                message(p,"The local imported hull appears beside the workshop when installed. Select its corners to include it in your blueprint.");
            }
        }
        return 1;
    }

    // Read a scoreboard value for the player; 0 when the objective or score does not exist.
    private int score(ServerPlayer p,String objective) {
        var obj=server.getScoreboard().getObjective(objective);if(obj==null)return 0;
        var s=server.getScoreboard().getPlayerScoreInfo(p,obj);return s==null?0:s.value();
    }

    // Creative-style flight for a survival player: allowed, active, speed .13 (vanilla default is .05, so about 2.6 times faster), and fall damage reset.
    private void enableFlight(ServerPlayer p) {
        p.getAbilities().mayfly=true;p.getAbilities().flying=true;p.getAbilities().setFlyingSpeed(.13f);p.onUpdateAbilities();p.resetFallDistance();
    }

    // Leave the pilot seat and put the player's original abilities back. Creative players stay able to fly.
    private void unboard(ServerPlayer p,Ship s) {
        s.piloting=false;p.entityTags().remove("spain.pilot");
        p.getAbilities().mayfly=s.originalMayfly||p.gameMode().isCreative();
        p.getAbilities().flying=p.gameMode().isCreative();p.getAbilities().setFlyingSpeed(s.originalSpeed);p.onUpdateAbilities();p.resetFallDistance();
        view.accept(p,new FlightView(false,4));
    }

    // Called after every server tick. Order: advance blueprint scans, then handle each online player (see below), then settle ships whose owners are offline and save every 100 ticks.
    public void tick(MinecraftServer server) {
        this.server=server;ticks++;

        // Each scan processes its budget and is removed when it returns true (finished).
        scans.entrySet().removeIf(e -> e.getValue().step());
        for(ServerPlayer p:server.getPlayerList().getPlayers()) {
            // First tick for this player since joining (or since the server started): clear a stale pilot tag and flight permission left by a crash or quit mid-flight, so nobody stays able to fly.
            if(connected.add(p.getUUID())&&p.entityTags().contains("spain.pilot")) {
                p.entityTags().remove("spain.pilot");
                p.getAbilities().mayfly=p.gameMode().isCreative();p.getAbilities().flying=false;
                p.getAbilities().setFlyingSpeed(.05f);p.onUpdateAbilities();
            }

            // Turn request tags set by the data pack (tools/extend_pack.py) into actions; remove() returns true only if the tag existed, so each request runs once.
            for(String action:new String[]{"capture","board","land","spore","recall","create"}) if(p.entityTags().remove("spain.request."+action)) action(p,action);

            // Spacesuit: refill air whenever the head is not under water, so there is no suffocation in space, yet a suited player can still drown underwater.
            if(p.entityTags().contains("spain.suit")&&!p.isUnderWater()) p.setAirSupply(p.getMaxAirSupply());

            // Arrival check: a player with a ship (launch >= 3) who stands on the station platform (inside x/z ±17, y 64..72) completes the flight test once.
            if(dimension(p).equals("spain:orbit")&&p.getY()>=64&&p.getY()<72&&Math.abs(p.getX())<17&&Math.abs(p.getZ())<17&&score(p,"spain.launch")>=3&&!p.entityTags().contains("spain.test_complete")) {
                message(p,"Dock workers: Welcome to the world of endless possibility!");command(p,"function spain:quest/arrival");
            }
            Ship s=ships.get(p.getUUID());if(s==null)continue;

            // Piloted ship: keep flight enabled, handle the gravity boundary, and glue the ship to the player.
            if(s.piloting) {
                if(!p.isAlive()) {unboard(p,s);continue;}
                enableFlight(p);
                boolean inOrbit=dimension(p).equals("spain:orbit");

                // Leaving the atmosphere: above y=280 on Earth, send the player to space near the station (0.5, 95, 30.5).
                if(!inOrbit&&p.getY()>280) {
                    ServerLevel orbit=world("spain:orbit");
                    if(orbit!=null) p.teleportTo(orbit,0.5,95,30.5,Set.of(),180,0,false);
                    message(p,"Gravity fades. Space is yours. Fly to the station at X 0, Y 65, Z 0, or open the Galaxy Guide.");

                // Falling out of orbit back to Earth: place the player high above the ground (y=265) so they can fly down.
                } else if(inOrbit&&p.getY()<40) {
                    ServerLevel earth=world("minecraft:overworld");p.teleportTo(earth,.5,265,.5,Set.of(),p.getYRot(),p.getXRot(),false);
                    message(p,"Entering Earth's gravity field.");
                }
                String now=dimension(p);

                // The player changed dimension (quick travel or the boundary): the old render entities belong to the other world, so drop them and re-render here.
                if(!now.equals(s.dimension)) {clearDisplays(s);s.dimension=now;}
                // Cockpit sits above the lower hull; one Minecraft block remains one part.

                // The ship is where the player is and faces where they look; no velocity is carried because the player's own flight moves them.
                s.anchor=p.position();s.yaw=p.getYRot();s.velocity=0;
            } else {
                if(!dimension(p).equals(s.dimension)) continue;

                // Parked ship: let it fall or float.
                settle(s);
            }

            // Only render ships within 256 blocks of their owner (distance squared avoids a square root); farther displays would not be seen anyway.
            if(p.position().distanceToSqr(s.anchor)<256*256) render(s);
        }

        // Forget players who left, so their next join triggers the stale-tag cleanup again.
        connected.removeIf(id -> server.getPlayerList().getPlayer(id)==null);

        // Ships of offline players keep settling, but only if their chunk is loaded, so none keeps falling into the void.
        // Offline ships also settle. No damage system or health pool exists for ships.
        for(var e:ships.entrySet()) if(server.getPlayerList().getPlayer(e.getKey())==null) {
            Ship s=e.getValue();s.piloting=false;ServerLevel level=world(s.dimension);
            if(level!=null&&level.hasChunkAt(BlockPos.containing(s.anchor))) {settle(s);render(s);}
        }
        if(ticks%100==0)save(server);
    }

    // One physics step for a parked ship: a vertical-only movement. Public so the verification probe can test it directly
    // without a player. The unit of velocity is blocks per tick.
    public void settle(Ship s) {
        ServerLevel level=world(s.dimension);if(level==null||!level.hasChunkAt(BlockPos.containing(s.anchor)))return;

        // Every part is tested, so the ship can rest on a tree top or a ceiling above it, not just on its base.
        // Every occupied cell participates, allowing tree tips, mountain peaks and ceilings.
        double move=0;boolean water=false;
        for(Part part:s.parts) if(level.getFluidState(BlockPos.containing(partPosition(s,part))).is(FluidTags.WATER)) {water=true;break;}

        // In water: float up 0.2 blocks per tick, no accumulated speed. Otherwise: gravity of 0.04 per tick, falling at most 0.8.
        if(water) {s.velocity=0;move=.20;}
        else {s.velocity=Math.max(-.8,s.velocity-.04);move=s.velocity;}
        double allowed=move;

        // Half-width of a part's box after rotation (|cos|+|sin|)/2: a 1-block cube turned by yaw covers up to 1.41 blocks across. Used so rotated ships collide correctly.
        double half=(Math.abs(Math.cos(Math.toRadians(s.yaw)))+Math.abs(Math.sin(Math.toRadians(s.yaw))))*.5;
        for(Part part:s.parts) {
            Vec3 position=partPosition(s,part);

            // Collision box of one part, shrunk by 0.01 on each side so touching a neighbouring wall does not count as blocked.
            var cell=new net.minecraft.world.phys.AABB(position.x+.5-half+.01,position.y,position.z+.5-half+.01,position.x+.5+half-.01,position.y+1,position.z+.5+half-.01);

            // Ask Minecraft how far the box can move vertically before hitting terrain. The ship may only move by the most restrictive part (the smallest allowed distance).
            Vec3 clipped=net.minecraft.world.entity.Entity.collideBoundingBox(net.minecraft.world.phys.shapes.CollisionContext.empty(),new Vec3(0,move,0),cell,level,List.of());
            allowed=move<0?Math.max(allowed,clipped.y):Math.min(allowed,clipped.y);
        }

        // Landed (or blocked): reset speed so it does not accumulate while resting.
        if(Math.abs(allowed)<.0001)s.velocity=0;
        s.anchor=s.anchor.add(0,allowed,0);
    }

    // World position of a part: rotate the (x, z) offset by the ship's yaw (standard 2D rotation) and add it to the anchor. y is not rotated.
    private Vec3 partPosition(Ship ship,Part part) {
        double angle=Math.toRadians(ship.yaw),c=Math.cos(angle),s=Math.sin(angle);
        return ship.anchor.add(c*part.x-s*part.z,part.y,s*part.x+c*part.z);
    }

    // Create or update the visible block displays. If the entity count differs from the part count or one was removed (chunk unload), rebuild all.
    private void render(Ship s) {
        ServerLevel level=world(s.dimension);if(level==null)return;
        if(s.displays.size()!=s.parts.size()||s.displays.stream().anyMatch(e -> e.isRemoved())) {
            clearDisplays(s);
            for(Part part:s.parts) {
                // shouldBeSaved() returns false, so displays never end up in world files; if the server crashes they vanish on the next load (see load()).
                Display.BlockDisplay display=new Display.BlockDisplay(EntityTypes.BLOCK_DISPLAY,level) {
                    @Override public boolean shouldBeSaved() {return false;}
                };
                CompoundTag tag=new CompoundTag();
                tag.put("block_state",BlockState.CODEC.encodeStart(NbtOps.INSTANCE,part.state).getOrThrow());

                // teleport_duration 1 = smooth interpolation of position over one tick; view_range 4 draws it up to about 4 x 64 blocks away (the value is a multiplier of the default).
                tag.putInt("teleport_duration",1);tag.putFloat("view_range",4);
                display.load(TagValueInput.create(ProblemReporter.DISCARDING,level.registryAccess(),tag));

                // Tag so load() (and tests) can find and delete leftovers.
                display.addTag("spain.ship_display");display.setNoGravity(true);display.setPos(partPosition(s,part));display.setYRot(s.yaw);
                level.addFreshEntity(display);s.displays.add(display);
            }
        }

        // Every tick: move each display to its part's current position and heading.
        for(int i=0;i<s.parts.size();i++) {Part part=s.parts.get(i);s.displays.get(i).setPos(partPosition(s,part));s.displays.get(i).setYRot(s.yaw);}
    }

    // Remove all display entities of a ship (discard) and forget them.
    private void clearDisplays(Ship s) {for(var e:s.displays)e.discard();s.displays.clear();}

    // Save file inside the world folder, so the ship data travels with the world and is separate per world.
    private Path path(MinecraftServer server) {return server.getWorldPath(LevelResource.ROOT).resolve("spain-ships.json");}

    // Write every ship (owner, dimension, yaw, anchor, parts with full block state as JSON) to spain-ships.json. The write goes to a .tmp file first and is
    // then moved over the real file atomically, so a crash during saving cannot leave a half-written file.
    public void save(MinecraftServer server) {
        if(server==null)return;
        JsonObject root=new JsonObject();root.addProperty("version",1);
        JsonArray array=new JsonArray();
        for(var e:ships.entrySet()) {
            Ship s=e.getValue();JsonObject ship=new JsonObject();ship.addProperty("owner",e.getKey().toString());ship.addProperty("dimension",s.dimension);
            ship.addProperty("yaw",s.yaw);
            ship.add("anchor",gson.toJsonTree(new double[]{s.anchor.x,s.anchor.y,s.anchor.z}));
            JsonArray parts=new JsonArray();
            for(Part p:s.parts) {JsonObject part=new JsonObject();part.addProperty("x",p.x);part.addProperty("y",p.y);part.addProperty("z",p.z);part.add("state",BlockState.CODEC.encodeStart(JsonOps.INSTANCE,p.state).getOrThrow());parts.add(part);}ship.add("parts",parts);array.add(ship);
        }
        root.add("ships",array);
        try {Path file=path(server),temp=file.resolveSibling("spain-ships.json.tmp");Files.writeString(temp,gson.toJson(root));Files.move(temp,file,StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);}
        catch(Exception e) {throw new IllegalStateException("Could not save Spain ships",e);}
    }

    // Reset all in-memory state, delete leftover display entities from any previous session, then read spain-ships.json if it exists.
    // A corrupt file throws instead of being replaced, so the original is kept for repair (the message says so).
    public void load(MinecraftServer server) {
        this.server=server;ships.clear();scans.clear();selections.clear();connected.clear();

        // First remove old displays everywhere: the list in each Ship starts empty and render() will create fresh ones.
        // Displays are disposable render proxies; blueprints are the authoritative save.
        for(ServerLevel level:server.getAllLevels()) for(var e:java.util.stream.StreamSupport.stream(level.getAllEntities().spliterator(),false).filter(Objects::nonNull).toList()) if(e.entityTags().contains("spain.ship_display"))e.discard();
        Path file=path(server);if(!Files.exists(file))return;
        try {
            JsonObject root=JsonParser.parseString(Files.readString(file)).getAsJsonObject();
            for(JsonElement item:root.getAsJsonArray("ships")) {
                JsonObject value=item.getAsJsonObject();Ship s=new Ship();s.dimension=value.get("dimension").getAsString();
                s.yaw=value.has("yaw")?value.get("yaw").getAsFloat():0;
                JsonArray anchor=value.getAsJsonArray("anchor");s.anchor=new Vec3(anchor.get(0).getAsDouble(),anchor.get(1).getAsDouble(),anchor.get(2).getAsDouble());
                for(JsonElement element:value.getAsJsonArray("parts")) {JsonObject p=element.getAsJsonObject();s.parts.add(new Part(p.get("x").getAsInt(),p.get("y").getAsInt(),p.get("z").getAsInt(),BlockState.CODEC.parse(JsonOps.INSTANCE,p.get("state")).getOrThrow()));}
                ships.put(UUID.fromString(value.get("owner").getAsString()),s);
            }
        } catch(Exception e) {throw new IllegalStateException("Could not read Spain ship save; preserved original file",e);}
    }
}
