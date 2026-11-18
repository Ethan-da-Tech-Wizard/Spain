# Program: Spain - extend_pack.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Adds the Earth city, rocket workshop, creator dialogs, NPC upgrades and flight-request commands on top of the base data pack built by build_pack.py.
"""Earth-to-station test, layered over the colony content generator."""
# Imports: json for dialog files, Path for files, and helper functions from build_pack.
import json
from pathlib import Path
from build_pack import city, dialog, dialog_button, fill, function, tell, write_json, ROOT


def extend(root: Path):
    """Add the Earth-to-station test content to the pack folder at root."""
    # Append the new scoreboard objectives and Earth setup to the load function.
    # Versioned construction guards also let existing colony saves receive the new city.
    load = root/'data/spain/function/load.mcfunction'
    with load.open('a') as f:
        f.write('scoreboard objectives add spain.ship trigger\nscoreboard objectives add spain.launch dummy\nexecute unless score #earth spain.state matches 2 run function spain:earth/setup\n')
    # Earth setup: mark the state, force-load the area and schedule the build.
    function(root, 'earth/setup', ['scoreboard players set #earth spain.state 1', 'execute in minecraft:overworld run forceload add -32 -32 31 31', 'schedule function spain:earth/build 4s replace'])
    # Collect the commands that build Earth's city, starting with stone below and air above to clear space.
    earth = []
    for y in range(60, 96, 6): earth.append(fill(-26,y,-26,26,min(y+5,95),26,'stone'))
    for y in range(97, 142, 6): earth.append(fill(-26,y,-26,26,min(y+5,141),26,'air'))
    # Reuse the colony city design with forest settings.
    planet = {'surface':'grass_block','accent':'lime_concrete','wall':'oak_planks','roof':'deepslate_tiles','theme':'forest'}
    # Translate the city upward, leaving the rest of the normal overworld untouched.
    import re
    # Take the city commands (without the last five) and move them up 32 blocks; the code edits the y values of fill and setblock commands.
    for command in city(planet)[:-5]:
        if command.startswith('fill '):
            parts=command.split(); parts[2]=str(int(parts[2])+32); parts[5]=str(int(parts[5])+32); command=' '.join(parts)
        elif command.startswith('setblock '):
            parts=command.split(); parts[2]=str(int(parts[2])+32); command=' '.join(parts)
        earth.append(command)
    # Add a yellow launch pad.
    earth += [fill(7,96,-2,13,96,4,'yellow_concrete')]
    # Editable hull around an open cockpit, built with native Minecraft materials.
    # Build the rocket hull frame: four iron pillars with magma bases.
    for x,z in [(8,0),(10,0),(8,2),(10,2)]:
        earth += [fill(x,97,z,x,100,z,'iron_block'), f'setblock {x} 97 {z} minecraft:magma_block']
    # Add the roof, lightning rod, floor and window.
    earth += [fill(8,101,0,10,101,2,'white_concrete'), 'setblock 9 102 1 minecraft:lightning_rod', 'setblock 9 97 1 minecraft:iron_block', 'setblock 9 99 0 minecraft:glass']
    # If the local Spore models exist, place them too.
    if (ROOT/'local-assets/structures/spore_rocket.nbt').exists():
        earth += ['place template spain:imported/spore_rocket 12 97 -8','place template spain:imported/spore_thruster 18 97 3']
    # Summon the visitor animals and other creatures near the plaza.
    earth += ['summon minecraft:cow -21 97 5 {Tags:["spain.alien","spain.friendly"],Age:-24000,PersistenceRequired:1b,CustomName:{text:"Sprout · curious visitor"}}','summon minecraft:pig -21 97 8 {Age:-24000,PersistenceRequired:1b}', 'summon minecraft:goat -21 97 11 {Tags:["spain.alien","spain.neutral"],PersistenceRequired:1b,CustomName:{text:"Pebble · indifferent visitor"}}','summon minecraft:husk 25 97 -22 {Tags:["spain.alien","spain.hostile"],PersistenceRequired:1b,CustomName:{text:"Grumble · grumpy visitor"}}']
    # NPC construction is guarded separately; upgrading never doubles residents.
    # Move the overworld NPC spawn lines from the NPC spawn function into the Earth build function.
    spawn=root/'data/spain/function/npc/spawn.mcfunction'
    lines=spawn.read_text().splitlines()
    earth += [line for line in lines if 'in minecraft:overworld' in line]
    spawn.write_text('\n'.join(line for line in lines if 'in minecraft:overworld' not in line)+'\n')
    # Mark Earth as built and stop force-loading.
    earth += ['scoreboard players set #earth spain.state 2', 'execute in minecraft:overworld run forceload remove -32 -32 31 31']
    # Write the Earth build function.
    function(root, 'earth/build', earth)
    # Wrap the build so it runs in the overworld.
    # Scheduled functions default to overworld, explicitly wrap for clarity.
    path=root/'data/spain/function/earth/build.mcfunction'
    body=path.read_text(); function(root,'earth/build_geometry',body.splitlines())
    function(root,'earth/build',['execute in minecraft:overworld run function spain:earth/build_geometry'])
    # Edit the main tick function: change the travel targets, block travel while piloting, and add the rocket request triggers.
    tick=root/'data/spain/function/tick.mcfunction'
    text=tick.read_text().replace('run function spain:travel/orbit\n','run function spain:travel/earth\n')
    # Above replacement also affects travel=1 dispatch; restore station destination.
    text=text.replace('scores={spain.travel=1,spain.cooldown=0}] if score #built spain.state matches 2 run function spain:travel/earth','scores={spain.travel=1,spain.cooldown=0}] if score #built spain.state matches 2 run function spain:travel/orbit')
    text=text.replace('if entity @s[y=-64,dy=115]','unless entity @s[tag=spain.pilot] if entity @s[y=-64,dy=115]')
    # All travel modes are available immediately during this freedom-focused test.
    text=text.replace('scoreboard players set @a[scores={spain.travel=1..}] spain.travel 0', 'execute as @a[scores={spain.travel=5,spain.cooldown=0}] if score #earth spain.state matches 2 run function spain:travel/earth\nscoreboard players set @a[scores={spain.travel=1..}] spain.travel 0')
    text += '\nscoreboard players enable @a spain.ship\n'
    # Map each trigger value to a request tag read by the Java mod.
    for value,tag in [(1,'capture'),(2,'board'),(3,'land'),(5,'spore'),(6,'recall'),(7,'create')]:
        text += f'execute as @a[scores={{spain.ship={value}}}] run tag @s add spain.request.{tag}\n'
    text += 'execute as @a[scores={spain.ship=4}] run dialog show @s spain:rocket\nscoreboard players set @a spain.ship 0\n'
    # Write the edited tick function back.
    tick.write_text(text)
    # Create the travel-to-Earth function.
    function(root,'travel/earth',['tag @s add spain.started','execute in minecraft:overworld run teleport @s 0.5 97 0.5 90 0','execute in minecraft:overworld run spawnpoint @s 0 97 0','scoreboard players set @s spain.cooldown 0','scoreboard players set @s spain.travel 0',tell('Earth · Harborlight. Speak to Mira, then Dr Pip at the east workshop.'),'function spain:dialogue/menu'])
    # Remove the travel cooldown from every travel function.
    # Quick travel can interrupt or resume freeflight without a waiting timer.
    for p in (root/'data/spain/function/travel').glob('*.mcfunction'):
        text=p.read_text().replace('spain.cooldown 40','spain.cooldown 0')
        p.write_text(text)
    # Reset the new scores for new players.
    welcome=root/'data/spain/function/player/welcome.mcfunction'
    with welcome.open('a') as f:
        f.write('scoreboard players set @s spain.ship 0\nscoreboard players set @s spain.launch 0\n')
    # Schedule the NPC upgrade once.
    with load.open('a') as f:f.write('execute unless score #npc_version spain.state matches 2 run schedule function spain:npc/upgrade_init 6s replace\n')
    with (root/'data/spain/function/build/all.mcfunction').open('a') as f:f.write('scoreboard players set #npc_version spain.state 2\n')
    # Add the Earth and Rocket controls buttons to the chat menu.
    menu=root/'data/spain/function/dialogue/menu.mcfunction'
    with menu.open('a') as f:
        f.write('tellraw @s '+json.dumps([{'text':'[Earth] ','color':'green','click_event':{'action':'run_command','command':'/trigger spain.travel set 5'}},{'text':'[Rocket controls]','color':'gold','click_event':{'action':'run_command','command':'/trigger spain.ship set 4'}}])+'\n')
    # Add an Earth button to the Galaxy Guide dialog.
    galaxy=root/'data/spain/dialog/galaxy.json'; content=json.loads(galaxy.read_text()); content['actions'].insert(0,dialog_button('Earth · Harborlight','spain.travel',5)); galaxy.write_text(json.dumps(content,indent=2)+'\n')
    # Buttons for the rocket workshop dialog.
    rocket_actions=[dialog_button('Open rocket creator','spain.ship',7),dialog_button('Go to my rocket','spain.ship',6),dialog_button('Capture workshop design','spain.ship',1),dialog_button('Board / resume freeflight','spain.ship',2),dialog_button('Land / leave cockpit','spain.ship',3),dialog_button('Add imported Spore hull to workshop','spain.ship',5),dialog_button('Quick travel: Galaxy Guide','spain.talk',1)]
    # Create the rocket workshop dialog with building and flight instructions.
    dialog(root,'rocket','Rocket workshop & flight','Build freely on the east pad (X 8–20, Y 97–103, Z -8–7), then Capture and Board. WASD moves; Space rises; Shift descends. Fly above Y 280 to enter space. Land beside a surface or leave the ship to settle. Use /spain corner1 X Y Z and corner2 to select a larger blueprint: no part-count limit. Your spacesuit works forever in space; underwater breath still runs out.',rocket_actions)
    # Buttons for the rocket creator dialog.
    creator_actions=[{'label':label,'width':210,'action':{'type':'minecraft:run_command','command':'/spain design '+part}} for label,part in [('Add Spore hull','hull'),('Add symmetric wings','wings'),('Add Spore engine','engine'),('Add glass cockpit','cabin'),('Stretch the design','stretch'),('Rotate preview','rotate'),('Undo last part','undo'),('Clear / start again','clear')]]
    # Add boarding, capture and travel buttons.
    creator_actions += [dialog_button('Board and take off','spain.ship',2),dialog_button('Capture a block sculpture','spain.ship',1),dialog_button('Quick travel anywhere','spain.talk',1)]
    # Create the rocket creator dialog.
    dialog(root,'creator','Create a rocket','Build a rocket from parts. Hulls and engines use local Spore geometry; wings and cabins share Minecraft materials. Add components without a part budget, stretch the shape, or undo changes. Close this screen to inspect the preview in front of you. Board to pilot from inside the craft. F5 switches between cockpit and chase views. No NPC is needed.',creator_actions)
    # Use two columns for the creator dialog.
    creator=root/'data/spain/dialog/creator.json';data=json.loads(creator.read_text());data['columns']=2;creator.write_text(json.dumps(data,indent=2)+'\n')
    # Create the launch quest function that gives the spacesuit and building blocks.
    function(root,'quest/launch',['execute unless dimension minecraft:overworld run return 0','execute unless entity @e[type=minecraft:villager,tag=spain.scientist,distance=..6] run return 0','execute if score @s spain.launch matches 2.. run return 0','scoreboard players set @s spain.launch 2','tag @s add spain.suit','give @s minecraft:iron_block 64','give @s minecraft:white_concrete 64','give @s minecraft:glass 32','give @s minecraft:magma_block 16','give @s minecraft:iron_helmet 1','give @s minecraft:iron_chestplate 1','give @s minecraft:iron_leggings 1','give @s minecraft:iron_boots 1',tell('Dr Pip: Spacesuit activated. Build the rocket, capture it, and board. Shift to descend, Space to climb.','gold')])
    # Add the new behavior to the NPC dialogue functions.
    npcs=json.loads((ROOT/'content/npcs.json').read_text())
    for n in npcs:
        path=root/f'data/spain/function/dialogue/{n["id"]}.mcfunction'
        if n['action']=='launch_guide':
            with path.open('a') as f:f.write('execute unless score @s spain.launch matches 1.. run scoreboard players set @s spain.launch 1\n')
        if n['action']=='scientist':
            dialog(root,n['id'],n['name'],n['dialogue'],rocket_actions)
            with path.open('a') as f:f.write('execute at @s run function spain:quest/launch\n')
        if n['action']=='arrival':
            with path.open('a') as f:f.write('function spain:quest/arrival\n')
    # Build the NPC upgrade function: re-run each summon only if that NPC does not exist yet.
    upgrade=[]
    for line in lines:
        if 'run summon ' not in line:continue
        dimension=line.split(' in ')[1].split(' ')[0]; tag=line.split('"spain.npc","')[1].split('"')[0]
        entity='minecraft:interaction' if 'summon minecraft:interaction' in line else 'minecraft:villager'
        upgrade.append(line.replace(' run summon ',f' unless entity @e[type={entity},tag={tag}] run summon '))
    upgrade += ['scoreboard players set #npc_version spain.state 2']
    # The init function force-loads each world, then runs the upgrade.
    upgrade_init=['execute if score #npc_version spain.state matches 2 run return 0']
    # Force-load each world for the upgrade, then release it afterward.
    for dimension in ['minecraft:overworld','spain:orbit','spain:astraea','spain:cinder','spain:borealis']:
        upgrade_init.append(f'execute in {dimension} run forceload add -32 -32 31 31')
        upgrade.append(f'execute in {dimension} run forceload remove -32 -32 31 31')
    upgrade_init.append('schedule function spain:npc/upgrade 2s replace')
    # Write the two upgrade functions.
    function(root,'npc/upgrade_init',upgrade_init)
    function(root,'npc/upgrade',upgrade)
    # Tag the Lucy, diplomat and medic NPCs as aliens.
    # Some residents already come from other worlds; dialogue hitboxes stay unchanged.
    with spawn.open('a') as f:
        for npc in ['lucy','diplomat','medic']:
            f.write(f'execute in spain:orbit run tag @e[type=minecraft:villager,tag=spain.{npc}] add spain.alien\n')
            with (root/'data/spain/function/npc/upgrade.mcfunction').open('a') as u:u.write(f'execute in spain:orbit run tag @e[type=minecraft:villager,tag=spain.{npc}] add spain.alien\n')
    # Create the arrival function that completes the flight test.
    function(root,'quest/arrival',['execute if entity @s[tag=spain.test_complete] run return 0','execute unless score @s spain.launch matches 3.. run return 0','tag @s add spain.test_complete','scoreboard players set @s spain.launch 4','title @s title {"text":"Endless possibility","color":"aqua"}','title @s subtitle {"text":"Flight test complete · keep exploring","color":"gold"}',tell('The station workers welcome you to the world of endless possibility. Test complete! Your galaxy stays open.','green')])
