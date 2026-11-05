import pygame
from src.core.config import BG, CYAN, MUTED


class Scene:
    def __init__(self, game):
        self.game = game
        self.buttons = []
        self.focus = -1
        self.hovered = -1

    def feedback(self):
        hovered = next((i for i, (_, rect, _, enabled) in enumerate(self.buttons)
                        if enabled and rect.collidepoint(self.game.mouse)), -1)
        if hovered != self.hovered and hovered >= 0:
            self.game.audio.play('hover')
        self.hovered = hovered

    def activate(self, index):
        if 0 <= index < len(self.buttons) and self.buttons[index][3]:
            self.game.audio.play('click')
            self.buttons[index][2]()

    def button(self, label, rect, callback, enabled=True):
        self.buttons.append((label, pygame.Rect(rect), callback, enabled))

    def event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index, (_, rect, action, enabled) in enumerate(list(self.buttons)):
                if enabled and rect.collidepoint(event.pos):
                    self.activate(index)
                    return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_UP, pygame.K_DOWN):
            enabled = [i for i, button in enumerate(self.buttons) if button[3]]
            if enabled:
                current = enabled.index(self.focus) if self.focus in enabled else (-1 if event.key == pygame.K_DOWN else 0)
                self.focus = enabled[(current + (1 if event.key == pygame.K_DOWN else -1)) % len(enabled)]
                self.game.audio.play('hover')
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and self.focus >= 0:
            self.activate(self.focus)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.scenes.pop()

    def update(self, dt):
        pass

    def draw_buttons(self, screen):
        self.feedback()
        for index, (label, rect, _, enabled) in enumerate(self.buttons):
            self.game.ui.button(screen, label, rect, self.game.mouse, enabled)
            if index == self.focus and enabled:
                pygame.draw.rect(screen, CYAN, rect.inflate(6, 6), 1)

    def header(self, screen, title, subtitle=''):
        screen.fill(BG)
        self.game.ui.pixel(screen, 'BLOODY / TRAIL', (44, 26), 22, CYAN)
        self.game.ui.text(screen, title, (44, 72), 37)
        self.game.ui.text(screen, subtitle, (46, 124), 20, MUTED)


class Message(Scene):
    def __init__(self, game, title, text):
        super().__init__(game)
        self.title, self.text = title, text
        self.button('Назад', (48, 622, 220, 52), game.scenes.pop)

    def draw(self, screen):
        self.header(screen, self.title)
        self.game.ui.paragraph(screen, self.text, (50, 196, 1120, 400), 24)
        self.draw_buttons(screen)
