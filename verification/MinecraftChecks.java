// ==============================================================================
// Program: MinecraftChecks.java
// Programmer: Ethan-da-Tech-Wizard
// Last Modified: November 19, 2026
// Purpose: Mojang GameTest headless assertion suite validating mod registration contracts.
//          Executes within the vanilla server runtime to programmatically assert block state registries,
//          entity display spawning capabilities, and multi-dimensional coordinate bounds.
// ==============================================================================

// Fit in the repo: the in-game test probe. verification/run_checks.py compiles this file against Minecraft 26.3's own jars and the
// built mod classes, then runs it as the main class. It starts Mojang's real headless GameTest server with the Spain
// data pack loaded and registers ONE test function, spain:core (the data-pack side test_instance json points at it).
// That function plays through the game like a person would: it checks dimensions and NPCs, simulates a player
// joining, talks to NPCs, builds, boards and flies a ship, uses travel triggers, completes the quest and saves. If any
// check() fails an AssertionError stops the test and the run fails; if all pass it writes results.json
// ({"minecraft":"26.3","checks":N,"passed":true}) that tools/install_prism.py later requires.
// //
// Why a probe and not unit tests: almost all behaviour lives in data-pack functions and in the mod, which can only be trusted
// when run by the real game, so the probe uses real server, real commands, real packets and a real saved world (the world
// it leaves behind is reused as the starter world).
// //
// Timing: the test lets the world build for 100 ticks (5 s), then at tick 140 runs every check in one block; that is
// intentional, because checks depend on each other (for example the quest steps).
// Limits: it uses reflection on Mojang internals to register the test (see main), so a Minecraft update can break
// the probe even if the mod itself is fine. Output lines are "SPAIN CHECK n: <what was proven>".
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

// (See the file header for the overall design.)
/** Runs against Mojang's real server; no replacement movement, NPC, save or command engine. */
public final class MinecraftChecks {
    // Number of passed checks so far; printed in each line and stored in the result report.
    private static int checks;

    // Start-up sequence: initialise Minecraft's registries, add our test to the (normally frozen) test-function registry,
    // freeze it again, and hand over to Mojang's GameTest server runner with the command line arguments from run_checks.py.
    public static void main(String[] args) throws Exception {
        // Detect the game version and load all built-in registries; required before any Minecraft class is used.
        SharedConstants.tryDetectVersion();
        net.minecraft.server.Bootstrap.bootStrap();
        // This standalone probe has no loader bootstrap hook. Open only the test-function
        // registry to install its check, then freeze it again before loading any worlds.

        // Registries are locked after bootstrap. Normally a mod adds entries before that using the loader's hook; this standalone
        // program has none, so reflection briefly unlocks the test-function registry, registers the test, and (in `finally`) locks it again even on failure.
        var frozen = net.minecraft.core.MappedRegistry.class.getDeclaredField("frozen");
        frozen.setAccessible(true);
        frozen.setBoolean(BuiltInRegistries.TEST_FUNCTION, false);
        try {
            java.util.function.Consumer<GameTestHelper> check = MinecraftChecks::test;
            var holder = Registry.registerForHolder(BuiltInRegistries.TEST_FUNCTION, Identifier.fromNamespaceAndPath("spain", "core"), check);

            // registerForHolder leaves the entry unbound (no value yet); binding it by reflection completes the registration so lookups find the function.
            var bind = net.minecraft.core.Holder.Reference.class.getDeclaredMethod("bindValue", Object.class);
            bind.setAccessible(true);
            bind.invoke(holder, check);
        } finally {
            frozen.setBoolean(BuiltInRegistries.TEST_FUNCTION, true);
        }

        // Runs the server and the tests, then exits; the lambda is a callback (unused) for finished tests.
        GameTestMainUtil.runGameTestServer(args, ignored -> {});
    }

