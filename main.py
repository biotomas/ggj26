from __future__ import annotations

import math
import time
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List

import pygame
from pygame.math import Vector2

try:
    from levels import all_levels
except ImportError:
    # This is a common workaround for certain pygbag versions
    import levels
    all_levels = levels.all_levels

import os
import sys

import asyncio


def resource_path(relative_path):
    """ Get absolute path to resource, compatible with PyInstaller and Pygbag """
    try:
        # Check for PyInstaller's temporary folder
        base_path = sys._MEIPASS
    except Exception:
        # For Pygbag and local dev, use the directory of the script
        # This is more reliable than abspath(".") in a browser context
        base_path = os.path.dirname(__file__)

    # Ensure we use forward slashes for the web virtual filesystem
    path = os.path.join(base_path, relative_path)
    return path.replace("\\", "/")

# ============================
# Config / Constants
# ============================

TILE_SIZE: int = 80
SCREEN_SIZE: tuple[int, int] = (1360, 768)
PLAYER_SPEED: float = 220.0  # pixels / second

Color = tuple[int, int, int]

WHITE: Color = (255, 255, 255)
GRAY: Color = (160, 160, 160)
DARK_GRAY: Color = (60, 60, 60)
BLUE: Color = (80, 140, 255)
BROWN: Color = (160, 110, 60)

break_mask = None
ignore_mask = None
push_mask = None
floor_normal = None
floor_glow = None
crystal_normal = None
crystal_glow = None
background = None
hero_down = None
hero_up = None
hero_left = None
hero_right = None

shatter = None

break_sound = None
push_sound = None
move_sound = None

mask_sounds = None

# ============================
# Grid Utilities
# ============================

@dataclass(frozen=True, slots=True)
class GridPos:
    x: int
    y: int

    def to_world(self) -> Vector2:
        return Vector2(pygame.Rect(self.x * TILE_SIZE, self.y * TILE_SIZE, TILE_SIZE, TILE_SIZE).center)


# ============================
# Level
# ============================


# # = wall, @ = player, + = player on goal, $ = crystal, * = crystal on goal, . = goal, ' ' = floor
# P = push mask, B = break mask, I = ignore mask
level_str: str = """
######
#.$@ #
#P# B#
#$# I#
#$  $#
######
"""

class LevelText:
    def __init__(self, pos: GridPos, text: str) -> None:
        self.pos = pos
        font = pygame.font.Font(None, 40)
        self.text = font.render(text, False, (20, 20, 20))

    def draw(self, surface: pygame.Surface, camera: Camera2D) -> None:

        # Center the text
        rect = pygame.Rect(
            self.pos.x * TILE_SIZE,
            self.pos.y * TILE_SIZE,
            TILE_SIZE,
            TILE_SIZE,
        )
        rect = self.text.get_rect(center=rect.center)
        # rect = camera.apply_rect(rect)

        # --- Create a temporary surface for the rounded rectangle ---
        padding = 20  # space around the text
        radius = 16  # corner radius

        bg_surf = pygame.Surface(
            (rect.width + padding * 2, rect.height + padding * 2), pygame.SRCALPHA
        )
        bg_color = (150, 150, 150, 180)  # semi-transparent gray (A=180)
        pygame.draw.rect(bg_surf, bg_color, bg_surf.get_rect(), border_radius=radius)

        # --- Blit the background and then the text ---
        bg_rect = bg_surf.get_rect(center=rect.center)
        camera.blit(surface, bg_surf, bg_rect.topleft)
        camera.blit(surface, self.text, rect.topleft)



