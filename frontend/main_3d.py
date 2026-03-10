from ursina import *
import random
import time

app = Ursina()

# Window & Camera Settings
window.title = "Back2Driving - Clinical 3D Simulator (2026)"
window.borderless = False
window.fullscreen = False
window.exit_button.visible = False
window.fps_counter.enabled = True
camera.fov = 60 

# Colors
ASPHALT = color.rgb(40, 40, 40)
GRASS = color.rgb(34, 139, 34)

# Assets
crash_sound = Audio('crash.wav', autoplay=False, loop=False)

# -----------------
# Environment Classes
# -----------------

class RoadManager:
    def __init__(self):
        # Endless Road
        self.road = Entity(model='plane', scale=(12, 1, 1000), color=ASPHALT, z=450)
        self.grass_l = Entity(model='plane', scale=(100, 1, 1000), color=GRASS, x=-56, z=450)
        self.grass_r = Entity(model='plane', scale=(100, 1, 1000), color=GRASS, x=56, z=450)
        self.lines = [Entity(model='cube', scale=(0.2, 0.05, 3), color=color.white, x=0, z=i*10, y=0.01) for i in range(100)]
        
        # Trees
        self.trees = []
        for i in range(60):
            tx = random.choice([-15, 15]) + random.uniform(-2, 2)
            tz = random.uniform(20, 800)
            t = Entity(model='cube', scale=(1, 5, 1), color=color.rgb(101, 67, 33), position=(tx, 2.5, tz))
            Entity(parent=t, model='sphere', scale=(4, 2, 4), color=color.rgb(0, 100, 0), y=0.8)
            self.trees.append(t)

    def update(self, speed, dt):
        # Move lines
        for line in self.lines:
            line.z -= speed * dt
            if line.z < -20: line.z += 1000
        # Move trees
        for tree in self.trees:
            tree.z -= speed * dt
            if tree.z < -20:
                tree.z += 800
                tree.x = random.choice([-15, 15]) + random.uniform(-3, 3)

# -----------------
# Hazard Entities (Class-Based)
# -----------------

class RealisticHouse(Entity):
    def __init__(self, side, **kwargs):
        super().__init__(**kwargs)
        self.x = -16 if side == 'left' else 16
        # Structure
        Entity(parent=self, model='cube', scale=(10, 6, 8), position=(0, 3, 0), color=color.rgb(220, 200, 180))
        Entity(parent=self, model='cube', scale=(6, 4, 6), position=(-2, 8, -1), color=color.rgb(210, 190, 170))
        # Roofs
        Entity(parent=self, model='cone', scale=(13, 3, 11), position=(0, 6, 0), color=color.rgb(110, 30, 30))
        Entity(parent=self, model='cone', scale=(8, 2, 8), position=(-2, 10, -1), color=color.rgb(110, 30, 30))
        # Details
        Entity(parent=self, model='cube', scale=(0.15, 0.4, 0.05), position=(0, -0.4, 0.51), color=color.brown) # Door

class WomanPedestrian(Entity):
    def __init__(self, **kwargs):
        super().__init__(model=None, **kwargs)
        skin = color.rgb(255, 200, 150)
        dress = color.rgb(200, 50, 50)
        hair = color.rgb(45, 25, 15)

        # Torso (Shirt)
        self.torso = Entity(parent=self, model='cube', scale=(0.7, 0.8, 0.4), position=(0, 1.4, 0), color=color.white)
        # Skirt (Cone base)
        self.skirt = Entity(parent=self, model='cone', scale=(1, 1.1, 1), position=(0, 0.65, 0), color=dress)
        
        # Neck
        Entity(parent=self, model='cube', scale=(0.15, 0.2, 0.15), position=(0, 1.85, 0), color=skin)
        
        # Head
        self.head_box = Entity(parent=self, model='cube', scale=(0.55, 0.55, 0.5), position=(0, 2.2, 0), color=skin)
        
        # Face Features
        Entity(parent=self.head_box, model='cube', scale=(0.08, 0.08, 0.08), position=(-0.15, 0.1, 0.26), color=color.black) # Left Eye
        Entity(parent=self.head_box, model='cube', scale=(0.08, 0.08, 0.08), position=(0.15, 0.1, 0.26), color=color.black) # Right Eye
        Entity(parent=self.head_box, model='cube', scale=(0.15, 0.04, 0.05), position=(0, -0.15, 0.26), color=color.rgb(200, 100, 100)) # Mouth
        
        # Hair (Multi-part for realistic shape)
        Entity(parent=self.head_box, model='cube', scale=(0.65, 0.2, 0.6), position=(0, 0.3, 0), color=hair) # Top
        Entity(parent=self.head_box, model='cube', scale=(0.65, 0.7, 0.25), position=(0, -0.1, -0.2), color=hair) # Back
        Entity(parent=self.head_box, model='cube', scale=(0.15, 0.7, 0.6), position=(-0.3, -0.1, 0), color=hair) # Side L
        Entity(parent=self.head_box, model='cube', scale=(0.15, 0.7, 0.6), position=(0.3, -0.1, 0), color=hair) # Side R

        # Arms
        self.arm_l = Entity(parent=self, model='cube', scale=(0.2, 0.8, 0.2), position=(-0.45, 1.4, 0), color=skin)
        self.arm_r = Entity(parent=self, model='cube', scale=(0.2, 0.8, 0.2), position=(0.45, 1.4, 0), color=skin)
        
        # Legs/Shoes
        self.shoe_l = Entity(parent=self, model='cube', scale=(0.25, 0.3, 0.3), position=(-0.2, 0.15, 0), color=color.black)
        self.shoe_r = Entity(parent=self, model='cube', scale=(0.25, 0.3, 0.3), position=(0.2, 0.15, 0), color=color.black)

