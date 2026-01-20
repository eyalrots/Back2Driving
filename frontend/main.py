# import pygame
# import sys
# import random
#
# # --- הגדרות קבועות ---
# WIDTH, HEIGHT = 800, 600
# FPS = 60
# ROAD_WIDTH = 440
# ROAD_L = (WIDTH - ROAD_WIDTH) // 2
# ROAD_R = ROAD_L + ROAD_WIDTH
#
# # צבעים
# GRASS = (34, 139, 14)
# ASPHALT = (45, 45, 45)
# WHITE = (255, 255, 255)
# RED = (200, 0, 0)
# BLACK = (20, 20, 20)
# BROWN = (101, 67, 33)
# YELLOW = (255, 255, 0)
# ICE_COLOR = (173, 216, 230, 160) # תכלת שקוף
#
# pygame.init()
# pygame.mixer.init() # אתחול סאונד
# screen = pygame.display.set_mode((WIDTH, HEIGHT))
# pygame.display.set_caption("Driving Rehab Simulator - Enhanced Metrics")
# clock = pygame.time.Clock()
# font_large = pygame.font.SysFont("Arial", 32, bold=True)
# font_small = pygame.font.SysFont("Arial", 20, bold=True)
#
# # ניסיון טעינת סאונד
# try:
#     crash_sound = pygame.mixer.Sound("crash.wav")
# except:
#     crash_sound = None
#     print("Warning: crash.wav not found. Sound disabled.")
#
#
# # --- מחלקות המשחק ---
#
# class Tree:
#     def __init__(self, side):
#         self.x = random.randint(20, ROAD_L - 80) if side == 0 else random.randint(ROAD_R + 20, WIDTH - 80)
#         self.y = -150
#         self.size = random.randint(40, 60)
#
#     def update(self, speed):
#         self.y += speed
#
#     def draw(self, surface):
#         pygame.draw.rect(surface, BROWN, (self.x + self.size // 2 - 5, self.y + self.size - 10, 10, 25))
#         pygame.draw.circle(surface, (0, 100, 0), (self.x + self.size // 2, self.y + self.size // 2), self.size // 2)
#
# class Pedestrian:
#     """ילדה שחוצה את הכביש בתזמון מפתיע"""
#     def __init__(self):
#         self.rect = pygame.Rect(0, 0, 25, 45)
#         self.reset()
#
#     def reset(self):
#         self.rect.x = ROAD_L - 50
#         self.rect.y = -100
#         self.speed_x = 3
#         self.is_active = False
#         self.has_hit = False
#
#     def spawn(self):
#         self.rect.y = random.randint(50, 200)
#         self.rect.x = ROAD_L - 40
#         self.is_active = True
#         self.has_hit = False
#
#     def update(self, road_speed):
#         if not self.is_active: return
#         self.rect.x += self.speed_x
#         self.rect.y += road_speed
#         if self.rect.x > ROAD_R + 50 or self.rect.y > HEIGHT:
#             self.is_active = False
#
#     def draw(self, surface):
#         if self.is_active:
#             pygame.draw.ellipse(surface, (255, 200, 200), self.rect) # גוף הילדה
#             pygame.draw.circle(surface, (0, 0, 0), (self.rect.centerx, self.rect.y), 10) # ראש
#
# class IcePatch:
#     def __init__(self):
#         self.rect = pygame.Rect(ROAD_L + 50, -300, 340, 150)
#         self.is_active = False
#
#     def spawn(self):
#         self.rect.y = -200
#         self.is_active = True
#
#     def update(self, speed):
#         if self.is_active:
#             self.rect.y += speed
#             if self.rect.y > HEIGHT: self.is_active = False
#
#     def draw(self, surface):
#         if self.is_active:
#             s = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
#             pygame.draw.rect(s, ICE_COLOR, (0, 0, self.rect.width, self.rect.height), border_radius=15)
#             surface.blit(s, (self.rect.x, self.rect.y))
#
#
#
#
#
# class BallHazard:
#     """כדורגל שמתגלגל מהדשא השמאלי באלכסון לתוך הכביש"""
#
#     def __init__(self):
#         self.reset()
#
#     def reset(self):
#         # מתחיל מחוץ למסך משמאל (באזור הדשא) ובחלק העליון
#         self.x = ROAD_L - 80
#         self.y = -50
#         self.radius = 20
#         self.is_active = False
#
#         # מהירויות התנועה של הכדור
#         self.speed_x = 4.5  # כמה מהר הוא נכנס ימינה לכביש
#         self.speed_y_base = 2  # כמה מהר הוא יורד למטה ללא קשר למהירות הרכב
#
#     def spawn(self):
#         self.x = ROAD_L - 80
#         self.y = random.randint(-100, -20)  # גובה משתנה להתחלה
#         self.is_active = True
#
#     def update(self, road_speed):
#         if not self.is_active: return
#
#         # 1. תנועה ימינה (כניסה לכביש)
#         self.x += self.speed_x
#
#         # 2. תנועה למטה (שילוב של גלגול הכדור + תנועת המכונית קדימה)
#         self.y += road_speed + self.speed_y_base
#
#         # אם הכדור עבר את הכביש או יצא מהמסך
#         if self.y > HEIGHT or self.x > ROAD_R + 100:
#             self.is_active = False
#
#     def draw(self, surface):
#         if not self.is_active: return
#         # ציור כדורגל
#         pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), self.radius)
#         # כתמים שחורים לעיצוב
#         for offset in [(-6, -6), (7, 3), (-2, 9)]:
#             pygame.draw.circle(surface, BLACK, (int(self.x + offset[0]), int(self.y + offset[1])), 4)
# class Junction:
#     def __init__(self):
#         self.y = -500
#         self.type = "LIGHT"
#         self.is_active = False
#         self.light_state = "RED"
#         self.timer = 0
#
#     def spawn(self, type):
#         self.y = -600  # מתחיל רחוק יותר
#         self.type = type
#         self.is_active = True
#         self.light_state = "RED"
#         self.timer = pygame.time.get_ticks()
#
#     def update(self, speed):
#         if not self.is_active: return
#         self.y += speed
#         now = pygame.time.get_ticks()
#         # הרמזור הופך לירוק אחרי 6 שניות
#         if self.type == "LIGHT" and self.light_state == "RED" and now - self.timer > 6000:
#             self.light_state = "GREEN"
#         if self.y > HEIGHT: self.is_active = False
#
#     def draw(self, surface):
#         if not self.is_active: return
#         for i in range(0, ROAD_WIDTH, 50):
#             pygame.draw.rect(surface, WHITE, (ROAD_L + i + 10, self.y, 30, 100))
#         sign_x = ROAD_R + 15
#         if self.type == "LIGHT":
#             pygame.draw.rect(surface, BLACK, (sign_x, self.y, 40, 100), border_radius=5)
#             red_c = (255, 0, 0) if self.light_state == "RED" else (60, 0, 0)
#             green_c = (0, 255, 0) if self.light_state == "GREEN" else (0, 60, 0)
#             pygame.draw.circle(surface, red_c, (sign_x + 20, self.y + 25), 15)
#             pygame.draw.circle(surface, green_c, (sign_x + 20, self.y + 75), 15)
#         else:
#             pygame.draw.rect(surface, (100, 100, 100), (sign_x + 27, self.y + 55, 6, 50))
#             points = [(sign_x + 18, self.y), (sign_x + 42, self.y), (sign_x + 60, self.y + 18),
#                       (sign_x + 60, self.y + 42), (sign_x + 42, self.y + 60), (sign_x + 18, self.y + 60),
#                       (sign_x, self.y + 42), (sign_x, self.y + 18)]
#             pygame.draw.polygon(surface, RED, points)
#             pygame.draw.polygon(surface, WHITE, points, 3)
#
#
# class Car:
#     def __init__(self):
#         self.rect = pygame.Rect(WIDTH // 2 - 20, HEIGHT - 120, 40, 75)
#         self.speed = 0
#         self.max_speed = 15
#         self.accel = 0.06
#         self.brake_power = 0.12
#         self.drag = 0.99
#
#     def update(self, gas, brake):
#         if brake:
#             self.speed -= self.brake_power
#         elif gas:
#             self.speed += self.accel
#         self.speed *= self.drag
#         self.speed = max(0, min(self.speed, self.max_speed))
#
#     def draw(self, surface, brake_on):
#         pygame.draw.rect(surface, (20, 20, 20), (self.rect.x + 4, self.rect.y + 4, 40, 75), border_radius=8)
#         pygame.draw.rect(surface, (0, 80, 180), self.rect, border_radius=8)
#         pygame.draw.rect(surface, (180, 230, 255), (self.rect.x + 5, self.rect.y + 12, 30, 18), border_radius=2)
#         tail_light = (255, 0, 0) if brake_on else (150, 0, 0)
#         pygame.draw.rect(surface, tail_light, (self.rect.x + 3, self.rect.y + 68, 10, 5))
#         pygame.draw.rect(surface, tail_light, (self.rect.x + 27, self.rect.y + 68, 10, 5))
#
#
# # --- ניהול מדידות ---
#
# def draw_ui(surface, speed, limit, alert, ball_metrics, light_metrics):
#     kmh = int(speed * 10)
#     pygame.draw.rect(surface, (30, 30, 30), (10, 10, 200, 180), border_radius=10)
#     surface.blit(font_small.render(f"SPEED: {kmh} KM/H", True, WHITE), (20, 20))
#     surface.blit(font_small.render(f"LIMIT: {limit}", True, WHITE), (20, 45))
#
#     # הצגת תוצאות כדור
#     surface.blit(font_small.render(f"BALL RX: {ball_metrics[0]}ms", True, YELLOW), (20, 80))
#     surface.blit(font_small.render(f"BALL STOP: {ball_metrics[1]}ms", True, WHITE), (20, 105))
#
#     # הצגת תוצאות רמזור
#     surface.blit(font_small.render(f"LIGHT RX: {light_metrics[0]}ms", True, YELLOW), (20, 140))
#     surface.blit(font_small.render(f"LIGHT STOP: {light_metrics[1]}ms", True, WHITE), (20, 165))
#
#     if alert:
#         if (pygame.time.get_ticks() // 400) % 2 == 0:
#             pygame.draw.rect(surface, (150, 0, 0), (WIDTH // 2 - 110, 150, 220, 40), border_radius=5)
#             surface.blit(font_small.render(alert, True, YELLOW), (WIDTH // 2 - 100, 158))
#
#
# # --- לולאה מרכזית ---
# car = Car()
# junction = Junction()
# ball = BallHazard()
# trees = []
# road_lines = [pygame.Rect(WIDTH // 2 - 5, i * 120, 10, 50) for i in range(7)]
#
# # משתני ניטור
# ball_m = [0, 0]  # [תגובה, עצירה]
# light_m = [0, 0]  # [תגובה, עצירה]
# t0_ball = 0;
# t1_ball = 0;
# ball_active = False
# t0_light = 0;
# t1_light = 0;
# light_active = False
#
# next_event = 4000
# next_hazard = 8000
# current_limit = 50
#
# while True:
#     screen.fill(GRASS)
#     pygame.draw.rect(screen, ASPHALT, (ROAD_L, 0, ROAD_WIDTH, HEIGHT))
#     now = pygame.time.get_ticks()
#
#     for event in pygame.event.get():
#         if event.type == pygame.QUIT: pygame.quit(); sys.exit()
#
#     keys = pygame.key.get_pressed()
#     car.update(keys[pygame.K_UP], keys[pygame.K_DOWN])
#
#     # --- לוגיקת כדור ---
#     if not ball.is_active and now > next_hazard and car.speed > 5:
#         ball.spawn()
#         t0_ball = now;
#         t1_ball = 0;
#         ball_active = True
#
#     if ball_active:
#         if keys[pygame.K_DOWN] and t1_ball == 0:
#             t1_ball = now
#             ball_m[0] = t1_ball - t0_ball
#         if car.speed <= 0.1 and t1_ball != 0:
#             ball_m[1] = now - t1_ball
#             ball_active = False
#             next_hazard = now + random.randint(15000, 25000)
#
#     # --- לוגיקת רמזור אדום ---
#     if junction.is_active and junction.type == "LIGHT" and junction.light_state == "RED":
#         # המדידה מתחילה כשהרמזור נכנס למסך (y > 0)
#         if junction.y > 0 and t0_light == 0:
#             t0_light = now;
#             t1_light = 0;
#             light_active = True
#
#         if light_active:
#             if keys[pygame.K_DOWN] and t1_light == 0:
#                 t1_light = now
#                 light_m[0] = t1_light - t0_light
#             if car.speed <= 0.1 and t1_light != 0:
#                 light_m[1] = now - t1_light
#                 light_active = False
#     else:
#         t0_light = 0  # איפוס מוכנות למדידה הבאה
#
#     # עדכוני תנועה
#     ball.update(car.speed)
#     junction.update(car.speed)
#     for line in road_lines:
#         line.y += car.speed
#         if line.y > HEIGHT: line.y = -120
#     if random.random() < 0.03: trees.append(Tree(random.choice([0, 1])))
#     for t in trees[:]:
#         t.update(car.speed)
#         if t.y > HEIGHT: trees.remove(t)
#
#     # תזמון אירועים
#     if not junction.is_active and not ball.is_active and now > next_event:
#         junction.spawn(random.choice(["LIGHT", "STOP"]))
#         next_event = now + random.randint(15000, 25000)
#
#     alert = "WATCH OUT!" if ball.is_active else ("JUNCTION!" if junction.is_active and car.speed > 2 else "")
#
#     # ציור
#     for line in road_lines: pygame.draw.rect(screen, WHITE, line)
#     junction.draw(screen)
#     ball.draw(screen)
#     for t in trees: t.draw(screen)
#     car.draw(screen, keys[pygame.K_DOWN])
#     draw_ui(screen, car.speed, current_limit, alert, ball_m, light_m)
#
#     pygame.display.flip()
#     clock.tick(FPS)


