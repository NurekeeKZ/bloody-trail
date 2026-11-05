from src.scenes.base import Scene, Message
from src.core.config import CYAN, MUTED, data
from src.systems.campaign import ACHIEVEMENTS


class ChapterIntro(Message):
    def __init__(self, game, day):
        chapter = data('chapters')[str(day)]
        super().__init__(game, f'Day {day} — ' + chapter['title'], chapter['text'])
        self.buttons[0] = ('Продолжить расследование', self.buttons[0][1].inflate(220, 0).move(110, 0), game.scenes.pop, True)


class FullVersion(Scene):
    def __init__(self, game, destination=None, load_slot=None):
        super().__init__(game)
        self.destination, self.load_slot = destination, load_slot
        self.message = ('Все три дня уже открыты на этом ноутбуке. Продолжайте историю кнопкой ниже.' if game.access.full_version_unlocked else 'Учебная сборка: откройте все три дня бесплатно. Покупка и регистрация не нужны.')
        self.rebuild()

    def rebuild(self):
        self.buttons=[]
        unlocked=self.game.access.full_version_unlocked
        label='Открыть всю историю бесплатно'
        if unlocked:
            label=('Продолжить переход' if self.destination else 'Загрузить выбранное сохранение' if self.load_slot else
                   'Вернуться к расследованию' if self.game.active else
                   'Продолжить сохранённую игру' if self.game.saves.path.exists() else 'Начать полную историю')
        self.button(label,(50,450,1120,62),self.proceed if unlocked else self.unlock)
        self.button('Отдельные дела / DLC',(50,530,1120,50),self.dlc)
        self.button('Назад',(50,630,300,50),self.game.scenes.pop)

    def unlock(self):
        try:
            self.game.access.unlock()
        except OSError as exc:
            self.message='Не удалось сохранить доступ. Проверьте права на папку сохранений и нажмите кнопку повторно. '+str(exc)
            return False
        self.game.access.error=''
        self.message='Все три дня открыты! Доступ сохранён на этом ноутбуке. Продолжайте расследование кнопкой ниже.'
        self.game.toast('Полная история открыта: Day 1, Day 2 и Day 3.')
        self.rebuild()
        if self.destination or self.load_slot is not None:
            return self.proceed()
        return True

    def proceed(self):
        if not self.game.access.full_version_unlocked:
            return self.unlock()
        if self.load_slot is not None:
            result=self.game.load(self.load_slot)
        elif self.destination:
            result=self.game.travel(self.destination)
        elif self.game.active:
            self.game.scenes.pop()
            return True
        elif self.game.saves.path.exists():
            result=self.game.load()
        else:
            self.game.new_game()
            return True
        if not result:
            self.message=self.game.notice or 'Переход ещё закрыт сюжетом. Соберите улики и подтвердите выводы на доске.'
        return result

    def dlc(self):
        from src.scenes.settings import AdditionalCases
        self.game.scenes.push(AdditionalCases(self.game))

    def draw(self, screen):
        unlocked=self.game.access.full_version_unlocked
        self.header(screen,'Полная история / три дня','Доступ к контенту сохраняется отдельно от прогресса расследования')
        for i,(day,title) in enumerate([('DAY 1','Первые следы'),('DAY 2','Архив «Сигма»'),('DAY 3','Правда или месть')]):
            x=50+i*400
            self.game.ui.panel(screen,(x,180,380,112),CYAN if unlocked or i==0 else MUTED)
            self.game.ui.text(screen,day+' / '+('ДОСТУПЕН' if unlocked or i==0 else 'ЗАКРЫТ'),(x+16,195),20,CYAN if unlocked or i==0 else MUTED)
            self.game.ui.text(screen,title,(x+16,238),23)
        self.game.ui.paragraph(screen,self.message,(50,318,1120,90),23,CYAN if unlocked else MUTED)
        self.game.ui.text(screen,'Дни открываются по сюжету: доступ не заменяет улики и выводы.',(50,410),20,MUTED)
        self.game.ui.text(screen,'План коммерческой версии: 5,99 USD + DLC. В этой сборке платежей нет.',(50,595),18,MUTED)
        self.draw_buttons(screen)


