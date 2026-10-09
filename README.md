# Spain · Starforge

A playable Earth-to-space test built inside **Minecraft Java 26.3**, with a small Fabric mod and an adventure data pack. Minecraft supplies terrain, mobs, controls, inventory and saves. Spain adds a rocket creator, free flight, quick travel, cities and conversations.

## Play

Restart your Spain instance after an update, then use **Play Spain.desktop** or `./play-spain.sh`. The local test defaults to the offline name SpainExplorer; pass `--profile YOUR_PROFILE` to use a Prism account. Building, checking and installing never launch the game automatically.

You start in **Harborlight on Earth**, surrounded by normal, chunk-loaded Minecraft terrain. Meet Mira and Dr Pip for the introductory story, or open **`/spain create`** immediately. Flying and building do not require an NPC.

The creator lets you add Spore hulls and engines, symmetric wings and glass cockpits; stretch the design; rotate its preview; and undo changes. Components use Minecraft block materials throughout. Close the creator to inspect the preview, then board. There is no gameplay part-count budget; very large designs remain limited by Minecraft and your hardware. This is a first creator with part buttons and a world preview; Spore's full drag-and-sculpt editor is a later milestone.

| Control | Action |
| --- | --- |
| `/spain create` | Open the rocket creator |
| `/spain board` | Enter the cockpit and take off |
| WASD / mouse | Move and turn the rocket |
| Space / Shift | Ascend / descend |
| F5 | Switch cockpit and chase views |
| `/spain land` | Exit; the ship settles onto a surface |
| `/spain recall` | Teleport beside your parked rocket |
| `/trigger spain.talk set 1` | Open quick travel anywhere, including in flight |
| `/trigger spain.ship set 4` | Rocket controls and workshop capture |

Boarding centers the craft on the player's cockpit position and activates a chase camera sized to the rocket. Your previous camera mode returns on exit. Native Minecraft camera collision still applies. Ship orientation follows your view; quick travel preserves an active cockpit.

Fly above **Y 280** on a planet to enter orbit. The station is at **X 0, Y 65, Z 0**. Descend below **Y 40** in orbit to return to Earth's upper atmosphere. Quick travel also reaches Earth, the station and three colonies without a waiting timer.

The six station workers welcome the pilot to **“the world of endless possibility.”** This completes the flight test; the world stays open for exploration. Right-click all thirteen named residents for dialogue, guidance and humor. Iona and Sera also offer a persistent quest connecting two colonies.

Ships have no health or damage. A parked ship falls when its support disappears, lands on solid surfaces including leaves and mountain tips, and rises in water until it meets the surface or a ceiling. Your spacesuit supports indefinite space exploration; underwater breath still runs out. Survival, gathering and ordinary hostile Minecraft mobs remain available.

## Build your own sculpture or appearance

Build a rocket from ordinary blocks in the Earth workshop, then capture it. The default selection is X 8–20, Y 97–103, Z -8–7 and includes locally imported Spore props. For a larger or different design:

```text
/spain corner1 X Y Z
/spain corner2 X Y Z
/spain capture
/spain board
```

Capture runs in batches and preserves the workshop as an editable blueprint. Ships render as moving block displays; inventories, redstone and block-entity contents are not transported.

Some residents and creatures use the imported Spore silhouette with the same Minecraft materials. Others keep their ordinary Minecraft appearance. `/spain avatar default` restores your normal Minecraft skin; `/spain avatar spore` selects the local creature. Select a block sculpture with the corner commands, then `/spain avatar capture` to create your own creature appearance. `/spain avatar custom` reselects it after a restart. F5 previews appearances. Custom Minecraft skins use Minecraft's existing account skin system. Importing arbitrary Spore PNG creations and a full creature editor are future work.

## Build, check and install

Install Minecraft 26.3 through Prism first. The project reads your installed game and does not bundle Minecraft binaries. `./scripts/update.sh` handles available local asset imports, library repair, checks and installation without opening a game window. Individual steps:

```sh
./scripts/setup.sh
./scripts/build.sh
python3 verification/run_checks.py
python3 tools/install_prism.py
```

Setup installs a checksum-verified JDK 25 locally. Building pins Fabric Loader 0.19.5 and Fabric API 0.161.0+26.3. `SPAIN_MC_LIBRARIES` and `SPAIN_JAVA_HOME` override the default local paths. Outputs are `dist/Spain.zip` and `dist/spain-flight-0.1.0.jar`.

The installer uses a separate, managed **Spain** Prism instance. It rejects unmanaged instances, preserves existing saves, and atomically replaces mod files. An earlier generated colony preview was preserved as `Spain-colony-preview`. A first install removes test players and test ship/avatar files from the verified starter world. Default memory and render settings are kept modest; the verification server uses a 768 MB heap, two CPU workers and no graphics.

`python3 tools/repair_libraries.py` repairs missing Linux launcher libraries using Prism metadata and checksums. `python3 tools/asset_status.py` reports Steam download completion and local build resources. Neither opens the game.

## Local assets

All three Steam installs were complete on October 9, 2026: Spore, Creepy & Cute and Galactic Adventures. Selected UFO, rocket-part and creature meshes currently come from the base game's `Spore_Graphics.package`.

```sh
python3 tools/setup_spore.py
python3 tools/import_spore.py
python3 -m venv .venv
.venv/bin/pip install Pillow==12.0.0
.venv/bin/python tools/import_assets.py
./scripts/build.sh
```

[SporeModder FX](https://github.com/Spore-Community/SporeModder-FX) supplies the separately installed archive/model reader. The adapter calls that library; no extractor source was copied. Spore geometry is converted to Minecraft blocks and recolored into the same palette. A crate and pine use prepared local Melty GLBs and their embedded colors. Original art remains credited to EA/Maxis and Activision/Treyarch.

Local extracted art and provenance stay in ignored `local-assets/` and enter only local builds. GitHub contains source, conversion tools and the asset catalog. SkyCraft informed the Fabric integration approach; its Skyrim bridge and source were not copied.

## Verification and limits

The real Minecraft GameTest server checks dimensions, city construction, exactly-once NPC spawning, right-click packets, quests, free flight, quick travel during flight, creator parts/undo, cockpit position, boarding without NPCs, saved ships/avatars, finite underwater breath, support destruction, buoyancy and ceilings. It also inspects Minecraft's persisted scoreboard. Logs and results live in `verification/output/`.

```sh
.venv/bin/python -m unittest discover -s verification -p 'test_*.py'
```

The initial graphical client was opened and its native NPC dialogue inspected. The latest creator/chase-camera revision was compiled and checked without opening another graphical client, following the request to keep RAM/VRAM usage low. Its camera mixin targets Minecraft 26.3's native zoom method and preserves terrain collision; visual behavior should be checked on the next manual launch.

Earth uses normal Minecraft terrain, rather than a geographic Earth map or spherical surface. The other colonies currently use flat themed starter terrain. Space entry is a dimension transition at an altitude boundary. The wider friendship-driven campaign, multiplayer diplomacy, procedural city growth and creature-to-space civilizations remain planned. `tools/evolution.py` and `content/evolution.json` provide a tested progression model with maturity, habitat, cooperation, knowledge and stable stage gates; they are not yet connected to world ticks.

## GitHub comparison

GitHub `Ethan-da-Tech-Wizard/Spain` and `wyldgms/spain` initially matched at `15c670fd9b66733d746823a859e9989c71aba013`: ten design documents and no runnable game code. This implementation follows the subsequent Minecraft, NPC, Spore and free-travel requests. Older custom-engine and save-format documents remain historical design references.
