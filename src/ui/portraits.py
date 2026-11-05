"""Dedicated authored 96x128 face/shoulder portraits, replaceable PNG assets."""
import pygame
from src.core.config import ROOT

EMOTIONS=('neutral','angry','sad','surprised','thinking','suspicious')
CHARACTERS={
 'nikita':('Никита Волков',(172,124,105),(19,19,28),(70,44,51),False),
 'nurs':('N.U.R.S.',(125,181,199),(13,32,51),(28,67,88),True),
 'sokolov':('Нурсултан Ермеков',(177,137,104),(77,79,84),(29,57,77),False),
 'anna':('Аружан',(183,139,109),(41,27,31),(112,73,64),False),
 'weir':('Данияр Сарсенов',(166,123,99),(31,29,35),(35,37,51),False),
 'pavel':('Ерлан Сейтов',(173,134,103),(53,39,35),(77,78,66),True),
 'marina':('Айгуль Сейтова',(188,144,114),(48,31,31),(104,60,76),False),
 'guard':('Айдос',(168,130,98),(32,29,27),(54,65,65),False),
 'archivist':('Мадина',(184,143,112),(52,35,29),(52,80,65),True),
 'officer':('Алихан',(173,130,97),(28,28,32),(35,62,82),False),
 'commuter':('Асем',(190,147,116),(60,37,30),(102,72,95),False),
 'victim':('Азамат Нурланов',(175,136,105),(58,43,34),(73,71,65),True)}

class PortraitManager:
    def __init__(self, directory=None):
        self.directory=directory or ROOT/'assets/portraits'
        self.cache={}

    def get(self, character, emotion='neutral', size=(168,224)):
        key=(character,emotion,size)
        if key not in self.cache:
            path=self.directory/character/(emotion+'.png')
            if not path.exists():path=self.directory/character/'neutral.png'
            source=pygame.image.load(str(path)) if path.exists() else self.paint(character,'neutral')
            self.cache[key]=pygame.transform.scale(source,size)
        return self.cache[key]

    def draw(self,surface,character,pos,emotion='neutral',size=(168,224)):
        surface.blit(self.get(character,emotion,size),pos)

    @staticmethod
    def paint(character,emotion):
        _,skin,hair,coat,glasses=CHARACTERS.get(character,CHARACTERS['nikita'])
        s=pygame.Surface((96,128));s.fill((10,19,30))
        accent=(52,182,210) if character=='nurs' else (153,55,68)
        for y in range(8,128,8):pygame.draw.line(s,(17,32,46),(4,y),(91,y))
        pygame.draw.rect(s,accent,(90,5,2,118))
        shadow=tuple(max(0,c-37) for c in skin)
        pygame.draw.polygon(s,coat,[(4,128),(7,103),(28,89),(41,85),(65,86),(87,101),(96,128)])
        pygame.draw.polygon(s,(21,28,39),[(31,91),(48,108),(64,88),(76,101),(65,128),(31,128)])
        pygame.draw.polygon(s,shadow,[(37,72),(59,72),(62,94),(49,104),(36,93)])
        pygame.draw.polygon(s,skin,[(25,31),(38,19),(65,23),(73,41),(69,67),(59,82),(43,85),(28,70),(23,48)])
        pygame.draw.polygon(s,shadow,[(25,39),(31,46),(33,67),(44,78),(58,81),(43,85),(28,70),(23,48)])
        pygame.draw.polygon(s,hair,[(20,51),(16,27),(28,13),(52,9),(72,19),(79,35),(70,46),(63,29),(49,33),(35,27),(29,50),(28,63),(23,58)])
        if character in ('anna','marina','commuter','archivist'):
            pygame.draw.polygon(s,hair,[(19,35),(24,42),(25,80),(31,91),(20,86),(15,68)])
        for x,y in [(24,26),(31,20),(42,17),(54,17),(63,23)]:pygame.draw.line(s,tuple(min(255,c+19) for c in hair),(x,y),(x+9,y-4),2)
        for x in (35,58):
            ey=49 if emotion!='sad' else 52
            pygame.draw.rect(s,(227,207,175),(x,ey,11,3 if emotion!='surprised' else 6))
            pygame.draw.rect(s,accent if character=='nurs' else (35,35,40),(x+5,ey,3,4))
            offset=3 if emotion=='angry' else -2 if emotion=='sad' else 0
            pygame.draw.line(s,hair,(x-1,ey-5),(x+11,ey-5+offset),2)
        pygame.draw.lines(s,shadow,False,[(52,49),(50,61),(56,63)],2)
        pygame.draw.line(s,(108,60,59),(43,71),(58,70 if emotion=='suspicious' else 72),2)
        if emotion=='surprised':pygame.draw.rect(s,(78,43,47),(48,70,6,6))
        if emotion=='thinking':pygame.draw.polygon(s,skin,[(64,115),(60,91),(54,77),(59,74),(69,91),(76,117)])
        if glasses:
            for x in (32,56):pygame.draw.rect(s,(45,70,83),(x,45,19,14),1)
            pygame.draw.line(s,(45,70,83),(51,49),(56,49))
        if character=='sokolov':
            pygame.draw.polygon(s,(31,49,65),[(19,27),(24,13),(66,13),(76,27)])
            pygame.draw.rect(s,(181,159,89),(22,25,51,4));pygame.draw.rect(s,(201,177,100),(46,17,7,6))
        if character=='nikita':
            pygame.draw.polygon(s,(176,159,141),[(30,92),(44,99),(41,111)])
            pygame.draw.polygon(s,(154,48,60),[(47,103),(53,103),(57,126),(46,126)])
        if character=='nurs':
            for y in range(4,128,4):pygame.draw.line(s,(39,93,117),(5,y),(89,y),1)
        pygame.draw.rect(s,accent,(0,0,96,128),1)
        return s
