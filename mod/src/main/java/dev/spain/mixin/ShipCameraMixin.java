// Program: Spain - ShipCameraMixin.java
// Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
// Last Modified: 2026-11-18
// Purpose: Mixin that lengthens the third-person camera distance while the player is piloting a ship.
// Package for mixins (small patches into Minecraft's own classes).
package dev.spain.mixin;
// Imports: our client state, Minecraft's Camera and the Mixin annotations.
import dev.spain.SpainClient;
import net.minecraft.client.Camera;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyVariable;
// This patches the Camera class.
/** Retains Minecraft's terrain collision and camera rotation; changes cockpit chase distance. */
// Target class: Minecraft's Camera.
@Mixin(Camera.class)
public abstract class ShipCameraMixin {
    // At the start of getMaxZoom, replace its distance argument with our own.
    @ModifyVariable(method="getMaxZoom",at=@At("HEAD"),argsOnly=true)
    // If piloting, use the ship camera distance; otherwise keep the normal value.
    private float spain$shipDistance(float distance){return SpainClient.piloting?SpainClient.distance:distance;}
}
