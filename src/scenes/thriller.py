"""Playable warehouse branches, sensor stealth and chase adapters."""
import math,time
import pygame
from src.core.config import data,CYAN,MUTED,RED,BG
from src.scenes.base import Scene,Message
from src.entities.player import Player
from src.systems.stealth_system import StealthSystem,QTESystem
from src.ai.devices import SensorSession


def show_phase(game,fade=True):
    phase=game.state.thriller['phase']
    if phase=='hiding':scene=HideScene(game)
    elif phase=='chase':scene=ChaseScene(game)
    elif phase in data('branch_rooms'):scene=BranchRoom(game)
    else:
        from src.scenes.exploration import Exploration
        scene=Exploration(game)
    if fade:game.transition(scene,lambda:game.scenes.replace(scene))
    else:game.scenes.replace(scene)


def start_episode(game):
    if game.state.location!='port' or not game.access.full_version_unlocked:return False
    if game.state.thriller['phase']=='resolved':
        game.scenes.push(BranchFinale(game));return True
    game.story_manager.start();game.save();show_phase(game);return True


class EpisodePause(Message):
    def __init__(self,game):
        super().__init__(game,'Эпизод приостановлен','Сенсоры отключены. При возврате к пряткам выберите режим заново. Прогресс и опасность сохраняются; новая калибровка не обнуляет последствия.')
        self.button('Сохранить',(330,622,260,52),game.manual_save)
        self.button('Главное меню',(640,622,330,52),lambda:game.to_menu() if game.save() else None)


