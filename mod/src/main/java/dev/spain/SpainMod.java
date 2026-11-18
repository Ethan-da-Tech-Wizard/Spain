// Program: Spain - SpainMod.java
// Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
// Last Modified: 2026-11-18
// Purpose: Main entry point of the Spain Fabric mod: registers the flight packet, game event hooks and the /spain commands.
// Package for the mod.
package dev.spain;
// Imports: Fabric events and Minecraft's command classes.
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
/** Runs on both client and server when the mod loads. */
public final class SpainMod implements ModInitializer {
    // One shared flight system and one shared appearance system for the whole server.
    public static final FlightSystem FLIGHT = new FlightSystem();
    public static final SporeVisuals VISUALS = new SporeVisuals();
    /** Wires everything together when the mod starts. */
    @Override public void onInitialize() {
        // Tell Fabric about the FlightView packet (server to client).
        net.fabricmc.fabric.api.networking.v1.PayloadTypeRegistry.clientboundPlay().register(FlightView.TYPE,FlightView.CODEC);
        // Give the flight system a way to send that packet, only to clients that understand it.
        FLIGHT.view=(player,payload)->{
            if(net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking.canSend(player,FlightView.TYPE))
                net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking.send(player,payload);
        };
        // On server start, load saved ships and avatars.
        ServerLifecycleEvents.SERVER_STARTED.register(FLIGHT::load);
        ServerLifecycleEvents.SERVER_STARTED.register(VISUALS::load);
        // Every tick, update ships and appearance displays.
        ServerTickEvents.END_SERVER_TICK.register(FLIGHT::tick);
        ServerTickEvents.END_SERVER_TICK.register(VISUALS::tick);
        // On server stop, save everything and remove temporary displays.
        ServerLifecycleEvents.SERVER_STOPPING.register(FLIGHT::save);
        ServerLifecycleEvents.SERVER_STOPPING.register(server -> { VISUALS.save(server); VISUALS.clear(); });
        // Build the /spain command tree.
        CommandRegistrationCallback.EVENT.register((dispatcher, context, selection) -> {
            // /spain create opens the rocket creator.
            var command=Commands.literal("spain");
            command.then(Commands.literal("create").executes(c->{FLIGHT.action(c.getSource().getPlayerOrException(),"create");return 1;}));
            // /spain design <part> for each creator button.
            var design=Commands.literal("design");
            for(String part:new String[]{"hull","wings","engine","cabin","stretch","rotate","undo","clear"})
                design.then(Commands.literal(part).executes(c->FLIGHT.design(c.getSource().getPlayerOrException(),part)));
            command.then(design);
            // /spain avatar default|spore|custom|capture.
            var avatar=Commands.literal("avatar");
            for(String mode:new String[]{"default","spore","custom"})
                avatar.then(Commands.literal(mode).executes(c -> {VISUALS.select(c.getSource().getPlayerOrException(),mode);return 1;}));
            avatar.then(Commands.literal("capture").executes(c -> FLIGHT.captureAvatar(c.getSource().getPlayerOrException())));
            command.then(avatar);
            // Simple /spain commands that all go to FlightSystem.action.
            for (String name : new String[]{"capture","board","land","help","spore","recall"})
                command.then(Commands.literal(name).executes(c -> FLIGHT.action(c.getSource().getPlayerOrException(),name)));
            // /spain corner1 and corner2 take a block position (X Y Z).
            for (int n=1;n<=2;n++) {
                final int corner=n;
                command.then(Commands.literal("corner"+n).then(Commands.argument("position",BlockPosArgument.blockPos()).executes(c -> {
                    FLIGHT.corner(c.getSource().getPlayerOrException(),corner,BlockPosArgument.getBlockPos(c,"position")); return 1;
                })));
            }
            // Finish by registering the whole command.
            dispatcher.register(command);
        });
        // Log a line so the startup is visible in the game log.
        org.slf4j.LoggerFactory.getLogger("Spain").info("Spain flight system ready: /spain help");
    }
}
