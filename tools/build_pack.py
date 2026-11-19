#!/usr/bin/env python3
# ==============================================================================
# Program: build_pack.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Procedural Minecraft data pack synthesizer generating planetary systems and quests.
#          Compiles dimensional JSON definitions, biomes, dynamic dialog trees, and mcfunction
#          scripts. Enforces mathematical volume bounds (<= 32,768 blocks per /fill invocation)
#          and strict coordinate invariants for procedural planetary settlement generation.
# ==============================================================================

"""Build a vanilla Minecraft 26.3 adventure from reviewable content and functions."""

# Fit in the repo: this is the data-pack generator, the first stage of the Spain build (scripts/build.sh
# runs `tools/build_pack.py` and then `tools/build_mod.py`). Nothing in dist/Spain is written by hand; this
# script writes every JSON and .mcfunction file from two small content tables (content/planets.json and
# content/npcs.json), so changing a planet colour or a villager line means editing data, then rebuilding.
# tools/extend_pack.py layers the Earth start area, rocket workshop and flight quests on top of what is
# generated here (build() calls its extend(root) near the end), and verification/run_checks.py builds the
# pack, then runs it in a real Minecraft game-test server.
#
# What a build produces (dist/Spain, plus dist/Spain.zip):
#   * one dimension type + flat-world dimension per planet, and an empty "orbit" dimension for the space station
#   * a world preset (spain:starforge) that adds those dimensions to the normal "Create World" preset
#   * `load` / `tick` functions (Minecraft runs these automatically), travel, dialogue and quest functions
#   * villager NPCs with click-to-talk advancements, and dialog screens (Minecraft's native dialog UI)
# Inputs : the local Minecraft 26.3 client jar (only read, to copy its overworld dimension type and world
#          preset so the pack stays compatible with the installed version); content/*.json; optional
#          local-assets/ (local-only structures converted from the owner's own files).
# Run    : python3 tools/build_pack.py [--minecraft-jar PATH]   (prints the path of the zip)
# Limits : targets exactly Minecraft 26.3 (pack format 121) and refuses any other version; command strings
#          are assembled as text and are only validated by running them in the game (see verification/).
from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path

# Repository root (tools/ lives one level below it); output goes to ROOT/dist.
ROOT = Path(__file__).resolve().parents[1]

# Where Prism Launcher keeps the Minecraft 26.3 client jar on Linux. Override with --minecraft-jar elsewhere.
DEFAULT_JAR = Path.home() / '.local/share/PrismLauncher/libraries/com/mojang/minecraft/26.3/minecraft-26.3-client.jar'


