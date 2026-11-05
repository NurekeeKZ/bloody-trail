import pygame
from src.scenes.base import Scene
from src.scenes.overlays import Assistant
from src.core.config import CYAN, MUTED
from src.ai.devices import SensorSession


class DeviceList(Scene):
    """Expanded device selector with pagination; labels are supplied by the drivers."""
    def __init__(self,game,title,rows,selected):
        super().__init__(game);self.title=title;self.rows=rows;self.selected=selected;self.page=0;self.rebuild()
    def rebuild(self):
        self.buttons=[]
        for i,(name,key) in enumerate(self.rows[self.page*7:self.page*7+7]):
            self.button(name,(45,180+i*56,1190,48),lambda key=key:self.choose(key))
        self.button('Назад',(45,640,250,48),self.game.scenes.pop)
        self.button('Предыдущие',(340,640,300,48),lambda:self.turn(-1),self.page>0)
        self.button('Следующие',(680,640,300,48),lambda:self.turn(1),(self.page+1)*7<len(self.rows))
    def turn(self,step):self.page+=step;self.rebuild()
    def choose(self,key):self.game.scenes.pop();self.selected(key)
    def draw(self,screen):
        self.header(screen,self.title,'Системное устройство по умолчанию выбирается операционной системой.')
        self.draw_buttons(screen)


class MicrophoneTest(Assistant):
    def __init__(self,game):
        super().__init__(game)
        self.response='Тест: нажмите микрофон, разрешите попытку и скажите «Покажи улики». Команда здесь не изменяет дело.'
    def execute(self,intent):
        self.on_exit();self.response='Проверка успешна. Определён интент: '+intent+'. Аудио не сохранялось.'


class AudioDevices(Scene):
    labels=[('volume','Общая'),('music_volume','Музыка'),('environment_volume','Окружение'),
            ('dialogue_volume','Диалоги / текстовый сигнал'),('effects_volume','Эффекты'),('rain_volume','Дождь')]
    def __init__(self,game):
        super().__init__(game);self.section='levels';self.discovery=SensorSession();self.inputs=[];self.status='Определение микрофонов…';self.refresh();self.rebuild()
    def refresh(self):
        try:self.discovery.start('devices',consent=True)
        except Exception as exc:self.status='Устройства недоступны: '+str(exc)
    def on_exit(self):self.discovery.close()
    def update(self,dt):
        for event in self.discovery.poll():
            if event['type']=='devices':
                self.inputs=event['devices'];self.status=f'Найдено микрофонов: {len(self.inputs)}. Захват выключен.'
                key=self.game.settings.microphone_device
                if key and not any(d['key']==key for d in self.inputs):
                    self.game.set_setting('microphone_device','');self.status='Сохранённый микрофон отключён. Выбран системный вход.'
                self.rebuild()
            elif event['type']=='error':self.status='Устройства недоступны: '+event['message']
    def tab(self,name):self.section=name;self.rebuild()
    def change(self,key,value):self.game.set_setting(key,value);self.rebuild()
    def input(self):
        rows=[('Системное устройство по умолчанию','')]+[(d['name'],d['key']) for d in self.inputs]
        self.game.scenes.push(DeviceList(self.game,'Выбор микрофона',rows,lambda key:self.change('microphone_device',key)))
    def output(self):
        names,error=self.game.audio.output_devices()
        if error:self.status='Не удалось получить выходы: '+error
        self.game.scenes.push(DeviceList(self.game,'Динамики / наушники',[('Системное устройство по умолчанию','')]+[(n,n) for n in names],self.select_output))
    def select_output(self,key):
        success=self.game.audio.switch_output(key)
        self.game.set_setting('output_device',key if success else '')
        self.status='Выход переключён.' if success else self.game.audio.error
        self.rebuild()
    def rebuild(self):
        self.buttons=[]
        self.button('Уровни звука',(45,170,350,45),lambda:self.tab('levels'))
        self.button('Устройства',(420,170,350,45),lambda:self.tab('devices'))
        self.button('Назад',(45,650,260,45),self.game.scenes.pop)
        if self.section=='levels':
            for i,(key,label) in enumerate(self.labels):
                y=240+i*55
                self.button('−',(1030,y,65,40),lambda key=key:self.change(key,max(0,getattr(self.game.settings,key)-10)))
                self.button('+',(1110,y,65,40),lambda key=key:self.change(key,min(100,getattr(self.game.settings,key)+10)))
            self.button('Проверить эффекты',(440,650,350,45),lambda:self.game.audio.play('evidence'))
        else:
            mic=self.game.settings.microphone_device or 'Системное устройство по умолчанию'
            out=self.game.settings.output_device or 'Системное устройство по умолчанию'
            self.button('Микрофон ▾ '+mic,(45,250,1190,50),self.input)
            self.button('Вывод ▾ '+out,(45,315,1190,50),self.output)
            self.button('Проверить микрофон',(45,395,550,50),lambda:self.game.scenes.push(MicrophoneTest(self.game)))
            self.button('Обновить список',(650,395,550,50),self.refresh)
            self.button('Чувствительность −25%',(45,475,400,50),lambda:self.change('microphone_gain',max(25,self.game.settings.microphone_gain-25)))
            self.button('Чувствительность +25%',(780,475,420,50),lambda:self.change('microphone_gain',min(400,self.game.settings.microphone_gain+25)))
    def event(self,event):
        if self.section=='levels' and (event.type==pygame.MOUSEBUTTONDOWN and event.button==1 or event.type==pygame.MOUSEMOTION and event.buttons[0]):
            for i,(key,_) in enumerate(self.labels):
                if pygame.Rect(440,240+i*55,540,40).collidepoint(event.pos):self.change(key,round(max(0,min(100,(event.pos[0]-440)/540*100))));return
        super().event(event)
    def draw(self,screen):
        self.header(screen,'Аудио и устройства','Выбор устройств не включает запись. Каждая попытка требует согласия.')
        if self.section=='levels':
            for i,(key,label) in enumerate(self.labels):
                value=getattr(self.game.settings,key);y=240+i*55
                self.game.ui.text(screen,label,(45,y+8),21)
                pygame.draw.rect(screen,MUTED,(440,y+15,540,12));pygame.draw.rect(screen,CYAN,(440,y+15,round(5.4*value),12))
                self.game.ui.text(screen,str(value),(985,y+6),18,CYAN)
            self.game.ui.text(screen,'Реплики пока без озвучки: «Диалоги» регулирует звук появления текста.',(45,590),20,MUTED)
        else:
            self.game.ui.text(screen,str(self.game.settings.microphone_gain)+'%',(570,489),24,CYAN)
            self.game.ui.paragraph(screen,self.status,(45,555,1150,75),20,MUTED)
        self.draw_buttons(screen)