# הקוד עם הילדה שהולכת במעבר חצייה
import pygame
import sys
import random

# --- הגדרות קבועות ---
WIDTH, HEIGHT = 800, 600
FPS = 60
ROAD_WIDTH = 440
ROAD_L = (WIDTH - ROAD_WIDTH) // 2
ROAD_R = ROAD_L + ROAD_WIDTH

# צבעים
GRASS = (34, 139, 14)
ASPHALT = (45, 45, 45)
WHITE = (255, 255, 255)
RED = (200, 0, 0)
BLACK = (20, 20, 20)
BROWN = (101, 67, 33)
YELLOW = (255, 255, 0)
ICE_COLOR = (173, 216, 230, 160)  # צבע קרח

pygame.init()
pygame.mixer.init()  # אתחול מערכת הקול
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Driving Rehab Simulator - Enhanced Metrics & Hazards")
clock = pygame.time.Clock()
font_large = pygame.font.SysFont("Arial", 32, bold=True)
font_small = pygame.font.SysFont("Arial", 20, bold=True)

# טעינת סאונד התראה/התנגשות (וודא שיש קובץ כזה או שנה את השם)
try:
    crash_sound = pygame.mixer.Sound("crash.wav")
except:
    crash_sound = None


# --- מחלקות המשחק ---

