import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import json,tempfile,unittest
from pathlib import Path
import pygame
from src.core.game import Game
from src.core.config import ROOT,data
from src.core.state import GameState
from src.scenes.exploration import Exploration
from src.scenes.investigation import Investigation,ObjectInspection
from src.scenes.overlays import Assistant,Dialogue
from src.scenes.puzzles import PuzzleScene
from src.ai.pathfinding import NPCPathfinding
from src.ai.companion import CompanionAI
from src.ui.portraits import PortraitManager,CHARACTERS,EMOTIONS
from scenario_steps import solve_location,deduce

class ExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'tests')
        cls.game=Game(storage_dir=Path(cls.temp.name))
    @classmethod
    def tearDownClass(cls):
        cls.game.scenes.close();pygame.quit();cls.temp.cleanup()
    def setUp(self):
        self.game.new_game(prologue=False)
    def test_portraits_all_emotions_and_fallback(self):
        manager=PortraitManager()
        for key in CHARACTERS:
            for mood in EMOTIONS:
                self.assertTrue((ROOT/'assets/portraits'/key/(mood+'.png')).exists())
                self.assertEqual(manager.get(key,mood).get_size(),(168,224))
        self.assertEqual(pygame.image.tostring(manager.get('nikita','missing'),'RGB'),pygame.image.tostring(manager.get('nikita'),'RGB'))
        self.assertNotEqual(pygame.image.tostring(manager.get('nikita'),'RGB'),pygame.image.tostring(manager.get('sokolov'),'RGB'))
    def test_names_and_family_explanation(self):
        content=' '.join(p.read_text(encoding='utf8') for p in (ROOT/'src/data').rglob('*.json'))
        for old in ('Левицк','Соколов','Вейр','Павел','Марина','Анна'):self.assertNotIn(old,content)
        self.assertIn('сохранил фамилию Волков',content)
        self.assertIn('Нурсултан Ермеков',content)
    def test_astar_detours_and_disconnected(self):
        nav=NPCPathfinding((240,240),[pygame.Rect(96,0,24,170)])
        path=nav.path((36,36),(180,36));self.assertTrue(path)
        self.assertGreater(max(p.y for p in path),170)
        for p in path:self.assertIn(nav.cell(p),nav.free)
        blocked=NPCPathfinding((240,240),[pygame.Rect(96,0,24,240)])
        self.assertEqual(blocked.path((36,36),(180,36)),[])
    def test_follow_motion_and_collision(self):
        scene=self.game.scenes.current;c=scene.companion
        target=pygame.Vector2(850,570);before=c.actor.position.distance_to(target)
        for _ in range(500):
            c.update(.02,target)
            self.assertFalse(any(c.actor.rect.colliderect(w) for w in scene.walls))
            self.assertGreater(c.actor.position.distance_to(target),35)
        self.assertLess(c.actor.position.distance_to(target),100)
        self.assertLess(c.actor.position.distance_to(target),before)
    def test_roam_stay_and_recall(self):
        c=self.game.scenes.current.companion;c.command('stay');before=c.actor.position.copy()
        for _ in range(30):c.update(.1,(900,570))
        self.assertEqual(before,c.actor.position)
        c.command('roam')
        for _ in range(100):c.update(.1,(350,520))
        self.assertGreater(c.actor.position.distance_to(before),10)
        c.command('come')
        for _ in range(350):c.update(.1,(350,520))
        self.assertLess(c.actor.position.distance_to((350,520)),100)
    def test_transition_safe_and_mode_preserved(self):
        self.game.state.companion['mode']='roam'
        for loc,world in self.game.worlds.items():
            self.game.state.location=loc;self.game.state.position=world['spawn'][:]
            scene=Exploration(self.game)
            self.assertEqual(scene.companion.saved['mode'],'roam')
            self.assertFalse(any(scene.companion.actor.rect.colliderect(w) for w in scene.walls))
            self.assertGreater(scene.companion.actor.position.distance_to(scene.player.position),40)
    def test_patrol_moves_without_walls(self):
        scene=self.game.scenes.current;npc=scene.npcs[0];before=npc.actor.position.copy()
        for _ in range(400):
            npc.update(.05,pygame.Vector2(1300,850))
            self.assertFalse(any(npc.actor.rect.colliderect(w) for w in scene.walls))
        self.assertGreater(npc.actor.position.distance_to(before),20)
    def test_puzzle_rejects_missing_context_and_wrong_code(self):
        self.assertFalse(self.game.puzzles.solve('computer','2035')[0])
        self.game.evidence.collect('note');self.game.evidence.collect('book_drive')
        self.assertFalse(self.game.puzzles.solve('computer','0000')[0]);self.assertNotIn('key',self.game.state.evidence_ids)
        self.assertTrue(self.game.puzzles.solve('computer','2035')[0]);score=self.game.evidence.score
        self.assertFalse(self.game.puzzles.solve('computer','2035')[0]);self.assertEqual(score,self.game.evidence.score)
    def test_hidden_rug_is_idempotent(self):
        room=Investigation(self.game,'apartment');spot=next(s for s in room.content['hotspots'] if s['id']=='rug')
        detail=ObjectInspection(self.game,room,spot)
        self.assertTrue(detail.execute(detail.actions[0]));score=self.game.evidence.score
        self.assertFalse(detail.execute(detail.actions[0]));self.assertEqual(score,self.game.evidence.score)
        self.assertIn('note',self.game.state.evidence_ids)
    def test_archive_requires_permission(self):
        self.game.evidence.collect('key')
        self.assertFalse(self.game.puzzles.solve('cell','120')[0])
        self.game.accept_case();d=Dialogue(self.game,'archivist');d.choose(d.node['choices'][0])
        self.assertTrue(self.game.puzzles.solve('cell','120')[0])
    def test_fragments_photos_and_door(self):
        self.assertFalse(self.game.puzzles.solve('fragments','123')[0])
        self.assertTrue(self.game.puzzles.solve('fragments','321')[0])
        p=PuzzleScene(self.game,'photos');p.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(1030,477)))
        self.assertIn('blood',self.game.state.evidence_ids)
        self.assertFalse(self.game.puzzles.solve('door','0714')[0])
        self.game.evidence.collect('key');self.game.evidence.collect('password_note')
        self.assertTrue(self.game.puzzles.solve('door','0714')[0])
    def test_assistant_does_not_solve_deduction(self):
        self.game.accept_case();self.game.evidence.collect('photo');self.game.evidence.collect('metadata')
        assistant=Assistant(self.game);assistant.execute('analyze')
        self.assertEqual(self.game.state.flags,[]);self.assertIn('доске',assistant.response)
        deduce(self.game);self.assertIn('initial_anomaly',self.game.state.flags)
    def test_hint_progression(self):
        for level in (1,2,3,3):self.assertIn(f'{level}/3',self.game.hints.next('apartment'))
        self.assertNotIn('key',self.game.state.evidence_ids)
    def test_save_new_state_and_version6_migration(self):
        self.game.accept_case();self.game.state.location='apartment';solve_location(self.game,'apartment')
        self.game.state.companion['mode']='stay';self.game.hints.next('archive');self.game.state.intuition=42.5
        self.game.save();self.assertEqual(self.game.saves.load().to_dict(),self.game.state.to_dict())
        payload=json.loads(self.game.saves.path.read_text(encoding='utf8'));payload['version']=6
        for key in ('companion','discoveries','intuition'):payload['state'].pop(key)
        self.game.saves.path.write_text(json.dumps(payload),encoding='utf8')
        loaded=self.game.saves.load();self.assertIn('key',loaded.evidence_ids);self.assertEqual(loaded.companion['mode'],'follow')
    def test_render_new_interfaces(self):
        directory=ROOT/'docs/screenshots/expansion';directory.mkdir(exist_ok=True)
        for loc,world in self.game.worlds.items():
            self.game.state.location=loc;self.game.state.position=world['spawn'][:]
            scene=Exploration(self.game);scene.draw(self.game.screen)
            pygame.image.save(self.game.screen,str(directory/(loc+'.png')))
        for name,scene in [('portrait',Dialogue(self.game,'sokolov')),('apartment_room',Investigation(self.game,'apartment')),('photo_puzzle',PuzzleScene(self.game,'photos'))]:
            if hasattr(scene,'writer'):scene.writer.finish()
            scene.draw(self.game.screen);pygame.image.save(self.game.screen,str(directory/(name+'.png')))
    def test_kazakh_glyphs(self):
        self.assertTrue(all(metric is not None for metric in self.game.ui.font(20).metrics('ӘҒҚҢӨҰҮҺІәғқңөұүһі')))

if __name__=='__main__':unittest.main()
