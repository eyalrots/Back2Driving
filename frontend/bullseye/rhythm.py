import sys
import os
import json
import random
import time
import pygame
from PyQt6.QtWidgets import (QApplication, QMainWindow, QStackedWidget, QWidget, 
                             QVBoxLayout, QLabel, QGraphicsView, QGraphicsScene, 
                             QGraphicsRectItem, QGraphicsTextItem, QGraphicsPolygonItem)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QColor, QBrush, QPen, QPainter, QFont, QPolygonF

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

# --- CONFIGURATION & CONSTANTS ---
WIDTH = 1066
HEIGHT = 600
FPS = 60

MIN_BRAKE = 40000
MAX_BRAKE = 215000
MIN_GAS = 2600

# Dashboard Aesthetic Colors
BLACK = QColor(18, 18, 21)
ASPHALT = QColor(30, 30, 35)
CYAN_LINE = QColor(0, 180, 180)

WHITE = QColor(255, 255, 255)
CYAN_NOTE = QColor(0, 255, 255)       
DARK_CYAN_TAIL = QColor(0, 100, 100)  
RED_NOTE = QColor(255, 60, 60)        
DARK_RED_TAIL = QColor(100, 20, 20)
GREEN_PERFECT = QColor(50, 255, 100)
GOLD = QColor(255, 200, 50)

# Perspective Math
SCROLL_SPEED = 0.5      
HIT_Y = 520             
LANE_WIDTH_BOTTOM = 220 
LANE_WIDTH_TOP = 40     
VANISHING_POINT_Y = 100 

# Expanded Hit Windows (ms)
PERFECT_WINDOW = 80     
GOOD_WINDOW = 180
OKAY_WINDOW = 300
GRACE_PERIOD = 200      

BEATMAP_PATH = os.path.join(SCRIPT_DIR, "beatmap.json")

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

def get_width_for_y(y):
    rel_y = max(0.0, min(1.0, (y - VANISHING_POINT_Y) / (HEIGHT - VANISHING_POINT_Y)))
    return LANE_WIDTH_TOP + (LANE_WIDTH_BOTTOM - LANE_WIDTH_TOP) * rel_y

def get_x_for_lane(y, lane_type):
    w = get_width_for_y(y)
    center_x = WIDTH / 2
    # Flipped logic: Gas (1) on right, Brake (-1) on left
    return center_x if lane_type == 1 else center_x - w

# --- GAME ENTITIES ---
class Note:
    def __init__(self, target_time, note_type, duration, scene):
        self.target_time = target_time * 1000  
        self.type = note_type                  
        self.duration = duration * 1000        
        self.hit = False
        self.missed = False
        
        self.is_holding = False
        self.hold_completed = False
        self.release_time = 0                  
        
        self.color = CYAN_NOTE if self.type == 1 else RED_NOTE
        self.tail_color = DARK_CYAN_TAIL if self.type == 1 else DARK_RED_TAIL

        self.tail_item = QGraphicsPolygonItem()
        self.tail_item.setPen(QPen(Qt.PenStyle.NoPen))
        self.tail_item.hide()
        scene.addItem(self.tail_item)
        
        self.head_item = QGraphicsRectItem()
        self.head_item.setPen(QPen(Qt.PenStyle.NoPen))
        self.head_item.hide()
        scene.addItem(self.head_item)

    def update_graphics(self, current_time):
        if self.missed or self.hold_completed:
            self.head_item.hide()
            self.tail_item.hide()
            return

        y = HIT_Y - (self.target_time - current_time) * SCROLL_SPEED
        tail_y = HIT_Y - (self.target_time + self.duration - current_time) * SCROLL_SPEED
        
        head_y = y
        if self.is_holding:
            head_y = HIT_Y
            if tail_y > HIT_Y: tail_y = HIT_Y

        if tail_y > HEIGHT or (head_y < VANISHING_POINT_Y and tail_y < VANISHING_POINT_Y):
            self.head_item.hide()
            self.tail_item.hide()
            return

        if self.duration > 0:
            w_top = get_width_for_y(tail_y) * 0.8
            x_top = get_x_for_lane(tail_y, self.type) + 5
            w_bot = get_width_for_y(head_y) * 0.8
            x_bot = get_x_for_lane(head_y, self.type) + 5
            
            poly = QPolygonF()
            poly.append(QPointF(x_top, tail_y))
            poly.append(QPointF(x_top + w_top, tail_y))
            poly.append(QPointF(x_bot + w_bot, head_y))
            poly.append(QPointF(x_bot, head_y))
            
            self.tail_item.setPolygon(poly)
            self.tail_item.setBrush(QBrush(self.color if self.is_holding else self.tail_color))
            self.tail_item.show()
        else:
            self.tail_item.hide()

        if not self.hold_completed and head_y >= VANISHING_POINT_Y and head_y <= HEIGHT + 50:
            curr_w = get_width_for_y(head_y) * 0.8
            curr_x = get_x_for_lane(head_y, self.type) + 5
            rect_h = max(2.0, 20.0 * (head_y / HIT_Y))
            
            self.head_item.setRect(curr_x, head_y - rect_h/2, curr_w, rect_h)
            self.head_item.setBrush(QBrush(WHITE if self.is_holding else self.color))
            self.head_item.show()
        else:
            self.head_item.hide()

