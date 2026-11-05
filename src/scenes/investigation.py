import pygame
from src.core.config import BG, CYAN, MUTED, SIZE
from src.scenes.base import Scene


class Investigation(Scene):
    def __init__(self, game, scene_id):
        super().__init__(game)
        self.content = game.investigations[scene_id]
        self.selected = None
        self.focus_active=False
        self.hovered_spot = None
        self.cursor = pygame.SYSTEM_CURSOR_ARROW
        self.background = pygame.Surface(SIZE)
        game.investigation_art.background(self.background, self.content, game.art)
        for i, (label, target) in enumerate([('Карта [M]', 'map'), ('Доска [B]', 'board'), ('Улики [Tab]', 'inventory'),
                                           ('N.U.R.S. [T]', 'assistant'), ('Вернуться [Esc]', 'exit')]):
            self.button(label, (24 + i * 250, 660, 232, 44), lambda target=target: self.navigate(target))

    def update(self,dt):
        self.focus_active=bool(pygame.key.get_pressed()[pygame.K_q]) and self.game.state.intuition>0
        self.game.state.intuition=max(0,min(100,self.game.state.intuition+(-15 if self.focus_active else 5)*dt))

    def navigate(self, target):
        from src.scenes.overlays import Board, Inventory, CityMap, Assistant
        if target == 'exit':
            if len(self.game.scenes.stack) > 1:
                previous = self.game.scenes.stack[-2]
                self.game.transition(previous, self.game.scenes.pop)
            return
        self.game.scenes.push({'board': Board, 'inventory': Inventory, 'map': CityMap, 'assistant': Assistant}[target](self.game))

    def event(self, event):
        if event.type == pygame.KEYDOWN:
            target = {pygame.K_ESCAPE: 'exit', pygame.K_m: 'map', pygame.K_b: 'board',
                      pygame.K_TAB: 'inventory', pygame.K_t: 'assistant'}.get(event.key)
            if target:
                self.navigate(target)
                return
        super().event(event)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and 106 <= event.pos[1] < 650:
            spot = next((s for s in self.content['hotspots'] if pygame.Rect(s['rect']).collidepoint(event.pos)), None)
            if spot:
                self.select(spot)

    def select(self, spot):
        self.selected = spot
        self.game.audio.play('click')
        self.game.scenes.push(ObjectInspection(self.game, self, spot))

    def collect(self):
        """Compatibility helper for simple scenes; uses the same gated action executor."""
        if self.selected:
            detail = ObjectInspection(self.game, self, self.selected)
            action = next((a for a in detail.actions if a['type'] == 'collect'), None)
            if action:
                detail.execute(action)

    def draw(self, screen):
        screen.blit(self.background, (0, 0))
        self.hovered_spot = next((s for s in self.content['hotspots'] if pygame.Rect(s['rect']).collidepoint(self.game.mouse)), None)
        self.cursor = pygame.SYSTEM_CURSOR_HAND if self.hovered_spot else pygame.SYSTEM_CURSOR_ARROW
        for index, spot in enumerate(self.content['hotspots']):
            rect = pygame.Rect(spot['rect'])
            hover = spot is self.hovered_spot
            if self.focus_active and abs(rect.centerx-self.game.mouse[0])<160 and abs(rect.centery-self.game.mouse[1])<160:
                pygame.draw.rect(screen,(108,133,137),rect,1)
            if hover:
                light = pygame.Surface(rect.size, pygame.SRCALPHA)
                light.fill((79, 209, 219, 28))
                screen.blit(light, rect)
                pygame.draw.rect(screen, CYAN, rect, 2)
            # Numbered corner markers make even the temporary background discoverable.
            if self.content.get('markers',True):
                pygame.draw.rect(screen, BG, (rect.x, rect.y, 28, 25))
                self.game.ui.text(screen, str(index + 1).zfill(2), (rect.x + 3, rect.y + 1), 17, CYAN)
        if self.hovered_spot:
            label = self.hovered_spot['label']
            width = self.game.ui.font(21).size(label)[0] + 34
            x = min(1250 - width, max(24, int(self.game.mouse[0]) + 18))
            y = min(608, max(110, int(self.game.mouse[1]) - 46))
            self.game.ui.panel(screen, (x, y, width, 38))
            self.game.ui.text(screen, label, (x + 16, y + 6), 21, CYAN)
        pygame.draw.rect(screen, BG, (0, 0, 1280, 106))
        state = self.game.state
        daytime = ('Утро', 'Полдень', 'День', 'Вечер', 'Ночь', 'Поздняя ночь')[state.time_slot]
        self.game.ui.pixel(screen, self.content.get('case', 'Дело Нурланова'), (28, 18), 28)
        self.game.ui.text(screen, f'{self.content["title"]}  /  День {state.current_day} · {daytime}', (28, 62), 22, MUTED)
        self.game.ui.text(screen, f'Улики {len(state.evidence_ids)}/{len(self.game.catalog)}  ·  Выводы {len(state.flags)}/{len(self.game.rules)}', (900, 28), 21, CYAN)
        pygame.draw.rect(screen, BG, (0, 650, 1280, 70))
        self.draw_buttons(screen)


