import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from array import array
import pygame
from src.core.config import ROOT
from src.core.game import Game
from src.scenes.prologue import Prologue,PresentBriefing,Flashback
from src.scenes.exploration import Exploration
from src.scenes.overlays import Assistant
from src.scenes.audio_settings import AudioDevices,MicrophoneTest
from src.ai.audio_input import microphones,resolve_input,supported_rate,apply_gain
from src.ai.devices import SensorSession,audio_worker
from src.systems.settings import SettingsManager

class PrologueAudioTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=ROOT/'tests');self.game=Game(storage_dir=Path(self.temp.name))
 def tearDown(self):
  self.game.scenes.close();owner=SensorSession._capture_owner
  if owner:owner.close()
  pygame.quit();self.temp.cleanup()
 def test_menu_starts_prologue_and_full_playthrough(self):
  self.game.scenes.current.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE));self.game.scenes.current.new()
  p=self.game.scenes.current;self.assertIsInstance(p,Prologue)
  for _ in range(len(p.steps)):p.writer.finish();p.advance();p.update(.4)
  self.assertIsInstance(self.game.scenes.current,PresentBriefing)
  self.game.update(.1);self.assertTrue(self.game.audio.duck)
  self.assertTrue(self.game.state.narrative['prologue_complete'])
  self.assertIn('EVIDENCE_BLOOD_MARK_2020',self.game.state.evidence_ids)
  self.game.scenes.current.begin();self.assertIsInstance(self.game.scenes.current,Exploration)
 def test_skip_confirmation_and_loading_never_replays(self):
  self.game.new_game();p=self.game.scenes.current
  p.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE))
  self.assertFalse(self.game.state.narrative['prologue_complete']);p.skip()
  self.assertTrue(self.game.state.narrative['prologue_complete']);self.game.save();self.assertTrue(self.game.load())
  self.assertIsInstance(self.game.scenes.current,Exploration)
 def test_load_interrupted_prologue_is_safe(self):
  self.game.new_game();self.assertTrue(self.game.load());self.assertIsInstance(self.game.scenes.current,Exploration)
  self.assertIn('EVIDENCE_BLOOD_MARK_2020',self.game.state.evidence_ids)
 def test_replay_is_read_only(self):
  self.game.new_game(prologue=False);before=self.game.state.to_dict()
  p=Prologue(self.game,replay=True);self.game.scenes.push(p);p.finish()
  self.assertEqual(before,self.game.state.to_dict())
 def test_flashback_once_and_independent_confirmation(self):
  self.game.new_game();self.game.complete_prologue();self.game.scenes.current.choose('photo')
  self.assertIsInstance(self.game.scenes.current,Flashback)
  self.game.scenes.current.finish();self.game.evidence.collect('photo');self.assertIsInstance(self.game.scenes.current,PresentBriefing)
  pair=('EVIDENCE_BLOOD_MARK_2020','EVIDENCE_BLOOD_MARK_2035');key=self.game.evidence.propose(*pair)
  self.assertIn('могут быть связаны',self.game.state.hypotheses[key]['reason'])
  self.game.evidence.evaluate(key);self.assertEqual(self.game.state.hypotheses[key]['status'],'pending')
  self.game.evidence.collect('archive');self.game.evidence.evaluate(key)
  self.assertEqual(self.game.state.hypotheses[key]['status'],'confirmed');self.assertTrue(self.game.state.narrative['journal'])
  self.assertFalse(self.game.evidence.can_finalize());self.game.save();self.assertTrue(self.game.load())
 def test_settings_channels_gain_speed_persist(self):
  for k,v in [('rain_volume',12),('music_volume',33),('environment_volume',44),('dialogue_volume',55),('effects_volume',66),('microphone_gain',175),('microphone_device','real-key'),('output_device','real-output'),('text_speed',80)]:self.assertTrue(self.game.set_setting(k,v))
  s=SettingsManager(self.game.preferences.path).value
  self.assertEqual(s.rain_volume,12);self.assertEqual(s.microphone_gain,175);self.assertEqual(s.text_speed,80);self.assertEqual(s.output_device,'real-output')
 def test_old_settings_and_v5_save_migrate(self):
  self.game.preferences.path.write_text('{"volume":40}',encoding='utf-8')
  self.assertEqual(SettingsManager(self.game.preferences.path).value.rain_volume,40)
  self.game.new_game(prologue=False);payload=json.loads(self.game.saves.path.read_text());payload['version']=5;payload['state'].pop('narrative');self.game.saves.path.write_text(json.dumps(payload))
  self.assertTrue(self.game.load());self.assertIsInstance(self.game.scenes.current,Exploration)
 def test_rain_default_reduced_sixty_percent_duck_and_no_stack(self):
  a=self.game.audio
  for _ in range(200):a.ambience('rain',.05)
  self.assertAlmostEqual(a.levels[0],a.volume*.28*.4,places=4)
  sound=pygame.mixer.Channel(0).get_sound()
  a.ambience('rain',.05);self.assertIs(pygame.mixer.Channel(0).get_sound(),sound)
  normal=a.levels[0]
  for _ in range(60):a.ambience('rain',.05,duck=True)
  self.assertLess(a.levels[0],normal*.31)
  for _ in range(60):a.ambience('menu',.05)
  self.assertFalse(pygame.mixer.Channel(0).get_busy())
 def test_output_failure_recovers_default(self):
  with patch('pygame.mixer.init',side_effect=[pygame.error('disconnected'),None]):
   self.assertFalse(self.game.audio.switch_output('missing'))
  self.assertIn('системный',self.game.audio.error)
 def test_zero_one_multiple_and_unplugged_microphones(self):
  sd=Mock();sd.query_hostapis.return_value=[{'name':'WASAPI'}]
  sd.query_devices.return_value=[];self.assertEqual(microphones(sd),[])
  dev={'name':'USB Microphone','max_input_channels':1,'hostapi':0}
  sd.query_devices.return_value=[dev];rows=microphones(sd);self.assertEqual(resolve_input(sd,rows[0]['key'])[0],0)
  sd.query_devices.return_value=[dev,dict(dev,name='Headset')];self.assertEqual(len(microphones(sd)),2)
  self.assertEqual(resolve_input(sd,'removed')[0],None);self.assertTrue(resolve_input(sd,'removed')[1])
 def test_native_rate_mono_fallback_and_gain_clamp(self):
  sd=Mock();sd.query_devices.return_value={'default_samplerate':48000};sd.check_input_settings.side_effect=[RuntimeError('unsupported'),None]
  self.assertEqual(supported_rate(sd,2),16000)
  self.assertEqual(sd.check_input_settings.call_args.kwargs['channels'],1)
  self.assertEqual(array('h',apply_gain(array('h',[20000,-20000]).tobytes(),200)).tolist(),[32767,-32768])
 def test_fast_clicks_do_not_spawn_and_owner_released(self):
  session=SensorSession();session.process=Mock();session.process.is_alive.return_value=True
  with patch('src.ai.devices.mp.get_context') as spawn:
   session.start('voice',consent=True);spawn.assert_not_called()
  session.process=None
 def test_recognition_repeat_scene_exit_errors_and_silence(self):
  a=Assistant(self.game)
  fake=Mock();fake.poll.return_value=[{'type':'active'},{'type':'sample','db':-20},{'type':'text','text':''}];a.voice=fake
  a.update(.1);self.assertIn('Не удалось распознать',a.voice_status);fake.close.assert_called()
  fake.poll.return_value=[{'type':'error','message':'device unplugged'}];a.update(.1);self.assertEqual(a.voice_status,'Устройство недоступно')
  with patch.object(fake,'start') as start:
   a.start_voice();a.on_cover();a.start_voice();self.assertEqual(start.call_count,2)
  with patch.object(fake,'start',side_effect=PermissionError('Windows access denied')):
   a.start_voice();self.assertEqual(a.voice_status,'Устройство недоступно')
  before=self.game.state.to_dict();self.assertIsNone(self.game.command_router.resolve('абракадабра',voice=True));self.assertEqual(before,self.game.state.to_dict())
 def test_missing_model_worker_never_queries_or_captures(self):
  out=Mock();stop=Mock();stop.is_set.return_value=False
  with patch.dict('sys.modules',{'sounddevice':Mock()}) as modules:
   audio_worker(out,stop,{'mode':'voice','model':'missing'})
   modules['sounddevice'].RawInputStream.assert_not_called()
  self.assertTrue(any(c.args[0]['type']=='error' for c in out.put_nowait.call_args_list))
 def test_microphone_test_no_game_action(self):
  scene=MicrophoneTest(self.game);before=self.game.state.to_dict();scene.execute('analyze');self.assertEqual(before,self.game.state.to_dict())
 def test_pcm_worker_selected_device_native_rate_and_repeat(self):
  from types import SimpleNamespace
  sd=Mock();dev={'name':'Test microphone','max_input_channels':1,'hostapi':0,'default_samplerate':48000}
  sd.query_devices.side_effect=lambda *args:[dev] if not args else dev
  sd.query_hostapis.return_value=[{'name':'Test API'}]
  raw_kwargs=[]
  class Stream:
   def __init__(self,**kwargs):self.kwargs=kwargs;raw_kwargs.append(kwargs)
   def __enter__(self):self.kwargs['callback'](bytes(9600),4800,None,None);return self
   def __exit__(self,*args):return False
  sd.RawInputStream.side_effect=Stream
  recognizer=Mock();recognizer.AcceptWaveform.return_value=True;recognizer.Result.return_value='{"text":"покажи улики"}'
  vosk=SimpleNamespace(Model=Mock(),KaldiRecognizer=Mock(return_value=recognizer),SetLogLevel=Mock())
  model_path=Path(self.temp.name)/'model';(model_path/'am').mkdir(parents=True);(model_path/'am/final.mdl').write_bytes(b'mock')
  for _ in range(2):
   out=Mock();stop=Mock();stop.is_set.return_value=False
   with patch.dict('sys.modules',{'sounddevice':sd,'vosk':vosk}):
    audio_worker(out,stop,{'mode':'voice','model':str(model_path),'phrases':['покажи улики'],'device_key':'Test API | Test microphone | 0','gain':100})
   self.assertTrue(any(c.args[0].get('text')=='покажи улики' for c in out.put_nowait.call_args_list))
  self.assertEqual(raw_kwargs[0]['device'],0);self.assertEqual(raw_kwargs[0]['samplerate'],48000)
  self.assertEqual(raw_kwargs[0]['channels'],1);self.assertEqual(raw_kwargs[0]['dtype'],'int16')
  self.assertEqual(vosk.KaldiRecognizer.call_args.args[1],48000)
 def test_two_sessions_release_previous_capture(self):
  p1=Mock();p2=Mock();p1.pid=p2.pid=1;p1.is_alive.return_value=False;p2.is_alive.return_value=False
  ctx=Mock();ctx.Process.side_effect=[p1,p2]
  with patch('src.ai.devices.mp.get_context',return_value=ctx):
   a=SensorSession();b=SensorSession();a.start('voice',consent=True);b.start('noise',consent=True)
   self.assertIsNone(a.process);p1.close.assert_called_once();self.assertIs(SensorSession._capture_owner,b);b.close()
 def test_old_player_can_recall_without_restarting_story(self):
  self.game.new_game(prologue=False);self.game.evidence.collect('photo')
  self.assertTrue(self.game.recall_blood_mark());self.game.scenes.current.finish()
  self.assertFalse(self.game.recall_blood_mark())
  self.assertIn('EVIDENCE_BLOOD_MARK_2035',self.game.state.evidence_ids)
 def test_mark_identical_in_both_year_photographs(self):
  a=pygame.image.load(str(ROOT/'assets/evidence/EVIDENCE_BLOOD_MARK_2020.png'))
  b=pygame.image.load(str(ROOT/'assets/evidence/EVIDENCE_BLOOD_MARK_2035.png'))
  rect=pygame.Rect(145,42,180,180)
  self.assertEqual(pygame.image.tostring(a.subsurface(rect),'RGB'),pygame.image.tostring(b.subsurface(rect),'RGB'))
 def test_cinematic_and_audio_ui_render(self):
  folder=ROOT/'docs/screenshots';p=Prologue(self.game)
  for i in (0,4,8,10,12):
   p.index=i;p.enter();p.update(1);p.draw(self.game.screen);pygame.image.save(self.game.screen,str(folder/f'prologue_{i}.png'))
  with patch.object(AudioDevices,'refresh'):
   a=AudioDevices(self.game);a.draw(self.game.screen);pygame.image.save(self.game.screen,str(folder/'audio_levels.png'))
   a.tab('devices');a.draw(self.game.screen);pygame.image.save(self.game.screen,str(folder/'audio_devices.png'));a.on_exit()

if __name__=='__main__':unittest.main()
