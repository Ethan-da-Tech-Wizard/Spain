# Files 1 of 1 — Spain — Starforge

[All pages](../FILE_GUIDE.md) · [Project guide](../PROJECT_GUIDE.md)

| File | Role and useful details |
| --- | --- |
| [.gitignore](../../.gitignore) | Defines local data, credentials, dependencies, and generated outputs that Git should leave untracked. |
| [GAME_DESIGN.md](../../GAME_DESIGN.md) | Documentation: Starforge Planets. Covers Core Pitch; Game Feel; Technical Direction. |
| [LICENSE](../../LICENSE) | Preserved license, copyright, or attribution terms; read the full text before reusing the covered component. |
| [PROJECT_NOTES.md](../../PROJECT_NOTES.md) | Preserved detailed setup, usage, architecture, and development notes from the earlier README. |
| [Play Spain.desktop](../../Play%20Spain.desktop) | Linux desktop launcher for Play Spain; records the command, icon, and desktop integration settings. |
| [README.md](../../README.md) | Project overview, current status, entry points, setup navigation, and documentation links. |
| [agent_prompts.md](../../agent_prompts.md) | Documentation: Voxel Space Game: Division of Labor & Agent Prompts. Covers 🏗 1. Division of Labor; 🤖 2. Agent Prompt 1: Voxel Engine & Shader Programmer; System Prompt Code. |
| [brainstorming_planetary_mechanics.md](../../brainstorming_planetary_mechanics.md) | Documentation: Starforge Planets: Brainstorming & Concepts. Covers 🚀 Core Gameplay Loop; 🪐 Pillar 1: Planetary Mechanics; 1. Dynamic Gravity Fields. |
| [content/assets.json](../../content/assets.json) | Structured assets data; top-level fields: `style`, `sources`. |
| [content/evolution.json](../../content/evolution.json) | Structured evolution data; top-level fields: `stages`, `initial_life_stage`, `simulation_step_game_days`, `world_progress_policy`, `gates`, `temperament`, `friendship_inputs`, `invasion_resolution`. |
| [content/npcs.json](../../content/npcs.json) | Structured npcs list with 13 records. |
| [content/planets.json](../../content/planets.json) | Structured planets list with 3 records. |
| [docs/DEPENDENCIES.csv](../../docs/DEPENDENCIES.csv) | Machine-readable inventory of declared and locked dependencies, versions, reported licenses, and evidence URLs. |
| [docs/FILE_GUIDE.md](../../docs/FILE_GUIDE.md) | Index of the complete tracked-file guide, with one entry for every file and links to the paginated descriptions. |
| [docs/LICENSE_REVIEW.md](../../docs/LICENSE_REVIEW.md) | Original-code license, preserved component notices, dependency-license evidence, and unresolved distribution questions. |
| [docs/PROJECT_GUIDE.md](../../docs/PROJECT_GUIDE.md) | Maintainer orientation: purpose, important entry points, source layout, commands, and project-specific boundaries. |
| [docs/file-guide/files-001.md](../../docs/file-guide/files-001.md) | One page of the tracked-file catalog; links each listed path to its role and source-derived details. |
| [implementation_plan.md](../../implementation_plan.md) | Documentation: Spain: Minecraft Implementation Plan. Covers Implemented test; Following milestones. |
| [mod/src/main/java/dev/spain/FlightSystem.java](../../mod/src/main/java/dev/spain/FlightSystem.java) | Source module for FlightSystem; defines `FlightSystem`, `Ship`, `Scan`, `spain`. |
| [mod/src/main/java/dev/spain/FlightView.java](../../mod/src/main/java/dev/spain/FlightView.java) | Source module for FlightView. |
| [mod/src/main/java/dev/spain/SpainClient.java](../../mod/src/main/java/dev/spain/SpainClient.java) | Source module for SpainClient; defines `SpainClient`. |
| [mod/src/main/java/dev/spain/SpainMod.java](../../mod/src/main/java/dev/spain/SpainMod.java) | Source module for SpainMod; defines `SpainMod`. |
| [mod/src/main/java/dev/spain/SporeVisuals.java](../../mod/src/main/java/dev/spain/SporeVisuals.java) | Source module for SporeVisuals; defines `SporeVisuals`. |
| [mod/src/main/java/dev/spain/mixin/ShipCameraMixin.java](../../mod/src/main/java/dev/spain/mixin/ShipCameraMixin.java) | Source module for ShipCameraMixin; defines `ShipCameraMixin`. |
| [mod/src/main/resources/fabric.mod.json](../../mod/src/main/resources/fabric.mod.json) | Structured fabric.mod data; top-level fields: `schemaVersion`, `id`, `version`, `name`, `description`, `license`, `authors`, `environment`, `entrypoints`. |
| [mod/src/main/resources/spain.client.mixins.json](../../mod/src/main/resources/spain.client.mixins.json) | Structured spain.client.mixins data; top-level fields: `required`, `package`, `compatibilityLevel`, `client`, `injectors`. |
| [play-spain.sh](../../play-spain.sh) | Command-line automation for play spain; review prerequisites and side effects before executing. |
| [scripts/build.sh](../../scripts/build.sh) | Command-line automation for build; review prerequisites and side effects before executing. |
| [scripts/setup.sh](../../scripts/setup.sh) | Command-line automation for setup; review prerequisites and side effects before executing. |
| [scripts/update.sh](../../scripts/update.sh) | Command-line automation for update; review prerequisites and side effects before executing. |
| [task.md](../../task.md) | Documentation: Java Voxel Space Game: Design & Layout Tracker. Covers Minecraft implementation — October 9, 2026. |
| [tools/SporeResources.java](../../tools/SporeResources.java) | Source module for SporeResources; defines `SporeResources`. |
| [tools/asset_status.py](../../tools/asset_status.py) | Read Steam download manifests and check the local Minecraft/Spore build inputs. Defines `status`. |
| [tools/build_mod.py](../../tools/build_mod.py) | Compile the small, unmapped Minecraft 26.3 Fabric module against local game libraries. Defines `dependencies`, `compile_mod`. |
| [tools/build_pack.py](../../tools/build_pack.py) | Build a vanilla Minecraft 26.3 adventure from reviewable content and functions. Defines `write_json`, `tell`, `button`, `dialog_button`, `dialog`, `function` and 4 more top-level symbols. |
| [tools/evolution.py](../../tools/evolution.py) | Deterministic population progression prototype; not yet attached to Minecraft ticks. Defines `Population`, `advance`. |
| [tools/extend_pack.py](../../tools/extend_pack.py) | Earth-to-station test, layered over the colony content generator. Defines `extend`. |
| [tools/import_assets.py](../../tools/import_assets.py) | Convert selected local Melty GLB art into ordinary, editable Minecraft blocks. Defines `load_glb`, `accessor`, `node_transform`, `primitives`, `voxelize`, `main`. |
| [tools/import_spore.py](../../tools/import_spore.py) | Import selected Spore meshes via SporeModder FX, then remesh into Minecraft blocks. Defines `voxelize_mesh`, `main`. |
| [tools/install_prism.py](../../tools/install_prism.py) | Install the verified starter world in a separate, managed Prism instance. Defines `copy_atomic`, `prepare_level`, `install`. |
| [tools/nbt.py](../../tools/nbt.py) | Small big-endian NBT codec for Minecraft structures and verification reports. Defines `string`, `payload`, `structure`, `read`. |
| [tools/repair_libraries.py](../../tools/repair_libraries.py) | Fetch missing Linux client libraries using Prism's own version metadata and hashes. Defines `fetch`, `repair`. |
| [tools/setup_spore.py](../../tools/setup_spore.py) | Install a pinned, verified SporeModder FX CLI locally; extracted art stays local. Defines `setup`. |
| [verification/MinecraftChecks.java](../../verification/MinecraftChecks.java) | Source module for MinecraftChecks; defines `MinecraftChecks`, `spain`. |
| [verification/run_checks.py](../../verification/run_checks.py) | Compile a small probe against the user's Minecraft and run Mojang's GameTest server. Defines `main`. |
| [verification/test_tools.py](../../verification/test_tools.py) | Automated checks for tools. Defines `ToolChecks`. |
| [voxel_game_layout.md](../../voxel_game_layout.md) | Documentation: Voxel Space Game: Layout & Design Specs (Java / Minecraft Style). Covers 🖥 1. HUD (Heads-Up Display) Layout; HUD Components; 🗂 2. Game Menu Layouts. |
| [voxel_quests_dialogue.md](../../voxel_quests_dialogue.md) | Documentation: Voxel Space Game: Quests, Dialogue & End-Game Systems. Covers 💬 1. Morrowind & RuneScape Hybrid Dialogue Interface; Key Dialogue Features; Keyword-to-Quest Hook Rules. |
| [voxel_save_format.md](../../voxel_save_format.md) | Documentation: Voxel Space Game: Save File Format & Serialization. Covers 💾 1. The Serialization Goal; 📁 2. File System Layout; ⚙ 3. Binary Chunk Format (`.chunk` Layout). |
| [voxel_tech_architecture.md](../../voxel_tech_architecture.md) | Documentation: Voxel Space Game: Technical Architecture (Java / LWJGL). Covers 🛠 1. Recommended Java Tech Stack; 🪐 2. The "Origami Warp" Landing Transition (Vertex Shader Math); The Math behind the Deformation Shader (Low-Tech Optimization). |
| [walkthrough.md](../../walkthrough.md) | Documentation: Spain: Playable Test Walkthrough. |
