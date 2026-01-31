from __future__ import annotations

import math
import time
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List

import pygame
from pygame.math import Vector2

from levels import all_levels

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

break_mask = pygame.image.load("assets/break_mask.png")
ignore_mask = pygame.image.load("assets/ignore_mask.png")
push_mask = pygame.image.load("assets/push_mask.png")
floor_normal = pygame.image.load("assets/floor.png")
floor_glow = pygame.image.load("assets/floor_glow.png")
crystal_normal = pygame.image.load("assets/crystal_normal.png")
crystal_glow = pygame.image.load("assets/crystal_glow.png")
background = pygame.image.load("assets/background.jpg")
hero_down = pygame.image.load("assets/hero_down.png")
hero_up = pygame.image.load("assets/hero_up.png")
hero_left = pygame.image.load("assets/hero_left.png")
hero_right = pygame.image.load("assets/hero_right.png")

# ============================
# Grid Utilities
# ============================

@dataclass(frozen=True, slots=True)
class GridPos:
    x: int
    y: int

    def to_world(self) -> Vector2:
        return Vector2(self.x * TILE_SIZE, self.y * TILE_SIZE)


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


class Level:
    def __init__(self, level: str) -> None:
        self.walls: set[GridPos] = set()
        self.goals: set[GridPos] = set()
        self.floors: set[GridPos] = set()
        self.boxes: set[GridPos] = set()
        self.masks: set[Mask] = set()
        self.player: GridPos | None = None

        rows = [row.rstrip("\n") for row in level.strip("\n").splitlines()]

        for y, row in enumerate(rows):
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

    def draw(self, surface: pygame.Surface) -> None:
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
            surface.blit(scaled_image, rect.topleft)
        # for wall in self.walls:
        #     rect = pygame.Rect(
        #         wall.x * TILE_SIZE,
        #         wall.y * TILE_SIZE,
        #         TILE_SIZE,
        #         TILE_SIZE,
        #     )
        #     pygame.draw.rect(surface, DARK_GRAY, rect)
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
            surface.blit(scaled_image, rect.topleft)


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

    def draw(self, surface: pygame.Surface) -> None:

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

        surface.blit(scaled_image, image_rect)


# ============================
# Box (Grid-aligned)
# ============================

class Box:
    def __init__(self, grid_pos: GridPos) -> None:
        self.grid_pos = grid_pos

    def try_push(self, direction: Vector2, level: Level, boxes: Iterable[Box]) -> bool:
        dx = int(direction.x)
        dy = int(direction.y)
        target = GridPos(self.grid_pos.x + dx, self.grid_pos.y + dy)

        if level.is_wall(target):
            return False

        if any(b.grid_pos == target for b in boxes):
            return False

        self.grid_pos = target
        return True

    def draw(self, surface: pygame.Surface, transparency: float, glows: bool) -> None:
        alpha = max(0, min(255, int(transparency * 255)))

        # Target rectangle for the tile
        rect = pygame.Rect(
            self.grid_pos.x * TILE_SIZE,
            self.grid_pos.y * TILE_SIZE,
            TILE_SIZE,
            TILE_SIZE,
        )

        image = crystal_glow if glows else crystal_normal
        # Scale the image to fit the tile
        scaled_image = pygame.transform.smoothscale(image, (rect.width, rect.height))

        # Apply transparency if needed
        if alpha < 255:
            scaled_image = scaled_image.copy()  # don't modify original
            scaled_image.set_alpha(alpha)

        # Draw the image
        surface.blit(scaled_image, rect.topleft)


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
                if future_rect.colliderect(box_rect):
                    direction = Vector2(round(input_dir.x), round(input_dir.y))
                    if self.current_ability == Power.BREAK:
                        boxes.remove(box)
                        return
                    if self.current_ability != Power.PUSH:
                        return
                    if not box.try_push(direction, level, boxes):
                        return

        # Max pickup
        for mask in level.masks.copy():
            mask_rect = mask.rect
            if future_rect.colliderect(mask_rect):
                self.abilities.add(mask.power)
                self.current_ability = mask.power
                level.masks.remove(mask)

        self.position = new_pos

    def draw(self, surface: pygame.Surface, time: int) -> None:
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

        pygame.draw.rect(surface, BLUE, self.rect)
        surface.blit(scaled_image, image_rect)

