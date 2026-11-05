import pygame
from src.core.config import CYAN, RED, MUTED, BG
from src.scenes.base import Scene


class EvidenceDetail(Scene):
    def __init__(self, game, eid):
        super().__init__(game)
        self.eid = eid
        self.button('Назад [Esc]', (44, 644, 270, 48), game.scenes.pop)

    def draw(self, screen):
        entry = self.game.catalog[self.eid]
        record = self.game.state.evidence_records[self.eid]
        self.header(screen, entry['title'], 'Карточка материала / ' + self.eid)
        screen.blit(self.game.investigation_art.image(entry['image'], (560, 350)), (44, 190))
        self.game.ui.paragraph(screen, entry.get('media_note', ''), (44, 558, 560, 65), 17, MUTED)
        self.game.ui.paragraph(screen, entry['text'], (650, 192, 570, 175), 23)
        self.game.ui.text(screen, 'Источник: ' + record['source'], (650, 382), 20, CYAN)
        daytime = ('Утро', 'Полдень', 'День', 'Вечер', 'Ночь', 'Поздняя ночь')[record['slot']]
        self.game.ui.text(screen, f'Найдено: день {record["day"]}, {daytime.lower()}', (650, 418), 20)
        self.game.ui.text(screen, 'Статус: ' + ('в проверенной цепочке' if record['verified'] else 'не сопоставлена'), (650, 454), 20)
        related = record.get('related', [])
        self.game.ui.paragraph(screen, 'Связанные доказательства: ' + (', '.join(self.game.catalog[e]['title'] for e in related) or 'пока нет'), (650, 495, 570, 115), 20, MUTED)
        self.draw_buttons(screen)


