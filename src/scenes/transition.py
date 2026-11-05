import pygame
from src.core.config import SIZE
from src.scenes.base import Scene


class FadeTransition(Scene):
    """Freeze both scenes until the fade finishes; movement cannot leak through."""
    def __init__(self, game, destination, commit):
        super().__init__(game)
        self.age = 0
        self.destination, self.commit = destination, commit
        self.before = pygame.Surface(SIZE)
        game.scenes.current.draw(self.before)

    def event(self, event):
        pass

    def update(self, dt):
        self.age += dt
        if self.age >= 0.44:
            self.game.scenes.pop()
            self.commit()
            self.game.fade_scene, self.game.fade_age = self.game.scenes.current, 1.0

    def draw(self, screen):
        if self.age < 0.22:
            screen.blit(self.before, (0, 0))
            alpha = self.age / 0.22
        else:
            self.destination.draw(screen)
            alpha = 1 - (self.age - 0.22) / 0.22
        veil = pygame.Surface(SIZE)
        veil.fill((0, 0, 0))
        veil.set_alpha(round(max(0, min(1, alpha)) * 255))
        screen.blit(veil, (0, 0))
