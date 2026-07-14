# Starforge Planets Implementation Plan

Implement a fully playable, rich-aesthetic 3D space web application called **Starforge Planets**. This game will feature a 3D planet creator, rocket builder, open-world space flight, planet walking (landing zones), a right-side controller interface, and local state saving.

---

## User Review Required

> [!IMPORTANT]
> - **Game Engine**: We will build the 3D graphics using **Three.js** loaded via CDN. This allows running the app instantly in a browser without heavy build setups.
> - **Styling**: We will write raw Vanilla CSS to achieve a premium, futuristic dark-cyberpunk/space theme using CSS variables, backdrop-filters (glassmorphism), and neon drop shadows.
> - **Core Loop**: We will implement 4 active game modes:
>   1. **Planet Creator Mode** (3D editor for planet color, size, rings, clouds, and surface elements).
>   2. **Rocket Builder Mode** (3D constructor where players customize nose, body, wing, engine shapes and paint colors).
>   3. **Galaxy Space Flight Mode** (Open-world space piloting, steering the custom rocket around planets, moons, asteroid fields, and collecting resources).
>   4. **Planet Walking Mode** (Landing on a planet, walking around on foot in a third-person view, using a mining tool to extract crystals/plasma).

---

## Proposed Changes

We will create a clean and organized modular project structure within `/Users/mirandazavala/Desktop/spain/`:

### Core Components

#### [NEW] [index.html](file:///Users/mirandazavala/Desktop/spain/index.html)
The entry point. It sets up the UI container, overlay panels (Planet Editor, Rocket Editor, Inventory, Planet landing HUD, and Galaxy Map), the Three.js Canvas, and imports the JS and CSS.

#### [NEW] [style.css](file:///Users/mirandazavala/Desktop/spain/style.css)
The design system stylesheet. Defines custom CSS variables, custom typography, animations, HUD layout, glassmorphic UI card designs, custom buttons, and the interactive PlayStation-like right-side shape button controller.

#### [NEW] [game.js](file:///Users/mirandazavala/Desktop/spain/game.js)
The core JavaScript file containing the Game Controller, Three.js engine setup, asset generators, state management, and interaction logic.

---

## Component Breakdowns

### 1. Three.js Engine & Generators
*   **Scene Controller**: Manages three separate Three.js sub-scenes:
    *   *Creator Scene*: Centered camera, high-detail lighting for editing the planet or rocket.
    *   *Space Scene*: Infinite starfield, orbit lines, celestial bodies (sun, planets, moons), floating resource pickups, and player's custom rocket.
    *   *Planet Surface Scene*: A local terrain mesh, skybox matching the planet's atmospheric colors, outposts, and player character model.
*   **Procedural Planet Generator**: Builds 3D spheres with height maps, vertex noise (for non-spherical shapes), color-gradient materials, clouds (outer rotating sphere), asteroid rings (flat disc), and decorative surface particles (forest pins, crystal pillars, lava flows).
*   **Procedural Rocket Generator**: Dynamically translates rocket configuration parameters into a grouped 3D mesh (nose cone, cylindrical body sections, engine nozzles, thruster particles, wing fins, weapons).
*   **Procedural Character Generator**: Simple cute astronaut model for planet walking mode.

### 2. State & Storage Management
*   **Game State**:
    *   `planet`: Name, primary/secondary colors, ring flag, cloud flag, crater intensity, shape distortion, position in galaxy.
    *   `rocket`: Nose color, body length, engine type, wing shape, trail color.
    *   `player`: X, Y, Z coordinates in space, rotation, speed, inventory (`metal`, `crystal`, `fuel`, `plasma`).
    *   `mode`: `'space' \| 'planet-creator' \| 'rocket-builder' \| 'planet-walking'`.
    *   `activePlanetId`: The target planet when walking.
*   **Save System**: Automatically commits modifications to `localStorage` on any editor change, land/takeoff, or resource pickup.

### 3. User Interface (HUD & Panels)
*   **Main Dashboard**:
    *   Left side: Resource trackers (Metal, Crystal, Fuel, Plasma) with pulsing light indicators.
    *   Right side: Interactive Gamepad containing `X` (Chat), `△` (Inventory), `◯` (Create/Edit), `⬜` (Scan/Map).
*   **Planet Editor Panel**: Sliders for radius, color picker inputs, toggle checkboxes, name input field, and save/exit options.
*   **Rocket Editor Panel**: Selector buttons for nose, body, wing styles, paint hue, and trail colors.
*   **Chat Overlay**: Standard simulation screen for player chat, featuring procedural messages from "alien contacts" or "other explorers".
*   **Map HUD**: Top-down radar representation showing nearby points of interest.

### 4. Interactive Mechanics
*   **Flight Controls**: 
    *   `W`/`S` (or up/down arrow keys) to accelerate/decelerate.
    *   `A`/`D` (or left/right arrow keys) to roll or yaw.
    *   Mouse drag to rotate camera view.
*   **Walking Controls**:
    *   `W`/`A`/`S`/`D` to walk relative to camera view.
    *   `Space` to jump (low gravity simulation based on planet's mass).
    *   Left click to fire the "Mining Laser" at resource nodes, generating beam effects and adding materials to inventory.
*   **Warp/Landing Transitions**:
    *   Warp effect: Particle stretch shaders for space travel when boosting.
    *   Landing sequence: Camera swoops down, clouds flash across, and the player is placed on the terrain next to their landed rocket.

---

## Verification Plan

### Automated Tests
*   Verify code compilation and clean loading in browser console.
*   Ensure state loading does not throw serialization errors if `localStorage` is empty.

### Manual Verification
*   Open the app in Chrome/Safari/Firefox.
*   Test **Planet Creator**: customize a purple planet with rings, name it "Xenon-9", and confirm it displays correctly in space.
*   Test **Rocket Builder**: customize rocket components, change paint to neon green, and inspect the changes in 3D.
*   Test **Space Flight**: steer the rocket in space, crash into a floating crystal resource, and verify inventory updates.
*   Test **Planet Walking**: land on a planet, walk up to a crystal, fire the laser (left-click), gather materials, and take off back to space.
*   Refresh page to confirm all customizations and coordinates persist in `localStorage`.