class Level:
    def __init__(self, level: str) -> None:
        self.walls: set[GridPos] = set()
        self.goals: set[GridPos] = set()
        self.floors: set[GridPos] = set()
        self.boxes: set[GridPos] = set()
        self.masks: set[Mask] = set()
        self.text: set[LevelText] = set()
        self.player: GridPos | None = None

        rows = [row.rstrip("\n") for row in level.strip("\n").splitlines()]

        for y, row in enumerate(rows):
            row, text_x, text = (row.split("_", 2) + [None, None])[:3]
            if text and text_x:
                self.text.add(LevelText(GridPos(int(text_x), y), text))
            for x, ch in enumerate(row):
                pos = GridPos(x, y)

                match ch:
                    case "#":  # wall
                        self.walls.add(pos)

                    case ".":  # goal
                        self.goals.add(pos)

                    case "$":  # box
                        self.boxes.add(pos)
                        self.floors.add(pos)

                    case "@":  # player
                        self.player = pos
                        self.floors.add(pos)

                    case "*":  # box on goal
                        self.boxes.add(pos)
                        self.goals.add(pos)

                    case "+":  # player on goal
                        self.player = pos
                        self.goals.add(pos)

                    case "P":  # push mask
                        self.floors.add(pos)
                        self.masks.add(Mask(pos, Power.PUSH))

                    case "B":  # break mask
                        self.floors.add(pos)
                        self.masks.add(Mask(pos, Power.BREAK))

                    case "I":  # Ignore mask
                        self.floors.add(pos)
                        self.masks.add(Mask(pos, Power.IGNORE))

                    case " ":  # floor
                        self.floors.add(pos)

    def is_wall(self, pos: GridPos) -> bool:
        return pos in self.walls

    def is_solved(self, boxes: list[Box]) -> bool:
        box_locations = set(b.grid_pos for b in boxes)
        for g in self.goals:
            if g not in box_locations:
                return False
        return True

    def draw(self, surface: pygame.Surface, camera: Camera2D) -> None:
        for floor in self.floors:
            rect = pygame.Rect(
                floor.x * TILE_SIZE,
                floor.y * TILE_SIZE,
                TILE_SIZE,
                TILE_SIZE,
            )

            # Scale the image to fit the tile
            scaled_image = pygame.transform.smoothscale(floor_normal, (TILE_SIZE, TILE_SIZE))

            # Draw the image
            camera.blit(surface, scaled_image, rect.topleft)

        for goal in self.goals:
            rect = pygame.Rect(
                goal.x * TILE_SIZE,
                goal.y * TILE_SIZE,
                TILE_SIZE,
                TILE_SIZE,
            )
            # Scale the image to fit the tile
            scaled_image = pygame.transform.smoothscale(floor_glow, (TILE_SIZE, TILE_SIZE))

            # Draw the image
            camera.blit(surface, scaled_image, rect.topleft)

        for text in self.text:
            text.draw(surface, camera)


class Power(Enum):
    NONE = 0
    PUSH = 1
    BREAK = 2
    IGNORE = 3

    def get_image(self) -> pygame.Surface:
        if self == Power.PUSH:
            return push_mask
        if self == Power.BREAK:
            return break_mask
        if self == Power.IGNORE:
            return ignore_mask
        raise ValueError(f"Power {self} not supported")


class Mask:
    def __init__(self, pos: GridPos, power: Power) -> None:
        self.pos: GridPos = pos
        self.power: Power = power
        self.rect = pygame.Rect(
            self.pos.x * TILE_SIZE + 15,
            self.pos.y * TILE_SIZE + 15,
            TILE_SIZE - 30,
            TILE_SIZE - 30,
        )

    def draw(self, surface: pygame.Surface, camera: Camera2D) -> None:

        image = self.power.get_image()

        img_w, img_h = image.get_size()

        # Scale while maintaining aspect ratio
        scale = min(
            self.rect.width / img_w,
            self.rect.height / img_h
        )

        new_size = (
            int(img_w * scale),
            int(img_h * scale),
        )

        scaled_image = pygame.transform.smoothscale(image, new_size)

        # Center the image in the target rect
        image_rect = scaled_image.get_rect(center=self.rect.center)

        camera.blit(surface, scaled_image, image_rect)


# ============================
# Box (Grid-aligned)
# ============================