    // The test body. GameTestHelper gives access to the server, the level and the tick scheduler.
    private static void test(GameTestHelper helper) {
        // Tick 100: force-load the centre chunks of every dimension so the pack's builders (which run from a scheduled function)
        // can place blocks and spawn NPCs while the test waits. Without a player nearby those chunks would not load.
        helper.runAtTickTime(100, () -> {
            command(helper.getLevel().getServer(), null, "execute in minecraft:overworld run forceload add -32 -32 31 31");
            for (String id : new String[]{"orbit", "astraea", "cinder", "borealis"})
                command(helper.getLevel().getServer(), null, "execute in spain:" + id + " run forceload add -32 -32 31 31");
        });

        // Tick 140: the whole checking sequence. Wrapped in try/catch so any failure (assertion or crash) is reported with a stack trace and fails the test.
        helper.runAtTickTime(140, () -> {
            try {
                MinecraftServer server = helper.getLevel().getServer();

                // World generation checks: the build finished, each dimension exists, its landing pad is solid and has air above for a player to stand in.
                check(score(server, ScoreHolder.forNameOnly("#built"), "spain.state") == 2, "Cities finish building");
                for (String id : new String[]{"orbit", "astraea", "cinder", "borealis"}) {
                    ServerLevel level = dimension(server, id);
                    check(level != null, "Dimension exists: " + id);
                    check(!level.getBlockState(new BlockPos(0, 64, 0)).isAir(), "Landing pad exists: " + id);
                    check(level.getBlockState(new BlockPos(0, 65, 0)).isAir(), "Landing headroom: " + id);
                }
                for (String id : new String[]{"earth","orbit","astraea","cinder","borealis"}) {
                    // Exactly one set of NPCs per world: the upgrade functions must not duplicate residents (4 on Earth, 6 in orbit, 1 on each planet).
                    var residents=dimension(server,id).getEntities((Entity)null,new AABB(-30,60,-30,30,140,30),e->e instanceof net.minecraft.world.entity.npc.villager.Villager&&e.entityTags().contains("spain.npc"));
                    int expected=id.equals("earth")?4:id.equals("orbit")?6:1;
                    check(residents.size()==expected,"NPCs spawn exactly once: "+id);
                }
                ServerLevel astraea = dimension(server, "astraea");
                if (Boolean.getBoolean("spain.imported"))
                    check(!astraea.getBlockState(new BlockPos(8, 65, 10)).isAir(), "Local imported crate is placed");

                // Reload safety: place a block as if a player built it, run the pack's load function again (what /reload does) and check that nothing was rebuilt over it.
                astraea.setBlockAndUpdate(new BlockPos(2, 65, 2), Blocks.DIAMOND_BLOCK.defaultBlockState());
                command(server, null, "function spain:load");
                check(astraea.getBlockState(new BlockPos(2, 65, 2)).is(Blocks.DIAMOND_BLOCK), "Reload preserves player builds");
                astraea.setBlockAndUpdate(new BlockPos(2, 65, 2), Blocks.AIR.defaultBlockState());

                // Why a real player object: the helper's mock player always reports creative mode, which would hide survival-only behaviour (breath, flight permission), so a normal ServerPlayer with a fake network connection is created and joined.
                // GameTestHelper's mock overrides gameMode() to always return CREATIVE.
                // Use a regular ServerPlayer and Mojang's embedded connection instead.
                var profile = new com.mojang.authlib.GameProfile(java.util.UUID.randomUUID(), "test-mock-player");
                var cookie = net.minecraft.server.network.CommonListenerCookie.createInitial(profile, false);
                ServerPlayer player = new ServerPlayer(server, helper.getLevel(), profile, cookie.clientInformation());
                var connection = new net.minecraft.network.Connection(net.minecraft.network.protocol.PacketFlow.SERVERBOUND);
                new io.netty.channel.embedded.EmbeddedChannel(connection);
                server.getPlayerList().placeNewPlayer(connection, player, cookie);
                player.setGameMode(GameType.SURVIVAL);

                // First-join flow, then Earth start: the player begins in the overworld on the launch platform.
                command(server, player, "function spain:player/welcome");
                command(server, player, "function spain:travel/earth");
                check(player.level()==server.overworld(), "Players begin on Earth");
                check(score(server,ScoreHolder.forNameOnly("#earth"),"spain.state")==2,"Earth city is built");
                check(!server.overworld().getBlockState(new BlockPos(0,96,0)).isAir(),"Earth city has a walkable plaza");

                // Quest chain on Earth: the mayor sends the player to the scientist (launch score 1), the scientist starts the rocket quest (score 2) and activates the spacesuit tag.
                interact(server,player,"earth","mayor");
                check(score(server,player,"spain.launch")==1,"Mayor directs player to scientist");
                interact(server,player,"earth","scientist");
                check(score(server,player,"spain.launch")==2,"Scientist issues rocket quest");
                check(player.entityTags().contains("spain.suit"),"Scientist activates spacesuit");

                // A separate FlightSystem instance (not the mod's static one) is driven by hand: capture the workshop, board, fly above y=280 (must arrive in orbit), quick-travel away mid-flight, return to the station (arrival completes the test), land.
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

                // Physics of a parked ship, using a one-block ship: it must stop on a solid surface without damage, fall when its support is removed, float up in water and be stopped by a ceiling above the water.
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

                // Appearance system: Spore avatar hides the player and creates block displays, "default" restores them, a custom avatar built from the ship persists through a save and reload. Skipped when the local Spore art is not installed.
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

                // Spacesuit rules: flooding a small area, an underwater suited player must still lose air (no infinite breathing underwater) and air must refill outside water.
                // The spacesuit must not refill breath while eyes are underwater.
                command(server,player,"function spain:travel/astraea");
                for(int x=2;x<=4;x++)for(int z=2;z<=4;z++)for(int y=65;y<=69;y++)astraea.setBlockAndUpdate(new BlockPos(x,y,z),Blocks.WATER.defaultBlockState());
                player.setPos(3.5,66,3.5);player.baseTick();player.setAirSupply(100);player.baseTick();flight.tick(server);
                check(player.isUnderWater(),"Underwater environment detected by Minecraft");
                check(player.getAirSupply()<100,"Spacesuit preserves finite underwater breath");
                player.setPos(0.5,73,0.5);player.baseTick();flight.tick(server);
                check(player.getAirSupply()==player.getMaxAirSupply(),"Spacesuit restores air outside water");
                for(int x=2;x<=4;x++)for(int z=2;z<=4;z++)for(int y=65;y<=69;y++)astraea.setBlockAndUpdate(new BlockPos(x,y,z),Blocks.AIR.defaultBlockState());

                // Persistence: save then reload the flight system and compare the number of parts.
                flight.save(server);int parts=flight.ship(player).parts.size();
                flight.load(server);check(flight.ship(player).parts.size()==parts,"Rocket parts persist through save and reload");

                // Rocket creator without any NPC: add hull, wings, engine, cabin, undo, board, check the player sits at the cockpit centre, land and recall.
                command(server,player,"scoreboard players set @s spain.launch 0");
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

                // Travel triggers exactly as a player uses them: enable the trigger, run `trigger spain.travel set 2` as the player (the real permission check) and let the tick function react.
                command(server, player, "scoreboard players set @s spain.cooldown 0");
                command(server, player, "scoreboard players enable @s spain.travel");
                server.getCommands().performPrefixedCommand(player.createCommandSourceStack(), "trigger spain.travel set 2");
                check(score(server, player, "spain.travel") == 2, "Player can use travel trigger");
                command(server, null, "function spain:tick");
                check(player.level() == astraea, "Travel trigger reaches selected planet");

                // Every destination works and the player lands on the pad (y == 65), not inside blocks.
                for (String id : new String[]{"orbit", "astraea", "cinder", "borealis"}) {
                    command(server, player, "function spain:travel/" + id);
                    check(player.level() == dimension(server, id), "Travel arrives: " + id);
                    check(player.getY() == 65, "Travel safely lands: " + id);
                }
                interact(server, player, "orbit", "navigator");
                interact(server, player, "orbit", "lucy");

                // Planet quest "A shared sky" end to end, including abuse cases: turn-in without the crystal fails, the crystal cannot be collected twice, the reward is paid once and the crystal is consumed.
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

                // Reloading must keep quest progress.
                command(server, null, "function spain:load");
                check(score(server, player, "spain.quest") == 2, "Reload preserves quest progress");
                for (String id : new String[]{"orbit", "astraea", "cinder", "borealis"})
                    command(server, null, "execute in spain:" + id + " run forceload remove -32 -32 31 31");
                // Save through Minecraft itself; this world can also be copied into a separate Prism instance.
                server.getPlayerList().remove(player);

                // Save the world through Minecraft itself (flush, suspend autosave, force). The saved world is what run_checks.py inspects afterwards and what the installer copies as the starter world.
                server.saveEverything(true, true, true);
                Path result = Path.of(System.getProperty("spain.report", "verification/output/results.json"));
                Files.createDirectories(result.toAbsolutePath().getParent());

                // Success report, written only after every check passed (a failure throws before this line). A stale report is deleted by run_checks.py beforehand.
                Files.writeString(result, "{\"minecraft\":\"26.3\",\"checks\":" + checks + ",\"passed\":true}\n");
                helper.succeed();
            } catch (Throwable failure) {
                failure.printStackTrace();
                helper.fail(failure.toString());
            }
        });
    }

