<h1 align="center">Spain · Starforge</h1>
<p align="center"><b>Build a rocket on Earth. Fly it to space. All inside Minecraft.</b></p>
<p align="center">
<img alt="Java" src="https://img.shields.io/badge/Minecraft-Java-62b47a">
<img alt="Fabric" src="https://img.shields.io/badge/Fabric-mod-dbd0b4">
<img alt="License" src="https://img.shields.io/badge/license-MIT-blue">
</p>

Spain is a playable Earth-to-space adventure built on **Minecraft Java** with a small **Fabric mod** and an adventure **data pack**. Minecraft supplies terrain, mobs, controls, inventory and saves. Spain adds a rocket creator, free flight, quick travel, cities and conversations.

## Features

- **Rocket creator:** add Spore hulls and engines, symmetric wings and glass cockpits; stretch the design, rotate the preview and undo changes.
- **Free flight:** take off from Earth and fly your own design.
- **Quick travel:** hop between locations once you have discovered them.
- **Cities and conversations:** start in Harborlight on Earth and meet Mira and Dr Pip for the intro story.
- **Nothing to unlock first:** flying and building never require an NPC. Run `/spain create` to start right away.

## Quick start

```sh
./play-spain.sh                      # offline test profile (SpainExplorer)
./play-spain.sh --profile YOUR_NAME  # use a Prism account
```

On desktop you can also launch **Play Spain.desktop**. Restart your Spain instance after updating. Building, checking and installing never launch the game automatically.

## Assets and requirements

Spain **uses Minecraft's own assets for gameplay**, and ships none of them. You need your own copy of **Minecraft Java Edition** (run through [Prism Launcher](https://prismlauncher.org)); Spain reads from that installation at runtime.

| Source | Used for | Included in this repo? |
|---|---|---|
| **Minecraft Java** (Mojang / Microsoft) | Terrain, player skins, mobs, material textures, inventory and the renderer | No. Comes from your own install |
| **Spore** (EA / Maxis) | UFO hull, thruster and creature shapes, recolored into the Minecraft block palette | No. Extracted locally from your own Steam copy; never committed |
| **World at War models** (Activision / Treyarch) | Optional crate and pine geometry converted to blocks | No. Local files only |
| **SkyCraft** (MIT) | Reference for Fabric integration only; no code copied | No |

Everything extracted lands in git-ignored local folders (`.tools/`, `local-assets/`), so the repository contains only Spain's own code and content. See [`content/assets.json`](content/assets.json) for the full manifest and credits.

## Repository map

| Path | What lives there |
|---|---|
| `mod/src/main` | Fabric mod source |
| `content/` | Adventure data pack content |
| `scripts/` and `tools/` | Build, check and install helpers |
| `verification/` | Verification material |
| `GAME_DESIGN.md` | Game design and planetary mechanics |
| `voxel_*.md` | Voxel tech architecture, save format and quest dialogue notes |

## Design notes

Start with [GAME_DESIGN.md](GAME_DESIGN.md), then [voxel_tech_architecture.md](voxel_tech_architecture.md) and [implementation_plan.md](implementation_plan.md).

## License

Released under the [MIT License](LICENSE).

<sub>Not an official Minecraft product. Not approved by or associated with Mojang or Microsoft. Minecraft is a trademark of Mojang Synergies AB; Spore is a trademark of Electronic Arts Inc.; all other assets belong to their respective owners.</sub>
