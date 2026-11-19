// ==============================================================================
// Program: ShipCameraMixin.java
// Programmer: Ethan-da-Tech-Wizard
// Last Modified: November 19, 2026
// Purpose: Bytecode mixin transformer intercepting vanilla Minecraft camera zoom calculations.
//          Modifies Camera.getMaxZoom via SpongePowered ASM injection at method entry to override
//          view distances when spacecraft piloting mode is active, while preserving terrain clipping.
// ==============================================================================

package dev.spain.mixin;
import dev.spain.SpainClient;
import net.minecraft.client.Camera;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyVariable;
/** Retains Minecraft's terrain collision and camera rotation; changes cockpit chase distance. */
@Mixin(Camera.class)
public abstract class ShipCameraMixin {
    @ModifyVariable(method="getMaxZoom",at=@At("HEAD"),argsOnly=true)
    private float spain$shipDistance(float distance){return SpainClient.piloting?SpainClient.distance:distance;}
}
