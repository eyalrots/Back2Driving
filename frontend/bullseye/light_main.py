import sys
import random
import time
import os
import subprocess
from datetime import datetime
import pygame
from PyQt6.QtWidgets import (QApplication, QMainWindow, QStackedWidget, QWidget, 
                             QVBoxLayout, QLabel, QGraphicsView, QGraphicsScene, 
                             QGraphicsRectItem, QGraphicsTextItem, QGraphicsItemGroup)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QPen, QPainter, QFont

# --- PATH CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR)) 

try:
    from access_shared import SensorSharedMemory
    HAS_SENSOR = True
except ImportError as e:
    SensorSharedMemory = None
    HAS_SENSOR = False
    print(f"Warning: Shared memory is not available. ({e})")

# --- CONSTANTS & CONFIG ---
WIDTH = 1066 
HEIGHT = 600
GAME_DURATION = 180 
FRICTION = 0.15 

MIN_BRAKE = 40000
MAX_BRAKE = 215000
MIN_GAS = 2600
MAX_GAS_BASE = 3500 

DIFFICULTY_SETTINGS = {
    "Easy": {"MAX_SPEED": 10.0, "BRAKE_FORCE": 1.1, "ACCEL": 0.18, "SPAWN_DIST": (-2000, -1400)},
    "Medium": {"MAX_SPEED": 14.0, "BRAKE_FORCE": 0.8, "ACCEL": 0.22, "SPAWN_DIST": (-1700, -1100)},
    "Hard": {"MAX_SPEED": 19.0, "BRAKE_FORCE": 0.55, "ACCEL": 0.28, "SPAWN_DIST": (-1400, -800)}
}

GLOBAL_STYLESHEET = """
QWidget {
    font-family: "Segoe UI", Arial, sans-serif;
    background-color: #121215;
}
QLabel {
    color: #E0E0E0;
    letter-spacing: 2px;
}
"""

# --- AUDIO SETUP ---
try:
    pygame.mixer.init()
except Exception:
    pass

SUCCESS_SOUNDS = ['assets/good_job_1.mpeg', 'assets/good_job_2.mpeg', 'assets/nice_one.mpeg', 'assets/great_job.mpeg', 'assets/great_succ.mpeg']
FAIL_SOUNDS = ['assets/fail.mpeg', 'assets/you_missed_that_one.mp3']
GAMEOVER_SOUND = 'assets/game_over.mpeg'

def play_sound(sound_list_or_path):
    try:
        path = random.choice(sound_list_or_path) if isinstance(sound_list_or_path, list) else sound_list_or_path
        pygame.mixer.Sound(path).play()
    except:
        pass

