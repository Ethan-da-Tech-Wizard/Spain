# Starforge Planets

## Core Pitch

Starforge Planets is a 3D creative space adventure where players build their own planet, design a rocket ship, place their planet in a shared galaxy, and explore space with friends. The game should feel easy to play, generous with resources, and focused on creativity first.

The player should always feel like they have power over their world. The game can have wars, missions, enemies, and danger, but it should not punish the player too harshly or make progress feel slow.

## Game Feel

- 3D movement and camera style inspired by Minecraft dimensionally.
- Creative-first progression.
- Resources are common and easy to collect.
- Building and customization matter more than grinding.
- Players can play peacefully, explore, trade, build, or join space wars.
- The world should feel big, colorful, and alive.

## Technical Direction

- Engine: Unity.
- Language: C#.
- Target platforms: Android tablets/phones, iPhone/iPad, Windows, macOS, and Linux.
- Style: 3D, stylized, colorful, readable on small screens.

## Player Fantasy

The player is the creator and leader of a new planet in a huge galaxy. They can shape the planet, name it, paint it, build cities on it, make rockets, meet other players, and decide whether they want to explore, fight, trade, help, or create.

## Planet Creator

Players can:

- Name their planet.
- Pick planet colors.
- Choose terrain style.
- Add rings.
- Add clouds.
- Add craters.
- Add oceans.
- Add mountains, glowing areas, ice zones, forests, deserts, or lava regions.
- Edit the planet shape so it does not have to be a perfect sphere.
- Add custom flags, symbols, lights, and badges.
- Save multiple versions or presets.

Planet editing should feel powerful and simple. Players should be able to make beautiful planets quickly without needing rare items.

## Shared Galaxy Map

Players can place their planet on a shared map. Other players can see the planet, visit if allowed, send messages, trade, or form alliances.

Map ideas:

- Nearby stars and planets.
- Asteroid belts.
- Space stations.
- Ruins.
- Enemy zones.
- Alliance territories.
- Safe creative zones.
- War zones for players who want combat.

## Rocket Builder

Players build rockets from parts:

- Cockpit.
- Body sections.
- Engines.
- Wings/fins.
- Fuel tanks.
- Cargo modules.
- Shield generators.
- Weapons.
- Scanner/radar parts.
- Decoration parts.
- Paint colors.
- Trails and engine effects.

The rocket builder should be highly creative. Parts should snap together easily, but players should also be able to rotate, scale, color, and decorate pieces.

## Resources

Resources exist, but they should not be hard to get.

Resource types:

- Metal.
- Crystal.
- Fuel.
- Plasma.
- Rare alien tech.
- Stardust.
- Energy cores.
- Food/water for colonies.

Resources should come from:

- Planet mines.
- Asteroids.
- Missions.
- Trading.
- Exploring ruins.
- Daily gifts.
- Alliance sharing.
- Friendly NPCs.

Rare items can exist, but basic building should never feel blocked for too long.

## Planet Upgrades

Players can build:

- Cities.
- Shields.
- Shipyards.
- Farms.
- Mines.
- Defense towers.
- Space elevators.
- Launch pads.
- Research labs.
- Trading hubs.
- Decoration buildings.

Upgrades should look visible on the planet so each world feels unique.

## Space Wars

Combat can include:

- Pirates.
- Rival factions.
- Alien fleets.
- Boss ships.
- Optional player-versus-player zones.
- Alliance wars if players choose to join them.

Important rule: peaceful or creative players should not have their planets destroyed unfairly. War should be opt-in or limited to specific areas.

## Alliances

Players can:

- Create or join alliances.
- Share resources.
- Build group space stations.
- Defend each other.
- Create alliance flags.
- Vote on alliance missions.
- Explore special alliance zones.

## Missions

Mission examples:

- Rescue astronauts.
- Deliver supplies.
- Spy on enemy planets.
- Defend colonies.
- Escort cargo ships.
- Recover alien artifacts.
- Repair a damaged station.
- Clear pirates from an asteroid belt.
- Discover new planets.