class Football(Entity):
    def __init__(self, **kwargs):
        super().__init__(model='sphere', scale=1.2, color=color.white, collider='sphere', **kwargs)
        # Hex patterns
        for i in range(12):
            p = Entity(parent=self, model='sphere', scale=0.4, color=color.black)
            phi, theta = random.uniform(0, 3.14), random.uniform(0, 6.28)
            p.position = (math.sin(phi)*math.cos(theta)*0.5, math.sin(phi)*math.sin(theta)*0.5, math.cos(phi)*0.5)

# -----------------
# Main Car Physics
# -----------------

class SimulatorCar(Entity):
    def __init__(self):
        super().__init__(model='cube', color=color.rgb(30, 144, 255), scale=(2.4, 0.8, 5), position=(0, 0.6, 0), collider='box')
        self.cabin = Entity(parent=self, model='cube', scale=(0.85, 0.6, 0.5), position=(0, 0.8, -0.05), color=color.rgb(30, 144, 255))
        Entity(parent=self.cabin, model='cube', scale=(0.95, 0.8, 0.4), position=(0, 0, 0.1), color=color.rgb(20, 20, 20)) 
        
        self.brake_lights = [
            Entity(parent=self, model='cube', scale=(0.35, 0.2, 0.1), position=(-0.35, 0, -0.51), color=color.rgb(100,0,0)),
            Entity(parent=self, model='cube', scale=(0.35, 0.2, 0.1), position=(0.35, 0, -0.51), color=color.rgb(100,0,0))
        ]
        
        self.speed = 0.0
        self.max_speed = 35.0
        self.accel = 12.0
        self.brake_power = 45.0
        self.drag = 3.0
        self.idle_creep = 1.5

    def update_physics(self, gas, brake, dt):
        if brake:
            self.speed -= self.brake_power * dt
            for bl in self.brake_lights: bl.color = color.red
        elif gas:
            self.speed += self.accel * dt
            for bl in self.brake_lights: bl.color = color.rgb(100,0,0)
        else:
            # Creep Forward logic
            if self.speed < self.idle_creep: self.speed += 2.0 * dt
            else: self.speed -= self.drag * dt
            for bl in self.brake_lights: bl.color = color.rgb(100,0,0)
            
        self.speed = clamp(self.speed, 0, self.max_speed)

# -----------------
# Global State & HUD
# -----------------

road_manager = RoadManager()
car = SimulatorCar()

hud_bg = Entity(parent=camera.ui, model='quad', scale=(0.4, 0.35), position=(-0.65, 0.3), color=color.rgba(10, 20, 30, 220))
speed_text = Text(parent=hud_bg, text="0 KM/H", position=(-0.45, 0.2), scale=4)
status_text = Text(parent=hud_bg, text="STATUS: NOMINAL", position=(-0.45, -0.05), scale=2, color=color.green)
reaction_text = Text(parent=hud_bg, text="-- ms", position=(-0.05, -0.25), scale=2)

active_hazard = None
hazard_timer = time.time() + 3.0
reaction_start = 0

