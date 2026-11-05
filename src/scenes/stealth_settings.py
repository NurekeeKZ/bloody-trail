from src.scenes.base import Scene
from src.core.config import CYAN,MUTED
class StealthSettings(Scene):
    def __init__(self,game):super().__init__(game);self.rebuild()
    def change(self,key,value):self.game.set_setting(key,value);self.rebuild()
    def rebuild(self):
        self.buttons=[];s=self.game.settings
        for i,(key,label) in enumerate([('stealth_noise_sensitivity','Чувствительность шума'),('stealth_motion_sensitivity','Чувствительность движения')]):
            y=260+i*90;value=getattr(s,key)
            self.button(label+f': {value}% −',(50,y,550,54),lambda key=key,value=value:self.change(key,max(50,value-25)))
            self.button('+',(640,y,200,54),lambda key=key,value=value:self.change(key,min(150,value+25)))
        self.button('По умолчанию: '+('клавиши' if s.stealth_manual else 'предлагать сенсоры'),(50,440,790,54),lambda:self.change('stealth_manual',not s.stealth_manual))
        for i,(label,key) in enumerate([('QTE: 3 с','standard'),('QTE: 6 с','easy'),('QTE без таймера','untimed')]):
            self.button(label+(' [выбрано]' if s.qte_mode==key else ''),(50+i*400,530,380,54),lambda key=key:self.change('qte_mode',key))
        self.button('Назад',(50,635,300,50),self.game.scenes.pop)
    def draw(self,screen):
        self.header(screen,'Стелс / доступность','Устройства включаются только после отдельного согласия на попытку.')
        self.game.ui.paragraph(screen,'Большая чувствительность быстрее реагирует на отклонения. Перед захватом — калибровка 2 секунды. Клавиши дают те же улики и концовки. Выбор режима по умолчанию лишь выделяет кнопку; не включает устройства.',(50,185,1140,65),20,MUTED)
        self.draw_buttons(screen)
