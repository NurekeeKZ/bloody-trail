import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import json
import tempfile
import unittest
from pathlib import Path
from collections import defaultdict
from unittest.mock import patch
import pygame
from src.core.config import ROOT
from src.core.game import Game
from src.scenes.menu import Splash, Menu, Pause, ConfirmNew
from src.scenes.exploration import Exploration
from src.scenes.overlays import FinalChoice
from src.scenes.results import Results, GameOver, format_time
from src.scenes.settings import SettingsScene, LoadScene, AdditionalCases, QTEPractice
from src.systems.settings import SettingsManager


class Lab09Tests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / 'tests')
        self.game = Game(storage_dir=Path(self.folder.name))

    def tearDown(self):
        pygame.quit()
        self.folder.cleanup()

    def click(self, label, scene=None):
        scene = scene or self.game.scenes.current
        button = next(b for b in scene.buttons if b[0] == label)
        scene.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=button[1].center))

    def key(self, key, scene=None):
        (scene or self.game.scenes.current).event(pygame.event.Event(pygame.KEYDOWN, key=key))

    def start(self):
        self.key(pygame.K_SPACE)
        self.click('Новая игра')
        from src.scenes.prologue import Prologue
        self.assertIsInstance(self.game.scenes.current, Prologue)
        self.game.new_game(prologue=False)  # Isolate the original gameplay regression fixtures.

    def test_start_waits_and_menu_has_six_working_entries(self):
        self.game.update(20)
        self.assertIsInstance(self.game.scenes.current, Splash)
        self.key(pygame.K_SPACE)
        menu = self.game.scenes.current
        self.assertIsInstance(menu, Menu)
        self.assertEqual(len(menu.buttons), 9)
        self.assertFalse(menu.buttons[1][3])
        self.click('Продолжить')
        self.assertIs(self.game.scenes.current, menu)
        for label, cls in [('Загрузить', LoadScene), ('Настройки', SettingsScene), ('Дополнительные дела', AdditionalCases)]:
            self.click(label)
            self.assertIsInstance(self.game.scenes.current, cls)
            self.key(pygame.K_ESCAPE)
            self.assertIs(self.game.scenes.current, menu)
        self.click('Выход')
        self.assertFalse(self.game.running)

    def test_full_success_transition_chain(self):
        self.game.access.unlock()
        self.start()
        self.game.accept_case()
        exploration = self.game.scenes.current
        self.assertIsInstance(exploration, Exploration)
        self.key(pygame.K_ESCAPE)
        self.assertIsInstance(self.game.scenes.current, Pause)
        self.click('Продолжить')
        self.assertIs(self.game.scenes.current, exploration)
        for location in self.game.worlds:
            if location != self.game.state.location:
                self.game.evidence.analyze()
                self.assertTrue(self.game.travel(location))
                if location in ('apartment', 'metro'):
                    qte = self.game.scenes.current
                    qte.start()
                    for key in qte.sequence:
                        self.key(key, qte)
                    self.game.scenes.pop()
            for spot in self.game.investigations[location]['hotspots']:
                if 'evidence' in spot:
                    self.game.evidence.collect(spot['evidence'])
            from scenario_steps import solve_location
            solve_location(self.game,location)
        self.game.evidence.analyze()
        self.game.backup_case()
        self.game.state.campaign['weir_confronted'] = True
        final = FinalChoice(self.game)
        self.game.scenes.push(final)
        self.click('Вызвать подкрепление')
        self.assertIsInstance(self.game.scenes.current, Results)
        self.assertEqual(self.game.state.ending, 'arrest')
        self.click('Главное меню')
        self.assertIsInstance(self.game.scenes.current, Menu)
        self.click('Продолжить')
        self.assertIsInstance(self.game.scenes.current, Results)

    def test_failure_retry_and_menu_transition(self):
        self.start()
        checkpoint = self.game.save_manager('checkpoint').load().to_dict()
        self.game.evidence.collect('photo')
        self.key(pygame.K_ESCAPE)
        self.click('Отказаться от дела…')
        self.click('Подтвердить отказ')
        self.assertIsInstance(self.game.scenes.current, GameOver)
        self.assertEqual(self.game.save_manager('checkpoint').load().to_dict(), checkpoint)
        self.click('Повторить с контрольной точки')
        self.assertIsInstance(self.game.scenes.current, Exploration)
        self.assertEqual(self.game.state.to_dict(), checkpoint)
        self.game.fail()
        self.click('Загрузить сохранение')
        self.assertIsInstance(self.game.scenes.current, LoadScene)
        self.key(pygame.K_ESCAPE)
        self.click('Главное меню')
        self.assertIsInstance(self.game.scenes.current, Menu)

    def test_pause_all_settings_links_and_escape(self):
        self.start()
        self.key(pygame.K_ESCAPE)
        pause = self.game.scenes.current
        for label, section in [('Настройки звука', 'sound'), ('Настройки управления', 'controls'),
                               ('Доступность QTE', 'qte'), ('Разрешение камеры', 'privacy'), ('Разрешение микрофона', 'privacy')]:
            self.click(label)
            self.assertEqual(self.game.scenes.current.section, section)
            self.key(pygame.K_ESCAPE)
            self.assertIs(self.game.scenes.current, pause)
        self.click('Сохранить')
        self.assertTrue(self.game.save_manager('manual').path.exists())
        self.click('Загрузить')
        self.assertIsInstance(self.game.scenes.current, LoadScene)
        self.key(pygame.K_ESCAPE)
        self.click('Главное меню')
        self.assertIsInstance(self.game.scenes.current, Menu)

    def test_manual_slot_is_independent(self):
        self.start()
        self.game.evidence.collect('photo')
        self.game.manual_save()
        manual = self.game.save_manager('manual').load().to_dict()
        self.game.evidence.collect('metadata')
        self.game.save()
        self.game.new_game(prologue=False)
        self.assertEqual(self.game.save_manager('manual').load().to_dict(), manual)
        self.assertTrue(self.game.load('manual'))
        self.assertEqual(self.game.state.evidence_ids, ['photo'])

    def test_load_empty_and_corrupt_slots(self):
        empty = LoadScene(self.game)
        self.assertTrue(all(not b[3] for b in empty.buttons[:3]))
        self.start()
        self.game.manual_save()
        self.game.saves.path.write_text('{broken', encoding='utf-8')
        scene = LoadScene(self.game)
        self.assertFalse(scene.buttons[0][3])
        self.assertTrue(scene.buttons[1][3])
        before = self.game.state.to_dict()
        self.assertFalse(self.game.load())
        self.assertEqual(self.game.state.to_dict(), before)

    def test_settings_persist_audio_and_mute(self):
        scene = SettingsScene(self.game)
        for _ in range(3):
            scene.volume(-20)
        self.assertEqual(self.game.audio.volume, 0)
        self.assertEqual(SettingsManager(self.game.preferences.path).value.volume, 0)
        scene.volume(20)
        self.assertEqual(self.game.audio.volume, 0.2)
        self.assertTrue({'hover', 'click', 'step', 'evidence'}.issubset(self.game.audio.sounds))

    def test_settings_corruption_safe_default(self):
        self.game.preferences.path.write_text('{"camera_consent": "yes"}', encoding='utf-8')
        manager = SettingsManager(self.game.preferences.path)
        self.assertFalse(manager.value.camera_consent)
        self.assertTrue(manager.error)

    def test_controls_change_actual_direction(self):
        self.start()
        keys = defaultdict(bool, {pygame.K_d: True})
        self.game.set_setting('controls', 'arrows')
        self.assertEqual(self.game.scenes.current.direction(keys), (0, 0))
        keys[pygame.K_RIGHT] = True
        self.assertEqual(self.game.scenes.current.direction(keys), (1, 0))
        self.game.set_setting('controls', 'wasd')
        keys[pygame.K_d] = False
        self.assertEqual(self.game.scenes.current.direction(keys), (0, 0))

    def test_sensor_consent_confirmation_cancel_and_revoke(self):
        scene = SettingsScene(self.game, 'privacy')
        self.game.scenes.push(scene)
        for key in ('microphone_consent', 'camera_consent'):
            scene.consent(key)
            self.assertFalse(getattr(self.game.settings, key))
            self.key(pygame.K_ESCAPE)
            self.assertFalse(getattr(self.game.settings, key))
            scene.consent(key)
            self.click('Сохранить согласие')
            self.assertTrue(getattr(self.game.settings, key))
            self.assertTrue(getattr(SettingsManager(self.game.preferences.path).value, key))
            scene.consent(key)
            self.assertFalse(getattr(self.game.settings, key))

    def test_qte_modes_and_no_story_mutation(self):
        before = self.game.state.to_dict()
        for mode, limit in [('standard', 3), ('easy', 6), ('untimed', None)]:
            self.game.set_setting('qte_mode', mode)
            scene = QTEPractice(self.game)
            self.assertEqual(scene.limit, limit)
            scene.update(10)
            self.assertEqual(bool(scene.result), limit is not None)
            scene.reset()
            for key in (pygame.K_a, pygame.K_d, pygame.K_SPACE):
                self.key(key, scene)
            self.assertIn('Успех', scene.result)
        self.assertEqual(before, self.game.state.to_dict())

    def test_time_excludes_pause_settings_results_and_counts_elapsed(self):
        self.game.update(10)
        self.assertEqual(self.game.state.play_seconds, 0)
        self.start()
        self.game.update(0.05, 2)
        self.assertEqual(self.game.state.play_seconds, 2)
        self.key(pygame.K_ESCAPE)
        self.game.update(9)
        self.click('Настройки звука')
        self.game.update(9)
        self.assertEqual(self.game.state.play_seconds, 2)
        self.assertEqual(format_time(3661), '01:01:01')

    def test_old_save_migration(self):
        self.start()
        old = self.game.state.to_dict()
        old.pop('play_seconds')
        self.game.saves.path.write_text(json.dumps({'version': 1, 'state': old}), encoding='utf-8')
        self.assertTrue(self.game.load())
        self.assertEqual(self.game.state.play_seconds, 0)

    def test_fullscreen_invokes_real_display_flags_and_persists(self):
        with patch('pygame.display.set_mode', return_value=pygame.Surface((1920, 1080))) as set_mode:
            self.game.toggle_fullscreen()
            set_mode.assert_called_with((0, 0), pygame.FULLSCREEN)
            self.assertTrue(SettingsManager(self.game.preferences.path).value.fullscreen)
            self.game.toggle_fullscreen()
            set_mode.assert_called_with((1280, 720), pygame.RESIZABLE)

    def test_button_hover_once_and_keyboard_navigation(self):
        self.key(pygame.K_SPACE)
        menu = self.game.scenes.current
        self.game.mouse = menu.buttons[2][1].center
        with patch.object(self.game.audio, 'play') as play:
            menu.draw_buttons(self.game.screen)
            menu.draw_buttons(self.game.screen)
            play.assert_called_once_with('hover')
        self.key(pygame.K_DOWN)
        self.key(pygame.K_DOWN)
        self.assertEqual(menu.focus, 2)  # Disabled Continue is skipped.
        self.key(pygame.K_RETURN)
        self.assertIsInstance(self.game.scenes.current, LoadScene)

    def test_reduced_motion_disables_fade_and_rain_animation(self):
        self.game.set_setting('reduced_motion', True)
        self.game.draw(0)
        first = pygame.image.tobytes(self.game.screen, 'RGB')
        self.game.update(1)
        self.game.draw(1)
        self.assertEqual(first, pygame.image.tobytes(self.game.screen, 'RGB'))

    def test_results_and_gameover_do_not_create_checkpoint(self):
        self.start()
        before = self.game.save_manager('checkpoint').path.read_bytes()
        self.game.fail()
        self.game.save()
        self.assertEqual(self.game.save_manager('checkpoint').path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
