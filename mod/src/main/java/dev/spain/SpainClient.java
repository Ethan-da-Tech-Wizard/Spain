// ==============================================================================
// Program: SpainClient.java
// Programmer: Ethan-da-Tech-Wizard
// Last Modified: November 19, 2026
// Purpose: Fabric client mod initializer governing keybinding input and camera perspective state.
//          Registers custom payload receivers for FlightView packets, manages smooth camera
//          transitions between first-person cockpit and third-person chase cameras, and restores
//          client view settings upon disconnect or pilot dismount.
// ==============================================================================

// Fit in the mod: client-only entry point (declared as "client" in fabric.mod.json). It receives the
// FlightView packet that FlightSystem sends and reacts by switching the camera to a third-person chase view
// while the player pilots a rocket; ShipCameraMixin then uses `distance` to set how far back that camera sits.
// Not loaded on a dedicated server, so it may use net.minecraft.client classes.
package dev.spain;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayConnectionEvents;
import net.minecraft.client.CameraType;

/** Client-side state and packet receiver for the rocket chase camera. */
public final class SpainClient implements ClientModInitializer {
    // True while the server says this player is flying a ship. Read by ShipCameraMixin on every camera update.
    public static boolean piloting;

    // Chase-camera distance in blocks (default 12; the server sends the real value, clamped to 6..128 here).
    public static float distance=12;

    // The camera mode the player had before boarding (for example first person), restored when they leave the cockpit.
    private static CameraType previous=CameraType.FIRST_PERSON;

    // Registers the packet receiver and a disconnect cleanup.
    @Override public void onInitializeClient() {
        // Packets arrive on the network thread; client().execute(...) moves the work to the main client thread, where touching game options is safe.
        ClientPlayNetworking.registerGlobalReceiver(FlightView.TYPE,(payload,context)->context.client().execute(()->{
            var options=context.client().options;

            // Transition into piloting: remember the old camera and switch to third person, behind the player.
            if(payload.piloting()&&!piloting){previous=options.getCameraType();options.setCameraType(CameraType.THIRD_PERSON_BACK);}

            // Transition out: put the previous camera mode back.
            if(!payload.piloting()&&piloting)options.setCameraType(previous);

            // Math.clamp keeps a bad value from the server within a sensible range (6 to 128 blocks).
            piloting=payload.piloting();distance=Math.clamp(payload.distance(),6,128);
        }));

        // If the player quits or loses the connection mid-flight, restore their camera setting so it is not stuck in third person on the next world.
        ClientPlayConnectionEvents.DISCONNECT.register((handler,client)->{if(piloting)client.options.setCameraType(previous);piloting=false;});
    }
}
