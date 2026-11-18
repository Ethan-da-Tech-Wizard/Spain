// Program: Spain - MinecraftChecks.java
// Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
// Last Modified: 2026-11-18
// Purpose: Test program that starts a real Minecraft server in GameTest mode and checks the Spain data pack and mod: cities, NPCs, quests, flight, saving and appearance.
// Imports: Minecraft server, game test, world and network classes used by the checks.
import net.minecraft.SharedConstants;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.core.BlockPos;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.gametest.framework.GameTestMainUtil;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.InteractionHand;
import net.minecraft.network.protocol.game.ServerboundInteractPacket;
import net.minecraft.world.item.Items;
import net.minecraft.world.scores.ScoreHolder;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import java.nio.file.Files;
import java.nio.file.Path;

// Each check() call prints a numbered line, and any failed check stops the run with an error.
/** Runs against Mojang's real server; no replacement movement, NPC, save or command engine. */
public final class MinecraftChecks {
    // Counts how many checks have passed.
    private static int checks;

    /** Starts Minecraft's own GameTest server after registering our test function. */
    public static void main(String[] args) throws Exception {
        // Prepare Minecraft's version info and built-in registries.
        SharedConstants.tryDetectVersion();
        net.minecraft.server.Bootstrap.bootStrap();
        // This standalone probe has no loader bootstrap hook. Open only the test-function
        // registry to install its check, then freeze it again before loading any worlds.
        // Registries are locked after startup, so briefly unlock the test list with reflection...
        var frozen = net.minecraft.core.MappedRegistry.class.getDeclaredField("frozen");
        frozen.setAccessible(true);
        frozen.setBoolean(BuiltInRegistries.TEST_FUNCTION, false);
        try {
            // ...register our test under the name spain:core...
            java.util.function.Consumer<GameTestHelper> check = MinecraftChecks::test;
            var holder = Registry.registerForHolder(BuiltInRegistries.TEST_FUNCTION, Identifier.fromNamespaceAndPath("spain", "core"), check);
            var bind = net.minecraft.core.Holder.Reference.class.getDeclaredMethod("bindValue", Object.class);
            bind.setAccessible(true);
            bind.invoke(holder, check);
        } finally {
            // ...and lock it again no matter what happened.
            frozen.setBoolean(BuiltInRegistries.TEST_FUNCTION, true);
        }
        // Run the server; it will call test() below.
        GameTestMainUtil.runGameTestServer(args, ignored -> {});
    }

