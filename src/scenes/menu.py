import pygame
from src.core.config import BG, CYAN, RED, MUTED
from src.scenes.base import Scene, Message


def city_background(screen, age, reduced=False):
    city = pygame.Surface((640, 360))
    city.fill(BG)
    for i in range(25):
        x, height = i * 28, 45 + (i * 47) % 160
        pygame.draw.rect(city, (17 + i % 3 * 4, 29, 45), (x, 340 - height, 26, height))
        for y in range(348 - height, 330, 14):
            for xx in (x + 5, x + 17):
                pygame.draw.rect(city, (43, 99, 119) if (i + y) % 3 else (143, 45, 61), (xx, y, 3, 4))
    pygame.draw.rect(city, (19, 33, 46), (0, 340, 640, 20))
    for i in range(75):
        tick = 0 if reduced else age * 50
        x, y = (i * 97 - tick * 0.4) % 640, (i * 53 + tick * 1.7) % 360
        pygame.draw.line(city, (47, 82, 105), (int(x), int(y)), (int(x - 3), int(y + 11)))
    screen.blit(pygame.transform.scale(city, (1280, 720)), (0, 0))


class Splash(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.age = 0

    def event(self, event):
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            self.game.audio.play('click')
            self.game.scenes.replace(Menu(self.game))

    def update(self, dt):
        self.age += dt

    def draw(self, screen):
        city_background(screen, self.age, self.game.settings.reduced_motion)
        self.game.ui.pixel(screen, 'ASTERA / 2035', (480, 80), 30, CYAN)
        self.game.ui.pixel(screen, 'BLOODY', (350, 160), 112)
        self.game.ui.pixel(screen, 'TRAIL', (470, 275), 112, RED)
        self.game.ui.text(screen, 'Правда всегда оставляет след', (385, 425), 30)
        self.game.ui.panel(screen, (390, 576, 500, 64))
        self.game.ui.pixel(screen, 'Нажмите любую клавишу', (438, 594), 28, CYAN)


class Menu(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.age = 0
        from src.scenes.settings import SettingsScene, LoadScene, AdditionalCases
        entries = [('Новая игра', self.new, True), ('Продолжить', game.load, game.saves.path.exists()),
                   ('Загрузить', lambda: game.scenes.push(LoadScene(game)), True),
                   ('Настройки', lambda: game.scenes.push(SettingsScene(game)), True),
                   ('Дополнительные дела', lambda: game.scenes.push(AdditionalCases(game)), True),
                   ('Выход', game.quit, True)]
        for i, (label, callback, enabled) in enumerate(entries):
            self.button(label, (72, 267 + i * 62, 390, 50), callback, enabled)

        from src.scenes.prologue import Prologue
        self.button('Воспоминания / 2020', (700, 225, 490, 44), lambda: game.scenes.push(Prologue(game, replay=True)))
        from src.scenes.campaign import FullVersion, Leaderboard
        self.button('Полная версия / доступ', (700, 610, 490, 44), lambda: game.scenes.push(FullVersion(game)))
        self.button('Таблица результатов', (700, 664, 490, 44), lambda: game.scenes.push(Leaderboard(game)))

    def new(self):
        if self.game.saves.path.exists():
            self.game.scenes.push(ConfirmNew(self.game))
        else:
            self.game.new_game()

    def update(self, dt):
        self.age += dt

    def draw(self, screen):
        city_background(screen, self.age, self.game.settings.reduced_motion)
        self.game.ui.pixel(screen, 'BLOODY TRAIL', (64, 78), 62)
        self.game.ui.text(screen, 'Правда всегда оставляет след', (72, 157), 24, CYAN)
        self.game.ui.text(screen, 'Полная история открыта · Day 1–3' if self.game.access.full_version_unlocked else 'Демоверсия · Day 1 / полная история — справа', (72, 210), 20, MUTED)
        self.game.art.portrait(screen, 'nikita', (755, 310))
        self.game.art.portrait(screen, 'nurs', (985, 310))
        self.game.ui.text(screen, 'ТРИ ДНЯ. ПЯТНАДЦАТЬ ЛЕТ МОЛЧАНИЯ.', (680, 565), 22)
        self.game.ui.text(screen, 'Мышь или ↑ / ↓ и Enter', (74, 666), 18, MUTED)
        self.draw_buttons(screen)


class ConfirmNew(Message):
    def __init__(self, game):
        super().__init__(game, 'Новое расследование', 'Автосохранение и контрольная точка будут заменены. Ручной слот сохранится. Продолжить?')
        self.button('Начать заново', (300, 622, 260, 52), game.new_game)


class Pause(Scene):
    def __init__(self, game):
        super().__init__(game)
        from src.scenes.settings import SettingsScene, LoadScene
        entries = [('Продолжить', game.scenes.pop), ('Сохранить', game.manual_save),
                   ('Загрузить', lambda: game.scenes.push(LoadScene(game))),
                   ('Настройки звука', lambda: game.scenes.push(SettingsScene(game, 'sound'))),
                   ('Настройки управления', lambda: game.scenes.push(SettingsScene(game, 'controls'))),
                   ('Полноэкранный режим', game.toggle_fullscreen),
                   ('Доступность QTE', lambda: game.scenes.push(SettingsScene(game, 'qte'))),
                   ('Разрешение микрофона', lambda: game.scenes.push(SettingsScene(game, 'privacy'))),
                   ('Разрешение камеры', lambda: game.scenes.push(SettingsScene(game, 'privacy'))),
                   ('Главное меню', self.menu), ('Отказаться от дела…', self.withdraw),
                   ('Ресурсы / достижения', self.status)]
        for i, (label, action) in enumerate(entries):
            self.button(label, (50 + (i % 2) * 610, 185 + (i // 2) * 72, 560, 56), action)

    def status(self):
        from src.scenes.campaign import CaseStatus
        self.game.scenes.push(CaseStatus(self.game))

    def menu(self):
        if self.game.save():
            self.game.to_menu()

    def withdraw(self):
        confirm = Message(self.game, 'Передать дело комиссии?', 'Никита отказывается от расследования. Это поражение. Контрольная точка останется доступна.')
        confirm.button('Подтвердить отказ', (300, 622, 300, 52), lambda: self.game.fail('withdraw'))
        self.game.scenes.push(confirm)

    def draw(self, screen):
        self.header(screen, 'Пауза / расследование остановлено', 'Время прохождения не идёт. Esc — вернуться к игре. F11 — полноэкранный режим.')
        self.draw_buttons(screen)
