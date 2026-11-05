import pygame
from src.core.config import CYAN, MUTED, RED
from src.scenes.base import Scene, Message


class SettingsScene(Scene):
    def __init__(self, game, section='sound'):
        super().__init__(game)
        self.section = section
        self.rebuild()

    def rebuild(self):
        self.buttons = []
        for i, (label, section) in enumerate([('Звук', 'sound'), ('Управление', 'controls'), ('QTE / экран', 'qte'), ('Приватность', 'privacy')]):
            self.button(label, (44 + i * 300, 170, 280, 52), lambda section=section: self.tab(section))
        self.button('Назад [Esc]', (44, 634, 260, 50), self.game.scenes.pop)
        settings = self.game.settings
        if self.section == 'sound':
            from src.scenes.audio_settings import AudioDevices
            self.button('Аудио и устройства', (50, 550, 1100, 54), lambda:self.game.scenes.push(AudioDevices(self.game)))
            self.button('Тише −20%', (50, 370, 300, 54), lambda: self.volume(-20))
            self.button('Громче +20%', (370, 370, 300, 54), lambda: self.volume(20))
            self.button('Проверить звук', (690, 370, 300, 54), lambda: self.game.audio.play('click'))
        elif self.section == 'controls':
            self.button('Текст медленнее', (650, 540, 260, 48), lambda:self.change('text_speed',max(16,settings.text_speed-16)))
            self.button('Текст быстрее', (930, 540, 260, 48), lambda:self.change('text_speed',min(96,settings.text_speed+16)))
            for i, (name, value) in enumerate([('WASD + стрелки', 'both'), ('Только WASD', 'wasd'), ('Только стрелки', 'arrows')]):
                self.button(name + ('  [выбрано]' if settings.controls == value else ''), (50, 310 + i * 75, 550, 56),
                            lambda value=value: self.change('controls', value))
        elif self.section == 'qte':
            from src.scenes.stealth_settings import StealthSettings
            self.button('Стелс / чувствительность сенсоров',(650,480,550,48),lambda:self.game.scenes.push(StealthSettings(self.game)))
            modes = [('Стандарт: 3 секунды', 'standard'), ('Облегчённый: 6 секунд', 'easy'), ('Без таймера', 'untimed')]
            for i, (name, value) in enumerate(modes):
                self.button(name + ('  [выбрано]' if settings.qte_mode == value else ''), (50, 275 + i * 70, 560, 54),
                            lambda value=value: self.change('qte_mode', value))
            self.button('Проверить QTE в тренировке', (650, 275, 550, 54), lambda: self.game.scenes.push(QTEPractice(self.game)))
            self.button('Полный экран: ' + ('вкл' if settings.fullscreen else 'выкл'), (650, 345, 550, 54), self.fullscreen)
            self.button('Меньше анимации: ' + ('да' if settings.reduced_motion else 'нет'), (650, 415, 550, 54),
                        lambda: self.change('reduced_motion', not settings.reduced_motion))
        else:
            for i, (label, key) in enumerate([('Микрофон', 'microphone_consent'), ('Камера', 'camera_consent')]):
                state = 'согласие сохранено' if getattr(settings, key) else 'не разрешён'
                self.button(label + ': ' + state, (50, 360 + i * 80, 760, 56), lambda key=key: self.consent(key))

    def tab(self, section):
        self.section = section
        self.focus = -1
        self.rebuild()

    def change(self, key, value):
        self.game.set_setting(key, value)
        self.rebuild()

    def volume(self, amount):
        self.change('volume', max(0, min(100, self.game.settings.volume + amount)))

    def fullscreen(self):
        self.game.toggle_fullscreen()
        self.rebuild()

    def consent(self, key):
        if getattr(self.game.settings, key):
            self.change(key, False)
            return
        confirm = Message(self.game, 'Локальное согласие',
                          'Эта настройка сохраняет ваше предпочтение. Сенсор включается только после отдельного согласия перед попыткой. '
                          'Устройство сейчас не включается. Разрешение Windows не запрашивается. '
                          'Запись и отправка аудио или видео отсутствуют. Согласие можно отозвать в один клик.')
        def accept():
            self.change(key, True)
            self.game.scenes.pop()
        confirm.button('Сохранить согласие', (300, 622, 350, 52), accept)
        self.game.scenes.push(confirm)

    def draw(self, screen):
        self.header(screen, 'Настройки', 'Изменения применяются сразу и сохраняются локально. Esc — назад.')
        if self.section == 'sound':
            self.game.ui.pixel(screen, f'ОБЩАЯ ГРОМКОСТЬ: {self.game.settings.volume}%', (50, 275), 32, CYAN)
            pygame.draw.rect(screen, (32, 50, 66), (50, 330, 940, 12))
            pygame.draw.rect(screen, CYAN, (50, 330, int(9.4 * self.game.settings.volume), 12))
            self.game.ui.paragraph(screen, 'Музыка, дождь и эффекты; раздельные уровни и выбор устройств — ниже. ' +
                                  ('Аудиоустройство доступно.' if self.game.audio.available else 'Аудиоустройство недоступно: игра работает без звука.'), (50, 460, 1100, 80), 22, MUTED)
        elif self.section == 'controls':
            self.game.ui.text(screen, f'Скорость текста: {self.game.settings.text_speed} знаков/с', (650,490), 21, CYAN)
            self.game.ui.text(screen, 'Выберите схему движения. Изменения не затрагивают горячие клавиши.', (50, 260), 22)
            self.game.ui.paragraph(screen, 'Shift — быстрый шаг; E — взаимодействие; Tab — улики; M — карта; N — N.U.R.S.; Esc — пауза. В меню: стрелки вверх/вниз и Enter.', (650, 315, 540, 200), 23, MUTED)
        elif self.section == 'qte':
            self.game.ui.paragraph(screen, 'Режим применяется к QTE, включая погоню. Ошибка сюжетного QTE отнимает 35 здоровья. Без таймера можно спокойно выполнить те же действия. «Меньше анимации» отключает дождь и появление окон.', (50, 545, 1140, 65), 21, MUTED)
        else:
            self.game.ui.paragraph(screen, 'Vosk и OpenCV включаются добровольно в N.U.R.S. и у охранника метро. Здесь сохраняются только предпочтения; перед каждой попыткой запрашивается отдельное согласие. Нет записи и отправки данных.', (50, 265, 1130, 90), 23, MUTED)
            self.game.ui.text(screen, 'Расследование доступно без обоих устройств.', (50, 550), 24, CYAN)
        self.draw_buttons(screen)


class LoadScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.rows = []
        for i, (key, label) in enumerate([('auto', 'Автосохранение'), ('manual', 'Ручной слот'), ('checkpoint', 'Контрольная точка')]):
            try:
                state = game.save_manager(key).load()
                info = f'День {state.current_day} / {game.worlds[state.location]["title"]} / улики: {len(state.evidence_ids)}'
                enabled = True
            except FileNotFoundError:
                info, enabled = 'Слот пуст', False
            except (OSError, ValueError):
                info, enabled = 'Файл повреждён или недоступен; остальные слоты сохранены', False
            self.rows.append((label, info))
            self.button('Загрузить', (970, 190 + i * 126, 230, 55), lambda key=key: game.load(key), enabled)
        self.button('Назад [Esc]', (44, 634, 260, 50), game.scenes.pop)

    def draw(self, screen):
        self.header(screen, 'Загрузить расследование', 'Выберите слот. Загрузка заменяет текущий несохранённый прогресс.')
        for i, (label, info) in enumerate(self.rows):
            y = 175 + i * 126
            self.game.ui.panel(screen, (44, y, 1188, 108), MUTED)
            self.game.ui.pixel(screen, label, (64, y + 15), 26, CYAN)
            self.game.ui.text(screen, info, (64, y + 61), 20, MUTED)
        self.draw_buttons(screen)


class AdditionalCases(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.button('Назад [Esc]', (44, 634, 260, 50), game.scenes.pop)
        self.cases = [('Дело 02 / Эхо архива', 'Следы исчезнувшего городского реестра. Предварительная идея, сценарий не утверждён.'),
                      ('Дело 03 / Последний рейс', 'Ночное расследование на транспортном узле Астеры. Предварительная идея.')]

    def draw(self, screen):
        self.header(screen, 'Дополнительные дела', 'Демонстрационный каталог. DLC ещё не разработаны. Покупок и платежей нет.')
        for i, (title, description) in enumerate(self.cases):
            x = 50 + i * 600
            self.game.ui.panel(screen, (x, 190, 570, 330), MUTED)
            self.game.ui.pixel(screen, 'ДОСТУП ЗАКРЫТ', (x + 22, 215), 26, RED)
            self.game.ui.text(screen, title, (x + 22, 270), 27)
            self.game.ui.paragraph(screen, description, (x + 22, 325, 525, 110), 22, MUTED)
            self.game.ui.text(screen, 'ЗАБЛОКИРОВАНО / не выпущено', (x + 22, 465), 22, MUTED)
        self.game.ui.paragraph(screen, 'Модель: бесплатная демоверсия → полная ПК-версия ориентировочно за 5,99 USD → самостоятельные расследования DLC. Цена — гипотеза; магазин и даты релиза отсутствуют.', (50, 545, 1140, 80), 21)
        self.draw_buttons(screen)


class QTEPractice(Scene):
    """Isolated accessibility exercise, never awards story evidence or changes health."""
    def __init__(self, game):
        super().__init__(game)
        self.button('Назад', (44, 634, 260, 50), game.scenes.pop)
        self.button('Повторить', (330, 634, 260, 50), self.reset)
        self.reset()

    def reset(self):
        self.elapsed = 0.0
        self.index = 0
        self.result = ''
        self.sequence = [pygame.K_a, pygame.K_d, pygame.K_SPACE]
        self.limit = {'standard': 3.0, 'easy': 6.0, 'untimed': None}[self.game.settings.qte_mode]

    def event(self, event):
        super().event(event)
        if event.type == pygame.KEYDOWN and not self.result and event.key == self.sequence[self.index]:
            self.index += 1
            self.game.audio.play('click')
            if self.index == len(self.sequence):
                self.result = 'Успех. Действие выполнено.'

    def update(self, dt):
        if not self.result:
            self.elapsed += dt
            if self.limit is not None and self.elapsed >= self.limit:
                self.result = 'Время вышло. Повторите или выберите режим без таймера.'

    def draw(self, screen):
        self.header(screen, 'Тренировка QTE', 'Изолированный тест управления: здоровье и материалы расследования не меняются.')
        label = self.result or f'Нажмите: {("A", "D", "SPACE")[self.index]}'
        self.game.ui.pixel(screen, label, (50, 270), 28, CYAN)
        self.game.ui.text(screen, f'Выполнено {self.index}/3', (50, 350), 25)
        timer = 'Без ограничения времени' if self.limit is None else f'Осталось: {max(0, self.limit - self.elapsed):.1f} с'
        self.game.ui.text(screen, timer, (50, 410), 25, MUTED)
        self.draw_buttons(screen)