class CaseStatus(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.button('Назад', (50, 630, 300, 50), game.scenes.pop)

    def draw(self, screen):
        s = self.game.state
        self.header(screen, 'Дело / ресурсы и достижения', 'Ресурс времени тратится на критические действия; чтение документов бесплатно.')
        self.game.ui.text(screen, f'День {s.current_day}/3   Здоровье {s.health}   Репутация {s.reputation}   Осталось {s.time_remaining} ч   Очки {self.game.evidence.score}', (50, 185), 24, CYAN)
        self.game.ui.paragraph(screen, s.narrative['objective'], (540,310,670,80), 21, CYAN)
        self.game.ui.paragraph(screen, ' '.join(s.narrative['journal']), (540,405,670,180), 19, MUTED)
        self.game.ui.text(screen, 'Доверие: ' + ' · '.join(f'{n}: {s.trust.get(k,50)}' for k,n in [('sokolov','Ермеков'),('anna','Аружан'),('guard','Охранник')]), (50,235), 23)
        for i,(key,title) in enumerate(ACHIEVEMENTS.items()):
            self.game.ui.text(screen, ('✓ ' if key in s.achievements else '— ') + title, (50, 310 + 54*i), 24, CYAN if key in s.achievements else MUTED)


class Leaderboard(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.error = ''
        try:
            self.rows = sorted(game.journal.read(), key=lambda r:r['score'], reverse=True)[:8]
        except (OSError, ValueError) as exc:
            self.rows = []
            self.error = 'Таблица недоступна: ' + str(exc)
        self.button('Назад', (50,630,300,50), game.scenes.pop)

    def draw(self,screen):
        from src.scenes.results import Results
        self.header(screen,'Локальная таблица результатов','Последний исход каждого расследования · повторная загрузка не создаёт дубликаты')
        if not self.rows: self.game.ui.text(screen,self.error or 'Завершённых расследований пока нет.',(50,210),24)
        for i,row in enumerate(self.rows):
            from src.scenes.thriller import BranchEnding
            ending = BranchEnding.CONTENT[row['ending']][0] if row['ending'] in BranchEnding.CONTENT else Results.TEXTS.get(row['ending'], ('Поражение', ''))[0]
            self.game.ui.text(screen,f"{i+1}. {ending}   ·   {row['score']} очков   ·   {row['evidence']} улик   ·   {row['seconds']} с   ·   репутация {row['reputation']}",(50,185+i*48),22,CYAN)
        self.draw_buttons(screen)


class WeirConfrontation(Message):
    def __init__(self, game):
        super().__init__(game, 'Порт / Сарсенов', 'Сарсенов: «Ты пришёл за правдой о родителях или за местью? Покажи, что связывает меня с исчезнувшими данными».')
        from src.scenes.thriller import start_episode, BranchFinale
        self.button('Склад 07 / последствия',(50,580,540,36),lambda:start_episode(game))
        self.button('Развязки нового эпизода',(630,580,540,36),lambda:game.scenes.push(BranchFinale(game)))
        self.button('Предъявить проверенную цепочку', (50,390,1120,50), self.present)
        self.button('Обвинить без завершённого дела', (50,455,1120,50), self.accuse)
        self.button('Передать резервную копию Ермекову', (50,520,1120,50), self.backup, 'server' in game.state.evidence_ids)

    def draw(self,screen):
        self.header(screen,self.title)
        self.game.art.portrait(screen,'weir',(50,185))
        self.game.ui.paragraph(screen,self.text,(250,196,960,200),24)
        self.draw_buttons(screen)

    def backup(self):
        self.game.backup_case()
        self.text = 'Копия передана Ермекову. Условия законного задержания: полная цепочка, репутация и доверие не ниже 40.'

    def present(self):
        if not self.game.evidence.can_finalize():
            self.text = 'Цепочка неполна. Вернитесь к доске: нужны совпадение следов, связь с Сигмой, маршрут и независимая серверная копия.'
            return
        self.game.state.campaign['weir_confronted'] = True
        self.game.save()
        from src.scenes.overlays import FinalChoice
        self.game.scenes.push(FinalChoice(self.game))

    def accuse(self):
        if self.game.evidence.can_finalize():
            self.present()
            return
        confirm = Message(self.game, 'Предъявить недоказанное обвинение?', 'Комиссия отклонит дело без полной цепочки. Это завершит расследование поражением; можно вернуться к поиску.')
        confirm.button('Подтвердить обвинение', (330,622,650,52), lambda:self.game.fail('insufficient'))
        self.game.scenes.push(confirm)
