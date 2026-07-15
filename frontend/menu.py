import sys
import os
import subprocess
import time
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont

# --- PATH CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR) 

try:
    from access_shared import SensorSharedMemory
    HAS_SENSOR = True
except ImportError as e:
    SensorSharedMemory = None
    HAS_SENSOR = False
    print(f"Warning: Shared memory is not available. ({e})")

# --- SUBPROCESS CONFIG ---
SENSOR_EXE_PATH = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "backend", "backend"))

def kill_sensor_backend():
    print("Terminating sensor backend...")
    try:
        # Restored 'sudo' to guarantee the root process is terminated
        subprocess.run(["sudo", "pkill", "-x", "backend"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Error terminating backend: {e}")

# --- MENU CONFIGURATION ---
GAMES = [
    {"title": "Bullseye Braking", "path": "bullseye/light_main.py"},
    {"title": "Rhythm Drive", "path": "bullseye/rhythm.py"},
    {"title": "Power Off Device", "path": None} 
]

GLOBAL_STYLESHEET = """
QWidget {
    background-color: #1E1E23;
    font-family: "Segoe UI", Arial, sans-serif;
}
QLabel {
    color: white;
}
"""

class MainMenuApp(QMainWindow):
    def __init__(self):
        # --- HIDE CURSOR ON START ---
        os.system("setterm -cursor off > /dev/tty1")
        
        super().__init__()
        self.setWindowTitle("System Main Menu")
        self.setStyleSheet(GLOBAL_STYLESHEET)
        
        # --- LAUNCH C BACKEND ---
        if HAS_SENSOR and os.path.exists(SENSOR_EXE_PATH):
            # Restored 'sudo' for bit-banging timing and memory access
            subprocess.Popen(["sudo", SENSOR_EXE_PATH], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.5)
        
        # --- SHARED MEMORY INIT ---
        self.sensor_shm = None
        if HAS_SENSOR:
            try:
                self.sensor_shm = SensorSharedMemory(path="/home", project_id='R')
                self.sensor_shm.connect()
            except Exception as e:
                print(f"Menu: Hardware connection failed: {e}")

        # --- UI LAYOUT ---
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.setSpacing(20)
        
        title = QLabel("SYSTEM MAIN MENU")
        title.setFont(QFont("Segoe UI", 48, QFont.Weight.Bold))
        title.setStyleSheet("color: #00CCFF; margin-bottom: 20px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(title)
        
        instructions = QLabel("GREEN: Select Game  |  YELLOW: Scroll List\n(Hold BOTH to Force Quit to Terminal)")
        instructions.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        instructions.setStyleSheet("color: #AAAAAA; margin-bottom: 40px;")
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(instructions)
        
        self.game_labels = []
        self.current_index = 0
        
        for game in GAMES:
            lbl = QLabel(game["title"])
            lbl.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout.addWidget(lbl)
            self.game_labels.append(lbl)
            
        self.update_ui()
        self.showFullScreen()
        self.setCursor(Qt.CursorShape.BlankCursor)
        
        # --- STATE MACHINE VARIABLES ---
        self.prev_green = False
        self.prev_yellow = False
        self.dual_hold_counter = 0 
        
        # Masking flags for interrupt handling
        self.first_poll = True
        self.mask_green_stale = False
        self.mask_yellow_stale = False
        
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll_hardware_buttons)
        self.poll_timer.start(50) 

    def update_ui(self):
        for i, lbl in enumerate(self.game_labels):
            if i == self.current_index:
                lbl.setStyleSheet("background-color: #3A3A45; border: 4px solid #00FF00; border-radius: 10px; padding: 15px; color: #00FF00;")
            else:
                lbl.setStyleSheet("background-color: #2A2A35; border: 4px solid transparent; border-radius: 10px; padding: 15px; color: white;")

    def poll_hardware_buttons(self):
        if not self.sensor_shm: return

        try:
            data = self.sensor_shm.read_data()
            if "sync" in data and "flags" in data["sync"]:
                raw_green = int(data["sync"]["flags"][0]) == 1
                raw_yellow = int(data["sync"]["flags"][1]) == 1
                
                # --- 1. STALE EDGE MASKING ---
                if self.first_poll:
                    self.mask_green_stale = raw_green
                    self.mask_yellow_stale = raw_yellow
                    self.first_poll = False
                    if raw_green or raw_yellow:
                        print("Stale memory detected. Masking buttons until physical release.")

                if self.mask_green_stale and not raw_green:
                    self.mask_green_stale = False
                if self.mask_yellow_stale and not raw_yellow:
                    self.mask_yellow_stale = False

                green_pressed = raw_green and not self.mask_green_stale
                yellow_pressed = raw_yellow and not self.mask_yellow_stale
                
                # --- 2. DUAL BUTTON HOLD DETECTION ---
                if green_pressed and yellow_pressed:
                    self.dual_hold_counter += 1
                    if self.dual_hold_counter >= 20: 
                        self.quit_to_terminal()
                        self.dual_hold_counter = 0
                    return 
                else:
                    self.dual_hold_counter = 0 
                    
                # --- 3. SINGLE BUTTON ACTIONS ---
                if yellow_pressed and not self.prev_yellow:
                    self.current_index = (self.current_index + 1) % len(GAMES)
                    self.update_ui()
                elif green_pressed and not self.prev_green:
                    self.launch_selected()
                    
                self.prev_green = green_pressed
                self.prev_yellow = yellow_pressed
        except Exception as e: 
            print(f"Hardware Poll Error: {e}") 

    def launch_selected(self):
        selected_item = GAMES[self.current_index]
        if selected_item["path"] is None:
            self.shutdown() 
        else:
            self.poll_timer.stop()
            self.hide()
            QApplication.processEvents()
            
            script_path = os.path.join(SCRIPT_DIR, selected_item["path"])
            venv_python = os.path.abspath(os.path.join(SCRIPT_DIR, "venv", "bin", "python"))
            
            subprocess.run([venv_python, script_path, "-platform", "linuxfb"])
            
            self.show()
            self.prev_green = True
            self.prev_yellow = True
            self.poll_timer.start(50)

    def quit_to_terminal(self):
        print("Forcing exit to terminal...")
        self.poll_timer.stop()
        kill_sensor_backend()
        
        os.system("sudo kbd_mode -a")
        os.system("setterm -cursor on > /dev/tty1")
        os.system("stty sane")
        os.system("reset")
        
        subprocess.run(["sudo", "systemctl", "start", "getty@tty1.service"])
        subprocess.run(["sudo", "systemctl", "stop", "driving-menu.service"])
        
        QApplication.quit()
        sys.exit(0)

    def shutdown(self):
        print("Initiating full system shutdown...")
        os.system("setterm -cursor on > /dev/tty1")
        self.poll_timer.stop()
        kill_sensor_backend()
        os.system("stty sane")
        os.system("reset")
        
        subprocess.run(["sudo", "systemctl", "poweroff"])
        QApplication.quit()
        sys.exit(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainMenuApp()
    sys.exit(app.exec())