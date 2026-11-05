import pygame
from src.scenes.base import Scene
from src.core.config import CYAN,MUTED

class PuzzleScene(Scene):
    def __init__(self,game,key):
        super().__init__(game);self.key=key;self.puzzle=game.puzzles.definitions[key];self.input='';self.message=self.puzzle['prompt']
        self.order=[]
        self.button('Назад',(44,642,220,48),game.scenes.pop)
        self.button('Подсказка N.U.R.S.',(280,642,330,48),self.hint)
        self.button('Проверить',(950,642,280,48),self.submit)
        if self.puzzle['kind']=='fragments':
            for i,text in enumerate(self.puzzle['fragments']):
                self.button(text,(140,335+i*64,990,52),lambda i=i:self.fragment(i))
            self.button('Сбросить порядок',(640,642,280,48),self.reset)
    def fragment(self,i):
        if str(i+1) not in self.order:self.order.append(str(i+1))
        self.input=''.join(self.order)
    def reset(self):self.input='';self.order=[]
    def hint(self):
        self.message=self.game.hints.next(self.game.state.location);self.game.save()
    def submit(self):
        ok,self.message=self.game.puzzles.solve(self.key,self.input)
        if ok:
            self.game.toast('N.U.R.S.: материал получен. Проверьте его связь с другими источниками на доске.')
        self.game.save()
    def event(self,event):
        if event.type==pygame.TEXTINPUT and self.puzzle['kind'] not in ('fragments','photos'):
            self.input=(self.input+''.join(c for c in event.text if c.isdigit()))[:8]
        if event.type==pygame.KEYDOWN and event.key==pygame.K_BACKSPACE:self.input=self.input[:-1]
        if event.type==pygame.KEYDOWN and event.key==pygame.K_RETURN:self.submit();return
        if event.type==pygame.MOUSEBUTTONDOWN and self.puzzle['kind']=='photos':
            # Difference is the missing blue seal on the lower right of the second photo.
            if pygame.Rect(1000,445,66,65).collidepoint(event.pos):self.input='seal';self.submit();return
            if pygame.Rect(690,330,440,230).collidepoint(event.pos):self.input='other';self.submit();return
        super().event(event)
    def draw(self,screen):
        self.header(screen,self.puzzle['title'],'Осмотрите источники в комнате. Esc — отложить без потери прогресса.')
        self.game.ui.paragraph(screen,self.message,(60,180,1150,110),23)
        if self.puzzle['kind']=='photos':
            for x in (160,690):
                pygame.draw.rect(screen,(180,168,137),(x,330,440,230))
                pygame.draw.rect(screen,(51,55,63),(x+35,355,210,160))
                from src.ui.prologue_art import blood_mark
                screen.blit(blood_mark(100),(x+85,380))
                for dy in range(0,130,22):pygame.draw.line(screen,(124,118,101),(x+265,365+dy),(x+410,365+dy),3)
            pygame.draw.circle(screen,CYAN,(503,477),27,4)
            self.game.ui.text(screen,'Экспертный подлинник',(160,580),22)
            self.game.ui.text(screen,'Неполная копия — найдите отличие',(690,580),22)
        elif self.puzzle['kind']!='fragments':
            self.game.ui.panel(screen,(330,360,620,100))
            self.game.ui.text(screen,self.input or 'Введите код…',(365,391),32,CYAN)
        else:self.game.ui.text(screen,'Порядок: '+self.input,(140,555),24,CYAN)
        self.draw_buttons(screen)
