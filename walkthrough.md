# Java Voxel Space Game Walkthrough

The layout design, system interface blueprints, and software specifications for the Java-based Voxel Space Game have been successfully drafted and verified.

---

## 📂 Design Files Created (Artifacts)
*   [voxel_game_layout.md](file:///Users/mirandazavala/.gemini/antigravity/brain/3c12e510-edc1-44c4-9207-847fc1e1df0d/voxel_game_layout.md) — User interface rules, color-coded unified 3D coordinates ($X, Y, Z$ vectors), flat cubical gravity mechanics, and Borderlands-style cloning respawn.
*   [voxel_tech_architecture.md](file:///Users/mirandazavala/.gemini/antigravity/brain/3c12e510-edc1-44c4-9207-847fc1e1df0d/voxel_tech_architecture.md) — Software requirements (LWJGL 3, JOML, OpenJDK 21), vertex shader formulas for the "Origami Warp" folding transition, camera portal view matrix offsets, and greedy meshing algorithms.
*   [voxel_save_format.md](file:///Users/mirandazavala/.gemini/antigravity/brain/3c12e510-edc1-44c4-9207-847fc1e1df0d/voxel_save_format.md) — Voxel serialization schemas using compressed Run-Length Encoding (RLE) streams and Named Binary Tag (NBT) compound structures.
*   [voxel_quests_dialogue.md](file:///Users/mirandazavala/.gemini/antigravity/brain/3c12e510-edc1-44c4-9207-847fc1e1df0d/voxel_quests_dialogue.md) — Morrowind-style interactive keyword dialogue frames, RuneScape animated NPC avatars, Oblivion-style guild hierarchies, Void end-game loops, the **Sabotage & Rehabilitation** final boss, the **Lucy AI guide character arc (with in-depth script dialogue)**, and fully unlocked spaceship component builders.

---

## 🎨 Layout Highlights

1.  **Voxel Edge Traversals**: Dynamic view matrix offsets act like a portal lens to bend adjacent faces flat beneath the player's feet, allowing seamless continuous walking across all 6 faces of the cubical planet.
2.  **Color-Coded Nav**: The top-left HUD coordinates are mapped to intuitive primary color visual cues (<span style="color:#ff3333; font-weight:bold;">X/Red</span>, <span style="color:#33ff33; font-weight:bold;">Y/Green</span>, <span style="color:#3333ff; font-weight:bold;">Z/Blue</span>).
3.  **Low-Penalty Loop**: Ship destructions occur but player cloning (Borderlands-style) preserves construction templates and respawns resources at the nearest space station.
4.  **Keyword Dialogue Grid**: Conversing with NPCs highlights keywords to open new lore tabs and automatically log coordinates to the player's coordinate compass.
5.  **Sabotage & Rehabilitation Boss Loop**: Disable the boss's power stations and redirect their supply cargo to drain their shields. Once defenseless, board their ship and use historical lore logs to rehabilitate them instead of executing them.
6.  **Full Creative Freedom**: All spaceship parts, hulls, engines, and reactors are completely unlocked from the start of the game, encouraging immediate customization.
7.  **The Lucy Mainframe Test**: Enter the double blast doors of the planetary mainframe, refuse Lucy's direct command to overload the core by telling her she is crazy, and walk out. Exiting the doors reveals her standing in the prior room, proud that you rejected "ruthless nameless violence."
