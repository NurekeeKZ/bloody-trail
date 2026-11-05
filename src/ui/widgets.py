import pygame
from src.core.config import PANEL, CYAN, INK, MUTED


class UI:
    def __init__(self):
        self.fonts = {}

    def font(self, size):
        if size not in self.fonts:
            self.fonts[size] = pygame.font.SysFont('tahoma,dejavusans,arial', size)
        return self.fonts[size]

    def text(self, surface, text, pos, size=22, color=INK):
        surface.blit(self.font(size).render(str(text), True, color), pos)

    def pixel(self, surface, text, pos, size=32, color=INK):
        # Cyrillic-capable raster lettering at half resolution, scaled without filtering.
        glyphs = self.font(max(8, size // 2)).render(str(text), False, color)
        surface.blit(pygame.transform.scale(glyphs, (glyphs.get_width() * 2, glyphs.get_height() * 2)), pos)

    def paragraph(self, surface, text, rect, size=22, color=INK):
        x, y, width, height = rect
        line = ''
        for word in str(text).split():
            candidate = (line + ' ' + word).strip()
            if self.font(size).size(candidate)[0] > width and line:
                self.text(surface, line, (x, y), size, color)
                y += size + 9
                line = word
            else:
                line = candidate
        if line:
            self.text(surface, line, (x, y), size, color)
        return y + size + 9

    def panel(self, surface, rect, border=CYAN):
        pygame.draw.rect(surface, PANEL, rect)
        pygame.draw.rect(surface, border, rect, 1)

    def button(self, surface, label, rect, mouse, enabled=True):
        rect = pygame.Rect(rect)
        hover = rect.collidepoint(mouse) and enabled
        pygame.draw.rect(surface, (30, 58, 73) if hover else PANEL, rect)
        pygame.draw.rect(surface, CYAN if enabled else MUTED, rect, 2 if hover else 1)
        size = 21
        while size > 14 and self.font(size).size(label)[0] > rect.w - 32:
            size -= 1
        self.text(surface, label, (rect.x + 16, rect.y + (rect.h - self.font(size).get_height()) // 2), size, INK if enabled else MUTED)


class Typewriter:
    def __init__(self, text):
        self.text, self.age = text, 0.0

    def update(self, dt):
        self.age += dt

    def finish(self):
        self.age = len(self.text)

    @property
    def visible(self):
        return self.text[:int(self.age * 48)]
