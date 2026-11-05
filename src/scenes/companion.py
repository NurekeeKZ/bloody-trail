from src.scenes.base import Scene
from src.ai.companion import MODES
class CompanionCommands(Scene):
    def __init__(self,game,companion):
        super().__init__(game);self.companion=companion
        for i,(key,label) in enumerate(MODES.items()):
            self.button(label,(360,210+i*76,560,58),lambda key=key:self.choose(key))
        self.button('Назад',(360,550,560,48),game.scenes.pop)
    def choose(self,key):
        self.companion.command(key);self.game.save();self.game.scenes.pop()
    def draw(self,screen):
        self.header(screen,'N.U.R.S. / режим сопровождения','F — управление спутником · T — голос и текст')
        self.game.art.portrait(screen,'nurs',(90,240));self.draw_buttons(screen)
