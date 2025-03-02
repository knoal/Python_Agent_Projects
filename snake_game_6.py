import pygame
import random
import time
import os

# Initialize pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 600, 400
CELL_SIZE = 20

# Colors
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLACK = (0, 0, 0)
PURPLE = (128, 0, 128)

# Directions
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)

# Set up display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Self-Playing Snake Game with Obstacles")

clock = pygame.time.Clock()

# Font for score display
font = pygame.font.Font(None, 36)

HIGH_SCORE_FILE = "highscore.txt"


def load_high_score():
    """ Load the high score from a file or return 0 if file doesn't exist. """
    if os.path.exists(HIGH_SCORE_FILE):
        with open(HIGH_SCORE_FILE, "r") as file:
            return int(file.read().strip() or 0)
    return 0


def save_high_score(score):
    """ Save the high score to a file immediately when it's updated. """
    with open(HIGH_SCORE_FILE, "w") as file:
        file.write(str(score))


def random_position(exclude):
    """ Generate a random position avoiding the given exclude list. """
    while True:
        pos = (random.randint(0, (WIDTH // CELL_SIZE) - 1) * CELL_SIZE,
               random.randint(0, (HEIGHT // CELL_SIZE) - 1) * CELL_SIZE)
        if pos not in exclude:
            return pos


def get_valid_directions(snake, obstacles):
    """ Returns a list of valid directions the snake can move without hitting itself or an obstacle. """
    head_x, head_y = snake[0]
    possible_moves = []

    for move in [UP, DOWN, LEFT, RIGHT]:
        new_pos = (head_x + move[0] * CELL_SIZE, head_y + move[1] * CELL_SIZE)
        if (0 <= new_pos[0] < WIDTH and 0 <= new_pos[1] < HEIGHT and
                new_pos not in snake and new_pos not in obstacles):
            possible_moves.append(move)

    return possible_moves


def get_direction_to_food(snake, food, obstacles):
    """ AI determines the best move to reach food while avoiding obstacles. """
    valid_moves = get_valid_directions(snake, obstacles)

    if not valid_moves:
        return RIGHT  # If stuck, default to right

    head_x, head_y = snake[0]
    food_x, food_y = food

    # Prioritize moving toward food while avoiding obstacles
    best_move = None
    min_distance = float('inf')

    for move in valid_moves:
        new_x = head_x + move[0] * CELL_SIZE
        new_y = head_y + move[1] * CELL_SIZE
        distance = abs(food_x - new_x) + abs(food_y - new_y)

        if distance < min_distance:
            min_distance = distance
            best_move = move

    return best_move if best_move else random.choice(valid_moves)


def draw_score(score, high_score):
    """ Display the current score and high score on the screen. """
    score_text = font.render(f"Score: {score}", True, WHITE)
    high_score_text = font.render(f"High Score: {high_score}", True, WHITE)

    screen.blit(score_text, (10, 10))  # Score at top-left
    screen.blit(high_score_text, (WIDTH - 190, 10))  # High Score positioned left


def main():
    snake = [(WIDTH // 2, HEIGHT // 2)]
    direction = RIGHT
    fruit = random_position(snake)
    obstacles = []  # List to store obstacles
    last_obstacle_time = time.time()
    score = 0  # Initialize score
    high_score = load_high_score()

    running = True
    while running:
        screen.fill(BLACK)

        # AI controls the snake direction
        new_direction = get_direction_to_food(snake, fruit, obstacles)
        if new_direction:
            direction = new_direction

        # Move snake
        head_x, head_y = snake[0]
        new_head = (head_x + direction[0] * CELL_SIZE, head_y + direction[1] * CELL_SIZE)

        # Check for collisions with walls or itself
        if (new_head in snake or
                new_head[0] < 0 or new_head[0] >= WIDTH or
                new_head[1] < 0 or new_head[1] >= HEIGHT):
            running = False
            continue

        # Check if snake collides with an obstacle
        if new_head in obstacles:
            score = max(0, score - 3)  # Subtract 3 points, but keep score >= 0
            obstacles.remove(new_head)  # Remove the obstacle the snake hit

        # Move the snake forward
        snake.insert(0, new_head)

        # Check if snake eats the fruit
        if new_head == fruit:
            fruit = random_position(snake + obstacles)  # New food, avoid obstacles
            score += 5  # Increase score
            if score > high_score:  # If new high score, update it and save immediately
                high_score = score
                save_high_score(high_score)
        else:
            snake.pop()  # Remove the tail

        # Add obstacles every 2 seconds
        if time.time() - last_obstacle_time > 2:
            obstacles.append(random_position(snake + obstacles + [fruit]))
            last_obstacle_time = time.time()

        # Draw snake
        for segment in snake:
            pygame.draw.rect(screen, GREEN, (segment[0], segment[1], CELL_SIZE, CELL_SIZE))

        # Draw fruit
        pygame.draw.rect(screen, RED, (fruit[0], fruit[1], CELL_SIZE, CELL_SIZE))

        # Draw obstacles
        for obstacle in obstacles:
            pygame.draw.rect(screen, PURPLE, (obstacle[0], obstacle[1], CELL_SIZE, CELL_SIZE))

        # Display score and high score
        draw_score(score, high_score)

        pygame.display.flip()
        clock.tick(10)  # Adjust speed if needed

    pygame.quit()


if __name__ == "__main__":
    main()





