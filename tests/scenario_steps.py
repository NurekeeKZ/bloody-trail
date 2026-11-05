"""Actual scene actions for the expanded campaign (explicit solutions, no rewards injected)."""
from src.scenes.investigation import Investigation,ObjectInspection
from src.scenes.puzzles import PuzzleScene
from src.scenes.overlays import Dialogue
from src.scenes.evidence_board import Board

def solve_location(game,location):
    room=Investigation(game,location)
    if location=='archive':
        d=Dialogue(game,'archivist');d.choose(game.dialogues.conversations['archivist']['choices'][0])
    if location=='apartment':
        for name in ('rug','book'):
            spot=next(s for s in room.content['hotspots'] if s['id']==name)
            detail=ObjectInspection(game,room,spot);detail.execute(detail.actions[0])
    keys={'apartment':['computer','safe','photos'],'archive':['fragments','cell'],'helios':['door']}.get(location,[])
    for key in keys:
        panel=PuzzleScene(game,key);panel.input=panel.puzzle['answer'];panel.submit()
        assert key in game.state.discoveries['solved'],panel.message

def deduce(game):
    for rule in game.rules:
        if set(rule['requires']).issubset(game.state.evidence_ids) and rule['id'] not in game.state.flags:
            board=Board(game)
            for eid in rule['pair']:board.select(eid)
            board.propose();board.confirm()
