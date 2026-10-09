package dev.spain;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
public final class SpainMod implements ModInitializer {
    public static final FlightSystem FLIGHT = new FlightSystem();
    public static final SporeVisuals VISUALS = new SporeVisuals();
    @Override public void onInitialize() {
        net.fabricmc.fabric.api.networking.v1.PayloadTypeRegistry.clientboundPlay().register(FlightView.TYPE,FlightView.CODEC);
        FLIGHT.view=(player,payload)->{
            if(net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking.canSend(player,FlightView.TYPE))
                net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking.send(player,payload);
        };
        ServerLifecycleEvents.SERVER_STARTED.register(FLIGHT::load);
        ServerLifecycleEvents.SERVER_STARTED.register(VISUALS::load);
        ServerTickEvents.END_SERVER_TICK.register(FLIGHT::tick);
        ServerTickEvents.END_SERVER_TICK.register(VISUALS::tick);
        ServerLifecycleEvents.SERVER_STOPPING.register(FLIGHT::save);
        ServerLifecycleEvents.SERVER_STOPPING.register(server -> { VISUALS.save(server); VISUALS.clear(); });
        CommandRegistrationCallback.EVENT.register((dispatcher, context, selection) -> {
            var command=Commands.literal("spain");
            command.then(Commands.literal("create").executes(c->{FLIGHT.action(c.getSource().getPlayerOrException(),"create");return 1;}));
            var design=Commands.literal("design");
            for(String part:new String[]{"hull","wings","engine","cabin","stretch","rotate","undo","clear"})
                design.then(Commands.literal(part).executes(c->FLIGHT.design(c.getSource().getPlayerOrException(),part)));
            command.then(design);
            var avatar=Commands.literal("avatar");
            for(String mode:new String[]{"default","spore","custom"})
                avatar.then(Commands.literal(mode).executes(c -> {VISUALS.select(c.getSource().getPlayerOrException(),mode);return 1;}));
            avatar.then(Commands.literal("capture").executes(c -> FLIGHT.captureAvatar(c.getSource().getPlayerOrException())));
            command.then(avatar);
            for (String name : new String[]{"capture","board","land","help","spore","recall"})
                command.then(Commands.literal(name).executes(c -> FLIGHT.action(c.getSource().getPlayerOrException(),name)));
            for (int n=1;n<=2;n++) {
                final int corner=n;
                command.then(Commands.literal("corner"+n).then(Commands.argument("position",BlockPosArgument.blockPos()).executes(c -> {
                    FLIGHT.corner(c.getSource().getPlayerOrException(),corner,BlockPosArgument.getBlockPos(c,"position")); return 1;
                })));
            }
            dispatcher.register(command);
        });
        org.slf4j.LoggerFactory.getLogger("Spain").info("Spain flight system ready: /spain help");
    }
}
