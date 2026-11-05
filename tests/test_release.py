"""RC regressions discovered during release audit."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import json
import tempfile
import unittest
from pathlib import Path
import pygame
from src.core.game import Game
from src.core.config import ROOT

class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'tests')
        self.game=Game(storage_dir=Path(self.tmp.name))
        self.game.new_game(prologue=False)
    def tearDown(self):
        self.game.scenes.close();pygame.quit();self.tmp.cleanup()
    def corrupt(self, mutate):
        payload=json.loads(self.game.saves.path.read_text(encoding='utf-8'))
        mutate(payload['state'])
        self.game.saves.path.write_text(json.dumps(payload),encoding='utf-8')
    def test_missing_source_rejected_at_load(self):
        self.game.evidence.collect('photo');self.game.save()
        self.corrupt(lambda s:s['evidence_records']['photo'].pop('source'))
        with self.assertRaises(ValueError):self.game.saves.load()
    def test_invalid_beta_statistics_rejected_at_load(self):
        for name in ('qte_failures','deduction_mistakes','anna_respect','perfect_interview'):
            self.game.save()
            self.corrupt(lambda s:s['statistics'].update({name:'broken'}))
            with self.subTest(name=name),self.assertRaises(ValueError):self.game.saves.load()
    def test_assistant_synchronizes_existing_hypothesis(self):
        for eid in ('metadata','archive'):self.game.evidence.collect(eid)
        key=self.game.evidence.propose('metadata','archive')
        self.game.evidence.evaluate(key);self.game.evidence.reject(key)
        self.game.evidence.collect('sigma');self.game.evidence.analyze()
        self.assertIn('history',self.game.state.flags)
        self.assertEqual(self.game.state.hypotheses[key]['status'],'confirmed')
    def test_out_of_time_nonterminal_save_rejected(self):
        self.corrupt(lambda s:s.update(time_remaining=0))
        with self.assertRaises(ValueError):self.game.saves.load()
    def test_main_has_freeze_support_before_parser(self):
        import ast
        tree=ast.parse((ROOT/'main.py').read_text(encoding='utf-8-sig'))
        guarded=[n for n in tree.body if isinstance(n,ast.If)]
        calls=[n.func.attr if isinstance(n.func,ast.Attribute) else getattr(n.func,'id','') for n in ast.walk(guarded[-1]) if isinstance(n,ast.Call)]
        self.assertIn('freeze_support',calls)
        self.assertLess(calls.index('freeze_support'),calls.index('main'))

if __name__=='__main__':unittest.main()
