import sys
import random
import time
import os
from datetime import datetime
import pygame  # For Clinical Audio Feedback
from PyQt6.QtWidgets import (QApplication, QMainWindow, QStackedWidget, QWidget, 
                             QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QLineEdit, QComboBox, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QGraphicsView, QGraphicsScene, 
                             QGraphicsRectItem, QGraphicsTextItem, QGraphicsItemGroup)
from PyQt6.QtCore import QTimer, Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QPen, QPainter, QFont, QLinearGradient

# Add parent directory to path to import access_shared
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from access_shared import SensorSharedMemory
    HAS_SENSOR = True
except ImportError as e:
    SensorSharedMemory = None
    HAS_SENSOR = False
    print(f"Warning: Shared memory is not available. Falling back to keyboard. ({e})")

# --- CONSTANTS & CONFIG ---
WIDTH = 800
HEIGHT = 600
FPS = 60
GAME_DURATION = 180 
FRICTION = 0.15 

DIFFICULTY_SETTINGS = {
    "Easy": {"MAX_SPEED": 10.0, "BRAKE_FORCE": 1.1, "ACCEL": 0.18, "SPAWN_DIST": (-2000, -1400)},
    "Medium": {"MAX_SPEED": 14.0, "BRAKE_FORCE": 0.8, "ACCEL": 0.22, "SPAWN_DIST": (-1700, -1100)},
    "Hard": {"MAX_SPEED": 19.0, "BRAKE_FORCE": 0.55, "ACCEL": 0.28, "SPAWN_DIST": (-1400, -800)}
}

# --- GLOBAL KEYBOARD STYLESHEET ---
# This makes whichever element has keyboard focus aggressively highlight in cyan
GLOBAL_STYLESHEET = """
QWidget {
    font-family: "Segoe UI", Arial, sans-serif;
}
QLineEdit, QComboBox, QPushButton {
    padding: 10px;
    font-size: 18px;
    border: 2px solid #555;
    border-radius: 5px;
    background-color: #333;
    color: white;
}
QComboBox::drop-down {
    border: 0px;
}
/* THE MAGIC KIOSK CSS: Aggressive highlight when focused via TAB */
QLineEdit:focus, QComboBox:focus, QPushButton:focus {
    border: 4px solid #00FFFF;
    background-color: #445;
    outline: none;
}
QPushButton:pressed {
    background-color: #0088CC;
}
"""

# --- AUDIO SETUP ---
try:
    pygame.mixer.init()
except Exception as e:
    print(f"Pygame Mixer Init Error: {e}")

SUCCESS_SOUNDS = [
    'assets/good_job_1.mpeg', 
    'assets/good_job_2.mpeg', 
    'assets/nice_one.mpeg', 
    'assets/great_job.mpeg', 
    'assets/great_succ.mpeg'
]
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
        shadow = QGraphicsRectItem(-5, -5, 210, 250)
        shadow.setBrush(QBrush(QColor(0, 0, 0, 40)))
        shadow.setPen(QPen(Qt.PenStyle.NoPen))
        self.addToGroup(shadow)

        self.outer = QGraphicsRectItem(0, 0, 200, 240)
        self.outer.setBrush(QBrush(QColor(220, 50, 50, 160)))
        self.outer.setPen(QPen(Qt.GlobalColor.white, 2))
        
        self.middle = QGraphicsRectItem(10, 60, 180, 120)
        self.middle.setBrush(QBrush(QColor(240, 240, 50, 180)))
        self.middle.setPen(QPen(Qt.GlobalColor.white, 1))
        
        self.inner = QGraphicsRectItem(20, 100, 160, 40)
        self.inner.setBrush(QBrush(QColor(50, 255, 50, 210)))
        self.inner.setPen(QPen(Qt.GlobalColor.white, 2))
        
        self.addToGroup(self.outer)
        self.addToGroup(self.middle)
        self.addToGroup(self.inner)
        self.setPos(300 + x_offset, y_pos)
        self.scored = False

    def check_score(self, car_rect):
        ty = car_rect.top()
        ly = ty - self.y()
        if 100 <= ly <= 140: return 5, "BULLSEYE! +5", "#00FF00"
        elif 60 <= ly <= 180: return 3, "GOOD STOP! +3", "#FFFF00"
        elif 0 <= ly <= 240: return 1, "OKAY +1", "#FFFFFF"
        return 0, "MISSED", "#FF5555"