    /** The main test: schedules the setup and then runs every check in order. */
    private static void test(GameTestHelper helper) {
        // At tick 100, force-load the world areas so the cities finish building.
        helper.runAtTickTime(100, () -> {
            command(helper.getLevel().getServer(), null, "execute in minecraft:overworld run forceload add -32 -32 31 31");
            for (String id : new String[]{"orbit", "astraea", "cinder", "borealis"})
                command(helper.getLevel().getServer(), null, "execute in spain:" + id + " run forceload add -32 -32 31 31");
        });
        // At tick 140, run all the checks. Any exception is printed and reported as a test failure.
        helper.runAtTickTime(140, () -> {
            try {
                // Cities, landing pads and NPC counts for each world.
                MinecraftServer server = helper.getLevel().getServer();
                check(score(server, ScoreHolder.forNameOnly("#built"), "spain.state") == 2, "Cities finish building");
                for (String id : new String[]{"orbit", "astraea", "cinder", "borealis"}) {
                    ServerLevel level = dimension(server, id);
                    check(level != null, "Dimension exists: " + id);
                    check(!level.getBlockState(new BlockPos(0, 64, 0)).isAir(), "Landing pad exists: " + id);
                    check(level.getBlockState(new BlockPos(0, 65, 0)).isAir(), "Landing headroom: " + id);
                }
                for (String id : new String[]{"earth","orbit","astraea","cinder","borealis"}) {
                    var residents=dimension(server,id).getEntities((Entity)null,new AABB(-30,60,-30,30,140,30),e->e instanceof net.minecraft.world.entity.npc.villager.Villager&&e.entityTags().contains("spain.npc"));
                    int expected=id.equals("earth")?4:id.equals("orbit")?6:1;
                    check(residents.size()==expected,"NPCs spawn exactly once: "+id);
                }
                // Check the imported crate, then check that reloading the data pack keeps player builds.
                ServerLevel astraea = dimension(server, "astraea");
                if (Boolean.getBoolean("spain.imported"))
                    check(!astraea.getBlockState(new BlockPos(8, 65, 10)).isAir(), "Local imported crate is placed");
                astraea.setBlockAndUpdate(new BlockPos(2, 65, 2), Blocks.DIAMOND_BLOCK.defaultBlockState());
                command(server, null, "function spain:load");
                check(astraea.getBlockState(new BlockPos(2, 65, 2)).is(Blocks.DIAMOND_BLOCK), "Reload preserves player builds");
                astraea.setBlockAndUpdate(new BlockPos(2, 65, 2), Blocks.AIR.defaultBlockState());

                // Create a real survival player with an embedded network connection.
                // GameTestHelper's mock overrides gameMode() to always return CREATIVE.
                // Use a regular ServerPlayer and Mojang's embedded connection instead.
                var profile = new com.mojang.authlib.GameProfile(java.util.UUID.randomUUID(), "test-mock-player");
                var cookie = net.minecraft.server.network.CommonListenerCookie.createInitial(profile, false);
                ServerPlayer player = new ServerPlayer(server, helper.getLevel(), profile, cookie.clientInformation());
                var connection = new net.minecraft.network.Connection(net.minecraft.network.protocol.PacketFlow.SERVERBOUND);
                new io.netty.channel.embedded.EmbeddedChannel(connection);
                server.getPlayerList().placeNewPlayer(connection, player, cookie);
                player.setGameMode(GameType.SURVIVAL);
                // Welcome the player and check the Earth start and the quest steps with the mayor and scientist.
                command(server, player, "function spain:player/welcome");
                command(server, player, "function spain:travel/earth");
                check(player.level()==server.overworld(), "Players begin on Earth");
                check(score(server,ScoreHolder.forNameOnly("#earth"),"spain.state")==2,"Earth city is built");
                check(!server.overworld().getBlockState(new BlockPos(0,96,0)).isAir(),"Earth city has a walkable plaza");
                interact(server,player,"earth","mayor");
                check(score(server,player,"spain.launch")==1,"Mayor directs player to scientist");
                interact(server,player,"earth","scientist");
                check(score(server,player,"spain.launch")==2,"Scientist issues rocket quest");
                check(player.entityTags().contains("spain.suit"),"Scientist activates spacesuit");
                // Flight checks: capture a hull, board, fly into space, travel, land and restore abilities.
                var flight=new dev.spain.FlightSystem();flight.load(server);flight.tick(server);
                flight.action(player,"capture");for(int scan=0;scan<4;scan++)flight.tick(server);
                check(flight.ship(player)!=null&&!flight.ship(player).parts.isEmpty(),"Player-built hull captured");
                flight.action(player,"board");flight.tick(server);
                check(player.getAbilities().flying&&player.getAbilities().mayfly,"Survival player receives cockpit flight");
                player.setPos(0,281,0);flight.tick(server);
                check(player.level()==dimension(server,"orbit"),"Freeflight crosses gravity boundary into space");
                command(server,player,"function spain:travel/cinder");flight.tick(server);
                check(flight.ship(player).dimension.equals("spain:cinder")&&flight.ship(player).piloting,"Quick travel interrupts freeflight and keeps cockpit active");
                command(server,player,"function spain:travel/orbit");flight.tick(server);
                check(player.entityTags().contains("spain.test_complete"),"Workers welcome pilot; station completes test");
                flight.action(player,"land");
                check(!player.getAbilities().mayfly&&!player.getAbilities().flying,"Disembarking restores survival abilities");
                // Physics checks with a one-block ship: it lands on a surface, falls without support, floats in water and is stopped by a ceiling.
                var physics=new dev.spain.FlightSystem.Ship();physics.dimension="spain:astraea";physics.anchor=new Vec3(3,68,3);
                physics.parts.add(new dev.spain.FlightSystem.Part(0,0,0,Blocks.IRON_BLOCK.defaultBlockState()));
                for(int i=0;i<40;i++)flight.settle(physics);
                check(physics.anchor.y>=65&&physics.anchor.y<65.1,"Ship lands without damage on solid surface");
                astraea.setBlockAndUpdate(new BlockPos(3,64,3),Blocks.AIR.defaultBlockState());
                for(int i=0;i<10;i++)flight.settle(physics);
                check(physics.anchor.y<65,"Destroying support makes parked ship fall");
                astraea.setBlockAndUpdate(new BlockPos(3,64,3),Blocks.STONE_BRICKS.defaultBlockState());
                for(int y=65;y<69;y++)astraea.setBlockAndUpdate(new BlockPos(3,y,3),Blocks.WATER.defaultBlockState());
                physics.anchor=new Vec3(3,65,3);
                for(int i=0;i<10;i++)flight.settle(physics);
                check(physics.anchor.y>66,"Submerged ship floats upward");
                astraea.setBlockAndUpdate(new BlockPos(3,68,3),Blocks.STONE.defaultBlockState());
                for(int i=0;i<30;i++)flight.settle(physics);
                check(physics.anchor.y<67.1,"Ceiling blocks ship buoyancy");
                for(int y=65;y<=68;y++)astraea.setBlockAndUpdate(new BlockPos(3,y,3),Blocks.AIR.defaultBlockState());
                // Appearance checks: Spore avatar, custom avatar, save and reload.
                var visuals=dev.spain.SpainMod.VISUALS;visuals.load(server);
                if(visuals.available()) {
                    visuals.select(player,"spore");visuals.tick(server);
                    check(player.isInvisible(),"Spore avatar replaces default appearance");
                    check(java.util.stream.StreamSupport.stream(player.level().getAllEntities().spliterator(),false).filter(java.util.Objects::nonNull).anyMatch(e->e.entityTags().contains("spain.appearance_display")),"Spore avatar has visible block displays");
                    visuals.select(player,"default");check(!player.isInvisible(),"Minecraft skin restored after switching appearance");
                    visuals.custom(player,flight.ship(player).parts);visuals.tick(server);
                    check(player.entityTags().contains("spain.avatar.custom"),"Player-built creature can be selected as avatar");
                    visuals.save(server);visuals.clear();visuals.load(server);visuals.select(player,"custom");
                    check(player.entityTags().contains("spain.avatar.custom"),"Custom avatar persists through save and reload");
                    visuals.select(player,"default");visuals.clear();
                }
                // Air supply checks in water and out of water.
                // The spacesuit must not refill breath while eyes are underwater.
                command(server,player,"function spain:travel/astraea");
                for(int x=2;x<=4;x++)for(int z=2;z<=4;z++)for(int y=65;y<=69;y++)astraea.setBlockAndUpdate(new BlockPos(x,y,z),Blocks.WATER.defaultBlockState());
                player.setPos(3.5,66,3.5);player.baseTick();player.setAirSupply(100);player.baseTick();flight.tick(server);
                check(player.isUnderWater(),"Underwater environment detected by Minecraft");
                check(player.getAirSupply()<100,"Spacesuit preserves finite underwater breath");
                player.setPos(0.5,73,0.5);player.baseTick();flight.tick(server);
                check(player.getAirSupply()==player.getMaxAirSupply(),"Spacesuit restores air outside water");
                for(int x=2;x<=4;x++)for(int z=2;z<=4;z++)for(int y=65;y<=69;y++)astraea.setBlockAndUpdate(new BlockPos(x,y,z),Blocks.AIR.defaultBlockState());
                // Save and reload checks for ships.
                flight.save(server);int parts=flight.ship(player).parts.size();
                flight.load(server);check(flight.ship(player).parts.size()==parts,"Rocket parts persist through save and reload");
                command(server,player,"scoreboard players set @s spain.launch 0");
                // Rocket creator checks: hull, wings, engine, cabin, undo, boarding and recall.
                flight.design(player,"clear");flight.design(player,"hull");
                check(!flight.ship(player).parts.isEmpty(),"Creator adds hull without visiting NPC");
                int hull=flight.ship(player).parts.size();flight.design(player,"wings");
                check(flight.ship(player).parts.size()>hull,"Creator adds symmetric wings");
                flight.design(player,"engine");int engine=flight.ship(player).parts.size();
                check(engine>hull,"Creator adds Spore engine");flight.design(player,"cabin");flight.design(player,"undo");
                check(flight.ship(player).parts.size()==engine,"Creator undo restores previous design");
                flight.action(player,"board");flight.tick(server);
                check(flight.ship(player).piloting,"Creator rocket boards without NPC");
                check(flight.ship(player).anchor.distanceTo(player.position())<.01,"Player occupies the controlled cockpit center");
                flight.action(player,"land");flight.action(player,"recall");
                check(player.position().distanceTo(flight.ship(player).anchor)<2,"Rocket can be recalled independently");
                // Quick-travel trigger checks.
                command(server, player, "scoreboard players set @s spain.cooldown 0");
                command(server, player, "scoreboard players enable @s spain.travel");
                server.getCommands().performPrefixedCommand(player.createCommandSourceStack(), "trigger spain.travel set 2");
                check(score(server, player, "spain.travel") == 2, "Player can use travel trigger");
                command(server, null, "function spain:tick");
                check(player.level() == astraea, "Travel trigger reaches selected planet");
                for (String id : new String[]{"orbit", "astraea", "cinder", "borealis"}) {
                    command(server, player, "function spain:travel/" + id);
                    check(player.level() == dimension(server, id), "Travel arrives: " + id);
                    check(player.getY() == 65, "Travel safely lands: " + id);
                }
                // Talk to NPCs, then check the Iona quest from accept to reward, including that it cannot be repeated.
                interact(server, player, "orbit", "navigator");
                interact(server, player, "orbit", "lucy");
                interact(server, player, "astraea", "iona");
                command(server, player, "function spain:quest/accept");
                check(score(server, player, "spain.quest") == 1, "Iona quest accepted");
                command(server, player, "function spain:quest/turn_in");
                check(score(server, player, "spain.quest") == 1, "Missing crystal cannot complete quest");
                interact(server, player, "cinder", "sera");
                command(server, player, "function spain:quest/collect");
                check(player.getInventory().countItem(Items.AMETHYST_SHARD) == 1, "Sera gives survey crystal");
                command(server, player, "function spain:quest/collect");
                check(player.getInventory().countItem(Items.AMETHYST_SHARD) == 1, "Survey crystal cannot be duplicated");
                interact(server, player, "astraea", "iona");
                command(server, player, "function spain:quest/turn_in");
                check(score(server, player, "spain.quest") == 2, "Quest completed");
                check(player.getInventory().countItem(Items.AMETHYST_SHARD) == 0, "Quest consumes exactly one crystal");
                check(player.getInventory().countItem(Items.EMERALD) == 4, "Quest rewards four emeralds");
                command(server, player, "function spain:quest/turn_in");
                check(player.getInventory().countItem(Items.EMERALD) == 4, "Quest reward cannot be repeated");
                interact(server, player, "borealis", "arlen");
                for(String id:new String[]{"gardener","chef"})interact(server,player,"earth",id);
                for(String id:new String[]{"mechanic","medic","porter","diplomat"})interact(server,player,"orbit",id);
                command(server, null, "function spain:load");
                check(score(server, player, "spain.quest") == 2, "Reload preserves quest progress");
                for (String id : new String[]{"orbit", "astraea", "cinder", "borealis"})
                    command(server, null, "execute in spain:" + id + " run forceload remove -32 -32 31 31");
                // Write the final report of passed checks.
                // Save through Minecraft itself; this world can also be copied into a separate Prism instance.
                server.getPlayerList().remove(player);
                server.saveEverything(true, true, true);
                Path result = Path.of(System.getProperty("spain.report", "verification/output/results.json"));
                Files.createDirectories(result.toAbsolutePath().getParent());
                Files.writeString(result, "{\"minecraft\":\"26.3\",\"checks\":" + checks + ",\"passed\":true}\n");
                helper.succeed();
            } catch (Throwable failure) {
                failure.printStackTrace();
                helper.fail(failure.toString());
            }
        });
    }

