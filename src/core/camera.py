import math
import pygame


class Camera:
    def __init__(self, world_size, viewport=(1280, 720)):
        self.world_size = world_size
        self.viewport = viewport
        self.offset = pygame.Vector2()

    def update(self, target, dt, snap=False):
        goal = pygame.Vector2(*(max(0, min(target[i] - self.viewport[i] / 2,
                                          self.world_size[i] - self.viewport[i])) for i in range(2)))
        self.offset += (goal - self.offset) * (1 if snap else 1 - math.exp(-7 * dt))

    def apply(self, rect):
        return rect.move(-round(self.offset.x), -round(self.offset.y))