class QuickTarget(QGraphicsItemGroup):
    def __init__(self, y_pos, x_offset=0):
        super().__init__()
        tiers = [(60, 5, "EASY TARGET"), (30, 10, "MEDIUM TARGET"), (12, 15, "HARD TARGET")]
        self.h, self.pts, self.tier_name = random.choice(tiers)
        
        self.box = QGraphicsRectItem(40, 120 - self.h/2, 120, self.h)
        self.box.setBrush(QBrush(QColor(0, 255, 255, 220)))
        self.box.setPen(QPen(Qt.GlobalColor.white, 2))
        
        label = QGraphicsTextItem(self.tier_name, self)
        label.setDefaultTextColor(QColor("white"))
        label.setFont(QFont("Arial", 7, QFont.Weight.Bold))
        label.setPos(60, 120 - self.h/2 - 15)
        
        self.addToGroup(self.box)
        self.setPos(300 + x_offset, y_pos)
        self.scored = False

    def check_score(self, car_rect):
        ty = car_rect.top()
        ly = ty - self.y()
        if (120 - self.h/2) <= ly <= (120 + self.h/2):
            return self.pts, f"PRECISION! +{self.pts}", "#00FFFF"
        return 0, "MISSED", "#FF5555"

class PlayerCar(QGraphicsItemGroup):
    def __init__(self):
        super().__init__()
        body = QGraphicsRectItem(0, 0, 50, 85)
        grad = QLinearGradient(0, 0, 50, 0)
        grad.setColorAt(0, QColor(0, 100, 255))
        grad.setColorAt(1, QColor(0, 200, 255))
        body.setBrush(QBrush(grad))
        body.setPen(QPen(Qt.GlobalColor.white, 2))
        
        self.left_light = QGraphicsRectItem(5, 75, 12, 6)
        self.right_light = QGraphicsRectItem(33, 75, 12, 6)
        self.set_braking(False)
        
        self.addToGroup(body)
        self.addToGroup(self.left_light)
        self.addToGroup(self.right_light)
        self.setZValue(100)

    def set_braking(self, is_braking):
        color = QColor(255, 0, 0) if is_braking else QColor(80, 0, 0)
        self.left_light.setBrush(QBrush(color))
        self.right_light.setBrush(QBrush(color))

# --- APP SCREENS ---

class GameView(QGraphicsView):
    key_signal = pyqtSignal(int, bool)
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSceneRect(0, 0, WIDTH, HEIGHT)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.keys_pressed = set()

    def keyPressEvent(self, event):
        if not event.isAutoRepeat():
            self.keys_pressed.add(event.key())
            self.key_signal.emit(event.key(), True)
        event.accept()

    def keyReleaseEvent(self, event):
        if not event.isAutoRepeat() and event.key() in self.keys_pressed:
            self.keys_pressed.remove(event.key())
            self.key_signal.emit(event.key(), False)
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

