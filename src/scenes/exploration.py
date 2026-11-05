import pygame
from src.core.config import CYAN, MUTED, BG
from src.core.camera import Camera
from src.entities.player import Player
from src.systems.interaction import InteractionSystem
from src.scenes.base import Scene


class Exploration(Scene):
    def __init__(self, game):
        super().__init__(game)
        from copy import deepcopy
        self.world = deepcopy(game.worlds[game.state.location])
        if game.state.thriller['ally_lost']:
            self.world['objects']=[o for o in self.world['objects'] if o.get('dialogue')!='anna']
        if game.state.location=='port' and game.state.thriller['ally_saved']:
            self.world['objects'].append(dict(id='anna_safe',kind='dialogue',name='Аружан / спасена',dialogue='anna',rect=[960,560,28,24]))
        self.player = Player(game.state.position)
        self.camera = Camera(self.world['size'])
        self.camera.update(self.player.position, 0, snap=True)
        self.walls = [pygame.Rect(r) for r in self.world['walls']]
        self.walls.extend(pygame.Rect(o['rect']) for o in self.world['objects'] if o['kind'] in ('investigation', 'board'))
        self.interactions = InteractionSystem()
        self.near = None
        from src.ai.companion import CompanionAI
        self.companion = CompanionAI(game.state,self.world,self.walls)
        self.focusing = False
        from src.entities.npc import PatrolNPC
        self.npcs=[PatrolNPC(o,self.companion.nav,self.walls) for o in self.world['objects'] if o.get('patrol')]

    def event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        from src.scenes.menu import Pause
        from src.scenes.overlays import Inventory, CityMap, Assistant
        if event.key == pygame.K_ESCAPE:
            self.game.scenes.push(Pause(self.game))
        elif event.key == pygame.K_TAB:
            self.game.scenes.push(Inventory(self.game))
        elif event.key == pygame.K_m:
            self.game.scenes.push(CityMap(self.game))
        elif event.key in (pygame.K_n, pygame.K_t):
            self.game.scenes.push(Assistant(self.game))
        elif event.key == pygame.K_j:
            from src.scenes.campaign import CaseStatus
            self.game.scenes.push(CaseStatus(self.game))
        elif event.key == pygame.K_f:
            from src.scenes.companion import CompanionCommands
            self.game.scenes.push(CompanionCommands(self.game,self.companion))
        elif event.key == pygame.K_e:
            self.interact()

    def interact(self):
        obj = self.interactions.nearest(self.player.position, self.world['objects'], self.walls)
        if not obj:
            return
        if obj['kind']=='branch':
            from src.scenes.thriller import start_episode
            start_episode(self.game);return
        if obj['kind'] == 'investigation' and self.game.state.location == 'station' and not self.game.state.story['case_accepted']:
            self.game.toast('Сначала поговорите с капитаном Ермековым справа и выберите «Принять дело Нурланова».')
            return
        from src.scenes.investigation import Investigation
        from src.scenes.overlays import Board, CityMap, Dialogue
        from src.scenes.sensors import GuardDialogue
        from src.scenes.campaign import WeirConfrontation
        scene = {'investigation': lambda: Investigation(self.game, obj['scene']),
                 'board': lambda: Board(self.game), 'map': lambda: CityMap(self.game),
                 'dialogue': lambda: GuardDialogue(self.game) if obj['dialogue'] == 'guard' else WeirConfrontation(self.game) if obj['dialogue'] == 'weir' else Dialogue(self.game, obj['dialogue'])}[obj['kind']]()
        self.game.save()
        if obj['kind'] == 'investigation':
            self.game.transition(scene, lambda: self.game.scenes.push(scene))
        else:
            self.game.scenes.push(scene)

    def update(self, dt):
        keys = pygame.key.get_pressed()
        direction = self.direction(keys)
        self.player.SPEED=115 if self.game.state.thriller['leg_injured'] else 180
        occupied=[self.companion.actor.rect]+[npc.actor.rect for npc in self.npcs]
        self.player.move(direction, dt, self.walls+occupied, keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
        if self.player.moving and pygame.time.get_ticks() - getattr(self, 'last_step', 0) > 320:
            self.game.audio.play('step')
            self.last_step = pygame.time.get_ticks()
        self.game.state.position = list(self.player.position)
        self.companion.update(dt,self.player.position,[pygame.Rect(o['rect']).inflate(30,20) for o in self.world['objects'] if o['kind']=='dialogue'])
        for npc in self.npcs: npc.update(dt,self.player.position)
        self.focusing = bool(keys[pygame.K_q]) and self.game.state.intuition>0
        self.game.state.intuition=max(0,min(100,self.game.state.intuition+(-15 if self.focusing else 5)*dt))
        self.camera.update(self.player.position, dt)
        self.near = self.interactions.nearest(self.player.position, self.world['objects'], self.walls)

    def direction(self, keys):
        wasd = self.game.settings.controls in ('both', 'wasd')
        arrows = self.game.settings.controls in ('both', 'arrows')
        return (int((wasd and keys[pygame.K_d]) or (arrows and keys[pygame.K_RIGHT])) - int((wasd and keys[pygame.K_a]) or (arrows and keys[pygame.K_LEFT])),
                int((wasd and keys[pygame.K_s]) or (arrows and keys[pygame.K_DOWN])) - int((wasd and keys[pygame.K_w]) or (arrows and keys[pygame.K_UP])))

    def draw(self, screen):
        screen.fill(BG)
        screen.blit(self.game.art.world(self.game.state.location, self.world), (-round(self.camera.offset.x), -round(self.camera.offset.y)))
        # Rain is restricted to the exterior windows, not the interior floor.
        ticks = 0 if self.game.settings.reduced_motion else pygame.time.get_ticks() // 40
        for wx in ((126, 474, 822, 1170) if self.game.state.location in ('station','apartment','helios') else ()):
            window = self.camera.apply(pygame.Rect(wx + 6, 24, 198, 63))
            previous_clip = screen.get_clip()
            screen.set_clip(window)
            for i in range(18):
                x = window.x + (i * 37 - ticks * 2) % 198
                y = window.y + (i * 19 + ticks * 5) % 63
                pygame.draw.line(screen, (72, 131, 157), (x, y), (x - 4, y + 12), 2)
            screen.set_clip(previous_clip)
        if self.game.state.location=='metro' and (pygame.time.get_ticks()//180)%17==0 and not self.game.settings.reduced_motion:
            veil=pygame.Surface((1280,720),pygame.SRCALPHA);veil.fill((7,9,18,35));screen.blit(veil,(0,0))
        self.game.ui.text(screen, self.world.get('district',self.world['title']), (400 - self.camera.offset.x, 120 - self.camera.offset.y), 17, MUTED)
        for obj in self.world['objects']:
            rect = self.camera.apply(pygame.Rect(obj['rect']))
            if obj['kind'] == 'dialogue':
                self.game.art.person(screen, rect.midbottom, hologram=obj['name'] == 'N.U.R.S.', captain=obj['dialogue'] == 'sokolov', character=obj['dialogue'])
                if obj['dialogue'] == 'sokolov':
                    self.game.ui.text(screen, 'ЕРМЕКОВ', (rect.centerx - 40, rect.y - 106), 16, CYAN)
            if obj['kind']=='branch':
                pygame.draw.rect(screen,(82,67,54),rect)
                pygame.draw.rect(screen,CYAN,rect,2)
                self.game.ui.text(screen,'СКЛАД 07',(rect.x-8,rect.y-30),18,CYAN)
            if obj['kind'] == 'map':
                self.game.ui.text(screen, 'ВЫХОД', (rect.x - 3, rect.y - 28), 18, CYAN)
        self.game.art.person(screen,self.companion.actor.position-self.camera.offset,hologram=True)
        p = self.player.position - self.camera.offset
        self.game.art.person(screen, p, int(self.player.animation * 7) if self.player.moving else 0,
                             self.player.facing, action=self.near is not None)
        pygame.draw.rect(screen, BG, (0, 0, 1280, 86))
        self.game.ui.text(screen, 'BLOODY / TRAIL', (26, 14), 21, CYAN)
        self.game.ui.text(screen, self.world['title'], (26, 44), 23)
        self.game.ui.text(screen, f'Реп. {self.game.state.reputation} · {self.game.state.time_remaining} ч · J: дело', (450, 51), 18, CYAN)
        self.game.ui.text(screen, f'Очки: {self.game.evidence.score}', (580, 18), 22, CYAN)
        self.game.ui.text(screen, f'ДЕНЬ {self.game.state.current_day:02} / 03    УЛИКИ {len(self.game.state.evidence_ids):02} / {len(self.game.catalog)}', (822, 15), 22)
        self.game.ui.text(screen, f'Здоровье: {self.game.state.health}/100', (822, 51), 18, CYAN)
        pygame.draw.rect(screen, (35, 51, 64), (1028, 56, 190, 12))
        pygame.draw.rect(screen, CYAN, (1028, 56, int(1.9 * self.game.state.health), 12))
        pygame.draw.rect(screen, BG, (0, 665, 1280, 55))
        self.game.ui.text(screen, 'WASD / стрелки — шаг    Shift — быстрее    E — осмотр    Tab — улики    M — карта    T/N — N.U.R.S.    Esc — пауза', (24, 682), 18, MUTED)
        mode_label={'follow':'следование','roam':'осмотр','stay':'ожидание','come':'подойти'}[self.companion.saved['mode']]
        self.game.ui.text(screen, f'F: N.U.R.S. {mode_label} · Q: интуиция {int(self.game.state.intuition)}', (26, 92), 18, CYAN)
        if self.focusing:
            for obj in self.world['objects']:
                rect=pygame.Rect(obj['rect'])
                if obj['kind']=='investigation' and self.player.position.distance_to(rect.center)<220:
                    pygame.draw.rect(screen,(112,133,144),self.camera.apply(rect).inflate(12,12),1)
        if not self.near and self.game.state.location == 'station':
            self.game.ui.panel(screen, (295, 602, 690, 45))
            hint = ('Ермеков справа: подойдите к капитану и нажмите E.' if not self.game.state.story['case_accepted'] else
                    'Стол выше: E — осмотр. Снимок + метаданные → доска → квартира.')
            self.game.ui.text(screen, hint, (313, 614), 18, CYAN)
        if self.near:
            text = '[E] Осмотреть: ' + self.near['name']
            width = min(1160, self.game.ui.font(21).size(text)[0] + 40)
            self.game.ui.panel(screen, ((1280 - width) // 2, 600, width, 48))
            self.game.ui.text(screen, text, ((1280 - width) // 2 + 20, 610), 21, CYAN)
