# Voxel Space Game: Technical Architecture (Java / LWJGL)

This document outlines the software requirements, JVM libraries, and graphics math required to implement the voxel planetary mechanics, the "Origami Warp" landing transition, and hybrid rocket physics in Java.

---

## 🛠 1. Recommended Java Tech Stack

To build a custom voxel engine with high performance and Minecraft-like aesthetics:

| Component | Library / API | Purpose |
| :--- | :--- | :--- |
| **Runtime Environment** | **OpenJDK 21 (JVM)** | Modern garbage collectors (ZGC) for zero-latency chunk loading and memory recycling. |
| **Windowing & Input** | **GLFW (via LWJGL 3)** | High-performance desktop window management, keyboard/mouse polling, and gamepad input support. |
| **Graphics API** | **OpenGL 4.6 (Core Profile)** | Modern programmable pipeline for custom shaders (necessary for the planet warp effect). |
| **Math Library** | **JOML (Java OpenGL Math Library)** | Fast 3D vector, matrix, and quaternion math, optimized for voxel operations. |
| **Audio Engine** | **OpenAL (via LWJGL 3)** | Positional 3D audio for engines, mining lasers, and planetary wind. |
| **Asset Loading** | **Lwjgl-stb** | Fast texture image parsing for pixel-art textures. |

---

## 🪐 2. The "Origami Warp" Landing Transition (Vertex Shader Math)

To create the impressive transition where a cubical planet bends, unfolds, and flattens out beneath the player, we use a custom **GLSL Vertex Shader** during orbital descent.

```
                  [High Orbit: Cubical World]
                           +-------+
                          /       /|
                         /       / |
                        +-------+  |
                        |       |  +
                        |       | /
                        +-------+
                            |
                            | [Descent Phase: GLSL Deformation]
                            v
                      \-----------/   <- Ground begins to fold open
                       \         /
                        \_______/
                            |
                            | [Ground Level: Fully Flattened Grid]
                            v
                  =========================
```

### The Math behind the Deformation Shader (Low-Tech Optimization)
To run smoothly on low-end integrated graphics cards, we choose a **curved dome projection** for the warp. The math uses simple trigonometric sweeps, which require minimal GPU clock cycles:

As the spacecraft descends from Orbit Altitude ($H_{orbit}$) to Ground Altitude ($H_{ground}$), we compute a interpolation factor $t \in [0, 1]$:
$$t = \text{clamp}\left(\frac{\text{PlayerHeight} - H_{ground}}{H_{orbit} - H_{ground}}, 0, 1\right)$$

In the vertex shader, each vertex's coordinate ($P_{cube}$) on the cube face is projected into a flat plane coordinate ($P_{flat}$):
$$P_{final} = \text{lerp}(P_{flat}, P_{cube}, t)$$

*   **Curvature Wave (Low-GPU Cost)**: We bend the horizon downwards by offsetting the vertical position ($P_{final}.y$) as a function of the vertex's horizontal distance from the player, multiplied by $t$:
    $$P_{final}.y -= \sin(\text{Distance} \times 0.02) \times 12.0 \times t$$
*   **When $t = 1$ (Space)**: The world is rendered as a clean rotating voxel cube.
*   **When $0 < t < 1$ (Landing Transition)**: The terrain curves downward at the edges, giving the visual illusion that the cube is folding open like a dome under the ship while the player retains active flight steering.
*   **When $t = 0$ (On the Ground)**: The world has fully flattened out into a standard flat voxel coordinate plane, eliminating coordinate conversion issues while walking.

---

## 📸 3. Camera Portal Lens (Voxel Edge Crossing)

To make walking across the edges of the voxel cube look completely flat and seamless, we implement a **Dynamic View Matrix Offset** when a player approaches face boundaries:
1.  **Face Projection**: The active face has a local orthogonal plane projection.
2.  **Portal Warp Matrix**: When the player's bounding box is within 16 blocks of a cube edge, we compute a transformation matrix that projects the geometry of the adjacent cube face into the active viewport coordinates as if it lay on the same flat plane.
3.  **Rotation Lerp**: As the player steps over the edge boundary, we apply a smooth camera quaternion rotation:
    $$\text{CameraQuaternion} = \text{slerp}(\text{FaceA\_Orientation}, \text{FaceB\_Orientation}, \text{EdgeTransitionProgress})$$
    The camera perspective rolls 90 degrees instantly, but the visual alignment is kept flush by warping the geometry vertices using the portal projection matrix.

---

## 🧭 4. Unified 3D Coordinate Grid & Color Codes

In Java, we utilize **JOML (Java OpenGL Math Library)** vectors to handle coordinates. We maintain a unified $X, Y, Z$ grid across space and planetary dimensions:
*   **Vector Class**: `org.joml.Vector3f` (floating-point for physics) and `org.joml.Vector3i` (integer block coordinates).
*   **Color-Coded Rendering**: When coordinates are logged in the chat box or drawn on the HUD, they are parsed using ANSI/HTML style colors to align with our visual tokens:
    *   **X (Red)**: `new Vector4f(1.0f, 0.2f, 0.2f, 1.0f)`
    *   **Y (Green)**: `new Vector4f(0.2f, 1.0f, 0.2f, 1.0f)`
    *   **Z (Blue)**: `new Vector4f(0.2f, 0.2f, 1.0f, 1.0f)`

---

