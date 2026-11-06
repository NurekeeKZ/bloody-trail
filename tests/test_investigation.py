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
from src.scenes.investigation import Investigation, ObjectInspection
from src.scenes.evidence_board import Board, EvidenceDetail
from src.scenes.overlays import Dialogue, Inventory, FinalChoice
from src.scenes.transition import FadeTransition
from src.ui.investigation_art import InvestigationArt


class InvestigationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / 'tests')
        self.game = Game(storage_dir=Path(self.folder.name))
        self.game.new_game(prologue=False)
        self.exploration = self.game.scenes.current
        self.room = Investigation(self.game, 'station')

    def tearDown(self):
        pygame.quit()
        self.folder.cleanup()

    def key(self, key):
        self.game.scenes.current.event(pygame.event.Event(pygame.KEYDOWN, key=key))

    def click(self, label):
        scene = self.game.scenes.current
        button = next(b for b in scene.buttons if b[0] == label)
        scene.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=button[1].center))

    def open_object(self, name):
        spot = next(s for s in self.room.content['hotspots'] if s['id'] == name)
        self.room.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pygame.Rect(spot['rect']).center))
        self.assertIsInstance(self.game.scenes.current, ObjectInspection)
        return self.game.scenes.current

    def test_station_full_cycle_changes_dialogue_and_preserves_position(self):
        self.game.accept_case()
        self.exploration.player.position.update(500, 435)
        self.exploration.player.rect.center = (500, 435)
        self.exploration.update(0)
        position = self.game.state.position[:]
        self.key(pygame.K_e)
        self.assertIsInstance(self.game.scenes.current, FadeTransition)
        self.game.update(0.1)
        self.assertEqual(self.game.state.position, position)
        self.game.update(0.4)
        self.room = self.game.scenes.current
        self.assertIsInstance(self.room, Investigation)
        self.open_object('documents')
        self.click('Зафиксировать фотографию')
        self.key(pygame.K_ESCAPE)
        self.open_object('computer')
        self.click('Проверить удалённые файлы')
        self.key(pygame.K_ESCAPE)
        self.open_object('folders')
        self.assertFalse(self.game.scenes.current.buttons[0][3])
        self.key(pygame.K_ESCAPE)
        self.assertEqual(set(self.game.state.evidence_ids), {'photo', 'metadata', 'order'})
        self.key(pygame.K_TAB)
        self.assertIsInstance(self.game.scenes.current, Inventory)
        self.click('Открыть фотографию / документ')
        self.assertIsInstance(self.game.scenes.current, EvidenceDetail)
        self.key(pygame.K_ESCAPE)
        self.key(pygame.K_ESCAPE)
        _, choices = self.game.dialogues.get('sokolov', self.game.state.evidence_ids, self.game.state.flags)
        self.assertFalse(any('requires_flags' in c for c in choices))
        self.key(pygame.K_b)
        board = self.game.scenes.current
        self.assertIsInstance(board, Board)
        board.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=board.question_rects()['initial_anomaly'].center))
        for eid in ('photo', 'metadata'):
            board.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=board.cards[eid].center))
        self.assertEqual(board.slot_values('initial_anomaly'), ['photo', 'metadata'])
        self.assertNotIn('initial_anomaly', self.game.state.flags)
        self.click('Проверить вывод')
        self.assertIn('initial_anomaly', self.game.state.flags)
        self.assertEqual(self.game.state.hypotheses['metadata|photo']['status'], 'confirmed')
        self.assertFalse(self.game.evidence.can_finalize())
        self.key(pygame.K_ESCAPE)
        self.open_object('phone')
        self.click('Связаться с Ермековым')
        dialogue = self.game.scenes.current
        self.assertIsInstance(dialogue, Dialogue)
        self.click('Обсудить связь снимка и удаления')
        self.assertIn('Связь записи со снимком подтверждена', dialogue.writer.text)
        self.key(pygame.K_ESCAPE)
        self.key(pygame.K_ESCAPE)
        self.click('Вернуться [Esc]')
        self.assertIsInstance(self.game.scenes.current, FadeTransition)
        self.game.update(0.5)
        self.assertIs(self.game.scenes.current, self.exploration)
        self.assertEqual(self.game.state.position, position)
        loaded = self.game.saves.load()
        self.assertEqual(loaded.hypotheses, self.game.state.hypotheses)
        self.assertEqual(loaded.evidence_records['photo']['related'], ['metadata'])

    def test_gated_action_cannot_be_called_early_or_repeated_for_rewards(self):
        self.game.scenes.push(self.room)
        detail = self.open_object('computer')
        action = next(a for a in detail.actions if a['id'] == 'deleted')
        self.assertFalse(detail.execute(action))
        self.assertEqual(self.game.state.evidence_ids, [])
        self.game.evidence.collect('photo')
        self.assertTrue(detail.execute(action))
        snapshot = self.game.state.to_dict()
        self.assertFalse(detail.execute(action))
        self.assertEqual(snapshot, self.game.state.to_dict())

    def test_invalid_link_explained_rejected_and_no_flags(self):
        for eid in ('photo', 'order'):
            self.game.evidence.collect(eid)
        key = self.game.evidence.propose('photo', 'order')
        explanation = self.game.evidence.evaluate(key)
        self.assertIn('нет основания', explanation)
        self.assertEqual(self.game.state.hypotheses[key]['status'], 'rejected')
        self.assertEqual(self.game.state.flags, [])
        self.assertFalse(self.game.state.evidence_records['photo']['verified'])

    def test_slot_deduction_wrong_missing_and_correct(self):
        for eid in ('anna', 'transit', 'order'):
            self.game.evidence.collect(eid)
        ok, message = self.game.evidence.check_deduction('route', ['anna', 'transit', 'order'])
        self.assertFalse(ok)
        self.assertIn('не все материалы', message)
        self.assertEqual(self.game.state.statistics.get('deduction_mistakes', 0), 0)
        self.game.evidence.collect('pass')
        reputation = self.game.state.reputation
        ok, message = self.game.evidence.check_deduction('route', ['anna', 'order', 'pass'])
        self.assertFalse(ok)
        self.assertIn('подходят 2 из 3', message)
        self.assertEqual(self.game.state.reputation, reputation - 2)
        self.assertNotIn('route', self.game.state.flags)
        ok, _ = self.game.evidence.check_deduction('route', ['pass', 'anna', 'transit'])
        self.assertTrue(ok)
        self.assertIn('route', self.game.state.flags)
        self.assertEqual(self.game.state.hypotheses['anna|transit']['status'], 'confirmed')

    def test_board_slots_target_and_toggle(self):
        for eid in ('photo', 'metadata'):
            self.game.evidence.collect(eid)
        board = Board(self.game)
        board.choose_question('initial_anomaly')
        board.place('photo')
        board.place('metadata')
        self.assertEqual(board.slot_values('initial_anomaly'), ['photo', 'metadata'])
        board.clear_slot(0)
        board.place('metadata')
        self.assertEqual(board.slot_values('initial_anomaly'), [None, None])
        board.clear_slot(0)
        board.place('metadata')
        self.assertEqual(board.slot_values('initial_anomaly'), ['metadata', None])
        board.draw(self.game.screen)

    def test_valid_pair_needs_independent_third_source(self):
        for eid in ('anna', 'transit'):
            self.game.evidence.collect(eid)
        key = self.game.evidence.propose('anna', 'transit')
        self.assertIn('Пропуск Сарсенова', self.game.evidence.evaluate(key))
        self.assertEqual(self.game.state.hypotheses[key]['status'], 'pending')
        self.assertNotIn('route', self.game.state.flags)
        self.game.evidence.collect('pass')
        self.game.evidence.evaluate(key)
        self.assertIn('route', self.game.state.flags)

    def test_pair_order_unique_and_manual_rejection_recheck(self):
        for eid in ('photo', 'metadata'):
            self.game.evidence.collect(eid)
        key = self.game.evidence.propose('photo', 'metadata')
        self.assertEqual(key, self.game.evidence.propose('metadata', 'photo'))
        self.assertEqual(len(self.game.state.hypotheses), 1)
        self.game.evidence.reject(key)
        self.assertEqual(self.game.state.hypotheses[key]['status'], 'rejected')
        self.game.evidence.evaluate(key)
        self.assertEqual(self.game.state.hypotheses[key]['status'], 'confirmed')
        self.game.evidence.reject(key)
        self.assertEqual(self.game.state.hypotheses[key]['status'], 'confirmed')

    def test_missing_or_same_evidence_cannot_link(self):
        self.game.evidence.collect('photo')
        for pair in [('photo', 'photo'), ('photo', 'metadata')]:
            with self.assertRaises(ValueError):
                self.game.evidence.propose(*pair)

    def test_forged_confirmed_link_rejected_on_load(self):
        for eid in ('photo', 'order'):
            self.game.evidence.collect(eid)
        key = self.game.evidence.propose('photo', 'order')
        self.game.state.hypotheses[key]['status'] = 'confirmed'
        self.game.save()
        with self.assertRaises(ValueError):
            self.game.saves.load()

    def test_schema_migration_v2_and_all_hypothesis_states_roundtrip(self):
        old = self.game.state.to_dict()
        old.pop('hypotheses')
        self.game.saves.path.write_text(json.dumps({'version': 2, 'state': old}), encoding='utf-8')
        self.assertEqual(self.game.saves.load().hypotheses, {})
        for eid in ('photo', 'metadata', 'order', 'anna', 'transit'):
            self.game.evidence.collect(eid)
        for a, b in [('photo', 'metadata'), ('photo', 'order'), ('anna', 'transit')]:
            self.game.evidence.evaluate(self.game.evidence.propose(a, b))
        self.game.save()
        self.assertEqual(self.game.saves.load().to_dict(), self.game.state.to_dict())
        self.assertEqual({h['status'] for h in self.game.state.hypotheses.values()}, {'confirmed', 'pending', 'rejected'})

    def test_assets_and_seven_non_overlapping_hotspots(self):
        spots = self.room.content['hotspots']
        self.assertGreaterEqual(len(spots), 7)
        self.assertEqual(len({s['evidence'] for s in spots if 'evidence' in s}), 3)
        for i, spot in enumerate(spots):
            self.assertTrue(spot['actions'])
            for other in spots[i + 1:]:
                self.assertFalse(pygame.Rect(spot['rect']).colliderect(pygame.Rect(other['rect'])))
        for eid, entry in self.game.catalog.items():
            self.assertEqual(entry['id'], eid)
            self.assertTrue((ROOT / entry['image']).is_file())
        self.assertTrue((ROOT / self.room.content['background']).is_file())

    def test_hover_cursor_and_asset_replacement_without_logic(self):
        spot = self.room.content['hotspots'][0]
        self.game.mouse = pygame.Rect(spot['rect']).center
        self.room.draw(self.game.screen)
        self.assertIs(self.room.hovered_spot, spot)
        self.assertEqual(self.room.cursor, pygame.SYSTEM_CURSOR_HAND)
        self.game.mouse = (0, 0)
        self.room.draw(self.game.screen)
        self.assertEqual(self.room.cursor, pygame.SYSTEM_CURSOR_ARROW)
        before = self.game.state.to_dict()
        renderer = InvestigationArt()
        alternative = dict(self.room.content, background='assets/reference/image1.png')
        renderer.background(self.game.screen, alternative, self.game.art)
        renderer.background(self.game.screen, dict(alternative, background='missing.png'), self.game.art)
        self.assertEqual(before, self.game.state.to_dict())

    def test_early_conclusion_cannot_unlock_ending(self):
        for eid in ('photo', 'metadata'):
            self.game.evidence.collect(eid)
        self.game.evidence.evaluate(self.game.evidence.propose('photo', 'metadata'))
        self.game.state.location = 'helios'
        FinalChoice(self.game).finish('arrest')
        self.assertEqual(self.game.state.ending, '')

    def test_board_native_double_click_opens_document(self):
        self.game.evidence.collect('photo')
        board = Board(self.game)
        self.game.scenes.push(board)
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=board.cards['photo'].center)
        board.event(event)
        board.event(event)
        self.assertIsInstance(self.game.scenes.current, EvidenceDetail)


if __name__ == '__main__':
    unittest.main()
