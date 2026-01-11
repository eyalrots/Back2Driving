# System Architecture

## Overview
This platform utilizes a `Raspberry Pi Zero 2 W` to drive a real-time driving simulator for lower-limb rehabilitation. The system interfaces with physical hardware (Gas and Brake pedals) and provides immediate visual feedback via a mini-HDMI display.

To ensure low latency and high reliability, the software employs a `multi-threaded architecture` optimized for the Pi's quad-core Cortex-A53 processor. The design prioritizes sensor accuracy and smooth visual rendering by decoupling data acquisition from the simulation loop.

## Architectural design
The software is devided into three primary concurrent threads, utilizing CPU affinity to minimize context switching and maximize deterministic behavior.

### 1. The Input Engine (Hardware Interface)
* **Role**: High-frequency Data Acquisition.
* **Responsibility**: This thread handles the General Purpose Input/Output (GPIO) interface. It polls the `Hall-Effect Sensor` (Gas pedal) and the `Loac cell` (Breake pedal) synchronously.
* **Optimization**: By combining both sensors unto a single high-priority thread, we ensure that the state is the pedals is captured atomically, preventing "skew" between gas and brake readings. This thread pushes normalized data into a thread-safe circular buffer for the Logic Engine to consume.

### 2. The Logic Engine (Data Processing)
* **Role**: Real-time Physics & Rehabilitation Algorithms.
* **Responsibility**: This thread consumes raw sensor data to calculate rehabilitation metrics, such as:
    * Reaction time (latency between simulus and pedal depression).
    * Peak breaking force (analyzed from Load cell strain).
* **Optimization**: This thread runs decoupled from rendering frame rate. This ensures that even if the graphics lag (frame drop), the medical data collection remains percise and uninterrupted.

### 3. The Simulation Engine (Presentation Layer)
* **Role**: User Interuction & Visual Feedback.
* **Responsibility**: Renders the driving enviroment and feedback UI to the display. It reads the processed "World State" from the `Logic Engine` and updates the screen at 60 FPS (or 30 depending on harware limitations).
* **Oprimization**: As the most compute-intensive task, this thread is allocated the majority of remaining CPU reasouces. It is isolated from the sensor timing to prevent graphical operations from blocking the reading of critical sensors.

## Technical Specifications
* **Hardware**: Raspberry Pi Zero 2 W (Quad-core 1GHz ARM Cortex-A53).
* **Sensors**: Hall-Effect (Analog / PWM), Load Cell (HX711 Interface).
* **Concurrency Model**: Producer-Consumer pattern with Mutex-protected shared state.

## Implementation Strategy
To balance real-time hardware constraints with rich visual feedback, the system is split into two independent processes communicating via `Shared Memory (IPC)`.

### 1. Read-Time Backend (C)
* **Role**: Handles all `Input Engine` and `Logic Engine`.
* **Responsibilities**: 
    * Direct GPIO manipulation for high-frequency polling of the Hall-effect sensor and Load Cell.
    * Execution of rehabilitation algorithms (filtering, physics calculations, etc.) with deterministic timing.
* **Why C?** Provides "close-to-metal" performance, ensuring minimal jutter in sensor readings and low-overhead processing. 
* **Output**: Updates a thread-safe struct in `Shared Memory` with the current system state (pedal positions, forces, metrics, etc.).

### 2. The Visual Frontend (Python)
* **Role**: Handles the `Simulation Engine` and User Interface.
* **Responsibilities**:
    * Renders the driving simulation and biofeedback graphs to the HDMI display.
    * Manages user sessions and high-level application flow.
* **Why Python?** Enables rapid development of complex graphics using hardware-accelerated libraries like `Pygame` without the complex memory management of C.
* **Input**: Reads the Latest state from `Shared Memory` asynchronously to render frames at ~60 FPS, independent of the sensor polling rate.