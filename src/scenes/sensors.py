"""Pygame adapters for engine-independent local sensor modules."""
import time
import pygame
from src.scenes.base import Scene, Message
from src.core.config import CYAN, MUTED, RED
from src.ai.devices import SensorSession
from src.ai.signals import CalmTrial, SilenceTrial


class SensorConsent(Message):
    def __init__(self, game, kind, accepted):
        name = 'камеру' if kind == 'camera' else 'микрофон'
        super().__init__(game, 'Разрешить ' + name + ' для этой попытки?',
                         'Обработка только на этом ПК. Аудио и видео не записываются и не отправляются. '
                         'Во время работы виден индикатор. Esc или «Отключить» прекращает захват. '
                         'Можно отказаться и пройти тот же эпизод кнопками. Камера измеряет наличие лица и движение, '
                         'а не эмоции, ложь или психологическое состояние.')
        def accept():
            game.scenes.pop()  # Remove consent before opening device; settings never auto-start it.
            accepted()
        self.button('Разрешить только эту попытку', (300, 622, 620, 52), accept)


class SensorChallenge(Scene):
    def __init__(self, game, kind):
        super().__init__(game)
        self.kind = kind
        self.session = SensorSession()
        self.mode = ''
        self.trial = None
        self.message = 'Выберите локальный сенсор или равноценный кнопочный режим.'
        self.level = -90.0
        self.motion = 0.0
        self.present = False
        self.reliable = False
        self.manual_until = 0.0
        self.manual_clock = 0.0
        self.last_sample = time.monotonic()
        self.calibration = []
        self.calibration_time = 0.0
        self.rebuild()

    def rebuild(self):
        self.buttons = []
        self.button('Назад [Esc]', (44, 640, 270, 48), self.game.scenes.pop)
        if not self.mode:
            self.button('Включить камеру' if self.kind == 'calm' else 'Включить микрофон', (50, 455, 540, 55), self.request_sensor)
            self.button('Кнопочный режим', (640, 455, 540, 55), self.start_manual)
        else:
            self.button('Отключить / остановить', (50, 550, 540, 55), self.cancel)
            if self.mode == 'manual':
                self.button('Сохранять спокойствие [Space]' if self.kind == 'calm' else 'Идти тихо [Space]',
                            (640, 550, 540, 55), self.pulse)

    def request_sensor(self):
        self.game.scenes.push(SensorConsent(self.game, 'camera' if self.kind == 'calm' else 'microphone', self.start_sensor))

    def reset_trial(self):
        self.trial = CalmTrial() if self.kind == 'calm' else SilenceTrial()
        self.manual_clock = self.manual_until = 0.0

    def start_manual(self):
        self.session.close()
        self.reset_trial()
        self.mode = 'manual'
        self.message = 'Нажимайте Space или кнопку не реже раза в 2 секунды в течение 12 секунд. Сенсор выключен.'
        self.rebuild()

    def start_sensor(self):
        self.reset_trial()
        self.calibration, self.calibration_time = [], 0.0
        try:
            self.session.start('camera' if self.kind == 'calm' else 'noise', consent=True,
                               device_key=self.game.settings.microphone_device, gain=self.game.settings.microphone_gain)
            self.mode = 'sensor'
            self.last_sample = time.monotonic()
            self.message = 'Подключение… Затем 12 секунд. Для микрофона сначала 2 секунды тишины для калибровки.'
        except Exception as exc:
            self.mode = ''
            self.message = 'Сенсор недоступен: ' + str(exc) + '. Выберите кнопочный режим.'
        self.rebuild()

    def on_exit(self):
        self.session.close()
        self.mode = ''

    def on_cover(self):
        if self.mode:
            self.cancel()

    def cancel(self):
        self.on_exit()
        self.message = 'Попытка остановлена без последствий. Устройство выключено; можно начать кнопочный режим.'
        self.rebuild()

    def pulse(self):
        self.manual_until = self.manual_clock + 2.0

    def event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and self.mode == 'manual':
            self.pulse()
            return
        super().event(event)

    def finish(self, success):
        self.on_exit()
        # Numeric outcomes only; never evidence or identity flags from a face/noise signal.
        if self.kind == 'calm':
            self.game.state.statistics['guard_shortcut'] = int(success)
            self.game.state.statistics['guard_attempts'] = self.game.state.statistics.get('guard_attempts', 0) + 1
            self.message = ('Охранник прекращает провокации: доступна короткая реплика «Пройти к журналу».' if success else
                            'Проверка не пройдена. Вернитесь к охраннику и объясните цель визита или предъявите дело 2020.')
        else:
            self.game.state.statistics['stealth_quiet'] = int(success)
            self.game.state.statistics['stealth_attempts'] = self.game.state.statistics.get('stealth_attempts', 0) + 1
            self.message = ('Вы прошли незамеченным: охранник сразу предложит журнал.' if success else
                            'Шум замечен. Охранник потребует дополнительное объяснение; улика не потеряна.')
        self.game.save()
        self.rebuild()

    def sample(self, event):
        dt = min(.25, max(0, event['dt']))
        if self.kind == 'silence':
            self.level = event['db']
            if self.calibration_time < 2:
                self.calibration.append(self.level)
                self.calibration_time += dt
                if self.calibration_time >= 2:
                    floor = sorted(self.calibration)[len(self.calibration) // 2]
                    self.trial.threshold = min(-18, max(-50, floor + 12))
                    self.message = f'Калибровка завершена. Порог {self.trial.threshold:.0f} dBFS. Сохраняйте тишину 12 секунд.'
                return
        else:
            self.present, self.motion = event['present'], event['motion']
            self.reliable = event['reliable']
            self.message = 'Одно лицо и оба глаза в кадре; избегайте резких перемещений. Это игровой сигнал.'

    def update(self, dt):
        if self.mode == 'manual':
            self.manual_clock += dt
            pressed = self.manual_clock <= self.manual_until
            if self.kind == 'calm':
                result = self.trial.step(dt, pressed, pressed, 0 if pressed else 1)
            else:
                self.level = -60 if pressed else -10
                result = self.trial.step(dt, self.level)
            if result is not None:
                self.finish(result)
        elif self.mode == 'sensor':
            for event in self.session.poll():
                if event['type'] == 'active':
                    self.last_sample = time.monotonic()
                elif event['type'] == 'sample':
                    now = time.monotonic()
                    if now - event.get('at', now) > .8:
                        continue  # stale frames never count as successful presence
                    self.last_sample = now
                    self.sample(event)
                    if not self.mode:
                        break
                elif event['type'] in ('error', 'stopped'):
                    self.cancel()
                    self.message = event.get('message', 'Поток остановлен') + '. Доступен кнопочный режим.'
                    break
            if self.mode == 'sensor' and self.session.active:
                fresh = time.monotonic() - self.last_sample <= .5 and dt <= .5
                result = None
                if self.kind == 'calm':
                    result = self.trial.step(dt, self.present and fresh, self.reliable and fresh, self.motion)
                elif self.calibration_time >= 2:
                    result = self.trial.step(dt, self.level if fresh else 0)
                if result is not None:
                    self.finish(result)
            if self.mode == 'sensor' and self.session.active and time.monotonic() - self.last_sample > 3:
                self.cancel()
                self.message = 'Нет свежих данных сенсора. Попытка отменена, выберите ручной режим.'

    def draw(self, screen):
        self.header(screen, 'Охранник / сохранять спокойствие' if self.kind == 'calm' else 'Метро / пройти незамеченным',
                    'Локальная обработка · нет записи · одинаковый сюжетный доступ без устройств')
        active = self.session.active
        indicator = ('КАМЕРА ВКЛЮЧЕНА' if self.kind == 'calm' else 'МИКРОФОН ВКЛЮЧЁН') if active else 'СЕНСОР ВЫКЛЮЧЕН'
        self.game.ui.pixel(screen, indicator, (50, 180), 26, RED if active else CYAN)
        self.game.ui.paragraph(screen, self.message, (50, 235, 1140, 105), 24)
        if self.trial:
            elapsed = self.trial.elapsed
            if self.kind == 'calm':
                detail = 'кнопочный режим' if self.mode == 'manual' else ('лицо в кадре: ' + ('да' if self.present else 'нет'))
                label = f'Время {elapsed:.1f}/12 с · стабильные сигналы {self.trial.good:.1f} с · {detail}'
                progress = self.trial.good / 12
            else:
                label = f'Время {elapsed:.1f}/12 с · шум {self.level:.0f} dBFS · порог {self.trial.threshold:.0f} · опасность {self.trial.danger:.0%}'
                progress = self.trial.danger
            self.game.ui.text(screen, label, (50, 365), 22, CYAN)
            pygame.draw.rect(screen, MUTED, (50, 410, 1130, 16))
            pygame.draw.rect(screen, CYAN, (50, 410, round(1130 * min(1, progress)), 16))
        self.draw_buttons(screen)


class GuardDialogue(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.message = 'Охранник: «Уверен, что тебе сюда? Объясни свой интерес к журналу». Можно пройти проверку или ответить обычной репликой.'
        self.rebuild()

    def rebuild(self):
        self.buttons = []
        stats = self.game.state.statistics
        short = stats.get('guard_shortcut', 0) or stats.get('stealth_quiet', 0)
        self.button('Сохранять спокойствие — 12 секунд', (50, 350, 1130, 50), lambda: self.challenge('calm'))
        self.button('Пройти незамеченным — тишина', (50, 410, 1130, 50), lambda: self.challenge('silence'))
        self.button('Пройти к журналу' if short else 'Объяснить цель визита', (50, 470, 1130, 50), lambda: self.answer(bool(short)))
        self.button('Предъявить дело 2020', (50, 530, 1130, 50), lambda: self.grant(), 'archive' in self.game.state.evidence_ids)
        self.button('Назад [Esc]', (50, 640, 300, 48), self.game.scenes.pop)

    def challenge(self, kind):
        self.game.scenes.push(SensorChallenge(self.game, kind))

    def answer(self, short):
        if short or self.game.state.statistics.get('guard_explained', 0):
            self.grant()
        else:
            self.game.state.statistics['guard_explained'] = 1
            self.game.save()
            self.message = 'Никита объясняет: «Проверяю маршрут Нурланова, не обвиняю без оснований». Охранник: «Хорошо, подтвердите запрос ещё раз — покажу журнал».'

    def grant(self):
        if not self.game.state.statistics.get('guard_access'):
            self.game.state.trust['guard'] = min(100, self.game.state.trust.get('guard', 50) + 10)
            self.game.toast('Запрос обоснован: доверие охранника +10.')
        self.game.evidence.collect('transit')
        self.game.state.statistics['guard_access'] = 1
        self.game.save()
        self.message = 'Охранник открыл журнал проходов. Запись добавлена в материалы дела; повторное получение не даёт очков.'

    def event(self, event):
        self.rebuild()
        super().event(event)

    def draw(self, screen):
        self.header(screen, 'Метро / Айдос', 'Успех сенсора сокращает диалог. Обычная реплика даёт ту же улику.')
        self.game.art.portrait(screen,'guard',(50,185))
        self.game.ui.paragraph(screen, self.message, (250, 190, 930, 140), 25)
        self.rebuild()
        self.draw_buttons(screen)