    /**
     * Simulates a player right-clicking an NPC and checks the dialogue reacts.
     *
     * @param server running test server
     * @param player the (fake) player
     * @param dimension "earth", "orbit", "astraea", "cinder" or "borealis"
     * @param npc NPC id suffix of the entity tag (for example "iona" matches tag spain.iona)
     *
     * Teleports the player next to the NPC's invisible interaction entity and sends the same packet a real click does, then verifies the "met" tag.
     * It clicks twice, removing the tag between clicks, to prove dialogue can be repeated.
     */
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

    /**
     * Returns the level for "earth" (the overworld) or a Spain dimension name; null if it does not exist.
     */
    private static ServerLevel dimension(MinecraftServer server, String name) {
        if(name.equals("earth"))return server.overworld();
        return server.getLevel(ResourceKey.create(Registries.DIMENSION, Identifier.fromNamespaceAndPath("spain", name)));
    }

    /**
     * Runs a command as the server (player == null) or as the given player at their position and dimension.
     */
    private static void command(MinecraftServer server, ServerPlayer player, String command) {
        var source = server.createCommandSourceStack();
        if (player != null) source = source.withEntity(player).withLevel((ServerLevel) player.level()).withPosition(player.position());
        server.getCommands().performPrefixedCommand(source, command);
    }

    /**
     * Reads a scoreboard value; returns -1 if the holder has no score for the objective (distinguishes "unset" from 0).
     */
    private static int score(MinecraftServer server, ScoreHolder player, String objective) {
        var scoreboard = server.getScoreboard();
        var value = scoreboard.getPlayerScoreInfo(player, scoreboard.getObjective(objective));
        return value == null ? -1 : value.value();
    }

    /**
     * Records one assertion: throws AssertionError with the message when false, otherwise counts it and prints "SPAIN CHECK n: message".
     */
    private static void check(boolean success, String message) {
        if (!success) throw new AssertionError(message);
        checks++;
        System.out.println("SPAIN CHECK " + checks + ": " + message);
    }
}
