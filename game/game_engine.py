import pygame
import random
from .player import Player
from .enemy import EnemyGrid
from .bullet import Bullet

# Game Engine

WHITE = (255, 255, 255)
GREEN = (0, 200, 0)
RED = (220, 60, 60)
GRAY = (180, 180, 180)

# Enemy speed (pixels per frame) and per-enemy fire chance (per frame) for each difficulty.
# "Medium" matches the original game values.
DIFFICULTIES = {
    "Easy":   {"speed": 1.0, "fire_chance": 0.005},
    "Medium": {"speed": 1.5, "fire_chance": 0.01},
    "Hard":   {"speed": 2.5, "fire_chance": 0.02},
}

# Keys on the game-over screen that start a new game
DIFFICULTY_KEYS = {
    pygame.K_1: "Easy",
    pygame.K_KP1: "Easy",
    pygame.K_2: "Medium",
    pygame.K_KP2: "Medium",
    pygame.K_3: "Hard",
    pygame.K_KP3: "Hard",
}

QUIT_KEYS = (pygame.K_q, pygame.K_ESCAPE)

class GameEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.font = pygame.font.SysFont("Arial", 30)
        self.title_font = pygame.font.SysFont("Arial", 64, bold=True)

        # Reused every frame for the dimmed game-over background
        self._overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 180))

        self._reset("Medium")

    def _reset(self, difficulty):
        """Rebuild all game state from scratch using the chosen difficulty."""
        settings = DIFFICULTIES[difficulty]
        self.difficulty = difficulty

        self.player = Player(self.width // 2 - 20, self.height - 50, 40, 20)
        self.enemy_grid = EnemyGrid(self.width, speed=settings["speed"])

        self.player_bullets = []
        self.enemy_bullets = []
        self._shoot_cooldown = 0
        self.enemy_fire_chance = settings["fire_chance"]

        self.score = 0
        self.game_over = False

    def handle_event(self, event):
        if self.game_over:
            # 1/2/3 restart at that difficulty; Q or Esc closes the game by posting a QUIT event.
            # Space is intentionally ignored so rapid fire doesn't skip the screen.
            if event.type == pygame.KEYDOWN:
                if event.key in DIFFICULTY_KEYS:
                    self._reset(DIFFICULTY_KEYS[event.key])
                elif event.key in QUIT_KEYS:
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            if self._shoot_cooldown <= 0:
                bullet_x = self.player.center_x() - 2
                self.player_bullets.append(Bullet(bullet_x, self.player.y, direction=-1))
                self._shoot_cooldown = 15

    def handle_input(self):
        if self.game_over:
            return

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.player.move(-self.player.speed, self.width)
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.player.move(self.player.speed, self.width)

    def _find_hit_enemy(self, bullet):
        """Return the front-most alive enemy the bullet touched this frame, or None."""
        path = bullet.swept_rect()
        hit = None
        for enemy in self.enemy_grid.alive_enemies():
            if path.colliderect(enemy.rect()):
                # Player bullets travel up, so the enemy with the lowest bottom edge is hit first.
                if hit is None or (enemy.y + enemy.height) > (hit.y + hit.height):
                    hit = enemy
        return hit

    def update(self):
        if self.game_over:
            return

        if self._shoot_cooldown > 0:
            self._shoot_cooldown -= 1

        self.enemy_grid.move()

        for enemy in self.enemy_grid.alive_enemies():
            if random.random() < self.enemy_fire_chance:
                bullet_x = enemy.x + enemy.width // 2
                self.enemy_bullets.append(Bullet(bullet_x, enemy.y + enemy.height, direction=1))

        for bullet in self.player_bullets:
            bullet.move()
        for bullet in self.enemy_bullets:
            bullet.move()

        # Collisions run BEFORE off-screen pruning so bullets at the edge still count.
        # Build a new list of surviving bullets rather than removing from the list
        # being iterated (which caused bullets to be skipped).
        surviving_bullets = []
        for bullet in self.player_bullets:
            enemy = self._find_hit_enemy(bullet)
            if enemy is not None:
                enemy.alive = False
                self.score += 1
            else:
                surviving_bullets.append(bullet)
        self.player_bullets = surviving_bullets

        for bullet in self.enemy_bullets:
            if bullet.rect().colliderect(self.player.rect()):
                self.game_over = True
                break

        self.player_bullets = [b for b in self.player_bullets if not b.off_screen(self.height)]
        self.enemy_bullets = [b for b in self.enemy_bullets if not b.off_screen(self.height)]

        if self.enemy_grid.reached_bottom(self.player.y):
            self.game_over = True

    def _draw_centered(self, screen, font, text, color, center_y):
        surface = font.render(text, True, color)
        rect = surface.get_rect(center=(self.width // 2, center_y))
        screen.blit(surface, rect)

    def _render_game_over(self, screen):
        screen.blit(self._overlay, (0, 0))
        mid = self.height // 2
        self._draw_centered(screen, self.title_font, "GAME OVER", RED, mid - 90)
        self._draw_centered(screen, self.font, f"Final Score: {self.score}", WHITE, mid - 20)
        self._draw_centered(screen, self.font, "Play again:", GRAY, mid + 40)
        self._draw_centered(screen, self.font, "1 - Easy", WHITE, mid + 80)
        self._draw_centered(screen, self.font, "2 - Medium", WHITE, mid + 115)
        self._draw_centered(screen, self.font, "3 - Hard", WHITE, mid + 150)
        self._draw_centered(screen, self.font, "Q / ESC - Exit", GRAY, mid + 205)

    def render(self, screen):
        pygame.draw.rect(screen, GREEN, self.player.rect())

        for enemy in self.enemy_grid.alive_enemies():
            pygame.draw.rect(screen, WHITE, enemy.rect())

        for bullet in self.player_bullets:
            pygame.draw.rect(screen, WHITE, bullet.rect())
        for bullet in self.enemy_bullets:
            pygame.draw.rect(screen, RED, bullet.rect())

        score_text = self.font.render(f"Score: {self.score}", True, WHITE)
        screen.blit(score_text, (10, 10))

        if self.game_over:
            self._render_game_over(screen)