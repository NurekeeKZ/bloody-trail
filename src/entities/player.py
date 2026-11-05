import pygame


class Player:
    SPEED = 180

    def __init__(self, position):
        self.position = pygame.Vector2(position)
        self.rect = pygame.Rect(0, 0, 24, 18)
        self.rect.center = self.position
        self.moving = False
        self.facing = 1
        self.animation = 0.0

    def move(self, direction, dt, walls, fast=False):
        direction = pygame.Vector2(direction)
        self.moving = direction.length_squared() > 0
        if self.moving:
            direction = direction.normalize()
            if direction.x:
                self.facing = 1 if direction.x > 0 else -1
        distance = direction * self.SPEED * (1.65 if fast else 1) * dt
        # Small steps prevent tunnelling, including low frame rates / sprint.
        steps = max(1, int(max(abs(distance.x), abs(distance.y)) / 5) + 1)
        for _ in range(steps):
            for axis in (0, 1):
                delta = distance[axis] / steps
                self.position[axis] += delta
                self.rect.center = round(self.position.x), round(self.position.y)
                for wall in walls:
                    if self.rect.colliderect(wall):
                        if axis == 0:
                            if delta > 0: self.rect.right = wall.left
                            elif delta < 0: self.rect.left = wall.right
                            self.position.x = self.rect.centerx
                        else:
                            if delta > 0: self.rect.bottom = wall.top
                            elif delta < 0: self.rect.top = wall.bottom
                            self.position.y = self.rect.centery
        self.animation += dt
