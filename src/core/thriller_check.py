"""Prepared runtime fixture; drives real episode UI callbacks without devices."""
def verify(game):
    import pygame
    from src.scenes.thriller import start_episode,HideScene,ChaseScene,BranchRoom,finish_branch
    from src.scenes.exploration import Exploration
    from src.core.config import data
    game.new_game(prologue=False);game.access.unlock();game.accept_case()
    for eid in game.catalog:
        if eid not in ('warehouse_record','captor_ledger'):game.evidence.collect(eid)
    game.evidence.analyze();game.state.location='port';game.state.current_day=3;game.state.position=game.worlds['port']['spawn'][:]
    old_motion=game.settings.reduced_motion;game.settings.reduced_motion=True
    try:
        game.scenes.replace(Exploration(game));assert start_episode(game)
        game.scenes.current.interact('closet');hide=game.scenes.current;assert isinstance(hide,HideScene)
        hide.start(set());hide.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE))
        for _ in range(151):
            if hide.stage=='finished':break
            hide.update(.1)
        room=game.scenes.current;assert isinstance(room,BranchRoom) and room.phase=='quiet'
        room.interact('record');room.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_t));room.interact('pursue')
        chase=game.scenes.current;assert isinstance(chase,ChaseScene)
        for step in data('chase'):
            key=pygame.K_d if step['type']=='direction' else {'space':pygame.K_SPACE,'e':pygame.K_e,'shift':pygame.K_LSHIFT,'f':pygame.K_f}[step['key']]
            for _ in range(step.get('count',1)):
                chase.event(pygame.event.Event(pygame.KEYDOWN,key=key))
                if step['type']=='hold':
                    for _ in range(10):chase.update(.1)
                chase.event(pygame.event.Event(pygame.KEYUP,key=key))
            if not chase.cooldown:chase.update(.01)
            chase.draw(game.screen);chase.update(1.)
        room=game.scenes.current;assert isinstance(room,BranchRoom) and room.phase=='street'
        room.interact('signal');room.interact('rescue');game.backup_case();game.state.campaign['weir_confronted']=True
        assert finish_branch(game,'secret');assert game.load();assert game.state.ending=='secret'
        game.scenes.current.draw(game.screen)
        return True
    finally:game.settings.reduced_motion=old_motion
