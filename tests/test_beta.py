"""Beta regression: real scene callbacks; no microphone/camera activation."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import json
import tempfile
import unittest
from pathlib import Path
from collections import deque
import pygame
from src.core.game import Game
from src.core.config import ROOT
from src.scenes.menu import Menu
from src.scenes.overlays import Assistant, Dialogue, FinalChoice
from src.scenes.investigation import Investigation, ObjectInspection
from src.scenes.campaign import FullVersion, WeirConfrontation, CaseStatus, Leaderboard
from src.scenes.results import Results, GameOver
from src.scenes.qte import StoryQTE
from src.scenes.sensors import SensorChallenge, GuardDialogue
from src.systems.profile import ContentAccess


class BetaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "tests")
        self.game = Game(storage_dir=Path(self.temp.name))
        self.game.scenes.current.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE))
        self.assertIsInstance(self.game.scenes.current,Menu)
        self.game.new_game(prologue=False)

    def tearDown(self):
        self.game.scenes.close()
        pygame.quit()
        self.temp.cleanup()

    def collect(self, location):
        room = Investigation(self.game, location)
        spots = sorted(room.content['hotspots'], key=lambda s:s.get('evidence') == 'metadata')
        for spot in spots:
            if spot.get('evidence') in ('anna','transit'): continue
            detail = ObjectInspection(self.game,room,spot)
            for action in detail.actions:
                if action['type']=='collect' and action['evidence'] not in self.game.state.evidence_ids:
                    self.assertTrue(detail.execute(action), (location,action))

        from scenario_steps import solve_location
        solve_location(self.game,location)

    def analyze(self):
        assistant = Assistant(self.game)
        assistant.input = 'сравни следы'
        assistant.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN))
        from scenario_steps import deduce
        deduce(self.game)

    def travel(self,location):
        self.assertTrue(self.game.travel(location), location)
        if isinstance(self.game.scenes.current,StoryQTE):
            qte=self.game.scenes.current
            qte.start()
            for key in qte.sequence: qte.event(pygame.event.Event(pygame.KEYDOWN,key=key))
        self.assertEqual(self.game.state.location,location)
        self.assertTrue(self.game.load(), self.game.notice)

    def day_one(self):
        dlg=Dialogue(self.game,'sokolov')
        dlg.choose(next(c for c in self.game.dialogues.conversations['sokolov']['choices'] if c.get('action')=='accept_case'))
        self.collect('station')
        self.analyze()
        self.travel('apartment')
        self.collect('apartment')
        self.analyze()

    def route(self):
        self.day_one()
        self.assertFalse(self.game.travel('archive'))
        self.assertIsInstance(self.game.scenes.current,FullVersion)
        self.game.scenes.current.unlock()
        self.assertEqual(self.game.state.location,'archive')
        self.collect('archive')
        self.analyze()
        self.travel('metro')
        dialogue=Dialogue(self.game,'anna')
        choice=next(c for c in self.game.dialogues.conversations['anna']['choices'] if c.get('effect_id')=='anna_respect')
        dialogue.choose(choice)
        trust=self.game.state.trust['anna']
        dialogue.choose(choice)
        self.assertEqual(self.game.state.trust['anna'],trust)
        challenge=SensorChallenge(self.game,'calm')
        challenge.start_manual()
        for _ in range(48):
            challenge.pulse()
            challenge.update(.25)
        self.assertEqual(self.game.state.statistics['guard_shortcut'],1)
        guard=GuardDialogue(self.game)
        guard.answer(True)
        self.travel('helios')
        self.collect('helios')
        self.analyze()
        self.travel('port')
        self.collect('port')
        self.analyze()
        self.assertTrue(self.game.evidence.can_finalize())
        self.assertEqual(self.game.state.current_day,3)
        self.assertEqual(self.game.state.time_remaining,13)

    def test_full_route_three_endings_achievements_journal(self):
        self.route()
        self.assertFalse(self.game.finish_case('arrest'))
        self.game.backup_case()
        WeirConfrontation(self.game).present()
        snapshot=self.game.state.to_dict()
        from src.core.state import GameState
        for ending in ('arrest','revenge','release'):
            self.game.bind_state(GameState(**json.loads(json.dumps(snapshot))))
            FinalChoice(self.game).finish(ending)
            self.assertIsInstance(self.game.scenes.current,Results)
            self.assertEqual(self.game.saves.load().ending,ending)
            self.assertFalse(self.game.finish_case('release'))
            if ending=='arrest': self.assertEqual(len(self.game.state.achievements),5)
            self.assertEqual(len(self.game.journal.read()),1)
        self.assertEqual(self.game.state.reputation,85)
        self.assertTrue(self.game.load())
        self.assertEqual(len(self.game.journal.read()),1)

    def test_demo_load_and_direct_entry_blocked(self):
        self.day_one()
        before=self.game.state.to_dict()
        self.assertFalse(self.game.enter_location('archive'))
        self.assertEqual(self.game.state.to_dict(),before)
        self.game.access.unlock()
        self.travel('archive')
        self.game.access.full_version_unlocked=False
        self.assertFalse(self.game.load())
        self.assertIsInstance(self.game.scenes.current,FullVersion)
        self.assertTrue(ContentAccess(self.game.access.path).full_version_unlocked)

    def test_qte_adaptation_and_no_duplicate_reward(self):
        self.game.accept_case()
        self.game.evidence.collect('photo'); self.game.evidence.collect('metadata'); self.analyze()
        self.game.travel('apartment');qte=self.game.scenes.current
        for _ in range(2):
            qte.start();qte.update(4)
        self.assertEqual(self.game.state.health,30)
        self.assertTrue(any('6 с' in b[0] for b in qte.buttons))
        qte.adapt();self.assertEqual(qte.limit,6)
        score=self.game.evidence.score
        self.assertFalse(self.game.evidence.collect('photo'))
        self.assertEqual(score,self.game.evidence.score)

    def test_deduction_errors_and_hint(self):
        from src.scenes.evidence_board import Board
        self.game.accept_case();self.game.evidence.collect('photo')
        board=Board(self.game);board.select('order');board.select('photo');board.propose()
        for _ in range(3): board.confirm()
        self.assertEqual(self.game.state.reputation,94)
        self.assertIn('N.U.R.S.',self.game.notice)
        self.assertFalse(self.game.evidence.can_finalize())

    def test_insufficient_and_deadline(self):
        self.day_one()
        self.game.fail('insufficient')
        self.assertIsInstance(self.game.scenes.current,GameOver)
        self.assertEqual(self.game.saves.load().ending,'insufficient')
        self.assertEqual(len(self.game.journal.read()),1)
        self.game.new_game(prologue=False)
        self.assertFalse(self.game.spend_time(18,'Тест срока'))
        self.assertEqual(self.game.saves.load().time_remaining,0)

    def test_resources_gate_arrest(self):
        self.route();self.game.backup_case();WeirConfrontation(self.game).present()
        self.game.state.reputation=39
        self.assertFalse(self.game.finish_case('arrest'))
        self.assertTrue(self.game.finish_case('release'))

    def test_render_beta_screens(self):
        self.game.access.unlock()
        folder=ROOT/'docs/screenshots'
        for name,scene in [('beta_full',FullVersion(self.game)),('beta_status',CaseStatus(self.game)),('beta_table',Leaderboard(self.game)),('beta_port',Investigation(self.game,'port'))]:
            if name == 'beta_port': self.game.state.current_day=3
            scene.draw(self.game.screen)
            pygame.image.save(self.game.screen,str(folder/(name+'.png')))

    def test_maps_have_reachable_interactions(self):
        # Grid flood fill with actual player footprint checks, including new obstacles.
        for name,world in self.game.worlds.items():
            walls=[pygame.Rect(r) for r in world['walls']]+[pygame.Rect(o['rect']) for o in world['objects'] if o['kind'] in ('investigation','board')]
            def free(p):
                r=pygame.Rect(0,0,24,18);r.center=p
                return 12<=p[0]<world['size'][0]-12 and 9<=p[1]<world['size'][1]-9 and not any(r.colliderect(w) for w in walls)
            start=tuple(world['spawn']);visited={start};queue=deque([start])
            while queue:
                x,y=queue.popleft()
                for p in ((x+16,y),(x-16,y),(x,y+16),(x,y-16)):
                    if p not in visited and free(p):visited.add(p);queue.append(p)
            from src.systems.interaction import InteractionSystem
            for obj in world['objects']:
                self.assertTrue(any(InteractionSystem().nearest(p,[obj],walls) for p in visited), (name,obj['id']))

if __name__=='__main__':unittest.main()