class BranchRoom(Scene):
    def __init__(self,game):
        super().__init__(game);self.phase=game.state.thriller['phase'];self.room=data('branch_rooms')[self.phase]
        self.player=Player(game.state.thriller['position']);self.walls=[pygame.Rect(r) for r in [[30,140,1220,20],[30,590,1220,20],[30,140,20,470],[1230,140,20,470]]+self.room['walls']]
        self.near=None;self.age=0.;self.message='WASD — идти · E — взаимодействовать · T — Нурс · Esc — пауза'
    def event(self,event):
        if event.type!=pygame.KEYDOWN:return
        if event.key==pygame.K_ESCAPE:self.game.scenes.push(EpisodePause(self.game))
        elif event.key==pygame.K_t:
            t=self.game.state.thriller
            if self.phase=='quiet' and 'warehouse_record' in self.game.state.evidence_ids:
                t['secret_hint']=True;self.message='Нурс: сопоставь запись с флешкой из книги и карточкой сейфа. Проследи за связным, сохрани союзника и передай полную цепочку.'
                self.game.story_manager.log('secret_hint','Нурс предложил проверить корневой архив по записи, флешке и карточке; решение требует независимой цепочки.')
            else:self.message={'warehouse':'Нурс: шаги! Выбери шкаф или стол.','captive':'Нурс: проволока под кроватью; записка у вентиляции. Замок допускает три попытки.','recovery':'Нурс: перевязка снимет ограничение скорости.','alley':'Нурс: сначала открой служебный проход рычагом.','street':'Нурс: вызови помощь прежде, чем идти за Аружан.'}.get(self.phase,'Нурс: сначала подслушай разговор у окна.')
            self.game.save()
        elif event.key==pygame.K_e and self.near:self.interact(self.near['id'])
    def update(self,dt):
        self.age+=dt;keys=pygame.key.get_pressed()
        direction=(int(keys[pygame.K_d] or keys[pygame.K_RIGHT])-int(keys[pygame.K_a] or keys[pygame.K_LEFT]),int(keys[pygame.K_s] or keys[pygame.K_DOWN])-int(keys[pygame.K_w] or keys[pygame.K_UP]))
        self.player.SPEED=115 if self.game.state.thriller['leg_injured'] else 180
        self.player.move(direction,min(dt,.1),self.walls,keys[pygame.K_LSHIFT])
        self.game.state.thriller['position']=list(self.player.position)
        self.near=next((o for o in self.room['objects'] if self.player.position.distance_to(pygame.Rect(o['rect']).center)<110),None)
    def change(self,phase,branch=None):
        self.game.story_manager.phase(phase,branch);self.game.save();show_phase(self.game)
    def interact(self,key):
        story=self.game.story_manager;t=self.game.state.thriller
        if key in ('closet','table'):
            t['items']=[item for item in t['items'] if not item.startswith('cover_')]
            story.collect('cover_'+key);self.change('hiding');return
        if key=='record':
            self.game.evidence.collect('warehouse_record');self.message='Нурс: они скрывают корневой архив. T — обсудить новую запись. Преследовать связного или передать запись и уйти?'
        elif key=='pursue':
            if 'warehouse_record' not in self.game.state.evidence_ids:self.message='Сначала подслушайте разговор у окна.';return
            story.begin_chase();self.game.save();show_phase(self.game);return
        elif key=='leave':
            if 'warehouse_record' not in self.game.state.evidence_ids:self.message='У окна слышны голоса — сначала получите запись.';return
            t['ally_saved']=True;self.change('resolved');return
        elif key=='medkit':
            t['leg_injured']=False;story.collect('bandage');self.message='Нога перевязана. Скорость восстановлена; факт травмы остался в журнале.'
        elif key=='escape':story.begin_chase();self.game.save();show_phase(self.game);return
        elif key=='wire':story.collect('wire');self.message='Проволока извлечена из кровати. Ею можно добраться до контактов замка.'
        elif key=='code':story.collect('code');self.message='На записке: 4172. Три неверные попытки включат блокировку.'
        elif key=='ledger':self.game.evidence.collect('captor_ledger');self.message='Журнал похитителей сохранён. Его не отнимут при следующей ошибке.'
        elif key=='lock':
            if not {'wire','code'}.issubset(t['items']):self.message='Нужны проволока и записка с кодом.';return
            self.game.scenes.push(CaptiveLock(self.game));return
        elif key in ('signal','latch'):
            story.collect(key);self.message='Помощь вызвана. Теперь можно вывести Аружан.' if key=='signal' else 'Проход открыт. Аружан можно вывести через боковую дверь.'
        elif key=='rescue':
            needed='latch' if self.phase=='alley' else 'signal'
            if needed not in t['items']:self.message='Сначала '+('откройте проход рычагом.' if needed=='latch' else 'вызовите помощь по телефону.');return
            story.rescue(True);self.game.save();show_phase(self.game);return
        elif key=='abandon':
            panel=Message(self.game,'Уйти без Аружан?','Аружан заперта в горящем складе. Уход без помощи приведёт к её гибели. Можно вернуться и открыть проход / вызвать помощь.')
            def abandon():story.rescue(False);self.game.save();show_phase(self.game)
            panel.button('Уйти одному',(330,622,400,52),abandon);self.game.scenes.push(panel);return
        self.game.save()
    def draw(self,screen):
        screen.fill((14,24,34));self.game.ui.text(screen,self.room['title'],(40,35),32,CYAN)
        self.game.ui.paragraph(screen,self.message,(40,80,1180,60),19)
        floor={'warehouse':(40,38,43),'quiet':(35,47,50),'recovery':(48,43,38),'captive':(33,32,38),'alley':(22,29,43),'street':(38,48,62)}[self.phase]
        pygame.draw.rect(screen,floor,(50,160,1180,430))
        for x in range(50,1230,48):pygame.draw.line(screen,(25,29,35),(x,160),(x,590))
        for wall in self.walls:pygame.draw.rect(screen,(69,75,77),wall);pygame.draw.rect(screen,(103,110,105),wall,2)
        for o in self.room['objects']:
            r=pygame.Rect(o['rect']);pygame.draw.rect(screen,(77,62,50),r);pygame.draw.rect(screen,CYAN if self.near is o else MUTED,r,2)
            for y in range(r.y+10,r.bottom-5,14):pygame.draw.line(screen,(115,96,73),(r.x+6,y),(r.right-6,y))
            self.game.ui.paragraph(screen,o['name'],(r.x,r.bottom+3,r.width+90,45),15,CYAN)
        self.game.art.person(screen,self.player.position,int(self.player.animation*7),self.player.facing)
        if self.phase not in ('captive','recovery'):self.game.art.person(screen,(self.player.position.x-65,self.player.position.y),hologram=True)
        self.game.ui.text(screen,'[E] '+self.near['name'] if self.near else 'Подойдите к предмету. T — контекстная подсказка.',(40,644),23,CYAN)
        self.game.ui.text(screen,'Травма ноги: скорость снижена' if self.game.state.thriller['leg_injured'] else 'Сенсоры выключены · предметы доступны без оборудования',(40,686),18,MUTED)