class ObjectInspection(Scene):
    def __init__(self, game, room, spot):
        super().__init__(game)
        self.room, self.spot = room, spot
        eid = spot.get('evidence')
        self.description = spot.get('description', game.catalog[eid]['text'] if eid else '')
        self.actions = spot.get('actions', [{'id': 'collect', 'label': 'Зафиксировать улику', 'type': 'collect', 'evidence': eid}])
        self.rebuild()

    def missing(self, action):
        return [eid for eid in action.get('requires', []) if eid not in self.game.state.evidence_ids]

    def allowed(self, action):
        return not self.missing(action) and set(action.get('requires_flags', [])).issubset(self.game.state.flags)

    def rebuild(self):
        self.buttons = []
        for i, action in enumerate(self.actions):
            taken = action['type'] == 'collect' and action['evidence'] in self.game.state.evidence_ids
            label = 'Улика уже получена' if taken else action['label']
            self.button(label, (680, 275 + i * 80, 425, 54), lambda action=action: self.execute(action), self.allowed(action) and not taken)
        self.button('Назад к кабинету [Esc]', (170, 575, 430, 48), self.game.scenes.pop)

    def event(self, event):
        self.rebuild()
        super().event(event)

    def execute(self, action):
        if not self.allowed(action):
            self.description = 'Сначала найдите: ' + ', '.join(self.game.catalog[e]['title'] for e in self.missing(action))
            return False
        kind = action['type']
        if kind == 'puzzle':
            from src.scenes.puzzles import PuzzleScene
            self.game.scenes.push(PuzzleScene(self.game, action['puzzle']))
            return True
        if kind == 'reveal':
            fresh=self.game.hidden.reveal(action['marker'])
            self.description=action['text']
            if fresh:
                self.game.state.narrative['journal'].append(action['text'])
                if action.get('evidence'): self.game.evidence.collect(action['evidence'])
                self.game.save()
            return fresh
        if kind == 'collect':
            eid = action['evidence']
            added = self.game.evidence.collect(eid)
            self.description = self.game.catalog[eid]['text'] + (' Улика зафиксирована.' if added else ' Уже в материалах дела; повторного начисления нет.')
            if added:
                if eid == 'metadata' and not self.game.state.story['anomaly_announced']:
                    self.game.state.story['anomaly_announced'] = True
                    self.description = ('N.U.R.S.: обнаружена аномалия — у снимка Нурланова удалены метаданные. '
                                        'Это ещё не доказательство виновности. На доске сопоставьте снимок и запись. '
                                        'Улика добавлена в инвентарь.')
                    self.game.toast('N.U.R.S.: аномалия в записи Нурланова. Откройте доску [B] и проверьте связь.')
                self.game.save()
            self.rebuild()
            return added
        if kind == 'read':
            self.description = action['text']
        elif kind == 'dialogue':
            from src.scenes.overlays import Dialogue
            self.game.scenes.push(Dialogue(self.game, action['dialogue']))
        elif kind == 'assistant':
            from src.scenes.overlays import Assistant
            assistant = Assistant(self.game)
            assistant.execute('analyze')
            self.game.scenes.push(assistant)
        elif kind == 'backup':
            self.description = 'Копия передана Ермекову.' if self.game.backup_case() else 'Сначала найдите серверную копию.'
        elif kind == 'finale':
            from src.scenes.campaign import WeirConfrontation
            self.game.scenes.push(WeirConfrontation(self.game))
        elif kind == 'guard':
            from src.scenes.sensors import GuardDialogue
            self.game.scenes.push(GuardDialogue(self.game))
        else:
            self.room.navigate(kind)
        return True

    def draw(self, screen):
        self.room.draw(screen)
        veil = pygame.Surface(SIZE, pygame.SRCALPHA)
        veil.fill((0, 0, 0, 165))
        screen.blit(veil, (0, 0))
        self.game.ui.panel(screen, (140, 126, 1000, 514))
        self.game.ui.pixel(screen, self.spot['label'], (168, 151), 28, CYAN)
        self.game.ui.paragraph(screen, self.description, (170, 205, 470, 170), 21)
        rect = pygame.Rect(self.spot['rect'])
        preview = self.room.background.subsurface(rect)
        fit = preview.get_rect().fit(pygame.Rect(170, 388, 470, 163))
        screen.blit(pygame.transform.scale(preview, fit.size), fit)
        self.game.ui.text(screen, 'ДОСТУПНЫЕ ДЕЙСТВИЯ', (680, 222), 20, MUTED)
        self.rebuild()
        for i, action in enumerate(self.actions):
            missing = self.missing(action)
            if missing:
                self.game.ui.text(screen, 'Нужна: ' + self.game.catalog[missing[0]]['title'], (680, 333 + i * 80), 16, MUTED)
        self.draw_buttons(screen)