class MainMenu(QWidget):
    start_signal = pyqtSignal(str, str)
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        title = QLabel("BULLSEYE BRAKING")
        title.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
        title.setStyleSheet("color: #00CCFF; margin-bottom: 0px;")
        layout.addWidget(title)

        # KEYBOARD HINT
        hint = QLabel("Use [TAB] to navigate, [ENTER] to select")
        hint.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        hint.setStyleSheet("color: #AAAAAA; margin-bottom: 20px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        layout.addWidget(QLabel("Patient Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter patient name...")
        self.name_input.setFixedWidth(300)
        # Prevent mouse requirement to select
        self.name_input.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout.addWidget(self.name_input)

        layout.addWidget(QLabel("Select Difficulty:"))
        self.diff_box = QComboBox()
        self.diff_box.addItems(["Easy", "Medium", "Hard"])
        self.diff_box.setFixedWidth(300)
        self.diff_box.setCurrentText("Medium")
        self.diff_box.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout.addWidget(self.diff_box)

        self.start_btn = QPushButton("START CLINICAL SESSION")
        self.start_btn.setFixedWidth(300)
        self.start_btn.setFixedHeight(50)
        # Setting AutoDefault ensures pressing ENTER while focused triggers it
        self.start_btn.setAutoDefault(True) 
        self.start_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.start_btn.clicked.connect(self.on_start)
        layout.addWidget(self.start_btn)

    def on_start(self):
        name = self.name_input.text().strip() or "Anonymous"
        diff = self.diff_box.currentText()
        self.start_signal.emit(name, diff)

class GameScreen(QWidget):
    finished_signal = pyqtSignal(dict)
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.scene = QGraphicsScene(0, 0, WIDTH, HEIGHT)
        self.scene.setBackgroundBrush(QBrush(QColor(30, 30, 35)))
        self.view = GameView(self.scene, self)
        self.layout.addWidget(self.view)
        self.view.key_signal.connect(self.handle_keyboard_input)
        
        self.sensor_shm = None

        if HAS_SENSOR:
            try:
                self.sensor_shm = SensorSharedMemory(path="/home", project_id='R')
                self.sensor_shm.connect()
                print("Bullseye: Connected to Hardware via Shared Memory.")
            except Exception as e:
                print(f"Bullseye: Hardware connection failed: {e}")
                self.sensor_shm = None
 
        self.last_input_state = {"gas": False, "brake": False}
        self.keys_pressed = set()
        self.gas_value = 0.0
        self.brake_value = 0.0
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_game)
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.tick_time)

    def start_session(self, name, difficulty):
        self.patient_name = name
        self.difficulty = difficulty
        self.config = DIFFICULTY_SETTINGS[difficulty]
        self.scene.clear()
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
        self.gas_value = 0.0
        self.brake_value = 0.0
        self.setup_environment()
        self.timer.start(16)
        self.countdown_timer.start(1000)

    def setup_environment(self):
        self.grass_patches = []
        for i in range(-1, 9):
            for x in [0, 550]:
                # FIX: Create the rectangle at 0,0 local coordinates
                p = QGraphicsRectItem(0, 0, 250, 100)
                # FIX: Use setPos to set its actual trackable scene position
                p.setPos(x, i * 100)
                p.setBrush(QBrush(QColor(30, 80, 30) if i % 2 == 0 else QColor(35, 90, 35)))
                p.setPen(QPen(Qt.PenStyle.NoPen))
                self.scene.addItem(p)
                self.grass_patches.append(p)

        self.road_lines = []
        for i in range(-1, 11):
            # FIX: Create the line at 0,0 local coordinates
            line = QGraphicsRectItem(0, 0, 8, 35)
            # FIX: Use setPos to set its actual trackable scene position
            line.setPos(WIDTH // 2 - 4, i * 70)
            line.setBrush(QBrush(QColor(255, 255, 255, 180)))
            line.setPen(QPen(Qt.PenStyle.NoPen))
            self.scene.addItem(line)
            self.road_lines.append(line)

        self.player = PlayerCar()
        self.player.setPos(WIDTH // 2 - 25, HEIGHT - 150)
        self.scene.addItem(self.player)

        self.score_text = self.create_hud(f"SCORE: 0", 30, 30, "white", 22)
        self.streak_text = self.create_hud(f"STREAK: 0/3", 30, 100, "#00FFFF", 16)
        self.time_text = self.create_hud(f"TIME: {self.time_left}", WIDTH - 160, 30, "#FFCC00", 22)
        self.speed_text = self.create_hud("SPEED: 0 km/h", 30, 140, "#00FFFF", 14)

        self.msg_bg = QGraphicsRectItem(WIDTH // 2 - 150, 220, 300, 60)
        self.msg_bg.setBrush(QBrush(QColor(0, 0, 0, 180)))
        self.msg_bg.setPen(QPen(Qt.GlobalColor.white, 1))
        self.msg_bg.hide()
        self.scene.addItem(self.msg_bg)
        self.msg_text = self.create_hud("", WIDTH // 2, 230, "white", 20)
        self.msg_text.setZValue(200)

        self.targets = []
        self.spawn_target(-800)

    def create_hud(self, text, x, y, color, size):
        item = QGraphicsTextItem(text)
        item.setDefaultTextColor(QColor(color))
        item.setFont(QFont("Segoe UI", size, QFont.Weight.Bold))
        item.setPos(x, y)
        item.setZValue(150)
        self.scene.addItem(item)
        return item

    def spawn_target(self, y):
        x_var = random.randint(-45, 45)
        if random.random() > 0.4:
            t = MultiTarget(y, x_var)
        else:
            t = QuickTarget(y, x_var)
        self.scene.addItem(t)
        self.targets.append(t)
        self.active_target_spawn_time = time.time()
        self.has_braked_for_current_target = False

    def handle_keyboard_input(self, key, is_pressed):
        if is_pressed:
            self.keys_pressed.add(key)
        else:
            self.keys_pressed.discard(key)

    def tick_time(self):
        self.time_left -= 1
        self.time_text.setPlainText(f"TIME: {self.time_left}")
        if self.time_left <= 0:
            self.end_game()

    def update_game(self):
        if not self.is_active:
            return

        keyboard_gas = any(k in self.keys_pressed for k in [Qt.Key.Key_Up, 16777235])
        keyboard_brake = any(k in self.keys_pressed for k in [Qt.Key.Key_Down, 16777237])
        
        # --- NEW: Keyboard fallback to exit the game during testing ---
        if any(k in self.keys_pressed for k in [Qt.Key.Key_Escape]):
            print("Escape key pressed. Shutting down...")
            QApplication.quit()
            return

        gas_value = 1.0 if keyboard_gas else 0.0
        brake_value = 1.0 if keyboard_brake else 0.0

        GAS_MIN = 2122
        GAS_MAX = 3200
        BRAKE_MIN = 0
        BRAKE_MAX = 8388608

        def normalize_sensor(raw_value, min_value, max_value):
            if max_value == min_value:
                return 0.0
            if (raw_value < 0):
                raw_value  = -raw_value
            value = (raw_value - min_value) / (max_value - min_value)
            return value

        if self.sensor_shm:
            try:
                data = self.sensor_shm.read_data()
                
                # --- CORRECTED HARDWARE EXIT CHECK ---
                # Step 1: Look inside the "sync" dictionary first
                if "sync" in data and "flags" in data["sync"]:
                    try:
                        # Step 2: Grab the first item in the flags array
                        button_state = int(data["sync"]["flags"][0])
                        
                        if button_state == 1:
                            print("Hardware exit button pressed! Shutting down...")
                            
                            # Clean up Pygame audio before exit
                            try:
                                pygame.mixer.quit()
                            except:
                                pass
                                
                            QApplication.quit()
                            import os
                            os._exit(0) # Force immediate kill
                    except Exception as e:
                        print(f"Error reading flag: {e}")
                # ------------------------------------

                raw_brake = data["load_cell"]["sample"]
                raw_gas = data["hall_effect"]["sample"]
                gas_value = normalize_sensor(raw_gas, GAS_MIN, GAS_MAX)
                brake_value = normalize_sensor(raw_brake, BRAKE_MIN, BRAKE_MAX)
            except Exception as e:
                pass

        GAS_THRESHOLD = 0.15
        BRAKE_THRESHOLD = 0.01

        gas_pressed = gas_value > GAS_THRESHOLD
        brake_pressed = brake_value > BRAKE_THRESHOLD

        if brake_pressed and not self.last_input_state["brake"]:
            if self.active_target_spawn_time and not self.has_braked_for_current_target:
                self.reaction_times.append(time.time() - self.active_target_spawn_time)
                self.has_braked_for_current_target = True

            if self.gas_release_time:
                self.ptt_times.append(time.time() - self.gas_release_time)
                self.gas_release_time = None

        if not gas_pressed and self.last_input_state["gas"]:
            self.gas_release_time = time.time()

        self.last_input_state = {"gas": gas_pressed, "brake": brake_pressed}

        self.player.set_braking(brake_pressed)

        if gas_value > 0.05:
            self.current_speed += self.config["ACCEL"] * gas_value
        if brake_value > 0.05:
            self.current_speed -= self.config["BRAKE_FORCE"] * brake_value
        if gas_value <= 0.05 and brake_value <= 0.05:
            if self.current_speed > 0:
                self.current_speed -= FRICTION

        self.current_speed = max(0, min(self.current_speed, self.config["MAX_SPEED"]))

        # 4. Move environment

        for p in self.grass_patches:
            p.setY(p.y() + self.current_speed)
            if p.y() >= HEIGHT:
                p.setY(p.y() - 1000)

        for line in self.road_lines:
            line.setY(line.y() + self.current_speed)
            if line.y() >= HEIGHT:
                line.setY(line.y() - 840)

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
                            self.combo_count += 1
                            play_sound(SUCCESS_SOUNDS)
                            if self.combo_count == 3:
                                self.score += 15
                                self.combo_count = 0
                                msg, color = "COMBO STREAK! +15", "#FFD700"
                        elif isinstance(t, MultiTarget) and pts == 5:
                            play_sound(SUCCESS_SOUNDS)
                    else:
                        play_sound(FAIL_SOUNDS)
                        if isinstance(t, QuickTarget):
                            self.combo_count = 0

                    self.streak_text.setPlainText(f"STREAK: {self.combo_count}/3")
                    self.score_text.setPlainText(f"SCORE: {self.score}")
                    self.msg_text.setDefaultTextColor(QColor(color))
                    self.msg_text.setPlainText(msg)
                    self.msg_text.setX(WIDTH // 2 - self.msg_text.boundingRect().width() // 2)
                    self.msg_bg.show()
                    QTimer.singleShot(1200, self.clear_msg)

            if t.y() > HEIGHT:
                if not t.scored:
                    play_sound(FAIL_SOUNDS)
                    if isinstance(t, QuickTarget):
                        self.combo_count = 0
                    self.streak_text.setPlainText(f"STREAK: {self.combo_count}/3")

                self.scene.removeItem(t)
                self.targets.remove(t)

                dist = self.config["SPAWN_DIST"]
                self.spawn_target(random.randint(dist[0], dist[1]))

        self.speed_text.setPlainText(f"SPEED: {int(self.current_speed * 6)} km/h")

    def clear_msg(self):
        self.msg_text.setPlainText("")
        self.msg_bg.hide()

    def end_game(self):
        self.is_active = False
        self.timer.stop()
        self.countdown_timer.stop()
        play_sound(GAMEOVER_SOUND)
        avg_rt = sum(self.reaction_times) / len(self.reaction_times) if self.reaction_times else 0
        avg_ptt = sum(self.ptt_times) / len(self.ptt_times) if self.ptt_times else 0
        stats = {"time": datetime.now().strftime("%Y-%m-%d %H:%M"), "name": self.patient_name,
                 "difficulty": self.difficulty, "score": self.score, "avg_rt": avg_rt, "avg_ptt": avg_ptt}
        self.finished_signal.emit(stats)

class ResultsScreen(QWidget):
    restart_signal = pyqtSignal()
    home_signal = pyqtSignal()
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        # KEYBOARD HINT
        hint = QLabel("Use [TAB] to switch buttons, [ENTER] to select")
        hint.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        hint.setStyleSheet("color: #AAAAAA; margin-bottom: 10px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        title = QLabel("CLINICAL SESSION HISTORY")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Attempt", "Date/Time", "Name", "Difficulty", "Score", "Avg Reaction", "Avg PTT"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # CRITICAL UI CHANGE: Disable focus on the table so the user doesn't get trapped 
        # tabbing through empty cells when they just want to press "Play Again".
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        self.play_again_btn = QPushButton("PLAY AGAIN")
        self.play_again_btn.setFixedHeight(50)
        self.play_again_btn.setAutoDefault(True) # Triggers on Enter
        self.play_again_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.play_again_btn.clicked.connect(lambda: self.restart_signal.emit())
        
        self.home_btn = QPushButton("NEW PLAYER / HOME")
        self.home_btn.setFixedHeight(50)
        self.home_btn.setAutoDefault(True) # Triggers on Enter
        self.home_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.home_btn.clicked.connect(lambda: self.home_signal.emit())
        
        btn_layout.addWidget(self.play_again_btn)
        btn_layout.addWidget(self.home_btn)
        layout.addLayout(btn_layout)
        self.session_count = 0

    def add_result(self, stats):
        self.session_count += 1
        row = self.table.rowCount()
        self.table.insertRow(row)
        for i, val in enumerate([str(self.session_count), stats["time"], stats["name"], stats["difficulty"], 
                                 str(stats["score"]), f"{stats['avg_rt']:.3f}s", f"{stats['avg_ptt']:.3f}s"]):
            self.table.setItem(row, i, QTableWidgetItem(val))
        self.table.scrollToBottom()

class BullseyeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bullseye Braking Clinical Tool")
        
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        
        # Inject the global keyboard-focus stylesheet
        self.setStyleSheet(GLOBAL_STYLESHEET)
        
        self.menu = MainMenu()
        self.game = GameScreen() 
        self.results = ResultsScreen()
        
        self.stack.addWidget(self.menu)
        self.stack.addWidget(self.game)
        self.stack.addWidget(self.results)
        
        self.menu.start_signal.connect(self.start_game)
        self.game.finished_signal.connect(self.show_results)
        self.results.restart_signal.connect(self.play_again)
        self.results.home_signal.connect(self.go_home)

        self.showFullScreen()
        self.setCursor(Qt.CursorShape.BlankCursor) 
        
        # Explicitly set focus to the name input on boot
        self.menu.name_input.setFocus()

    def start_game(self, name, difficulty):
        self.last_name, self.last_difficulty = name, difficulty
        self.stack.setCurrentIndex(1)
        self.game.start_session(name, difficulty)
        # Give focus strictly to the game view to catch keyboard events
        self.game.view.setFocus()

    def show_results(self, stats):
        self.results.add_result(stats)
        self.stack.setCurrentIndex(2)
        # Explicitly set focus to the Play Again button so Enter works immediately
        self.results.play_again_btn.setFocus()

    def play_again(self):
        self.start_game(self.last_name, self.last_difficulty)

    def go_home(self):
        self.menu.name_input.clear()
        self.stack.setCurrentIndex(0)
        # Explicitly set focus back to the name input when returning home
        self.menu.name_input.setFocus()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BullseyeApp()
    sys.exit(app.exec())