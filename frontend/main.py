import os
import random
import sys
from pathlib import Path

import pygame
from typing import Tuple


def _is_raspberry_pi() -> bool:
    """Best-effort Raspberry Pi detection without extra dependencies."""
    model_path = Path('/proc/device-tree/model')
    try:
        return model_path.exists() and 'raspberry pi' in model_path.read_text().lower()
    except Exception:
        return False


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


BASE_DIR = Path(__file__).resolve().parent
AUTO_PI = _is_raspberry_pi()
RASPBERRY_PI_MODE = _env_flag('B2D_PI_MODE', AUTO_PI)
ENABLE_SOUND = _env_flag('B2D_ENABLE_SOUND', True)
INPUT_MODE = os.getenv('B2D_INPUT_MODE', 'KEYBOARD').strip().upper()

if RASPBERRY_PI_MODE:
    WIDTH, HEIGHT = 640, 480
    FPS = 30
    ROAD_WIDTH = 360
    TREE_SPAWN_RATE = 0.018
    MAX_TREES = 40
else:
    WIDTH, HEIGHT = 800, 600
    FPS = 60
    ROAD_WIDTH = 440
    TREE_SPAWN_RATE = 0.03
    MAX_TREES = 70

ROAD_L = (WIDTH - ROAD_WIDTH) // 2
ROAD_R = ROAD_L + ROAD_WIDTH

# Colors
GRASS = (34, 139, 14)
ASPHALT = (45, 45, 45)
WHITE = (255, 255, 255)
RED = (200, 0, 0)
BLACK = (20, 20, 20)
BROWN = (101, 67, 33)
YELLOW = (255, 255, 0)
ICE_COLOR = (173, 216, 230, 160)


def asset_path(filename: str) -> Path:
    return BASE_DIR / filename


if ENABLE_SOUND:
    # Lower audio settings reduce CPU load and crackling risk on Pi Zero.
    pygame.mixer.pre_init(frequency=22050, size=-16, channels=1, buffer=256)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
mode_label = 'PI' if RASPBERRY_PI_MODE else 'PC'
pygame.display.set_caption(f'Driving Rehab Simulator ({mode_label})')
clock = pygame.time.Clock()
font_large = pygame.font.Font(None, 36 if RASPBERRY_PI_MODE else 42)
font_small = pygame.font.Font(None, 24 if RASPBERRY_PI_MODE else 28)

crash_sound = None
if ENABLE_SOUND:
    try:
        pygame.mixer.init()
        crash_sound = pygame.mixer.Sound(str(asset_path('crash.wav')))
    except Exception as exc:
        crash_sound = None
        print(f'[WARN] Audio disabled: {exc}')


class InputManager:
    """Reads driving input from keyboard or GPIO sensors."""

    def __init__(self, mode: str):
        self.mode = mode
        self._gpio = None
        self._ready = False
        self.gas_pin = 17
        self.brake_pin = 27

        if self.mode != 'SENSORS':
            return

        try:
            import RPi.GPIO as gpio  # type: ignore

            self._gpio = gpio
            gpio.setmode(gpio.BCM)
            gpio.setup(self.gas_pin, gpio.IN, pull_up_down=gpio.PUD_DOWN)
            gpio.setup(self.brake_pin, gpio.IN, pull_up_down=gpio.PUD_DOWN)
            self._ready = True
            print('[INFO] Sensor input enabled on GPIO 17/27.')
        except Exception as exc:
            self.mode = 'KEYBOARD'
            print(f'[WARN] Sensor mode unavailable ({exc}). Fallback to keyboard input.')

    def read(self, keys) -> Tuple[bool, bool]:
        if self.mode == 'SENSORS' and self._ready and self._gpio is not None:
            gas = bool(self._gpio.input(self.gas_pin))
            brake = bool(self._gpio.input(self.brake_pin))
            return gas, brake

        return bool(keys[pygame.K_UP]), bool(keys[pygame.K_DOWN])

    def close(self) -> None:
        if self._ready and self._gpio is not None:
            self._gpio.cleanup()


