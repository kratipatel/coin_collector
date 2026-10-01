"""
GameEngine: owns the player, coins, obstacles, lives and the round timer.
"""

import random
import pygame

from game.player import Player
from game.coin import Coin
from game.collection import check_collection
from game.renderer import WIDTH, HEIGHT

NUM_COINS = 6
NUM_OBSTACLES = 5
START_LIVES = 3
INVULN_MS = 1000      # invulnerability after a hit, in milliseconds
ROUND_SECONDS = 30    # length of a round

# (name, value, color, spawn weight)
COIN_TYPES = [
    ("bronze", 1, (205, 127, 50), 60),
    ("silver", 3, (192, 192, 192), 30),
    ("gold",   5, (255, 215, 0),   10),
]


class GameEngine:
    def __init__(self):
        self.reset()

    def reset(self):
        """Start a fresh round: score, lives, timer, coins and obstacles."""
        self.player = Player(x=WIDTH / 2, y=HEIGHT / 2)
        self.obstacles = self._make_obstacles()
        self.coins = [self._random_coin() for _ in range(NUM_COINS)]
        self.score = 0
        self.lives = START_LIVES
        self.invulnerable_until = 0
        self.game_over = False
        self.end_reason = ""
        self.round_start = pygame.time.get_ticks()
        self.time_left = float(ROUND_SECONDS)

    def _make_obstacles(self):
        # keep the area around the player's start position clear
        safe_zone = pygame.Rect(0, 0, 200, 200)
        safe_zone.center = (WIDTH // 2, HEIGHT // 2)
        obstacles = []
        while len(obstacles) < NUM_OBSTACLES:
            w = random.randint(40, 90)
            h = random.randint(30, 70)
            x = random.randint(0, WIDTH - w)
            y = random.randint(40, HEIGHT - h)  # y >= 40 keeps the HUD readable
            rect = pygame.Rect(x, y, w, h)
            if rect.colliderect(safe_zone):
                continue
            if any(rect.colliderect(o.inflate(20, 20)) for o in obstacles):
                continue
            obstacles.append(rect)
        return obstacles

    def _random_coin(self):
        while True:
            x = random.randint(30, WIDTH - 30)
            y = random.randint(30, HEIGHT - 30)
            name, value, color, _ = random.choices(
                COIN_TYPES, weights=[t[3] for t in COIN_TYPES]
            )[0]
            coin = Coin(x=x, y=y, radius=12, value=value, color=color)
            # don't spawn a coin inside an obstacle
            if not any(coin.get_rect().colliderect(o) for o in self.obstacles):
                return coin

    def handle_input(self, keys_pressed):
        if self.game_over:
            return
        dx = dy = 0
        if keys_pressed[pygame.K_UP]:
            dy -= self.player.speed
        if keys_pressed[pygame.K_DOWN]:
            dy += self.player.speed
        if keys_pressed[pygame.K_LEFT]:
            dx -= self.player.speed
        if keys_pressed[pygame.K_RIGHT]:
            dx += self.player.speed
        self.player.move(dx, dy, WIDTH, HEIGHT)

    def update(self):
        if self.game_over:
            return

        now = pygame.time.get_ticks()

        # timer
        elapsed = (now - self.round_start) / 1000
        self.time_left = max(0.0, ROUND_SECONDS - elapsed)
        if self.time_left <= 0:
            self.game_over = True
            self.end_reason = "TIME'S UP!"
            return

        # coins: collected exactly once, then replaced
        collected = check_collection(self.player, self.coins)
        for coin in collected:
            self.score += coin.value
            self.coins.remove(coin)
            self.coins.append(self._random_coin())

        # obstacles: lose one life per hit, then a short invulnerability window
        if now >= self.invulnerable_until:
            player_rect = self.player.get_rect()
            if any(player_rect.colliderect(o) for o in self.obstacles):
                self.lives -= 1
                self.invulnerable_until = now + INVULN_MS
                if self.lives <= 0:
                    self.game_over = True
                    self.end_reason = "OUT OF LIVES!"

    def draw(self, surface, font):
        from game import renderer
        now = pygame.time.get_ticks()
        # blink the player while invulnerable
        blinking = (not self.game_over
                    and now < self.invulnerable_until
                    and (now // 100) % 2 == 0)
        renderer.draw_scene(surface, self.player, self.coins,
                            self.obstacles, show_player=not blinking)

        # HUD
        renderer.draw_text(surface, font, f"Score: {self.score}", (10, 10))
        renderer.draw_text(surface, font, f"Time: {int(self.time_left) + (1 if self.time_left % 1 else 0)}",
                           (WIDTH // 2 - 45, 10))
        renderer.draw_text(surface, font, f"Lives: {self.lives}", (WIDTH - 130, 10))

        # game over screen
        if self.game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            surface.blit(overlay, (0, 0))

            cx, cy = WIDTH // 2, HEIGHT // 2
            lines = [
                (self.end_reason, (255, 220, 80), -50),
                (f"Final Score: {self.score}", (255, 255, 255), 0),
                ("Press R to play again", (180, 220, 255), 50),
            ]
            for text, color, offset in lines:
                surf = font.render(text, True, color)
                surface.blit(surf, surf.get_rect(center=(cx, cy + offset)))