## 🧬 5. Cloning & Ship Reconstruction Loop (Borderlands-Style)

When the voxel ship collides with an asteroid, it splits blocks apart dynamically using standard voxel grid fracture formulas. If the reactor is destroyed, the ship explodes.

### The Java State Machine for Respawning:

```
[Active Flight / Walking] 
         │
         v (Asteroid Collision / HP = 0)
[Ship Explodes / Player Dies]
         │
         ▼ (Freeze Inputs, Trigger Glitch Fx)
[Deconstitute Player Byte Array]
         │
         ▼ (Deduct Stardust Insurance fee)
[Reconstruct at Nearest Cloning Pad]
         │
         ▼ (Bake Ship Mesh from Saved Blueprint)
[Instantiate New Voxel Ship Entity]
```

*   **Template Persistence**: The player's customized ship layout is stored in RAM as a compressed byte array representing the original placed block grid.
*   **Reconstitution**: On death, the engine instantiates a new player entity at the coordinates of the closest active outposts' Cloning Station, loads the ship template byte array, rebakes the greedy mesh, and places the player back in the cockpit.

---

## 🚀 6. Hybrid Voxel Rocket Mechanics

Rockets are constructed on a local grid, but fly as single entities in space using rigid-body calculations.

### Voxel Mesh Baking (Greedy Meshing)
*   To prevent FPS drops, adjacent internal faces of placed blocks are culled.
*   A "Greedy Meshing" algorithm combines adjacent flat faces of the same texture into larger single quadrilaterals, reducing the draw call vertex count by up to 90%.

### Flight Physics & Control Bindings (Arrows + WASD)
We map GLFW keyboard polling directly to JOML forces and quaternions in our physics tick loop:
1.  **Thrust Control (Up / Down Arrows)**:
    *   `Up Arrow`: Adds a forward force vector along the rocket's local direction vector:
        $$\vec{F}_{thrust} = \text{ForwardDirection} \times \text{EnginePower}$$
    *   `Down Arrow`: Appliess a reverse force vector (deceleration / backup):
        $$\vec{F}_{brake} = -\text{ForwardDirection} \times \text{EnginePower} \times 0.5$$
2.  **Attitude & Direction Steering (W / S / A / D)**:
    *   `W` / `S`: Controls Pitch (nose up/down) by rotating the ship's local X-axis.
    *   `A` / `D`: Controls Roll (tilt left/right) and Yaw (turn left/right) by rotating the local Z and Y axes.
    *   Rotations are accumulated in a quaternion: `org.joml.Quaternionf`.

### Continuous Laser Mining Raycast (JOML Math)
When holding left-click to fire the continuous mining laser:
1.  **Ray Generation**: We cast a 3D ray starting at the player's camera position ($\vec{O}$) along the camera forward vector ($\vec{D}$):
    $$\vec{R}(d) = \vec{O} + d \times \vec{D}$$
2.  **Voxel Intersection Check**: A fast voxel traversal algorithm checks intersected block coordinates along the ray up to a maximum distance of 30 blocks.
3.  **Visual Laser Mesh**: If an intersection occurs, we calculate the distance ($d$) and render a glowing OpenGL cylindrical beam segment stretched from the player's weapon attachment coordinate to the target voxel intersection coordinate. We apply a ticking mining damage counter to the targeted block.

### Low-Performance Block Weather Shader
To render rain/snow block effects efficiently without spawning millions of separate particle objects:
1.  **Particle Grid Columns**: We pre-allocate a tiny grid (e.g. $4 \times 4$ columns) of tall rain-textured block meshes.
2.  **Offset Lock**: This weather mesh grid is parented to the player's current $X, Z$ coordinates so that rain only renders in the player's immediate field of view.
3.  **OpenGL Texture Scrolling**: Instead of moving individual drop vertices on the CPU, the vertex shader scrolls the texture coordinates ($V$) vertically over time inside GPU memory:
    $$V_{new} = V_{old} + (\text{SystemTime} \times \text{FallSpeed})$$
    This gives the perfect visual effect of falling voxel rain while consuming virtually zero CPU/GPU overhead.

---

## 💾 7. Thread-Safe Chunk Pooling & Low-Tech Optimizations

Voxel terrain is split into $16 \times 16 \times 16$ voxel Chunks. To ensure the game runs smoothly on low-tech systems (like older laptops or school computers) without micro-stutters:

### 1. Hard-Capped Rendering Boundaries
*   **8-Chunk Render Distance**: The maximum chunk render distance is capped at 8 chunks (128 blocks sphere). This reduces total active chunks to a fraction of modern render loads, ensuring high FPS on integrated graphics.
*   **Face Culling**: When the player lands and walk-mode is active on a specific cube face, the other 5 faces of the planet are completely unloaded from CPU and GPU memory. This keeps RAM usage under $250\text{MB}$ at all times.

### 2. Zero-Garbage Memory Management
*   **Asynchronous Loading**: Chunk meshing runs in a background pool (`ExecutorService` with 2 threads max to prevent CPU throttling on dual-core processors).
*   **Off-Heap ByteBuffers**: Direct memory allocations via LWJGL's `MemoryUtil` bypass the JVM Garbage Collector.
*   **Chunk Recycling**: Instead of destroying chunk objects and allocating new ones, out-of-range chunks are placed in a pool and rewritten in place, eliminating GC pauses.
