"""Conversational N.U.R.S.: plot-safe context, reply filter, routing and offline fallback.

A fake client replaces Ollama, so the suite needs neither the model nor a network.
"""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import pygame
from src.core.config import ROOT
from src.core.game import Game
from src.ai.devices import SensorSession, audio_worker
from src.ai.nurs_brain import normalize
from src.scenes.overlays import Assistant, Inventory
from src.scenes.audio_settings import MicrophoneTest


class FakeClient:
    def __init__(self, reply='', error=None):
        self.reply, self.error, self.calls = reply, error, []

    def chat(self, messages):
        self.calls.append(messages)
        if self.error:
            raise self.error
        return self.reply


class NursConversationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / 'tests')
        self.game = Game(storage_dir=Path(self.folder.name))
        self.game.new_game(prologue=False)
        self.game.accept_case()

    def tearDown(self):
        self.game.scenes.close()
        pygame.quit()
        self.folder.cleanup()

    def ask(self, assistant, text):
        assistant.input = text
        assistant.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        if assistant.pending is not None:
            assistant.pending.thread.join(2)
        assistant.update(.1)

    def known(self):
        return normalize(self.game.nurs.facts())

    def test_context_contains_only_uncovered_facts(self):
        facts = self.game.nurs.facts()
        self.assertIn('Поручение Ермекова', facts)
        self.assertNotIn('Сарсенов', facts)
        self.assertNotIn('Сигм', facts)
        self.assertNotIn('бесплатн', facts)  # Chapter texts carry out-of-world wording.
        self.game.evidence.collect('pass')
        self.assertIn('Сарсенов', self.game.nurs.facts())

    def test_filter_rejects_meta_foreign_script_and_latin(self):
        brain, known = self.game.nurs, self.known()
        for reply in ('Я всего лишь языковая модель.', 'Это же просто игра, Никита.', 'Я работаю на Qwen.',
                      'Следы совпадают 痕迹.', 'I cannot answer that question right now.'):
            self.assertEqual(brain.clean(reply, known), '', reply)
        self.assertEqual(brain.clean('Это играет важную роль, Никита.', known), 'Это играет важную роль, Никита.')

    def test_guarded_terms_and_numbers_need_uncovered_source(self):
        brain = self.game.nurs
        self.assertEqual(brain.clean('Проверьте Сарсенова.', self.known()), '')
        self.assertEqual(brain.clean('Код сейфа — 120.', self.known()), '')
        self.game.evidence.collect('pass')
        self.assertEqual(brain.clean('Проверьте Сарсенова.', self.known()), 'Проверьте Сарсенова.')
        self.assertEqual(brain.clean('N.U.R.S.: **Срок** — три дня.', self.known()), 'Срок — три дня.')

    def test_free_question_answers_without_changing_state(self):
        self.game.nurs.client = FakeClient('Совпадение следа ещё не доказательство. Начните с терминала, Никита.')
        assistant = Assistant(self.game)
        self.game.scenes.push(assistant)
        before = self.game.state.to_dict()
        self.ask(assistant, 'Нурс, как ты думаешь, что значит этот след?')
        self.assertIn('N.U.R.S.: Совпадение следа', assistant.response)
        self.assertEqual(before, self.game.state.to_dict())
        self.assertEqual(len(self.game.nurs.history), 2)
        system = self.game.nurs.client.calls[0][0]['content']
        self.assertIn('Найденные материалы', system)

    def test_blocked_reply_is_replaced_and_not_remembered(self):
        self.game.nurs.client = FakeClient('Как нейросеть, я не могу знать убийцу.')
        assistant = Assistant(self.game)
        self.game.scenes.push(assistant)
        self.ask(assistant, 'Кто убийца?')
        self.assertIn(assistant.response.split('N.U.R.S.: ')[1], self.game.nurs.persona['fallback_replies'])
        self.assertEqual(self.game.nurs.history, [])

    def test_offline_model_falls_back_to_command_classifier(self):
        self.game.nurs.client = FakeClient(error=OSError('connection refused'))
        assistant = Assistant(self.game)
        self.game.scenes.push(assistant)
        self.ask(assistant, 'список улик')
        self.assertIsInstance(self.game.scenes.current, Inventory)
        self.game.scenes.pop()
        before = self.game.state.to_dict()
        self.ask(assistant, 'расскажи что-нибудь интересное')
        self.assertIn('Аналитический модуль недоступен', assistant.response)
        self.assertIn('Ollama', assistant.voice_status)
        self.assertEqual(before, self.game.state.to_dict())

    def test_commands_inside_short_phrase_keep_actions(self):
        router = self.game.command_router
        self.assertEqual(router.match('Нурс, покажи улики, пожалуйста'), 'evidence')
        self.assertEqual(router.match('открой карту'), 'map')
        self.assertIsNone(router.match('почему ты не хочешь сейчас покажи улики мне назвать'))
        self.assertIsNone(router.match(''))
        self.game.nurs.client = FakeClient('не должен вызываться')
        assistant = Assistant(self.game)
        self.game.scenes.push(assistant)
        self.ask(assistant, 'Нурс, покажи улики')
        self.assertIsInstance(self.game.scenes.current, Inventory)
        self.assertEqual(self.game.nurs.client.calls, [])

    def test_voice_conversation_uses_free_speech_but_microphone_test_keeps_allowlist(self):
        with patch.object(SensorSession, 'start') as start:
            Assistant(self.game).start_voice()
            self.assertIsNone(start.call_args.kwargs['phrases'])
            MicrophoneTest(self.game).start_voice()
            self.assertEqual(start.call_args.kwargs['phrases'], self.game.command_router.phrases)

    def test_recognized_speech_goes_to_model(self):
        self.game.nurs.client = FakeClient('Сначала проверьте снимок и терминал.')
        assistant = Assistant(self.game)
        self.game.scenes.push(assistant)
        assistant.voice = Mock()
        assistant.voice.poll.return_value = [{'type': 'text', 'text': 'с чего мне начать расследование'}]
        assistant.update(.1)
        assistant.voice.poll.return_value = []
        assistant.pending.thread.join(2)
        assistant.update(.1)
        self.assertIn('Сначала проверьте снимок', assistant.response)

    def test_history_resets_with_new_game(self):
        self.game.nurs.history.append({'role': 'user', 'content': 'вопрос'})
        self.game.new_game(prologue=False)
        self.assertEqual(self.game.nurs.history, [])

    def test_worker_without_phrases_builds_free_recognizer(self):
        sd = Mock()
        dev = {'name': 'Test microphone', 'max_input_channels': 1, 'hostapi': 0, 'default_samplerate': 16000}
        sd.query_devices.side_effect = lambda *args: [dev] if not args else dev
        sd.query_hostapis.return_value = [{'name': 'Test API'}]

        class Stream:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def __enter__(self):
                self.kwargs['callback'](bytes(3200), 1600, None, None)
                return self

            def __exit__(self, *args):
                return False
        sd.RawInputStream.side_effect = Stream
        recognizer = Mock()
        recognizer.AcceptWaveform.return_value = True
        recognizer.Result.return_value = json.dumps({'text': 'кто закрыл дело'}, ensure_ascii=False)
        vosk = SimpleNamespace(Model=Mock(), KaldiRecognizer=Mock(return_value=recognizer), SetLogLevel=Mock())
        model_path = Path(self.folder.name) / 'model'
        (model_path / 'am').mkdir(parents=True)
        (model_path / 'am/final.mdl').write_bytes(b'mock')
        out, stop = Mock(), Mock()
        stop.is_set.return_value = False
        with patch.dict('sys.modules', {'sounddevice': sd, 'vosk': vosk}):
            audio_worker(out, stop, {'mode': 'voice', 'model': str(model_path), 'phrases': None, 'gain': 100})
        self.assertEqual(len(vosk.KaldiRecognizer.call_args.args), 2)
        self.assertTrue(any(c.args[0].get('text') == 'кто закрыл дело' for c in out.put_nowait.call_args_list))


if __name__ == '__main__':
    unittest.main()
