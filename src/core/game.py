import os
import pygame
from src.core.config import ROOT, SIZE, data, CYAN, default_storage
from src.core.state import GameState
from src.core.scene_manager import SceneManager
from src.systems.save import SaveManager
from src.systems.evidence import EvidenceManager
from src.systems.dialogue import DialogueManager
from src.ai.intents import IntentClassifier
from src.ai.commands import CommandRouter
from src.ui.widgets import UI
from src.ui.art import Art
from src.systems.settings import SettingsManager
from src.systems.audio import AudioManager
from src.ui.investigation_art import InvestigationArt
from src.systems.profile import ContentAccess, ResultJournal
from src.systems.campaign import refresh_achievements, ending_allowed


class Game:
    def __init__(self, storage_dir=None):
        pygame.init()
        self.storage_dir = storage_dir or default_storage()
        self.preferences = SettingsManager(self.storage_dir / 'settings.json')
        self.settings = self.preferences.value
        self.access = ContentAccess(self.storage_dir / 'content_access.json')
        self.journal = ResultJournal(self.storage_dir / 'results.json')
        pygame.display.set_caption('Bloody Trail — Астера, 2035')
        self.window = pygame.display.set_mode(SIZE, pygame.RESIZABLE)
        if self.settings.fullscreen and pygame.display.get_driver() != 'dummy':
            try:
                self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            except pygame.error:
                self.settings.fullscreen = False
        self.screen = pygame.Surface(SIZE)
        self.clock = pygame.time.Clock()
        self.ui, self.art = UI(), Art()
        self.investigation_art = InvestigationArt()
        self.current_cursor = None
        self.audio = AudioManager()
        self.audio.apply(self.settings)
        if self.settings.output_device:
            if not self.audio.switch_output(self.settings.output_device):
                self.settings.output_device = ''
                try: self.preferences.save()
                except OSError: pass
        self.worlds, self.catalog, self.rules = data('worlds'), data('evidence'), data('rules')
        import json
        for location in self.worlds:
            map_file=ROOT/'src/data/maps'/f'{location}.json'
            if map_file.exists(): self.worlds[location].update(json.loads(map_file.read_text(encoding='utf8')))
        self.investigations = data('investigations')
        self.dialogues = DialogueManager(data('dialogues'))
        self.classifier = IntentClassifier(data('intents'))
        self.command_router = CommandRouter(data('voice_commands'), self.classifier)
        self.saves = SaveManager(self.storage_dir / 'slot1.json', self.worlds, self.catalog, self.rules)
        self.bind_state(GameState())
        self.scenes = SceneManager()
        self.mouse = (-1, -1)
        self.running, self.active = True, False
        self.notice, self.notice_time = '', 0
        self.fade_scene, self.fade_age = None, 0.0
        if self.preferences.error or self.access.error:
            self.toast(self.preferences.error or self.access.error)
        from src.scenes.menu import Splash
        self.scenes.replace(Splash(self))
        pygame.key.start_text_input()

    def bind_state(self, state):
        self.state = state
        self.evidence = EvidenceManager(state, self.catalog, self.rules)
        self.evidence.on_change = self.evidence_changed
        from src.systems.puzzles import PuzzleManager, HiddenEvidenceSystem, HintManager
        self.puzzles=PuzzleManager(state,self.evidence,data('puzzles'))
        self.hidden=HiddenEvidenceSystem(state)
        self.hints=HintManager(state,self.puzzles.definitions)
        from src.systems.story_manager import StoryManager
        self.story_manager=StoryManager(state,self.evidence)
        from src.ai.nurs_brain import NursBrain
        self.nurs=NursBrain(state,self.catalog,self.rules,self.worlds,data('chapters'),self.puzzles.definitions,data('nurs_persona'))

    def evidence_changed(self, kind, identifier):
        if kind == 'collect':
            self.audio.play('evidence')
            if identifier not in self.state.discoveries['comments']:
                self.state.discoveries['comments'].append(identifier)
                entry = self.catalog[identifier]
                self.toast('N.U.R.S.: ' + entry.get('nurs', 'новый источник — '+entry['source']+'. Сопоставьте его с уже найденными материалами.'))
        if kind == 'collect' and identifier == 'photo' and self.state.narrative['started'] and not self.state.narrative['flashback_seen']:
            self.recall_blood_mark()
        if kind == 'conclusion' and identifier == 'blood_history':
            self.state.narrative['objective'] = 'Проверить связь семейного дела с Сигмой'
            note = 'Архив независимо подтвердил связь преступлений 2020 и 2035. Личность виновного неизвестна.'
            if note not in self.state.narrative['journal']: self.state.narrative['journal'].append(note)
        if kind == 'mistake':
            self.state.reputation = max(0, self.state.reputation - 2)
            self.toast('Неподтверждённая версия: репутация −2. N.U.R.S. может подсказать недостающие основания.')
        earned = refresh_achievements(self.state, self.evidence)
        if earned: self.toast('Достижение: ' + ', '.join(earned))

    def recall_blood_mark(self):
        if 'photo' not in self.state.evidence_ids or self.state.narrative['flashback_seen']: return False
        self.state.narrative['flashback_seen']=True
        self.evidence.collect('EVIDENCE_BLOOD_MARK_2020')
        self.evidence.collect('EVIDENCE_BLOOD_MARK_2035')
        self.state.narrative['objective']='Сопоставить следы 2020 и 2035 годов; найти независимый протокол'
        from src.scenes.prologue import Flashback
        self.scenes.push(Flashback(self))
        self.save()
        return True

    def spend_time(self, amount, reason):
        self.state.time_remaining = max(0, self.state.time_remaining - amount)
        self.state.time_slot = min(5, self.state.time_slot + amount)
        self.toast(f'{reason}: время −{amount} ч. Осталось {self.state.time_remaining} ч.')
        if self.state.time_remaining == 0:
            self.fail('insufficient')
            return False
        return True

    def backup_case(self):
        if 'server' not in self.state.evidence_ids: return False
        if not self.state.campaign['backup']:
            self.state.campaign['backup'] = True
            self.state.trust['sokolov'] = min(100, self.state.trust.get('sokolov', 50) + 10)
            self.toast('Резервная копия передана. Доверие Ермекова +10.')
            self.save()
        return True

    def finish_case(self, ending):
        if self.state.ending or not self.access.full_version_unlocked or not ending_allowed(self.state, self.evidence, ending):
            self.toast('Не выполнены условия концовки: доказательства, решения, здоровье или доступ к полной версии.')
            return False
        from src.scenes.overlays import Ending
        if ending == 'revenge': self.state.reputation = max(0, self.state.reputation - 40)
        if ending == 'release': self.state.reputation = max(0, self.state.reputation - 15)
        self.scenes.replace(Ending(self, ending))
        return True

    def record_result(self):
        refresh_achievements(self.state, self.evidence)
        try:
            self.journal.record(self.state, self.evidence.score)
        except (OSError, ValueError) as exc:
            self.toast('Не удалось записать таблицу результатов: ' + str(exc))

    def toast(self, text):
        self.notice, self.notice_time = text, 4.5

    def transition(self, destination, commit):
        if self.settings.reduced_motion:
            commit()
        else:
            from src.scenes.transition import FadeTransition
            self.scenes.push(FadeTransition(self, destination, commit))

    def save_manager(self, slot='auto'):
        if slot == 'auto':
            return self.saves
        if slot not in ('manual', 'checkpoint'):
            raise ValueError('Неизвестный слот')
        path = self.saves.path.with_name(self.saves.path.stem + '_' + slot + '.json')
        return SaveManager(path, self.worlds, self.catalog, self.rules)

    def save(self, slot='auto'):
        try:
            refresh_achievements(self.state, self.evidence)
            self.save_manager(slot).save(self.state)
            return True
        except OSError as exc:
            self.toast('Не удалось сохранить: ' + str(exc))
            return False

    def manual_save(self):
        if self.save('manual'):
            self.toast('Игра сохранена в ручной слот.')

    def set_setting(self, key, value):
        old = getattr(self.settings, key)
        setattr(self.settings, key, value)
        try:
            self.preferences.save()
        except OSError as exc:
            setattr(self.settings, key, old)
            self.toast('Настройка не сохранена: ' + str(exc))
            return False
        self.audio.apply(self.settings)
        return True

    def toggle_fullscreen(self):
        target = not self.settings.fullscreen
        try:
            self.window = pygame.display.set_mode((0, 0) if target else SIZE,
                                                 pygame.FULLSCREEN if target else pygame.RESIZABLE)
            if not self.set_setting('fullscreen', target):
                self.window = pygame.display.set_mode((0, 0) if not target else SIZE,
                                                     pygame.FULLSCREEN if not target else pygame.RESIZABLE)
        except pygame.error as exc:
            self.toast('Режим экрана недоступен: ' + str(exc))

    def to_menu(self):
        from src.scenes.menu import Menu
        self.active = False
        self.scenes.replace(Menu(self))

    def fail(self, reason='withdraw'):
        from src.scenes.results import GameOver
        if reason not in ('withdraw', 'health', 'insufficient'):
            raise ValueError('Эта причина поражения пока не реализована')
        self.scenes.replace(GameOver(self, reason))

    def new_game(self, prologue=True):
        from src.scenes.exploration import Exploration
        self.bind_state(GameState())
        self.state.narrative['started'] = prologue
        self.active = True
        self.scenes.replace(Exploration(self))
        if prologue:
            from src.scenes.prologue import Prologue
            self.scenes.push(Prologue(self))
        self.save()
        self.save('checkpoint')

    def complete_prologue(self, show_intro=True):
        n=self.state.narrative
        n['prologue_complete']=True
        self.evidence.collect('EVIDENCE_BLOOD_MARK_2020')
        n['objective']='Изучить фотографии Нурланова'
        if 'Воспоминание о ночи 2020 года' not in n['journal']:n['journal'].append('Воспоминание о ночи 2020 года')
        self.accept_case()
        if show_intro:
            from src.scenes.prologue import PresentBriefing
            from src.scenes.exploration import Exploration
            self.scenes.replace(Exploration(self));self.scenes.push(PresentBriefing(self))
        self.save();self.save('checkpoint')

    def load(self, slot='auto'):
        from src.scenes.exploration import Exploration
        from src.scenes.overlays import Ending
        try:
            state = self.save_manager(slot).load()
            world = self.worlds[state.location]
            if not self.access.allows(world['chapter']):
                from src.scenes.campaign import FullVersion
                self.scenes.push(FullVersion(self, load_slot=slot))
                self.toast('Сохранение относится к полной версии. Откройте полный доступ — выбранное сохранение загрузится автоматически.')
                return False
            footprint = pygame.Rect(0, 0, 24, 18)
            footprint.center = state.position
            obstacles = world['walls'] + [o['rect'] for o in world['objects'] if o['kind'] in ('investigation', 'board')]
            if any(footprint.colliderect(pygame.Rect(r)) for r in obstacles):
                raise ValueError('Позиция внутри препятствия')
            if not set(world.get('load_requires', world['requires'])).issubset(state.evidence_ids):
                raise ValueError('Локация ещё не открыта')
            if state.ending in ('arrest', 'revenge', 'release') and not all(r['id'] in state.flags for r in self.rules if not r.get('optional')):
                raise ValueError('Финал без доказательств')
            self.bind_state(state)
            self.active = True
            if state.narrative['started'] and not state.narrative['prologue_complete']:
                self.complete_prologue(show_intro=False)
            from src.scenes.results import GameOver
            from src.systems.story_manager import NEW_ENDINGS
            if state.ending in NEW_ENDINGS:
                from src.scenes.thriller import BranchEnding
                self.scenes.replace(BranchEnding(self,state.ending))
            elif not state.ending and state.thriller['phase'] not in ('idle','resolved'):
                from src.scenes.thriller import show_phase
                show_phase(self,fade=False)
            elif state.ending in ('withdraw', 'health', 'insufficient'):
                self.scenes.replace(GameOver(self, state.ending, persist=False))
            else:
                self.scenes.replace(Ending(self, state.ending, persist=False) if state.ending else Exploration(self))
            if not state.ending:
                self.save('checkpoint')
            return True
        except (OSError, ValueError) as exc:
            self.toast('Не удалось загрузить: ' + str(exc))
            return False

    def accept_case(self):
        self.evidence.collect('order')
        self.state.story['case_accepted'] = True
        self.save()

    def can_enter(self, destination):
        world = self.worlds[destination]
        return (set(world['requires']).issubset(self.state.evidence_ids)
                and set(world.get('requires_flags', [])).issubset(self.state.flags)
                and all(self.state.story.get(key, False) for key in world.get('requires_story', [])))

    def travel(self, destination):
        if self.state.ending or self.state.health <= 0:
            return False
        if destination not in self.worlds[self.state.location]['neighbors']:
            return False
        if not self.can_enter(destination):
            self.toast('Сначала получите дело у Ермекова, соберите материалы и подтвердите связь на доске.')
            return False
        if not self.access.allows(self.worlds[destination]['chapter']):
            from src.scenes.campaign import FullVersion
            self.scenes.push(FullVersion(self, destination))
            return False
        if destination == 'apartment' and not self.state.story['qte_complete']:
            from src.scenes.qte import StoryQTE
            if not isinstance(self.scenes.current, StoryQTE):
                if not self.save('checkpoint'):
                    return False
                self.scenes.push(StoryQTE(self))
            return True
        if destination == 'metro' and not self.state.campaign['archive_qte']:
            from src.scenes.qte import StoryQTE
            if not self.save('checkpoint'): return False
            self.scenes.push(StoryQTE(self, episode='archive'))
            return True
        return self.enter_location(destination)

    def enter_location(self, destination):
        """Commit a validated travel or successful QTE; not a UI action."""
        world = self.worlds[destination]
        if not self.access.allows(world['chapter']):
            return False
        from src.scenes.exploration import Exploration
        previous_day = self.state.current_day
        first_visit = destination not in self.state.visited
        if first_visit and not self.spend_time(1, 'Переезд к новому месту расследования'): return False
        if first_visit: self.state.visited.append(destination)
        self.state.location = destination
        self.state.position = list(world['spawn'])
        self.state.current_day = max(self.state.current_day, world['chapter'])
        if self.state.current_day != previous_day: self.state.time_slot = 0
        self.scenes.replace(Exploration(self))
        if self.state.current_day != previous_day:
            if self.state.current_day >= 2: self.evidence.collect('expert_death')
            from src.scenes.campaign import ChapterIntro
            self.scenes.push(ChapterIntro(self, self.state.current_day))
        self.save()
        self.save('checkpoint')
        return True

    def complete_archive(self):
        if not self.can_enter('metro') or not self.access.full_version_unlocked or self.state.ending: return False
        self.state.campaign['archive_qte'] = True
        return self.enter_location('metro')

    def complete_entry(self):
        if not self.can_enter('apartment') or self.state.health <= 0 or self.state.ending:
            return False
        self.state.story['qte_complete'] = True
        first_completion = not self.state.story['mvp_complete']
        self.state.story['mvp_complete'] = True
        if not self.enter_location('apartment'): return False
        if first_completion:
            from src.scenes.qte import MVPComplete
            self.scenes.push(MVPComplete(self))
        return True

    def quit(self):
        if self.active and not self.save():
            return
        self.scenes.close()
        self.running = False

    def viewport(self):
        w, h = self.window.get_size()
        scale = min(w / SIZE[0], h / SIZE[1])
        size = (max(1, round(SIZE[0] * scale)), max(1, round(SIZE[1] * scale)))
        return pygame.Rect((w - size[0]) // 2, (h - size[1]) // 2, *size)

    def logical_mouse(self, pos):
        rect = self.viewport()
        return ((pos[0] - rect.x) * SIZE[0] / rect.w, (pos[1] - rect.y) * SIZE[1] / rect.h)

    def pause_on_focus_loss(self):
        current=self.scenes.current
        getattr(current,'on_cover',lambda:None)()
        from src.scenes.exploration import Exploration
        from src.scenes.menu import Pause
        from src.scenes.qte import StoryQTE
        from src.scenes.thriller import HideScene,ChaseScene,BranchRoom,EpisodePause
        if isinstance(current,Exploration):self.scenes.push(Pause(self))
        elif isinstance(current,StoryQTE):current.pause()
        elif isinstance(current,(HideScene,ChaseScene,BranchRoom)):self.scenes.push(EpisodePause(self))

    def run(self):
        while self.running:
            elapsed = self.clock.tick(60) / 1000
            dt = min(elapsed, 0.05)
            self.mouse = self.logical_mouse(pygame.mouse.get_pos())
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                elif event.type == pygame.WINDOWFOCUSLOST:
                    self.pause_on_focus_loss()
                else:
                    if hasattr(event, 'pos'):
                        event = pygame.event.Event(event.type, {**event.dict, 'pos': self.logical_mouse(event.pos)})
                    self.scenes.current.event(event)
            self.update(dt, elapsed)
            self.draw(dt)
            if self.notice_time > 0:
                self.notice_time -= dt
                self.ui.panel(self.screen, (40, 92, 1200, 60))
                self.ui.paragraph(self.screen, self.notice, (55, 105, 1170, 45), 18, CYAN)
            self.window.fill((0, 0, 0))
            rect = self.viewport()
            self.window.blit(pygame.transform.scale(self.screen, rect.size), rect)
            pygame.display.flip()
        pygame.quit()

    def update(self, dt, elapsed=None):
        from src.scenes.exploration import Exploration
        from src.scenes.investigation import Investigation, ObjectInspection
        from src.scenes.evidence_board import EvidenceDetail
        from src.scenes.overlays import Inventory, Board, CityMap, Assistant, Dialogue, FinalChoice
        from src.scenes.qte import StoryQTE
        from src.scenes.sensors import SensorChallenge, GuardDialogue
        from src.scenes.campaign import WeirConfrontation
        sensor_active = any(getattr(s,'sensors_active',False) or getattr(getattr(s, 'session', None), 'process', None) is not None or
                            getattr(getattr(s, 'voice', None), 'process', None) is not None for s in self.scenes.stack)
        from src.scenes.prologue import Prologue, Flashback, PresentBriefing
        cinematic = isinstance(self.scenes.current, (Prologue, Flashback))
        mode = self.scenes.current.audio_mode if cinematic else ('rain' if self.active else 'menu')
        self.audio.ambience('silent' if sensor_active else mode, dt, duck=cinematic or isinstance(self.scenes.current, (Dialogue, Assistant, WeirConfrontation, PresentBriefing)))
        self.audio.location_ambience(self.state.location if self.active and not cinematic and not sensor_active else None)
        from src.scenes.thriller import BranchRoom, HideScene, ChaseScene
        if self.active and isinstance(self.scenes.current,(BranchRoom,HideScene,ChaseScene)): self.state.play_seconds += dt if elapsed is None else elapsed
        from src.scenes.puzzles import PuzzleScene
        if self.active and isinstance(self.scenes.current,PuzzleScene): self.state.play_seconds += dt if elapsed is None else elapsed
        if self.active and not self.state.ending and isinstance(self.scenes.current,
                (Exploration, Investigation, ObjectInspection, EvidenceDetail, Inventory, Board, CityMap, Assistant, Dialogue, FinalChoice, WeirConfrontation)):
            self.state.play_seconds += dt if elapsed is None else elapsed
        if self.active and isinstance(self.scenes.current, (SensorChallenge, GuardDialogue)):
            self.state.play_seconds += dt if elapsed is None else elapsed
        if self.active and isinstance(self.scenes.current, StoryQTE) and self.scenes.current.phase == 'running':
            self.state.play_seconds += dt if elapsed is None else elapsed
        from src.scenes.settings import QTEPractice
        self.scenes.current.update(elapsed if elapsed is not None and isinstance(self.scenes.current, (QTEPractice, StoryQTE, SensorChallenge, ChaseScene)) else dt)

    def draw(self, dt):
        current = self.scenes.current
        if current is not self.fade_scene:
            self.fade_scene, self.fade_age = current, 0.0
        self.fade_age += dt
        current.draw(self.screen)
        desired = getattr(current, 'cursor', pygame.SYSTEM_CURSOR_ARROW)
        if desired != self.current_cursor:
            try:
                pygame.mouse.set_cursor(desired)
            except pygame.error:
                pass  # Headless SDL has no system cursor; highlighted hotspot still works.
            self.current_cursor = desired
        from src.scenes.transition import FadeTransition
        if not isinstance(current, FadeTransition) and not self.settings.reduced_motion and self.fade_age < 0.22:
            veil = pygame.Surface(SIZE)
            veil.fill((6, 11, 20))
            veil.set_alpha(round(180 * (1 - self.fade_age / 0.22)))
            self.screen.blit(veil, (0, 0))

    def smoke(self):
        """Render all main scenes; never touch the player's save file."""
        import tempfile
        from pathlib import Path
        from src.scenes.menu import Menu, Splash, Pause
        from src.scenes.settings import SettingsScene, LoadScene, AdditionalCases, QTEPractice
        from src.scenes.results import Results, GameOver
        from src.scenes.investigation import Investigation, ObjectInspection
        from src.scenes.evidence_board import EvidenceDetail
        from src.scenes.overlays import Inventory, Board, Assistant, CityMap, Dialogue
        folder = ROOT / 'docs' / 'screenshots'
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=folder) as temporary:
            self.saves.path = Path(temporary) / 'smoke.json'
            self.new_game(prologue=False)
            scenes = [('start', Splash(self)), ('menu', Menu(self)), ('exploration', self.scenes.current),
                      ('investigation', Investigation(self, 'station')), ('assistant', Assistant(self)),
                      ('map', CityMap(self)), ('dialogue', Dialogue(self, 'briefing')),
                      ('pause', Pause(self)), ('settings_sound', SettingsScene(self)),
                      ('settings_controls', SettingsScene(self, 'controls')),
                      ('settings_qte', SettingsScene(self, 'qte')),
                      ('settings_privacy', SettingsScene(self, 'privacy')),
                      ('load', LoadScene(self)), ('dlc', AdditionalCases(self)), ('qte', QTEPractice(self))]
            for eid in self.catalog:
                self.evidence.collect(eid)
            self.evidence.analyze()
            scenes.extend([('inventory', Inventory(self)), ('board', Board(self))])
            room = Investigation(self, 'station')
            scenes.extend([('object_computer', ObjectInspection(self, room, room.content['hotspots'][0])),
                           ('evidence_photo', EvidenceDetail(self, 'photo')),
                           ('evidence_document', EvidenceDetail(self, 'metadata')),
                           ('sokolov_unlocked', Dialogue(self, 'sokolov'))])
            linked = Board(self)
            linked.select('photo')
            linked.select('metadata')
            linked.propose()
            linked.confirm()
            scenes.append(('board_confirmed', linked))
            scenes.extend([('results', Results(self, 'arrest', persist=False)), ('game_over', GameOver(self, persist=False))])
            for name, scene in scenes:
                scene.update(0.1)
                scene.draw(self.screen)
                pygame.image.save(self.screen, str(folder / (name + '.png')))
            print('SMOKE OK: ' + ', '.join(name for name, _ in scenes))
            from src.scenes.qte import StoryQTE, MVPComplete
            self.new_game(prologue=False)
            self.accept_case()
            for eid in ('photo', 'metadata'):
                self.evidence.collect(eid)
            self.evidence.evaluate(self.evidence.propose('photo', 'metadata'))
            self.save('checkpoint')
            qte = StoryQTE(self)
            def capture(name, scene):
                scene.draw(self.screen)
                pygame.image.save(self.screen, str(folder / (name + '.png')))
            capture('mvp1_qte_ready', qte)
            qte.start()
            qte.update(.8)
            capture('mvp1_qte_running', qte)
            qte.pause()
            capture('mvp1_qte_paused', qte)
            qte.resume()
            qte.update(10)
            capture('mvp1_qte_failed', qte)
            qte.assisted_entry()
            capture('mvp1_complete', MVPComplete(self))
            self.state.health = 0
            capture('mvp1_health_gameover', GameOver(self, 'health', persist=False))
            print('MVP1 SMOKE OK: 6 additional story screens; 30 total')
            from src.scenes.sensors import GuardDialogue, SensorChallenge, SensorConsent
            self.state.health = 100
            self.state.location = 'metro'
            capture('lab12_guard', GuardDialogue(self))
            capture('lab12_camera_consent', SensorConsent(self, 'camera', lambda: None))
            calm = SensorChallenge(self, 'calm')
            calm.start_manual()
            calm.pulse()
            calm.update(1)
            capture('lab12_calm_manual', calm)
            noise = SensorChallenge(self, 'silence')
            noise.start_manual()
            noise.update(1)
            capture('lab12_noise_manual', noise)
            capture('lab12_assistant', Assistant(self))
            calm.on_exit()
            noise.on_exit()
            print('LAB12 SMOKE OK: 5 additional screens; 35 total; no devices activated')
        pygame.quit()
