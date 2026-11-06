"""Live webcam check of the guard-scene signals: face presence, motion and FER+ expression.

Runs the same FaceProcessor as the game and prints the numbers the 12-second CalmTrial uses.
Frames stay in memory; nothing is written to disk. Usage:
    python tools/camera_check.py [--seconds 15] [--device 0] [--window]
"""
import argparse
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.ai.signals import FaceProcessor, composure

MOTION_LIMIT = .65
SUCCESS_SHARE = .8


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--seconds', type=float, default=15)
    parser.add_argument('--device', type=int, default=0)
    parser.add_argument('--window', action='store_true', help='show a local preview with face box and expression')
    args = parser.parse_args()

    import cv2
    processor = FaceProcessor()
    print('Модель мимики:', 'загружена' if processor.emotion_net is not None else 'НЕ НАЙДЕНА — только лицо и движение')
    capture = cv2.VideoCapture(args.device)
    if not capture.isOpened():
        sys.exit('Камера недоступна или занята')
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    frames, present, reliable, good, motions, dominants = 0, 0, 0, 0, [], Counter()
    started = last = time.monotonic()
    try:
        while time.monotonic() - started < args.seconds:
            ok, frame = capture.read()
            if not ok:
                sys.exit('Камера перестала передавать кадры')
            now = time.monotonic()
            result = processor.process(frame, now - last)
            last = now
            frames += 1
            composed, dominant = composure(result.get('emotions'))
            if result['present']:
                present += 1
                dominants[dominant or '—'] += 1
            if result['reliable']:
                reliable += 1
                motions.append(result['motion'])
            if result['present'] and result['reliable'] and result['motion'] <= MOTION_LIMIT and composed:
                good += 1
            if args.window:
                show(cv2, processor, frame, result, dominant, composed)
                if cv2.waitKey(1) & 0xFF in (27, ord('q')):
                    break
    finally:
        capture.release()
        if args.window:
            cv2.destroyAllWindows()

    elapsed = time.monotonic() - started
    share = good / max(frames, 1)
    print(f'Кадров: {frames} за {elapsed:.1f} с ({frames / max(elapsed, .001):.1f} кадр/с)')
    print(f'Лицо найдено: {present / max(frames, 1):.0%} · надёжный сигнал: {reliable / max(frames, 1):.0%}')
    if motions:
        print(f'Движение: медиана {statistics.median(motions):.2f}, максимум {max(motions):.2f} (порог {MOTION_LIMIT})')
    if dominants:
        print('Преобладающая мимика:', ', '.join(f'{name} {count / present:.0%}' for name, count in dominants.most_common()))
    print(f'Доля «спокойных» кадров: {share:.0%} (для успеха в игре нужно {SUCCESS_SHARE:.0%}) →',
          'ПРОЙДЕНО' if share >= SUCCESS_SHARE else 'НЕ ПРОЙДЕНО')


def show(cv2, processor, frame, result, dominant, composed):
    gray = cv2.equalizeHist(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
    color = (80, 210, 90) if composed and result['motion'] <= MOTION_LIMIT else (60, 60, 220)
    for x, y, w, h in processor.face.detectMultiScale(gray, 1.15, 5, minSize=(70, 70)):
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
    label = f'{dominant or "no face"}  motion {result["motion"]:.2f}'
    cv2.putText(frame, label, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, .8, color, 2)
    cv2.imshow('Bloody Trail camera check (Esc - exit)', frame)


if __name__ == '__main__':
    main()
