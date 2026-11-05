import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import pygame
from src.core.game import Game
from src.scenes.menu import Menu
from src.scenes.campaign import FullVersion
from src.scenes.prologue import Prologue
from src.systems.profile import ContentAccess

class FullAccessTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).parent);self.game=Game(storage_dir=Path(self.temp.name))
        self.game.scenes.replace(Menu(self.game))
    def tearDown(self):
        self.game.scenes.close();pygame.quit();self.temp.cleanup()
    def click(self,scene,index=0):
        scene.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=scene.buttons[index][1].center))
    def test_menu_mouse_unlock_start_and_persistence(self):
        menu=self.game.scenes.current
        self.click(menu,next(i for i,b in enumerate(menu.buttons) if b[0]=='Полная версия / доступ'))
        screen=self.game.scenes.current;self.assertIsInstance(screen,FullVersion)
        self.click(screen)
        self.assertTrue(ContentAccess(self.game.access.path).allows(3))
        self.assertEqual(screen.buttons[0][0],'Начать полную историю')
        self.click(screen);self.assertIsInstance(self.game.scenes.current,Prologue)
    def test_already_unlocked_shows_play_not_unlock(self):
        self.game.access.unlock();screen=FullVersion(self.game)
        self.assertEqual(screen.buttons[0][0],'Начать полную историю')
    def test_resume_does_not_reset_progress(self):
        self.game.new_game(prologue=False);self.game.accept_case();self.game.to_menu()
        screen=FullVersion(self.game);self.game.scenes.push(screen);self.click(screen)
        self.assertEqual(screen.buttons[0][0],'Продолжить сохранённую игру')
        self.click(screen);self.assertIn('order',self.game.state.evidence_ids)
    def test_selected_slot_retried_on_unlock(self):
        screen=FullVersion(self.game,load_slot='manual');self.game.scenes.push(screen)
        with patch.object(self.game,'load',return_value=True) as load:
            self.click(screen);load.assert_called_once_with('manual')
    def test_load_gate_passes_original_slot(self):
        self.game.state.location='archive'
        with patch.object(self.game.saves,'load',return_value=self.game.state):
            self.assertFalse(self.game.load())
        screen=self.game.scenes.current
        self.assertIsInstance(screen,FullVersion);self.assertEqual(screen.load_slot,'auto')
    def test_write_error_no_false_success_and_retry(self):
        screen=FullVersion(self.game)
        with patch('src.systems.profile.atomic_json',side_effect=PermissionError('read only')):
            self.click(screen)
        self.assertFalse(self.game.access.full_version_unlocked)
        self.assertIn('Не удалось',screen.message)
        self.click(screen);self.assertTrue(self.game.access.full_version_unlocked)
    def test_render_states(self):
        screen=FullVersion(self.game);screen.draw(self.game.screen)
        screen.unlock();screen.draw(self.game.screen)

if __name__=='__main__':unittest.main()

