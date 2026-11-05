"""Optional local sensor workers. Never import Pygame; never record audio/video.

Workers own devices; terminating an unresponsive worker releases its OS handles.
Only text and numerical signals cross the process boundary, never camera frames.
"""
import json
import multiprocessing as mp
import queue
import time
from pathlib import Path
from src.ai.signals import pcm_level


def emit(output, event):
    try:
        output.put_nowait(event)
    except queue.Full:
        pass


def audio_worker(output, stop, options):
    try:
        if options['mode']=='voice' and not (Path(options['model'])/'am/final.mdl').exists():
            raise RuntimeError('Нет модели Vosk: установите локальную модель из assets/models/README.md')
        import sounddevice as sd
        from src.ai.audio_input import resolve_input, supported_rate, apply_gain
        device, warning = resolve_input(sd, options.get('device_key', ''))
        if warning: emit(output, {'type':'warning','message':warning})
        rate = supported_rate(sd, device)
        recognizer = None
        if options['mode'] == 'voice':
            emit(output, {'type':'status','message':'Подключение: загрузка локальной модели…'})
            from vosk import Model, KaldiRecognizer, SetLogLevel
            path = Path(options['model'])
            if not (path / 'am' / 'final.mdl').exists():
                raise RuntimeError('Нет модели Vosk: запустите tools/download_voice_model.py')
            SetLogLevel(-1)
            model = Model(str(path))
            recognizer = KaldiRecognizer(model, rate, json.dumps(options['phrases'] + ['[unk]'], ensure_ascii=False))
        if stop.is_set():
            return
        chunks = queue.Queue(maxsize=24)
        def callback(data, frames, timing, status):
            if status:
                emit(output, {'type': 'error', 'message': 'Аудиопоток: ' + str(status)})
                stop.set()
                return
            try:
                chunks.put_nowait(bytes(data))
            except queue.Full:
                emit(output, {'type': 'error', 'message': 'Аудиопоток перегружен. Повторите команду.'})
                stop.set()
        with sd.RawInputStream(samplerate=rate, blocksize=max(1, rate // 10), channels=1,
                               dtype='int16', device=device, callback=callback):
            if stop.is_set(): return
            emit(output, {'type': 'active'})
            started = last = time.monotonic()
            while not stop.is_set():
                now = time.monotonic()
                if now - started > (9 if recognizer else 30):
                    if recognizer:
                        emit(output, {'type':'status','message':'Обрабатываю…'})
                        emit(output, {'type': 'text', 'text': json.loads(recognizer.FinalResult()).get('text', '')})
                    break
                try:
                    pcm = chunks.get(timeout=.25)
                except queue.Empty:
                    if now - last > 2:
                        raise RuntimeError('Микрофон не передаёт данные')
                    continue
                last = now
                pcm = apply_gain(pcm, options.get('gain',100))
                emit(output, {'type': 'sample', 'db': pcm_level(pcm), 'dt': len(pcm) / (2 * rate), 'at': now})
                if recognizer and recognizer.AcceptWaveform(pcm):
                    text = json.loads(recognizer.Result()).get('text', '')
                    if text:
                        emit(output, {'type':'status','message':'Обрабатываю…'})
                        emit(output, {'type': 'text', 'text': text})
                        break
    except Exception as exc:
        emit(output, {'type': 'error', 'message': f'{type(exc).__name__}: {exc}'})
    finally:
        emit(output, {'type': 'stopped'})


def camera_worker(output, stop, options):
    cap = None
    try:
        import cv2
        from src.ai.signals import FaceProcessor
        if options.get('processor')=='upper_body':
            from src.ai.motion_detector import MotionDetector
            processor=MotionDetector()
        else: processor = FaceProcessor()
        cap = cv2.VideoCapture(options.get('device', 0))
        if not cap.isOpened():
            raise RuntimeError('Камера недоступна или занята')
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        emit(output, {'type': 'active'})
        last = time.monotonic()
        while not stop.is_set():
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError('Камера перестала передавать кадры')
            now = time.monotonic()
            dt = now - last
            result = processor.process(frame, dt)
            last = now
            emit(output, {'type': 'sample', 'dt': dt, 'at': now, **result})
            stop.wait(.05)
    except Exception as exc:
        emit(output, {'type': 'error', 'message': f'{type(exc).__name__}: {exc}'})
    finally:
        if cap is not None:
            cap.release()
        emit(output, {'type': 'stopped'})


def discovery_worker(output, stop, options):
    try:
        import sounddevice as sd
        from src.ai.audio_input import microphones
        emit(output, {'type':'devices','devices':microphones(sd)})
    except Exception as exc:
        emit(output, {'type':'error','message':str(exc)})
    finally: emit(output, {'type':'stopped'})


class SensorSession:
    _capture_owner = None

    def __init__(self):
        self.process = self.output = self.stop_event = None
        self.active = False
        self.started = self.last_event = 0.0

    def start(self, kind, *, consent=False, **options):
        if self.process is not None and self.process.is_alive():
            return  # Rapid repeated clicks never spawn competing workers.
        self.close()
        if not consent:
            raise PermissionError('Требуется явное согласие на эту сессию')
        if kind not in ('voice', 'noise', 'camera', 'devices'):
            raise ValueError('Неизвестный сенсор')
        if kind in ('voice','noise'):
            owner = SensorSession._capture_owner
            if owner is not None and owner is not self: owner.close()
            SensorSession._capture_owner = self
        ctx = mp.get_context('spawn')
        self.output, self.stop_event = ctx.Queue(maxsize=64), ctx.Event()
        target = discovery_worker if kind == 'devices' else camera_worker if kind == 'camera' else audio_worker
        self.process = ctx.Process(target=target, args=(self.output, self.stop_event, {'mode': kind, **options}), daemon=True)
        self.started = self.last_event = time.monotonic()
        try:
            self.process.start()
        except Exception:
            self.close()
            raise

    def poll(self):
        if self.output is None:
            return []
        events = []
        while True:
            try:
                event = self.output.get_nowait()
            except queue.Empty:
                break
            self.last_event = time.monotonic()
            if event['type'] == 'active':
                self.active = True
            if event['type'] in ('stopped', 'error'):
                self.active = False
            events.append(event)
        # A frozen driver/model cannot freeze the UI or silently keep a device open.
        if time.monotonic() - self.last_event > (3 if self.active else 25):
            events.append({'type': 'error', 'message': 'Сенсор не отвечает. Используйте ручной режим.'})
            self.close()
        elif self.process is not None and not self.process.is_alive() and not events:
            events.append({'type': 'stopped'})
            self.close()
        return events

    def close(self):
        if SensorSession._capture_owner is self: SensorSession._capture_owner = None
        if self.process is not None:
            self.stop_event.set()
            if self.process.pid is not None:
                self.process.join(.12)
                if self.process.is_alive():
                    self.process.terminate()
                    self.process.join(.12)
                self.process.close()
        if self.output is not None:
            self.output.cancel_join_thread()
            self.output.close()
        self.process = self.output = self.stop_event = None
        self.active = False
