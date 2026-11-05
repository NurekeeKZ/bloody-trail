"""Replaceable office illustration and evidence facsimiles; no gameplay logic."""
import random
import pygame
from src.core.config import ROOT
from src.ui.prologue_art import blood_mark


class InvestigationArt:
    def __init__(self):
        self.cache = {}

    def image(self, relative, size):
        key = (relative, tuple(size))
        if key not in self.cache:
            path = (ROOT / relative).resolve()
            try:
                if not path.is_relative_to(ROOT):
                    raise ValueError('Asset outside project')
                self.cache[key] = pygame.transform.scale(pygame.image.load(str(path)).convert(), size)
            except (OSError, ValueError, pygame.error):
                fallback = pygame.Surface(size)
                fallback.fill((30, 47, 61))
                pygame.draw.rect(fallback, (93, 156, 168), fallback.get_rect(), 2)
                self.cache[key] = fallback
        return self.cache[key]

    def background(self, screen, content, old_art):
        path = ROOT / content.get('background', '__missing__')
        if content.get('background') and path.is_file():
            screen.blit(self.image(content['background'], (1280, 720)), (0, 0))
        elif content.get('renderer') == 'apartment':
            from src.ui.apartment_art import apartment
            screen.blit(apartment(),(0,0))
        elif content.get('renderer') == 'port':
            port_scene(screen, old_art)
        elif content.get('renderer') == 'office':
            if 'office_fallback' not in self.cache:
                self.cache['office_fallback'] = office()
            screen.blit(self.cache['office_fallback'], (0, 0))
        else:
            old_art.room(screen, content['hotspots'])


