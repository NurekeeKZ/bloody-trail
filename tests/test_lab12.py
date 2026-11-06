import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from array import array
import pygame
from src.core.config import ROOT
from src.core.game import Game
from src.ai.devices import SensorSession, audio_worker
from src.ai.signals import CalmTrial, SilenceTrial, FaceProcessor, pcm_level
from src.scenes.overlays import Assistant, Inventory
from src.scenes.sensors import GuardDialogue, SensorChallenge, SensorConsent


class FakeSession:
    def __init__(self, events=()):
        self.events = list(events)
        self.active = True
        self.closed = False

    def poll(self):
        events, self.events = self.events, []
        return events

    def close(self):
        self.closed, self.active = True, False


class Lab12Tests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / 'tests')
        self.game = Game(storage_dir=Path(self.folder.name))
        self.game.new_game(prologue=False)

    def tearDown(self):
        self.game.scenes.close()
        pygame.quit()
        self.folder.cleanup()

    def test_t_opens_assistant_without_opening_devices(self):
        with patch.object(SensorSession, 'start') as start:
            self.game.scenes.current.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_t))
            self.assertIsInstance(self.game.scenes.current, Assistant)
            self.assertFalse(start.called)

    def test_consent_decline_and_accept_order(self):
        assistant = Assistant(self.game)
        self.game.scenes.push(assistant)
        with patch.object(SensorSession, 'start') as start:
            assistant.request_voice()
            self.assertIsInstance(self.game.scenes.current, SensorConsent)
            self.game.scenes.pop()
            start.assert_not_called()
            assistant.request_voice()
            self.game.scenes.current.activate(1)
            self.assertIs(self.game.scenes.current, assistant)
            self.assertTrue(start.call_args.kwargs['consent'])

    def test_voice_output_dispatch_and_context(self):
        assistant = Assistant(self.game)
        self.game.scenes.push(assistant)
        assistant.execute('testimony')
        self.assertIn('ещё не записаны', assistant.response)
        self.game.evidence.collect('anna')
        assistant.execute('testimony')
        self.assertIn('Аружан:', assistant.response)
        assistant.voice = FakeSession([{'type': 'text', 'text': 'покажи улики'}])
        session = assistant.voice
        assistant.update(.1)
        self.assertIsInstance(self.game.scenes.current, Inventory)
        self.assertTrue(session.closed)

    def test_unknown_voice_and_error_never_mutate_game(self):
        assistant = Assistant(self.game)
        before = self.game.state.to_dict()
        assistant.voice = FakeSession([{'type': 'text', 'text': '[unk]'}])
        assistant.update(.1)
        self.assertIn('не распознана', assistant.response)
        assistant.voice = FakeSession([{'type': 'error', 'message': 'no device'}])
        assistant.update(.1)
        self.assertIn('Доступны текст', assistant.response)
        self.assertEqual(before, self.game.state.to_dict())

    def test_scene_pop_replace_and_focus_cover_release_sensor(self):
        for operation in ('pop', 'replace', 'push'):
            assistant = Assistant(self.game)
            self.game.scenes.push(assistant)
            assistant.voice = FakeSession()
            sensor = assistant.voice
            if operation == 'pop':
                self.game.scenes.pop()
            elif operation == 'replace':
                self.game.to_menu()
            else:
                self.game.scenes.push(Inventory(self.game))
            self.assertTrue(sensor.closed)

    def test_rms_and_silence_threshold_affect_stealth(self):
        self.assertEqual(pcm_level(bytes(320)), -90)
        loud = pcm_level(array('h', [16000] * 160).tobytes())
        self.assertGreater(loud, -10)
        silent, noisy = SilenceTrial(), SilenceTrial()
        for _ in range(120):
            quiet_result = silent.step(.1, -60)
        self.assertTrue(quiet_result)
        result = None
        for _ in range(30):
            if result is None:
                result = noisy.step(.1, loud)
        self.assertFalse(result)

    def test_calm_missing_face_or_motion_fails(self):
        for present, reliable, motion, expected in [(True, True, 0, True), (False, False, 0, False), (True, True, 3, False)]:
            trial = CalmTrial()
            for _ in range(120):
                result = trial.step(.1, present, reliable, motion)
            self.assertEqual(result, expected)

    def test_camera_samples_change_guard_dialogue_not_evidence(self):
        self.game.state.location = 'metro'
        scene = SensorChallenge(self.game, 'calm')
        self.game.scenes.push(scene)
        scene.reset_trial()
        scene.mode = 'sensor'
        scene.session = FakeSession()
        for _ in range(121):
            scene.session.events = [{'type': 'sample', 'dt': .1, 'at': time.monotonic(),
                                     'present': True, 'reliable': True, 'motion': .01}]
            scene.update(.1)
        self.assertEqual(self.game.state.statistics['guard_shortcut'], 1)
        self.assertEqual(self.game.state.evidence_ids, [])
        guard = GuardDialogue(self.game)
        self.assertTrue(any(b[0] == 'Пройти к журналу' for b in guard.buttons))
        guard.answer(True)
        self.assertIn('transit', self.game.state.evidence_ids)
        self.assertEqual(self.game.saves.load().statistics['guard_shortcut'], 1)

    def test_manual_modes_have_same_success_and_no_hardware(self):
        for kind, flag in [('calm', 'guard_shortcut'), ('silence', 'stealth_quiet')]:
            scene = SensorChallenge(self.game, kind)
            with patch.object(SensorSession, 'start') as start:
                scene.start_manual()
                for _ in range(121):
                    scene.pulse()
                    scene.update(.1)
                start.assert_not_called()
            self.assertEqual(self.game.state.statistics[flag], 1)

    def test_failed_sensor_retains_long_dialogue_route(self):
        self.game.state.location = 'metro'
        scene = SensorChallenge(self.game, 'calm')
        scene.finish(False)
        guard = GuardDialogue(self.game)
        guard.answer(False)
        self.assertNotIn('transit', self.game.state.evidence_ids)
        guard.answer(False)
        self.assertIn('transit', self.game.state.evidence_ids)
        score = self.game.evidence.score
        guard.answer(False)
        self.assertEqual(self.game.evidence.score, score)

    def test_absent_device_error_cancels_without_penalty(self):
        scene = SensorChallenge(self.game, 'calm')
        scene.mode = 'sensor'
        scene.reset_trial()
        scene.session = FakeSession([{'type': 'error', 'message': 'camera busy'}])
        before = self.game.state.to_dict()
        scene.update(.1)
        self.assertEqual(scene.mode, '')
        self.assertIn('кнопочный', scene.message)
        self.assertEqual(before, self.game.state.to_dict())

    def test_session_requires_consent_without_spawning(self):
        session = SensorSession()
        with self.assertRaises(PermissionError):
            session.start('camera')
        self.assertIsNone(session.process)

    def test_optional_dependencies_not_required_for_game_startup(self):
        import builtins
        original = builtins.__import__
        def blocked(name, *args, **kwargs):
            if name.split('.')[0] in ('vosk', 'sounddevice', 'cv2', 'numpy'):
                raise ImportError('optional package deliberately absent')
            return original(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=blocked):
            self.game.new_game(prologue=False)
            Assistant(self.game)
            SensorChallenge(self.game, 'calm').start_manual()

    def test_opencv_real_blank_frame_processing(self):
        try:
            import numpy as np
            import cv2
        except ImportError:
            self.skipTest('optional OpenCV absent')
        processor = FaceProcessor()
        for brightness in (0, 80, 255):
            result = processor.process(np.full((480, 640, 3), brightness, dtype=np.uint8), .1)
            self.assertFalse(result['present'])

    def test_detected_eye_centers_measure_translation(self):
        try:
            import numpy as np
            import cv2
        except ImportError:
            self.skipTest('optional OpenCV absent')
        from unittest.mock import Mock
        processor = FaceProcessor()
        # Synthetic detector rectangles isolate the movement calculation; NOT CV accuracy.
        processor.face = Mock()
        processor.eyes = Mock()
        processor.face.detectMultiScale.return_value = [(100, 100, 200, 200)]
        processor.eyes.detectMultiScale.return_value = [(25, 40, 30, 20), (125, 40, 30, 20)]
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.assertFalse(processor.process(frame, .1)['reliable'])
        self.assertEqual(processor.process(frame, .1)['motion'], 0)
        processor.face.detectMultiScale.return_value = [(120, 100, 200, 200)]
        moved = processor.process(frame, .1)
        self.assertTrue(moved['present'])
        self.assertTrue(moved['reliable'])
        self.assertAlmostEqual(moved['motion'], 1.0)

    def test_face_motion_falls_back_to_face_center_without_eyes(self):
        try:
            import numpy as np
            import cv2
        except ImportError:
            self.skipTest('optional OpenCV absent')
        from unittest.mock import Mock
        processor = FaceProcessor(emotion_model=None)
        processor.face = Mock()
        processor.eyes = Mock()
        processor.face.detectMultiScale.return_value = [(100, 100, 200, 200)]
        processor.eyes.detectMultiScale.return_value = []
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.assertFalse(processor.process(frame, .1)['reliable'])
        still = processor.process(frame, .1)
        self.assertTrue(still['reliable'])
        self.assertEqual(still['motion'], 0)
        processor.face.detectMultiScale.return_value = [(120, 100, 200, 200)]
        self.assertAlmostEqual(processor.process(frame, .1)['motion'], 1.0)

    def test_composure_signal_and_calm_trial(self):
        from src.ai.signals import composure
        self.assertEqual(composure({}), (True, None))
        self.assertEqual(composure({'neutral': .7, 'sadness': .2, 'happiness': .1}), (True, 'neutral'))
        self.assertEqual(composure({'neutral': .3, 'sadness': .7}), (True, 'sadness'))
        self.assertEqual(composure({'neutral': .2, 'happiness': .8}), (False, 'happiness'))
        trial = CalmTrial()
        result = None
        while result is None:
            result = trial.step(.1, True, True, 0, composed=False)
        self.assertFalse(result)

    def test_emotion_model_runs_on_face_crop(self):
        try:
            import numpy as np
            import cv2
        except ImportError:
            self.skipTest('optional OpenCV absent')
        processor = FaceProcessor()
        if processor.emotion_net is None:
            self.skipTest('emotion model absent')
        scores = processor.expression(np.full((480, 640), 128, dtype=np.uint8), (100, 100, 200, 200))
        self.assertEqual(len(scores), 8)
        self.assertAlmostEqual(sum(scores.values()), 1.0, places=2)

    def test_missing_model_child_reports_error_and_releases(self):
        # A missing model is checked before any stream opens; no hardware capture.
        session = SensorSession()
        try:
            session.start('voice', consent=True, model=str(ROOT / 'does-not-exist'), phrases=['покажи улики'])
            deadline = time.monotonic() + 15
            events = []
            while time.monotonic() < deadline:
                events.extend(session.poll())
                if any(e['type'] == 'error' for e in events):
                    break
                time.sleep(.05)
            self.assertTrue(any(e['type'] == 'error' for e in events), events)
            self.assertFalse(any(e['type'] == 'active' for e in events))
        finally:
            session.close()
        self.assertIsNone(session.process)


if __name__ == '__main__':
    unittest.main()