class CaptiveLock(Scene):
    def __init__(self,game):
        super().__init__(game);self.code='';self.message='Введите код с записки у вентиляции. Enter — проверить.'
        self.button('Назад',(40,620,260,52),game.scenes.pop)
        self.button('Проверить код',(340,620,400,52),self.submit)
    def event(self,event):
        if event.type==pygame.TEXTINPUT:self.code=(self.code+''.join(c for c in event.text if c.isdigit()))[:4]
        if event.type==pygame.KEYDOWN and event.key==pygame.K_BACKSPACE:self.code=self.code[:-1]
        if event.type==pygame.KEYDOWN and event.key==pygame.K_RETURN:self.submit();return
        super().event(event)
    def submit(self):
        if self.game.state.thriller['escape_attempts']>=3:return
        if self.game.story_manager.escape(self.code):self.game.save();show_phase(self.game);return
        self.code='';self.message='Неверный код. Осталось попыток: '+str(3-self.game.state.thriller['escape_attempts'])
        self.game.save()
        if self.game.state.thriller['escape_attempts']>=3:finish_branch(self.game,'prisoner')
    def draw(self,screen):
        self.header(screen,'Камера / электронный замок');self.game.ui.paragraph(screen,self.message,(60,200,1100,120),24)
        self.game.ui.pixel(screen,self.code or '----',(480,380),64,CYAN);self.draw_buttons(screen)


