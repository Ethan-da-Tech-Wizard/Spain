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
