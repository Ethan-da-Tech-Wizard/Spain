// ==============================================================================
// Program: SpainClient.java
// Programmer: Ethan-da-Tech-Wizard
// Last Modified: November 19, 2026
// Purpose: Fabric client mod initializer governing keybinding input and camera perspective state.
//          Registers custom payload receivers for FlightView packets, manages smooth camera
//          transitions between first-person cockpit and third-person chase cameras, and restores
//          client view settings upon disconnect or pilot dismount.
// ==============================================================================

package dev.spain;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayConnectionEvents;
import net.minecraft.client.CameraType;
public final class SpainClient implements ClientModInitializer {
    public static boolean piloting;
    public static float distance=12;
    private static CameraType previous=CameraType.FIRST_PERSON;
    @Override public void onInitializeClient() {
        ClientPlayNetworking.registerGlobalReceiver(FlightView.TYPE,(payload,context)->context.client().execute(()->{
            var options=context.client().options;
            if(payload.piloting()&&!piloting){previous=options.getCameraType();options.setCameraType(CameraType.THIRD_PERSON_BACK);}
            if(!payload.piloting()&&piloting)options.setCameraType(previous);
            piloting=payload.piloting();distance=Math.clamp(payload.distance(),6,128);
        }));
        ClientPlayConnectionEvents.DISCONNECT.register((handler,client)->{if(piloting)client.options.setCameraType(previous);piloting=false;});
    }
}
