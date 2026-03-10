# Rhythm Drive: Driving Rehabilitation Rhythm Game

**Rhythm Drive** is a specialized Pygame-based rhythm application designed for physical therapy and driving rehabilitation. Unlike traditional rhythm games that prioritize high-speed finger dexterity, Rhythm Drive focuses on lower-limb coordination, leg endurance, and reaction precision using foot pedals.

## 1. Game Overview & Rehabilitation Goal
The primary objective of Rhythm Drive is to bridge the gap between repetitive physical therapy exercises and functional driving skills. 

### Clinical Objectives:
*   **Lower Limb Strength & Endurance:** Utilizing "Hold" notes to simulate sustained pressure on gas or brake pedals (e.g., maintaining speed or waiting at a light).
*   **Reaction Time (RT):** Measuring the latency between visual stimuli (notes) and physical engagement (pedal press).
*   **Inhibitory Control:** Training the patient to differentiate between "Go" (Gas/Up) and "Stop" (Brake/Down) cues under rhythmic pressure.
*   **Proprioception:** Improving the patient's ability to locate and toggle between pedals without looking at their feet.

---

## 2. Core Mechanics

### Audio Synchronization & JSON Beatmaps
To ensure frame-independent precision, the game uses a **Time-Based Sync** system. The position of notes is calculated based on the current millisecond of the music track rather than frame counts.

**Beatmap Structure (`song_name.json`):**
```json
{
  "song_metadata": { "title": "Firework", "bpm": 124, "offset": 150 },
  "notes": [
    { "time": 1200, "type": "tap", "lane": "gas" },
    { "time": 2400, "type": "hold", "lane": "brake", "duration": 3000 },
    { "time": 5800, "type": "tap", "lane": "gas" }
  ]
}
```

### Note Types
*   **Tap Notes:** Single rhythmic hits synced to the beat.
*   **Hold Notes:** Requires the player to depress the pedal at the start and maintain pressure until the end of the note. This simulates the isometric muscle contraction required during actual driving.

### Lane Mapping
*   **Gas (Blue / Up Arrow):** Represents acceleration.
*   **Brake (Red / Down Arrow):** Represents deceleration/stopping.
*   *Note:* The game interprets Up/Down arrow keys, allowing compatibility with standard digital foot pedals.

---

## 3. Hit System & Analytics

### Precision Windows
The game calculates the difference ($\Delta t$) between the `note.time` and the `event.time` of the user input:
*   **Perfect:** $\pm$ 50ms
*   **Good:** $\pm$ 150ms
*   **Miss:** > 150ms or wrong lane.

### Data Logging (PT Assessment)
Every session generates a `session_report_[TIMESTAMP].csv` to allow therapists to track progress over time.

**Exported Metrics:**
*   **Timestamp:** Exact time of the event.
*   **Reaction Latency:** The $\Delta t$ in milliseconds (identifies if the patient is consistently "early" or "late").
*   **Hold Continuity:** Percentage of a hold note successfully maintained (measures leg tremors or fatigue).
*   **Accuracy Ratio:** Percentage of Gas vs. Brake errors.

---

## 4. UI/UX Features
*   **Scrolling Highway:** A 2D perspective-scrolling background that accelerates/decelerates based on performance to simulate the feeling of forward motion.
*   **Visual Feedback Popups:** "PERFECT", "GOOD", or "MISS" text rendered at the hit zone with a slight fade-out animation.
*   **Combo Tracker:** Encourages "Flow State" by tracking consecutive successful hits.
*   **Health/Stability Bar:** If too many notes are missed, the "Vehicle Stability" drops, providing a clear visual cue of performance.

---

## 5. Development Plan

### Phase 1: Engine Foundation
*   Initialize Pygame window and basic game loop.
*   Implement a `Clock` system using `get_ticks()` for millisecond precision.
*   Create the `Note` and `Lane` class structures.

### Phase 2: Audio & Sync
*   Implement the JSON parser to load song data.
*   Develop the "Note Spawner" that calculates screen position based on `(note_time - current_audio_time) * scroll_speed`.

### Phase 3: Input & Collision Logic
*   Map Up/Down arrows to the hit detection logic.
*   Implement "Hold" note logic (detecting `KEYUP` events before the note duration ends).

### Phase 4: UI & Polish
*   Add the scrolling highway background.
*   Create the hit animation system and combo counter.
*   Integrate audio visualizers or progress bars.

### Phase 5: Analytics Integration
*   Build the `Logger` module to capture real-time hit data.
*   Implement the CSV export functionality on game exit or song completion.
