"""Code-native pixel art: low resolution layers, nearest-neighbour scaling."""
import random
import pygame
from src.core.config import ROOT


class Art:
    def __init__(self):
        self.cache = {}

    def portrait(self, surface, key, pos):
        from src.ui.portraits import PortraitManager
        if not hasattr(self, 'portraits'): self.portraits = PortraitManager()
        self.portraits.draw(surface, key, pos)

    def person(self, surface, feet, frame=0, facing=1, hologram=False, action=False, captain=False, character=None):
        sprite = pygame.Surface((20, 32), pygame.SRCALPHA)
        # Deliberately authored silhouette: coat, lapels, red tie, swept hair.
        colors = {'h': (18, 18, 28), 's': (188, 144, 126), 'c': (52, 57, 74),
                  'l': (103, 113, 131), 'r': (181, 56, 66), 'b': (17, 27, 43), 'w': (201, 205, 193)}
        rows = ['      hhhhhh        ', '     hhhhhhhh       ', '    hhhhhhhhhh      ',
                '    hhhhssssh       ', '     hssssss        ', '     hssbsss        ',
                '      sssss         ', '       sss          ', '    cclwwlccc       ',
                '   ccclwrlcccc      ', '   cccclrlcccc      ', '   cccclrlcccc      ',
                '   sccclrlcccs      ', '   sccclrlcccs      ', '    ccclrlccc       ',
                '    ccccrcccc       ', '    ccccccccc       ', '    ccccccccc       ',
                '    ccccccccc       ', '    ccc b ccc       ', '     bb   bb        ',
                '     bb   bb        ', '     bb   bb        ', '    bbb   bbb       ']
        if captain:
            colors.update(h=(122, 132, 141), c=(30, 57, 77), l=(163, 147, 91), r=(60, 105, 132))
            rows[0:3] = ['     ccccccccc      ', '    ccllllllccc     ', '     hhhhhhhh       ']
        if character and character not in ('sokolov','briefing'):
            from src.ui.portraits import CHARACTERS
            if character in CHARACTERS:
                _,skin,hair,coat,_=CHARACTERS[character]
                colors.update(s=skin,h=hair,c=coat)
        if character=='pursuer':
            colors.update(h=(12,18,27),s=(61,66,72),c=(23,34,47),l=(39,51,63),r=(62,65,70),w=(67,72,79))
        for y, row in enumerate(rows):
            for x, letter in enumerate(row):
                if letter in colors:
                    color = {'h':(15,60,92),'s':(89,198,220),'c':(28,95,133),'l':(84,181,206),'r':(47,218,229),'b':(15,45,76),'w':(141,221,225)}[letter] if hologram else colors[letter]
                    sprite.set_at((x, y + 4), color)
        if frame % 2:
            pygame.draw.rect(sprite, (17, 27, 43), (5, 27, 3, 3))
        if action:
            pygame.draw.rect(sprite, (83, 216, 230), (14, 13, 5, 7))
        if facing < 0:
            sprite = pygame.transform.flip(sprite, True, False)
        x, y = int(feet[0]), int(feet[1])
        pygame.draw.ellipse(surface, (8, 13, 22), (x - 24, y - 8, 48, 18))
        surface.blit(pygame.transform.scale(sprite, (60, 96)), (x - 30, y - 86))

    def world(self, location, world):
        if location in self.cache:
            return self.cache[location]
        s = pygame.Surface((512, 320))
        rng = random.Random(location)
        floor = {'station': (28, 38, 50), 'apartment': (43, 35, 40), 'archive': (31, 40, 42),
                 'metro': (30, 39, 49), 'helios': (25, 40, 48), 'port': (25, 32, 42)}[location]
        floor=tuple(world.get('floor',floor))
        s.fill(floor)
        for y in range(38, 310, 16):
            for x in range(0, 512, 24):
                tint = rng.randint(-3, 3)
                pygame.draw.rect(s, tuple(c + tint for c in floor), (x, y, 23, 15))
                pygame.draw.line(s, (19, 27, 38), (x, y + 15), (x + 24, y + 15))
        pygame.draw.rect(s, (12, 22, 36), (0, 0, 512, 38))
        pygame.draw.line(s, (67, 110, 129), (0, 37), (512, 37), 2)
        for x in (42, 158, 274, 390):
            pygame.draw.rect(s, (44, 69, 86), (x, 6, 70, 25))
            pygame.draw.rect(s, (10, 25, 43), (x + 2, 8, 66, 21))
            for _ in range(20):
                rx, ry = rng.randint(x + 3, x + 64), rng.randint(8, 26)
                pygame.draw.line(s, (54, 101, 127), (rx, ry), (rx - 2, ry + 4))
            pygame.draw.line(s, (43, 70, 83), (x + 35, 7), (x + 35, 30), 2)
        for wall in world['walls'][4:]:
            x, y, w, h = [v // 3 for v in wall]
            pygame.draw.rect(s, (9, 18, 28), (x + 3, y + 5, w, h))
            pygame.draw.rect(s, (47, 61, 70), (x, y, w, h))
            for sy in range(y + 4, y + h - 2, 8):
                pygame.draw.rect(s, (21, 33, 44), (x + 3, sy, w - 6, 6))
                pygame.draw.line(s, (98, 111, 112), (x + w // 2 - 3, sy + 2), (x + w // 2 + 3, sy + 2))
        for obj in world['objects']:
            x, y, w, h = [v // 3 for v in obj['rect']]
            if obj['kind'] == 'investigation':
                pygame.draw.rect(s, (9, 16, 25), (x + 4, y + 5, w, h))
                pygame.draw.rect(s, (97, 72, 64), (x, y, w, h))
                pygame.draw.rect(s, (129, 94, 74), (x, y, w, 2))
                pygame.draw.rect(s, (15, 26, 40), (x + 5, y - 7, 24, 19))
                pygame.draw.rect(s, (65, 160, 176), (x + 7, y - 5, 20, 14))
                for a in range(3):
                    pygame.draw.line(s, (120, 220, 213), (x + 9, y - 2 + a * 4), (x + 23, y - 2 + a * 4))
                pygame.draw.rect(s, (35, 45, 52), (x + 7, y + 17, 26, 7))
                pygame.draw.rect(s, (180, 181, 163), (x + 42, y + 10, 14, 17))
                pygame.draw.line(s, (65, 77, 81), (x + 44, y + 14), (x + 53, y + 14))
                pygame.draw.circle(s, (185, 170, 135), (x + 52, y + 3), 4)
            elif obj['kind'] == 'board':
                pygame.draw.rect(s, (105, 77, 67), (x, y, w, h))
                for dx, dy in [(4, 3), (25, 10), (45, 3)]:
                    pygame.draw.rect(s, (179, 184, 163), (x + dx, y + dy, 10, 9))
                pygame.draw.line(s, (198, 59, 74), (x + 8, y + 7), (x + 30, y + 14))
                pygame.draw.line(s, (198, 59, 74), (x + 30, y + 14), (x + 50, y + 7))
            elif obj['kind'] == 'map':
                pygame.draw.rect(s, (10, 18, 29), (x, y, w, h))
                pygame.draw.rect(s, (72, 193, 200), (x, y, w, 3))
                pygame.draw.line(s, (62, 91, 109), (x + w // 2, y + 5), (x + w // 2, y + h))
        from src.ui.location_art import decorate
        decorate(s, location, world)
        result = pygame.transform.scale(s, tuple(world['size']))
        self.cache[location] = result
        return result

    def room(self, surface, hotspots):
        s = pygame.Surface((640, 360))
        s.fill((16, 26, 41))
        pygame.draw.rect(s, (25, 38, 52), (30, 66, 580, 190))
        for y in range(68, 250, 16):
            pygame.draw.line(s, (30, 44, 57), (30, y), (610, y))
        pygame.draw.rect(s, (10, 22, 37), (50, 78, 150, 72))
        for x in range(56, 190, 18):
            pygame.draw.rect(s, (33, 64, 83), (x, 86 + (x % 5), 12, 57))
        pygame.draw.line(s, (81, 133, 146), (120, 78), (120, 150), 2)
        pygame.draw.polygon(s, (50, 42, 45), [(30, 250), (610, 250), (640, 360), (0, 360)])
        pygame.draw.rect(s, (91, 65, 57), (65, 215, 460, 54))
        pygame.draw.rect(s, (136, 100, 78), (65, 215, 460, 4))
        pygame.draw.rect(s, (34, 30, 37), (80, 269, 20, 42))
        pygame.draw.rect(s, (34, 30, 37), (490, 269, 20, 42))
        for hotspot in hotspots:
            x, y, w, h = [v // 2 for v in hotspot['rect']]
            if hotspot['art'] == 'terminal':
                pygame.draw.rect(s, (8, 17, 27), (x, y, w, h - 15))
                pygame.draw.rect(s, (34, 91, 108), (x + 6, y + 6, w - 12, h - 29))
                for row in range(5):
                    pygame.draw.line(s, (100, 198, 198), (x + 14, y + 15 + row * 9), (x + w - 25 - row * 3, y + 15 + row * 9), 2)
                pygame.draw.rect(s, (44, 57, 68), (x + 43, y + h - 15, 40, 10))
                pygame.draw.rect(s, (18, 29, 41), (x - 3, y + h - 4, w + 6, 12))
            elif hotspot['art'] == 'papers':
                pygame.draw.polygon(s, (206, 196, 166), [(x + 4, y), (x + w - 12, y + 7), (x + w, y + h), (x, y + h - 6)])
                for line in range(5):
                    pygame.draw.line(s, (87, 87, 85), (x + 14, y + 13 + line * 7), (x + w - 23, y + 13 + line * 7))
                pygame.draw.rect(s, (166, 49, 66), (x + w - 27, y + h - 20, 14, 11))
            else:
                pygame.draw.rect(s, (109, 77, 66), (x, y, w, h))
                for dx, dy in [(8, 8), (60, 12), (30, 54)]:
                    pygame.draw.rect(s, (190, 183, 160), (x + dx, y + dy, 32, 31))
                pygame.draw.lines(s, (209, 64, 75), False, [(x + 22, y + 21), (x + 76, y + 25), (x + 46, y + 70)], 2)
        surface.blit(pygame.transform.scale(s, (1280, 720)), (0, 0))
