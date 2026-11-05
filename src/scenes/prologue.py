import pygame
from src.core.config import data, CYAN, MUTED
from src.scenes.base import Scene, Message
from src.ui.widgets import Typewriter
from src.ui.prologue_art import family_room, blood_mark, portrait


class Prologue(Scene):
    def __init__(self,game,replay=False):
        super().__init__(game);self.replay=replay;self.steps=data('prologue');self.index=0;self.age=0;self.text_clock=0;self.enter()
    @property
    def audio_mode(self):return 'aftermath' if self.step['stage'] in ('aftermath','mark','title','present') else 'prologue'
    def enter(self):
        self.step=self.steps[self.index];self.writer=Typewriter(self.step['text']);self.age=0;self.text_clock=0;self.transitioning=False;self.fade_out=0;self.cues=set()
        if self.step.get('sound'):self.game.audio.play(self.step['sound'])
    def advance(self):
        if len(self.writer.visible)<len(self.writer.text):self.writer.finish();return
        if not self.transitioning: self.transitioning=True;self.fade_out=0
    def finish(self):
        if self.replay:self.game.scenes.pop()
        else:self.game.complete_prologue()
    def event(self,event):
        if event.type==pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE,pygame.K_RETURN):self.advance()
            elif event.key==pygame.K_ESCAPE:
                confirm=Message(self.game,'Пропустить воспоминание?','Обязательные сведения о прошлом Никиты сохранятся. Улика из воспоминания не доказывает личность убийцы.')
                confirm.button('Пропустить',(320,622,500,52),self.skip);self.game.scenes.push(confirm)
    def skip(self):
        self.game.scenes.pop();self.finish()
    def update(self,dt):
        if self.transitioning:
            self.fade_out+=dt
            if self.fade_out>=.35:
                self.index+=1
                if self.index>=len(self.steps):self.finish();return
                self.enter()
        if self.step['stage']=='night':
            for at,cue in ((.8,'step'),(1.3,'step'),(1.8,'whisper')):
                if self.age>=at and at not in self.cues:self.cues.add(at);self.game.audio.play(cue)
        self.age+=dt;self.writer.update(dt*self.game.settings.text_speed/48)
        if len(self.writer.visible)<len(self.writer.text):
            self.text_clock+=dt
            if self.text_clock>.13:self.text_clock=0;self.game.audio.play('dialogue')
    def draw(self,screen):
        stage=self.step['stage'];screen.fill((5,9,18))
        if stage == 'photo':
            screen.blit(self.game.investigation_art.image('assets/evidence/photo.png',(680,425)),(300,90))
        elif stage not in ('title','present'):
            room=family_room(self.game,stage,self.age)
            if stage=='mark':
                t=min(1,self.age/7);r=pygame.Rect(round(130*t),round(45*t),round(640-320*t),round(360-180*t));room=pygame.transform.scale(room.subsurface(r),(640,360))
            elif not self.game.settings.reduced_motion:
                room=pygame.transform.scale(room,(660,372));room=room.subsurface((round(10+8*min(1,self.age/5)),4,640,360))
            screen.blit(pygame.transform.scale(room,(1280,720)),(0,0))
        pygame.draw.rect(screen,(5,9,18),(0,0,1280,85))
        self.game.ui.text(screen,self.step['title'],(40,28),30,CYAN)
        if stage in ('title','present'):self.game.ui.paragraph(screen,self.step['title'],(150,225,980,180),44,CYAN)
        self.game.ui.panel(screen,(30,515,1220,165))
        screen.blit(portrait(self.game,self.step['speaker']),(44,526))
        # Portrait crop stays inside dialogue panel; labels identify the family member.
        self.game.ui.text(screen,self.step['speaker'],(220,534),22,CYAN)
        self.game.ui.paragraph(screen,self.writer.visible,(220,570,990,92),24)
        self.game.ui.text(screen,'Space / Enter — дальше · Esc — пропуск с подтверждением',(35,692),17,MUTED)
        if self.transitioning and not self.game.settings.reduced_motion:
            veil=pygame.Surface((1280,720));veil.fill((0,0,0));veil.set_alpha(round(255*min(1,self.fade_out/.35)));screen.blit(veil,(0,0))
        if self.age<.65 and not self.game.settings.reduced_motion:
            veil=pygame.Surface((1280,720));veil.fill((0,0,0));veil.set_alpha(round(255*(1-self.age/.65)));screen.blit(veil,(0,0))


class PresentBriefing(Message):
    def __init__(self,game):
        super().__init__(game,'2035 / капитан Нурсултан Ермеков','«Волков, новое дело. Архивист Азамат Нурланов. Тело обнаружили сегодня утром». На столе фотографии, документы и терминал N.U.R.S.')
        self.buttons=[]
        for i,(label,kind) in enumerate([('Изучить место преступления / фото','photo'),('Изучить документы жертвы','documents'),('Спросить N.U.R.S. о следах','assistant')]):
            self.button(label,(50,380+i*66,1170,54),lambda kind=kind:self.choose(kind))
        self.button('Начать исследование участка',(50,622,700,52),self.begin)
    def choose(self,kind):
        if kind=='photo':
            added=self.game.evidence.collect('photo');self.game.save()
            if not added:
                from src.scenes.evidence_board import EvidenceDetail
                self.game.scenes.push(EvidenceDetail(self.game,'photo'))
        elif kind=='documents':
            self.game.scenes.push(Message(self.game,'Документы Нурланова','Архивист работал с материалами 2020 года. Метаданные изучите на компьютере в кабинете; затем проверьте связь на доске.'))
        else:
            from src.scenes.overlays import Assistant
            a=Assistant(self.game);a.response='На снимке необычный след. Сравните его с воспоминанием, затем ищите независимый архивный протокол. Личность преступника неизвестна.';self.game.scenes.push(a)
    def begin(self):
        from src.scenes.exploration import Exploration
        self.game.scenes.replace(Exploration(self.game));self.game.save()


class Flashback(Prologue):
    def __init__(self,game):
        Scene.__init__(self,game);self.replay=False;self.index=0;self.age=0;self.text_clock=0
        lines=[('Никита','Нет… Этого не может быть.'),('N.U.R.S.','Никита, твой пульс участился. Ты узнал этот символ?'),('Никита','Я видел его раньше. Пятнадцать лет назад.'),('N.U.R.S.','В архиве найдено частичное совпадение с материалами дела Сейтовых от 2020 года. Нужен независимый протокол.'),('Никита','Тот, кто убил Нурланова, может быть связан с убийством моих родителей.')]
        self.steps=[dict(stage='photo' if i==0 else 'flashback',title='2020 → 2035 / воспоминание',speaker=n,text=t,sound='memory' if i==0 else '') for i,(n,t) in enumerate(lines)];self.enter()
    @property
    def audio_mode(self):return 'aftermath'
    def finish(self):self.game.scenes.pop();self.game.save()

    def draw(self,screen):
        super().draw(screen)
        if self.index==0 and self.age<.18 and not self.game.settings.reduced_motion:
            flash=pygame.Surface((1280,720));flash.fill((145,190,205));flash.set_alpha(round(80*(1-self.age/.18)));screen.blit(flash,(0,0))
