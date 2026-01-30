from __future__ import annotations

import pygame
from pygame.math import Vector2
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

# ============================
# Config / Constants
# ============================

TILE_SIZE: int = 64
SCREEN_SIZE: tuple[int, int] = (800, 600)
PLAYER_SPEED: float = 220.0  # pixels / second

Color = tuple[int, int, int]

WHITE: Color = (255, 255, 255)
GRAY: Color = (160, 160, 160)
DARK_GRAY: Color = (60, 60, 60)
BLUE: Color = (80, 140, 255)
BROWN: Color = (160, 110, 60)


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


# # = wall, @ = player, + = player on goal, $ = box, * = box on goal, . = goal, ' ' = floor
level_str: str = """
######
#.@ ##
# #  #
#$#  #
#    #
######
"""


class Level:
    def __init__(self, level: str) -> None:
        self.walls: set[GridPos] = set()
        self.goals: set[GridPos] = set()
        self.boxes: set[GridPos] = set()
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

                    case "@":  # player
                        self.player = pos

                    case "*":  # box on goal
                        self.boxes.add(pos)
                        self.goals.add(pos)

                    case "+":  # player on goal
                        self.player = pos
                        self.goals.add(pos)

                    case " ":  # floor
                        pass

    def is_wall(self, pos: GridPos) -> bool:
        return pos in self.walls

    def is_solved(self, boxes: list[Box]) -> bool:
        box_locations = set(b.grid_pos for b in boxes)
        for g in self.goals:
            if g not in box_locations:
                return False
        return True

    def draw(self, surface: pygame.Surface) -> None:
        for wall in self.walls:
            rect = pygame.Rect(
                wall.x * TILE_SIZE,
                wall.y * TILE_SIZE,
                TILE_SIZE,
                TILE_SIZE,
            )
            pygame.draw.rect(surface, DARK_GRAY, rect)
        for goal in self.goals:
            center = (
                goal.x * TILE_SIZE + TILE_SIZE // 2,
                goal.y * TILE_SIZE + TILE_SIZE // 2,
            )
            radius = TILE_SIZE // 4
            pygame.draw.circle(surface, DARK_GRAY, center, radius)


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

    def draw(self, surface: pygame.Surface) -> None:
        rect = pygame.Rect(
            self.grid_pos.x * TILE_SIZE,
            self.grid_pos.y * TILE_SIZE,
            TILE_SIZE,
            TILE_SIZE,
        )
        pygame.draw.rect(surface, BROWN, rect)


# ============================
# Player (Fluid movement)
# ============================

class Player:
    def __init__(self, start_pos: Vector2) -> None:
        self.position: Vector2 = start_pos
        self.velocity: Vector2 = Vector2(0, 0)
        self.size: Vector2 = Vector2(TILE_SIZE * 0.7)
        self.can_push = True
        self.can_break = False
        self.can_pull = False
        self.can_teleport = False

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.position, self.size)

    def update(
            self,
            dt: float,
            level: Level,
            boxes: List[Box],
            input_dir: Vector2,
    ) -> None:
        if input_dir.length_squared() > 0:
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

        # Box pushing logic (grid-aligned)
        for box in boxes:
            box_rect = pygame.Rect(
                box.grid_pos.x * TILE_SIZE,
                box.grid_pos.y * TILE_SIZE,
                TILE_SIZE,
                TILE_SIZE,
            )
            if future_rect.colliderect(box_rect):
                direction = Vector2(round(input_dir.x), round(input_dir.y))
                if not self.can_push:
                    return
                if not box.try_push(direction, level, boxes):
                    return

        self.position = new_pos

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, BLUE, self.rect)


# ============================
# Game
# ============================


class Game:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.display.set_caption("The Masked Warehouseperson")
        self.clock = pygame.time.Clock()

        self.level = Level(level_str)

        self.player = Player(self.level.player.to_world())
        self.boxes: List[Box] = [Box(b) for b in self.level.boxes]

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
        while running:
            dt = self.clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            self.player.update(dt, self.level, self.boxes, self.input_direction())

            self.screen.fill(WHITE)
            self.level.draw(self.screen)
            for box in self.boxes:
                box.draw(self.screen)
            self.player.draw(self.screen)
            if self.level.is_solved(self.boxes):
                self.draw_you_won()

            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    Game().run()