class HideScene(Scene):
    def __init__(self,game):
        super().__init__(game);self.mic=SensorSession();self.camera_session=SensorSession()
        self.mode='';self.requested=set();self.signals={};self.status='Выберите укрытие и способ управления. Оборудование не влияет на доступность концовок.'
        self.trial=None;self.stage='ready';self.age=0.;self.held=set();self.last_beat=0.;self.game.audio.play('door');self.fault_time=0.;self.rebuild();self.focus=0 if game.settings.stealth_manual else 1
    @property
    def sensors_active(self):return self.mic.process is not None or self.camera_session.process is not None
    def rebuild(self):
        self.buttons=[]
        self.button('Клавиши: SPACE + неподвижность',(30,645,390,48),lambda:self.start(set()))
        self.button('Микрофон + камера',(435,645,310,48),lambda:self.consent({'mic','camera'}))
        self.button('Только микрофон',(760,645,240,48),lambda:self.consent({'mic'}))
        self.button('Отключить / пауза',(1015,645,240,48),self.pause)
    def consent(self,kinds):
        panel=Message(self.game,'Разрешить сенсоры на эту попытку?','Микрофон измеряет шум, камера — присутствие лица и движение в области головы и верхней части тела. Обработка локальная, записи и передачи нет. При ошибке можно перейти на клавиши с теми же сюжетными возможностями. Esc отключает устройства. Камера не определяет эмоции или ложь.')
        def accept():self.game.scenes.pop();self.start(kinds)
        panel.button('Разрешить на эту попытку',(330,622,650,52),accept);self.game.scenes.push(panel)
    def start(self,kinds):
        self.close_devices();self.requested=set(kinds);self.mode='sensor' if kinds else 'manual';self.signals={};self.held=set();self.fault_time=0.
        t=self.game.state.thriller;s=self.game.settings
        self.trial=StealthSystem(s.stealth_noise_sensitivity,s.stealth_motion_sensitivity,t['hide_elapsed'],t['danger'])
        self.stage='calibration' if kinds else 'running';self.status='Калибровка: 2 секунды тишины и неподвижности.' if kinds else 'Держите SPACE (дыхание), не нажимайте WASD/стрелки. Осталось 15 секунд или меньше.'
        try:
            if 'mic' in kinds:self.mic.start('noise',consent=True,device_key=s.microphone_device,gain=s.microphone_gain)
            if 'camera' in kinds:self.camera_session.start('camera',consent=True,processor='upper_body')
        except Exception as exc:self.fault(str(exc))
    def close_devices(self):self.mic.close();self.camera_session.close()
    def on_exit(self):
        self.close_devices();self.held.clear()
        if self.stage in ('running','calibration'):self.stage='ready';self.status='Сенсоры отключены. Выберите режим, чтобы продолжить сохранённую попытку.'
    on_cover=on_exit
    def pause(self):
        self.on_exit();self.game.save();self.game.scenes.push(EpisodePause(self.game))
    def fault(self,text):
        self.close_devices();self.stage='ready';self.status='Сенсор недоступен: '+text+'. Выберите клавиши или повторите калибровку; штрафа нет.'
    def event(self,event):
        if event.type==pygame.KEYDOWN:
            if event.key==pygame.K_ESCAPE:self.pause();return
            self.held.add(event.key)
        elif event.type==pygame.KEYUP:self.held.discard(event.key)
        elif event.type==pygame.WINDOWFOCUSLOST:self.pause();return
        super().event(event)
    def update(self,dt):
        self.age+=dt
        if self.stage not in ('running','calibration'):return
        now=time.monotonic()
        for key,session in [('mic',self.mic),('camera',self.camera_session)]:
            for event in session.poll():
                if event['type']=='sample':self.signals[key]=(event.get('at',now),event)
                elif event['type'] in ('error','stopped'):
                    self.fault(event.get('message','поток остановлен'));return
        db=-75. if pygame.K_SPACE in self.held else -10.
        motion=1.4 if self.held.intersection({pygame.K_w,pygame.K_a,pygame.K_s,pygame.K_d,pygame.K_UP,pygame.K_DOWN,pygame.K_LEFT,pygame.K_RIGHT}) else 0.
        reliable=True
        for key in self.requested:
            sample=self.signals.get(key)
            if sample is None or now-sample[0]>.6:reliable=False;continue
            value=sample[1]
            if key=='mic':db=value['db']
            else:motion=value['motion'];reliable=reliable and value['present'] and value['reliable']
        if self.mode=='sensor' and 'mic' not in self.requested:db=-75. if pygame.K_SPACE in self.held else -10.
        if self.mode=='sensor' and 'camera' not in self.requested:motion=0. if not self.held.intersection({pygame.K_w,pygame.K_a,pygame.K_s,pygame.K_d}) else 1.4
        if not reliable:
            self.fault_time+=dt;self.status='Нет надёжного сигнала: таймер остановлен. Верните лицо в кадр / стабилизируйте свет, либо выберите клавиши.'
            if self.fault_time>8:self.fault('нет надёжных данных')
            return
        self.fault_time=0.
        if self.stage=='calibration':
            if self.trial.calibrate(dt,db,motion,reliable):self.stage='running';self.status='Нурс: уведомления отключены. Он прямо перед тобой…'
            return
        result=self.trial.step(dt,db,motion,reliable)
        t=self.game.state.thriller;t['hide_elapsed']=self.trial.elapsed;t['danger']=self.trial.danger
        if self.trial.danger>.25:self.status='Преследователь: «Что это было?..»'
        if self.trial.danger>.7:self.status='Преследователь: «Я знаю, что ты здесь!»'
        if not self.sensors_active and self.age-self.last_beat>.85:
            self.game.audio.play('heartbeat');self.game.audio.play('step');self.last_beat=self.age
        if result:
            self.close_devices();self.stage='finished';self.game.story_manager.hide_result(result);self.game.save();show_phase(self.game)
    def draw(self,screen):
        screen.fill((8,14,24));t=self.game.state.thriller
        table='cover_table' in t['items']
        pygame.draw.rect(screen,(40,41,44),(80,145,1120,370))
        for x in range(80,1200,48):pygame.draw.line(screen,(26,30,36),(x,145),(x,515))
        offset=0 if self.game.settings.reduced_motion else int(math.sin(self.age*11)*t['danger']*4)
        enemy_x=810-int(110*math.sin(self.age*.35))
        pygame.draw.ellipse(screen,(5,9,15),(enemy_x-45,405,210,40))
        self.game.art.person(screen,(enemy_x+offset,416),int(self.age*5),character='pursuer')
        entry=1 if self.game.settings.reduced_motion else min(1,self.age/1.2)
        if table:
            actor=pygame.Surface((100,110),pygame.SRCALPHA);self.game.art.person(actor,(50,100),action=True)
            screen.blit(pygame.transform.scale(actor,(90,int(110-35*entry))),(int(430-230*entry),390))
        else:self.game.art.person(screen,(int(470-225*entry),int(500-40*entry)),int(self.age*7),action=True)
        if table:
            pygame.draw.rect(screen,(85,62,50),(150,365,260,28))
            for x in (160,390):pygame.draw.rect(screen,(60,45,40),(x,390,18,90))
        else:
            pygame.draw.rect(screen,(69,51,45),(150,190,225,295),8)
            pygame.draw.rect(screen,(39,34,36),(160,200,int(110*entry),275));pygame.draw.rect(screen,(100,77,60),(264,325,5,20))
        for inset in range(0,65,8):pygame.draw.rect(screen,(7+inset//10,12+inset//10,20),(inset,inset,1280-inset*2,620-inset*2),8)
        self.game.ui.text(screen,'ТЫ ПРЯЧЕШЬСЯ / НЕ ДВИГАЙСЯ',(45,32),32,CYAN)
        self.game.ui.paragraph(screen,self.status,(45,88,1180,80),21)
        noise=self.trial.noise if self.trial else 0;motion=self.trial.motion if self.trial else 0
        for i,(label,value) in enumerate([('Шум',noise),('Движение',motion),('Опасность',t['danger'])]):
            x=45+i*410;self.game.ui.text(screen,f'{label}: {round(value*100)}%',(x,530),20)
            pygame.draw.rect(screen,(40,52,64),(x,562,370,15));pygame.draw.rect(screen,RED if i==2 else CYAN,(x,562,int(370*value),15))
        remain=max(0,15-t['hide_elapsed']);self.game.ui.text(screen,f'Осталось {remain:.1f} с · Микрофон: {"ВКЛ" if self.mic.active else "выкл"} · Камера: {"ВКЛ" if self.camera_session.active else "выкл"}',(45,600),20,CYAN)
        self.draw_buttons(screen)


class ChaseScene(Scene):
    def __init__(self,game):
        super().__init__(game);self.steps=data('chase');self.age=0.;self.cooldown=0.;self.physical=set();self.message='Нурс: беги! Следи за препятствием.';self.make_prompt()
    def on_cover(self):
        self.physical.clear();self.qte.held.clear()

    def make_prompt(self):
        index=self.game.state.thriller['chase_step']
        self.qte=QTESystem(self.steps[min(index,len(self.steps)-1)],self.game.settings.qte_mode,self.game.state.thriller['leg_injured'])
        self.qte.blocked=set(self.physical)
    def event(self,event):
        if event.type==pygame.WINDOWFOCUSLOST:self.physical.clear();self.qte.held.clear();self.game.scenes.push(EpisodePause(self.game));return
        if event.type not in (pygame.KEYDOWN,pygame.KEYUP):return
        if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:
            self.physical.clear();self.qte.held.clear();self.game.scenes.push(EpisodePause(self.game));return
        names={pygame.K_SPACE:'space',pygame.K_e:'e',pygame.K_a:'a',pygame.K_d:'d',pygame.K_LSHIFT:'shift',pygame.K_RSHIFT:'shift',pygame.K_f:'f'}
        key=names.get(event.key)
        if key is None:return
        if event.type==pygame.KEYUP:self.physical.discard(key);self.qte.key(key,False)
        elif key not in self.physical:
            self.physical.add(key)
            if not self.cooldown:self.qte.key(key,True)
    def update(self,dt):
        self.age+=dt
        if self.game.state.thriller['chase_step']>=len(self.steps) and not self.cooldown:
            self.game.story_manager.finish_chase();self.game.save();show_phase(self.game);return
        if self.cooldown:
            self.cooldown=max(0,self.cooldown-dt)
            if self.cooldown==0:
                if self.game.state.thriller['chase_step']>=len(self.steps):self.game.story_manager.finish_chase();self.game.save();show_phase(self.game)
                else:self.make_prompt()
            return
        result=self.qte.update(dt)
        if result is not None:
            self.game.story_manager.qte_result(self.qte.definition['id'],result,self.qte.route)
            self.message='Нурс: получилось, дальше!' if result else 'Нурс: не останавливайся! Ошибка изменила маршрут.'
            self.game.audio.play('step' if result else 'struggle');self.cooldown=.8;self.game.save()
    def draw(self,screen):
        screen.fill((13,23,37));scroll=0 if self.game.settings.reduced_motion else int(self.age*200)%160
        for x in range(-160,1400,160):
            pygame.draw.rect(screen,(34,43,54),(x-scroll,160,120,290));pygame.draw.rect(screen,(62,96,108),(x-scroll+15,190,60,85))
        pygame.draw.rect(screen,(42,41,45),(0,460,1280,150))
        jump=0
        if self.qte.definition['id']=='jump' and self.cooldown and self.qte.result:jump=int(80*math.sin(math.pi*(.8-self.cooldown)/.8))
        if self.cooldown and not self.qte.result:
            layer=pygame.Surface((120,120),pygame.SRCALPHA);self.game.art.person(layer,(60,100));screen.blit(pygame.transform.rotate(layer,75),(400,440))
        else:self.game.art.person(screen,(470,500-jump),int(self.age*12),action=self.qte.definition['id'] in ('push','door'))
        self.game.art.person(screen,(180-int(110*self.cooldown) if self.qte.definition['id']=='push' and self.qte.result else 180,500),int(self.age*11),character='pursuer')
        if self.qte.definition['id']=='door':pygame.draw.rect(screen,(74,57,49),(800,230,80,280))
        else:pygame.draw.rect(screen,(107,81,57),(780,440,130,65))
        self.game.ui.text(screen,'ПОГОНЯ / '+str(min(5,self.game.state.thriller['chase_step']+1))+' из 5',(40,30),32,CYAN)
        self.game.ui.text(screen,self.message,(40,94),22)
        self.game.ui.panel(screen,(180,540,920,84),RED if self.cooldown and not self.qte.result else CYAN)
        self.game.ui.text(screen,self.qte.definition['label'],(210,563),32)
        progress=1 if math.isinf(self.qte.limit) else max(0,1-self.qte.elapsed/self.qte.limit)
        pygame.draw.rect(screen,(45,52,63),(180,634,920,15));pygame.draw.rect(screen,CYAN,(180,634,int(920*progress),15))
        self.game.ui.text(screen,f'Серия: {self.qte.presses} · удержание: {self.qte.hold_time:.1f} с · Esc — пауза',(180,668),20,MUTED)


def finish_branch(game,ending):
    from src.systems.story_manager import ending_allowed
    if game.state.ending or not game.access.full_version_unlocked or not ending_allowed(game.state,game.evidence,ending):
        game.toast('Для этой развязки ещё не выполнены условия.');return False
    game.state.thriller['ending_id']=ending;game.state.ending=ending
    game.scenes.replace(BranchEnding(game,ending));game.record_result();game.save();return True


class BranchFinale(Message):
    def __init__(self,game):
        from src.systems.story_manager import ending_allowed
        super().__init__(game,'Развязка / последствия','Полная цепочка, переданная копия, судьба Аружан и события на складе определяют доступные исходы. Для раскрытия дела предъявите цепочку Сарсенову. Секрет требует записи встречи, скрытых материалов, подсказки Нурса и безошибочной погони.')
        for i,(label,key) in enumerate([('Правда раскрыта','truth'),('Цена правды','price'),('Скрытая правда','secret')]):
            self.button(label,(50+i*400,410,380,58),lambda key=key:finish_branch(game,key),ending_allowed(game.state,game.evidence,key))
        self.button('Обвинить Айдоса без полной цепочки…',(50,490,1120,54),self.false_charge,game.state.thriller['phase']=='resolved' and not game.evidence.can_finalize())
    def false_charge(self):
        panel=Message(self.game,'Обвинить Айдоса?','У вас нет проверенной цепочки против охранника. Это завершит дело ложным обвинением; настоящий организатор уйдёт. Можно вернуться к расследованию.')
        def confirm():self.game.story_manager.log('false_charge','Никита сознательно предъявил непроверенное обвинение Айдосу.');finish_branch(self.game,'false_accusation')
        panel.button('Подтвердить обвинение',(330,622,650,52),confirm);self.game.scenes.push(panel)


class BranchEnding(Scene):
    CONTENT=data('branch_endings')
    def __init__(self,game,ending):
        super().__init__(game);self.ending=ending;self.age=0.;self.revealed=False
        self.title,self.text,self.speaker,self.color=self.CONTENT[ending]
        self.button('Показать итог',(50,630,350,52),lambda:setattr(self,'revealed',True))
        self.button('Главное меню',(830,630,400,52),game.to_menu)
    def update(self,dt):self.age+=dt
    def draw(self,screen):
        screen.fill(BG)
        if self.ending=='prisoner':
            for x in range(40,1280,90):pygame.draw.rect(screen,self.color,(x,0,15,610))
        elif self.ending=='price':
            pygame.draw.rect(screen,self.color,(900,170,120,220),4);pygame.draw.circle(screen,(195,155,100),(960,430),12)
        elif self.ending=='secret':
            for i in range(18):pygame.draw.line(screen,self.color,(300,160+i*22),(1180-(i%4)*100,160+i*22),2)
        elif self.ending=='false_accusation':
            for x in range(350,1200,100):pygame.draw.rect(screen,self.color,(x,130,8,420))
        else:
            for x in range(350,1200,120):pygame.draw.rect(screen,self.color,(x,120+(x%3)*40,90,300))
        self.game.ui.panel(screen,(25,25,1230,105),self.color);self.game.ui.pixel(screen,self.title,(50,55),42,CYAN)
        self.game.art.portrait(screen,self.speaker,(50,185))
        self.game.ui.panel(screen,(250,175,970,350),self.color)
        text=self.text if self.revealed or self.game.settings.reduced_motion else self.text[:int(self.age*self.game.settings.text_speed)]
        self.game.ui.paragraph(screen,text,(275,205,920,230),26)
        self.game.ui.text(screen,f'Улики: {len(self.game.state.evidence_ids)} · Репутация: {self.game.state.reputation} · Ошибки погони: {sum(not r["success"] for r in self.game.state.thriller["chase_results"])}',(275,465),20,CYAN)
        self.draw_buttons(screen)
