import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import json
import tempfile
import unittest
from pathlib import Path
import pygame
from src.core.config import ROOT
from src.core.game import Game
from src.scenes.menu import Menu
from src.scenes.exploration import Exploration
from src.scenes.investigation import Investigation
from src.scenes.overlays import Dialogue, Assistant, CityMap, Inventory
from src.scenes.evidence_board import Board
from src.scenes.qte import StoryQTE, MVPComplete
from src.scenes.results import GameOver


class MVP1Tests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / 'tests')
        self.game = Game(storage_dir=Path(self.folder.name))
        self.key(pygame.K_SPACE)
        self.click('Новая игра')
        from src.scenes.prologue import Prologue
        self.assertIsInstance(self.game.scenes.current, Prologue)
        self.game.new_game(prologue=False)  # Isolate the original gameplay regression fixtures.

    def tearDown(self):
        pygame.quit()
        self.folder.cleanup()

    def key(self, key):
        self.game.scenes.current.event(pygame.event.Event(pygame.KEYDOWN, key=key))

    def click(self, label):
        scene = self.game.scenes.current
        b = next(b for b in scene.buttons if b[0] == label)
        scene.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=b[1].center))

    def position(self, x, y):
        scene = self.game.scenes.current
        scene.player.position.update(x, y)
        scene.player.rect.center = (x, y)
        scene.update(0)

    def ready(self):
        self.game.accept_case()
        for eid in ('photo', 'metadata'):
            self.game.evidence.collect(eid)
        key = self.game.evidence.propose('photo', 'metadata')
        self.game.evidence.evaluate(key)
        self.assertTrue(self.game.travel('apartment'))
        self.assertIsInstance(self.game.scenes.current, StoryQTE)
        return self.game.scenes.current

    def test_full_episode_via_ui_and_save_reload(self):
        self.position(500, 435)
        self.key(pygame.K_e)
        self.assertIsInstance(self.game.scenes.current, Exploration)
        self.assertFalse(self.game.can_enter('apartment'))
        self.position(740, 450)
        self.key(pygame.K_e)
        self.assertIsInstance(self.game.scenes.current, Dialogue)
        self.assertIn('Ермеков', self.game.scenes.current.node['speaker'])
        self.click('Принять дело Нурланова')
        self.assertEqual(self.game.evidence.score, 10)
        self.click('Принять дело Нурланова')
        self.assertEqual(self.game.evidence.score, 10)
        self.click('Завершить разговор')
        self.position(500, 435)
        position = self.game.state.position[:]
        self.key(pygame.K_e)
        self.game.update(.5)
        room = self.game.scenes.current
        self.assertIsInstance(room, Investigation)
        def open_spot(key):
            spot = next(s for s in room.content['hotspots'] if s['id'] == key)
            room.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pygame.Rect(spot['rect']).center))
        open_spot('documents')
        self.click('Зафиксировать фотографию')
        self.key(pygame.K_ESCAPE)
        open_spot('computer')
        self.click('Изучить запись Нурланова')
        self.assertIn('Азамат Нурланов', self.game.scenes.current.description)
        self.click('Проверить удалённые файлы')
        self.assertIn('аномалия', self.game.scenes.current.description)
        self.assertTrue(self.game.state.story['anomaly_announced'])
        self.assertEqual(self.game.evidence.score, 30)
        self.key(pygame.K_ESCAPE)
        self.key(pygame.K_TAB)
        self.assertIsInstance(self.game.scenes.current, Inventory)
        self.assertEqual(len(self.game.state.evidence_ids), 3)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(self.game.can_enter('apartment'))
        self.key(pygame.K_b)
        board = self.game.scenes.current
        self.assertIsInstance(board, Board)
        board.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=board.question_rects()['initial_anomaly'].center))
        for eid in ('photo', 'metadata'):
            board.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=board.cards[eid].center))
        self.assertFalse(self.game.can_enter('apartment'))
        self.click('Проверить вывод')
        self.assertEqual(self.game.evidence.score, 50)
        self.click('Проверить вывод')
        self.assertEqual(self.game.evidence.score, 50)
        self.assertFalse(self.game.evidence.can_finalize())
        self.key(pygame.K_ESCAPE)
        self.key(pygame.K_ESCAPE)
        self.game.update(.5)
        self.assertEqual(self.game.state.position, position)
        self.key(pygame.K_m)
        self.assertIsInstance(self.game.scenes.current, CityMap)
        self.click('Квартира Нурланова')
        self.click('Начать испытание')
        for key in (pygame.K_a, pygame.K_d, pygame.K_SPACE):
            self.key(key)
        self.assertIsInstance(self.game.scenes.current, MVPComplete)
        self.assertEqual(self.game.state.health, 100)
        self.assertEqual(self.game.state.location, 'apartment')
        self.assertTrue(self.game.state.story['mvp_complete'])
        self.click('Продолжить в квартире')
        self.assertIsInstance(self.game.scenes.current, Exploration)
        self.game.manual_save()
        saved = self.game.state.to_dict()
        self.game.to_menu()
        self.assertTrue(self.game.load('manual'))
        self.assertEqual(self.game.state.to_dict(), saved)
        self.assertTrue(self.game.travel('station'))
        self.assertTrue(self.game.travel('apartment'))
        self.assertIsInstance(self.game.scenes.current, Exploration)  # no repeat reward/QTE

    def test_qte_timeout_three_failures_health_gameover_checkpoint(self):
        qte = self.ready()
        checkpoint = self.game.save_manager('checkpoint').load().to_dict()
        for expected in (65, 30, 0):
            qte.start()
            self.game.update(.05, elapsed=3.01)
            self.assertEqual(self.game.state.health, expected)
            qte.update(60)
            self.assertEqual(self.game.state.health, expected)
        self.assertIsInstance(self.game.scenes.current, GameOver)
        self.assertEqual(self.game.state.ending, 'health')
        self.assertEqual(self.game.save_manager('checkpoint').load().to_dict(), checkpoint)
        self.assertTrue(self.game.load())
        self.assertIsInstance(self.game.scenes.current, GameOver)
        self.assertEqual(self.game.scenes.current.reason, 'health')
        self.click('Повторить с контрольной точки')
        self.assertEqual(self.game.state.health, 100)
        self.assertFalse(self.game.state.ending)
        self.assertFalse(self.game.state.story['mvp_complete'])

    def test_wrong_key_and_alternative_have_once_only_consequences(self):
        qte = self.ready()
        qte.start()
        self.key(pygame.K_d)
        self.assertEqual(self.game.state.health, 65)
        self.click('Помощь дежурного: −10 репутации')
        self.assertIsInstance(self.game.scenes.current, MVPComplete)
        self.assertEqual(self.game.state.reputation, 90)
        qte.assisted_entry()
        self.assertEqual(self.game.state.reputation, 90)
        self.assertEqual(self.game.evidence.score, 50)

    def test_qte_ready_pause_easy_untimed(self):
        self.game.settings.qte_mode = 'easy'
        qte = self.ready()
        qte.update(100)
        self.assertEqual(qte.elapsed, 0)
        qte.start()
        qte.update(3.1)
        self.assertEqual(qte.phase, 'running')
        self.key(pygame.K_ESCAPE)
        qte.update(100)
        self.assertEqual(qte.elapsed, 3.1)
        self.key(pygame.K_ESCAPE)
        qte.update(3)
        self.assertEqual(self.game.state.health, 65)
        self.game.settings.qte_mode = 'untimed'
        unlimited = StoryQTE(self.game)
        self.game.scenes.replace(unlimited)
        unlimited.start()
        unlimited.update(1000)
        self.assertEqual(unlimited.phase, 'running')
        for key in unlimited.sequence:
            self.key(key)
        self.assertIsInstance(self.game.scenes.current, MVPComplete)

    def test_unknown_command_no_reward_and_known_intent_acts(self):
        assistant = Assistant(self.game)
        self.game.scenes.push(assistant)
        before = self.game.state.to_dict()
        assistant.input = 'победить немедленно'
        self.key(pygame.K_RETURN)
        self.assertEqual(before, self.game.state.to_dict())
        assistant.input = 'покажи улики'
        self.key(pygame.K_RETURN)
        self.assertIsInstance(self.game.scenes.current, Inventory)

    def test_false_mvp_completion_save_is_rejected(self):
        self.game.state.story['mvp_complete'] = True
        self.game.save()
        with self.assertRaises(ValueError):
            self.game.saves.load()

    def test_v3_migration_retains_existing_location_without_fabricated_evidence(self):
        self.game.evidence.collect('photo')
        self.game.state.location = 'apartment'
        self.game.save()
        payload = json.loads(self.game.saves.path.read_text(encoding='utf-8'))
        payload['version'] = 3
        del payload['state']['story']
        self.game.saves.path.write_text(json.dumps(payload), encoding='utf-8')
        self.assertTrue(self.game.load())
        self.assertEqual(self.game.state.evidence_ids, ['photo'])
        self.assertEqual(self.game.state.location, 'apartment')
        self.assertTrue(self.game.state.story['qte_complete'])
        self.assertFalse(self.game.state.story['mvp_complete'])
        self.game.save()
        self.assertTrue(self.game.load())


if __name__ == '__main__':
    unittest.main()
