import pygame
import sys

# Initialize Pygame
pygame.init()

# Set up display
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Infinite Chess AI")

# Clock to control framerate
clock = pygame.time.Clock()

# Game loop
running = True
while running:
    clock.tick(60)  # 60 FPS
    
    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Fill screen with color (RGB)
    screen.fill((30, 30, 30))  # dark gray background
        
    # Update display
    pygame.display.flip()

# Quit
pygame.quit()
sys.exit() 
