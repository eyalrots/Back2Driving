import pygame
import json
import time
import os
import csv
import math
import sys

# Add parent directory to path to import access_shared
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from access_shared import SensorSharedMemory
    HAS_SENSOR = True
except ImportError as e:
    SensorSharedMemory = None
    HAS_SENSOR = False
    print(f"Warning: Shared memory is not available. Falling back to keyboard. ({e})")

# --- Configuration & Constants ---
# ... (rest of imports and constants)
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (5, 5, 10)
ASPHALT = (30, 30, 35)
LANE_MARKER = (200, 200, 200)
BLUE = (0, 180, 255)    # Gas
RED = (255, 60, 100)    # Brake
GREEN = (0, 255, 150)
GOLD = (255, 215, 0)

# Game Settings
SCROLL_SPEED = 0.5      
HIT_Y = 520             
LANE_WIDTH_BOTTOM = 180 # Wider at bottom for perspective
LANE_WIDTH_TOP = 40     # Narrower at top
VANISHING_POINT_Y = 100 # Where the road "meets"

# Hit Windows (ms)
PERFECT_WINDOW = 60     
GOOD_WINDOW = 160
GRACE_PERIOD = 150      

# --- Asset Paths ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.dirname(CURRENT_DIR)

BEATMAP_PATH = os.path.join(CURRENT_DIR, "beatmap.json")
# Music is in the 'audio' folder, which is a sibling to the 'rhythm_drive' folder
MUSIC_PATH = os.path.join(FRONTEND_DIR, "audio", "Katy Perry_Firework.mp3")

def get_x_for_lane(y, lane_type):
    """Calculates X position based on Y for perspective road."""
    # Linear interpolation of lane width based on Y
    rel_y = (y - VANISHING_POINT_Y) / (SCREEN_HEIGHT - VANISHING_POINT_Y)
    current_lane_width = LANE_WIDTH_TOP + (LANE_WIDTH_BOTTOM - LANE_WIDTH_TOP) * rel_y
    
    center_x = SCREEN_WIDTH // 2
    if lane_type == 1: # Gas (Left)
        return center_x - current_lane_width
    else: # Brake (Right)
        return center_x

def get_width_for_y(y):
    rel_y = (y - VANISHING_POINT_Y) / (SCREEN_HEIGHT - VANISHING_POINT_Y)
    return LANE_WIDTH_TOP + (LANE_WIDTH_BOTTOM - LANE_WIDTH_TOP) * rel_y