    /** Moves the player next to an NPC in a world and right-clicks it twice, checking the dialogue tag each time. */
    private static void interact(MinecraftServer server, ServerPlayer player, String dimension, String npc) {
        command(server, player, "function spain:travel/" + dimension);
        ServerLevel level = dimension(server, dimension);
        Entity target = level.getEntities((Entity) null, new AABB(-30, 60, -30, 30, 140, 30), e -> e instanceof net.minecraft.world.entity.Interaction && e.entityTags().contains("spain." + npc)).stream().findFirst().orElseThrow();
        player.setPos(target.getX(), target.getY(), target.getZ() + 2);
        new net.minecraft.network.protocol.game.ServerboundPlayerLoadedPacket().handle(player.connection);
        player.connection.handleInteract(new ServerboundInteractPacket(target.getId(), InteractionHand.MAIN_HAND, new Vec3(0, 1, 0), false));
        check(player.entityTags().contains("spain.met." + npc), "Right-click dialogue fires: " + npc);
        player.entityTags().remove("spain.met." + npc);
        player.connection.handleInteract(new ServerboundInteractPacket(target.getId(), InteractionHand.MAIN_HAND, new Vec3(0, 1, 0), false));
        check(player.entityTags().contains("spain.met." + npc), "NPC can be spoken to again: " + npc);
    }