def office():
    s = pygame.Surface((640, 360))
    rng = random.Random(2035)
    s.fill((13, 22, 34))
    for y in range(54, 306):
        shade = int(12 * (1 - abs(y - 160) / 160))
        pygame.draw.line(s, (20 + shade, 30 + shade, 41 + shade), (14, y), (626, y))
    for y in range(64, 255, 17):
        pygame.draw.line(s, (20, 30, 40), (15, y), (625, y))
        for x in range(15 + (y % 2) * 35, 625, 70):
            pygame.draw.line(s, (22, 32, 43), (x, y), (x, y + 17))
    # Window recess, wet skyline and crossbars.
    pygame.draw.rect(s, (8, 14, 24), (28, 64, 134, 122))
    pygame.draw.rect(s, (64, 85, 95), (31, 67, 128, 115), 3)
    pygame.draw.rect(s, (14, 35, 53), (35, 71, 120, 106))
    for i in range(10):
        x, height = 36 + i * 12, 20 + (i * 19) % 68
        pygame.draw.rect(s, (20, 47, 64), (x, 172 - height, 10, height))
        for y in range(176 - height, 167, 9):
            pygame.draw.rect(s, (101, 127, 124) if i % 3 else (161, 58, 69), (x + 3, y, 2, 3))
    for _ in range(60):
        x, y = rng.randrange(36, 152), rng.randrange(74, 170)
        pygame.draw.line(s, (67, 112, 137), (x, y), (x - 2, y + 6))
    for x in (75, 116):
        pygame.draw.line(s, (55, 76, 86), (x, 69), (x, 178), 3)
    pygame.draw.line(s, (55, 76, 86), (33, 118), (157, 118), 3)
    pygame.draw.rect(s, (81, 90, 91), (25, 181, 141, 6))
    # Filing cabinets and dossiers.
    pygame.draw.rect(s, (18, 24, 32), (560, 65, 66, 150))
    for y in (69, 124, 178):
        pygame.draw.rect(s, (51, 61, 66), (562, y, 61, 48))
        pygame.draw.rect(s, (23, 34, 43), (565, y + 3, 55, 37))
        for i in range(6):
            x = 568 + i * 8
            pygame.draw.rect(s, [(106, 87, 68), (52, 86, 91), (83, 57, 62)][i % 3], (x, y + 7 + i % 3 * 2, 6, 30))
            pygame.draw.rect(s, (186, 184, 157), (x + 1, y + 16, 4, 8))
    # Investigation corkboard and red string.
    pygame.draw.rect(s, (8, 16, 23), (377, 65, 165, 114))
    pygame.draw.rect(s, (104, 76, 59), (382, 70, 155, 105))
    pygame.draw.rect(s, (153, 114, 76), (382, 70, 155, 105), 3)
    for _ in range(600):
        s.set_at((rng.randrange(386, 533), rng.randrange(74, 171)), (110, 82, 62))
    nodes = [(394, 83), (449, 81), (498, 91), (412, 129), (476, 135)]
    for i, (x, y) in enumerate(nodes):
        pygame.draw.rect(s, (209, 204, 177), (x, y, 25, 27))
        pygame.draw.rect(s, (42, 54, 60), (x + 3, y + 3, 19, 13))
        for line in range(2):
            pygame.draw.line(s, (92, 94, 86), (x + 3, y + 20 + line * 3), (x + 20, y + 20 + line * 3))
        pygame.draw.circle(s, (205, 65, 74), (x + 12, y), 2)
    pygame.draw.lines(s, (174, 46, 61), False, [(406, 83), (461, 81), (424, 129), (510, 91), (488, 135)], 1)
    # Ceiling lamp and warm pool of light.
    pygame.draw.line(s, (88, 83, 71), (323, 53), (323, 80), 2)
    pygame.draw.polygon(s, (50, 52, 54), [(299, 94), (311, 79), (335, 79), (348, 94)])
    pygame.draw.line(s, (233, 186, 112), (301, 95), (346, 95), 3)
    glow = pygame.Surface((640, 360), pygame.SRCALPHA)
    pygame.draw.polygon(glow, (210, 160, 93, 15), [(300, 97), (347, 97), (470, 282), (189, 282)])
    s.blit(glow, (0, 0))
    # Floor perspective and detective's desk.
    pygame.draw.polygon(s, (24, 27, 34), [(0, 267), (640, 267), (640, 360), (0, 360)])
    for x in range(-200, 900, 100):
        pygame.draw.line(s, (43, 42, 44), (320 + (x - 320) // 2, 266), (x, 360))
    for y in (280, 302, 332):
        pygame.draw.line(s, (40, 40, 42), (0, y), (640, y))
    pygame.draw.polygon(s, (91, 61, 47), [(165, 207), (596, 207), (620, 276), (144, 276)])
    for _ in range(190):
        x, y = rng.randrange(168, 590), rng.randrange(210, 272)
        pygame.draw.line(s, (102, 71, 52), (x, y), (min(x + rng.randrange(4, 35), 597), y))
    pygame.draw.rect(s, (49, 37, 35), (148, 277, 467, 25))
    pygame.draw.line(s, (144, 99, 65), (146, 276), (617, 276), 3)
    for x in (160, 560):
        pygame.draw.rect(s, (37, 33, 35), (x, 300, 30, 50))
    # Computer, keyboard, lamp reflections.
    pygame.draw.rect(s, (5, 14, 24), (182, 150, 119, 77))
    pygame.draw.rect(s, (61, 81, 91), (184, 151, 115, 72), 2)
    pygame.draw.rect(s, (17, 64, 78), (189, 156, 104, 60))
    for row in range(8):
        pygame.draw.line(s, (73, 167, 177), (195, 162 + row * 6), (265 - row % 3 * 14, 162 + row * 6))
    pygame.draw.rect(s, (100, 206, 211), (277, 164, 9, 24), 1)
    pygame.draw.rect(s, (31, 40, 45), (228, 224, 26, 11))
    pygame.draw.polygon(s, (26, 37, 45), [(186, 239), (290, 239), (301, 253), (178, 253)])
    for y in range(242, 250, 3):
        for x in range(188, 288, 6):
            pygame.draw.rect(s, (69, 91, 100), (x, y, 4, 2))
    # Documents with photo and stamp.
    pygame.draw.polygon(s, (197, 191, 162), [(328, 220), (414, 224), (422, 264), (325, 259)])
    pygame.draw.rect(s, (51, 51, 58), (335, 227, 40, 25))
    s.blit(blood_mark(36),(336,224))
    for y in (231, 237, 243, 249):
        pygame.draw.line(s, (90, 95, 87), (380, y), (408, y))
    pygame.draw.rect(s, (147, 54, 64), (389, 252, 23, 7), 1)
    # Desk phone and curly cable.
    pygame.draw.polygon(s, (18, 30, 39), [(514, 211), (577, 211), (590, 249), (509, 249)])
    pygame.draw.rect(s, (62, 94, 102), (526, 217, 39, 8))
    for y in range(230, 246, 5):
        for x in range(527, 566, 10):
            pygame.draw.rect(s, (92, 104, 103), (x, y, 6, 3))
    pygame.draw.rect(s, (9, 20, 30), (510, 207, 76, 9), border_radius=3)
    for y in range(220, 265, 3):
        pygame.draw.arc(s, (13, 22, 30), (593, y, 8, 5), 0, 5, 1)
    # Mug, pencils, chair and foreground shadows.
    pygame.draw.ellipse(s, (191, 169, 127), (452, 241, 17, 7))
    pygame.draw.rect(s, (93, 110, 110), (453, 244, 15, 16))
    pygame.draw.circle(s, (131, 146, 140), (470, 249), 5, 2)
    pygame.draw.rect(s, (26, 36, 45), (73, 232, 49, 65), border_radius=7)
    pygame.draw.rect(s, (46, 59, 65), (77, 236, 41, 45), border_radius=5)
    pygame.draw.line(s, (20, 28, 37), (98, 294), (98, 326), 6)
    pygame.draw.line(s, (20, 28, 37), (67, 326), (130, 326), 5)
    return pygame.transform.scale(s, (1280, 720))


def evidence_image(eid):
    s = pygame.Surface((480, 300))
    s.fill((15, 25, 37))
    font = pygame.font.SysFont('tahoma,arial', 18)
    if eid in ('photo', 'blood', 'EVIDENCE_BLOOD_MARK_2020', 'EVIDENCE_BLOOD_MARK_2035'):
        pygame.draw.rect(s, (194, 188, 167), (28, 22, 424, 252))
        pygame.draw.rect(s, (57, 57, 62), (39, 34, 402, 201))
        for y in range(34, 234, 22):
            pygame.draw.line(s, (69, 68, 71), (40, y), (440, y))
        s.blit(blood_mark(180),(145,42))
        s.blit(font.render(('ASTERA / 2020 / ВОСПОМИНАНИЕ' if eid.endswith('2020') else 'ASTERA / 2035 / РЕКОНСТРУКЦИЯ'), True, (45, 48, 53)), (47, 244))
    else:
        pygame.draw.rect(s, (202, 199, 176), (38, 15, 404, 270))
        s.blit(font.render('ОСОБЫЙ ОТДЕЛ / ' + eid.upper(), True, (31, 52, 62)), (56, 33))
        for i in range(10):
            pygame.draw.line(s, (101, 111, 111), (60, 83 + i * 13), (390 - i % 4 * 24, 83 + i * 13), 2)
        pygame.draw.rect(s, (158, 48, 66), (275, 230, 143, 34), 2)
        s.blit(font.render('КОПИЯ / 2035', True, (158, 48, 66)), (282, 236))
    return s


def port_scene(screen, art):
    """Original dock scene; coordinates correspond to JSON hotspots."""
    s = pygame.Surface((640,360))
    s.fill((9,19,32))
    pygame.draw.rect(s,(18,44,59),(0,135,640,110))
    for i in range(38):
        x,y=(i*83)%640,145+(i*29)%93
        pygame.draw.line(s,(39,83,99),(x,y),(x+28,y),1)
    for x in (60,430):
        pygame.draw.line(s,(61,77,86),(x,160),(x,64),6)
        pygame.draw.line(s,(61,77,86),(x,66),(x+150,90),6)
        pygame.draw.line(s,(80,98,107),(x+140,90),(x+140,149),2)
    for x,y,w in ((10,160,150),(350,158,170),(175,140,120)):
        pygame.draw.rect(s,(41,54,68),(x,y,w,80))
        pygame.draw.rect(s,(71,88,101),(x,y,w,80),2)
        for xx in range(x+8,x+w,12):pygame.draw.line(s,(27,41,55),(xx,y+3),(xx,y+76),2)
    pygame.draw.polygon(s,(31,35,45),[(0,230),(640,215),(640,325),(0,325)])
    for x in range(0,640,48):pygame.draw.line(s,(42,47,57),(x,233),(x-80,325),2)
    # Independent server archive on a shipping crate.
    pygame.draw.rect(s,(84,63,51),(245,219,135,50))
    pygame.draw.rect(s,(18,25,36),(255,190,108,48))
    for y in range(197,233,10):
        pygame.draw.rect(s,(63,83,98),(260,y,94,7))
        pygame.draw.rect(s,(91,217,212),(344,y+2,4,3))
    # Secure transmission terminal in foreground.
    pygame.draw.rect(s,(14,23,36),(62,246,124,44))
    pygame.draw.rect(s,(33,90,105),(68,251,112,30))
    for y in range(256,278,7):pygame.draw.line(s,(92,199,207),(73,y),(151,y),2)
    pygame.draw.rect(s,(48,66,79),(61,294,127,8))
    art.person(s,(505,290),captain=True)
    for i in range(70):
        x,y=(i*97)%640,60+(i*37)%250
        pygame.draw.line(s,(40,73,90),(x,y),(x-3,y+9))
    screen.blit(pygame.transform.scale(s,(1280,720)),(0,0))