class Note:
    def __init__(self, target_time, note_type, duration):
        self.target_time = target_time * 1000  
        self.type = note_type                  # 1: Gas, -1: Brake
        self.duration = duration * 1000        
        self.hit = False
        self.missed = False
        
        self.is_holding = False
        self.hold_completed = False
        self.release_time = 0                  
        
        self.y = -1000 
        self.color = BLUE if self.type == 1 else RED

    def update_position(self, current_time):
        # Normal scroll
        self.y = HIT_Y - (self.target_time - current_time) * SCROLL_SPEED
        self.tail_end_y = HIT_Y - (self.target_time + self.duration - current_time) * SCROLL_SPEED

    def draw(self, screen):
        if self.missed: return
        
        # Determine current drawing points
        head_y = self.y
        tail_top_y = self.tail_end_y
        
        # Sticky Logic: If holding, head stays at HIT_Y until the tail passes it
        if self.is_holding:
            head_y = HIT_Y
            # Tail shouldn't go past HIT_Y
            if tail_top_y > HIT_Y: tail_top_y = HIT_Y

        # Don't draw if completely off-screen top or bottom
        if head_y < VANISHING_POINT_Y and tail_top_y < VANISHING_POINT_Y: return
        if tail_top_y > SCREEN_HEIGHT: return

        # Drawing the Tail (The Hold Path)
        if self.duration > 0:
            points = []
            # Generate a few points along the tail for perspective curvature (simple linear for now)
            # Top of tail
            w_top = get_width_for_y(tail_top_y) * 0.8
            x_top = get_x_for_lane(tail_top_y, self.type) + 5
            # Bottom of tail (at head)
            w_bot = get_width_for_y(head_y) * 0.8
            x_bot = get_x_for_lane(head_y, self.type) + 5
            
            # Draw tail as a polygon for perspective
            poly_points = [
                (x_top, tail_top_y), 
                (x_top + w_top, tail_top_y),
                (x_bot + w_bot, head_y),
                (x_bot, head_y)
            ]
            alpha = 220 if self.is_holding else 120
            tail_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.polygon(tail_surface, (*self.color, alpha), poly_points)
            screen.blit(tail_surface, (0,0))

        # Drawing the Note Head
        if not self.hold_completed:
            curr_w = get_width_for_y(head_y) * 0.8
            curr_x = get_x_for_lane(head_y, self.type) + 5
            
            # Note "Body"
            rect_h = 20 * (head_y / HIT_Y) # Scale height slightly with perspective
            if self.is_holding:
                # Glow effect
                for i in range(3):
                    pygame.draw.rect(screen, WHITE, (curr_x-i, head_y-10-i, curr_w+i*2, rect_h+i*2), border_radius=6, width=1)
            
            pygame.draw.rect(screen, self.color, (curr_x, head_y - rect_h//2, curr_w, rect_h), border_radius=6)
            pygame.draw.rect(screen, WHITE, (curr_x + 10, head_y - 2, curr_w - 20, 4), border_radius=2)

class Popup:
    def __init__(self, text, x, y, color):
        self.text = text
        self.x = x
        self.y = y
        self.color = color
        self.life = 1.0
        self.start_time = time.time()

    def update(self):
        elapsed = time.time() - self.start_time
        self.life = 1.0 - (elapsed / 0.6)
        self.y -= 1.5

    def draw(self, screen, font):
        if self.life > 0:
            alpha = int(255 * self.life)
            text_surf = font.render(self.text, True, self.color)
            text_surf.set_alpha(alpha)
            screen.blit(text_surf, (self.x - text_surf.get_width()//2, self.y))

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Rhythm Drive: Musical rehab")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Verdana", 24, bold=True)
        self.large_font = pygame.font.SysFont("Verdana", 50, bold=True)
        
        self.last_input_state = {"gas": False, "brake": False}
        self.gas_value = 0.0
        self.brake_value = 0.0
        self.sensor_shm = None

        if HAS_SENSOR:
            try:
                self.sensor_shm = SensorSharedMemory(path="/home", project_id='R')
                self.sensor_shm.connect()
                print("Rhythm: Connected to Hardware via Shared Memory.")
            except Exception as e:
                print(f"Rhythm: Hardware connection failed: {e}")
                self.sensor_shm = None
        else:
            print("Rhythm: Running with keyboard fallback only.")
        
        self.load_assets()
        self.reset_game()

    def load_assets(self):
        try:
            with open(BEATMAP_PATH, "r") as f:
                data = json.load(f)
                self.notes = [Note(n['time'], n['type'], n.get('duration', 0)) for n in data]
        except: self.notes = []
        if os.path.exists(MUSIC_PATH): pygame.mixer.music.load(MUSIC_PATH)

    def reset_game(self):
        self.start_ticks = 0
        self.running = True
        self.score = 0
        self.combo = 0
        self.popups = []
        self.music_started = False
        self.road_offset = 0

    def handle_input(self):
        current_time = pygame.time.get_ticks() - self.start_ticks if self.music_started else 0

        # 1. Collect input states: Hardware samples + Keyboard fallback

        keys = pygame.key.get_pressed()
        keyboard_gas = keys[pygame.K_UP]
        keyboard_brake = keys[pygame.K_DOWN]

        # Default values from keyboard
        self.gas_value = 1.0 if keyboard_gas else 0.0
        self.brake_value = 1.0 if keyboard_brake else 0.0

        # Temporary calibration values
        GAS_MIN = 2122
        GAS_MAX = 3200
        BRAKE_MIN = 0
        BRAKE_MAX = 8388608

        GAS_THRESHOLD = 0.15
        BRAKE_THRESHOLD = 0.15

        def normalize_sensor(raw_value, min_value, max_value):
            if max_value == min_value:
                return 0.0

            value = (raw_value - min_value) / (max_value - min_value)
            return max(0.0, min(1.0, value))

        # Hardware polling from Shared Memory
        if self.sensor_shm:
            try:
                data = self.sensor_shm.read_data()

                # load_cell  -> brake force
                # hall_effect -> gas pedal position
                raw_brake = data["load_cell"]["sample"]
                raw_gas = data["hall_effect"]["sample"]

                self.gas_value = normalize_sensor(raw_gas, GAS_MIN, GAS_MAX)
                self.brake_value = normalize_sensor(raw_brake, BRAKE_MIN, BRAKE_MAX)

                # Keyboard still overrides hardware for testing
                # if keyboard_gas:
                #     self.gas_value = 1.0
                # if keyboard_brake:
                #     self.brake_value = 1.0

            except Exception as e:
                print(f"Sensor read error: {e}")

        gas_pressed = self.gas_value > GAS_THRESHOLD
        brake_pressed = self.brake_value > BRAKE_THRESHOLD

        # 2. Edge Detection for rhythm hits

        if gas_pressed and not self.last_input_state["gas"]:
            self.check_hit(current_time, 1)

        if brake_pressed and not self.last_input_state["brake"]:
            self.check_hit(current_time, -1)

        self.last_input_state = {"gas": gas_pressed, "brake": brake_pressed}

        # 3. Handle system events

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

    def check_hit(self, current_time, input_type):
        if not self.music_started: return
        
        # Re-catch logic for hold notes
        active_holds = [n for n in self.notes if n.hit and not n.hold_completed and n.type == input_type and n.duration > 0]
        if active_holds:
            if not active_holds[0].is_holding:
                active_holds[0].is_holding = True
                return

        potential = [n for n in self.notes if not n.hit and not n.missed and n.type == input_type]
        if not potential: return

        note = min(potential, key=lambda n: abs(n.target_time - current_time))
        delta = current_time - note.target_time
        abs_delta = abs(delta)

        if abs_delta <= GOOD_WINDOW:
            note.hit = True
            rating = "PERFECT!" if abs_delta <= PERFECT_WINDOW else "GOOD"
            color = GOLD if abs_delta <= PERFECT_WINDOW else GREEN
            self.score += 100
            self.combo += 1
            self.popups.append(Popup(rating, get_x_for_lane(HIT_Y, note.type) + get_width_for_y(HIT_Y)//2, HIT_Y - 40, color))
            if note.duration > 0: note.is_holding = True
        elif delta < 0 and abs_delta < 400:
            self.trigger_miss(note, "EARLY")

    def trigger_miss(self, note, reason="MISS"):
        note.missed = True
        self.combo = 0
        self.popups.append(Popup(reason, get_x_for_lane(HIT_Y, note.type) + get_width_for_y(HIT_Y)//2, HIT_Y - 40, RED))

    def update(self):
        current_time = pygame.time.get_ticks() - self.start_ticks if self.music_started else 0
        
        # Current input state for hold logic
        gas_now = self.last_input_state["gas"]
        brake_now = self.last_input_state["brake"]

        for note in self.notes:
            note.update_position(current_time)
            if not self.music_started: continue

            if not note.hit and not note.missed and (current_time - note.target_time) > GOOD_WINDOW:
                self.trigger_miss(note)

            if note.hit and note.duration > 0 and not note.hold_completed:
                # Use consolidated input state
                pedal_down = gas_now if note.type == 1 else brake_now
                
                if pedal_down:
                    note.is_holding = True
                    note.release_time = 0
                    self.score += 2
                else:
                    if note.is_holding:
                        note.is_holding = False
                        note.release_time = current_time
                    if note.release_time != 0 and (current_time - note.release_time) > GRACE_PERIOD:
                        note.hold_completed = True
                        self.combo = 0
                        self.popups.append(Popup("DROPPED", get_x_for_lane(HIT_Y, note.type) + 50, HIT_Y-80, RED))

                if current_time >= note.target_time + note.duration:
                    note.is_holding = False
                    note.hold_completed = True
                    self.score += 500
                    self.popups.append(Popup("FINISH!", get_x_for_lane(HIT_Y, note.type) + 50, HIT_Y-80, GOLD))

        for p in self.popups[:]:
            p.update()
            if p.life <= 0: self.popups.remove(p)
        
        if self.music_started:
            self.road_offset = (self.road_offset + 12) % 100
            if not pygame.mixer.music.get_busy() and current_time > 3000: self.running = False

    def draw(self):
        self.screen.fill(BLACK)
        
        # Perspective Road
        center_x = SCREEN_WIDTH // 2
        road_poly = [
            (center_x - LANE_WIDTH_TOP, VANISHING_POINT_Y),
            (center_x + LANE_WIDTH_TOP, VANISHING_POINT_Y),
            (center_x + LANE_WIDTH_BOTTOM, SCREEN_HEIGHT),
            (center_x - LANE_WIDTH_BOTTOM, SCREEN_HEIGHT)
        ]
        pygame.draw.polygon(self.screen, ASPHALT, road_poly)
        
        # Center Line (Perspective)
        pygame.draw.line(self.screen, WHITE, (center_x, VANISHING_POINT_Y), (center_x, SCREEN_HEIGHT), 2)
        
        # Moving Side Markers
        for i in range(10):
            # Logarithmic spacing for perspective
            y = VANISHING_POINT_Y + ((i * 100 + self.road_offset) % 600) * ((SCREEN_HEIGHT - VANISHING_POINT_Y) / 600)
            if y > VANISHING_POINT_Y:
                w = get_width_for_y(y)
                lx = center_x - w
                rx = center_x + w
                marker_w = 4 * (y / SCREEN_HEIGHT)
                pygame.draw.circle(self.screen, LANE_MARKER, (int(lx), int(y)), int(marker_w + 1))
                pygame.draw.circle(self.screen, LANE_MARKER, (int(rx), int(y)), int(marker_w + 1))

        # Hit Line (Perspective)
        hw = get_width_for_y(HIT_Y)
        pygame.draw.line(self.screen, (100, 100, 110), (center_x - hw, HIT_Y), (center_x + hw, HIT_Y), 4)

        # Draw Notes
        for note in sorted(self.notes, key=lambda n: n.target_time, reverse=True):
            note.draw(self.screen)

        # UI
        score_surf = self.font.render(f"SCORE: {self.score:06}", True, WHITE)
        self.screen.blit(score_surf, (30, 30))
        if self.combo > 0:
            combo_surf = self.large_font.render(f"{self.combo}", True, GOLD if self.combo > 10 else WHITE)
            self.screen.blit(combo_surf, (SCREEN_WIDTH - 120, 30))

        for p in self.popups: p.draw(self.screen, self.font)

        if not self.music_started:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            self.screen.blit(overlay, (0,0))
            txt = self.large_font.render("RHYTHM DRIVE", True, GOLD)
            sub = self.font.render("Press Gas (UP) or Brake (DOWN) to Start", True, WHITE)
            self.screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, SCREEN_HEIGHT//2 - 40))
            self.screen.blit(sub, (SCREEN_WIDTH//2 - sub.get_width()//2, SCREEN_HEIGHT//2 + 30))

        pygame.display.flip()

    def run(self):
        while self.running:
            self.handle_input()
            hardware_start = self.last_input_state["gas"] or self.last_input_state["brake"]
            if not self.music_started and hardware_start:
                pygame.mixer.music.play(); self.start_ticks = pygame.time.get_ticks(); self.music_started = True
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        # Cleanup before quit
        if hasattr(self, 'sensor_shm') and self.sensor_shm:
            self.sensor_shm.detach()
            print("Rhythm: Detached from Shared Memory.")
            
        pygame.quit()

if __name__ == "__main__":
    Game().run()
