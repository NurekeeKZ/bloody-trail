"""One canonical asymmetric mark used by both years, photographs and flashbacks."""
import pygame
MARK_POINTS=((19,23,12),(58,66,8),(82,36,5))

def blood_mark(size):
    s=pygame.Surface((100,100),pygame.SRCALPHA)
    for x,y,r in MARK_POINTS:
        pygame.draw.circle(s,(143,33,48),(x,y),r)
        pygame.draw.polygon(s,(143,33,48),[(x-r//2,y),(x,y+2*r),(x+r//2,y)])
    return pygame.transform.scale(s,(size,size))


def family_room(game,stage,age,zoom=False):
    s=pygame.Surface((640,360));dark=stage in ('night','aftermath','mark','flashback')
    s.fill((22,25,36) if dark else (65,48,48))
    pygame.draw.rect(s,(38,31,38) if dark else (106,71,56),(0,240,640,120))
    for y in range(244,360,20):pygame.draw.line(s,(34,28,34),(0,y),(640,y))
    pygame.draw.rect(s,(15,26,43),(30,48,155,145))
    for i in range(20):
        x=35+(i*37)%145;y=50+(i*43+age*36)%134
        pygame.draw.line(s,(53,85,105),(x,y),(x-3,y+10))
    for x in (30,105,181):pygame.draw.line(s,(97,83,76),(x,48),(x,193),4)
    pygame.draw.rect(s,(20,18,28),(520,50,75,198))
    pygame.draw.rect(s,(78,53,49),(516,46,83,205),4)
    pygame.draw.rect(s,(72,47,52),(35,215,145,46))
    pygame.draw.rect(s,(128,82,65),(250,208,190,20))
    for x in (267,415):pygame.draw.rect(s,(63,44,45),(x,225,12,65))
    pygame.draw.rect(s,(184,176,147),(325,197,44,14))
    pygame.draw.line(s,(49,50,55),(330,200),(361,200),2)
    pygame.draw.line(s,(129,106,72),(215,160),(215,252),4)
    pygame.draw.polygon(s,(81,74,59) if dark else (234,183,99),[(197,133),(234,133),(244,161),(187,161)])
    # Family snapshots and books establish a lived-in room.
    for x in (290,350,410):
        pygame.draw.rect(s,(124,98,72),(x,65,42,55),3)
        pygame.draw.circle(s,(160,129,101),(x+21,83),6)
        pygame.draw.rect(s,(68,80,91),(x+13,91,16,19))
    for x in range(32,165,12):pygame.draw.rect(s,(92+x%30,62,64),(x,207,9,22-x%7))
    def person(kind,feet,small=False):
        layer=pygame.Surface((90,110),pygame.SRCALPHA)
        game.art.person(layer,(45,100),captain=False)
        if kind=='marina':
            pygame.draw.rect(layer,(48,29,31),(31,23,6,25));pygame.draw.rect(layer,(48,29,31),(50,22,7,24))
            pygame.draw.polygon(layer,(109,62,80),[(30,55),(55,55),(62,82),(25,82)])
        scale=(40,49) if small else (55,67)
        layer=pygame.transform.scale(layer,scale)
        s.blit(layer,(feet[0]-scale[0]//2,feet[1]-scale[1]))
    if stage in ('home','secret'):
        person('pavel',(285,242));person('marina',(435,242))
    childx=480+min(65,age*9) if stage=='home' else 548 if stage=='secret' else 470-min(35,age*5)
    person('nikita',(childx,245),True)
    if stage in ('aftermath','mark','flashback'):
        # Covered silhouettes, no graphic injury.
        for x in (270,385):pygame.draw.ellipse(s,(34,34,45),(x,238,80,24))
        s.blit(blood_mark(75),(320,118))
    if zoom:
        crop=pygame.Rect(260,72,210,150)
        s=pygame.transform.scale(s.subsurface(crop),(640,360))
    return s


def portrait(game,speaker):
    from src.ui.portraits import PortraitManager
    key={'Айгуль':'marina','Ерлан':'pavel','N.U.R.S.':'nurs'}.get(speaker,'nikita')
    return PortraitManager().get(key,size=(105,140))
