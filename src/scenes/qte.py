"""First playable story challenge, separate from the harmless settings practice."""
import pygame
from src.core.config import CYAN, MUTED, RED
from src.scenes.base import Scene
from src.systems.stealth_system import QTESystem


class StoryQTE(Scene):
    DAMAGE = 35

    def __init__(self, game, episode='door'):
        super().__init__(game)
        self.episode = episode
        self.phase = 'ready'
        self.index = 0
        self.elapsed = 0.0
        self.sequence = (pygame.K_a, pygame.K_d, pygame.K_SPACE)
        self.limit = {'standard': 3.0, 'easy': 6.0, 'untimed': None}[game.settings.qte_mode]
        self.reason = ''
        self.engine=QTESystem({'type':'sequence','keys':['a','d','space']},game.settings.qte_mode)
        self.rebuild()

    def rebuild(self):
        self.buttons = []
        if self.phase == 'ready':
            self.button('Начать испытание', (50, 590, 400, 56), self.start)
            self.button('Отложить поездку', (480, 590, 400, 56), self.game.scenes.pop)
        elif self.phase == 'running':
            self.button('Пауза [Esc]', (50, 590, 400, 56), self.pause)
        elif self.phase == 'paused':
            self.button('Продолжить', (50, 590, 400, 56), self.resume)
        elif self.phase == 'failed':
            self.button('Повторить попытку', (50, 590, 400, 56), self.start)
            self.button('Помощь дежурного: −10 репутации', (480, 590, 690, 56), self.assisted_entry)
            if self.game.state.statistics.get('qte_failures', 0) >= 2 and self.limit is not None and self.limit < 6:
                self.button('N.U.R.S.: увеличить таймер до 6 с', (50, 650, 1120, 44), self.adapt)

    def adapt(self):
        if self.game.set_setting('qte_mode', 'easy'):
            self.limit = 6.0
            self.rebuild()

    def complete(self):
        return self.game.complete_archive() if self.episode == 'archive' else self.game.complete_entry()

    def start(self):
        if self.phase not in ('ready', 'failed'):
            return
        self.phase, self.elapsed, self.index, self.reason = 'running', 0.0, 0, ''
        self.engine=QTESystem({'type':'sequence','keys':['a','d','space']},self.game.settings.qte_mode)
        self.engine.limit=float('inf') if self.limit is None else self.limit
        self.rebuild()

    def pause(self):
        if self.phase == 'running':
            self.phase = 'paused'
            self.rebuild()

    def resume(self):
        if self.phase == 'paused':
            self.phase = 'running'
            self.rebuild()

    def fail_attempt(self, reason):
        if self.phase != 'running':
            return
        self.phase, self.reason = 'failed', reason
        self.game.state.statistics['qte_failures'] = self.game.state.statistics.get('qte_failures', 0) + 1
        self.game.state.health = max(0, self.game.state.health - self.DAMAGE)
        if self.game.state.health == 0:
            self.game.fail('health')
        else:
            if not self.game.spend_time(1, 'Повторная подготовка после ошибки QTE'): return
            self.game.save()  # Never overwrite the pre-challenge checkpoint.
            self.rebuild()

    def assisted_entry(self):
        if self.phase != 'failed':
            return
        self.phase = 'complete'
        self.game.state.reputation = max(0, self.game.state.reputation - 10)
        self.game.toast('Помощь дежурного: репутация −10.')
        self.complete()

    def event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.phase == 'ready':
                self.game.scenes.pop()
            elif self.phase == 'running':
                self.pause()
            elif self.phase == 'paused':
                self.resume()
            return
        if event.type == pygame.KEYDOWN and self.phase == 'running':
            if event.key in self.sequence:
                before=self.index
                self.engine.key(pygame.key.name(event.key),True)
                if self.engine.result is False:self.fail_attempt('Неверная клавиша: створка соскользнула.')
                else:
                    self.index=self.engine.presses
                    if self.index>before:self.game.audio.play('click')
                    if self.engine.result is True:
                        self.phase='complete';self.complete()
                return
        if event.type==pygame.KEYUP:self.engine.key(pygame.key.name(event.key),False)
        super().event(event)

    def update(self, dt):
        if self.phase == 'running':
            self.engine.elapsed=self.elapsed
            self.engine.update(dt);self.elapsed=self.engine.elapsed
            if self.engine.result is False:
                self.fail_attempt('Время вышло: заклинившая створка ударила Никиту.')

    def draw(self, screen):
        self.header(screen, 'Архив Сигма / аварийная выгрузка' if self.episode == 'archive' else 'Квартира Нурланова / заклинившая дверь', 'Сюжетный QTE · контрольная точка сохранена перед испытанием')
        instructions = ('Питание архива отключается. Переключите питание, подтвердите копирование и удержите соединение: A → D → Space. Ошибка: −35 здоровья и −1 час на восстановление. Улики не теряются.' if self.episode == 'archive' else
                        'Повреждённый доводчик удерживает вход. Подхватите створку, отведите фиксатор '
                               'и удержите дверь: A → D → Space. Ошибка или таймаут: −35 здоровья. '
                               'При нуле Никита не сможет продолжать расследование.')
        self.game.ui.paragraph(screen, instructions, (50, 180, 1140, 110), 23)
        labels = ('A', 'D', 'SPACE')
        for i, key in enumerate(labels):
            color = CYAN if i < self.index else (RED if self.phase == 'running' and i == self.index else MUTED)
            self.game.ui.panel(screen, (50 + i * 380, 325, 340, 95), color)
            self.game.ui.pixel(screen, key, (75 + i * 380, 350), 34, color)
        timer = 'Без таймера' if self.limit is None else f'Осталось {max(0, self.limit - self.elapsed):.1f} с'
        self.game.ui.text(screen, f'{timer}  •  Здоровье {self.game.state.health}/100  •  Очки {self.game.evidence.score}', (50, 448), 25, CYAN)
        messages = {'ready': 'Сначала прочитайте инструкцию. Таймер начнётся только после кнопки «Начать».',
                    'running': 'Нажимайте показанные клавиши по порядку. Esc — пауза без расхода времени.',
                    'paused': 'Испытание приостановлено. Время и здоровье не изменяются.',
                    'failed': self.reason + ' Можно повторить или войти с дежурным.',
                    'complete': 'Вход открыт.'}
        self.game.ui.paragraph(screen, messages[self.phase], (50, 500, 1140, 70), 22, MUTED)
        self.draw_buttons(screen)


class MVPComplete(Scene):
    """Episode victory, not an unsupported conclusion about the murderer."""
    def __init__(self, game):
        super().__init__(game)
        self.button('Продолжить в квартире', (50, 590, 520, 56), game.scenes.pop)
        self.button('Главное меню', (610, 590, 520, 56), game.to_menu)

    def draw(self, screen):
        self.header(screen, 'Day 1 / первый след найден', 'Первый эпизод пройден · полное дело ещё не раскрыто')
        self.game.ui.pixel(screen, 'ДОСТУП К КВАРТИРЕ ПОЛУЧЕН', (50, 200), 34, CYAN)
        self.game.ui.paragraph(screen, 'Ермеков поручил Никите дело. Снимок и удалённые метаданные связаны '
                               'проверенным выводом; вход в квартиру открыт. Это основание продолжить поиск, '
                               'но не обвинить Сарсенова. Материалы и контрольная точка сохранены.', (50, 275, 1110, 160), 25)
        self.game.ui.text(screen, f'Улики: {len(self.game.state.evidence_ids)}   Очки: {self.game.evidence.score}   '
                          f'Здоровье: {self.game.state.health}/100   Репутация: {self.game.state.reputation}', (50, 470), 25, CYAN)
        self.draw_buttons(screen)
