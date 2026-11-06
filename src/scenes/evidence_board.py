import pygame
from src.core.config import CYAN, INK, MUTED
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


THREAD = (178, 52, 60)


class Board(Scene):
    """Questions with empty slots: pick a question, fill every slot with evidence, check the conclusion.

    The pair API (select/propose/confirm) is kept for scripted checks and old flows.
    """
    QUESTION_TOP, QUESTION_ROW, SLOT_ROW = 196, 22, 28

    def __init__(self, game):
        super().__init__(game)
        self.selected = []
        self.active_key = None
        self.question = None
        self.target_slot = None
        self.slots = {}
        self.focus_card = None
        self.last_click = (None, -1000)
        self.message = ('Выберите вопрос справа, затем щёлкайте улики слева, чтобы заполнить пустые места. '
                        'Щелчок по заполненному месту освобождает его. Двойной щелчок открывает материал.')
        self.page=0
        self.update_cards()
        self.rebuild()

    def questions(self):
        """Opened questions: at least one source found; confirmed ones sink to the bottom."""
        found = set(self.game.state.evidence_ids)
        opened = [r for r in self.game.rules if found & set(r['requires'])]
        return sorted(opened, key=lambda r: r['id'] in self.game.state.flags)

    def rule(self, rule_id):
        return next(r for r in self.game.rules if r['id'] == rule_id)

    def slot_values(self, rule_id):
        return self.slots.setdefault(rule_id, [None] * len(self.rule(rule_id)['requires']))

    def shown_values(self):
        """Slot contents to display: a confirmed question always shows its real sources."""
        if not self.question:
            return []
        if self.question in self.game.state.flags:
            return list(self.rule(self.question)['requires'])
        return self.slot_values(self.question)

    def question_rects(self):
        return {r['id']: pygame.Rect(840, self.QUESTION_TOP + i * self.QUESTION_ROW, 408, self.QUESTION_ROW - 3)
                for i, r in enumerate(self.questions())}

    def slots_top(self):
        rows = len(self.questions()) + (len(self.questions()) < len(self.game.rules))
        return self.QUESTION_TOP + rows * self.QUESTION_ROW + 10

    def slot_rects(self):
        if not self.question:
            return []
        return [pygame.Rect(840, self.slots_top() + i * self.SLOT_ROW, 408, self.SLOT_ROW - 4)
                for i in range(len(self.rule(self.question)['requires']))]

    def choose_question(self, rule_id):
        self.question = rule_id
        self.target_slot = None
        rule = self.rule(rule_id)
        self.message = (rule['text'] if rule_id in self.game.state.flags else
                        rule.get('question', 'Какие материалы подтверждают этот вывод?'))
        self.rebuild()

    def place(self, eid):
        """Put a card into the chosen (or first empty) slot of the active question, or take it back."""
        if not self.question or self.question in self.game.state.flags:
            return
        values = self.slot_values(self.question)
        if eid in values:
            self.target_slot = values.index(eid)
            values[self.target_slot] = None
        else:
            index = self.target_slot if self.target_slot is not None else values.index(None) if None in values else len(values) - 1
            values[index] = eid
            self.target_slot = values.index(None) if None in values else None
        self.rebuild()

    def clear_slot(self, index):
        """A click on a slot makes it the target for the next card and frees it if filled."""
        if self.question and self.question not in self.game.state.flags:
            self.slot_values(self.question)[index] = None
            self.target_slot = index
            self.rebuild()

    def check_question(self):
        if not self.question:
            return
        values = self.slot_values(self.question)
        if None in values:
            return
        before = set(self.game.state.flags)
        confirmed, self.message = self.game.evidence.check_deduction(self.question, values)
        if not confirmed and self.game.state.statistics.get('deduction_mistakes', 0) >= 3:
            from src.scenes.overlays import Assistant
            helper = Assistant(self.game)
            helper.execute('help')
            self.game.toast('N.U.R.S.: ' + helper.response)
        if 'initial_anomaly' in set(self.game.state.flags) - before:
            self.game.toast('Первый вывод подтверждён. При наличии поручения доступна квартира [M]; открыт вопрос Ермекову.')
        self.game.save()
        self.rebuild()

    def update_cards(self):
        self.cards={eid:pygame.Rect(36+(i%4)*194,175+(i//4)*105,178,98) for i,eid in enumerate(self.game.state.evidence_ids[self.page*16:(self.page+1)*16])}

    def turn_page(self,delta):
        pages=max(1,(len(self.game.state.evidence_ids)+15)//16)
        self.page=(self.page+delta)%pages;self.update_cards();self.rebuild()

    def rebuild(self):
        self.buttons = []
        self.button('Назад [B / Esc]', (36, 650, 200, 48), self.game.scenes.pop)
        if len(self.game.state.evidence_ids)>16:
            self.button('<',(248,650,70,48),lambda:self.turn_page(-1))
            self.button(f'{self.page+1} / {(len(self.game.state.evidence_ids)+15)//16} >',(326,650,130,48),lambda:self.turn_page(1))
        self.button('Открыть материал', (468, 650, 240, 48), self.inspect, bool(self.focus_card or self.selected))
        ready = (self.question is not None and self.question not in self.game.state.flags
                 and None not in self.slot_values(self.question))
        self.button('Проверить вывод', (720, 650, 270, 48), self.check_question, ready)
        self.button('Финальное решение', (1002, 650, 254, 48), self.finalize,
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
        target = self.focus_card or (self.selected[-1] if self.selected else None)
        if target:
            self.game.scenes.push(EvidenceDetail(self.game, target))

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
            for rule_id, rect in self.question_rects().items():
                if rect.collidepoint(event.pos):
                    self.choose_question(rule_id)
                    return
            for index, rect in enumerate(self.slot_rects()):
                if rect.collidepoint(event.pos):
                    self.clear_slot(index)
                    return
            for eid, rect in self.cards.items():
                if rect.collidepoint(event.pos):
                    now = pygame.time.get_ticks()
                    double = self.last_click[0] == eid and now - self.last_click[1] < 350
                    if double or getattr(event, 'clicks', 1) >= 2:
                        # The first click of a double click already toggled the slot; undo it.
                        self.place(eid)
                        self.game.scenes.push(EvidenceDetail(self.game, eid))
                        self.last_click = (None, -1000)
                    else:
                        self.focus_card = eid
                        if self.question:
                            self.place(eid)
                        else:
                            self.select(eid)
                        self.last_click = (eid, now)
                    break

    def fit(self, text, width, size):
        while text and self.game.ui.font(size).size(text)[0] > width:
            text = text[:-2] + '…'
        return text

    def draw(self, screen):
        self.header(screen, 'Доска расследования', 'Вопрос → заполните все места уликами → проверка. Ложная связь стоит репутации.')
        pygame.draw.rect(screen, (31, 32, 39), (24, 164, 790, 463))
        for hypothesis in self.game.state.hypotheses.values():
            a, b = hypothesis['evidence']
            if hypothesis['status'] == 'confirmed' and a in self.cards and b in self.cards:
                self.draw_link(screen, self.cards[a], self.cards[b], CYAN, 3)
        placed = [e for e in self.shown_values() if e]
        for eid, rect in self.cards.items():
            border = THREAD if eid in placed else CYAN if eid == self.focus_card or eid in self.selected else MUTED
            self.game.ui.panel(screen, rect, border)
            if eid in placed:
                pygame.draw.rect(screen, THREAD, rect, 3)
            screen.blit(self.game.investigation_art.image(self.game.catalog[eid]['image'], (76, 47)), (rect.x + 8, rect.y + 8))
            verified = self.game.state.evidence_records[eid]['verified']
            self.game.ui.text(screen, 'в цепочке' if verified else 'не связана', (rect.x + 91, rect.y + 12), 14, CYAN if verified else MUTED)
            self.game.ui.paragraph(screen, self.game.catalog[eid]['title'], (rect.x + 8, rect.y + 53, rect.w - 16, 42), 16)
        if not self.cards:
            self.game.ui.paragraph(screen, 'Пока нет улик. Осмотрите фотоматериалы, компьютер и папки в кабинете.', (55, 230, 710, 100), 25)
        self.draw_questions(screen)
        slots = self.slot_rects()
        color = CYAN if self.question in self.game.state.flags else THREAD
        for eid, rect in zip(self.shown_values(), slots):
            if eid in self.cards:
                pygame.draw.line(screen, color, self.cards[eid].midright, rect.midleft, 2)
        self.draw_buttons(screen)

    def draw_questions(self, screen):
        ui, flags = self.game.ui, self.game.state.flags
        questions = self.questions()
        done = sum(r['id'] in flags for r in self.game.rules)
        ui.panel(screen, (832, 164, 424, 473), MUTED)
        ui.text(screen, f'ВОПРОСЫ ДЕЛА · подтверждено {done}/{len(self.game.rules)}', (848, 176), 18, CYAN)
        for rule_id, rect in self.question_rects().items():
            rule = self.rule(rule_id)
            confirmed = rule_id in flags
            active = rule_id == self.question
            if active:
                pygame.draw.rect(screen, (30, 58, 73), rect)
            mark = '+ ' if confirmed else '? '
            color = CYAN if confirmed else INK if active or rect.collidepoint(self.game.mouse) else MUTED
            ui.text(screen, self.fit(mark + rule.get('question', rule['id']), rect.w - 12, 15), (rect.x + 6, rect.y + 2), 15, color)
        hidden = len(self.game.rules) - len(questions)
        if hidden:
            ui.text(screen, f'Ещё {hidden} — откроются с новыми уликами', (846, self.QUESTION_TOP + len(questions) * self.QUESTION_ROW + 2), 15, MUTED)
        top = self.slots_top()
        pygame.draw.line(screen, MUTED, (840, top - 6), (1248, top - 6))
        message_top = top
        if self.question:
            rule = self.rule(self.question)
            confirmed = self.question in flags
            hints = rule.get('slots', [])
            values = self.shown_values()
            for i, (eid, rect) in enumerate(zip(values, self.slot_rects())):
                hint = hints[i] if i < len(hints) else f'Материал {i + 1}'
                label = self.game.catalog[eid]['title'] if eid else hint + ' — пусто'
                ui.panel(screen, rect, CYAN if confirmed else THREAD if eid else MUTED)
                if i == self.target_slot and not confirmed:
                    pygame.draw.rect(screen, CYAN, rect, 2)
                ui.text(screen, self.fit(label, rect.w - 14, 15), (rect.x + 7, rect.y + 4), 15,
                        CYAN if confirmed else INK if eid else MUTED)
            message_top = top + len(values) * self.SLOT_ROW + 4
        ui.paragraph(screen, self.message, (848, message_top, 396, 630 - message_top), 15)

    @staticmethod
    def draw_link(screen, first, second, color, width):
        a, b = first.midtop, second.midtop
        pygame.draw.lines(screen, color, False, [a, (a[0], a[1] - 10), (b[0], b[1] - 10), b], width)