class MusicManager:
    def __init__(self, volume=1.0):
        pygame.mixer.init()
        """
        tracks: list of file paths (length 4)
        loop_start_ms: millisecond position to loop from
        """
        self.tracks = [
            "assets/music/main.ogg",
            "assets/music/push.ogg",
            "assets/music/break.ogg",
            "assets/music/ignore.ogg"
        ]
        self.loop_start = 23.429
        self.volume = volume

        self.current_index = 0
        self.start_ticks = pygame.time.get_ticks()
        self.paused_time = 0.0

        pygame.mixer.music.set_volume(self.volume)
        self._play_track(0, start_pos=0.0)

    # -----------------------------------------------------

    def _play_track(self, index, start_pos):
        print(start_pos)
        pygame.mixer.music.load(self.tracks[index])
        pygame.mixer.music.play(loops=0, start=start_pos)
        self.start_ticks = pygame.time.get_ticks() - int(start_pos * 1000)
        self.current_index = index

    # -----------------------------------------------------

    def get_play_time(self):
        """Return current playback time in seconds"""
        elapsed_ms = pygame.time.get_ticks() - self.start_ticks
        return elapsed_ms / 1000.0

    # -----------------------------------------------------

    def switch_to(self, index, fade_ms=300):
        """Switch to another track, preserving play time"""
        if index == self.current_index:
            return

        play_time = self.get_play_time()
        pygame.mixer.music.fadeout(fade_ms)

        # Start new track at same time (wrapped later if needed)
        pygame.time.delay(fade_ms)
        self._play_track(index, start_pos=play_time)

    # -----------------------------------------------------

    def update(self):
        """Call every frame to handle looping"""
        if not pygame.mixer.music.get_busy():
            # Restart from loop_start, keeping sync
            print("music looping now")
            self._play_track(self.current_index, self.loop_start)

# ============================
# Game
# ============================


class Game:
    def __init__(self) -> None:
        pygame.init()
        self.music = MusicManager()


        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.display.set_caption("Maztek Spirit Warrior")
        self.clock = pygame.time.Clock()
        self.level = None
        self.player = None
        self.boxes = None
        self.level_index = 0
        self.restart_level()


    def restart_level(self) -> None:
        self.level = Level(all_levels[self.level_index])
        self.player = Player(self.level.player.to_world())
        self.boxes: List[Box] = [Box(b) for b in self.level.boxes]

    def draw_hud(self,
                 slot_size: int = 70,
                 padding: int = 10,
                 bottom_margin: int = 20,
                 highlight_color: tuple[int, int, int] = (255, 215, 0),
                 highlight_width: int = 10,
                 highlight_radius: int = 10,
                 ) -> None:
        """
        slot_images: list of length 4 (None = empty slot)
        highlighted_index: index of the selected slot (0–3)
        """
        slot_images = [None, push_mask, break_mask, ignore_mask]

        assert len(slot_images) == 4

        total_width = 4 * slot_size + 3 * padding
        start_x = (SCREEN_SIZE[0] - total_width) // 2
        y = SCREEN_SIZE[1] - slot_size - bottom_margin

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
            scale = min(
                (slot_size - 12) / img_w,
                (slot_size - 12) / img_h,
            )

            new_size = (int(img_w * scale), int(img_h * scale))
            scaled = pygame.transform.smoothscale(image, new_size)

            alpha = 255 if Power(i) in self.player.abilities else 50

            # Apply transparency (copy so original image is not modified)
            if alpha < 255:
                scaled = scaled.copy()
                scaled.set_alpha(alpha)

            img_rect = scaled.get_rect(center=slot_rect.center)
            self.screen.blit(scaled, img_rect)

    def draw_you_won(self) -> None:
        font = pygame.font.Font(None, 64)
        text = font.render("You won", True, (20, 20, 20))

        rect = text.get_rect(center=self.screen.get_rect().center)
        self.screen.blit(text, rect)

    def input_direction(self) -> Vector2:
        keys = pygame.key.get_pressed()
        return Vector2(
            keys[pygame.K_d] - keys[pygame.K_a],
            keys[pygame.K_s] - keys[pygame.K_w],
        )

    def run(self) -> None:
        running = True
        previous_ability = self.player.current_ability
        while running:
            dt = self.clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.player.next_ability()
            if pygame.key.get_pressed()[pygame.K_r]:
                self.restart_level()

            self.player.update(dt, self.level, self.boxes, self.input_direction())

            self.screen.fill(WHITE)
            self.screen.blit(background, (0, 0))

            self.level.draw(self.screen)
            for box in self.boxes:
                transparency = 0.5 if self.player.current_ability == Power.IGNORE else 1
                glow = box.grid_pos in self.level.goals
                box.draw(self.screen, transparency, glow)
            for mask in self.level.masks:
                mask.draw(self.screen)
            self.player.draw(self.screen, time.time_ns()/1000000000)
            if self.level.is_solved(self.boxes):
                self.draw_you_won()
                self.level_index = (self.level_index + 1) % len(all_levels)
                self.restart_level()
            self.draw_hud()
            if previous_ability != self.player.current_ability:
                previous_ability = self.player.current_ability
                self.music.switch_to(self.player.current_ability.value)

            self.music.update()

            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    Game().run()
