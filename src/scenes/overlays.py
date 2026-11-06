import pygame
from src.core.config import CYAN, MUTED, RED, PANEL, ROOT
from src.scenes.base import Scene, Message
from src.ui.widgets import Typewriter


class Inventory(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.selected = game.state.evidence_ids[0] if game.state.evidence_ids else None
        self.page=0
        self.rebuild()

    def rebuild(self):
        game=self.game;self.buttons=[]
        self.button('Назад [Esc / Tab]', (44,632,260,50),game.scenes.pop)
        self.button('Открыть фотографию / документ',(845,632,390,50),self.inspect,self.selected is not None)
        for i,eid in enumerate(game.state.evidence_ids[self.page*16:(self.page+1)*16]):
            self.button(game.catalog[eid]['title'],(44+(i//8)*390,180+(i%8)*54,370,46),lambda eid=eid:setattr(self,'selected',eid))
        if len(game.state.evidence_ids)>16:
            self.button('Другие материалы >',(350,632,400,50),self.turn_page)

    def turn_page(self):
        self.page=(self.page+1)%max(1,(len(self.game.state.evidence_ids)+15)//16);self.rebuild()

    def inspect(self):
        from src.scenes.evidence_board import EvidenceDetail
        if self.selected:
            self.game.scenes.push(EvidenceDetail(self.game, self.selected))

    def event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            self.game.scenes.pop()
        else:
            super().event(event)

    def draw(self, screen):
        self.header(screen, 'Материалы дела', f'{len(self.game.state.evidence_ids)} / {len(self.game.catalog)} улик · фиксация не равна доказанному выводу')
        if self.selected:
            item = self.game.catalog[self.selected]
            self.game.ui.panel(screen, (845, 180, 390, 410))
            self.game.ui.paragraph(screen, item['title'], (865, 200, 345, 80), 26, CYAN)
            self.game.ui.paragraph(screen, item['text'], (865, 290, 345, 210), 21)
            verified = self.game.state.evidence_records[self.selected]['verified']
            self.game.ui.text(screen, 'Связь проверена' if verified else 'Требует сопоставления', (865, 552), 20, MUTED)
        else:
            self.game.ui.text(screen, 'Пока нет улик. Подойдите к терминалу и нажмите E.', (48, 220), 25)
        self.draw_buttons(screen)


class CityMap(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.button('Назад [Esc / M]', (44, 632, 260, 50), game.scenes.pop)
        current = game.worlds[game.state.location]
        for i, (key, world) in enumerate(game.worlds.items()):
            unlocked = game.can_enter(key)
            reachable = key in current['neighbors'] and unlocked
            label = world['title']
            if key == game.state.location:
                label += '  ·  вы здесь'
            elif not unlocked:
                label += '  ·  закрыто'
            self.button(label, (40 + i * 205, 245 + (i % 2) * 150, 190, 100),
                        lambda key=key: game.travel(key), reachable)

    def event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            self.game.scenes.pop()
        else:
            super().event(event)

    def draw(self, screen):
        self.header(screen, 'Астера / схема маршрута', 'Можно перейти в соседний узел. Закрытые маршруты требуют улик.')
        points = [(135 + i * 205, 295 + (i % 2) * 150) for i in range(6)]
        pygame.draw.lines(screen, (48, 90, 108), False, points, 3)
        # Map labels wrap to keep full Russian location names visible.
        for label, rect, _, enabled in self.buttons[1:]:
            self.game.ui.panel(screen, rect, CYAN if enabled else MUTED)
            self.game.ui.paragraph(screen, label, (rect.x + 12, rect.y + 14, rect.w - 24, 80), 20, CYAN if enabled else MUTED)
        self.game.ui.button(screen, self.buttons[0][0], self.buttons[0][1], self.game.mouse)
        self.game.ui.text(screen, 'Квартира: поручение + фото + метаданные + первый вывод. Вход — сюжетное QTE.', (48, 565), 19, MUTED)


from src.scenes.evidence_board import Board


class Assistant(Scene):
    # Free phrases go to the local model; subclasses that only test commands switch this off.
    conversation = True

    def __init__(self, game):
        super().__init__(game)
        self.input = ''
        from src.ai.devices import SensorSession
        self.voice = SensorSession()
        self.voice_status = 'Микрофон выключен'
        self.level = -90.0
        self.device_warning = ''
        self.pending = None
        self.response = 'N.U.R.S. на связи. Спросите о деле своими словами — голосом или текстом — или выберите действие ниже.'
        self.button('Назад', (44, 632, 200, 50), game.scenes.pop)
        for i, (label, intent) in enumerate([('Улики', 'evidence'), ('Сравнить', 'analyze'), ('Карта', 'map'), ('Подсказка', 'help')]):
            self.button(label, (260 + i * 235, 632, 220, 50), lambda intent=intent: self.execute(intent))
        self.button('Микрофон / разрешить на один запрос', (48, 370, 620, 48), self.request_voice)
        self.button('Отключить микрофон', (690, 370, 520, 48), self.on_exit)
        self.button('Повторить показания', (48, 424, 340, 44), lambda: self.execute('testimony'))
        self.button('Вспомнить след / связь с 2020', (775,424,430,44), lambda:self.memory(), 'photo' in game.state.evidence_ids)
        self.button('Какие есть версии', (410, 424, 340, 44), lambda: self.execute('versions'))

    def on_exit(self):
        self.voice.close()
        self.level = -90.0
        self.voice_status = 'Микрофон выключен'

    on_cover = on_exit

    def request_voice(self):
        from src.scenes.sensors import SensorConsent
        self.game.scenes.push(SensorConsent(self.game, 'microphone', self.start_voice))

    def start_voice(self):
        try:
            self.voice.start('voice', consent=True, model=str(ROOT / 'assets/models/vosk-model-small-ru-0.22'),
                             phrases=None if self.conversation else self.game.command_router.phrases,
                             device_key=self.game.settings.microphone_device, gain=self.game.settings.microphone_gain)
            self.voice_status = 'Загрузка локальной модели…'
        except Exception as exc:
            self.voice_status = 'Устройство недоступно'
            self.response = 'Микрофон недоступен: ' + str(exc)

    def update(self, dt):
        if self.pending is not None and self.pending.done:
            self.finish_conversation()
        for event in self.voice.poll():
            if event['type'] == 'sample':
                self.level = event['db']
            elif event['type'] == 'warning':
                self.device_warning = event['message']
                self.response = event['message']
            elif event['type'] == 'status':
                self.voice_status = event['message']
            elif event['type'] == 'active':
                self.voice_status = 'Слушаю · микрофон включён · до 9 с'
            elif event['type'] == 'text':
                text = event['text']
                self.on_exit()
                router = self.game.command_router
                intent = router.match(text) if self.conversation else router.resolve(text, voice=True)
                if intent:
                    self.execute(intent)
                    self.voice_status = 'Команда распознана'
                    self.response = self.device_warning + ' Распознано: «' + text + '». ' + self.response
                elif self.conversation and text.strip() and text != '[unk]':
                    self.converse(text)
                else:
                    self.voice_status = 'Не удалось распознать'
                    self.response = 'Распознано: «' + (text or 'тишина') + '». Команда не распознана. Повторите запись или выберите действие вручную.'
                break
            elif event['type'] == 'error':
                self.on_exit()
                self.voice_status = 'Устройство недоступно'
                self.response = 'Не удалось включить голос: ' + event['message'] + '. Доступны текст и кнопки.'
                break
            elif event['type'] == 'stopped':
                self.on_exit()

    def event(self, event):
        # Enter belongs to the text field; it must not also activate a menu button.
        if event.type != pygame.KEYDOWN or event.key not in (pygame.K_RETURN, pygame.K_UP, pygame.K_DOWN):
            super().event(event)
        if event.type == pygame.TEXTINPUT:
            self.input = (self.input + event.text)[:100]
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.input = self.input[:-1]
            elif event.key == pygame.K_RETURN:
                router = self.game.command_router
                intent = router.match(self.input) if self.conversation else router.resolve(self.input)
                if intent:
                    self.execute(intent)
                elif self.conversation and self.input.strip():
                    self.converse(self.input.strip())
                else:
                    self.response = 'Не распознала. Используйте одну из команд или кнопки ниже.'
                self.input = ''

    def converse(self, text):
        """Ask the local model; the answer arrives in update() and never changes the game state."""
        if self.pending is not None:
            self.voice_status = 'N.U.R.S. ещё отвечает на предыдущий вопрос'
            return
        self.pending = self.game.nurs.ask(text)
        self.voice_status = 'N.U.R.S. анализирует…'
        self.response = self.quote(text) + ' N.U.R.S. сверяет материалы дела…'

    @staticmethod
    def quote(text):
        # The reply panel fits about five lines above the microphone buttons.
        return 'Вы: «' + (text if len(text) <= 80 else text[:79] + '…') + '».'

    def finish_conversation(self):
        request, self.pending = self.pending, None
        if request.status == 'offline':
            # Without the model the old command classifier keeps the panel usable.
            intent = self.game.command_router.resolve(request.question)
            if intent:
                self.execute(intent)
            else:
                self.response = 'Аналитический модуль недоступен. Используйте одну из команд или кнопки ниже.'
            self.voice_status = 'Локальная модель (Ollama) не отвечает · доступны команды и кнопки'
            return
        self.game.nurs.remember(request)
        self.voice_status = 'Ответ N.U.R.S.'
        self.response = self.quote(request.question) + ' N.U.R.S.: ' + request.reply

    def execute(self, intent):
        self.on_exit()
        if intent == 'evidence':
            self.response = 'Открыты найденные материалы дела.'
            self.game.scenes.push(Inventory(self.game))
        elif intent == 'map':
            self.response = 'Открыта карта доступных маршрутов.'
            self.game.scenes.push(CityMap(self.game))
        elif intent == 'analyze':
            if not self.game.state.evidence_ids:
                self.response = 'В этой сцене ещё нет записей для анализа. Сначала найдите улику.'
                return
            candidates=[r for r in self.game.rules if set(r['requires']).issubset(self.game.state.evidence_ids) and r['id'] not in self.game.state.flags]
            self.response=('Есть основания для проверки на доске: '+', '.join(' + '.join(self.game.catalog[e]['title'] for e in r.get('pair',[])) for r in candidates)) if candidates else 'Пока не хватает независимых источников. Используйте подсказку или осмотрите комнату.'
        elif intent == 'testimony':
            self.response = ('Аружан: ' + self.game.dialogues.conversations['anna']['text'] if 'anna' in self.game.state.evidence_ids else
                             'Показания Аружан ещё не записаны. Поговорите с ней в метро; помощник не выдумывает свидетельства.')
        elif intent == 'versions':
            confirmed = [r['text'] for r in self.game.rules if r['id'] in self.game.state.flags]
            self.response = 'Подтверждённые основания: ' + (' '.join(confirmed) if confirmed else 'пока отсутствуют. Сопоставьте найденные материалы на доске.')
        elif intent == 'help':
            if self.game.state.thriller['phase'] not in ('idle','resolved'):
                self.response='Нурс: используйте T в эпизоде склада для подсказки по текущей ветке. При травме найдите аптечку; в плену — инструмент и записку.'
                return
            self.response=self.game.hints.next(self.game.state.location)
            self.game.save()

    def memory(self):
        if self.game.recall_blood_mark(): return
        if 'blood_history' in self.game.state.flags:
            self.response='Независимый протокол подтвердил сходство следов. Теперь исследуем связь с Сигмой; имя виновного ещё не установлено.'
        else:
            self.response='Связь двух следов пока является гипотезой. Найдите независимый архивный протокол и проверьте её на доске.'

    def draw(self, screen):
        self.header(screen, 'N.U.R.S. / локальный помощник', 'Голос (Vosk) и текст · локальная модель через Ollama · без облака')
        self.game.art.portrait(screen, 'nurs', (48, 190))
        self.game.ui.paragraph(screen, self.response, (240, 186, 945, 165), 21)
        self.game.ui.text(screen, self.voice_status, (48, 478), 19, CYAN)
        pygame.draw.rect(screen, MUTED, (800,480,380,12))
        pygame.draw.rect(screen, CYAN, (800,480,round(380*max(0,min(1,(self.level+90)/90))),12))
        self.game.ui.panel(screen, (44, 510, 1170, 70))
        visible = self.input
        while self.game.ui.font(23).size(visible)[0] > 1100:
            visible = visible[1:]
        self.game.ui.text(screen, '> ' + visible + ('|' if pygame.time.get_ticks() % 1000 < 500 else ''), (60, 526), 23, CYAN)
        self.game.ui.text(screen, 'Enter — отправить. Спрашивайте своими словами; кнопки доступны без распознавания.', (48, 590), 18, MUTED)
        self.draw_buttons(screen)


class Dialogue(Scene):
    def __init__(self, game, dialogue_id):
        super().__init__(game)
        self.dialogue_id = dialogue_id
        self.node, choices = game.dialogues.get(dialogue_id, game.state.evidence_ids, game.state.flags)
        text=self.node['text']
        if game.state.thriller['was_captured']:text+=' Я слышал о похищении. Журнал со склада поможет следствию.'
        if dialogue_id=='anna' and game.state.thriller['ally_saved']:text+=' Спасибо, что вернулся за мной.'
        self.writer = Typewriter(text)
        self.emotion=self.node.get('emotion','neutral')
        self.text_sound_clock = 0
        for i, choice in enumerate(choices):
            self.button(choice['label'], (260, 440 + i * 66, 900, 54), lambda choice=choice: self.choose(choice))

    def choose(self, choice):
        if choice.get('close'):
            self.game.scenes.pop()
            return
        if choice.get('action') == 'archive_permission':
            self.game.hidden.reveal('archive_permission');self.game.save()
        if choice.get('action') == 'accept_case':
            self.game.accept_case()
        effect = choice.get('effect_id')
        if effect and not self.game.state.statistics.get(effect):
            s = self.game.state
            s.statistics[effect] = 1
            npc = choice.get('trust_npc', 'anna')
            s.trust[npc] = max(0, min(100, s.trust.get(npc, 50) + choice.get('trust_delta', 0)))
            s.reputation = max(0, min(100, s.reputation + choice.get('reputation_delta', 0)))
            if effect == 'anna_respect' and not s.statistics.get('anna_threat'):
                s.statistics['perfect_interview'] = 1
            self.game.toast(f'Доверие: {s.trust[npc]}/100 · Репутация: {s.reputation}/100')
            self.game.save()
        if 'evidence' in choice:
            self.game.evidence.collect(choice['evidence'])
            self.game.save()
        self.emotion=choice.get('emotion','angry' if choice.get('trust_delta',0)<0 else 'thinking')
        self.writer = Typewriter(choice['reply'])

    def event(self, event):
        super().event(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self.writer.finish()

    def update(self, dt):
        self.writer.update(dt*self.game.settings.text_speed/48)
        self.text_sound_clock += dt
        if len(self.writer.visible)<len(self.writer.text) and self.text_sound_clock>.13:
            self.text_sound_clock=0
            self.game.audio.play('dialogue')

    def draw(self, screen):
        self.header(screen, self.node['speaker'], 'Space — показать текст целиком · Esc — закончить разговор')
        from src.ui.portraits import PortraitManager
        PortraitManager().draw(screen, self.node.get('portrait', self.dialogue_id), (48, 194), self.emotion)
        self.game.ui.text(screen, 'Space >', (80, 426), 18, MUTED)
        self.game.ui.paragraph(screen, self.writer.visible, (260, 200, 910, 220), 26)
        self.draw_buttons(screen)


class FinalChoice(Message):
    def __init__(self, game):
        super().__init__(game, 'Сарсенов / решение Никиты', 'Доказательная цепочка собрана. Решение остаётся за вами. '
                         'Арест требует переданной копии, репутации и доверия Ермекова не ниже 40. Месть и освобождение имеют последствия.')
        from src.scenes.thriller import BranchFinale
        self.button('Развязки: правда / цена / скрытая правда',(50,540,1120,56),lambda:game.scenes.push(BranchFinale(game)))
        from src.systems.campaign import ending_allowed
        for i, (label, ending) in enumerate([('Вызвать подкрепление', 'arrest'), ('Выбрать месть', 'revenge'), ('Отпустить Сарсенова', 'release')]):
            self.button(label, (50 + i * 400, 440, 370, 58), lambda ending=ending: self.finish(ending), ending_allowed(game.state, game.evidence, ending))

    def finish(self, ending):
        self.game.finish_case(ending)


from src.scenes.results import Results


class Ending(Results):
    """Compatibility name used by the existing final-choice and load flows."""
    pass
