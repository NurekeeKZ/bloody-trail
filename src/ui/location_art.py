"""Original low resolution map props; no external art dependencies."""
import pygame

def decorate(s,location,world):
    accent=tuple(world.get('accent',(70,140,170)))
    for kind,box in world.get('decor',[]):
        r=pygame.Rect([v//3 for v in box]);x,y,w,h=r
        if kind in ('rug','corridor','platform'):
            pygame.draw.rect(s,(104,63,59) if kind=='rug' else accent,r)
            pygame.draw.rect(s,(46,39,45),r.inflate(-8,-8),2)
            if kind=='platform':
                for xx in range(x,x+w,12):pygame.draw.rect(s,(39,34,44),(xx,y,5,h))
        elif kind=='puddle':
            pygame.draw.ellipse(s,(39,64,82),r);pygame.draw.line(s,(77,116,132),(x+8,y+h//2),(x+w-8,y+h//2))
        elif kind=='papers':
            for dx,dy in [(0,4),(15,0),(7,12)]:pygame.draw.rect(s,(179,170,143),(x+dx,y+dy,16,20))
        elif kind=='crane':
            pygame.draw.line(s,(157,124,68),(x,y),(x+w,y),4);pygame.draw.line(s,(157,124,68),(x,y),(x,y+h),4)
            pygame.draw.line(s,(136,141,139),(x+w,y),(x+w,y+h//2),2)
        elif kind in ('tracks','stairs'):
            pygame.draw.rect(s,(13,19,26),r)
            for yy in range(y,y+h,9):pygame.draw.line(s,(91,97,103),(x,yy),(x+w,yy),2)
        elif kind=='glass':
            pygame.draw.rect(s,(70,110,131),r);pygame.draw.line(s,(143,184,191),r.topleft,r.bottomright,2)
        else:
            colors={'bed':(137,104,87),'kitchen':(121,125,117),'shelves':(82,94,66),'servers':(18,32,45),'container':(85,65,57),'train':(61,86,112),'warehouse':(80,82,86),'books':(98,69,52),'lab':(144,163,166)}
            pygame.draw.rect(s,(8,14,22),r.move(3,4));pygame.draw.rect(s,colors.get(kind,(62,76,83)),r)
            pygame.draw.rect(s,accent,r,1)
            if kind=='bed':
                pygame.draw.rect(s,(194,180,151),(x+5,y+4,w-10,h//3));pygame.draw.line(s,(85,70,68),(x+3,y+h//2),(x+w-3,y+h//2),2)
            elif kind=='train':
                for xx in range(x+5,x+w-12,23):pygame.draw.rect(s,(170,171,126),(xx,y+7,15,13))
            else:
                for yy in range(y+5,y+h-2,10):
                    pygame.draw.line(s,(23,34,40),(x+3,yy),(x+w-3,yy),2)
                    if kind in ('servers','terminal','scanner'):pygame.draw.rect(s,(65,208,180),(x+4,yy-3,3,2))
                    if kind in ('books','shelves'):
                        for xx in range(x+4,x+w-3,6):pygame.draw.rect(s,(126+xx%35,107,76),(xx,yy-7,4,6))