class Tree:
    def __init__(self, side: int):
        if side == 0:
            self.x = random.randint(20, ROAD_L - 80)
        else:
            self.x = random.randint(ROAD_R + 20, WIDTH - 80)
        self.y = -150
        self.size = random.randint(36, 56)

    def update(self, speed: float) -> None:
        self.y += speed

    def draw(self, surface) -> None:
        pygame.draw.rect(surface, BROWN, (self.x + self.size // 2 - 5, self.y + self.size - 10, 10, 25))
        pygame.draw.circle(surface, (0, 100, 0), (self.x + self.size // 2, self.y + self.size // 2), self.size // 2)


class IcePatch:
    """Ice hazard that reduces acceleration/brake effectiveness."""

    def __init__(self):
        self.rect = pygame.Rect(ROAD_L + 30, -250, ROAD_WIDTH - 60, 90 if RASPBERRY_PI_MODE else 100)
        self.is_active = False
        self.surface = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.rect(self.surface, ICE_COLOR, (0, 0, self.rect.width, self.rect.height), border_radius=15)

    def spawn(self) -> None:
        self.rect.y = -220
        self.is_active = True

    def update(self, speed: float) -> None:
        if self.is_active:
            self.rect.y += speed
            if self.rect.y > HEIGHT:
                self.is_active = False

    def draw(self, surface) -> None:
        if self.is_active:
            surface.blit(self.surface, self.rect.topleft)


class Pedestrian:
    def __init__(self):
        self.rect = pygame.Rect(0, 0, 24, 40)
        self.is_active = False
        self.speed_x = 2

    def spawn(self, start_y: float) -> None:
        self.rect.x = ROAD_L - 30
        self.rect.y = int(start_y)
        self.is_active = True

    def update(self, road_speed: float) -> None:
        if not self.is_active:
            return
        self.rect.x += self.speed_x
        self.rect.y += road_speed
        if self.rect.x > ROAD_R + 50 or self.rect.y > HEIGHT:
            self.is_active = False

    def draw(self, surface) -> None:
        if self.is_active:
            pygame.draw.ellipse(surface, (255, 180, 180), self.rect)
            pygame.draw.circle(surface, (0, 0, 0), (self.rect.centerx, self.rect.y), 8)


class BallHazard:
    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.x = float(ROAD_L - 80)
        self.y = -50.0
        self.radius = 20
        self.is_active = False
        self.speed_x = 4.5
        self.speed_y_base = 2

    def spawn(self) -> None:
        self.x = float(ROAD_L - 80)
        self.y = float(random.randint(-100, -20))
        self.is_active = True

    def update(self, road_speed: float) -> None:
        if not self.is_active:
            return
        self.x += self.speed_x
        self.y += road_speed + self.speed_y_base
        if self.y > HEIGHT or self.x > ROAD_R + 100:
            self.is_active = False

    def draw(self, surface) -> None:
        if not self.is_active:
            return
        pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), self.radius)
        for offset in [(-6, -6), (7, 3), (-2, 9)]:
            pygame.draw.circle(surface, BLACK, (int(self.x + offset[0]), int(self.y + offset[1])), 4)

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - self.radius), int(self.y - self.radius), self.radius * 2, self.radius * 2)


class Junction:
    def __init__(self):
        self.y = -500
        self.type = 'LIGHT'
        self.is_active = False
        self.light_state = 'RED'
        self.timer = 0
        self.violated = False

    def spawn(self, kind: str) -> None:
        self.y = -600
        self.type = kind
        self.is_active = True
        self.light_state = 'RED'
        self.timer = pygame.time.get_ticks()
        self.violated = False

    def update(self, speed: float) -> None:
        if not self.is_active:
            return

        self.y += speed
        now = pygame.time.get_ticks()
        if self.type == 'LIGHT' and self.light_state == 'RED' and now - self.timer > 6000:
            self.light_state = 'GREEN'
        if self.y > HEIGHT:
            self.is_active = False

    def draw(self, surface) -> None:
        if not self.is_active:
            return

        for i in range(0, ROAD_WIDTH, 50):
            pygame.draw.rect(surface, WHITE, (ROAD_L + i + 10, self.y, 30, 100))

        sign_x = ROAD_R + 15
        if self.type == 'LIGHT':
            pygame.draw.rect(surface, BLACK, (sign_x, self.y, 40, 100), border_radius=5)
            red_c = (255, 0, 0) if self.light_state == 'RED' else (60, 0, 0)
            green_c = (0, 255, 0) if self.light_state == 'GREEN' else (0, 60, 0)
            pygame.draw.circle(surface, red_c, (sign_x + 20, self.y + 25), 15)
            pygame.draw.circle(surface, green_c, (sign_x + 20, self.y + 75), 15)
        else:
            pygame.draw.rect(surface, (100, 100, 100), (sign_x + 27, self.y + 55, 6, 50))
            points = [
                (sign_x + 18, self.y),
                (sign_x + 42, self.y),
                (sign_x + 60, self.y + 18),
                (sign_x + 60, self.y + 42),
                (sign_x + 42, self.y + 60),
                (sign_x + 18, self.y + 60),
                (sign_x, self.y + 42),
                (sign_x, self.y + 18),
            ]
            pygame.draw.polygon(surface, RED, points)
            pygame.draw.polygon(surface, WHITE, points, 3)