# --- GAME ENTITIES ---
class MultiTarget(QGraphicsItemGroup):
    def __init__(self, y_pos, x_offset=0):
        super().__init__()
        
        self.outer = QGraphicsRectItem(0, 0, 200, 240)
        self.outer.setBrush(QBrush(QColor(70, 20, 20))) 
        self.outer.setPen(QPen(QColor(255, 60, 60), 2, Qt.PenStyle.DashLine))
        
        self.middle = QGraphicsRectItem(10, 60, 180, 120)
        self.middle.setBrush(QBrush(QColor(80, 60, 15))) 
        self.middle.setPen(QPen(QColor(255, 200, 50), 2, Qt.PenStyle.DotLine))
        
        self.inner = QGraphicsRectItem(20, 100, 160, 40)
        self.inner.setBrush(QBrush(QColor(15, 70, 30))) 
        self.inner.setPen(QPen(QColor(50, 255, 100), 3, Qt.PenStyle.SolidLine))
        
        self.addToGroup(self.outer)
        self.addToGroup(self.middle)
        self.addToGroup(self.inner)
        self.setPos((WIDTH // 2) - 100 + x_offset, y_pos)
        self.scored = False

    def check_score(self, car_rect):
        ty = car_rect.top()
        ly = ty - self.y()
        if 100 <= ly <= 140: return 5, "BULLSEYE! +5", "#32FF64"
        elif 60 <= ly <= 180: return 3, "GOOD STOP! +3", "#FFC832"
        elif 0 <= ly <= 240: return 1, "OKAY +1", "#FFFFFF"
        return 0, "MISSED", "#FF3C3C"

class QuickTarget(QGraphicsItemGroup):
    def __init__(self, y_pos, x_offset=0):
        super().__init__()
        tiers = [(60, 5, "EASY"), (30, 10, "MEDIUM"), (12, 15, "HARD")]
        self.h, self.pts, self.tier_name = random.choice(tiers)
        
        self.box = QGraphicsRectItem(40, 120 - self.h/2, 120, self.h)
        self.box.setBrush(QBrush(QColor(0, 60, 60))) 
        self.box.setPen(QPen(QColor(0, 255, 255), 2, Qt.PenStyle.SolidLine))
        
        label = QGraphicsTextItem(f"TARGET: {self.tier_name}", self)
        label.setDefaultTextColor(QColor(0, 255, 255))
        label.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        label.setPos(45, 120 - self.h/2 - 18)
        
        self.addToGroup(self.box)
        self.setPos((WIDTH // 2) - 100 + x_offset, y_pos)
        self.scored = False

    def check_score(self, car_rect):
        ty = car_rect.top()
        ly = ty - self.y()
        if (120 - self.h/2) <= ly <= (120 + self.h/2): return self.pts, f"PRECISION! +{self.pts}", "#00FFFF"
        return 0, "MISSED", "#FF3C3C"

class PlayerCar(QGraphicsItemGroup):
    def __init__(self):
        super().__init__()
        
        body = QGraphicsRectItem(0, 0, 50, 90)
        body.setBrush(QBrush(QColor(60, 60, 70)))
        body.setPen(QPen(QColor(100, 100, 120), 1))
        
        glass = QGraphicsRectItem(5, 25, 40, 25)
        glass.setBrush(QBrush(QColor(15, 20, 35)))
        glass.setPen(QPen(QColor(50, 150, 255), 1))
        
        hl_left = QGraphicsRectItem(5, 0, 10, 4)
        hl_left.setBrush(QBrush(QColor(200, 240, 255)))
        hl_left.setPen(QPen(Qt.PenStyle.NoPen))
        hl_right = QGraphicsRectItem(35, 0, 10, 4)
        hl_right.setBrush(QBrush(QColor(200, 240, 255)))
        hl_right.setPen(QPen(Qt.PenStyle.NoPen))
        
        self.left_light = QGraphicsRectItem(5, 86, 12, 4)
        self.right_light = QGraphicsRectItem(33, 86, 12, 4)
        self.set_braking(False)
        
        self.addToGroup(body)
        self.addToGroup(glass)
        self.addToGroup(hl_left)
        self.addToGroup(hl_right)
        self.addToGroup(self.left_light)
        self.addToGroup(self.right_light)
        self.setZValue(100)

    def set_braking(self, is_braking):
        color = QColor(255, 30, 30) if is_braking else QColor(80, 10, 10)
        self.left_light.setBrush(QBrush(color))
        self.right_light.setBrush(QBrush(color))
        self.left_light.setPen(QPen(Qt.PenStyle.NoPen))
        self.right_light.setPen(QPen(Qt.PenStyle.NoPen))

# --- APP SCREENS ---
class GameView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.setSceneRect(0, 0, WIDTH, HEIGHT)
        
        self.setRenderHints(QPainter.RenderHint.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.setStyleSheet("border: none; background-color: #121215;")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.width() > 100 and self.height() > 100:
            self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

class MainMenu(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(30)
        
        title = QLabel("BULLSEYE BRAKING")
        title.setFont(QFont("Segoe UI", 48, QFont.Weight.Bold))
        title.setStyleSheet("color: #00FFFF; text-transform: uppercase;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        instructions = QLabel("GREEN: LOCK / START  |  YELLOW: QUIT\nTAP GAS: Cycle Selected Value")
        instructions.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        instructions.setStyleSheet("color: #888899;")
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(instructions)
        
        self.thresh_label = QLabel("1. BRAKE THRESHOLD: 0.1")
        self.thresh_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.thresh_label.setStyleSheet("color: #FFC832;") # Active color out of the gate
        self.thresh_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.thresh_label)

        self.speed_label = QLabel("2. MAX SPEED: 80 km/h")
        self.speed_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.speed_label.setStyleSheet("color: #555566;") # Dimmed initially
        self.speed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.speed_label)

class GameScreen(QWidget):
    finished_signal = pyqtSignal(dict)
    def __init__(self, sensor_shm):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.scene = QGraphicsScene(0, 0, WIDTH, HEIGHT)
        self.view = GameView(self.scene, self)
        self.layout.addWidget(self.view)
        
        self.sensor_shm = sensor_shm
        self.last_input_state = {"gas": False, "brake": False}
        self.gas_value = 0.0
        self.brake_value = 0.0

        self.brake_min = 40000
        self.brake_max = 150000
        self.gas_min = 2650
        self.gas_max = 3500
        
        self.active_brake_threshold = 0.1
        self.session_max_brake = 0.0
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_game)
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.tick_time)

        self.targets = []
        self.setup_environment()

    def setup_environment(self):
        road = QGraphicsRectItem((WIDTH // 2) - 150, 0, 300, HEIGHT)
        road.setBrush(QBrush(QColor(30, 30, 35)))
        road.setPen(QPen(Qt.PenStyle.NoPen))
        self.scene.addItem(road)
        
        self.grass_patches = []
        grass_width = (WIDTH // 2) - 150
        for i in range(-1, 9):
            for x in [0, (WIDTH // 2) + 150]:
                p = QGraphicsRectItem(0, 0, grass_width, 100); p.setPos(x, i * 100)
                p.setBrush(QBrush(QColor(20, 30, 22) if i % 2 == 0 else QColor(22, 33, 24)))
                p.setPen(QPen(Qt.PenStyle.NoPen))
                self.scene.addItem(p); self.grass_patches.append(p)
                
        self.road_lines = []
        for i in range(-1, 11):
            line = QGraphicsRectItem(0, 0, 6, 35); line.setPos((WIDTH // 2) - 3, i * 70)
            line.setBrush(QBrush(QColor(0, 180, 180)))
            line.setPen(QPen(Qt.PenStyle.NoPen)); self.scene.addItem(line); self.road_lines.append(line)
            
        self.player = PlayerCar()
        self.player.setPos((WIDTH // 2) - 25, HEIGHT - 150)
        self.scene.addItem(self.player)
        
        self.score_text = self.create_hud(f"SCORE: 0", 20, 20, "#FFFFFF", 20)
        self.streak_text = self.create_hud(f"STREAK: 0/3", 20, 60, "#00FFFF", 14)
        self.speed_text = self.create_hud("SPEED: 0 km/h", 20, 90, "#00FFFF", 14)
        
        self.time_bg = QGraphicsRectItem(WIDTH - 210, 20, 190, 45)
        self.time_bg.setBrush(QBrush(QColor(20, 20, 20)))
        self.time_bg.setPen(QPen(QColor(255, 200, 0), 1))
        self.time_bg.setZValue(140); self.scene.addItem(self.time_bg)
        self.time_text = self.create_hud(f"TIME: 0", WIDTH - 200, 25, "#FFCC00", 20)
        
        self.msg_bg = QGraphicsRectItem((WIDTH // 2) - 150, 220, 300, 60)
        self.msg_bg.setBrush(QBrush(QColor(30, 30, 35)))
        self.msg_bg.setPen(QPen(QColor(0, 255, 255), 1))
        self.msg_bg.hide(); self.scene.addItem(self.msg_bg)
        self.msg_text = self.create_hud("", (WIDTH // 2), 230, "white", 18); self.msg_text.setZValue(200)

    def create_hud(self, text, x, y, color, size):
        item = QGraphicsTextItem(text); item.setDefaultTextColor(QColor(color))
        item.setFont(QFont("Segoe UI", size, QFont.Weight.Bold)); item.setPos(x, y); item.setZValue(150)
        self.scene.addItem(item)
        return item

    def start_session(self, difficulty="Medium", brake_threshold=0.1, max_speed_val=80):
        self.active_brake_threshold = brake_threshold
        self.difficulty = difficulty
        self.config = DIFFICULTY_SETTINGS[difficulty]
        
        # Override the dict's config with the dynamic visual mapping
        self.config["MAX_SPEED"] = max_speed_val / 6.0 
        
        self.score = 0
        self.combo_count = 0
        self.time_left = GAME_DURATION
        self.current_speed = 0.0
        self.is_active = True
        self.reaction_times = []
        self.ptt_times = []
        self.gas_release_time = None
        self.active_target_spawn_time = None
        self.has_braked_for_current_target = False
        self.last_input_state = {"gas": False, "brake": False}
        self.session_max_brake = 0.0
        
        for t in self.targets:
            self.scene.removeItem(t)
        self.targets.clear()

        self.score_text.setPlainText(f"SCORE: {self.score}")
        self.streak_text.setPlainText(f"STREAK: {self.combo_count}/3")
        self.speed_text.setPlainText("SPEED: 0 km/h")
        self.time_text.setPlainText(f"TIME: {self.time_left}")
        self.msg_bg.hide()
        self.msg_text.setPlainText("")

        self.player.setPos((WIDTH // 2) - 25, HEIGHT - 150)
        self.player.set_braking(False)

        idx = 0
        for i in range(-1, 9):
            for x in [0, (WIDTH // 2) + 150]:
                self.grass_patches[idx].setPos(x, i * 100)
                idx += 1
                
        for i in range(-1, 11):
            self.road_lines[i+1].setPos((WIDTH // 2) - 3, i * 70)

        self.spawn_target(-800)
        self.timer.start(16)
        self.countdown_timer.start(1000)

    def spawn_target(self, y):
        x_var = random.randint(-45, 45)
        t = MultiTarget(y, x_var) if random.random() > 0.4 else QuickTarget(y, x_var)
        self.scene.addItem(t); self.targets.append(t)
        self.active_target_spawn_time = time.time(); self.has_braked_for_current_target = False

    def tick_time(self):
        self.time_left -= 1
        self.time_text.setPlainText(f"TIME: {self.time_left}")
        if self.time_left <= 0: self.end_game()

    def update_game(self):
        if not self.is_active: return

        gas_value = 0.0
        brake_value = 0.0

        def normalize_sensor(raw_value, min_value, max_value):
            if max_value <= min_value: return 0.0
            if (raw_value < 0): raw_value = -raw_value
            norm = (raw_value - min_value) / (max_value - min_value)
            return max(0.0, min(1.0, norm))

        if self.sensor_shm:
            try:
                data = self.sensor_shm.read_data()
                raw_brake = float(data["load_cell"]["sample"])
                raw_gas = float(data["hall_effect"]["sample"])
                
                # Independently track the highest force exerted this session
                if raw_brake > self.session_max_brake:
                    self.session_max_brake = raw_brake
                
                if raw_brake < self.brake_min and raw_brake > MIN_BRAKE: self.brake_min = raw_brake
                if raw_brake > self.brake_max and raw_brake < MAX_BRAKE: self.brake_max = raw_brake
                
                if raw_gas < self.gas_min and raw_gas > MIN_GAS: self.gas_min = raw_gas
                if raw_gas > self.gas_max: self.gas_max = raw_gas

                gas_value = normalize_sensor(raw_gas, self.gas_min, self.gas_max)
                brake_value = normalize_sensor(raw_brake, self.brake_min, self.brake_max)
            except Exception: pass

        GAS_THRESHOLD = 0.15; BRAKE_THRESHOLD = self.active_brake_threshold
        gas_pressed = gas_value > GAS_THRESHOLD; brake_pressed = brake_value > BRAKE_THRESHOLD

        if brake_pressed and not self.last_input_state["brake"]:
            if self.active_target_spawn_time and not self.has_braked_for_current_target:
                self.reaction_times.append(time.time() - self.active_target_spawn_time)
                self.has_braked_for_current_target = True
            
            # The transition time captures the exact reaction window from gas release to brake press
            if self.gas_release_time:
                self.ptt_times.append(time.time() - self.gas_release_time)
                self.gas_release_time = None

        if not gas_pressed and self.last_input_state["gas"]:
            self.gas_release_time = time.time()

        self.last_input_state = {"gas": gas_pressed, "brake": brake_pressed}
        self.player.set_braking(brake_pressed)

        if gas_value > 0.05: self.current_speed += self.config["ACCEL"] * gas_value
        if brake_value > 0.05: self.current_speed -= self.config["BRAKE_FORCE"] * brake_value
        if gas_value <= 0.05 and brake_value <= 0.05 and self.current_speed > 0:
            self.current_speed -= FRICTION

        self.current_speed = max(0, min(self.current_speed, self.config["MAX_SPEED"]))

        for p in self.grass_patches:
            p.setY(p.y() + self.current_speed)
            if p.y() >= HEIGHT: p.setY(p.y() - 1000)

        for line in self.road_lines:
            line.setY(line.y() + self.current_speed)
            if line.y() >= HEIGHT: line.setY(line.y() - 840)

        for t in self.targets[:]:
            t.setY(t.y() + self.current_speed)
            if self.current_speed == 0 and not t.scored:
                car_rect = self.player.sceneBoundingRect()
                if t.sceneBoundingRect().intersects(car_rect):
                    pts, msg, color = t.check_score(car_rect)
                    t.scored = True
                    if pts > 0:
                        self.score += pts
                        if isinstance(t, QuickTarget):
                            self.combo_count += 1; play_sound(SUCCESS_SOUNDS)
                            if self.combo_count == 3:
                                self.score += 15; self.combo_count = 0; msg, color = "COMBO STREAK! +15", "#FFD700"
                        elif isinstance(t, MultiTarget) and pts == 5:
                            play_sound(SUCCESS_SOUNDS)
                    else:
                        play_sound(FAIL_SOUNDS)
                        if isinstance(t, QuickTarget): self.combo_count = 0

                    self.streak_text.setPlainText(f"STREAK: {self.combo_count}/3")
                    self.score_text.setPlainText(f"SCORE: {self.score}")
                    self.msg_text.setDefaultTextColor(QColor(color))
                    self.msg_text.setPlainText(msg)
                    self.msg_text.setX((WIDTH // 2) - self.msg_text.boundingRect().width() // 2)
                    self.msg_bg.show()
                    QTimer.singleShot(1200, self.clear_msg)

            if t.y() > HEIGHT:
                if not t.scored:
                    play_sound(FAIL_SOUNDS)
                    if isinstance(t, QuickTarget): self.combo_count = 0
                    self.streak_text.setPlainText(f"STREAK: {self.combo_count}/3")
                self.scene.removeItem(t); self.targets.remove(t)
                dist = self.config["SPAWN_DIST"]
                self.spawn_target(random.randint(dist[0], dist[1]))

        self.speed_text.setPlainText(f"SPEED: {int(self.current_speed * 6)} km/h")

    def clear_msg(self):
        self.msg_text.setPlainText(""); self.msg_bg.hide()

    def end_game(self):
        self.is_active = False; self.timer.stop(); self.countdown_timer.stop()
        play_sound(GAMEOVER_SOUND)
        
        # Calculate fastest switch or default to 0
        fastest_switch = min(self.ptt_times) if self.ptt_times else 0.0
        
        stats = {
            "score": self.score,
            "max_brake": self.session_max_brake,
            "fast_switch": fastest_switch
        }
        self.finished_signal.emit(stats)

class ResultsScreen(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(15) 
        
        self.score_label = QLabel("FINAL SCORE: 0")
        self.score_label.setFont(QFont("Segoe UI", 48, QFont.Weight.Bold))
        self.score_label.setStyleSheet("color: #FFCC00;")
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.score_label)
        
        # New Max Brake Display
        self.brake_stat_label = QLabel("MAX BRAKE FORCE: 0")
        self.brake_stat_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.brake_stat_label.setStyleSheet("color: #FF3C3C;")
        self.brake_stat_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.brake_stat_label)
        
        # New Fastest Switch Display
        self.switch_stat_label = QLabel("FASTEST SWITCH: 0.00s")
        self.switch_stat_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.switch_stat_label.setStyleSheet("color: #00FFFF;")
        self.switch_stat_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.switch_stat_label)
        
        layout.addSpacing(20)
        
        instructions = QLabel("GREEN: PLAY AGAIN  |  YELLOW: QUIT")
        instructions.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        instructions.setStyleSheet("color: #888899;")
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(instructions)

    def display_results(self, stats):
        self.score_label.setText(f"FINAL SCORE: {stats['score']}")
        self.brake_stat_label.setText(f"MAX BRAKE FORCE: {int(stats['max_brake'])}")
        
        switch_time = stats['fast_switch']
        if switch_time > 0:
            self.switch_stat_label.setText(f"FASTEST SWITCH: {switch_time:.3f} s")
        else:
            self.switch_stat_label.setText("FASTEST SWITCH: N/A")

class BullseyeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bullseye Braking")
        self.setStyleSheet(GLOBAL_STYLESHEET)
            
        self.sensor_shm = None
        if HAS_SENSOR:
            try:
                self.sensor_shm = SensorSharedMemory(path="/home", project_id='R')
                self.sensor_shm.connect()
                print("Game: Connected to Hardware via Shared Memory.")
            except Exception as e:
                print(f"Game: Hardware connection failed: {e}")

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        
        self.menu = MainMenu()
        self.game = GameScreen(self.sensor_shm)
        self.results = ResultsScreen()
        
        self.stack.addWidget(self.menu)
        self.stack.addWidget(self.game)
        self.stack.addWidget(self.results)
        
        self.game.finished_signal.connect(self.show_results)

        self.showFullScreen()
        self.setCursor(Qt.CursorShape.BlankCursor) 
        
        # State machine and calibration setup
        self.prev_green = False
        self.prev_yellow = False
        self.prev_gas_pressed = False
        self.calibration_state = 0 # 0 = Threshold, 1 = Max Speed
        self.brake_threshold = 0.1 
        self.max_speed_val = 80
        
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll_hardware_buttons)
        self.poll_timer.start(50)  

    def poll_hardware_buttons(self):
        if not self.sensor_shm:
            return
            
        try:
            data = self.sensor_shm.read_data()
            
            # --- TWO-STAGE CALIBRATION ---
            if "hall_effect" in data:
                raw_gas = float(data["hall_effect"]["sample"])
                is_gas_pressed = raw_gas > (MIN_GAS + 500) 
                
                if self.stack.currentIndex() == 0:
                    if is_gas_pressed and not self.prev_gas_pressed:
                        
                        if self.calibration_state == 0:
                            self.brake_threshold = round(self.brake_threshold + 0.1, 1)
                            if self.brake_threshold > 0.7:
                                self.brake_threshold = 0.1
                            self.menu.thresh_label.setText(f"1. BRAKE THRESHOLD: {self.brake_threshold:.1f}")
                            
                        elif self.calibration_state == 1:
                            self.max_speed_val += 5
                            if self.max_speed_val > 120:
                                self.max_speed_val = 80
                            self.menu.speed_label.setText(f"2. MAX SPEED: {self.max_speed_val} km/h")
                            
                self.prev_gas_pressed = is_gas_pressed

            # --- MENU NAVIGATION ---
            if "sync" in data and "flags" in data["sync"]:
                green_pressed = int(data["sync"]["flags"][0]) == 1
                yellow_pressed = int(data["sync"]["flags"][1]) == 1
                
                if yellow_pressed and not self.prev_yellow:
                    self.shutdown()
                    
                elif green_pressed and not self.prev_green:
                    if self.stack.currentIndex() == 0:
                        # Lock step 1, move to step 2
                        if self.calibration_state == 0:
                            self.calibration_state = 1
                            self.menu.thresh_label.setStyleSheet("color: #555566;")
                            self.menu.speed_label.setStyleSheet("color: #FFC832;")
                        # Lock step 2, launch game
                        elif self.calibration_state == 1:
                            self.start_game()
                            
                    elif self.stack.currentIndex() == 2:
                        self.start_game()
                        
                self.prev_green = green_pressed
                self.prev_yellow = yellow_pressed
        except Exception:
            pass

    def start_game(self):
        self.stack.setCurrentIndex(1)
        QApplication.processEvents()
        
        if self.game.view.width() > 100:
            self.game.view.fitInView(self.game.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            
        # Pass the fully locked values into the session
        self.game.start_session("Medium", self.brake_threshold, self.max_speed_val)
        self.game.view.viewport().repaint()

    def show_results(self, stats):
        self.results.display_results(stats)
        self.stack.setCurrentIndex(2)
        QApplication.processEvents()
        
    def closeEvent(self, event):
        self.shutdown()
        event.ignore() 

    def shutdown(self):
        print("Initiating clean return to Main Menu...")
        self.poll_timer.stop()
        if hasattr(self.game, 'timer'):
            self.game.timer.stop()
            self.game.countdown_timer.stop()
            
        try: 
            pygame.mixer.quit()
        except Exception: 
            pass
            
        QApplication.quit()
        sys.exit(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BullseyeApp()
    sys.exit(app.exec())