Missions should be short enough for phone/tablet play but still fun on computer.

## Cosmetic Fun

Players can customize:

- Planet flags.
- Planet badges.
- Rocket paint.
- Rocket trails.
- Player name banners.
- City styles.
- Space station colors.
- Engine glow.
- Landing effects.

Cosmetics should be a major part of the game.

## Right-Side Button Controls

The right side of the screen has four large shape buttons:

- X button: Toggle player chat on/off. Press once to talk to other players. Press again to stop talking until pressed again.
- Triangle button: Open resource and item menu.
- Circle button idea: Open creative/build mode. This would let players place buildings, edit terrain, decorate the planet, or customize the rocket depending on where they are.
- Square button idea: Open map/scanner mode. This would show nearby planets, missions, players, threats, stations, and resources.

Alternative Circle ideas:

- Boost/dash while flying.
- Interact/confirm.
- Open social/alliance menu.

Alternative Square ideas:

- Inventory quick actions.
- Rocket controls.
- Mission log.

Recommended setup:

- X: Chat toggle.
- Triangle: Resources/items.
- Circle: Create/build/edit.
- Square: Map/scanner/missions.

## First Playable Version

The first version should focus on proving the main fun:

1. 3D planet creator.
2. Basic rocket creator.
3. Fly around a small galaxy.
4. Place the player planet on the map.
5. See simple resource pickups.
6. Open the right-side button menu.
7. Save the player planet and rocket locally.

Online multiplayer and shared planets can come after the single-player creative loop feels good.

## Planet Walking Choice

This choice decides what it means to "go down" onto a planet.

### Option A: Full Walkable Planets

In this version, the whole planet is like a tiny Minecraft-style world. The player can land anywhere, walk around, build things, mine resources, explore caves, and see the sky curve above them.

What the player does:

- Fly to a planet.
- Land anywhere on it.
- Get out of the rocket.
- Walk, jump, build, mine, and explore.
- Place buildings almost anywhere.

Why this is cool:

- It feels very free.
- Players can explore every part of their planet.
- It feels closer to Minecraft.
- A creative player can make big custom areas.

Why it is harder to make:

- The game has to create a whole planet surface.
- Walking around a round planet is more complicated.
- It may be harder to make run well on phones and tablets.
- Multiplayer is harder because every player can change many parts of the planet.

Kid-friendly way to say it:

"You can land anywhere on the planet and run around the whole thing."

### Option B: Landing Zones

In this version, the player still creates and customizes the whole planet from space, but when they land, they visit special areas on the planet. Each planet might have a city zone, a mine zone, a forest zone, a spaceport zone, and a battle zone.

What the player does:

- Fly to a planet.
- Pick a landing spot from a simple menu or map.
- Land in a fun 3D area.
- Walk, build, collect resources, meet NPCs, or start missions.
- Go back to space and choose another area.

Why this is cool:

- It is easier to understand.
- It works better on phones and tablets.
- Each area can look more detailed and polished.
- It is easier to make multiplayer work.
- The player still gets to customize the whole planet from space.

Why it is less free:

- The player cannot walk across every inch of the planet at first.
- Some areas are chosen instead of fully open.

Kid-friendly way to say it:

"You make the whole planet, but when you land, you visit special places on it."

### Recommendation

Start with Option B: Landing Zones.

This is the clearest version for younger players and the easiest first version to build well. The player still gets creative power over the whole planet, but the walking parts are simple, fun, and not overwhelming.

Later, the game can grow toward Option A by adding bigger landing zones, connected zones, and eventually fully walkable planets if the game is running well.

Decision: The first version will use landing zones.

Simple explanation for kids:

"You make the whole planet from space. When you want to visit it, you choose a fun place to land, like the city, mine, forest, spaceport, or battle area."

## Open Questions

- Should players control a character on foot, or mostly control the rocket and planet editor?
- Should combat be arcade-style shooting, strategy-style fleets, or both?
- Should the game require accounts for shared planets, or start offline first?
- What should the final game name be?