class Car:
    def __init__(self):
        self.rect = pygame.Rect(WIDTH // 2 - 20, HEIGHT - 110, 40, 75)
        self.speed = 0.0
        self.max_speed = 13 if RASPBERRY_PI_MODE else 15
        self.accel = 0.055 if RASPBERRY_PI_MODE else 0.06
        self.brake_power = 0.12
        self.drag = 0.99
        self.on_ice = False

    def update(self, gas: bool, brake: bool) -> None:
        current_brake = self.brake_power if not self.on_ice else 0.01
        current_accel = self.accel if not self.on_ice else 0.02

        if brake:
            self.speed -= current_brake
        elif gas:
            self.speed += current_accel

        self.speed *= self.drag
        self.speed = max(0.0, min(self.speed, self.max_speed))

    def draw(self, surface, brake_on: bool) -> None:
        pygame.draw.rect(surface, (20, 20, 20), (self.rect.x + 4, self.rect.y + 4, 40, 75), border_radius=8)
        color = (0, 80, 180) if not self.on_ice else (150, 200, 255)
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, (180, 230, 255), (self.rect.x + 5, self.rect.y + 12, 30, 18), border_radius=2)
        tail_light = (255, 0, 0) if brake_on else (150, 0, 0)
        pygame.draw.rect(surface, tail_light, (self.rect.x + 3, self.rect.y + 68, 10, 5))
        pygame.draw.rect(surface, tail_light, (self.rect.x + 27, self.rect.y + 68, 10, 5))


