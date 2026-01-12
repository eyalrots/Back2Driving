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
GRASS = (34, 139, 34)
ASPHALT = (45, 45, 45)
WHITE = (255, 255, 255)
RED = (200, 0, 0)
BLACK = (20, 20, 20)
BROWN = (101, 67, 33)
YELLOW = (255, 255, 0)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Driving Rehab Simulator - Realistic Braking")
clock = pygame.time.Clock()
font_large = pygame.font.SysFont("Arial", 32, bold=True)
font_small = pygame.font.SysFont("Arial", 22, bold=True)


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


class Junction:
    def __init__(self):
        self.y = -500
        self.type = "LIGHT"
        self.is_active = False
        self.light_state = "RED"
        self.timer = 0

    def spawn(self, type):
        self.y = -500
        self.type = type
        self.is_active = True
        self.light_state = "RED"
        self.timer = pygame.time.get_ticks()

    def update(self, speed):
        if not self.is_active: return
        self.y += speed
        now = pygame.time.get_ticks()
        if self.type == "LIGHT" and self.light_state == "RED" and now - self.timer > 5000:
            self.light_state = "GREEN"
        if self.y > HEIGHT: self.is_active = False

    def draw(self, surface):
        if not self.is_active: return
        for i in range(0, ROAD_WIDTH, 50):
            pygame.draw.rect(surface, WHITE, (ROAD_L + i + 10, self.y, 30, 100))
        sign_x = ROAD_R + 15
        if self.type == "LIGHT":
            pygame.draw.rect(surface, BLACK, (sign_x, self.y, 40, 100), border_radius=5)
            color = (255, 0, 0) if self.light_state == "RED" else (0, 255, 0)
            pygame.draw.circle(surface, color, (sign_x + 20, self.y + (25 if self.light_state == "RED" else 75)), 15)
        else:
            pygame.draw.circle(surface, RED, (sign_x + 20, self.y + 20), 25)
            pygame.draw.rect(surface, WHITE, (sign_x + 5, self.y + 16, 30, 8))


class Car:
    def __init__(self):
        self.rect = pygame.Rect(WIDTH // 2 - 20, HEIGHT - 120, 40, 75)
        self.speed = 0
        self.max_speed = 15

        # --- פרמטרים של פיזיקה "כבדה" ---
        self.accel = 0.06  # האצה איטית (דורש לחיצה ממושכת)
        self.brake_power = 0.09  # עוצמת בלימה (ככל שזה נמוך יותר, ייקח יותר זמן לעצור)
        self.drag = 0.99  # התנגדות טבעית (חיכוך הכביש)

    def update(self, gas_input, brake_input):
        if brake_input:
            # בלימה הדרגתית: מורידים מהמהירות כמות קבועה בכל פריים
            self.speed -= self.brake_power
        elif gas_input:
            # האצה הדרגתית
            self.speed += self.accel

        # חיכוך טבעי תמידי (האטה כשלא לוחצים על כלום)
        self.speed *= self.drag

        # מניעת מהירות שלילית וקביעת מקסימום
        if self.speed < 0: self.speed = 0
        if self.speed > self.max_speed: self.speed = self.max_speed

    def draw(self, surface):
        # צל
        pygame.draw.rect(surface, (20, 20, 20), (self.rect.x + 4, self.rect.y + 4, 40, 75), border_radius=8)
        # גוף המכונית משופר (כחול כהה עם עיצוב)
        pygame.draw.rect(surface, (0, 80, 180), self.rect, border_radius=8)
        # שמשות (תכלת)
        pygame.draw.rect(surface, (180, 230, 255), (self.rect.x + 5, self.rect.y + 12, 30, 18), border_radius=2)
        pygame.draw.rect(surface, (180, 230, 255), (self.rect.x + 5, self.rect.y + 55, 30, 8), border_radius=2)
        # אורות אחוריים (אדום חזק בבלימה)
        tail_light_color = (255, 0, 0) if keys[pygame.K_DOWN] else (150, 0, 0)
        pygame.draw.rect(surface, tail_light_color, (self.rect.x + 3, self.rect.y + 68, 10, 5))
        pygame.draw.rect(surface, tail_light_color, (self.rect.x + 27, self.rect.y + 68, 10, 5))


# --- עזרים ---
def draw_ui(surface, speed, limit, alert):
    kmh = int(speed * 10)
    # מד מהירות
    pygame.draw.rect(surface, (30, 30, 30), (20, 20, 150, 60), border_radius=10)
    text = font_large.render(f"{kmh} KM/H", True, WHITE)
    surface.blit(text, (35, 30))
    # תמרור מהירות
    pygame.draw.circle(surface, RED, (WIDTH - 70, 70), 45)
    pygame.draw.circle(surface, WHITE, (WIDTH - 70, 70), 38)
    limit_text = font_large.render(str(limit), True, BLACK)
    surface.blit(limit_text, (WIDTH - 90, 50))
    # התראה
    if alert:
        if (pygame.time.get_ticks() // 500) % 2 == 0:
            alert_surf = font_small.render(alert, True, YELLOW)
            pygame.draw.rect(surface, (150, 0, 0), (WIDTH // 2 - 110, 140, 220, 40), border_radius=5)
            surface.blit(alert_surf, (WIDTH // 2 - 100, 145))


# --- לולאה מרכזית ---
car = Car()
junction = Junction()
trees = []
road_lines = [pygame.Rect(WIDTH // 2 - 5, i * 120, 10, 50) for i in range(7)]
current_limit = 50
next_limit_change = 10000
next_event_time = 4000

while True:
    screen.fill(GRASS)
    pygame.draw.rect(screen, ASPHALT, (ROAD_L, 0, ROAD_WIDTH, HEIGHT))
    now = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT: pygame.quit(); sys.exit()

    keys = pygame.key.get_pressed()
    car.update(keys[pygame.K_UP], keys[pygame.K_DOWN])

    # עדכון גרפיקה זזה
    for line in road_lines:
        line.y += car.speed
        if line.y > HEIGHT: line.y = -120
    if random.random() < 0.03: trees.append(Tree(random.choice([0, 1])))
    for t in trees[:]:
        t.update(car.speed)
        if t.y > HEIGHT: trees.remove(t)

    # אירועים (צומת/מהירות)
    if not junction.is_active and now > next_event_time:
        junction.spawn(random.choice(["LIGHT", "STOP"]))
        next_event_time = now + random.randint(10000, 18000)
    junction.update(car.speed)
    if now > next_limit_change:
        current_limit = random.choice([30, 50, 70, 90])
        next_limit_change = now + 20000

    alert_msg = ""
    if junction.is_active:
        dist = car.rect.y - junction.y
        if 150 < dist < 450: alert_msg = "JUNCTION AHEAD!"

    # ציור
    for line in road_lines: pygame.draw.rect(screen, WHITE, line)
    junction.draw(screen)
    for t in trees: t.draw(screen)
    car.draw(screen)
    draw_ui(screen, car.speed, current_limit, alert_msg)

    pygame.display.flip()
    clock.tick(FPS)