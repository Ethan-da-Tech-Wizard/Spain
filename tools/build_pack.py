#!/usr/bin/env python3
"""Build a vanilla Minecraft 26.3 adventure from reviewable content and functions."""
from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JAR = Path.home() / '.local/share/PrismLauncher/libraries/com/mojang/minecraft/26.3/minecraft-26.3-client.jar'


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def tell(text: str, color: str = 'aqua') -> str:
    return 'tellraw @s ' + json.dumps({'text': text, 'color': color}, ensure_ascii=False)


def button(text: str, objective: str, value: int, color: str = 'aqua') -> dict:
    return {'text': text, 'color': color, 'click_event': {'action': 'run_command', 'command': f'/trigger {objective} set {value}'}}


def dialog_button(text: str, objective: str, value: int) -> dict:
    return {'label': text, 'width': 210, 'action': {'type': 'minecraft:run_command', 'command': f'/trigger {objective} set {value}'}}


def dialog(root: Path, name: str, title: str, text: str, actions: list[dict]) -> None:
    write_json(root / f'data/spain/dialog/{name}.json', {'type': 'minecraft:multi_action', 'title': title, 'body': [{'type': 'minecraft:plain_message', 'contents': text, 'width': 350}], 'actions': actions, 'columns': 1, 'exit_action': {'label': 'Goodbye', 'width': 210}, 'pause': False, 'after_action': 'close'})


def function(root: Path, name: str, commands: list[str]) -> None:
    path = root / 'data/spain/function' / (name + '.mcfunction')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(commands) + '\n')


def fill(x1, y1, z1, x2, y2, z2, block):
    assert (abs(x2-x1)+1)*(abs(y2-y1)+1)*(abs(z2-z1)+1) <= 32768
    return f'fill {x1} {y1} {z1} {x2} {y2} {z2} minecraft:{block}'


def house(x: int, z: int, wall: str, roof: str) -> list[str]:
    return [
        fill(x, 64, z, x+8, 64, z+8, 'stone_bricks'),
        fill(x, 65, z, x+8, 69, z+8, wall),
        fill(x+1, 65, z+1, x+7, 68, z+7, 'air'),
        fill(x-1, 70, z-1, x+9, 70, z+9, roof),
        fill(x+3, 65, z+8, x+5, 67, z+8, 'air'),
        fill(x, 66, z+2, x, 67, z+6, 'glass'),
        fill(x+8, 66, z+2, x+8, 67, z+6, 'glass'),
        f'setblock {x+2} 65 {z+2} minecraft:crafting_table',
        f'setblock {x+6} 65 {z+2} minecraft:barrel',
        f'setblock {x+4} 68 {z+4} minecraft:sea_lantern',
    ]


def city(planet: dict) -> list[str]:
    commands = [
        '# Generated once. Reloading never rebuilds or erases a city.',
        fill(-26, 64, -26, 26, 64, 26, planet['surface']),
        fill(-3, 64, -24, 3, 64, 24, 'stone_bricks'),
        fill(-24, 64, -3, 24, 64, 3, 'stone_bricks'),
        fill(-4, 64, -4, 4, 64, 4, 'smooth_quartz'),
        fill(-2, 64, -2, 2, 64, 2, planet['accent']),
    ]
    for x, z in [(-20, -20), (12, -20), (-20, 12), (12, 12)]:
        commands.extend(house(x, z, planet['wall'], planet['roof']))
    for x, z in [(-6, -6), (6, -6), (-6, 6), (6, 6)]:
        commands.extend([fill(x, 65, z, x, 68, z, 'iron_bars'), f'setblock {x} 69 {z} minecraft:sea_lantern'])
    for x, z in [(-24, 0), (24, 0), (0, -24), (0, 24)]:
        if planet['theme'] == 'forest':
            commands += [fill(x, 65, z, x, 69, z, 'oak_log'), fill(x-2, 69, z-2, x+2, 71, z+2, 'oak_leaves[persistent=true]')]
        else:
            commands += [fill(x, 65, z, x, 69, z, 'amethyst_block'), f'setblock {x} 70 {z} minecraft:sea_lantern']
    # A rocket monument makes the spaceport visible without claiming piloted flight yet.
    commands += [fill(8, 65, 0, 10, 71, 2, 'iron_block'), fill(9, 72, 1, 9, 74, 1, 'white_concrete'), 'setblock 9 69 0 minecraft:light_blue_stained_glass', 'setblock 8 65 0 minecraft:magma_block', 'setblock 10 65 0 minecraft:magma_block']
    return commands


