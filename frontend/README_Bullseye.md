# Bullseye Braking - Development Plan

## 1. Game Overview
**Bullseye Braking** is a precision-based training simulation where the player controls a vehicle (represented by a ball, car, or block) that must navigate a road and stop accurately on targets. It emphasizes the "fine motor control" of braking rather than just binary stop/go actions.

## 2. Clinical Value
*   **Visual Recognition:** Training the brain to quickly identify target zones and estimate distance.
*   **Stopping Force Modulation:** Developing a "feel" for deceleration, crucial for real-world driving safety.
*   **Reaction Time:** The "Emergency Target" twist forces the player to inhibit current movement and execute an immediate motor response.
*   **Depth Perception Simulation:** Using 2D scaling or lane positioning to simulate closing distances.

## 3. Technical Architecture (PyQt6)
*   **View Layer:** `QGraphicsView` & `QGraphicsScene` for hardware-accelerated 2D rendering.
*   **Engine:** `QTimer` (set to ~16ms for 60FPS) driving the physics and collision updates.
*   **Physics Component:** A simple acceleration/friction model:
    *   `Velocity += Acceleration (Gas) - Friction - BrakingForce`
*   **Entity System:**
    *   `PlayerVehicle`: Handles position, velocity, and sprite/shape.
    *   `TargetZone`: A multi-layered rectangle with nested scoring areas (e.g., Outer = 10pts, Middle = 50pts, Bullseye = 100pts).

## 4. Step-by-Step Coding Plan

### Phase 1: Environment Setup
1.  Initialize a `QMainWindow` with a `QGraphicsView` as the central widget.
2.  Set up the `QGraphicsScene` with a vertical "Road" background.

### Phase 2: Player Movement
1.  Implement `keyPressEvent` and `keyReleaseEvent` for **Up Arrow** (Gas) and **Down Arrow** (Brake).
2.  Create a `update_physics()` method that calculates displacement based on velocity.
3.  Implement "Forward Only" constraints (player cannot move backward).

### Phase 4: Target Logic
1.  Create a `TargetManager` that spawns `TargetZone` objects at random intervals ahead of the player.
2.  Implement collision detection: when velocity hits 0, check which zone the `PlayerVehicle` center is overlapping.

### Phase 5: Emergency Twist
1.  Implement a timer-based trigger that occasionally spawns a bright red "EMERGENCY" target very close to the player.
2.  Add a penalty for failing to stop within the emergency zone.

### Phase 6: UI & Feedback
1.  Add a HUD (Heads-Up Display) using `QGraphicsTextItem` for Score and Time.
2.  Add visual feedback (e.g., the player object flashes green on a bullseye or red on a miss).
