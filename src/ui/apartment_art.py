"""Original temporary apartment illustration. Coordinates match JSON hotspots."""
import pygame

def apartment():
    s=pygame.Surface((640,360));s.fill((56,43,43))
    for y in range(54,245,12):pygame.draw.line(s,(65,49,46),(0,y),(640,y))
    pygame.draw.polygon(s,(91,63,49),[(0,245),(640,245),(640,360),(0,360)])
    for y in range(250,360,15):pygame.draw.line(s,(58,43,39),(0,y),(640,y))
    # Crooked painting, old river skyline.
    pygame.draw.polygon(s,(165,128,77),[(40,92),(136,85),(140,174),(44,181)])
    pygame.draw.polygon(s,(35,55,62),[(45,98),(131,91),(135,169),(49,175)])
    for i in range(6):pygame.draw.rect(s,(77,83,76),(52+i*12,116+i%3*8,9,35-i%3*8))
    pygame.draw.line(s,(152,143,101),(49,155),(134,148),2)
    # Bookcase with a single displaced blue spine.
    pygame.draw.rect(s,(91,60,46),(195,80,105,85))
    for row in (85,124):
        for i in range(10):
            color=(50,110,135) if i==5 else (91+i*7,76,58)
            pygame.draw.rect(s,color,(201+i*9,row-(4 if i==5 else 0),7,30))
        pygame.draw.rect(s,(151,109,69),(196,row+31,104,4))
    # Bed and window establish a residential room, not a police office.
    pygame.draw.rect(s,(14,29,42),(345,65,135,63))
    for x in (346,410,479):pygame.draw.line(s,(109,106,91),(x,65),(x,128),2)
    for i in range(18):
        x=350+i*7;y=70+i%4*10;pygame.draw.line(s,(72,107,125),(x,y),(x-2,y+9))
    pygame.draw.rect(s,(118,89,78),(525,190,105,85));pygame.draw.rect(s,(186,166,132),(533,195,88,22))
    # Desk and computer (760,275,280,190 in logical coordinates).
    pygame.draw.rect(s,(115,80,54),(368,213,150,33));pygame.draw.rect(s,(29,31,40),(383,141,121,73))
    pygame.draw.rect(s,(40,76,83),(389,147,109,59));pygame.draw.rect(s,(146,169,152),(432,164,23,23),2)
    pygame.draw.rect(s,(43,40,43),(378,227,140,12))
    # Photos on a low table, offset paper corners.
    pygame.draw.rect(s,(113,81,61),(192,189,151,100))
    for x in (205,265):
        pygame.draw.rect(s,(190,179,144),(x,203,52,67));pygame.draw.rect(s,(71,72,70),(x+5,209,42,34))
        pygame.draw.line(s,(113,105,83),(x+7,252),(x+43,252),2)
    # Rug has a raised corner (discoverable without Q).
    pygame.draw.polygon(s,(119,54,56),[(50,240),(153,245),(159,300),(51,301)])
    pygame.draw.rect(s,(181,125,84),(56,250,92,43),2)
    for x in range(60,148,12):pygame.draw.line(s,(157,96,73),(x,253),(x+5,290))
    pygame.draw.polygon(s,(192,146,104),[(143,290),(159,285),(159,300)])
    return pygame.transform.scale(s,(1280,720))
