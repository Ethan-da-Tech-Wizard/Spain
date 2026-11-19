// ==============================================================================
// Program: FlightView.java
// Programmer: Ethan-da-Tech-Wizard
// Last Modified: November 19, 2026
// Purpose: Custom network packet payload and binary codec for spacecraft camera synchronization.
//          Implements Mojang CustomPacketPayload contract using RegistryFriendlyByteBuf stream codecs.
//          Guarantees zero-allocation serialization of piloting state and third-person zoom distances.
// ==============================================================================

package dev.spain;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
public record FlightView(boolean piloting,float distance) implements CustomPacketPayload {
    public static final Type<FlightView> TYPE=new Type<>(net.minecraft.resources.Identifier.parse("spain:flight_view"));
    public static final StreamCodec<RegistryFriendlyByteBuf,FlightView> CODEC=StreamCodec.of((buf,value)->{buf.writeBoolean(value.piloting);buf.writeFloat(value.distance);},buf->new FlightView(buf.readBoolean(),buf.readFloat()));
    @Override public Type<FlightView> type(){return TYPE;}
}
