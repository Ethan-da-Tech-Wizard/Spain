# Voxel Space Game: Save File Format & Serialization

This document designs a high-performance save file format layout for the Java voxel game, optimized for storing customized voxel planets, placed blocks, outposts, and spaceship configurations without causing garbage collection spikes.

---

## 💾 1. The Serialization Goal

Voxel worlds generate massive amounts of data. A single planet face of $256 \times 256 \times 128$ blocks contains $8,388,608$ voxels. 
To keep load times under $50\text{ms}$ and save file sizes under $5\text{MB}$:
1.  **Binary Format**: Avoid JSON/XML for voxel block grids due to string parsing overhead. Use a compressed binary layout.
2.  **Run-Length Encoding (RLE)**: Compress runs of identical blocks (e.g., empty space or underground stone blocks).
3.  **GZIP Compression**: Stream the final binary arrays through Java’s native `GZIPOutputStream` for deep compression.

---

## 📁 2. File System Layout

The save directory structure for a player's galaxy profile:

```
/saves/[profile_name]/
  ├── player.dat          <- Player position, inventory, locked coordinates (Binary)
  ├── spaceship.dat       <- Voxel rocket layout, custom blocks, components (Binary)
  ├── galaxy.dat          <- List of discovered systems and custom placed planets (JSON)
  └── planets/
       ├── [planet_id]_face0.chunk  <- Compressed voxel chunks for Face 0 (North)
       ├── [planet_id]_face1.chunk  <- Compressed voxel chunks for Face 1 (South)
       └── ...
```

---

## ⚙ 3. Binary Chunk Format (`.chunk` Layout)

Each planet face is divided into $16 \times 16 \times 16$ voxel Chunks ($4,096$ blocks). The binary layout of a single chunk file contains a header followed by compressed block runs.

### Binary Stream Specification

| Byte Offset | Data Type | Field Name | Description |
| :--- | :--- | :--- | :--- |
| **0 - 3** | `int` | `MAGIC_NUMBER` | File signature verification (`0x53465043` = "SFPC" / Starforge Planet Chunk). |
| **4 - 7** | `int` | `VERSION` | Format version number for backward compatibility. |
| **8 - 11** | `int` | `CHUNK_X` | Relative X coordinate of this chunk in the face grid. |
| **12 - 15** | `int` | `CHUNK_Y` | Relative Y coordinate. |
| **16 - 19** | `int` | `CHUNK_Z` | Relative Z coordinate. |
| **20 - 23** | `int` | `PALETTE_SIZE` | Number of unique block types used in this chunk. |
| **Variable** | `String[]` | `PALETTE` | Map of palette indices to block IDs (e.g. `0 -> "air"`, `1 -> "grass"`, `2 -> "plasma_ore"`). |
| **Variable** | `byte[]` | `BLOCK_DATA` | **GZIP Compressed RLE Block Stream** (defined below). |

### Run-Length Encoding (RLE) Stream Structure
Instead of writing $4,096$ individual block IDs, blocks are serialized as pairs of `[palette_index, run_length]`:

```
[Byte 0: Palette ID] -> [Byte 1: Run Count (1-255)]
```

*   *Example:* A sequence of 120 Air blocks followed by 5 Iron Ore blocks is stored in just 4 bytes:
    `[0x00, 0x78]` (Air index 0, length 120), `[0x02, 0x05]` (Iron index 2, length 5).

---

## 🚀 4. Voxel Spaceship Serialization (`spaceship.dat`)

Unlike planets, spaceships are small ($16 \times 16 \times 32$ block bounding box) and carry functional metadata (thruster power, cargo inventory contents).

### Spaceship File Structure
We use a key-value binary layout similar to Minecraft's **NBT (Named Binary Tag)** format:

```
CompoundTag("Spaceship") {
    StringTag("ShipName"): "Starhawk V"
    FloatTag("SpeedMultiplier"): 1.25
    IntTag("MaxCargo"): 64
    
    // The raw block layout
    ByteArrayTag("Blocks"): [ ... RLE Encoded Grid ... ]
    
    // Inventory items inside cargo chests
    ListTag("CargoHold") {
        CompoundTag() {
            StringTag("Item"): "metal_ingot"
            IntTag("Count"): 32
        },
        CompoundTag() {
            StringTag("Item"): "glowing_crystal"
            IntTag("Count"): 12
        }
    }
}
```
*   **Java Implementation**: Custom `DataInputStream` and `DataOutputStream` handlers parse these tags directly into JVM records, minimizing garbage collector allocations during ship dry-docking.
