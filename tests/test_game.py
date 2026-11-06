import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import json
import tempfile
import unittest
from pathlib import Path
import pygame
from src.core.config import ROOT, data
from src.core.state import GameState
from src.core.camera import Camera
from src.core.game import Game
from src.entities.player import Player
from src.systems.interaction import InteractionSystem
from src.systems.evidence import EvidenceManager
from src.systems.save import SaveManager
from src.ai.intents import IntentClassifier
from src.scenes.exploration import Exploration
from src.scenes.investigation import Investigation
from src.scenes.overlays import Assistant, Board, FinalChoice, Ending


class SystemsTests(unittest.TestCase):
    def setUp(self):
        self.state = GameState()
        self.catalog, self.rules = data('evidence'), data('rules')
        self.manager = EvidenceManager(self.state, self.catalog, self.rules)

    def test_collision_no_tunnelling(self):
        p = Player((70, 100))
        p.move((1, 0), 2, [pygame.Rect(100, 0, 10, 200)], fast=True)
        self.assertLessEqual(p.rect.right, 100)

    def test_diagonal_speed_normalized(self):
        a, b = Player((0, 0)), Player((0, 0))
        a.move((1, 0), 0.2, [])
        b.move((1, 1), 0.2, [])
        self.assertAlmostEqual(a.position.length(), b.position.length())

    def test_camera_clamped_and_smooth(self):
        camera = Camera((1536, 960))
        camera.update((1500, 900), 0.016)
        self.assertTrue(0 < camera.offset.x < 256)
        camera.update((9000, 9000), 1, snap=True)
        self.assertEqual(tuple(camera.offset), (256, 240))

    def test_near_only_and_wall_occlusion(self):
        objects = [{'rect': [100, 100, 40, 40]}]
        system = InteractionSystem()
        self.assertIsNone(system.nearest((0, 0), objects))
        self.assertIsNotNone(system.nearest((80, 120), objects))
        self.assertIsNone(system.nearest((50, 120), objects, [pygame.Rect(70, 90, 10, 60)]))

    def test_unique_evidence(self):
        self.assertTrue(self.manager.collect('photo'))
        self.assertFalse(self.manager.collect('photo'))
        self.assertEqual(self.state.statistics['inspections'], 1)

    def test_partial_chain_not_proof(self):
        self.manager.collect('photo')
        self.assertEqual(self.manager.analyze(), [])
        self.assertFalse(self.manager.can_finalize())
        self.manager.collect('blood')
        self.assertEqual(len(self.manager.analyze()), 1)
        self.assertTrue(self.state.evidence_records['blood']['verified'])
        self.assertFalse(self.manager.can_finalize())

    def test_all_chains_required(self):
        for eid in self.catalog:
            self.manager.collect(eid)
        self.assertFalse(self.manager.can_finalize())
        self.assertEqual(len(self.manager.analyze()), len(self.rules))
        self.assertTrue(self.manager.can_finalize())
        self.assertEqual(self.manager.analyze(), [])

    def test_save_roundtrip_and_corruption(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tests') as folder:
            saves = SaveManager(Path(folder) / 'save.json', data('worlds'), self.catalog, self.rules)
            self.manager.collect('photo')
            self.state.position = [381.25, 540.75]
            saves.save(self.state)
            self.assertEqual(saves.load().to_dict(), self.state.to_dict())
            saves.path.write_text('{broken', encoding='utf-8')
            with self.assertRaises(ValueError):
                saves.load()

    def test_save_rejects_nan_and_false_proof(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tests') as folder:
            saves = SaveManager(Path(folder) / 'save.json', data('worlds'), self.catalog, self.rules)
            for field, value in [('position', [float('nan'), 300]), ('flags', ['identity']), ('current_day', 99)]:
                state = GameState()
                setattr(state, field, value)
                saves.save(state)
                with self.subTest(field=field), self.assertRaises(ValueError):
                    saves.load()

    def test_data_references_and_hotspots(self):
        for world in data('worlds').values():
            self.assertTrue(set(world['requires']).issubset(self.catalog))
            for neighbor in world['neighbors']:
                self.assertIn(neighbor, data('worlds'))
        for scene in data('investigations').values():
            for spot in scene['hotspots']:
                if 'evidence' in spot:
                    self.assertIn(spot['evidence'], self.catalog)
                self.assertTrue(pygame.Rect(0, 106, 1280, 544).contains(pygame.Rect(spot['rect'])))


class AITests(unittest.TestCase):
    def setUp(self):
        self.ai = IntentClassifier(data('intents'))

    def test_held_out_commands(self):
        samples = {'пожалуйста покажи улики': 'evidence', 'открой список улик': 'evidence',
                   'сравни запись': 'analyze', 'анализируй следы': 'analyze',
                   'покажи карту города': 'map', 'открой маршрут города': 'map',
                   'нужна помощь': 'help', 'помоги что делать': 'help'}
        for text, expected in samples.items():
            with self.subTest(text=text):
                self.assertEqual(self.ai.predict(text), expected)

    def test_unknown_and_ambiguous_do_nothing(self):
        for text in ('', 'купи пиццу', 'уничтожь сохранения', 'покажи', '!!!', 'hello world'):
            with self.subTest(text=text):
                self.assertIsNone(self.ai.predict(text))

    def test_case_and_punctuation(self):
        self.assertEqual(self.ai.predict('СРАВНИ СЛЕДЫ!'), 'analyze')


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / 'tests')
        self.game = Game(storage_dir=Path(self.folder.name))
        self.game.saves.path = Path(self.folder.name) / 'save.json'
        self.game.new_game(prologue=False)

    def tearDown(self):
        pygame.quit()
        self.folder.cleanup()

    def test_exploration_investigation_return_same_position(self):
        self.game.accept_case()
        scene = self.game.scenes.current
        scene.player.position.update(500, 435)
        scene.player.rect.center = scene.player.position
        scene.update(0)
        original = list(scene.player.position)
        scene.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
        self.game.update(0.5)
        investigation = self.game.scenes.current
        self.assertIsInstance(investigation, Investigation)
        spot = next(s for s in investigation.content['hotspots'] if s.get('evidence') == 'photo')
        investigation.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pygame.Rect(spot['rect']).center))
        self.game.scenes.current.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(800, 300)))
        self.assertIn('photo', self.game.state.evidence_ids)
        self.game.scenes.current.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        investigation.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.game.update(0.5)
        self.assertIs(self.game.scenes.current, scene)
        self.assertEqual(list(scene.player.position), original)

    def test_travel_gates_and_adjacency(self):
        self.assertFalse(self.game.travel('helios'))
        self.assertFalse(self.game.travel('apartment'))
        self.game.evidence.collect('photo')
        self.assertFalse(self.game.travel('apartment'))
        self.game.accept_case()
        self.game.evidence.collect('metadata')
        self.game.evidence.analyze()
        self.assertTrue(self.game.travel('apartment'))
        qte = self.game.scenes.current
        qte.start()
        for key in qte.sequence:
            qte.event(pygame.event.Event(pygame.KEYDOWN, key=key))
        self.assertFalse(self.game.travel('archive'))
        self.assertTrue(self.game.travel('station'))

    def test_full_route_and_all_endings(self):
        self.game.access.unlock()
        self.game.accept_case()
        for index, location in enumerate(self.game.worlds):
            if index:
                self.game.evidence.analyze()
                self.assertTrue(self.game.travel(location))
                if location in ('apartment', 'metro'):
                    qte = self.game.scenes.current
                    qte.start()
                    for key in qte.sequence:
                        qte.event(pygame.event.Event(pygame.KEYDOWN, key=key))
                    self.game.scenes.pop()
            scene = Investigation(self.game, location)
            spots = [s for s in scene.content['hotspots'] if 'evidence' in s]
            spots.sort(key=lambda s: s['evidence'] == 'metadata')
            for spot in spots:
                scene.select(spot)
                scene.collect()
                self.game.scenes.pop()
            from scenario_steps import solve_location
            solve_location(self.game,location)
            if location == 'metro':
                from src.scenes.sensors import GuardDialogue
                guard = GuardDialogue(self.game)
                guard.answer(False)
                guard.answer(False)
        # 14 route items + the Day 2 victim report collected on entering the archive.
        self.assertEqual(len(self.game.state.evidence_ids), 15)
        self.assertIn('expert_death', self.game.state.evidence_ids)
        assistant = Assistant(self.game)
        assistant.input = 'сравни следы'
        assistant.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        from scenario_steps import deduce
        deduce(self.game)
        self.assertTrue(self.game.evidence.can_finalize())
        self.assertEqual(self.game.state.current_day, 3)
        self.game.backup_case()
        self.game.state.campaign['weir_confronted'] = True
        for ending in ('arrest', 'revenge', 'release'):
            self.game.state.ending = ''  # Independent ending branches from the same proof fixture.
            FinalChoice(self.game).finish(ending)
            self.assertIsInstance(self.game.scenes.current, Ending)
            self.assertEqual(self.game.saves.load().ending, ending)

    def test_cannot_finalize_without_proof(self):
        FinalChoice(self.game).finish('arrest')
        self.assertEqual(self.game.state.ending, '')

    def test_nlp_unknown_does_not_change_state(self):
        assistant = Assistant(self.game)
        before = self.game.state.to_dict()
        assistant.input = 'удали все'
        assistant.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(self.game.state.to_dict(), before)

    def test_resolution_mouse_mapping(self):
        self.game.window = pygame.Surface((1920, 1080))
        self.assertEqual(self.game.logical_mouse((960, 540)), (640, 360))
        self.game.window = pygame.Surface((1280, 1000))
        self.assertEqual(self.game.logical_mouse((640, 500)), (640, 360))

    def test_load_keeps_state_after_corruption(self):
        self.game.saves.path.write_text('null', encoding='utf-8')
        self.game.load()
        self.assertEqual(self.game.state.location, 'station')
        self.assertIn('Не удалось загрузить', self.game.notice)


if __name__ == '__main__':
    unittest.main()
