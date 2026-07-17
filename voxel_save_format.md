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
  ├── narrative.dat       <- Quest ledger, known dialogue keywords, faction reputation (Binary/NBT)
  ├── restore.dat         <- Last safe save, New-U respawn anchors, restoration template index
  ├── autosaves/
  │    ├── landing.slot
  │    ├── launch.slot
  │    ├── room_transition.slot
  │    └── quest_checkpoint.slot
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

---

## 🧭 5. Narrative, Reputation & Dialogue Persistence (`narrative.dat`)

The narrative save file stores the RPG state that should survive death, ship destruction, and world restoration. This includes quest progress, known dialogue keywords, faction reputation, Lucy trust, and whether faction-impacting actions were witnessed.

### Narrative File Structure
Use the same NBT-style compound approach as `spaceship.dat`:

```
CompoundTag("Narrative") {
    ListTag("KnownKeywords") {
        StringTag("Keyword"): "Planetary Mainframe"
        StringTag("Keyword"): "Glow Crystals"
        StringTag("Keyword"): "Void Syndicate"
    }

    ListTag("JournalEntries") {
        CompoundTag() {
            StringTag("QuestId"): "lucy_mainframe_test"
            StringTag("SpeakerId"): "lucy"
            StringTag("LocationId"): "astraea4_mainframe_anteroom"
            StringTag("Text"): "Lucy ordered the player to overload the Planetary Mainframe."
            IntTag("Phase"): 3
        }
    }

    CompoundTag("FactionReputation") {
        IntTag("SolarSentinels"): 25
        IntTag("VoidSyndicate"): 10
        IntTag("AetherScavengers"): 18
        StringTag("SolarSentinelsRank"): "Useful"
        StringTag("VoidSyndicateRank"): "Unknown"
        StringTag("AetherScavengersRank"): "Useful"
    }

    ListTag("FactionRelationships") {
        CompoundTag() {
            StringTag("FactionA"): "SolarSentinels"
            StringTag("FactionB"): "VoidSyndicate"
            StringTag("RelationshipState"): "Hostile"
            IntTag("UnityProgress"): 12
        },
        CompoundTag() {
            StringTag("FactionA"): "VoidSyndicate"
            StringTag("FactionB"): "AetherScavengers"
            StringTag("RelationshipState"): "SecretlyCooperative"
            IntTag("UnityProgress"): 34
        }
    }

    CompoundTag("LucyState") {
        IntTag("Trust"): 42
        IntTag("Concern"): 7
        IntTag("HumorAffinity"): 15
        StringTag("MoralityCommentaryMode"): "reactive_only"
        BooleanTag("MainframeTestResolved"): false
    }
}
```

### Reputation Event Records
Reputation should not change because of invisible karma. Store reputation events with evidence context so quests can decide who knows what.

```
CompoundTag("ReputationEvent") {
    StringTag("EventId"): "destroyed_sentinel_depot_001"
    StringTag("LocationId"): "cinder_moon_depot"
    BooleanTag("Witnessed"): false
    BooleanTag("ScanEvidenceSurvived"): true
    BooleanTag("PlayerApologized"): false
    StringTag("PrimaryFactionAffected"): "SolarSentinels"
    IntTag("ReputationDeltaIfDiscovered"): -20
}
```

*   **Immediate Rep Change**: Apply only when witnessed, reported, scanned, confessed, or part of a public quest outcome.
*   **Delayed Rep Change**: Hidden actions can become known later if evidence survives or an NPC discovers the scene.
*   **Lucy Commentary**: Lucy can react immediately even when factions do not know, because her state is local to the player companion system. These reactions are emotional and atmospheric only; they should not unlock exclusive quests or block quest access.
*   **Apology State**: Store whether the player apologized for public destruction or betrayal. Apologies can soften dialogue and help repair trust, but they do not erase NPC memory.
*   **Rank Labels**: Store both raw reputation and rank labels (`Unknown`, `Useful`, `Trusted`, `Champion`, `Unifier`) so UI and dialogue can quickly branch.
*   **Faction Pair State**: Store relationship states between factions because some hate each other, some secretly cooperate, and some unexpectedly align before the larger unity arc is complete.

---

## 🧬 6. New-U Respawn, Autosave & Restoration Persistence (`restore.dat`)

Death should restore the player from the last safe save without meaningful loss. Destroyed ships, killed NPCs, cities, and planets can be rebuilt from templates when the game rules allow it.

### Restore File Structure
```
CompoundTag("Restore") {
    StringTag("LastSafeSlot"): "autosaves/room_transition.slot"
    StringTag("LastRespawnAnchorId"): "newu_astraea4_orbital_hangar"
    LongTag("LastAutosaveTimeUtc"): 1784041812000

    ListTag("RestoreTemplates") {
        CompoundTag() {
            StringTag("TemplateId"): "astraea4_pre_mainframe_city"
            StringTag("Scope"): "planet"
            StringTag("PlanetId"): "astraea4"
            StringTag("CityState"): "finished_stable"
            BooleanTag("CanSaveWhileDestroyed"): false
            BooleanTag("NpcMemoryPersists"): true
            BooleanTag("PlayerCanRestoreAtWill"): true
        },
        CompoundTag() {
            StringTag("TemplateId"): "player_ship_latest"
            StringTag("Scope"): "ship"
            BooleanTag("PlayerCanRestoreAtWill"): true
        }
    }
}
```

### Autosave Slots
Autosaves are small restore anchors, not full punishment checkpoints. They should fire at predictable RPG-style boundaries:

| Slot | Trigger | Purpose |
| :--- | :--- | :--- |
| `landing.slot` | Landing on a planet | Safe return before surface exploration. |
| `launch.slot` | Initial launch from a planet/station | Safe return before flight hazards. |
| `room_transition.slot` | Entering/exiting a loading-screen room | Safe return near dungeon/facility progress. |
| `quest_checkpoint.slot` | Quest phase completion or major dialogue start | Protects narrative progress. |
| `puzzle_checkpoint.slot` | Puzzle room stage reached | Lets Lucy help without forcing full restarts. |

### Respawn Rules
*   Reload the latest safe slot when the player dies.
*   Rebuild the player at the nearest valid New-U station, orbital hangar, room entrance, or faction medical bay.
*   Restore the latest ship template if the ship was destroyed.
*   Preserve inventory, known keywords, quest flags, completed phases, and faction reputation.
*   Allow NPCs to remember death/restoration events and react with anger, fear, sarcasm, or distrust, but do not remove cargo, reset major progress, or lock the player out of content.

### World Restoration Rules
*   Cities, planets, and NPC populations can have named restoration templates.
*   A restored location returns to the selected template's block layout, NPC roster, city state, and local quest availability.
*   City clone saves only capture finished, stable city states. The game should not save a new city template while the city is being destroyed, burning, evacuating, collapsing, or under active disaster conditions.
*   NPCs may remember the destruction/restoration as a strange clone-era event. A restored shopkeeper can be mad about being blown up, a mayor can demand an apology, and a guard can become jumpy around the player.
*   The journal should record that restoration happened, but factions only react if the destruction/restoration was witnessed, reported, or publicly visible.
*   Lucy may comment on restored worlds as a philosophical or funny continuity beat.
