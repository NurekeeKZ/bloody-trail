import os
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import pygame,numpy as np
from src.core.config import ROOT,data
from src.core.game import Game
from src.core.state import GameState
from src.systems.stealth_system import StealthSystem,QTESystem
from src.systems.story_manager import ending_allowed,NEW_ENDINGS,validate_thriller
from src.scenes.thriller import BranchRoom,HideScene,ChaseScene,CaptiveLock,BranchFinale,BranchEnding,start_episode,show_phase,finish_branch
from src.scenes.exploration import Exploration
from src.scenes.evidence_board import Board
from src.scenes.overlays import Inventory

class StealthSignalTests(unittest.TestCase):
    def calibrated(self):
        t=StealthSystem()
        for _ in range(21):t.calibrate(.1,-65,.02)
        return t
    def test_calibration_and_quiet(self):
        t=self.calibrated();self.assertAlmostEqual(t.noise_threshold,-53)
        for _ in range(151):result=t.step(.1,-65,.02)
        self.assertEqual(result,'quiet')
    def test_short_impulse_not_detection(self):
        t=self.calibrated()
        for _ in range(2):t.step(.1,0,0)
        for _ in range(40):t.step(.1,-65,0)
        self.assertIsNone(t.cause);self.assertEqual(t.danger,0)
    def test_continuous_noise_branch(self):
        t=self.calibrated()
        for _ in range(40):t.step(.1,-5,0)
        self.assertEqual(t.cause,'noise')
    def test_movement_branch(self):
        t=self.calibrated()
        for _ in range(40):t.step(.1,-65,2.)
        self.assertEqual(t.cause,'motion')
    def test_unreliable_signal_does_not_count_or_punish(self):
        t=self.calibrated()
        for _ in range(200):t.step(.1,0,20,False)
        self.assertEqual((t.elapsed,t.danger),(0,0))
    def test_sensitivity_and_smoothing(self):
        low=StealthSystem(50,50);high=StealthSystem(150,150)
        for _ in range(21):low.calibrate(.1,-60,0);high.calibrate(.1,-60,0)
        self.assertGreater(low.noise_threshold,high.noise_threshold)
        self.assertGreater(low.motion_threshold,high.motion_threshold)
        high.step(.01,0,2);self.assertLess(high.motion,.2)
    def test_qte_repeat_and_hold_release(self):
        burst=QTESystem(data('chase')[2]);burst.key('e',True)
        for _ in range(8):burst.key('e',True)
        self.assertEqual(burst.presses,1)
        for _ in range(2):burst.key('e',False);burst.key('e',True)
        self.assertTrue(burst.result)
        hold=QTESystem(data('chase')[3]);hold.blocked={'shift'};hold.key('shift',True)
        for _ in range(6):hold.update(.1)
        self.assertEqual(hold.hold_time,0)
        hold.key('shift',False);hold.key('shift',True)
        for _ in range(10):hold.update(.1)
        self.assertTrue(hold.result)
    def test_qte_timeout_modes_and_direction(self):
        q=QTESystem(data('chase')[0]);q.update(.2)
        for _ in range(20):q.update(.2)
        self.assertFalse(q.result)
        q=QTESystem(data('chase')[0],'untimed')
        for _ in range(100):q.update(.2)
        self.assertIsNone(q.result)
        q=QTESystem(data('chase')[1]);q.key('a',True);self.assertEqual(q.route,'left')
    def test_camera_blank_and_lighting_change(self):
        from src.ai.motion_detector import MotionDetector
        d=MotionDetector();frame=np.zeros((240,320,3),dtype=np.uint8)
        self.assertFalse(d.process(frame,.1)['present'])
        rng=np.random.default_rng(17);gray=rng.integers(30,160,(240,320),dtype=np.uint8)
        d.measure(gray,(110,40,50,50),.1)
        result=d.measure(gray+40,(110,40,50,50),.1)
        self.assertTrue(result['lighting']);self.assertFalse(result['reliable'])
    def test_camera_roi_motion_and_static_background(self):
        from src.ai.motion_detector import MotionDetector
        d=MotionDetector();rng=np.random.default_rng(33);gray=rng.integers(30,180,(240,320),dtype=np.uint8)
        d.measure(gray,(110,40,50,50),.1)
        still=d.measure(gray,(110,40,50,50),.1);self.assertTrue(still['reliable']);self.assertLess(still['motion'],.03)
        moved=gray.copy();moved[45:205,65:205]=np.roll(gray[45:205,65:205],5,axis=1)
        result=d.measure(moved,(110,40,50,50),.1)
        self.assertTrue(result['reliable']);self.assertGreater(result['motion'],.3)

class ThrillerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'tests');cls.game=Game(storage_dir=Path(cls.temp.name))
        cls.game.access.unlock();cls.game.settings.reduced_motion=True
    @classmethod
    def tearDownClass(cls):cls.game.scenes.close();pygame.quit();cls.temp.cleanup()
    def setUp(self):
        g=self.game;g.new_game(prologue=False);g.accept_case()
        for eid in g.catalog:
            if eid not in ('server','warehouse_record','captor_ledger'):g.evidence.collect(eid)
        g.evidence.analyze();g.state.location='port';g.state.current_day=3;g.state.position=g.worlds['port']['spawn'][:]
        g.scenes.replace(Exploration(g))
    def room(self,phase):
        self.game.story_manager.phase(phase);show_phase(self.game,False);return self.game.scenes.current
    def hide(self,keys):
        h=self.room('hiding');h.start(set())
        for key in keys:h.event(pygame.event.Event(pygame.KEYDOWN,key=key))
        for _ in range(155):
            if h.stage=='finished':break
            h.update(.1)
        return h
    def chase(self,failures=(),direction=pygame.K_d):
        self.game.story_manager.begin_chase();show_phase(self.game,False);c=self.game.scenes.current
        for step in data('chase'):
            if step['id'] in failures:
                key=pygame.K_a if step.get('key')!='a' else pygame.K_d
                if step['type']=='direction':key=pygame.K_f
                c.event(pygame.event.Event(pygame.KEYDOWN,key=key));c.event(pygame.event.Event(pygame.KEYUP,key=key))
            elif step['type']=='hold':
                c.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_LSHIFT))
                for _ in range(10):c.update(.1)
                c.event(pygame.event.Event(pygame.KEYUP,key=pygame.K_LSHIFT))
            else:
                key=direction if step['type']=='direction' else {'space':pygame.K_SPACE,'e':pygame.K_e,'f':pygame.K_f}[step['key']]
                for _ in range(step.get('count',1)):
                    c.event(pygame.event.Event(pygame.KEYDOWN,key=key));c.event(pygame.event.Event(pygame.KEYUP,key=key))
            if not c.cooldown:c.update(.01)
            c.update(1.)
        return self.game.scenes.current
    def proof(self):
        g=self.game;g.evidence.collect('server');g.evidence.analyze();g.backup_case();g.state.campaign['weir_confronted']=True
    def test_entry_from_exploration_object(self):
        scene=self.game.scenes.current;o=next(o for o in scene.world['objects'] if o['kind']=='branch')
        scene.player.position.update(pygame.Rect(o['rect']).midbottom);scene.player.position.y+=35
        scene.interact();self.assertIsInstance(self.game.scenes.current,BranchRoom)
        self.assertEqual(self.game.state.thriller['phase'],'warehouse')
    def test_quiet_playable_branch_record_hint_secret(self):
        self.hide([pygame.K_SPACE]);self.assertEqual(self.game.state.thriller['phase'],'quiet')
        room=self.game.scenes.current;room.interact('record');room.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_t))
        self.assertTrue(self.game.state.thriller['secret_hint'])
        room.interact('pursue');self.chase()
        self.assertEqual(self.game.state.thriller['phase'],'street')
        room=self.game.scenes.current;room.interact('rescue');self.assertEqual(self.game.state.thriller['phase'],'street')
        room.interact('signal');room.interact('rescue');self.proof()
        self.assertTrue(finish_branch(self.game,'secret'));self.assertIsInstance(self.game.scenes.current,BranchEnding)
        self.assertEqual(self.game.saves.load().ending,'secret');self.assertTrue(self.game.load())
    def test_noise_to_chase(self):
        self.hide([]);self.assertTrue(self.game.state.thriller['noise_detected']);self.assertIsInstance(self.game.scenes.current,ChaseScene)
    def test_motion_injury_recovery_and_future_speed(self):
        self.hide([pygame.K_SPACE,pygame.K_d]);t=self.game.state.thriller
        self.assertTrue(t['leg_injured']);self.assertEqual(t['phase'],'recovery')
        room=self.game.scenes.current;room.update(.01);self.assertEqual(room.player.SPEED,115)
        room.interact('medkit');room.update(.01);self.assertEqual(room.player.SPEED,180);self.assertTrue(t['injured_history'])
    def test_chase_alley_is_separate_playable_route(self):
        self.chase(direction=pygame.K_a);self.assertEqual(self.game.state.thriller['phase'],'alley')
        room=self.game.scenes.current;room.interact('rescue');self.assertFalse(self.game.state.thriller['ally_saved'])
        room.interact('latch');room.interact('rescue');self.assertTrue(self.game.state.thriller['ally_saved'])
    def test_capture_escape_gameplay(self):
        self.chase(('jump','door','push'));self.assertEqual(self.game.state.thriller['phase'],'captive')
        room=self.game.scenes.current
        for item in ('wire','code','ledger','lock'):room.interact(item)
        lock=self.game.scenes.current;self.assertIsInstance(lock,CaptiveLock);lock.code='4172';lock.submit()
        self.assertEqual(self.game.state.thriller['phase'],'street');self.assertIn('captor_ledger',self.game.state.evidence_ids)
    def test_captive_ending_after_three_real_failures(self):
        self.chase(('jump','door','push'));room=self.game.scenes.current
        for key in ('wire','code','lock'):room.interact(key)
        lock=self.game.scenes.current
        for _ in range(3):lock.code='0000';lock.submit()
        self.assertEqual(self.game.state.ending,'prisoner');self.assertEqual(self.game.saves.load().ending,'prisoner')
    def test_door_failure_starts_second_hide(self):
        self.chase(('door',));self.assertEqual(self.game.state.thriller['phase'],'hiding');self.assertIsInstance(self.game.scenes.current,HideScene)
    def test_truth_ending_and_deduplicated_result(self):
        self.hide([pygame.K_SPACE]);room=self.game.scenes.current;room.interact('record');room.interact('leave');self.proof()
        self.assertTrue(finish_branch(self.game,'truth'));self.assertFalse(finish_branch(self.game,'truth'));self.assertEqual(self.game.saves.load().ending,'truth')
    def test_price_ending_requires_actual_ally_choice(self):
        room=self.chase();room.interact('abandon');self.game.scenes.current.buttons[-1][2]();self.proof()
        self.assertFalse(ending_allowed(self.game.state,self.game.evidence,'truth'))
        self.assertTrue(finish_branch(self.game,'price'));self.assertEqual(self.game.saves.load().ending,'price')
    def test_false_charge_requires_confirmation_and_missing_chain(self):
        self.game.story_manager.phase('resolved');f=BranchFinale(self.game);self.game.scenes.push(f)
        self.assertFalse(finish_branch(self.game,'false_accusation'))
        f.false_charge();self.game.scenes.current.buttons[-1][2]()
        self.assertEqual(self.game.state.ending,'false_accusation');self.assertEqual(self.game.saves.load().ending,'false_accusation')
    def test_secret_not_available_from_evidence_alone(self):
        self.proof();self.game.state.thriller['phase']='resolved'
        for eid in self.game.catalog:self.game.evidence.collect(eid)
        self.assertFalse(finish_branch(self.game,'secret'))
    def test_save_resume_captivity_and_hide(self):
        self.game.story_manager.capture();self.game.story_manager.collect('wire');self.game.save();self.assertTrue(self.game.load())
        self.assertIsInstance(self.game.scenes.current,BranchRoom);self.assertIn('wire',self.game.state.thriller['items'])
        h=self.room('hiding');h.start(set());h.held.add(pygame.K_SPACE);h.update(.1);self.game.save();self.assertTrue(self.game.load())
        restored=self.game.scenes.current;self.assertIsInstance(restored,HideScene);self.assertEqual(restored.stage,'ready');self.assertIsNone(restored.mic.process)
        self.assertAlmostEqual(self.game.state.thriller['hide_elapsed'],.1)
    def test_hardware_failure_and_revoke_do_not_change_branch(self):
        h=self.room('hiding')
        with patch.object(h.mic,'start',side_effect=OSError('no microphone')):h.start({'mic','camera'})
        self.assertEqual(h.stage,'ready');self.assertEqual(self.game.state.thriller['phase'],'hiding')
        h.start(set());h.on_cover();self.assertEqual(h.stage,'ready');self.assertIsNone(h.mic.process);self.assertIsNone(h.camera_session.process)
    def test_sensor_consent_and_both_session_routing(self):
        h=self.room('hiding')
        with patch.object(h.mic,'start') as mic,patch.object(h.camera_session,'start') as cam:
            h.consent({'mic','camera'});mic.assert_not_called();cam.assert_not_called()
            self.game.scenes.current.buttons[-1][2]();self.assertTrue(mic.call_args.kwargs['consent']);self.assertTrue(cam.call_args.kwargs['consent'])
    def test_unreliable_camera_pauses_then_offers_fallback(self):
        h=self.room('hiding');h.start(set());h.mode='sensor';h.requested={'camera'}
        for _ in range(90):h.update(.1)
        self.assertEqual(h.stage,'ready');self.assertEqual(self.game.state.thriller['hide_elapsed'],0)
    def test_save_v7_migration_and_invalid_branch(self):
        self.game.save();p=self.game.saves.path;payload=json.loads(p.read_text(encoding='utf8'));payload['version']=7;payload['state'].pop('thriller');p.write_text(json.dumps(payload),encoding='utf8')
        self.assertEqual(self.game.saves.load().thriller['phase'],'idle')
        self.game.state.thriller['phase']='nonsense';self.game.save()
        with self.assertRaises(ValueError):self.game.saves.load()
    def test_saved_final_qte_resumes_without_repeat(self):
        t=self.game.state.thriller;t['phase']='chase'
        for item in data('chase'):self.game.story_manager.qte_result(item['id'],True,'right' if item['id']=='direction' else '')
        show_phase(self.game,False);self.game.scenes.current.update(.1)
        self.assertEqual(t['phase'],'street');self.assertEqual(len(t['chase_results']),5)
    def test_new_evidence_visible_on_second_pages(self):
        for eid in self.game.catalog:self.game.evidence.collect(eid)
        b=Board(self.game);b.turn_page(1);self.assertIn('warehouse_record',b.cards)
        b.select('photo');b.select('warehouse_record');b.draw(self.game.screen)
        inv=Inventory(self.game);inv.turn_page();self.assertTrue(any('Запись встречи' in row[0] for row in inv.buttons))
    def test_room_interactions_reachable_and_collision(self):
        from collections import deque
        for phase in data('branch_rooms'):
            room=self.room(phase);start=(180,500);queue=deque([start]);visited={start}
            while queue:
                x,y=queue.popleft()
                for point in ((x+16,y),(x-16,y),(x,y+16),(x,y-16)):
                    footprint=pygame.Rect(0,0,24,18);footprint.center=point
                    if point not in visited and 40<point[0]<1240 and 150<point[1]<600 and not any(footprint.colliderect(w) for w in room.walls):
                        visited.add(point);queue.append(point)
            for obj in room.room['objects']:
                center=pygame.Vector2(pygame.Rect(obj['rect']).center)
                self.assertTrue(any(center.distance_to(p)<110 for p in visited),(phase,obj['id']))
            room.player.move((-1,0),10,room.walls,True)
            self.assertGreaterEqual(room.player.rect.left,50)

    def test_combined_sensor_samples_calibrate_and_finish(self):
        import time
        h=self.room('hiding');h.mode='sensor';h.requested={'mic','camera'};h.stage='calibration';h.trial=StealthSystem()
        with patch.object(h.mic,'poll',side_effect=lambda:[dict(type='sample',db=-65,at=time.monotonic())]),patch.object(h.camera_session,'poll',side_effect=lambda:[dict(type='sample',present=True,reliable=True,motion=.02,at=time.monotonic())]):
            for _ in range(175):
                if h.stage=='finished':break
                h.update(.1)
        self.assertTrue(self.game.state.thriller['hide_success']);self.assertEqual(self.game.state.thriller['phase'],'quiet')

    def test_new_sensor_settings_persist(self):
        from src.systems.settings import SettingsManager
        from src.scenes.stealth_settings import StealthSettings
        screen=StealthSettings(self.game);screen.change('stealth_motion_sensitivity',150);screen.change('stealth_manual',False)
        settings=SettingsManager(self.game.preferences.path).value
        self.assertEqual(settings.stealth_motion_sensitivity,150);self.assertFalse(settings.stealth_manual)
        screen.change('stealth_motion_sensitivity',100);screen.change('stealth_manual',True)

    def test_real_focus_dispatch_pauses_chase_and_closes_hide(self):
        from src.scenes.thriller import EpisodePause
        c=self.room('chase');c.physical.add('shift');c.qte.held.add('shift')
        self.game.pause_on_focus_loss();self.assertIsInstance(self.game.scenes.current,EpisodePause)
        before=c.qte.elapsed;self.game.update(.5,elapsed=5)
        self.assertEqual(c.qte.elapsed,before);self.assertFalse(c.physical)
        h=self.room('hiding');h.start(set());self.game.pause_on_focus_loss()
        self.assertEqual(h.stage,'ready');self.assertIsNone(h.mic.process)

    def test_chase_timeout_uses_real_elapsed_time(self):
        c=self.room('chase');self.game.update(.05,elapsed=4)
        self.assertEqual(self.game.state.thriller['chase_step'],1)
        self.assertFalse(self.game.state.thriller['chase_results'][0]['success'])

    def test_scene_rendering(self):
        folder=ROOT/'docs/thriller/screenshots';folder.mkdir(parents=True,exist_ok=True)
        for phase in data('branch_rooms'):
            room=self.room(phase);room.draw(self.game.screen);pygame.image.save(self.game.screen,str(folder/(phase+'.png')))
        for name,scene in [('hiding',self.room('hiding')),('chase',self.room('chase'))]+[(e,BranchEnding(self.game,e)) for e in NEW_ENDINGS]:
            if isinstance(scene,BranchEnding):scene.revealed=True
            scene.update(.01);scene.draw(self.game.screen);pygame.image.save(self.game.screen,str(folder/(name+'.png')))

if __name__=='__main__':unittest.main()