class Board(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.selected = []
        self.active_key = None
        self.last_click = (None, -1000)
        self.message = 'Выберите две карточки и создайте гипотезу. Двойной щелчок открывает материал.'
        self.page=0
        self.update_cards()
        self.rebuild()

    def update_cards(self):
        self.cards={eid:pygame.Rect(36+(i%4)*194,175+(i//4)*105,178,98) for i,eid in enumerate(self.game.state.evidence_ids[self.page*16:(self.page+1)*16])}

    def turn_page(self,delta):
        pages=max(1,(len(self.game.state.evidence_ids)+15)//16)
        self.page=(self.page+delta)%pages;self.update_cards();self.rebuild()

    def rebuild(self):
        self.buttons = []
        self.button('Назад [B / Esc]', (36, 650, 250, 48), self.game.scenes.pop)
        if len(self.game.state.evidence_ids)>16:
            self.button('<',(320,650,90,48),lambda:self.turn_page(-1))
            self.button(f'{self.page+1} / {(len(self.game.state.evidence_ids)+15)//16} >',(430,650,170,48),lambda:self.turn_page(1))
        self.button('Создать / выбрать гипотезу', (846, 420, 400, 44), self.propose, len(self.selected) == 2)
        self.button('Проверить / подтвердить', (846, 474, 400, 44), self.confirm, self.active_key is not None)
        self.button('Опровергнуть гипотезу', (846, 528, 400, 44), self.reject, self.active_key is not None)
        self.button('Открыть выбранную улику', (846, 582, 400, 44), self.inspect, bool(self.selected))
        self.button('Финальное решение', (846, 650, 400, 48), self.finalize,
                    self.game.state.location == 'port')

    def select(self, eid):
        if eid in self.selected:
            self.selected.remove(eid)
        else:
            self.selected = (self.selected + [eid])[-2:]
        key = '|'.join(sorted(self.selected))
        self.active_key = key if len(self.selected) == 2 and key in self.game.state.hypotheses else None
        self.message = self.game.state.hypotheses[key]['reason'] if self.active_key else 'Гипотеза не создана. Соединение ещё не является доказательством.'
        self.rebuild()

    def propose(self):
        if len(self.selected) != 2:
            return
        self.active_key = self.game.evidence.propose(*self.selected)
        self.message = self.game.state.hypotheses[self.active_key]['reason']
        self.game.save()
        self.rebuild()

    def confirm(self):
        if self.active_key:
            before = set(self.game.state.flags)
            self.message = self.game.evidence.evaluate(self.active_key)
            if self.game.state.statistics.get('deduction_mistakes', 0) >= 3:
                from src.scenes.overlays import Assistant
                helper = Assistant(self.game)
                helper.execute('help')
                self.game.toast('N.U.R.S.: ' + helper.response)
            if 'initial_anomaly' in set(self.game.state.flags) - before:
                self.game.toast('Первый вывод подтверждён. При наличии поручения доступна квартира [M]; открыт вопрос Ермекову.')
            self.game.save()
            self.rebuild()

    def reject(self):
        if self.active_key:
            self.message = self.game.evidence.reject(self.active_key)
            self.game.save()

    def inspect(self):
        if self.selected:
            self.game.scenes.push(EvidenceDetail(self.game, self.selected[-1]))

    def finalize(self):
        from src.scenes.campaign import WeirConfrontation
        if self.game.state.location == 'port':
            self.game.scenes.push(WeirConfrontation(self.game))

    def event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_b:
            self.game.scenes.pop()
            return
        super().event(event)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for eid, rect in self.cards.items():
                if rect.collidepoint(event.pos):
                    now = pygame.time.get_ticks()
                    double = self.last_click[0] == eid and now - self.last_click[1] < 350
                    if double or getattr(event, 'clicks', 1) >= 2:
                        self.game.scenes.push(EvidenceDetail(self.game, eid))
                        self.last_click = (None, -1000)
                    else:
                        self.select(eid)
                        self.last_click = (eid, now)
                    break

    def draw(self, screen):
        self.header(screen, 'Доска расследования', 'Две улики → гипотеза → проверка независимых подтверждений')
        pygame.draw.rect(screen, (31, 32, 39), (24, 164, 790, 463))
        colors = {'pending': (208, 168, 91), 'confirmed': CYAN, 'rejected': RED}
        for hypothesis in self.game.state.hypotheses.values():
            a, b = hypothesis['evidence']
            if a in self.cards and b in self.cards:
                self.draw_link(screen, self.cards[a], self.cards[b], colors[hypothesis['status']], 3)
        if len(self.selected) == 2 and all(e in self.cards for e in self.selected):
            self.draw_link(screen, self.cards[self.selected[0]], self.cards[self.selected[1]], (233, 224, 192), 1)
        for eid, rect in self.cards.items():
            self.game.ui.panel(screen, rect, CYAN if eid in self.selected else MUTED)
            screen.blit(self.game.investigation_art.image(self.game.catalog[eid]['image'], (76, 47)), (rect.x + 8, rect.y + 8))
            self.game.ui.text(screen, eid[-4:] if eid.startswith('EVIDENCE_') else eid, (rect.x + 91, rect.y + 12), 14, MUTED)
            self.game.ui.paragraph(screen, self.game.catalog[eid]['title'], (rect.x + 8, rect.y + 53, rect.w - 16, 42), 16)
        if not self.cards:
            self.game.ui.paragraph(screen, 'Пока нет улик. Осмотрите фотоматериалы, компьютер и папки в кабинете.', (55, 230, 710, 100), 25)
        self.game.ui.panel(screen, (832, 164, 424, 473), MUTED)
        status = self.game.state.hypotheses[self.active_key]['status'] if self.active_key else 'pending'
        label = {'pending': 'ГИПОТЕЗА', 'confirmed': 'ПОДТВЕРЖДЕНО', 'rejected': 'ОТКЛОНЕНО'}[status]
        self.game.ui.pixel(screen, label, (848, 183), 26, colors[status])
        self.game.ui.paragraph(screen, self.message, (848, 230, 390, 180), 18)
        self.game.ui.text(screen, 'Голубой: подтверждено · красный: отклонено · янтарный: гипотеза', (40, 604), 16, MUTED)
        self.draw_buttons(screen)

    @staticmethod
    def draw_link(screen, first, second, color, width):
        a, b = first.midtop, second.midtop
        pygame.draw.lines(screen, color, False, [a, (a[0], a[1] - 10), (b[0], b[1] - 10), b], width)
