// Program: Spain - FlightView.java
// Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
// Last Modified: 2026-11-18
// Purpose: Network message (packet) sent from the server to a player's game client to switch the ship chase camera on or off and set its distance.
// Package for the mod.
package dev.spain;
// Imports for Minecraft's custom packet system.
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
/** The packet contents: whether the player is piloting and how far back the camera should sit. */
public record FlightView(boolean piloting,float distance) implements CustomPacketPayload {
    // Unique id of this packet type.
    public static final Type<FlightView> TYPE=new Type<>(net.minecraft.resources.Identifier.parse("spain:flight_view"));
    // How to write the two fields to bytes and read them back (boolean, then float).
    public static final StreamCodec<RegistryFriendlyByteBuf,FlightView> CODEC=StreamCodec.of((buf,value)->{buf.writeBoolean(value.piloting);buf.writeFloat(value.distance);},buf->new FlightView(buf.readBoolean(),buf.readFloat()));
    // Required by Minecraft: tells it which packet type this is.
    @Override public Type<FlightView> type(){return TYPE;}
}
