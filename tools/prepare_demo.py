"""Prepare explicitly labelled demo checkpoints through the existing game actions.
Run before packaging. Never touches the player's normal saves.
"""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import shutil
import tempfile
import pygame
from src.core.config import ROOT
from src.core.game import Game
from src.scenes.investigation import Investigation,ObjectInspection
from src.scenes.overlays import Dialogue
from src.scenes.qte import StoryQTE
from src.scenes.sensors import GuardDialogue


def prepare(output):
    with tempfile.TemporaryDirectory(dir=ROOT/'build') as tmp:
        game=Game(storage_dir=Path(tmp));game.new_game(prologue=False);game.accept_case()
        def snapshot(name,position):
            game.state.position=list(position)
            game.save();game.manual_save()
            target=output/'demo'/name;target.mkdir(parents=True,exist_ok=True)
            for f in Path(tmp).glob('*.json'):shutil.copy2(f,target/f.name)
        def collect(location):
            room=Investigation(game,location)
            for spot in sorted(room.content['hotspots'],key=lambda s:s.get('evidence')=='metadata'):
                detail=ObjectInspection(game,room,spot)
                for a in detail.actions:
                    if a['type']=='collect' and a['evidence'] not in game.state.evidence_ids:detail.execute(a)
            if location=='apartment':
                for key in ('rug','book'):
                    spot=next(s for s in room.content['hotspots'] if s['id']==key)
                    detail=ObjectInspection(game,room,spot);detail.execute(detail.actions[0])
            if location=='archive':
                dialogue=Dialogue(game,'archivist');dialogue.choose(dialogue.node['choices'][0])
            for key in {'apartment':['computer','safe','photos'],'archive':['fragments','cell'],'helios':['door']}.get(location,[]):
                ok,message=game.puzzles.solve(key,game.puzzles.definitions[key]['answer'])
                assert ok,message
            game.evidence.analyze()
        def travel(location):
            assert game.travel(location),location
            if isinstance(game.scenes.current,StoryQTE):
                q=game.scenes.current;q.start()
                for key in q.sequence:q.event(pygame.event.Event(pygame.KEYDOWN,key=key))
            assert game.state.location==location
        try:
            snapshot('start',(530,435))
            collect('station');travel('apartment');collect('apartment')
            game.access.unlock();travel('archive');collect('archive');travel('metro')
            snapshot('metro',(1200,440))
            dlg=Dialogue(game,'anna')
            dlg.choose(next(c for c in game.dialogues.conversations['anna']['choices'] if c.get('effect_id')=='anna_respect'))
            GuardDialogue(game).grant();travel('helios');collect('helios');travel('port');snapshot('thriller',(1150,850));collect('port')
            game.backup_case();snapshot('final',(805,470))
            for name in ('start','metro','thriller','final'):
                # Validate each fixture using the normal loader, not just JSON parsing.
                check=Game(storage_dir=output/'demo'/name)
                assert check.load(),check.notice
                check.scenes.close()
                (output/('Demo_'+name+'.cmd')).write_text('@echo off\r\n"%~dp0BloodyTrail.exe" --save-dir "%~dp0demo\\'+name+'"\r\n',encoding='ascii')
        finally:game.scenes.close();pygame.quit()
    (output/'demo/README.txt').write_text('Prepared demonstration checkpoints, not evidence of user play. Start: case already accepted; Metro/Thriller/Final: prior clues collected via game callbacks, teacher full access enabled. Copies can be changed during demonstration. Regenerate with tools/prepare_demo.py. Normal AppData saves are not touched.\n',encoding='utf-8')

if __name__=='__main__':prepare(ROOT/'dist/BloodyTrail')
