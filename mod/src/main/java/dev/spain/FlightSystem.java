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

/** Native block-display ships. Minecraft remains responsible for player movement and terrain. */
public final class FlightSystem {
    public record Part(int x,int y,int z,BlockState state) {}
    public static final class Ship {
        public final List<Part> parts=new ArrayList<>();
        public final List<Display.BlockDisplay> displays=new ArrayList<>();
        public String dimension="minecraft:overworld";
        public Vec3 anchor=new Vec3(9,97,1);
        public boolean piloting;
        public float yaw;
        float originalSpeed=.05f;
        boolean originalMayfly;
        double velocity;
    }
    private record Selection(String dimension,BlockPos a,BlockPos b) {}
    private final Map<UUID,Ship> ships=new HashMap<>();
    private final Map<UUID,Selection> selections=new HashMap<>();
    private final Map<UUID,Scan> scans=new HashMap<>();
    private final Set<UUID> connected=new HashSet<>();
    private final Map<UUID,Deque<List<Part>>> history=new HashMap<>();
    public java.util.function.BiConsumer<ServerPlayer,FlightView> view=(player,payload)->{};
    private MinecraftServer server;
    private int ticks;
    private final Gson gson=new GsonBuilder().setPrettyPrinting().create();
    private class Scan {
        final ServerPlayer player; final Ship ship=new Ship(); final Selection selection;
        boolean avatar;
        final Iterator<BlockPos> positions;
        Scan(ServerPlayer p,Selection s) {
            player=p;selection=s;positions=BlockPos.betweenClosed(s.a,s.b).iterator();
            ship.dimension=s.dimension;ship.anchor=new Vec3(s.a.getX(),s.a.getY(),s.a.getZ());
        }
        boolean step() {
            ServerLevel level=world(selection.dimension);
            for(int i=0;i<1024&&positions.hasNext();i++) {
                BlockPos p=positions.next(); BlockState state=level.getBlockState(p);
                if(!state.isAir()&&state.getFluidState().isEmpty()) ship.parts.add(new Part(p.getX()-selection.a.getX(),p.getY()-selection.a.getY(),p.getZ()-selection.a.getZ(),state));
            }
            if(positions.hasNext()) return false;
            if(ship.parts.isEmpty()) {message(player,"The selection is empty. Build your rocket first.");return true;}
            if(avatar) {SpainMod.VISUALS.custom(player,ship.parts);message(player,"Created your own block creature. Press F5 to preview it.");return true;}
            Ship previous=ships.get(player.getUUID());
            if(previous!=null) {if(previous.piloting) unboard(player,previous);clearDisplays(previous);}
            // Blueprints leave the workshop intact. A landed craft is an invulnerable projection.
            center(ship);
            ships.put(player.getUUID(),ship);
            ship.anchor=player.position().add(4,0,0);
            command(player,"scoreboard players set @s spain.launch 3");
            save(server);message(player,"Captured "+ship.parts.size()+" parts. Board to fly. Your workshop remains editable.");
            return true;
        }
    }
    public Ship ship(ServerPlayer player) {return ships.get(player.getUUID());}
    private void center(Ship ship) {
        int x=(ship.parts.stream().mapToInt(Part::x).min().orElse(0)+ship.parts.stream().mapToInt(Part::x).max().orElse(0))/2;
        int z=(ship.parts.stream().mapToInt(Part::z).min().orElse(0)+ship.parts.stream().mapToInt(Part::z).max().orElse(0))/2;
        var copy=ship.parts.stream().map(p->new Part(p.x-x,p.y,p.z-z,p.state)).toList();ship.parts.clear();ship.parts.addAll(copy);
    }
    private List<Part> model(String name) {
        try(var input=getClass().getResourceAsStream("/assets/spain/"+name+".voxels.json")) {
            if(input==null)return List.of();
            var json=JsonParser.parseString(new String(input.readAllBytes(),java.nio.charset.StandardCharsets.UTF_8)).getAsJsonObject();
            Ship s=new Ship();
            for(var element:json.getAsJsonArray("parts")) {var p=element.getAsJsonObject();s.parts.add(new Part(p.get("x").getAsInt(),p.get("y").getAsInt(),p.get("z").getAsInt(),net.minecraft.core.registries.BuiltInRegistries.BLOCK.getValue(Identifier.withDefaultNamespace(p.get("block").getAsString())).defaultBlockState()));}
            center(s);return s.parts;
        } catch(Exception e) {throw new IllegalStateException("Cannot load rocket creator part "+name,e);}
    }
    private BlockState block(String id){return net.minecraft.core.registries.BuiltInRegistries.BLOCK.getValue(Identifier.withDefaultNamespace(id)).defaultBlockState();}
    private void cockpit(Ship s) {s.parts.removeIf(p->Math.abs(p.x)<=1&&Math.abs(p.z)<=1&&p.y>=0&&p.y<=2);}
    public int design(ServerPlayer p,String choice) {
        server=p.level().getServer();Ship s=ships.computeIfAbsent(p.getUUID(),id->new Ship());
        if(s.piloting)unboard(p,s);
        clearDisplays(s);s.dimension=dimension(p);s.anchor=p.position().add(0,0,7);
        var undo=history.computeIfAbsent(p.getUUID(),id->new ArrayDeque<>());
        if(choice.equals("undo")) {if(!undo.isEmpty()){s.parts.clear();s.parts.addAll(undo.pop());}}
        else {
            undo.push(List.copyOf(s.parts));
            int reach=s.parts.stream().mapToInt(part->Math.abs(part.x)).max().orElse(3);
            int front=s.parts.stream().mapToInt(Part::z).max().orElse(0);
            switch(choice) {
                case "clear" -> s.parts.clear();
                case "rotate" -> s.yaw+=90;
                case "hull" -> {
                    var hull=model("spore_rocket");int offset=s.parts.isEmpty()?0:front+5;
                    if(hull.isEmpty()) {
                        for(int x=-3;x<=3;x++)for(int z=-4;z<=4;z++)if(Math.abs(x)+Math.abs(z)<=6)s.parts.add(new Part(x,0,z+offset,block("cyan_concrete")));
                    } else {
                        for(Part part:hull)s.parts.add(new Part(part.x,part.y,part.z+offset,part.state));
                    }
                }
                case "engine" -> {
                    int back=s.parts.stream().mapToInt(Part::z).min().orElse(0)-3;
                    var engine=model("spore_thruster");
                    if(engine.isEmpty())s.parts.add(new Part(0,0,back,block("magma_block")));
                    else for(Part part:engine)s.parts.add(new Part(part.x,part.y,part.z+back,part.state));
                    s.parts.add(new Part(0,1,back-3,block("magma_block")));
                }
                case "wings" -> {
                    for(int side:new int[]{-1,1})for(int x=1;x<=4;x++)for(int z=-2;z<=2;z++)if(x+Math.abs(z)<=5)s.parts.add(new Part(side*(reach+x),0,z,block(x==4?"cyan_concrete":"white_concrete")));
                }
                case "cabin" -> {
                    for(int x=-2;x<=2;x++)for(int z=-2;z<=2;z++)for(int y=1;y<=3;y++)if(Math.abs(x)==2||Math.abs(z)==2||y==3)s.parts.add(new Part(x,y,z,block(y==3?"white_concrete":"light_blue_stained_glass")));
                }
                case "stretch" -> {
                    var old=List.copyOf(s.parts);s.parts.clear();for(Part part:old)for(int z=0;z<2;z++)s.parts.add(new Part(part.x,part.y,part.z*2+z,part.state));
                }
            }
        }
        cockpit(s);
        // Merge shared cells while retaining unrestricted addition of distinct components.
        Map<BlockPos,Part> merged=new LinkedHashMap<>();for(Part part:s.parts)merged.put(new BlockPos(part.x,part.y,part.z),part);s.parts.clear();s.parts.addAll(merged.values());
        p.addTag("spain.suit");command(p,"scoreboard players set @s spain.launch 3");save(server);
        message(p,"Rocket creator: "+s.parts.size()+" blocks. Add parts as often as you like. Board when ready.");
        command(p,"dialog show @s spain:creator");return 1;
    }
    private float cameraDistance(Ship s) {return (float)Math.max(10,s.parts.stream().mapToDouble(part->Math.sqrt(part.x*part.x+part.z*part.z)).max().orElse(4)+7);}
    public int captureAvatar(ServerPlayer p) {
        server=p.level().getServer();Selection sel=selections.get(p.getUUID());
        if(sel==null||!dimension(p).equals(sel.dimension)) {message(p,"Select your creation with /spain corner1 and corner2 first.");return 0;}
        Scan scan=new Scan(p,sel);scan.avatar=true;scans.put(p.getUUID(),scan);return 1;
    }
    private ServerLevel world(String id) {return server.getLevel(ResourceKey.create(Registries.DIMENSION,Identifier.parse(id)));}
    private String dimension(ServerPlayer p) {return p.level().dimension().identifier().toString();}
    private void message(ServerPlayer p,String text) {p.sendSystemMessage(Component.literal(text));}
    private void command(ServerPlayer p,String text) {server.getCommands().performPrefixedCommand(server.createCommandSourceStack().withEntity(p).withLevel(p.level()).withPosition(p.position()).withSuppressedOutput(),text);}
    public void corner(ServerPlayer p,int n,BlockPos pos) {
        Selection old=selections.get(p.getUUID());
        if(old==null||!old.dimension.equals(dimension(p))) old=new Selection(dimension(p),pos,pos);
        selections.put(p.getUUID(),new Selection(dimension(p),n==1?pos:old.a,n==2?pos:old.b));
        message(p,"Blueprint corner "+n+": "+pos.toShortString()+". /spain capture scans without a part-count cap.");
    }
    public int action(ServerPlayer p,String action) {
        server=p.level().getServer();
        Ship ship=ships.get(p.getUUID());
        switch(action) {
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
            case "land" -> {if(ship!=null&&ship.piloting) {unboard(p,ship);message(p,"Disembarked. Your ship settles without damage and floats on water.");save(server);}}
            case "help" -> command(p,"dialog show @s spain:rocket");
            case "create" -> command(p,"dialog show @s spain:creator");
            case "recall" -> {if(ship!=null){p.teleportTo(world(ship.dimension),ship.anchor.x,ship.anchor.y+1,ship.anchor.z,Set.of(),p.getYRot(),p.getXRot(),false);message(p,"You are beside your rocket. Board whenever you like.");}}
            case "spore" -> {
                if(!dimension(p).equals("minecraft:overworld")) {message(p,"Return to the Earth workshop to add parts.");break;}
                command(p,"place template spain:imported/spore_rocket 14 97 -5");
                message(p,"The local imported hull appears beside the workshop when installed. Select its corners to include it in your blueprint.");
            }
        }
        return 1;
    }
    private int score(ServerPlayer p,String objective) {
        var obj=server.getScoreboard().getObjective(objective);if(obj==null)return 0;
        var s=server.getScoreboard().getPlayerScoreInfo(p,obj);return s==null?0:s.value();
    }
    private void enableFlight(ServerPlayer p) {
        p.getAbilities().mayfly=true;p.getAbilities().flying=true;p.getAbilities().setFlyingSpeed(.13f);p.onUpdateAbilities();p.resetFallDistance();
    }
    private void unboard(ServerPlayer p,Ship s) {
        s.piloting=false;p.entityTags().remove("spain.pilot");
        p.getAbilities().mayfly=s.originalMayfly||p.gameMode().isCreative();
        p.getAbilities().flying=p.gameMode().isCreative();p.getAbilities().setFlyingSpeed(s.originalSpeed);p.onUpdateAbilities();p.resetFallDistance();
        view.accept(p,new FlightView(false,4));
    }
    public void tick(MinecraftServer server) {
        this.server=server;ticks++;
        scans.entrySet().removeIf(e -> e.getValue().step());
        for(ServerPlayer p:server.getPlayerList().getPlayers()) {
            if(connected.add(p.getUUID())&&p.entityTags().contains("spain.pilot")) {
                p.entityTags().remove("spain.pilot");
                p.getAbilities().mayfly=p.gameMode().isCreative();p.getAbilities().flying=false;
                p.getAbilities().setFlyingSpeed(.05f);p.onUpdateAbilities();
            }
            for(String action:new String[]{"capture","board","land","spore","recall","create"}) if(p.entityTags().remove("spain.request."+action)) action(p,action);
            if(p.entityTags().contains("spain.suit")&&!p.isUnderWater()) p.setAirSupply(p.getMaxAirSupply());
            if(dimension(p).equals("spain:orbit")&&p.getY()>=64&&p.getY()<72&&Math.abs(p.getX())<17&&Math.abs(p.getZ())<17&&score(p,"spain.launch")>=3&&!p.entityTags().contains("spain.test_complete")) {
                message(p,"Dock workers: Welcome to the world of endless possibility!");command(p,"function spain:quest/arrival");
            }
            Ship s=ships.get(p.getUUID());if(s==null)continue;
            if(s.piloting) {
                if(!p.isAlive()) {unboard(p,s);continue;}
                enableFlight(p);
                boolean inOrbit=dimension(p).equals("spain:orbit");
                if(!inOrbit&&p.getY()>280) {
                    ServerLevel orbit=world("spain:orbit");
                    if(orbit!=null) p.teleportTo(orbit,0.5,95,30.5,Set.of(),180,0,false);
                    message(p,"Gravity fades. Space is yours. Fly to the station at X 0, Y 65, Z 0, or open the Galaxy Guide.");
                } else if(inOrbit&&p.getY()<40) {
                    ServerLevel earth=world("minecraft:overworld");p.teleportTo(earth,.5,265,.5,Set.of(),p.getYRot(),p.getXRot(),false);
                    message(p,"Entering Earth's gravity field.");
                }
                String now=dimension(p);
                if(!now.equals(s.dimension)) {clearDisplays(s);s.dimension=now;}
                // Cockpit sits above the lower hull; one Minecraft block remains one part.
                s.anchor=p.position();s.yaw=p.getYRot();s.velocity=0;
            } else {
                if(!dimension(p).equals(s.dimension)) continue;
                settle(s);
            }
            if(p.position().distanceToSqr(s.anchor)<256*256) render(s);
        }
        connected.removeIf(id -> server.getPlayerList().getPlayer(id)==null);
        // Offline ships also settle. No damage system or health pool exists for ships.
        for(var e:ships.entrySet()) if(server.getPlayerList().getPlayer(e.getKey())==null) {
            Ship s=e.getValue();s.piloting=false;ServerLevel level=world(s.dimension);
            if(level!=null&&level.hasChunkAt(BlockPos.containing(s.anchor))) {settle(s);render(s);}
        }
        if(ticks%100==0)save(server);
    }
    public void settle(Ship s) {
        ServerLevel level=world(s.dimension);if(level==null||!level.hasChunkAt(BlockPos.containing(s.anchor)))return;
        // Every occupied cell participates, allowing tree tips, mountain peaks and ceilings.
        double move=0;boolean water=false;
        for(Part part:s.parts) if(level.getFluidState(BlockPos.containing(partPosition(s,part))).is(FluidTags.WATER)) {water=true;break;}
        if(water) {s.velocity=0;move=.20;}
        else {s.velocity=Math.max(-.8,s.velocity-.04);move=s.velocity;}
        double allowed=move;
        double half=(Math.abs(Math.cos(Math.toRadians(s.yaw)))+Math.abs(Math.sin(Math.toRadians(s.yaw))))*.5;
        for(Part part:s.parts) {
            Vec3 position=partPosition(s,part);
            var cell=new net.minecraft.world.phys.AABB(position.x+.5-half+.01,position.y,position.z+.5-half+.01,position.x+.5+half-.01,position.y+1,position.z+.5+half-.01);
            Vec3 clipped=net.minecraft.world.entity.Entity.collideBoundingBox(net.minecraft.world.phys.shapes.CollisionContext.empty(),new Vec3(0,move,0),cell,level,List.of());
            allowed=move<0?Math.max(allowed,clipped.y):Math.min(allowed,clipped.y);
        }
        if(Math.abs(allowed)<.0001)s.velocity=0;
        s.anchor=s.anchor.add(0,allowed,0);
    }
    private Vec3 partPosition(Ship ship,Part part) {
        double angle=Math.toRadians(ship.yaw),c=Math.cos(angle),s=Math.sin(angle);
        return ship.anchor.add(c*part.x-s*part.z,part.y,s*part.x+c*part.z);
    }
    private void render(Ship s) {
        ServerLevel level=world(s.dimension);if(level==null)return;
        if(s.displays.size()!=s.parts.size()||s.displays.stream().anyMatch(e -> e.isRemoved())) {
            clearDisplays(s);
            for(Part part:s.parts) {
                Display.BlockDisplay display=new Display.BlockDisplay(EntityTypes.BLOCK_DISPLAY,level) {
                    @Override public boolean shouldBeSaved() {return false;}
                };
                CompoundTag tag=new CompoundTag();
                tag.put("block_state",BlockState.CODEC.encodeStart(NbtOps.INSTANCE,part.state).getOrThrow());
                tag.putInt("teleport_duration",1);tag.putFloat("view_range",4);
                display.load(TagValueInput.create(ProblemReporter.DISCARDING,level.registryAccess(),tag));
                display.addTag("spain.ship_display");display.setNoGravity(true);display.setPos(partPosition(s,part));display.setYRot(s.yaw);
                level.addFreshEntity(display);s.displays.add(display);
            }
        }
        for(int i=0;i<s.parts.size();i++) {Part part=s.parts.get(i);s.displays.get(i).setPos(partPosition(s,part));s.displays.get(i).setYRot(s.yaw);}
    }
    private void clearDisplays(Ship s) {for(var e:s.displays)e.discard();s.displays.clear();}
    private Path path(MinecraftServer server) {return server.getWorldPath(LevelResource.ROOT).resolve("spain-ships.json");}
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
    public void load(MinecraftServer server) {
        this.server=server;ships.clear();scans.clear();selections.clear();connected.clear();
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