def draw_ui(surface, speed: float, limit: int, alert: str, ball_metrics, light_metrics, failures: int) -> None:
    kmh = int(speed * 10)
    panel_h = 210 if HEIGHT <= 480 else 220
    pygame.draw.rect(surface, (30, 30, 30), (10, 10, 220, panel_h), border_radius=10)
    surface.blit(font_small.render(f'SPEED: {kmh} KM/H', True, WHITE), (20, 20))
    surface.blit(font_small.render(f'LIMIT: {limit}', True, WHITE), (20, 45))
    surface.blit(font_small.render(f'FAILURES: {failures}', True, RED), (20, 75))

    surface.blit(font_small.render(f'BALL RX: {ball_metrics[0]}ms', True, YELLOW), (20, 110))
    surface.blit(font_small.render(f'BALL STOP: {ball_metrics[1]}ms', True, WHITE), (20, 135))

    surface.blit(font_small.render(f'LIGHT RX: {light_metrics[0]}ms', True, YELLOW), (20, 165))
    surface.blit(font_small.render(f'LIGHT STOP: {light_metrics[1]}ms', True, WHITE), (20, 190))

    if alert and (pygame.time.get_ticks() // 400) % 2 == 0:
        pygame.draw.rect(surface, (150, 0, 0), (WIDTH // 2 - 110, 135, 220, 40), border_radius=5)
        surface.blit(font_small.render(alert, True, YELLOW), (WIDTH // 2 - 100, 143))


def play_crash() -> None:
    if crash_sound is not None:
        crash_sound.play()


def main() -> None:
    input_manager = InputManager(INPUT_MODE)

    car = Car()
    junction = Junction()
    ball = BallHazard()
    girl = Pedestrian()
    ice = IcePatch()
    trees = []

    road_lines = [pygame.Rect(WIDTH // 2 - 5, i * 110, 10, 45) for i in range((HEIGHT // 100) + 3)]

    ball_m = [0, 0]
    light_m = [0, 0]

    t0_ball = 0
    t1_ball = 0
    ball_active = False

    t0_light = 0
    t1_light = 0
    light_active = False

    failures = 0
    next_event = 4000
    next_hazard = 8000
    current_limit = 50

    running = True
    try:
        while running:
            screen.fill(GRASS)
            pygame.draw.rect(screen, ASPHALT, (ROAD_L, 0, ROAD_WIDTH, HEIGHT))
            now = pygame.time.get_ticks()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False

            keys = pygame.key.get_pressed()
            gas_pressed, brake_pressed = input_manager.read(keys)
            car.update(gas_pressed, brake_pressed)

            # Ice physics
            car.on_ice = ice.is_active and car.rect.colliderect(ice.rect)

            # Ball logic
            if (not ball.is_active) and now > next_hazard and car.speed > 4:
                ball.spawn()
                t0_ball = now
                t1_ball = 0
                ball_active = True

            if ball_active:
                if car.rect.colliderect(ball.get_rect()):
                    failures += 1
                    play_crash()
                    ball.is_active = False
                    ball_active = False
                    next_hazard = now + random.randint(15000, 25000)

                if brake_pressed and t1_ball == 0:
                    t1_ball = now
                    ball_m[0] = t1_ball - t0_ball

                if car.speed <= 0.1 and t1_ball != 0:
                    ball_m[1] = now - t1_ball
                    ball_active = False
                    next_hazard = now + random.randint(15000, 25000)

                if not ball.is_active and ball_active:
                    ball_active = False
                    next_hazard = now + random.randint(15000, 25000)

            # Junction logic + red-light violation
            if junction.is_active:
                if junction.type == 'LIGHT' and junction.light_state == 'RED' and not junction.violated:
                    if car.rect.top < junction.y + 50 and car.speed > 0.5:
                        failures += 1
                        junction.violated = True
                        play_crash()

                if junction.type == 'LIGHT' and junction.light_state == 'RED':
                    if junction.y > 0 and t0_light == 0:
                        t0_light = now
                        t1_light = 0
                        light_active = True

                    if light_active:
                        if brake_pressed and t1_light == 0:
                            t1_light = now
                            light_m[0] = t1_light - t0_light

                        if car.speed <= 0.1 and t1_light != 0:
                            light_m[1] = now - t1_light
                            light_active = False

                if junction.type == 'STOP' and junction.y > 50 and not girl.is_active:
                    girl.spawn(junction.y + 20)
            else:
                t0_light = 0
                t1_light = 0
                light_active = False

            # Pedestrian collision
            if girl.is_active and car.rect.colliderect(girl.rect):
                failures += 1
                play_crash()
                girl.is_active = False

            # Update world
            ball.update(car.speed)
            girl.update(car.speed)
            junction.update(car.speed)
            ice.update(car.speed)

            for line in road_lines:
                line.y += car.speed
                if line.y > HEIGHT:
                    line.y = -120

            if car.speed > 0.5 and len(trees) < MAX_TREES and random.random() < TREE_SPAWN_RATE:
                trees.append(Tree(random.choice([0, 1])))

            for tree in trees[:]:
                tree.update(car.speed)
                if tree.y > HEIGHT + 50:
                    trees.remove(tree)

            # Event timing
            if (not junction.is_active) and (not ball.is_active) and now > next_event:
                choice = random.choice(['LIGHT', 'STOP', 'ICE'])
                if choice == 'ICE':
                    ice.spawn()
                else:
                    junction.spawn(choice)
                next_event = now + random.randint(15000, 25000)

            # Alerts
            if ball.is_active or girl.is_active:
                alert = 'WATCH OUT!'
            elif junction.is_active and car.speed > 2:
                alert = 'JUNCTION!'
            else:
                alert = ''

            # Draw
            for line in road_lines:
                pygame.draw.rect(screen, WHITE, line)
            ice.draw(screen)
            junction.draw(screen)
            ball.draw(screen)
            girl.draw(screen)
            for tree in trees:
                tree.draw(screen)
            car.draw(screen, brake_pressed)
            draw_ui(screen, car.speed, current_limit, alert, ball_m, light_m, failures)

            pygame.display.flip()
            clock.tick(FPS)
    finally:
        input_manager.close()
        pygame.quit()
        sys.exit()


if __name__ == '__main__':
    main()
