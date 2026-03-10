import pygame
import json
import os

# --- הגדרות ---
SONG_PATH = "Katy Perry_Firework.mp3" # ודאי שזה השם המדויק של קובץ האודיו שלך
OUTPUT_FILE = "beatmap.json"

def record_beatmap():
    pygame.init()
    screen = pygame.display.set_mode((500, 300))
    pygame.display.set_caption("Rhythm Drive - Beatmap Recorder")
    font = pygame.font.SysFont(None, 36)
    
    if not os.path.exists(SONG_PATH):
        print(f"Error: Could not find audio file '{SONG_PATH}'")
        return

    pygame.mixer.init()
    pygame.mixer.music.load(SONG_PATH)
    
    beatmap = []
    # מילון לשמירת זמני תחילת לחיצה: [key] = start_time
    active_holds = {pygame.K_UP: None, pygame.K_DOWN: None}
    
    # מסך המתנה
    waiting = True
    while waiting:
        screen.fill((20, 20, 30))
        txt = font.render("Press SPACE to Start Recording", True, (255, 255, 255))
        screen.blit(txt, (50, 130))
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                waiting = False
    
    # התחלת הקלטה
    pygame.mixer.music.play()
    start_ticks = pygame.time.get_ticks()
    recording = True
    
    while recording:
        current_time = (pygame.time.get_ticks() - start_ticks) / 1000.0
        screen.fill((30, 30, 30))
        
        # תצוגה
        time_txt = font.render(f"Recording... Time: {current_time:.2f}s", True, (100, 255, 100))
        screen.blit(time_txt, (20, 20))
        inst1 = font.render("UP = Gas (Blue), DOWN = Brake (Red)", True, (200, 200, 200))
        screen.blit(inst1, (20, 80))
        inst2 = font.render("Press ESC to Save and Exit", True, (255, 100, 100))
        screen.blit(inst2, (20, 140))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                recording = False
                
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    recording = False
                elif event.key == pygame.K_UP and active_holds[pygame.K_UP] is None:
                    active_holds[pygame.K_UP] = current_time # מתחילים לחיצת גז
                elif event.key == pygame.K_DOWN and active_holds[pygame.K_DOWN] is None:
                    active_holds[pygame.K_DOWN] = current_time # מתחילים לחיצת ברקס
                    
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_UP and active_holds[pygame.K_UP] is not None:
                    duration = current_time - active_holds[pygame.K_UP]
                    beatmap.append({"time": round(active_holds[pygame.K_UP], 2), "type": 1, "duration": round(duration, 2)})
                    active_holds[pygame.K_UP] = None
                
                elif event.key == pygame.K_DOWN and active_holds[pygame.K_DOWN] is not None:
                    duration = current_time - active_holds[pygame.K_DOWN]
                    beatmap.append({"time": round(active_holds[pygame.K_DOWN], 2), "type": -1, "duration": round(duration, 2)})
                    active_holds[pygame.K_DOWN] = None

        pygame.display.flip()
        pygame.time.Clock().tick(60)
    
    # מיון התווים לפי זמן הופעה ושמירה לקובץ
    beatmap.sort(key=lambda x: x["time"])
    with open(OUTPUT_FILE, "w") as f:
        json.dump(beatmap, f, indent=4)
    
    print(f"\nSuccess! Saved {len(beatmap)} notes to {OUTPUT_FILE}")
    pygame.quit()

if __name__ == "__main__":
    record_beatmap()