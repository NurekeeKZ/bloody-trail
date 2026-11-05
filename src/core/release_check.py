"""Packaged runtime check; never opens a microphone or camera."""
import json
import multiprocessing as mp
import time
from pathlib import Path


def probe_worker(output):
    try:
        import cv2
        import numpy as np
        import sounddevice
        from vosk import Model, KaldiRecognizer, SetLogLevel
        from src.core.config import ROOT
        from src.ai.signals import FaceProcessor
        SetLogLevel(-1)
        model=Model(str(ROOT/'assets/models/vosk-model-small-ru-0.22'))
        recognizer=KaldiRecognizer(model,16000)
        recognizer.AcceptWaveform(bytes(64000))
        text=json.loads(recognizer.FinalResult()).get('text','')
        face=FaceProcessor().process(np.zeros((480,640,3),dtype=np.uint8),.1)
        from src.ai.motion_detector import MotionDetector
        motion=MotionDetector().process(np.zeros((480,640,3),dtype=np.uint8),.1)
        output.put({'vosk_silence':text=='','opencv_blank':not face['present'],
                    'sounddevice_import':True,'upper_body_blank':not motion['present'],'devices_opened':False})
    except Exception as exc:
        output.put({'error':repr(exc)})


def run(destination):
    import os
    import tempfile
    import sys
    import pygame
    from src.core.game import Game
    from src.scenes.investigation import Investigation
    from src.scenes.campaign import FullVersion
    destination=Path(destination).resolve()
    destination.parent.mkdir(parents=True,exist_ok=True)
    results={'frozen':bool(getattr(sys,'frozen',False)), 'devices_opened':False}
    with tempfile.TemporaryDirectory(dir=destination.parent) as directory:
        game=Game(storage_dir=Path(directory))
        try:
            results['video_driver']=pygame.display.get_driver()
            for _ in range(12):
                pygame.event.pump();game.update(.016);game.draw(.016);pygame.display.flip()
            game.scenes.current.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE))
            from src.scenes.prologue import Prologue, Flashback
            game.new_game()
            assert isinstance(game.scenes.current,Prologue)
            game.scenes.current.update(1);game.scenes.current.draw(game.screen)
            game.complete_prologue();game.scenes.current.choose('photo')
            assert isinstance(game.scenes.current,Flashback)
            game.scenes.current.draw(game.screen);game.scenes.current.finish()
            results['prologue_flashback']=True
            from src.scenes.audio_settings import AudioDevices
            devices=AudioDevices(game)
            deadline=time.monotonic()+6
            while devices.discovery.process is not None and time.monotonic()<deadline:
                devices.update(.05);pygame.event.pump();time.sleep(.05)
            devices.tab('devices');devices.draw(game.screen)
            results['input_endpoints']=len(devices.inputs)
            results['device_status']=devices.status
            devices.on_exit()
            results['output_default_reinit']=game.audio.switch_output('')
            game.new_game(prologue=False)
            game.scenes.current.draw(game.screen)
            results['startup']=True
            game.accept_case();game.evidence.collect('photo');game.evidence.collect('metadata')
            game.evidence.analyze();game.save()
            results['save_load']=game.load()
            for location in game.worlds:
                Investigation(game,location).draw(game.screen)
            results['all_rooms']=True
            FullVersion(game).unlock()
            results['content_access']=game.access.allows(3)
            access_screen=FullVersion(game)
            access_screen.draw(game.screen)
            results['full_access_ui']=access_screen.buttons[0][0]=='Вернуться к расследованию'
            pygame.image.save(game.screen,str(destination.with_name('full_access_screen.png')))
            for eid in game.catalog:game.evidence.collect(eid)
            game.evidence.analyze();game.enter_location('port')
            game.backup_case();game.state.campaign['weir_confronted']=True
            results['ending']=game.finish_case('arrest') and game.load()
            results['journal']=len(game.journal.read())==1
            results['commands']=all(game.command_router.resolve(t,voice=True) for t in
                ['открой карту','покажи улики','анализируй запись','повтори показания','какие есть версии','сравни следы'])
            game.scenes.current.draw(game.screen)
            pygame.image.save(game.screen,str(destination.with_suffix('.png')))
            game.audio.ambience('menu');game.audio.ambience('rain');game.audio.ambience('silent')
            results['audio_initialized']=game.audio.available
            from src.core.thriller_check import verify
            results['thriller_episode']=verify(game)
            pygame.image.save(game.screen,str(destination.with_name('thriller_runtime.png')))
        finally:
            game.scenes.close();pygame.quit()
    ctx=mp.get_context('spawn');output=ctx.Queue();process=ctx.Process(target=probe_worker,args=(output,))
    process.start()
    try:
        results['sensor_runtime']=output.get(timeout=60)
    except Exception as exc:
        results['sensor_runtime']={'error':repr(exc)}
    finally:
        process.join(2)
        if process.is_alive():process.terminate();process.join(2)
        results['worker_exitcode']=process.exitcode
        process.close();output.close()
    required=('thriller_episode','full_access_ui','startup','save_load','all_rooms','content_access','ending','journal','commands','audio_initialized','prologue_flashback','output_default_reinit')
    results['passed']=all(results.get(k) is True for k in required) and results['worker_exitcode']==0 and all(
        results['sensor_runtime'].get(k) is True for k in ('vosk_silence','opencv_blank','sounddevice_import','upper_body_blank'))
    destination.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    if not results['passed']:raise SystemExit(1)