def build(jar: Path = DEFAULT_JAR, output: Path | None = None) -> Path:
    root = output or ROOT / 'dist/Spain'
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    planets = json.loads((ROOT / 'content/planets.json').read_text())
    npcs = json.loads((ROOT / 'content/npcs.json').read_text())
    with zipfile.ZipFile(jar) as archive:
        version = json.loads(archive.read('version.json'))
        if version['id'] != '26.3':
            raise ValueError('This pack targets Minecraft 26.3')
        base_type = json.loads(archive.read('data/minecraft/dimension_type/overworld.json'))
        world_preset = json.loads(archive.read('data/minecraft/worldgen/world_preset/normal.json'))
    write_json(root / 'pack.mcmeta', {'pack': {'description': 'Spain · Starforge planets, cities and conversations', 'min_format': [121, 0], 'max_format': [121, 0]}})
    (root / 'CREDITS.txt').write_text('Spain content by Ethan-da-Tech-Wizard. Minecraft game assets are provided by your own Minecraft installation. No Minecraft binaries are bundled.\n')
    for planet in planets + [{'id': 'orbit', 'biome': 'the_void', 'sky': '#050817', 'fog': '#090e22'}]:
        dim_type = json.loads(json.dumps(base_type))
        dim_type.update({'min_y': 0, 'height': 384, 'logical_height': 384, 'monster_spawn_light_level': 0})
        dim_type['attributes']['minecraft:visual/sky_color'] = planet['sky']
        dim_type['attributes']['minecraft:visual/fog_color'] = planet['fog']
        if planet['id'] == 'orbit':
            dim_type.update({'ambient_light': .5, 'has_fixed_time': True, 'skybox': 'end'})
            dim_type['attributes']['minecraft:visual/sky_light_factor'] = 0.0
        write_json(root / f"data/spain/dimension_type/{planet['id']}.json", dim_type)
        layers = [] if planet['id'] == 'orbit' else [
            {'block': 'minecraft:bedrock', 'height': 1}, {'block': 'minecraft:stone', 'height': 59},
            {'block': 'minecraft:' + planet['subsurface'], 'height': 3}, {'block': 'minecraft:' + planet['surface'], 'height': 1}]
        write_json(root / f"data/spain/dimension/{planet['id']}.json", {'type': 'spain:' + planet['id'], 'generator': {'type': 'minecraft:flat', 'settings': {'biome': 'minecraft:' + planet['biome'], 'features': False, 'lakes': False, 'layers': layers, 'structure_overrides': []}}})
        world_preset['dimensions']['spain:' + planet['id']] = json.loads((root / f"data/spain/dimension/{planet['id']}.json").read_text())
    write_json(root / 'data/spain/worldgen/world_preset/starforge.json', world_preset)
    write_json(root / 'data/minecraft/tags/worldgen/world_preset/normal.json', {'replace': False, 'values': ['spain:starforge']})

    for tag in ['load', 'tick']:
        write_json(root / f'data/minecraft/tags/function/{tag}.json', {'values': ['spain:' + tag]})
    function(root, 'load', [
        'scoreboard objectives add spain.travel trigger', 'scoreboard objectives add spain.talk trigger',
        'scoreboard objectives add spain.cooldown dummy', 'scoreboard objectives add spain.quest dummy', 'scoreboard objectives add spain.crystals dummy',
        'scoreboard objectives add spain.state dummy',
        'execute unless score #built spain.state matches 2 run function spain:setup',
    ])
    setup = ['scoreboard players set #built spain.state 1']
    for dimension in ['orbit'] + [p['id'] for p in planets]:
        setup.append(f'execute in spain:{dimension} run forceload add -32 -32 31 31')
    setup += ['execute in spain:orbit run forceload add -96 -128 95 -33', 'schedule function spain:build/all 3s replace']
    function(root, 'setup', setup)
    all_build = ['execute in spain:orbit run function spain:build/orbit']
    for p in planets:
        function(root, 'build/' + p['id'], city(p))
        all_build.append(f"execute in spain:{p['id']} run function spain:build/{p['id']}")
    all_build += ['function spain:npc/spawn', 'scoreboard players set #built spain.state 2']
    for dimension in ['orbit'] + [p['id'] for p in planets]:
        all_build.append(f'execute in spain:{dimension} run forceload remove -32 -32 31 31')
    all_build += ['execute in spain:orbit run forceload remove -96 -128 95 -33', 'tellraw @a {"text":"Spain is ready. Type /trigger spain.travel set 1 to visit Starforge Station.","color":"aqua"}']
    function(root, 'build/all', all_build)
    orbit = [fill(-18, 63, -18, 18, 64, 18, 'smooth_quartz'), fill(-17, 64, -17, 17, 64, 17, 'gray_concrete'), fill(-3, 64, -16, 3, 64, 16, 'cyan_concrete'), fill(-16, 64, -3, 16, 64, 3, 'cyan_concrete')]
    for x in [-18, 18]:
        orbit += [fill(x, 65, -18, x, 66, 18, 'glass')]
    for z in [-18, 18]:
        orbit += [fill(-18, 65, z, 18, 66, z, 'glass')]
    orbit += house(-14, 5, 'white_concrete', 'cyan_concrete') + house(6, 5, 'white_concrete', 'purple_concrete')
    for x, planet in zip([-64, 0, 64], planets):
        orbit += [fill(x-12, 54, -100, x+12, 77, -76, planet['subsurface']), fill(x-12, 78, -100, x+12, 78, -76, planet['surface']), fill(x-4, 79, -92, x+4, 83, -84, planet['accent'])]
        # Text display is persistent decoration, separate from the actual visitable dimension.
        orbit.append(f'summon minecraft:text_display {x} 90 -74 {{Tags:["spain.decor"],billboard:"center",text:{{text:{json.dumps(planet["name"])},color:"aqua"}},background:0}}')
    function(root, 'build/orbit', orbit)

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
    for travel, dimension, name in [(1, 'orbit', 'Starforge Station')] + [(p['travel'], p['id'], p['name'] + ' · ' + p['city']) for p in planets]:
        tick.append(f'execute as @a[scores={{spain.travel={travel},spain.cooldown=0}}] if score #built spain.state matches 2 run function spain:travel/{dimension}')
        function(root, 'travel/' + dimension, [
            'tag @s add spain.started',
            f'execute in spain:{dimension} run teleport @s 0.5 65 0.5 180 0',
            f'execute in spain:{dimension} run spawnpoint @s 0 65 0',
            'scoreboard players set @s spain.cooldown 40', 'scoreboard players set @s spain.travel 0',
            tell(name), 'execute at @s run playsound minecraft:block.amethyst_block.chime master @s ~ ~ ~ 1 .7',
            'function spain:dialogue/menu',
        ])
    tick += [
        'scoreboard players set @a[scores={spain.travel=1..}] spain.travel 0',
        'execute as @a[tag=!spain.started] if score #built spain.state matches 2 run function spain:travel/orbit',
        'execute in spain:orbit as @a at @s if dimension spain:orbit if entity @s[y=-64,dy=115] run teleport @s 0.5 65 0.5',
    ]
    function(root, 'tick', tick)
    function(root, 'player/welcome', ['tag @s add spain.joined', 'scoreboard players set @s spain.travel 0', 'scoreboard players set @s spain.talk 0', 'scoreboard players set @s spain.cooldown 0', 'scoreboard players set @s spain.quest 0', tell('Welcome to Spain. Right-click named residents to talk. /trigger spain.talk set 1 opens your galaxy guide.'), 'function spain:dialogue/menu'])
    menu = [{'text': 'GALAXY GUIDE\n', 'color': 'gold', 'bold': True}]
    menu += [button('[Station] ', 'spain.travel', 1)]
    menu += [button('[' + p['name'] + '] ', 'spain.travel', p['travel']) for p in planets]
    function(root, 'dialogue/menu', ['tellraw @s ' + json.dumps(menu), tell('Click a destination above. Right-click Iona, Sera or Lucy to learn more.', 'gray')])
    travel_buttons = [dialog_button('Starforge Station', 'spain.travel', 1)] + [dialog_button(p['name'] + ' · ' + p['city'], 'spain.travel', p['travel']) for p in planets]
    dialog(root, 'galaxy', 'Galaxy Guide', 'Choose a colony to visit. Minecraft building, exploration and saves work on every planet.', travel_buttons)
    function(root, 'dialogue/open_guide', ['dialog show @s spain:galaxy'])

    npc_commands = []
    for npc in npcs:
        x, y, z = npc['position']
        tags = f'"spain.npc","spain.{npc["id"]}"'
        name = npc['name'] + ' · ' + npc['role']
        villager = f'{{Tags:[{tags}],CustomName:{{text:{json.dumps(name)},color:"aqua"}},CustomNameVisible:1b,NoAI:1b,Invulnerable:1b,PersistenceRequired:1b,VillagerData:{{type:"minecraft:plains",profession:"minecraft:{npc["profession"]}",level:2}}}}'
        npc_dimension = 'minecraft:overworld' if npc['dimension'] == 'earth' else 'spain:' + npc['dimension']
        npc_commands += [f'execute in {npc_dimension} run summon minecraft:villager {x} {y} {z} {villager}']
        npc_commands += [f'execute in {npc_dimension} run summon minecraft:interaction {x} {y} {z} {{Tags:[{tags}],width:0.85f,height:2.0f,response:1b}}']
        write_json(root / f'data/spain/advancement/talk/{npc["id"]}.json', {'criteria': {'talk': {'trigger': 'minecraft:player_interacted_with_entity', 'conditions': {'entity': {'type': 'minecraft:entity_properties', 'entity': 'this', 'predicate': {'minecraft:entity_tags': {'all_of': ['spain.' + npc['id']]}}}}}}, 'rewards': {'function': 'spain:dialogue/' + npc['id']}})
        commands = [f'advancement revoke @s only spain:talk/{npc["id"]}', f'tag @s add spain.met.{npc["id"]}', tell(npc['name'] + ': ' + npc['dialogue'])]
        if npc['action'] == 'travel':
            commands += ['function spain:dialogue/menu']
        elif npc['action'] == 'guide':
            commands += [tell('Journal: unite the colonies by helping Iona build the observatory.', 'gold'), 'function spain:dialogue/menu']
        elif npc['action'] == 'quest':
            commands += ['execute if score @s spain.quest matches 0 run tellraw @s ' + json.dumps(button('[Accept: A shared sky]', 'spain.talk', 2, 'green')), 'execute if score @s spain.quest matches 1 run tellraw @s ' + json.dumps(button('[Give Iona one amethyst shard]', 'spain.talk', 3, 'green')), 'execute if score @s spain.quest matches 2 run tellraw @s {"text":"Iona: The observatory is ready. Thank you for bringing our worlds together.","color":"green"}']
        elif npc['action'] == 'crystal':
            commands += ['execute if score @s spain.quest matches 1 unless entity @s[tag=spain.crystal_given] run tellraw @s ' + json.dumps(button('[Collect a survey crystal]', 'spain.talk', 4, 'green'))]
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
    from extend_pack import extend
    extend(root)
    provenance = ROOT/'local-assets/spore/provenance.json'
    if provenance.exists():
        shutil.copy2(provenance, root/'LOCAL-SPORE-PROVENANCE.json')
        with (root/'CREDITS.txt').open('a') as file: file.write('Local Spore mesh art: EA / Maxis. Archive reading: separately installed SporeModder FX (GPL-3.0).\n')
    zip_path = root.parent / (root.name + '.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob('*')):
            if path.is_file(): archive.write(path, path.relative_to(root))
    return zip_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--minecraft-jar', type=Path, default=DEFAULT_JAR)
    args = parser.parse_args()
    print(build(args.minecraft_jar))
