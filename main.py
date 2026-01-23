import pygame
import random
import sys

# Initialize pygame
pygame.init()

# Window setup
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Green Square Game")

clock = pygame.time.Clock()

# Colors
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)

# Player
player_size = 40
player_x = WIDTH // 2
player_y = HEIGHT // 2
player_speed = 5
player_rect = pygame.Rect(player_x, player_y, player_size, player_size)

# Red squares (obstacles)
obstacle_size = 40
num_obstacles = 8
obstacles = []

for _ in range(num_obstacles):
    x = random.randint(0, WIDTH - obstacle_size)
    y = random.randint(0, HEIGHT - obstacle_size)
    obstacles.append(pygame.Rect(x, y, obstacle_size, obstacle_size))

# Game loop
running = True
while running:
    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Movement input
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        player_rect.x -= player_speed
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        player_rect.x += player_speed
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        player_rect.y -= player_speed
    if keys[pygame.K_DOWN] or keys[pygame.K_s]:
        player_rect.y += player_speed

    # Keep player inside the screen
    player_rect.clamp_ip(screen.get_rect())

    # Collision detection
    for obstacle in obstacles:
        if player_rect.colliderect(obstacle):
            # Reset player to center if hit
            player_rect.center = (WIDTH // 2, HEIGHT // 2)

    # Drawing
    screen.fill(BLACK)

    # Draw obstacles
    for obstacle in obstacles:
        pygame.draw.rect(screen, RED, obstacle)

    # Draw player
    pygame.draw.rect(screen, GREEN, player_rect)

    pygame.display.flip()

# Quit
pygame.quit()
sys.exit()