def spawn_hazard():
    global active_hazard, reaction_start
    htype = random.choice(['ball', 'stop_sign', 'traffic_light'])
    
    # Scene Container
    scene = Entity(model=None, position=(0, 0, 250))
    scene.hazard_type = htype
    scene.triggered = False
    scene.is_cleared = False
    
    if htype == 'ball':
        side = random.choice(['left', 'right'])
        scene.house = RealisticHouse(side=side, parent=scene)
        scene.ball = Football(parent=scene, position=(-10 if side == 'left' else 10, 0.6, 0))
        scene.anim_speed = 5.5 if side == 'left' else -5.5
        
    elif htype == 'stop_sign':
        # Crosswalk
        for i in range(-5, 6, 2): Entity(parent=scene, model='plane', scale=(1, 1, 6), color=color.white, position=(i, 0.02, 0))
        # Sign
        sign = Entity(parent=scene, model='cube', color=color.red, scale=(1.5, 1.5, 0.1), position=(4, 2.5, 0))
        Text(parent=sign, text="STOP", scale=10, position=(-0.4, 0.4, -0.6), color=color.white)
        Entity(parent=sign, model='cube', color=color.gray, scale=(0.2, 6, 0.2), position=(0, -2, 0))
        
        scene.pedestrian = WomanPedestrian(parent=scene, position=(-12, 0, 0))
        scene.anim_speed = 4.2

    elif htype == 'traffic_light':
        for i in range(-5, 6, 2): Entity(parent=scene, model='plane', scale=(1, 1, 6), color=color.white, position=(i, 0.02, 0))
        # Frame
        frame = Entity(parent=scene, model='cube', color=color.black, scale=(1, 2.5, 0.6), position=(4, 3.5, 0))
        Entity(parent=frame, model='cube', color=color.gray, scale=(0.2, 6, 0.2), position=(0, -1.5, 0))
        scene.red_l = Entity(parent=frame, model='sphere', scale=(0.6, 0.3, 0.6), position=(0, 0.3, -0.4), color=color.red)
        scene.green_l = Entity(parent=frame, model='sphere', scale=(0.6, 0.3, 0.6), position=(0, -0.3, -0.4), color=color.rgb(0, 50, 0))
        
        scene.light_state = 'RED'
        scene.wait_timer = 0
        scene.timer_on = False
        scene.pedestrian = WomanPedestrian(parent=scene, position=(-12, 0, 0))
        scene.anim_speed = 4.5

    active_hazard = scene
    reaction_start = 0
    status_text.text = f"HAZARD: {htype.upper()}!"
    status_text.color = color.orange

def update():
    global active_hazard, hazard_timer, reaction_start

    gas = held_keys['up arrow'] or held_keys['w']
    brake = held_keys['down arrow'] or held_keys['s']
    dt = time.dt

    car.update_physics(gas, brake, dt)
    road_manager.update(car.speed, dt)
    
    speed_text.text = f"{int(car.speed * 3.6)} KM/H"

    if active_hazard:
        active_hazard.z -= car.speed * dt
        
        # -----------------
        # LATER CROSSING (trigger_dist = 40)
        # -----------------
        if active_hazard.hazard_type == 'ball':
            if active_hazard.z < 50:
                if not active_hazard.triggered:
                    active_hazard.triggered = True
                    reaction_start = time.time()
                active_hazard.ball.x += active_hazard.anim_speed * dt
                active_hazard.ball.rotation_z -= 400 * dt
                
        elif active_hazard.hazard_type in ['stop_sign', 'traffic_light']:
            # Woman crosses LATER (at distance 35)
            if active_hazard.z < 35:
                if not active_hazard.triggered:
                    active_hazard.triggered = True
                    reaction_start = time.time()
                active_hazard.pedestrian.x += active_hazard.anim_speed * dt
            
            # Traffic Light Hold Logic
            if active_hazard.hazard_type == 'traffic_light':
                if active_hazard.z < 20 and car.speed < 2.0 and not active_hazard.timer_on:
                    active_hazard.wait_timer = time.time()
                    active_hazard.timer_on = True
                    status_text.text = "HOLD BRAKE FOR GREEN..."
                
                if active_hazard.timer_on and active_hazard.light_state == 'RED':
                    if not brake: # Penalty for releasing brake
                        active_hazard.wait_timer = time.time()
                        status_text.text = "BRAKE RELEASED! RESET"
                        status_text.color = color.red
                    
                    if time.time() - active_hazard.wait_timer > 5.0:
                        active_hazard.light_state = 'GREEN'
                        active_hazard.red_l.color = color.rgb(50, 0, 0)
                        active_hazard.green_l.color = color.green
                        status_text.text = "LIGHT IS GREEN"
                        status_text.color = color.green

        # Reaction Timing
        if brake and not active_hazard.is_cleared and reaction_start > 0:
            ms = int((time.time() - reaction_start) * 1000)
            reaction_text.text = f"{ms} ms"
            reaction_text.color = color.green if ms < 600 else color.yellow
            active_hazard.is_cleared = True

        # Collision Check
        collision = False
        if active_hazard.hazard_type == 'ball':
            if distance(car, active_hazard.ball.world_position) < 3.5: collision = True
        elif hasattr(active_hazard, 'pedestrian'):
            if distance(car, active_hazard.pedestrian.world_position) < 3.5: collision = True
            
        if collision:
            status_text.text = "COLLISION!"
            status_text.color = color.red
            car.speed = 0
            if not crash_sound.playing: crash_sound.play()

        # Cleanup
        if active_hazard.z < -20:
            destroy(active_hazard)
            active_hazard = None
            hazard_timer = time.time() + random.uniform(3, 5)
            status_text.text = "STATUS: NOMINAL"
            status_text.color = color.green
    else:
        if time.time() > hazard_timer and car.speed > 15: spawn_hazard()

    # Camera Follow
    camera.position = lerp(camera.position, (0, 7.5, -22 - (car.speed * 0.15)), dt * 2)
    camera.look_at(car.position + Vec3(0, 0, 40))

if __name__ == '__main__':
    app.run()