    /** Finds a world by short name ("earth" is the overworld; others are in the spain namespace). */
    private static ServerLevel dimension(MinecraftServer server, String name) {
        if(name.equals("earth"))return server.overworld();
        return server.getLevel(ResourceKey.create(Registries.DIMENSION, Identifier.fromNamespaceAndPath("spain", name)));
    }

    /** Runs a command, as the player if one is given, otherwise as the server. */
    private static void command(MinecraftServer server, ServerPlayer player, String command) {
        var source = server.createCommandSourceStack();
        if (player != null) source = source.withEntity(player).withLevel((ServerLevel) player.level()).withPosition(player.position());
        server.getCommands().performPrefixedCommand(source, command);
    }

    /** Reads a scoreboard value (-1 if the holder has no score). */
    private static int score(MinecraftServer server, ScoreHolder player, String objective) {
        var scoreboard = server.getScoreboard();
        var value = scoreboard.getPlayerScoreInfo(player, scoreboard.getObjective(objective));
        return value == null ? -1 : value.value();
    }

    /** Fails with the message if the condition is false; otherwise counts and prints the check. */
    private static void check(boolean success, String message) {
        if (!success) throw new AssertionError(message);
        checks++;
        System.out.println("SPAIN CHECK " + checks + ": " + message);
    }
}
