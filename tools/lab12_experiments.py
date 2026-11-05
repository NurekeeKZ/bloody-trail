"""Reproducible AI experiments. Offline mode never opens a device.
Live modes demand a typed, per-run consent and store only requested numeric/text results.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.ai.commands import CommandRouter
from src.ai.intents import IntentClassifier
from src.ai.signals import FaceProcessor
from src.ai.devices import SensorSession

PHRASES = [('Покажи улики', 'evidence'), ('Анализируй запись', 'analyze'),
           ('Повтори показания', 'testimony'), ('Какие есть версии', 'versions'), ('Сравни следы', 'analyze')]
CAMERA_CASES = ['Ровный свет, лицо прямо', 'Тусклый свет, лицо прямо', 'Контровой свет',
                'Поворот лица 30 градусов', 'Резкое перемещение', 'Лица нет в кадре']


def router():
    read = lambda name: json.loads((ROOT / 'src/data' / (name + '.json')).read_text(encoding='utf-8'))
    return CommandRouter(read('voice_commands'), IntentClassifier(read('intents')))


def save(name, value):
    folder = ROOT / 'docs/lab12'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    if path.exists() and name.startswith('live_'):
        raise FileExistsError('Существующий эксперимент не перезаписывается: ' + str(path))
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def offline():
    route = router()
    rows = []
    for i in range(20):
        phrase, expected = PHRASES[i % 5]
        text = [phrase, phrase.upper(), phrase.lower() + '.', '  ' + phrase + '  '][i // 5]
        actual = route.resolve(text, voice=True)
        rows.append({'attempt': i + 1, 'input': text, 'expected': expected, 'actual': actual, 'correct': actual == expected})
    results = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'type': 'offline, no devices',
               'text_attempts': rows, 'text_correct': sum(r['correct'] for r in rows),
               'text_accuracy': sum(r['correct'] for r in rows) / len(rows)}
    try:
        import numpy as np
        import cv2
        processor = FaceProcessor()
        results['opencv'] = cv2.__version__
        results['blank_frames'] = [{'brightness': b, **processor.process(np.full((480, 640, 3), b, dtype=np.uint8), .1)} for b in (0, 80, 255)]
    except ImportError as exc:
        results['opencv_error'] = str(exc)
    try:
        from vosk import Model, KaldiRecognizer, SetLogLevel
        SetLogLevel(-1)
        model = Model(str(ROOT / 'assets/models/vosk-model-small-ru-0.22'))
        rec = KaldiRecognizer(model, 16000, json.dumps(route.phrases + ['[unk]'], ensure_ascii=False))
        rec.AcceptWaveform(bytes(16000 * 2 * 2))
        results['vosk_synthetic_silence'] = json.loads(rec.FinalResult())
    except Exception as exc:
        results['vosk_error'] = str(exc)
    save('offline_results.json', results)
    lines = ['# Фактические offline-проверки', '', 'Это НЕ распознавание 20 произнесённых фраз: проверяется маршрутизация текста после STT.', '',
             '| № | Текст | Ожидалось | Получено | Верно |', '|---|---|---|---|---|']
    lines += [f"| {r['attempt']} | {r['input'].strip()} | {r['expected']} | {r['actual']} | {r['correct']} |" for r in rows]
    lines += ['', f"Точность маршрутизации текста: {results['text_correct']}/20 = {results['text_accuracy']:.0%}. Это не Voice Accuracy.",
              '', 'OpenCV: три одноцветных кадра, результат: ' + str(results.get('blank_frames', results.get('opencv_error'))),
              '', 'Vosk, синтетическая тишина 2 с: ' + str(results.get('vosk_synthetic_silence', results.get('vosk_error')))]
    (ROOT / 'docs/lab12/Offline_Attempts.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps(results, ensure_ascii=False))


def live(kind):
    output_name = 'live_voice_results.json' if kind == 'voice' else 'live_camera_results.json'
    if (ROOT / 'docs/lab12' / output_name).exists():
        raise FileExistsError('Сначала сохраните предыдущий отчёт под другим именем')
    print('Обработка локальная; аудио/видео не сохраняются. В отчёт попадут только распознанные команды/числа.')
    if input('Разрешить устройство на этот эксперимент? Введите YES: ') != 'YES':
        print('Отказ: устройство не открывалось.')
        return
    route, rows = router(), []
    count = 20 if kind == 'voice' else len(CAMERA_CASES)
    try:
        for i in range(count):
            label, expected = PHRASES[i % 5] if kind == 'voice' else (CAMERA_CASES[i], i != 5)
            condition = ['Тихая комната, обычная громкость', 'Тихая комната, тихая речь',
                         'Умеренный фоновый шум', 'Расстояние около 1 метра'][i // 5] if kind == 'voice' else label
            input(f'{i + 1}/{count}: {label}. Условие: {condition}. Enter — начать; Ctrl+C — остановить: ')
            session = SensorSession()
            row = {'attempt': i + 1, 'prompt': label, 'condition': condition, 'expected': expected, 'actual': None, 'errors': []}
            started = None
            samples = []
            try:
                session.start('voice' if kind == 'voice' else 'camera', consent=True,
                              model=str(ROOT / 'assets/models/vosk-model-small-ru-0.22'), phrases=route.phrases)
                timeout = time.monotonic() + 40
                done = False
                while not done and time.monotonic() < timeout:
                    for event in session.poll():
                        if event['type'] == 'active':
                            started = time.monotonic()
                            print('УСТРОЙСТВО ВКЛЮЧЕНО — говорите' if kind == 'voice' else 'КАМЕРА ВКЛЮЧЕНА — 12 секунд')
                        elif event['type'] == 'text':
                            row['recognized_text'] = event['text']
                            row['actual'] = route.resolve(event['text'], voice=True)
                            done = True
                        elif event['type'] == 'sample' and kind != 'voice':
                            samples.append({k: event[k] for k in ('present', 'reliable', 'motion')})
                        elif event['type'] == 'error':
                            row['errors'].append(event['message'])
                            done = True
                        elif event['type'] == 'stopped':
                            done = True
                    if started and kind != 'voice' and time.monotonic() - started >= 12:
                        done = True
                    time.sleep(.02)
                if not done:
                    row['errors'].append('timeout')
            except Exception as exc:
                row['errors'].append(f'{type(exc).__name__}: {exc}')
            finally:
                session.close()
                print('УСТРОЙСТВО ВЫКЛЮЧЕНО')
            if kind != 'voice':
                row['samples'] = samples
                row['actual'] = sum(s['present'] for s in samples) / len(samples) if samples else None
            else:
                row['correct'] = row['actual'] == expected
            rows.append(row)
    except KeyboardInterrupt:
        print('Эксперимент прерван; сохраняются только реально завершённые попытки.')
    result = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'attempts': rows}
    if kind == 'voice':
        result['correct'] = sum(r['correct'] for r in rows)
        result['accuracy'] = result['correct'] / len(rows) if rows else None
    save(output_name, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('offline', 'voice', 'camera'), default='offline')
    args = parser.parse_args()
    offline() if args.mode == 'offline' else live(args.mode)
