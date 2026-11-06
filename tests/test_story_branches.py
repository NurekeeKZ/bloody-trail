import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import tempfile
import time
import unittest
from pathlib import Path
import pygame
from src.core.config import ROOT, data
from src.core.game import Game
from src.scenes.investigation import Investigation, ObjectInspection
from src.scenes.evidence_board import Board
from src.scenes.overlays import Dialogue
from src.scenes.results import Results
from src.scenes.thriller import BranchEnding
from src.scenes.campaign import ChapterIntro
from src.scenes.prologue import Prologue
from src.scenes.sensors import SensorChallenge, GUARD_REACTIONS
from src.systems.campaign import epilogue

CONFESSION = 'Спросить о постановлении 2020 года'
WARNING = 'Предупредить: вы следующий в списке'


class FakeSession:
    def __init__(self):
        self.events = []
        self.active = True

    def poll(self):
        events, self.events = self.events, []
        return events

    def close(self):
        self.active = False


class StoryBranchTests(unittest.TestCase):
    """Optional plot branches: mole Ermekov, second murder, red herring Aidos, spared Nikita."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / 'tests')
        self.game = Game(storage_dir=Path(self.folder.name))
        self.game.new_game(prologue=False)

    def tearDown(self):
        self.game.scenes.close()
        pygame.quit()
        self.folder.cleanup()

    def collect(self, *ids):
        for eid in ids:
            self.game.evidence.collect(eid)

    def sokolov_labels(self):
        _, choices = self.game.dialogues.get('sokolov', self.game.state.evidence_ids, self.game.state.flags)
        return [c['label'] for c in choices]

    def inspect(self, room_id, spot_id):
        room = Investigation(self.game, room_id)
        spot = next(s for s in room.content['hotspots'] if s['id'] == spot_id)
        detail = ObjectInspection(self.game, room, spot)
        return detail, detail.actions[0]

    def click(self, scene, label):
        button = next(b for b in scene.buttons if b[0] == label)
        scene.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=button[1].center))

    def test_new_rules_are_optional_and_reference_known_evidence(self):
        rules = {r['id']: r for r in self.game.rules}
        for rule_id in ('mole', 'cleanup', 'aidos_alibi'):
            rule = rules[rule_id]
            self.assertTrue(rule['optional'])
            self.assertTrue(set(rule['pair']).issubset(rule['requires']))
            self.assertEqual(len(rule['slots']), len(rule['requires']))
            for eid in rule['requires']:
                self.assertIn(eid, self.game.catalog)

    def test_closure_cabinet_needs_archive_protocol(self):
        detail, action = self.inspect('archive', 'closure')
        self.assertFalse(detail.execute(action))
        self.assertNotIn('closure_2020', self.game.state.evidence_ids)
        self.collect('archive')
        self.assertTrue(detail.execute(action))
        self.assertIn('closure_2020', self.game.state.evidence_ids)
        self.assertIn('Ермеков', self.game.notice)

    def test_mole_chain_unlocks_confession_and_epilogue(self):
        self.collect('order', 'archive', 'closure_2020')
        self.assertNotIn(CONFESSION, self.sokolov_labels())
        reputation = self.game.state.reputation
        ok, _ = self.game.evidence.check_deduction('mole', ['closure_2020', 'order', 'archive'])
        self.assertTrue(ok)
        self.assertIn('mole', self.game.state.flags)
        self.assertEqual(self.game.state.reputation, reputation)
        self.assertIn(CONFESSION, self.sokolov_labels())
        dialogue = Dialogue(self.game, 'sokolov')
        self.game.scenes.push(dialogue)
        self.click(dialogue, CONFESSION)
        self.assertIn('мальчик будет жить', dialogue.writer.text)
        self.assertIn('Ермеков даёт показания', epilogue(self.game.state))
        self.assertIn('Ермеков даёт показания', Results(self.game, 'arrest', persist=False).text)
        self.assertIn('Ермеков даёт показания', BranchEnding(self.game, 'truth').text)
        self.game.save()
        self.assertIn('mole', self.game.saves.load().flags)

    def test_mole_question_solved_through_board_clicks(self):
        self.collect('order', 'archive', 'closure_2020')
        board = Board(self.game)
        self.game.scenes.push(board)
        rects = board.question_rects()
        self.assertIn('mole', rects)
        board.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rects['mole'].center))
        for eid in ('closure_2020', 'order', 'archive'):
            board.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=board.cards[eid].center))
        self.assertEqual(board.slot_values('mole'), ['closure_2020', 'order', 'archive'])
        self.click(board, 'Проверить вывод')
        self.assertIn('mole', self.game.state.flags)
        board.draw(self.game.screen)

    def test_second_murder_reported_once_on_day_two(self):
        self.game.access.unlock()
        self.collect('order')
        self.assertTrue(self.game.enter_location('archive'))
        self.assertEqual(self.game.state.current_day, 2)
        self.assertIn('expert_death', self.game.state.evidence_ids)
        self.assertIn('Ахметов', self.game.notice)
        self.assertIsInstance(self.game.scenes.current, ChapterIntro)
        self.assertIn('Ахметов', data('chapters')['2']['text'])
        self.assertTrue(self.game.enter_location('metro'))
        self.assertEqual(self.game.state.evidence_ids.count('expert_death'), 1)
        self.assertIn('expert_death', self.game.saves.load().evidence_ids)

    def test_no_second_murder_on_day_one(self):
        self.game.accept_case()
        self.game.enter_location('station')
        self.assertNotIn('expert_death', self.game.state.evidence_ids)

    def test_cleanup_chain_unlocks_warning_without_epilogue(self):
        self.collect('expert_death', 'EVIDENCE_BLOOD_MARK_2035', 'closure_2020')
        self.assertNotIn(WARNING, self.sokolov_labels())
        ok, _ = self.game.evidence.check_deduction('cleanup', ['expert_death', 'EVIDENCE_BLOOD_MARK_2035', 'closure_2020'])
        self.assertTrue(ok)
        self.assertIn(WARNING, self.sokolov_labels())
        self.assertNotIn(CONFESSION, self.sokolov_labels())
        self.assertEqual(epilogue(self.game.state), '')

    def test_aidos_shift_record_and_alibi(self):
        detail, action = self.inspect('metro', 'shifts')
        self.assertFalse(detail.execute(action))
        self.collect('transit')
        self.assertTrue(detail.execute(action))
        self.assertIn('aidos_shift', self.game.state.evidence_ids)
        self.assertIn('Айдос', self.game.notice)
        self.collect('pass', 'anna')
        reputation = self.game.state.reputation
        ok, message = self.game.evidence.check_deduction('aidos_alibi', ['aidos_shift', 'transit', 'anna'])
        self.assertFalse(ok)
        self.assertIn('2 из 3', message)
        self.assertEqual(self.game.state.reputation, reputation - 2)
        ok, _ = self.game.evidence.check_deduction('aidos_alibi', ['aidos_shift', 'transit', 'pass'])
        self.assertTrue(ok)
        self.assertIn('Айдос снят с подозрений', epilogue(self.game.state))

    def test_optional_branches_do_not_gate_finale(self):
        mandatory = [r for r in self.game.rules if not r.get('optional')]
        for rule in mandatory:
            self.collect(*rule['requires'])
        self.game.evidence.analyze()
        for flag in ('mole', 'cleanup', 'aidos_alibi'):
            if flag in self.game.state.flags:
                self.game.state.flags.remove(flag)
        self.assertTrue(self.game.evidence.can_finalize())
        self.assertEqual(epilogue(self.game.state), '')
        self.assertNotIn('Ермеков даёт показания', Results(self.game, 'arrest', persist=False).text)

    def test_both_epilogues_combined(self):
        self.game.state.flags.extend(['mole', 'aidos_alibi'])
        text = epilogue(self.game.state)
        self.assertIn('Ермеков даёт показания', text)
        self.assertIn('Айдос снят с подозрений', text)

    def test_prologue_spared_child_scene(self):
        steps = data('prologue')
        texts = [s['text'] for s in steps]
        index = next(i for i, t in enumerate(texts) if 'Таков уговор' in t)
        self.assertTrue(any('Мама' in t for t in texts[:index]))
        prologue = Prologue(self.game)
        prologue.index = index
        prologue.enter()
        self.assertEqual(prologue.step['title'], 'Шаги у детской')
        prologue.update(.5)
        prologue.draw(self.game.screen)

    def test_guard_reacts_to_strong_expression_and_calm_face(self):
        scene = SensorChallenge(self.game, 'calm')
        self.game.scenes.push(scene)
        scene.reset_trial()
        scene.mode = 'sensor'
        scene.session = FakeSession()
        before = list(self.game.state.evidence_ids)

        def sample(emotions):
            scene.session.events = [{'type': 'sample', 'dt': .1, 'at': time.monotonic(),
                                     'present': True, 'reliable': True, 'motion': .01, 'emotions': emotions}]
            scene.update(.1)

        sample({'neutral': .1, 'happiness': .9})
        self.assertFalse(scene.composed)
        self.assertEqual(scene.dominant, 'happiness')
        self.assertIn(GUARD_REACTIONS['happiness'], scene.message)
        scene.draw(self.game.screen)
        sample({'neutral': .95, 'happiness': .05})
        self.assertTrue(scene.composed)
        self.assertIn(GUARD_REACTIONS['neutral'], scene.message)
        sample({})
        self.assertTrue(scene.composed)
        scene.draw(self.game.screen)
        self.assertEqual(self.game.state.evidence_ids, before)


if __name__ == '__main__':
    unittest.main()
