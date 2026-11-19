// ==============================================================================
// Program: FlightView.java
// Programmer: Ethan-da-Tech-Wizard
// Last Modified: November 19, 2026
// Purpose: Custom network packet payload and binary codec for spacecraft camera synchronization.
//          Implements Mojang CustomPacketPayload contract using RegistryFriendlyByteBuf stream codecs.
//          Guarantees zero-allocation serialization of piloting state and third-person zoom distances.
// ==============================================================================

// Fit in the mod: the one network message of the mod. FlightSystem (server) sends it to a player whenever their
// piloting state or chase distance changes (registered in SpainMod.onInitialize); SpainClient (client)
// receives it. It is a Java record, so the constructor, getters (piloting(), distance()), equals and hashCode come for free.
// Wire format: 1 byte (boolean) then a 4-byte float, 5 bytes in total.
package dev.spain;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;

/** Server-to-client packet: whether the player is piloting, and the chase-camera distance in blocks. */
public record FlightView(boolean piloting,float distance) implements CustomPacketPayload {
    // Packet identifier "spain:flight_view". The same constant is used to register, send and receive it, so the id is defined once.
    public static final Type<FlightView> TYPE=new Type<>(net.minecraft.resources.Identifier.parse("spain:flight_view"));

    // Serializer and deserializer pair: write boolean then float, read them back in the same order. Order must never differ between the two sides.
    public static final StreamCodec<RegistryFriendlyByteBuf,FlightView> CODEC=StreamCodec.of((buf,value)->{buf.writeBoolean(value.piloting);buf.writeFloat(value.distance);},buf->new FlightView(buf.readBoolean(),buf.readFloat()));

    // Required by CustomPacketPayload so Minecraft can look up the codec for an incoming packet.
    @Override public Type<FlightView> type(){return TYPE;}
}
