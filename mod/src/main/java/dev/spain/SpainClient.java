// Program: Spain - SpainClient.java
// Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
// Last Modified: 2026-11-18
// Purpose: Client-side setup that changes the camera to a chase view when the server says the player is piloting a ship, and restores it afterward.
// Package for the mod.
package dev.spain;
// Imports: Fabric client hooks and Minecraft's camera type.
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayConnectionEvents;
import net.minecraft.client.CameraType;
/** Entry point that runs only on the player's own game client. */
public final class SpainClient implements ClientModInitializer {
    // Shared state: whether we are piloting and how far back the camera is. The camera mixin reads these.
    public static boolean piloting;
    public static float distance=12;
    // The camera view the player had before boarding, so it can be put back.
    private static CameraType previous=CameraType.FIRST_PERSON;
    /** Registers the packet receiver and the disconnect handler. */
    @Override public void onInitializeClient() {
        // When a FlightView packet arrives, run on the main client thread.
        ClientPlayNetworking.registerGlobalReceiver(FlightView.TYPE,(payload,context)->context.client().execute(()->{
            // Boarding: save the current camera and switch to third person behind.
            // Leaving: restore the saved camera.
            // Then store the new state, limiting the distance to 6..128.
            var options=context.client().options;
            if(payload.piloting()&&!piloting){previous=options.getCameraType();options.setCameraType(CameraType.THIRD_PERSON_BACK);}
            if(!payload.piloting()&&piloting)options.setCameraType(previous);
            piloting=payload.piloting();distance=Math.clamp(payload.distance(),6,128);
        }));
        // If the player disconnects while piloting, restore the camera and clear the flag.
        ClientPlayConnectionEvents.DISCONNECT.register((handler,client)->{if(piloting)client.options.setCameraType(previous);piloting=false;});
    }
}
