// ==============================================================================
// Program: ShipCameraMixin.java
// Programmer: Ethan-da-Tech-Wizard
// Last Modified: November 19, 2026
// Purpose: Bytecode mixin transformer intercepting vanilla Minecraft camera zoom calculations.
//          Modifies Camera.getMaxZoom via SpongePowered ASM injection at method entry to override
//          view distances when spacecraft piloting mode is active, while preserving terrain clipping.
// ==============================================================================

// Fit in the mod: a Mixin (a Fabric/Sponge technique for changing vanilla methods at load time). It is listed in
// src/main/resources/spain.client.mixins.json, so it only applies on the client. It makes the third-person
// camera sit SpainClient.distance blocks behind a piloted rocket instead of vanilla's fixed 4 blocks.
package dev.spain.mixin;
import dev.spain.SpainClient;
import net.minecraft.client.Camera;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyVariable;

// How it works: Camera.getMaxZoom(float) takes the wanted camera distance and returns the largest distance that does not clip into blocks. Replacing the
// argument at the very start (@At("HEAD")) leaves vanilla's collision test and rotation logic in charge, so the camera
// still stops at walls; only the requested distance changes.
/** Retains Minecraft's terrain collision and camera rotation; changes cockpit chase distance. */
@Mixin(Camera.class)
public abstract class ShipCameraMixin {
    // argsOnly=true: only the method parameter is replaced, never a local variable of the same type. If a Minecraft update
    // renames or changes getMaxZoom, the mixin fails at startup, which is why it is kept this small.
    @ModifyVariable(method="getMaxZoom",at=@At("HEAD"),argsOnly=true)
    // The `spain$` prefix is Mixin's convention for names added to a vanilla class, preventing clashes with its own methods. While piloting, return the mod's distance; otherwise pass vanilla's value through.
    private float spain$shipDistance(float distance){return SpainClient.piloting?SpainClient.distance:distance;}
}