class PopupManager:
    def __init__(self, scene):
        self.popups = []
        for _ in range(8):  
            item = QGraphicsTextItem("")
            item.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            item.setZValue(200)
            item.hide()
            scene.addItem(item)
            self.popups.append({"item": item, "life": 0.0, "y": 0, "x": 0})

    def show_popup(self, text, x, y, color):
        for p in self.popups:
            if p["life"] <= 0:
                p["item"].setPlainText(text)
                p["item"].setDefaultTextColor(color)
                adjusted_x = x - (p["item"].boundingRect().width() / 2)
                p["x"] = adjusted_x
                p["y"] = y
                p["life"] = 1.0
                p["item"].setPos(adjusted_x, y)
                p["item"].show()
                break

    def update(self):
        for p in self.popups:
            if p["life"] > 0:
                p["life"] -= 0.03
                p["y"] -= 1.5
                p["item"].setPos(p["x"], p["y"])
                if p["life"] <= 0:
                    p["item"].hide()

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
        layout.setSpacing(40)
        
        title = QLabel("RHYTHM DRIVE")
        title.setFont(QFont("Segoe UI", 48, QFont.Weight.Bold))
        title.setStyleSheet("color: #00FFFF; text-transform: uppercase;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        instructions = QLabel("GREEN: START  |  YELLOW: QUIT\nTAP GAS: Calibrate Threshold")
        instructions.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        instructions.setStyleSheet("color: #888899;")
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(instructions)
        
        self.thresh_label = QLabel("BRAKE THRESHOLD: 0.1")
        self.thresh_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.thresh_label.setStyleSheet("color: #FFC832;")
        self.thresh_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.thresh_label)

    def update_threshold_display(self, val):
        self.thresh_label.setText(f"BRAKE THRESHOLD: {val:.1f}")

