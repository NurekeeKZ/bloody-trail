from src.core.config import CYAN, MUTED, RED
from src.scenes.base import Scene


def format_time(seconds):
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f'{hours:02}:{minutes:02}:{seconds:02}'


class Results(Scene):
    TEXTS = {
        'arrest': ('Арест', 'Сарсенов задержан. Дело Айгуль и Ерлана Сейтовых открыто заново. Никита выбирает доказательства и закон.'),
        'revenge': ('Цена мести', 'Никита убивает Сарсенова. Никите предстоят моральные и юридические последствия смертельного решения.'),
        'release': ('Отпустить прошлое', 'Никита отказывается от мести, прощает Сарсенова и отпускает его. Месть прекращается, но правосудие не обеспечено.')}

    def __init__(self, game, ending, persist=True):
        super().__init__(game)
        self.ending = ending
        self.title, self.text = self.TEXTS[ending]
        if ending == 'arrest':
            from src.systems.campaign import epilogue
            self.text = (self.text + ' ' + epilogue(game.state)).strip()
        if persist:
            game.state.ending = ending
            game.record_result()
            game.save()
        self.button('Главное меню', (44, 634, 340, 50), game.to_menu)
        from src.scenes.campaign import Leaderboard, CaseStatus
        self.button('Таблица', (430,634,340,50), lambda:game.scenes.push(Leaderboard(game)))
        self.button('Достижения', (820,634,390,50), lambda:game.scenes.push(CaseStatus(game)))

    def draw(self, screen):
        self.header(screen, 'Результаты расследования', 'Beta / исход определяется доказательствами и решением игрока')
        self.game.ui.pixel(screen, self.title.upper(), (50, 180), 36, CYAN)
        self.game.ui.paragraph(screen, self.text, (50, 240, 1150, 100), 24)
        state = self.game.state
        correct = sum(rule['id'] in state.flags and set(rule['requires']).issubset(state.evidence_ids) for rule in self.game.rules)
        metrics = [('Найдено улик', f'{len(state.evidence_ids)} / {len(self.game.catalog)}'),
                   ('Правильных выводов', f'{correct} / {len(self.game.rules)}'),
                   ('Репутация', f'{state.reputation} / 100'),
                   ('Время прохождения', format_time(state.play_seconds))]
        for i, (name, value) in enumerate(metrics):
            x, y = 50 + (i % 2) * 600, 355 + (i // 2) * 110
            self.game.ui.panel(screen, (x, y, 560, 90), MUTED)
            self.game.ui.text(screen, name, (x + 18, y + 12), 20, MUTED)
            self.game.ui.pixel(screen, value, (x + 18, y + 43), 30, CYAN)
        self.game.ui.text(screen, f'Очки расследования: {self.game.evidence.score}. Здоровье: {state.health}. Осталось: {state.time_remaining} ч.', (50, 586), 18, MUTED)
        self.draw_buttons(screen)


class GameOver(Scene):
    def __init__(self, game, reason='withdraw', persist=True):
        super().__init__(game)
        self.reason = reason
        if persist:
            game.state.ending = reason
            game.record_result()
            game.save()
        from src.scenes.settings import LoadScene
        checkpoint = game.save_manager('checkpoint')
        try:
            can_retry = not checkpoint.load().ending
        except (ValueError, OSError):
            can_retry = False
        self.button('Повторить с контрольной точки', (50, 420, 680, 56), lambda: game.load('checkpoint'), can_retry)
        self.button('Загрузить сохранение', (50, 495, 680, 56), lambda: game.scenes.push(LoadScene(game)))
        self.button('Главное меню', (50, 570, 680, 56), game.to_menu)
        self.can_retry = can_retry

    def draw(self, screen):
        injured = self.reason == 'health'
        self.header(screen, 'Game Over / расследование прекращено', 'Причина: здоровье исчерпано' if injured else 'Причина: недостаток доказательств / срок истёк' if self.reason == 'insufficient' else 'Причина: подтверждённый отказ от дела')
        self.game.ui.pixel(screen, 'НИКИТЕ НУЖНА ПОМОЩЬ' if injured else 'ДЕЛО ПЕРЕДАНО КОМИССИИ', (50, 210), 38, RED)
        text = ('Опасное испытание ранило Никиту. Продолжать расследование невозможно: его увозит медицинская бригада. '
                'Контрольная точка перед испытанием сохранена.' if injured else
                'Никита складывает материалы в папку. Три дня заканчиваются для него раньше срока: '
                               'он добровольно передаёт расследование внешней комиссии. След остаётся, но искать его будут другие.')
        if self.reason == 'insufficient':
            text = 'Доказательств недостаточно или срок расследования истёк. Комиссия отклоняет обвинение; Сарсенов покидает Астеру. Вернитесь к контрольной точке и завершите цепочку.'
        self.game.ui.paragraph(screen, text, (50, 285, 1120, 110), 24)
        if not self.can_retry:
            self.game.ui.text(screen, 'Контрольная точка отсутствует или повреждена.', (50, 650), 20, MUTED)
        self.draw_buttons(screen)