class Tree:
    def __init__(self, side):
        self.x = random.randint(20, ROAD_L - 80) if side == 0 else random.randint(ROAD_R + 20, WIDTH - 80)
        self.y = -150
        self.size = random.randint(40, 60)

    def update(self, speed):
        self.y += speed

    def draw(self, surface):
        pygame.draw.rect(surface, BROWN, (self.x + self.size // 2 - 5, self.y + self.size - 10, 10, 25))
        pygame.draw.circle(surface, (0, 100, 0), (self.x + self.size // 2, self.y + self.size // 2), self.size // 2)


class IcePatch:
    """מכשול קרח שגורם להחלקה"""

    def __init__(self):
        self.rect = pygame.Rect(ROAD_L + 50, -300, 300, 100)
        self.is_active = False

    def spawn(self):
        self.rect.y = -200
        self.is_active = True

    def update(self, speed):
        if self.is_active:
            self.rect.y += speed
            if self.rect.y > HEIGHT: self.is_active = False

    def draw(self, surface):
        if self.is_active:
            s = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            pygame.draw.rect(s, ICE_COLOR, (0, 0, self.rect.width, self.rect.height), border_radius=15)
            surface.blit(s, (self.rect.x, self.rect.y))


class Pedestrian:
    """הולכת רגל (ילדה) שחוצה את הכביש"""

    def __init__(self):
        self.rect = pygame.Rect(0, 0, 24, 40)
        self.is_active = False
        self.speed_x = 2

    def spawn(self, start_y):
        self.rect.x = ROAD_L - 30
        self.rect.y = start_y
        self.is_active = True

    def update(self, road_speed):
        if not self.is_active: return
        self.rect.x += self.speed_x
        self.rect.y += road_speed
        if self.rect.x > ROAD_R + 50 or self.rect.y > HEIGHT:
            self.is_active = False

    def draw(self, surface):
        if self.is_active:
            pygame.draw.ellipse(surface, (255, 180, 180), self.rect)  # גוף
            pygame.draw.circle(surface, (0, 0, 0), (self.rect.centerx, self.rect.y), 8)  # ראש


class BallHazard:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = ROAD_L - 80
        self.y = -50
        self.radius = 20
        self.is_active = False
        self.speed_x = 4.5
        self.speed_y_base = 2

    def spawn(self):
        self.x = ROAD_L - 80
        self.y = random.randint(-100, -20)
        self.is_active = True

    def update(self, road_speed):
        if not self.is_active: return
        self.x += self.speed_x
        self.y += road_speed + self.speed_y_base
        if self.y > HEIGHT or self.x > ROAD_R + 100:
            self.is_active = False

    def draw(self, surface):
        if not self.is_active: return
        pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), self.radius)
        for offset in [(-6, -6), (7, 3), (-2, 9)]:
            pygame.draw.circle(surface, BLACK, (int(self.x + offset[0]), int(self.y + offset[1])), 4)

    def get_rect(self):
        return pygame.Rect(self.x - self.radius, self.y - self.radius, self.radius * 2, self.radius * 2)


class Junction:
    def __init__(self):
        self.y = -500
        self.type = "LIGHT"
        self.is_active = False
        self.light_state = "RED"
        self.timer = 0
        self.violated = False  # האם כבר נרשמה פסילה על הרמזור הזה

    def spawn(self, type):
        self.y = -600
        self.type = type
        self.is_active = True
        self.light_state = "RED"
        self.timer = pygame.time.get_ticks()
        self.violated = False

    def update(self, speed):
        if not self.is_active: return
        self.y += speed
        now = pygame.time.get_ticks()
        if self.type == "LIGHT" and self.light_state == "RED" and now - self.timer > 6000:
            self.light_state = "GREEN"
        if self.y > HEIGHT: self.is_active = False

    def draw(self, surface):
        if not self.is_active: return
        for i in range(0, ROAD_WIDTH, 50):
            pygame.draw.rect(surface, WHITE, (ROAD_L + i + 10, self.y, 30, 100))
        sign_x = ROAD_R + 15
        if self.type == "LIGHT":
            pygame.draw.rect(surface, BLACK, (sign_x, self.y, 40, 100), border_radius=5)
            red_c = (255, 0, 0) if self.light_state == "RED" else (60, 0, 0)
            green_c = (0, 255, 0) if self.light_state == "GREEN" else (0, 60, 0)
            pygame.draw.circle(surface, red_c, (sign_x + 20, self.y + 25), 15)
            pygame.draw.circle(surface, green_c, (sign_x + 20, self.y + 75), 15)
        else:
            pygame.draw.rect(surface, (100, 100, 100), (sign_x + 27, self.y + 55, 6, 50))
            points = [(sign_x + 18, self.y), (sign_x + 42, self.y), (sign_x + 60, self.y + 18),
                      (sign_x + 60, self.y + 42), (sign_x + 42, self.y + 60), (sign_x + 18, self.y + 60),
                      (sign_x, self.y + 42), (sign_x, self.y + 18)]
            pygame.draw.polygon(surface, RED, points)
            pygame.draw.polygon(surface, WHITE, points, 3)


class Car:
    def __init__(self):
        self.rect = pygame.Rect(WIDTH // 2 - 20, HEIGHT - 120, 40, 75)
        self.speed = 0
        self.max_speed = 15
        self.accel = 0.06
        self.brake_power = 0.12
        self.drag = 0.99
        self.on_ice = False

    def update(self, gas, brake):
        # שינוי פיזיקה אם על קרח
        current_brake = self.brake_power if not self.on_ice else 0.01
        current_accel = self.accel if not self.on_ice else 0.02

        if brake:
            self.speed -= current_brake
        elif gas:
            self.speed += current_accel
        self.speed *= self.drag
        self.speed = max(0, min(self.speed, self.max_speed))

    def draw(self, surface, brake_on):
        pygame.draw.rect(surface, (20, 20, 20), (self.rect.x + 4, self.rect.y + 4, 40, 75), border_radius=8)
        color = (0, 80, 180) if not self.on_ice else (150, 200, 255)
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, (180, 230, 255), (self.rect.x + 5, self.rect.y + 12, 30, 18), border_radius=2)
        tail_light = (255, 0, 0) if brake_on else (150, 0, 0)
        pygame.draw.rect(surface, tail_light, (self.rect.x + 3, self.rect.y + 68, 10, 5))
        pygame.draw.rect(surface, tail_light, (self.rect.x + 27, self.rect.y + 68, 10, 5))


# --- ניהול מדידות ו-UI ---

def draw_ui(surface, speed, limit, alert, ball_metrics, light_metrics, failures):
    kmh = int(speed * 10)
    pygame.draw.rect(surface, (30, 30, 30), (10, 10, 210, 220), border_radius=10)
    surface.blit(font_small.render(f"SPEED: {kmh} KM/H", True, WHITE), (20, 20))
    surface.blit(font_small.render(f"LIMIT: {limit}", True, WHITE), (20, 45))

    # הצגת פסילות
    surface.blit(font_small.render(f"FAILURES: {failures}", True, RED), (20, 75))

    surface.blit(font_small.render(f"BALL RX: {ball_metrics[0]}ms", True, YELLOW), (20, 110))
    surface.blit(font_small.render(f"BALL STOP: {ball_metrics[1]}ms", True, WHITE), (20, 135))

    surface.blit(font_small.render(f"LIGHT RX: {light_metrics[0]}ms", True, YELLOW), (20, 170))
    surface.blit(font_small.render(f"LIGHT STOP: {light_metrics[1]}ms", True, WHITE), (20, 195))

    if alert:
        if (pygame.time.get_ticks() // 400) % 2 == 0:
            pygame.draw.rect(surface, (150, 0, 0), (WIDTH // 2 - 110, 150, 220, 40), border_radius=5)
            surface.blit(font_small.render(alert, True, YELLOW), (WIDTH // 2 - 100, 158))


# --- לולאה מרכזית ---
car = Car()
junction = Junction()
ball = BallHazard()
girl = Pedestrian()
ice = IcePatch()
trees = []
road_lines = [pygame.Rect(WIDTH // 2 - 5, i * 120, 10, 50) for i in range(7)]

# משתני ניטור (נשארים אותו דבר)
ball_m = [0, 0]
light_m = [0, 0]
t0_ball = 0;
t1_ball = 0;
ball_active = False
t0_light = 0;
t1_light = 0;
light_active = False

# משתני משחק חדשים
failures = 0
next_event = 4000
next_hazard = 8000
current_limit = 50
while True:
    screen.fill(GRASS)
    pygame.draw.rect(screen, ASPHALT, (ROAD_L, 0, ROAD_WIDTH, HEIGHT))
    now = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT: pygame.quit(); sys.exit()

    keys = pygame.key.get_pressed()
    car.update(keys[pygame.K_UP], keys[pygame.K_DOWN])

    # --- לוגיקת קרח ---
    car.on_ice = ice.is_active and car.rect.colliderect(ice.rect)

    # --- לוגיקת כדור (כולל התנגשות) ---
    if not ball.is_active and now > next_hazard and car.speed > 5:
        ball.spawn()
        t0_ball = now
        t1_ball = 0
        ball_active = True

    if ball_active:
        # בדיקת התנגשות פיזית בכדור
        if car.rect.colliderect(ball.get_rect()):
            failures += 1
            if crash_sound: crash_sound.play()
            ball.is_active = False # הכדור נעלם כדי שלא יספור שוב
            ball_active = False

        if keys[pygame.K_DOWN] and t1_ball == 0:
            t1_ball = now
            ball_m[0] = t1_ball - t0_ball
        if car.speed <= 0.1 and t1_ball != 0:
            ball_m[1] = now - t1_ball
            ball_active = False
            next_hazard = now + random.randint(15000, 25000)

    # --- לוגיקת רמזור ומעבר באדום ---
    if junction.is_active:
        # בדיקת מעבר באדום - רק אם סוג הצומת הוא רמזור (LIGHT)
        if junction.type == "LIGHT" and junction.light_state == "RED" and not junction.violated:
            # אם הרכב חוצה את קו הצומת (צד עליון של הרכב עובר את קו ה-Y של הצומת)
            if car.rect.top < junction.y + 50 and car.speed > 0.5:
                failures += 1
                junction.violated = True
                if crash_sound: crash_sound.play()

        # לוגיקת מדידת זמנים לרמזור אדום (נשארת ללא שינוי)
        if junction.type == "LIGHT" and junction.light_state == "RED":
            if junction.y > 0 and t0_light == 0:
                t0_light = now
                t1_light = 0
                light_active = True
            if light_active:
                if keys[pygame.K_DOWN] and t1_light == 0:
                    t1_light = now
                    light_m[0] = t1_light - t0_light
                if car.speed <= 0.1 and t1_light != 0:
                    light_m[1] = now - t1_light
                    light_active = False

        # לוגיקת הילדה בצומת STOP - מופיעה רק בתמרור
        if junction.type == "STOP" and junction.y > 50 and not girl.is_active:
            girl.spawn(junction.y + 20)

    # בדיקת התנגשות בילדה - רק אם יש מגע פיזי (colliderect)
    if girl.is_active:
        if car.rect.colliderect(girl.rect):
            failures += 1
            if crash_sound: crash_sound.play()
            girl.is_active = False # הילדה נעלמת כדי שלא יספור שוב

    # עדכוני תנועה
    ball.update(car.speed)
    girl.update(car.speed)
    junction.update(car.speed)
    ice.update(car.speed)

    for line in road_lines:
        line.y += car.speed
        if line.y > HEIGHT: line.y = -120
    if random.random() < 0.03: trees.append(Tree(random.choice([0, 1])))
    for t in trees[:]:
        t.update(car.speed)
        if t.y > HEIGHT: trees.remove(t)

    # תזמון אירועים (בחירה אקראית בין רמזור, תמרור עצור עם ילדה, או קרח)
    if not junction.is_active and not ball.is_active and now > next_event:
        choice = random.choice(["LIGHT", "STOP", "ICE"])
        if choice == "ICE":
            ice.spawn()
        else:
            junction.spawn(choice)
        next_event = now + random.randint(15000, 25000)

    # התראות על המסך
    alert = "WATCH OUT!" if ball.is_active or girl.is_active else (
        "JUNCTION!" if junction.is_active and car.speed > 2 else "")

    # ציור
    for line in road_lines: pygame.draw.rect(screen, WHITE, line)
    ice.draw(screen)
    junction.draw(screen)
    ball.draw(screen)
    girl.draw(screen)
    for t in trees: t.draw(screen)
    car.draw(screen, keys[pygame.K_DOWN])
    draw_ui(screen, car.speed, current_limit, alert, ball_m, light_m, failures)

    pygame.display.flip()
    clock.tick(FPS)