def write_json(path: Path, value: object) -> None:
    """Write `value` as pretty JSON (UTF-8, trailing newline) to `path`, creating parent folders.

    ensure_ascii=False keeps characters such as the middle dot in "Spain · Starforge" readable in the files.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def tell(text: str, color: str = 'aqua') -> str:
    """Return a `tellraw @s` command that shows `text` in chat to the executing player in the given colour."""
    return 'tellraw @s ' + json.dumps({'text': text, 'color': color}, ensure_ascii=False)


def button(text: str, objective: str, value: int, color: str = 'aqua') -> dict:
    """Return a clickable chat component that runs `/trigger <objective> set <value>` for the player.

    Trigger objectives are the one thing players may change without operator rights, so every menu
    action in the pack is a trigger value that the `tick` function reads and then resets.
    """
    return {'text': text, 'color': color, 'click_event': {'action': 'run_command', 'command': f'/trigger {objective} set {value}'}}


def dialog_button(text: str, objective: str, value: int) -> dict:
    """Return one button of a native Minecraft dialog screen that fires the same trigger as `button()`."""
    return {'label': text, 'width': 210, 'action': {'type': 'minecraft:run_command', 'command': f'/trigger {objective} set {value}'}}


def dialog(root: Path, name: str, title: str, text: str, actions: list[dict]) -> None:
    """Write data/spain/dialog/<name>.json: a one-column dialog with a text body, `actions` and a Goodbye button.

    pause=False keeps the game running while the screen is open (the world stays live on servers), and
    after_action 'close' closes the screen once a button was used.
    """
    write_json(root / f'data/spain/dialog/{name}.json', {'type': 'minecraft:multi_action', 'title': title, 'body': [{'type': 'minecraft:plain_message', 'contents': text, 'width': 350}], 'actions': actions, 'columns': 1, 'exit_action': {'label': 'Goodbye', 'width': 210}, 'pause': False, 'after_action': 'close'})


def function(root: Path, name: str, commands: list[str]) -> None:
    """Write data/spain/function/<name>.mcfunction with one command per line (`name` may contain '/').

    Overwrites any previous file of that name; extend_pack.py relies on that and on appending afterwards.
    """
    path = root / 'data/spain/function' / (name + '.mcfunction')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(commands) + '\n')


def fill(x1, y1, z1, x2, y2, z2, block):
    """Return a `/fill` command for the box between the two corners, filled with minecraft:<block>.

    The assert enforces Minecraft's limit of 32,768 blocks per fill. Corner order is irrelevant (abs() is
    used), and both corners are included, hence the +1 per axis. Failing here at build time is much better than
    a command silently failing in the game.
    """
    assert (abs(x2-x1)+1)*(abs(y2-y1)+1)*(abs(z2-z1)+1) <= 32768
    return f'fill {x1} {y1} {z1} {x2} {y2} {z2} minecraft:{block}'


def house(x: int, z: int, wall: str, roof: str) -> list[str]:
    """Return the commands for one 9x9 house whose north-west corner is (x, z), standing on y=64.

    Args: wall and roof are block ids without the "minecraft:" prefix (they come from the planet table).
    """
    return [
        # Floor slab, 9x9.
        fill(x, 64, z, x+8, 64, z+8, 'stone_bricks'),
        # Solid wall block, then the next line hollows the inside with air, leaving walls one block thick.
        fill(x, 65, z, x+8, 69, z+8, wall),
        fill(x+1, 65, z+1, x+7, 68, z+7, 'air'),
        # Flat roof one block wider than the walls on every side, so it overhangs like an eave.
        fill(x-1, 70, z-1, x+9, 70, z+9, roof),
        # Doorway: 3 wide, 3 tall, in the south wall (z+8), cut through the wall after it was built.
        fill(x+3, 65, z+8, x+5, 67, z+8, 'air'),
        # One window strip in each side wall (west here, east on the next line).
        fill(x, 66, z+2, x, 67, z+6, 'glass'),
        fill(x+8, 66, z+2, x+8, 67, z+6, 'glass'),
        # Furniture and a lantern so houses are usable and lit: crafting table, storage barrel, sea lantern.
        f'setblock {x+2} 65 {z+2} minecraft:crafting_table',
        f'setblock {x+6} 65 {z+2} minecraft:barrel',
        f'setblock {x+4} 68 {z+4} minecraft:sea_lantern',
    ]


def city(planet: dict) -> list[str]:
    """Return the commands that build one planet's starter city around the world origin (x, z in -26..26).

    Args:
        planet: one entry of content/planets.json. Keys used: surface and accent (block ids for the ground
            and the plaza), wall and roof (house materials), theme ('forest' adds oak trees, anything
            else adds amethyst pillars).

    The first line is an mcfunction comment (starts with '#'): the function is only run once, guarded by the
    #built score in `load`, so reloading the pack never rebuilds or erases player changes.
    extend_pack.py reuses this function for the Earth city and drops the last 5 commands (the rocket
    monument), so adding or removing commands at the END of this list changes Earth too.
    """
    commands = [
        '# Generated once. Reloading never rebuilds or erases a city.',
        # Ground plate 53x53, then two crossing stone-brick roads 7 wide, a quartz plaza 9x9 in the middle and a smaller accent square.
        fill(-26, 64, -26, 26, 64, 26, planet['surface']),
        fill(-3, 64, -24, 3, 64, 24, 'stone_bricks'),
        fill(-24, 64, -3, 24, 64, 3, 'stone_bricks'),
        fill(-4, 64, -4, 4, 64, 4, 'smooth_quartz'),
        fill(-2, 64, -2, 2, 64, 2, planet['accent']),
    ]

    # Four houses, one in each quadrant, clear of the roads (houses are 9 wide, roads 7 wide).
    for x, z in [(-20, -20), (12, -20), (-20, 12), (12, 12)]:
        commands.extend(house(x, z, planet['wall'], planet['roof']))

    # Four lamp posts around the plaza: an iron-bar column topped by a sea lantern.
    for x, z in [(-6, -6), (6, -6), (-6, 6), (6, 6)]:
        commands.extend([fill(x, 65, z, x, 68, z, 'iron_bars'), f'setblock {x} 69 {z} minecraft:sea_lantern'])

    # Landmarks at the four road ends: a tree for forest worlds, otherwise an amethyst pillar with a light.
    # `persistent=true` stops oak leaves decaying because the trunk is not a natural tree.
    for x, z in [(-24, 0), (24, 0), (0, -24), (0, 24)]:
        if planet['theme'] == 'forest':
            commands += [fill(x, 65, z, x, 69, z, 'oak_log'), fill(x-2, 69, z-2, x+2, 71, z+2, 'oak_leaves[persistent=true]')]
        else:
            commands += [fill(x, 65, z, x, 69, z, 'amethyst_block'), f'setblock {x} 70 {z} minecraft:sea_lantern']

    # Monument next to the plaza (the five commands extend_pack drops for Earth): an iron tower,
    # white nose and light-blue window with magma at the base to suggest engines.
    # A rocket monument makes the spaceport visible without claiming piloted flight yet.
    commands += [fill(8, 65, 0, 10, 71, 2, 'iron_block'), fill(9, 72, 1, 9, 74, 1, 'white_concrete'), 'setblock 9 69 0 minecraft:light_blue_stained_glass', 'setblock 8 65 0 minecraft:magma_block', 'setblock 10 65 0 minecraft:magma_block']
    return commands


def build(jar: Path = DEFAULT_JAR, output: Path | None = None) -> Path:
    """Generate the whole data pack and return the path of the zip file that contains it.

    Args:
        jar: Minecraft 26.3 client jar to read the vanilla overworld dimension type and world preset from.
        output: folder for the pack (default ROOT/dist/Spain). It is deleted and recreated, so never
            point it at a folder that holds anything you want to keep.

    Returns:
        Path of `<output>.zip` (for example dist/Spain.zip).

    Raises:
        ValueError: if the jar is not Minecraft 26.3 (the pack format and command syntax are version specific).
        OSError / zipfile.BadZipFile: if the jar or a content file is missing or unreadable.

    Side effects: deletes and rewrites the output folder; copies local-assets files into it when present.
    """
    root = output or ROOT / 'dist/Spain'

    # Always start from an empty folder so files from an earlier build (for example a removed planet) cannot linger.
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)

    # Content tables: planets (id, name, city, biome, colours, blocks, travel trigger number) and NPCs (id, role, dimension, position, dialogue, action).
    planets = json.loads((ROOT / 'content/planets.json').read_text())
    npcs = json.loads((ROOT / 'content/npcs.json').read_text())

    # Take the vanilla overworld dimension type and "normal" world preset from the player's own jar, instead of
    # bundling Mojang files, so no Minecraft data is redistributed and the pack follows that version's format.
    with zipfile.ZipFile(jar) as archive:
        version = json.loads(archive.read('version.json'))
        if version['id'] != '26.3':
            raise ValueError('This pack targets Minecraft 26.3')
        base_type = json.loads(archive.read('data/minecraft/dimension_type/overworld.json'))
        world_preset = json.loads(archive.read('data/minecraft/worldgen/world_preset/normal.json'))

    # pack.mcmeta marks the folder as a data pack. min_format/max_format [121, 0] pin it to the Minecraft 26.3 data format.
    write_json(root / 'pack.mcmeta', {'pack': {'description': 'Spain · Starforge planets, cities and conversations', 'min_format': [121, 0], 'max_format': [121, 0]}})

    # Credits file; extend_pack and the Spore import add lines to it later.
    (root / 'CREDITS.txt').write_text('Spain content by Ethan-da-Tech-Wizard. Minecraft game assets are provided by your own Minecraft installation. No Minecraft binaries are bundled.\n')

    # One dimension per planet plus the space station "orbit" (a pseudo-planet with only sky and fog colours).
    for planet in planets + [{'id': 'orbit', 'biome': 'the_void', 'sky': '#050817', 'fog': '#090e22'}]:
        # Deep copy through JSON so editing this dimension type never changes the shared vanilla one.
        dim_type = json.loads(json.dumps(base_type))

        # World height 0..384 (vanilla is -64..320) and monster_spawn_light_level 0 means hostile mobs spawn only in total darkness.
        dim_type.update({'min_y': 0, 'height': 384, 'logical_height': 384, 'monster_spawn_light_level': 0})
        dim_type['attributes']['minecraft:visual/sky_color'] = planet['sky']
        dim_type['attributes']['minecraft:visual/fog_color'] = planet['fog']

        # Orbit: constant daylight-free sky (has_fixed_time, end-style skybox, sky_light_factor 0) with fixed ambient light 0.5 so the station is lit without a sun.
        if planet['id'] == 'orbit':
            dim_type.update({'ambient_light': .5, 'has_fixed_time': True, 'skybox': 'end'})
            dim_type['attributes']['minecraft:visual/sky_light_factor'] = 0.0
        write_json(root / f"data/spain/dimension_type/{planet['id']}.json", dim_type)

        # Flat-world layers bottom to top: 1 bedrock, 59 stone, 3 subsurface, 1 surface = 64 blocks, so the
        # walkable ground is at y=64. Orbit has no layers (void) because the station floats in space.
        layers = [] if planet['id'] == 'orbit' else [
            {'block': 'minecraft:bedrock', 'height': 1}, {'block': 'minecraft:stone', 'height': 59},
            {'block': 'minecraft:' + planet['subsurface'], 'height': 3}, {'block': 'minecraft:' + planet['surface'], 'height': 1}]

        # Flat generator without features, lakes or structures: a clean canvas where only the pack's own builder adds anything.
        write_json(root / f"data/spain/dimension/{planet['id']}.json", {'type': 'spain:' + planet['id'], 'generator': {'type': 'minecraft:flat', 'settings': {'biome': 'minecraft:' + planet['biome'], 'features': False, 'lakes': False, 'layers': layers, 'structure_overrides': []}}})

        # Add the dimension to the world preset too, so a new world contains all planets from the start.
        world_preset['dimensions']['spain:' + planet['id']] = json.loads((root / f"data/spain/dimension/{planet['id']}.json").read_text())
    write_json(root / 'data/spain/worldgen/world_preset/starforge.json', world_preset)

    # Register our preset in the vanilla "normal" tag. replace False keeps vanilla presets and appends ours.
    write_json(root / 'data/minecraft/tags/worldgen/world_preset/normal.json', {'replace': False, 'values': ['spain:starforge']})

    # Function tags: spain:load runs on every world load and reload, spain:tick runs 20 times a second.
    for tag in ['load', 'tick']:
        write_json(root / f'data/minecraft/tags/function/{tag}.json', {'values': ['spain:' + tag]})

    # `load`: create scoreboard objectives (trigger = players can set it themselves; dummy = plain storage).
    # spain.state holds #built: 1 means building, 2 means finished. Setup only runs while #built is not 2, so reloads never rebuild.
    function(root, 'load', [
        'scoreboard objectives add spain.travel trigger', 'scoreboard objectives add spain.talk trigger',
        'scoreboard objectives add spain.cooldown dummy', 'scoreboard objectives add spain.quest dummy', 'scoreboard objectives add spain.crystals dummy',
        'scoreboard objectives add spain.state dummy',
        'execute unless score #built spain.state matches 2 run function spain:setup',
    ])

    # `setup`: forceload each dimension's centre chunks (-32..31) because functions can only place blocks in loaded chunks. Then schedule the real build 3 s later to give the game time to load them.
    setup = ['scoreboard players set #built spain.state 1']
    for dimension in ['orbit'] + [p['id'] for p in planets]:
        setup.append(f'execute in spain:{dimension} run forceload add -32 -32 31 31')
    setup += ['execute in spain:orbit run forceload add -96 -128 95 -33', 'schedule function spain:build/all 3s replace']
    function(root, 'setup', setup)

    # `build/all`: build the station, each city, spawn NPCs, mark the build finished (#built = 2), release the forceloads and tell everyone.
    all_build = ['execute in spain:orbit run function spain:build/orbit']
    for p in planets:
        function(root, 'build/' + p['id'], city(p))
        all_build.append(f"execute in spain:{p['id']} run function spain:build/{p['id']}")
    all_build += ['function spain:npc/spawn', 'scoreboard players set #built spain.state 2']
    for dimension in ['orbit'] + [p['id'] for p in planets]:
        all_build.append(f'execute in spain:{dimension} run forceload remove -32 -32 31 31')
    all_build += ['execute in spain:orbit run forceload remove -96 -128 95 -33', 'tellraw @a {"text":"Spain is ready. Type /trigger spain.travel set 1 to visit Starforge Station.","color":"aqua"}']
    function(root, 'build/all', all_build)

    # Station: a 37x37 quartz and concrete platform with cross-shaped cyan walkways, glass railings on all four sides, and two houses.
    orbit = [fill(-18, 63, -18, 18, 64, 18, 'smooth_quartz'), fill(-17, 64, -17, 17, 64, 17, 'gray_concrete'), fill(-3, 64, -16, 3, 64, 16, 'cyan_concrete'), fill(-16, 64, -3, 16, 64, 3, 'cyan_concrete')]
    for x in [-18, 18]:
        orbit += [fill(x, 65, -18, x, 66, 18, 'glass')]
    for z in [-18, 18]:
        orbit += [fill(-18, 65, z, 18, 66, z, 'glass')]
    orbit += house(-14, 5, 'white_concrete', 'cyan_concrete') + house(6, 5, 'white_concrete', 'purple_concrete')

    # Decorative "planet models" floating beyond the station edge (z -100..-76), one per planet, each with a name label. Only the first three planets are shown.
    for x, planet in zip([-64, 0, 64], planets):
        orbit += [fill(x-12, 54, -100, x+12, 77, -76, planet['subsurface']), fill(x-12, 78, -100, x+12, 78, -76, planet['surface']), fill(x-4, 79, -92, x+4, 83, -84, planet['accent'])]

        # The label is a text_display entity (decoration only); the real planet is a separate dimension you travel to.
        # Text display is persistent decoration, separate from the actual visitable dimension.
        orbit.append(f'summon minecraft:text_display {x} 90 -74 {{Tags:["spain.decor"],billboard:"center",text:{{text:{json.dumps(planet["name"])},color:"aqua"}},background:0}}')
    function(root, 'build/orbit', orbit)

    # `tick`: the heartbeat. Welcome new players, count cooldowns down, re-enable trigger objectives (a trigger
    # must be re-enabled after use), and dispatch trigger values to functions, resetting spain.talk afterwards.
    tick = [
        'execute as @a[tag=!spain.joined] run function spain:player/welcome',
        'scoreboard players remove @a[scores={spain.cooldown=1..}] spain.cooldown 1',
        'scoreboard players enable @a[scores={spain.cooldown=0}] spain.travel',
        'scoreboard players enable @a spain.talk',
        'execute as @a[scores={spain.talk=1}] run function spain:dialogue/open_guide',
        'execute as @a[scores={spain.talk=2}] at @s run function spain:quest/accept',
        'execute as @a[scores={spain.talk=3}] at @s run function spain:quest/turn_in',
        'execute as @a[scores={spain.talk=4}] at @s run function spain:quest/collect',
        'scoreboard players set @a[scores={spain.talk=1..}] spain.talk 0',
        'execute as @a[scores={spain.travel=1..}] unless score #built spain.state matches 2 run tellraw @s {"text":"The colonies are still preparing. Try again in a moment.","color":"yellow"}',
    ]

    # One travel function per destination (trigger value -> teleport), selected by trigger value and zero cooldown. Travel is refused with a message until the build finished (#built = 2).
    for travel, dimension, name in [(1, 'orbit', 'Starforge Station')] + [(p['travel'], p['id'], p['name'] + ' · ' + p['city']) for p in planets]:
        tick.append(f'execute as @a[scores={{spain.travel={travel},spain.cooldown=0}}] if score #built spain.state matches 2 run function spain:travel/{dimension}')
        function(root, 'travel/' + dimension, [
            # Travel function body: remember the player has started, teleport to the destination's centre (0.5 65 0.5 centres on the block), set respawn there, start a 40-tick (2 s) cooldown against trigger spam, announce it, play a chime and show the menu.
            'tag @s add spain.started',
            f'execute in spain:{dimension} run teleport @s 0.5 65 0.5 180 0',
            f'execute in spain:{dimension} run spawnpoint @s 0 65 0',
            'scoreboard players set @s spain.cooldown 40', 'scoreboard players set @s spain.travel 0',
            tell(name), 'execute at @s run playsound minecraft:block.amethyst_block.chime master @s ~ ~ ~ 1 .7',
            'function spain:dialogue/menu',
        ])
    tick += [
        # Reset any unhandled travel request, send brand-new players to the station, and lift anyone who fell into the void under the station (y from -64 up 115 blocks, below the platform) back to the centre. extend_pack.py patches these three lines.
        'scoreboard players set @a[scores={spain.travel=1..}] spain.travel 0',
        'execute as @a[tag=!spain.started] if score #built spain.state matches 2 run function spain:travel/orbit',
        'execute in spain:orbit as @a at @s if dimension spain:orbit if entity @s[y=-64,dy=115] run teleport @s 0.5 65 0.5',
    ]
    function(root, 'tick', tick)

    # First-join setup: tag the player and zero every personal score. The `tag` makes the tick function's `!spain.joined` test false afterwards.
    function(root, 'player/welcome', ['tag @s add spain.joined', 'scoreboard players set @s spain.travel 0', 'scoreboard players set @s spain.talk 0', 'scoreboard players set @s spain.cooldown 0', 'scoreboard players set @s spain.quest 0', tell('Welcome to Spain. Right-click named residents to talk. /trigger spain.talk set 1 opens your galaxy guide.'), 'function spain:dialogue/menu'])

    # Chat menu (clickable) and the equivalent native dialog (`galaxy`) listing every destination.
    menu = [{'text': 'GALAXY GUIDE\n', 'color': 'gold', 'bold': True}]
    menu += [button('[Station] ', 'spain.travel', 1)]
    menu += [button('[' + p['name'] + '] ', 'spain.travel', p['travel']) for p in planets]
    function(root, 'dialogue/menu', ['tellraw @s ' + json.dumps(menu), tell('Click a destination above. Right-click Iona, Sera or Lucy to learn more.', 'gray')])
    travel_buttons = [dialog_button('Starforge Station', 'spain.travel', 1)] + [dialog_button(p['name'] + ' · ' + p['city'], 'spain.travel', p['travel']) for p in planets]
    dialog(root, 'galaxy', 'Galaxy Guide', 'Choose a colony to visit. Minecraft building, exploration and saves work on every planet.', travel_buttons)
    function(root, 'dialogue/open_guide', ['dialog show @s spain:galaxy'])

    # NPCs: each is a frozen, invulnerable villager (the visible character) plus an invisible "interaction"
    # entity of the same tags that catches right-clicks. Both are listed in npc/spawn.
    npc_commands = []
    for npc in npcs:
        x, y, z = npc['position']
        tags = f'"spain.npc","spain.{npc["id"]}"'
        name = npc['name'] + ' · ' + npc['role']

        # NBT of the villager: NoAI so it stays put, PersistenceRequired so it never despawns, a visible custom name and a profession for its look.
        villager = f'{{Tags:[{tags}],CustomName:{{text:{json.dumps(name)},color:"aqua"}},CustomNameVisible:1b,NoAI:1b,Invulnerable:1b,PersistenceRequired:1b,VillagerData:{{type:"minecraft:plains",profession:"minecraft:{npc["profession"]}",level:2}}}}'
        npc_dimension = 'minecraft:overworld' if npc['dimension'] == 'earth' else 'spain:' + npc['dimension']
        npc_commands += [f'execute in {npc_dimension} run summon minecraft:villager {x} {y} {z} {villager}']
        npc_commands += [f'execute in {npc_dimension} run summon minecraft:interaction {x} {y} {z} {{Tags:[{tags}],width:0.85f,height:2.0f,response:1b}}']

        # Advancement that fires when a player right-clicks an entity with this NPC's tag; its reward runs the NPC's dialogue function (and that function revokes it, so the NPC can be talked to again).
        write_json(root / f'data/spain/advancement/talk/{npc["id"]}.json', {'criteria': {'talk': {'trigger': 'minecraft:player_interacted_with_entity', 'conditions': {'entity': {'type': 'minecraft:entity_properties', 'entity': 'this', 'predicate': {'minecraft:entity_tags': {'all_of': ['spain.' + npc['id']]}}}}}}, 'rewards': {'function': 'spain:dialogue/' + npc['id']}})
        commands = [f'advancement revoke @s only spain:talk/{npc["id"]}', f'tag @s add spain.met.{npc["id"]}', tell(npc['name'] + ': ' + npc['dialogue'])]

        # What each kind of NPC offers: `travel` opens the destination menu, `guide` gives the journal hint,
        # `quest` offers the three-phase quest "A shared sky", `crystal` hands out the quest item.
        if npc['action'] == 'travel':
            commands += ['function spain:dialogue/menu']
        elif npc['action'] == 'guide':
            commands += [tell('Journal: unite the colonies by helping Iona build the observatory.', 'gold'), 'function spain:dialogue/menu']
        elif npc['action'] == 'quest':
            commands += ['execute if score @s spain.quest matches 0 run tellraw @s ' + json.dumps(button('[Accept: A shared sky]', 'spain.talk', 2, 'green')), 'execute if score @s spain.quest matches 1 run tellraw @s ' + json.dumps(button('[Give Iona one amethyst shard]', 'spain.talk', 3, 'green')), 'execute if score @s spain.quest matches 2 run tellraw @s {"text":"Iona: The observatory is ready. Thank you for bringing our worlds together.","color":"green"}']
        elif npc['action'] == 'crystal':
            commands += ['execute if score @s spain.quest matches 1 unless entity @s[tag=spain.crystal_given] run tellraw @s ' + json.dumps(button('[Collect a survey crystal]', 'spain.talk', 4, 'green'))]

        # Dialog buttons for this NPC. The quest NPC gets one dialog per quest phase (0 not started, 1 shard needed, 2 done), chosen at run time from the player's spain.quest score.
        actions = travel_buttons if npc['action'] == 'travel' else [dialog_button('Galaxy Guide', 'spain.talk', 1)]
        if npc['action'] == 'quest':
            for phase in range(3):
                phase_actions = list(actions)
                if phase == 0: phase_actions.insert(0, dialog_button('Accept: A shared sky', 'spain.talk', 2))
                if phase == 1: phase_actions.insert(0, dialog_button('Give Iona one amethyst shard', 'spain.talk', 3))
                text = npc['dialogue'] if phase < 2 else 'The observatory is ready. Thank you for bringing our worlds together.'
                dialog(root, f'{npc["id"]}_{phase}', npc['name'] + ' · ' + npc['role'], text, phase_actions)
                commands.append(f'execute if score @s spain.quest matches {phase} run dialog show @s spain:{npc["id"]}_{phase}')
        else:
            if npc['action'] == 'crystal': actions.insert(0, dialog_button('Collect a survey crystal', 'spain.talk', 4))
            dialog(root, npc['id'], npc['name'] + ' · ' + npc['role'], npc['dialogue'], actions)
            commands.append(f'dialog show @s spain:{npc["id"]}')
        function(root, 'dialogue/' + npc['id'], commands)
    function(root, 'npc/spawn', npc_commands)

    # Quest "A shared sky" (score spain.quest: 0 not started, 1 active, 2 done). Each function starts with `return 0` guards, so it silently does nothing unless the player is in the right dimension, near the right NPC and in the right phase; that stops players triggering rewards from anywhere.
    # accept: talk to Iona (Astraea) -> active. collect: get a shard from Sera (Cinder), once (tag crystal_given). turn_in: give the shard to Iona -> 4 emeralds.
    function(root, 'quest/accept', ['execute unless score @s spain.quest matches 0 run return 0', 'execute unless dimension spain:astraea run return 0', 'execute unless entity @e[type=minecraft:villager,tag=spain.iona,distance=..6] run return 0', 'scoreboard players set @s spain.quest 1', tell('Journal · A shared sky: Ask Sera in Emberhaven for an amethyst shard, then bring it to Iona.', 'gold')])
    function(root, 'quest/collect', [
        'execute unless score @s spain.quest matches 1 run return 0', 'execute if entity @s[tag=spain.crystal_given] run return 0',
        'execute unless dimension spain:cinder run return 0', 'execute unless entity @e[type=minecraft:villager,tag=spain.sera,distance=..6] run return 0',
        'give @s minecraft:amethyst_shard 1', 'tag @s add spain.crystal_given', tell('Sera: Here you go. Tell Iona the survey crews are cheering her on.', 'green')])
    function(root, 'quest/turn_in', [
        'execute unless score @s spain.quest matches 1 run return 0', 'execute unless dimension spain:astraea run return 0',
        'execute unless entity @e[type=minecraft:villager,tag=spain.iona,distance=..6] run return 0',
        'execute store result score @s spain.crystals run clear @s minecraft:amethyst_shard 0',
        'execute unless score @s spain.crystals matches 1.. run tellraw @s {"text":"Iona: Bring me one amethyst shard. Sera can help.","color":"yellow"}',
        'execute unless score @s spain.crystals matches 1.. run return 0',
        'clear @s minecraft:amethyst_shard 1', 'scoreboard players set @s spain.quest 2', 'give @s minecraft:emerald 4',
        tell('Iona: The observatory can connect all three colonies. We did this together!', 'green'), tell('Quest complete · A shared sky. Reward: 4 emeralds.', 'gold')])

    # Local-only assets: if structures converted from the owner's own files exist (see import_assets.py and import_spore.py), copy them into the pack and place them in each city. They are absent in a fresh clone, and the pack builds fine without them.
    # Optional local Melty conversions are put only in the local pack build.
    local = ROOT / 'local-assets/structures'
    if local.exists():
        destination = root / 'data/spain/structure/imported'
        destination.mkdir(parents=True, exist_ok=True)
        for path in sorted(local.glob('*.nbt')):
            shutil.copy2(path, destination / path.name)
        for planet in planets:
            city_file = root / f'data/spain/function/build/{planet["id"]}.mcfunction'
            additions = []
            if (local / 'crate.nbt').exists(): additions.append('place template spain:imported/crate 8 65 10')
            if planet['id'] == 'astraea' and (local / 'pine.nbt').exists(): additions.append('place template spain:imported/pine 17 65 -5')
            with city_file.open('a') as file: file.write('\n'.join(additions) + '\n')
        shutil.copy2(ROOT / 'local-assets/provenance.json', root / 'LOCAL-ASSET-PROVENANCE.json')

    # Imported here rather than at the top because extend_pack itself imports helpers from this module (a circular import otherwise).
    from extend_pack import extend
    extend(root)

    # Local Spore art needs a credit line and a provenance record inside the pack.
    provenance = ROOT/'local-assets/spore/provenance.json'
    if provenance.exists():
        shutil.copy2(provenance, root/'LOCAL-SPORE-PROVENANCE.json')
        with (root/'CREDITS.txt').open('a') as file: file.write('Local Spore mesh art: EA / Maxis. Archive reading: separately installed SporeModder FX (GPL-3.0).\n')

    # Zip next to the folder: the folder is what Minecraft loads from a world's datapacks folder; the zip is a convenient single file for sharing.
    zip_path = root.parent / (root.name + '.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob('*')):
            if path.is_file(): archive.write(path, path.relative_to(root))
    return zip_path


# Command-line entry point.
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--minecraft-jar', type=Path, default=DEFAULT_JAR)
    args = parser.parse_args()
    print(build(args.minecraft_jar))