class Box:
    SLIDE_SPEED = 1.5  # tiles per second

    def __init__(self, grid_pos: GridPos) -> None:
        self.grid_pos = grid_pos

        # Visual position (in pixels)
        self.pixel_pos = pygame.Vector2(
            grid_pos.x * TILE_SIZE,
            grid_pos.y * TILE_SIZE,
        )

        # Sliding state
        self.target_pixel_pos = self.pixel_pos.copy()
        self.sliding = False

    # --------------------------------------------------

    def try_push(self, direction: Vector2, level: Level, boxes: Iterable["Box"]) -> bool:
        dx = int(direction.x)
        dy = int(direction.y)
        target = GridPos(self.grid_pos.x + dx, self.grid_pos.y + dy)

        if level.is_wall(target):
            return False

        if self.sliding:
            return False

        if any(b.grid_pos == target for b in boxes):
            return False

        # Logical move
        self.grid_pos = target

        # Visual slide target
        self.target_pixel_pos = pygame.Vector2(
            target.x * TILE_SIZE,
            target.y * TILE_SIZE,
        )
        self.sliding = True
        push_sound.play()

        return True

    # --------------------------------------------------

    def update(self, dt: float) -> None:
        """
        dt = delta time in seconds
        """
        if not self.sliding:
            return

        direction = self.target_pixel_pos - self.pixel_pos
        distance = direction.length()

        if distance < 0.01:  # small tolerance
            self.pixel_pos = self.target_pixel_pos
            self.sliding = False
            return

        # Move by step, but do not overshoot
        move_dist = self.SLIDE_SPEED * TILE_SIZE * dt
        if move_dist >= distance:
            self.pixel_pos = self.target_pixel_pos
            self.sliding = False
        else:
            direction.normalize_ip()
            self.pixel_pos += direction * move_dist
    # --------------------------------------------------

    def draw(self, surface: pygame.Surface, transparency: float, glows: bool, camera: Camera2D) -> None:
        alpha = max(0, min(255, int(transparency * 255)))

        rect = pygame.Rect(
            int(self.pixel_pos.x),
            int(self.pixel_pos.y),
            TILE_SIZE,
            TILE_SIZE,
        )

        image = crystal_glow if glows else crystal_normal
        scaled_image = pygame.transform.smoothscale(image, rect.size)

        if alpha < 255:
            scaled_image = scaled_image.copy()
            scaled_image.set_alpha(alpha)

        camera.blit(surface, scaled_image, rect.topleft)


class ShatterAnimation:
    def __init__(self, pos: GridPos) -> None:
        self.pos: GridPos = pos
        self.start = time.time()
        self.step = 0

    def update(self) -> bool:
        if (time.time() - self.start) < 0.1:
            return True
        self.start = time.time()
        self.step += 1
        if self.step >= len(shatter):
            return False
        return True

    def draw(self, surface: pygame.Surface, camera: Camera2D) -> None:
        rect = pygame.Rect(
            self.pos.x * TILE_SIZE,
            self.pos.y * TILE_SIZE,
            TILE_SIZE,
            TILE_SIZE,
        )

        image = shatter[self.step]
        scaled_image = pygame.transform.smoothscale(image, rect.size)

        camera.blit(surface, scaled_image, rect.topleft)


# ============================
# Player (Fluid movement)
# ============================