class GameScreen(QWidget):
    finished_signal = pyqtSignal(dict)
    def __init__(self, sensor_shm):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.scene = QGraphicsScene(0, 0, WIDTH, HEIGHT)
        self.scene.setBackgroundBrush(QBrush(BLACK))
        self.view = GameView(self.scene, self)
        self.layout.addWidget(self.view)
        
        self.sensor_shm = sensor_shm
        self.last_input_state = {"gas": False, "brake": False}
        
        # Initial Calibration Baselines
        self.brake_min = 30000
        self.brake_max = 80000
        self.gas_min = 2650
        self.gas_max = 3500
        self.active_brake_threshold = 0.1
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_game)

        self.notes = []
        self.beatmap_data = []
        self.load_beatmap()
        self.setup_environment()

    def load_beatmap(self):
        try:
            with open(BEATMAP_PATH, "r") as f:
                self.beatmap_data = json.load(f)
        except Exception:
            print("Warning: beatmap.json not found. Generating procedural 2-minute track.")
            self.beatmap_data = []
            current_t = 2.0
            while current_t < 120.0:  
                n_type = 1 if random.random() > 0.5 else -1
                duration = random.choice([0.0, 0.0, 0.0, 1.0, 1.5])
                self.beatmap_data.append({"time": current_t, "type": n_type, "duration": duration})
                current_t += random.uniform(1.0, 2.5)

    def setup_environment(self):
        road_poly = QPolygonF()
        road_poly.append(QPointF((WIDTH / 2) - LANE_WIDTH_TOP, VANISHING_POINT_Y))
        road_poly.append(QPointF((WIDTH / 2) + LANE_WIDTH_TOP, VANISHING_POINT_Y))
        road_poly.append(QPointF((WIDTH / 2) + LANE_WIDTH_BOTTOM, HEIGHT))
        road_poly.append(QPointF((WIDTH / 2) - LANE_WIDTH_BOTTOM, HEIGHT))
        
        road = QGraphicsPolygonItem(road_poly)
        road.setBrush(QBrush(ASPHALT))
        road.setPen(QPen(Qt.PenStyle.NoPen))
        self.scene.addItem(road)
        
        center_poly = QPolygonF()
        center_poly.append(QPointF(WIDTH / 2 - 1, VANISHING_POINT_Y))
        center_poly.append(QPointF(WIDTH / 2 + 1, VANISHING_POINT_Y))
        center_poly.append(QPointF(WIDTH / 2 + 2, HEIGHT))
        center_poly.append(QPointF(WIDTH / 2 - 2, HEIGHT))
        
        center_line = QGraphicsPolygonItem(center_poly)
        center_line.setBrush(QBrush(CYAN_LINE))
        center_line.setPen(QPen(Qt.PenStyle.NoPen))
        self.scene.addItem(center_line)

        hw = get_width_for_y(HIT_Y)
        hit_line = QGraphicsRectItem((WIDTH / 2) - hw, HIT_Y - 2, hw * 2, 4)
        hit_line.setBrush(QBrush(CYAN_LINE))
        hit_line.setPen(QPen(Qt.PenStyle.NoPen))
        self.scene.addItem(hit_line)

        self.brake_ind_bg = QGraphicsRectItem(20, HEIGHT - 50, 150, 30)
        self.brake_ind_bg.setBrush(QBrush(QColor(40, 0, 0)))
        self.brake_ind_bg.setPen(QPen(RED_NOTE, 2))
        self.scene.addItem(self.brake_ind_bg)
        self.brake_ind_txt = self.create_hud("BRAKE PEDAL", 35, HEIGHT - 48, "#FF3C3C", 12)

        self.gas_ind_bg = QGraphicsRectItem(WIDTH - 170, HEIGHT - 50, 150, 30)
        self.gas_ind_bg.setBrush(QBrush(QColor(0, 40, 40)))
        self.gas_ind_bg.setPen(QPen(CYAN_NOTE, 2))
        self.scene.addItem(self.gas_ind_bg)
        self.gas_ind_txt = self.create_hud("GAS PEDAL", WIDTH - 140, HEIGHT - 48, "#00FFFF", 12)
        
        self.score_text = self.create_hud("SCORE: 0", 20, 20, "#FFFFFF", 20)
        self.combo_text = self.create_hud("COMBO: 0", WIDTH - 160, 20, "#00FFFF", 20)
        
        self.popup_manager = PopupManager(self.scene)

    def create_hud(self, text, x, y, color, size):
        item = QGraphicsTextItem(text)
        item.setDefaultTextColor(QColor(color))
        item.setFont(QFont("Segoe UI", size, QFont.Weight.Bold))
        item.setPos(x, y)
        item.setZValue(150)
        self.scene.addItem(item)
        return item

    def start_session(self, brake_threshold=0.1):
        self.active_brake_threshold = brake_threshold
        self.score = 0
        self.combo = 0
        self.is_active = True
        self.last_input_state = {"gas": False, "brake": False}
        self.start_ticks = int(time.time() * 1000)
        
        self.session_max_brake = 0.0
        self.ptt_times = []
        self.gas_release_time = None
        
        for note in self.notes:
            self.scene.removeItem(note.head_item)
            self.scene.removeItem(note.tail_item)
        self.notes.clear()

        self.load_beatmap()

        for n_data in self.beatmap_data:
            self.notes.append(Note(n_data['time'], n_data['type'], n_data.get('duration', 0), self.scene))

        self.end_time = max([n.target_time + n.duration for n in self.notes], default=0) + 3000

        self.score_text.setPlainText(f"SCORE: {self.score}")
        self.combo_text.setPlainText(f"COMBO: {self.combo}")

        self.timer.start(16)

    def update_game(self):
        if not self.is_active: return

        current_time = int(time.time() * 1000) - self.start_ticks
        
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
                
                # Dynamically expand boundaries if new extremes are detected
                if raw_brake < self.brake_min and raw_brake > MIN_BRAKE: self.brake_min = raw_brake
                if raw_brake > self.brake_max and raw_brake < MAX_BRAKE: self.brake_max = raw_brake
                
                if raw_gas < self.gas_min and raw_gas > MIN_GAS: self.gas_min = raw_gas
                if raw_gas > self.gas_max: self.gas_max = raw_gas

                gas_value = normalize_sensor(raw_gas, self.gas_min, self.gas_max)
                brake_value = normalize_sensor(raw_brake, self.brake_min, self.brake_max)
            except Exception: pass

        GAS_THRESHOLD = 0.15; BRAKE_THRESHOLD = self.active_brake_threshold
        gas_pressed = gas_value > GAS_THRESHOLD
        brake_pressed = brake_value > BRAKE_THRESHOLD

        # Track the reaction gap between gas release and brake press
        if brake_pressed and not self.last_input_state["brake"]:
            if self.gas_release_time:
                self.ptt_times.append(time.time() - self.gas_release_time)
                self.gas_release_time = None

        if not gas_pressed and self.last_input_state["gas"]:
            self.gas_release_time = time.time()

        if gas_pressed:
            self.gas_ind_bg.setBrush(QBrush(CYAN_NOTE))
            self.gas_ind_txt.setDefaultTextColor(BLACK)
        else:
            self.gas_ind_bg.setBrush(QBrush(QColor(0, 40, 40)))
            self.gas_ind_txt.setDefaultTextColor(CYAN_NOTE)

        if brake_pressed:
            self.brake_ind_bg.setBrush(QBrush(RED_NOTE))
            self.brake_ind_txt.setDefaultTextColor(BLACK)
        else:
            self.brake_ind_bg.setBrush(QBrush(QColor(40, 0, 0)))
            self.brake_ind_txt.setDefaultTextColor(RED_NOTE)

        if gas_pressed and not self.last_input_state["gas"]:
            self.check_hit(current_time, 1)

        if brake_pressed and not self.last_input_state["brake"]:
            self.check_hit(current_time, -1)

        self.last_input_state = {"gas": gas_pressed, "brake": brake_pressed}

        gas_now = gas_pressed
        brake_now = brake_pressed

        for note in self.notes:
            note.update_graphics(current_time)

            if not note.hit and not note.missed and (current_time - note.target_time) > OKAY_WINDOW:
                self.trigger_miss(note)

            if note.hit and note.duration > 0 and not note.hold_completed:
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
                        self.combo_text.setPlainText(f"COMBO: {self.combo}")
                        lane_center_x = get_x_for_lane(HIT_Y, note.type) + (get_width_for_y(HIT_Y) / 2)
                        self.popup_manager.show_popup("DROPPED", lane_center_x, HIT_Y-80, RED_NOTE)

                if current_time >= note.target_time + note.duration:
                    note.is_holding = False
                    note.hold_completed = True
                    self.score += 500
                    lane_center_x = get_x_for_lane(HIT_Y, note.type) + (get_width_for_y(HIT_Y) / 2)
                    self.popup_manager.show_popup("FINISH!", lane_center_x, HIT_Y-80, GOLD)

        self.popup_manager.update()
        self.score_text.setPlainText(f"SCORE: {self.score:06}")

        if current_time > self.end_time:
            self.end_game()

    def check_hit(self, current_time, input_type):
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
        
        lane_center_x = get_x_for_lane(HIT_Y, note.type) + (get_width_for_y(HIT_Y) / 2)

        if abs_delta <= PERFECT_WINDOW:
            note.hit = True
            self.score += 100
            self.combo += 1
            self.popup_manager.show_popup("PERFECT!", lane_center_x, HIT_Y - 40, GOLD)
        elif abs_delta <= GOOD_WINDOW:
            note.hit = True
            self.score += 50
            self.combo += 1
            self.popup_manager.show_popup("GOOD!", lane_center_x, HIT_Y - 40, GREEN_PERFECT)
        elif abs_delta <= OKAY_WINDOW:
            note.hit = True
            self.score += 10
            self.combo += 1
            self.popup_manager.show_popup("OKAY", lane_center_x, HIT_Y - 40, WHITE)
        else:
            if abs_delta < 500:
                if delta < 0:
                    self.trigger_miss(note, "TOO EARLY")
                else:
                    self.trigger_miss(note, "TOO LATE")
            return

        self.combo_text.setPlainText(f"COMBO: {self.combo}")
        if note.duration > 0 and note.hit:
            note.is_holding = True

    def trigger_miss(self, note, reason="MISSED"):
        note.missed = True
        self.combo = 0
        self.combo_text.setPlainText(f"COMBO: {self.combo}")
        lane_center_x = get_x_for_lane(HIT_Y, note.type) + (get_width_for_y(HIT_Y) / 2)
        self.popup_manager.show_popup(reason, lane_center_x, HIT_Y - 40, RED_NOTE)

    def end_game(self):
        self.is_active = False
        self.timer.stop()
        
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
        
        self.brake_stat_label = QLabel("MAX BRAKE FORCE: 0")
        self.brake_stat_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.brake_stat_label.setStyleSheet("color: #FF3C3C;")
        self.brake_stat_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.brake_stat_label)
        
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

class RhythmApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rhythm Drive")
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
        
        self.prev_green = False
        self.prev_yellow = False
        self.prev_gas_pressed = False
        self.brake_threshold = 0.1
        
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll_hardware_buttons)
        self.poll_timer.start(50)  

    def poll_hardware_buttons(self):
        if not self.sensor_shm:
            return
            
        try:
            data = self.sensor_shm.read_data()

            # --- GAS PEDAL THRESHOLD CALIBRATION ---
            if "hall_effect" in data:
                raw_gas = float(data["hall_effect"]["sample"])
                is_gas_pressed = raw_gas > (MIN_GAS + 500)
                
                if self.stack.currentIndex() == 0:
                    if is_gas_pressed and not self.prev_gas_pressed:
                        self.brake_threshold = round(self.brake_threshold + 0.1, 1)
                        if self.brake_threshold > 0.7:
                            self.brake_threshold = 0.1
                        self.menu.update_threshold_display(self.brake_threshold)
                        
                self.prev_gas_pressed = is_gas_pressed

            # --- MENU NAVIGATION ---
            if "sync" in data and "flags" in data["sync"]:
                green_pressed = int(data["sync"]["flags"][0]) == 1
                yellow_pressed = int(data["sync"]["flags"][1]) == 1
                
                if yellow_pressed and not self.prev_yellow:
                    self.shutdown()
                    
                elif green_pressed and not self.prev_green:
                    if self.stack.currentIndex() != 1:  
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
            
        self.game.start_session(self.brake_threshold)
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
            
        try: 
            pygame.mixer.quit()
        except Exception: 
            pass
            
        QApplication.quit()
        sys.exit(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RhythmApp()
    sys.exit(app.exec())