class Player:
    def __init__(self, start_pos: Vector2) -> None:
        self.position: Vector2 = start_pos
        self.velocity: Vector2 = Vector2(0, 0)
        self.size: Vector2 = Vector2(TILE_SIZE * 0.3)
        self.abilities = {Power.NONE}
        self.current_ability = Power.NONE
        self.facing = None
        self.shatters = list()

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.position, self.size)

    def next_ability(self) -> None:
        for i in range(self.current_ability.value + 1, self.current_ability.value + 5):
            if Power(i % 4) in self.abilities:
                self.current_ability = Power(i % 4)
                return

    def update(
            self,
            dt: float,
            level: Level,
            boxes: List[Box],
            input_dir: Vector2,
    ) -> None:
        if input_dir.length_squared() > 0:
            self.facing = input_dir
            self.velocity = input_dir.normalize() * PLAYER_SPEED
        else:
            self.velocity = Vector2(0, 0)

        new_pos = self.position + self.velocity * dt
        future_rect = pygame.Rect(new_pos, self.size)

        # Wall collision (simple axis-aligned)
        for wall in level.walls:
            wall_rect = pygame.Rect(
                wall.x * TILE_SIZE,
                wall.y * TILE_SIZE,
                TILE_SIZE,
                TILE_SIZE,
            )
            if future_rect.colliderect(wall_rect):
                return

        if self.current_ability != Power.IGNORE:
            # Box pushing logic (grid-aligned)
            for box in boxes.copy():
                box_rect = pygame.Rect(
                    box.grid_pos.x * TILE_SIZE,
                    box.grid_pos.y * TILE_SIZE,
                    TILE_SIZE,
                    TILE_SIZE,
                )
                if box_rect.collidepoint(future_rect.center):
                    direction = Vector2(round(input_dir.x), round(input_dir.y))
                    if self.current_ability == Power.BREAK:
                        boxes.remove(box)
                        break_sound.play()
                        self.shatters.append(ShatterAnimation(box.grid_pos))
                        return
                    if self.current_ability != Power.PUSH:
                        return
                    if not box.try_push(direction, level, boxes):
                        return

        # Mask pickup
        for mask in level.masks.copy():
            mask_rect = mask.rect
            if future_rect.colliderect(mask_rect):
                self.abilities.add(mask.power)
                self.current_ability = mask.power
                mask_sounds[mask.power.value].play()
                level.masks.remove(mask)

        self.position = new_pos

    def draw(self, surface: pygame.Surface, time: int, camera: Camera2D) -> None:
        # Target area inside the tile
        target_rect = self.rect

        image = hero_down
        if self.facing:
            if self.facing[0] > 0:
                image = hero_right
            if self.facing[0] < 0:
                image = hero_left
            if self.facing[1] < 0:
                image = hero_up

        img_w, img_h = image.get_size()

        # Scale while maintaining aspect ratio
        scale = min(
            target_rect.width / img_w,
            target_rect.height / img_h
        )

        new_size = (
            4*int(img_w * scale),
            4*int(img_h * scale),
        )

        scaled_image = pygame.transform.smoothscale(image, new_size)

        # Center the image in the target rect
        image_rect = scaled_image.get_rect(center=target_rect.center)
        # Pulse parameters
        amplitude = 7  # pixels
        speed = 1.5  # cycles per second

        # Vertical pulsing using sine wave
        offset_y = amplitude * math.sin(2 * math.pi * speed * time)
        image_rect.y -= 40 + offset_y

        #pygame.draw.rect(surface, (0,0,0), camera.apply_rect(self.rect))
        pygame.draw.circle(surface, (0,0,0), camera.apply_rect(self.rect).center, self.rect.width // 2)
        camera.blit(surface, scaled_image, image_rect)

        for shatter in self.shatters.copy():
            if shatter.update():
                shatter.draw(surface, camera)
            else:
                self.shatters.remove(shatter)


class MusicManager:
    def __init__(self, volume=1.0, fade_ms=300):
        files = [
            resource_path("assets/music/main.ogg"),
            resource_path("assets/music/push.ogg"),
            resource_path("assets/music/break.ogg"),
            resource_path("assets/music/ignore.ogg")
        ]

        self.sounds = [pygame.mixer.Sound(f) for f in files]
        self.channels = [pygame.mixer.Channel(i) for i in range(len(files))]

        self.volume = volume
        self.fade_ms = fade_ms

        self.current = 0
        self.start_time = pygame.time.get_ticks() / 1000.0

        # Start ALL tracks at once, muted
        for ch, snd in zip(self.channels, self.sounds):
            ch.play(snd, loops=-1)
            ch.set_volume(0.0)

        # First track audible
        self.channels[0].set_volume(self.volume)
    # -------------------------------------

    def switch_to(self, index):
        if index == self.current:
            return

        old = self.channels[self.current]
        new = self.channels[index]

        old.set_volume(0)
        new.set_volume(self.volume)  # already playing → instant sync

        self.current = index

    # -------------------------------------

class Camera2D:
    def __init__(self, width: int, height: int, smooth_speed: float = 5.0):
        self.width = width
        self.height = height
        self.pos = pygame.Vector2(0, 0)
        self.smooth_speed = smooth_speed  # for smooth follow

    # ----------------------------

    def move(self, dx: float, dy: float) -> None:
        self.pos.x += dx
        self.pos.y += dy

    def set_pos(self, x: float, y: float) -> None:
        self.pos.x = x
        self.pos.y = y

    def follow(self, target_pos: pygame.Vector2, dt: float = 1.0) -> None:
        """Smoothly follow a target (e.g., player)"""
        target = pygame.Vector2(
            target_pos.x - self.width / 2,
            target_pos.y - self.height / 2
        )
        self.pos += (target - self.pos) * min(self.smooth_speed * dt, 1)

    # ----------------------------

    def apply(self, world_pos: pygame.Vector2) -> pygame.Vector2:
        return world_pos - self.pos

    def apply_rect(self, rect: pygame.Rect) -> pygame.Rect:
        return rect.move(-self.pos.x, -self.pos.y)

    # ----------------------------
    # NEW: blit wrapper
    # ----------------------------

    def blit(self, surface: pygame.Surface, image: pygame.Surface, world_pos, area=None) -> None:
        """
        Draw an image on the screen with camera offset.

        - world_pos: pygame.Vector2 or tuple (x, y) in world coordinates
        - area: optional pygame.Rect to blit a sub-rectangle of the image
        """
        if isinstance(world_pos, pygame.Vector2):
            screen_pos = self.apply(world_pos)
        else:
            screen_pos = (world_pos[0] - self.pos.x, world_pos[1] - self.pos.y)

        surface.blit(image, screen_pos, area)

# ============================
# Game
# ============================
WIN_EVENT = pygame.USEREVENT + 1

class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.display.set_caption("Maztek Spirit Warrior")



        self.camera = Camera2D(SCREEN_SIZE[0], SCREEN_SIZE[1])
        self.music  = None
        self.clock = pygame.time.Clock()
        self.level = None
        self.player = None
        self.boxes = None
        self.level_index = 0
        self.hud_area = None
        self.reset_area = None

        self.initialized = False  # Flag to track setup


    def restart_level(self) -> None:
        self.level = Level(all_levels[self.level_index])
        self.player = Player(self.level.player.to_world())
        self.boxes: List[Box] = [Box(b) for b in self.level.boxes]

    def draw_hud(
            self,
            slot_size: int = 70,
            padding: int = 10,
            bottom_margin: int = 20,
            highlight_color: tuple[int, int, int] = (255, 215, 0),
            highlight_width: int = 10,
            highlight_radius: int = 10,
            bg_color: tuple[int, int, int, int] = (50, 50, 50, 180),  # semi-transparent gray
            bg_radius: int = 16,
    ) -> None:
        """
        Draw the HUD with 4 slots and a semi-transparent background.
        slot_images: list of length 4 (None = empty slot)
        highlighted_index: index of the selected slot (0–3)
        """
        slot_images = [None, push_mask, break_mask, ignore_mask]
        assert len(slot_images) == 4

        # Compute HUD rectangle
        total_width = 4 * slot_size + 3 * padding
        hud_height = slot_size
        start_x = (SCREEN_SIZE[0] - total_width) // 2
        y = SCREEN_SIZE[1] - slot_size - bottom_margin

        hud_rect = pygame.Rect(start_x - padding, y - padding, total_width + 2 * padding, hud_height + 2 * padding)
        self.hud_area = hud_rect

        # --- Draw semi-transparent background ---
        bg_surf = pygame.Surface((hud_rect.width, hud_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(bg_surf, bg_color, bg_surf.get_rect(), border_radius=bg_radius)
        self.screen.blit(bg_surf, hud_rect.topleft)

        # --- Draw slots ---
        for i in range(4):
            slot_rect = pygame.Rect(
                start_x + i * (slot_size + padding),
                y,
                slot_size,
                slot_size,
            )

            # Highlighted slot
            if i == self.player.current_ability.value:
                pygame.draw.rect(
                    self.screen,
                    highlight_color,
                    slot_rect.inflate(6, 6),
                    highlight_width,
                    border_radius=highlight_radius,
                )

            image = slot_images[i]
            if image is None:
                continue

            # Scale image while preserving aspect ratio
            img_w, img_h = image.get_size()
            scale = min((slot_size - 12) / img_w, (slot_size - 12) / img_h)
            new_size = (int(img_w * scale), int(img_h * scale))
            scaled = pygame.transform.smoothscale(image, new_size)

            # Transparency for unavailable abilities
            alpha = 255 if Power(i) in self.player.abilities else 50
            if alpha < 255:
                scaled = scaled.copy()
                scaled.set_alpha(alpha)

            img_rect = scaled.get_rect(center=slot_rect.center)
            self.screen.blit(scaled, img_rect)

        # draw the reset button
        font = pygame.font.Font(None, 40)
        text = font.render("Reset Level", True, (120, 20, 20))

        # Center the text
        rect = text.get_rect(center=(100, SCREEN_SIZE[1] - 40))

        # --- Create a temporary surface for the rounded rectangle ---
        padding = 20  # space around the text
        radius = 16  # corner radius

        bg_surf = pygame.Surface(
            (rect.width + padding * 2, rect.height + padding * 2), pygame.SRCALPHA
        )
        bg_color = (150, 150, 150, 180)  # semi-transparent gray (A=180)
        pygame.draw.rect(bg_surf, bg_color, bg_surf.get_rect(), border_radius=radius)

        # --- Blit the background and then the text ---
        bg_rect = bg_surf.get_rect(center=rect.center)
        self.reset_area = bg_rect
        self.screen.blit(bg_surf, bg_rect.topleft)
        self.screen.blit(text, rect.topleft)


    def draw_you_won(self) -> None:
        font = pygame.font.Font(None, 64)
        text = font.render("Well done!", True, (20, 20, 20))

        # Center the text
        rect = text.get_rect(center=self.screen.get_rect().center)

        # --- Create a temporary surface for the rounded rectangle ---
        padding = 20  # space around the text
        radius = 16  # corner radius

        bg_surf = pygame.Surface(
            (rect.width + padding * 2, rect.height + padding * 2), pygame.SRCALPHA
        )
        bg_color = (150, 150, 150, 180)  # semi-transparent gray (A=180)
        pygame.draw.rect(bg_surf, bg_color, bg_surf.get_rect(), border_radius=radius)

        # --- Blit the background and then the text ---
        bg_rect = bg_surf.get_rect(center=rect.center)
        self.screen.blit(bg_surf, bg_rect.topleft)
        self.screen.blit(text, rect.topleft)

    def input_direction(self) -> Vector2:
        keys = pygame.key.get_pressed()
        direction = Vector2(
            keys[pygame.K_d] - keys[pygame.K_a],
            keys[pygame.K_s] - keys[pygame.K_w],
        )

        # Add touch/mouse input
        mouse_pressed = pygame.mouse.get_pressed()
        if mouse_pressed[0]:  # Left mouse button or touch
            x, y = pygame.mouse.get_pos()
            if not self.hud_area.collidepoint(x, y) and not self.reset_area.collidepoint(x, y):
                # Left side of the screen
                if x < SCREEN_SIZE[0] * 0.3:
                    direction.x -= 1
                # Right side of the screen
                elif x > SCREEN_SIZE[0] * 0.7:
                    direction.x += 1
                # Top of the screen
                if y < SCREEN_SIZE[1] * 0.5:
                    direction.y -= 1
                # Bottom of the screen
                elif y > SCREEN_SIZE[1] * 0.5:
                    direction.y += 1

        # Normalize to prevent faster diagonal movement
        if direction.length() > 0:
            direction = direction.normalize()

        return direction
    async def run(self) -> None:
        # DO ALL LOADING HERE INSTEAD OF __INIT__
        if not self.initialized:
            global background, floor_normal, floor_glow, crystal_normal, crystal_glow
            global hero_down, hero_up, hero_left, hero_right
            global break_mask, ignore_mask, push_mask
            global break_sound, push_sound, move_sound, shatter, mask_sounds

            background = pygame.image.load(resource_path("assets/background.png"))
            floor_normal = pygame.image.load(resource_path("assets/floor.png"))
            floor_glow = pygame.image.load(resource_path("assets/floor_glow.png"))
            crystal_normal = pygame.image.load(resource_path("assets/crystal_normal.png"))
            crystal_glow = pygame.image.load(resource_path("assets/crystal_glow.png"))
            await asyncio.sleep(0.1)
            break_mask = pygame.image.load(resource_path("assets/break_mask.png"))
            ignore_mask = pygame.image.load(resource_path("assets/ignore_mask.png"))
            push_mask = pygame.image.load(resource_path("assets/push_mask.png"))
            await asyncio.sleep(0.1)
            hero_down = pygame.image.load(resource_path("assets/hero_down.png"))
            hero_up = pygame.image.load(resource_path("assets/hero_up.png"))
            hero_left = pygame.image.load(resource_path("assets/hero_left.png"))
            hero_right = pygame.image.load(resource_path("assets/hero_right.png"))
            await asyncio.sleep(0.1)
            shatter = [
                pygame.image.load(resource_path("assets/shatter1.png")),
                pygame.image.load(resource_path("assets/shatter2.png")),
                pygame.image.load(resource_path("assets/shatter3.png"))
            ]

            pygame.mixer.init()

            break_sound = pygame.mixer.Sound(resource_path("assets/sound/break1.ogg"))
            push_sound = pygame.mixer.Sound(resource_path("assets/sound/push.ogg"))

            mask_sounds = [
                pygame.mixer.Sound(resource_path("assets/sound/noMask.ogg")),
                pygame.mixer.Sound(resource_path("assets/sound/greenMask.ogg")),
                pygame.mixer.Sound(resource_path("assets/sound/redMask.ogg")),
                pygame.mixer.Sound(resource_path("assets/sound/greyMask.ogg"))
            ]
            break_sound = pygame.mixer.Sound(resource_path("assets/sound/break1.ogg"))
            push_sound = pygame.mixer.Sound(resource_path("assets/sound/push.ogg"))

            self.music = MusicManager()
            self.camera = Camera2D(SCREEN_SIZE[0], SCREEN_SIZE[1])
            self.restart_level()
            self.initialized = True

        running = True
        win_state = False
        previous_ability = self.player.current_ability
        while running:
            dt = self.clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        if self.hud_area and self.hud_area.collidepoint(event.pos):
                            self.player.next_ability()
                        if self.reset_area and self.reset_area.collidepoint(event.pos):
                            self.restart_level()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.player.next_ability()
                    if event.key == pygame.K_r:
                        self.restart_level()
                if event.type == WIN_EVENT:
                    self.draw_you_won()
                    pygame.display.flip()
                    #pygame.time.delay(1000)
                    await asyncio.sleep(1.0)
                    self.level_index = (self.level_index + 1) % len(all_levels)
                    self.restart_level()
                    win_state = False


            self.player.update(dt, self.level, self.boxes, self.input_direction())
            self.camera.follow(self.player.position, dt)

            self.screen.blit(background, (0, 0))

            self.level.draw(self.screen, self.camera)
            for box in self.boxes:
                box.update(dt)
                transparency = 0.5 if self.player.current_ability == Power.IGNORE else 1
                glow = box.grid_pos in self.level.goals
                box.draw(self.screen, transparency, glow, self.camera)
            for mask in self.level.masks:
                mask.draw(self.screen, self.camera)
            self.player.draw(self.screen, pygame.time.get_ticks()/1000.0, self.camera)
            if not win_state and self.level.is_solved(self.boxes):
                win_state = True
                pygame.time.set_timer(WIN_EVENT, 1000, loops=1)
            self.draw_hud()
            if previous_ability != self.player.current_ability:
                previous_ability = self.player.current_ability
                self.music.switch_to(self.player.current_ability.value)

            pygame.display.flip()
            await asyncio.sleep(0)

        pygame.quit()


if __name__ == "__main__":
    asyncio.run(Game().run())
