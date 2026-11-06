"""Engine-independent signal scoring. No devices, files or game-state mutations."""
import math
from array import array
from pathlib import Path

EMOTION_MODEL = Path(__file__).resolve().parents[2] / 'assets' / 'models' / 'emotion-ferplus-8.onnx'
EMOTIONS = ('neutral', 'happiness', 'surprise', 'sadness', 'anger', 'disgust', 'fear', 'contempt')
# A resting webcam face often reads as mildly sad, so sadness never breaks composure.
STRONG_EMOTIONS = ('happiness', 'surprise', 'anger', 'disgust', 'fear', 'contempt')
STRONG_THRESHOLD = .6


def composure(emotions):
    """Game signal from expression scores: (composed, dominant expression). Not an emotion diagnosis."""
    if not emotions:
        return True, None
    dominant = max(emotions, key=emotions.get)
    return not any(emotions.get(name, 0) >= STRONG_THRESHOLD for name in STRONG_EMOTIONS), dominant


def pcm_level(pcm):
    samples = array('h', pcm)
    rms = math.sqrt(sum(float(x) * x for x in samples) / max(1, len(samples))) / 32768
    return max(-90.0, 20 * math.log10(max(rms, 1e-9)))


class SilenceTrial:
    duration = 12.0

    def __init__(self, threshold=-32.0):
        self.threshold = threshold
        self.elapsed = self.danger = 0.0

    def step(self, dt, db):
        dt = max(0, min(dt, self.duration - self.elapsed))
        self.elapsed += dt
        self.danger = max(0, min(1, self.danger + dt * (0.45 if db > self.threshold else -0.12)))
        return self.danger < 1 if self.danger >= 1 or self.elapsed >= self.duration - 1e-8 else None


class CalmTrial:
    duration = 12.0

    def __init__(self):
        self.elapsed = self.good = 0.0

    def step(self, dt, present, reliable, motion, composed=True):
        dt = max(0, min(dt, self.duration - self.elapsed))
        self.elapsed += dt
        if present and reliable and motion <= 0.65 and composed:
            self.good += dt
        return self.good / max(self.elapsed, .001) >= .8 if self.elapsed >= self.duration - 1e-8 else None


class FaceProcessor:
    """Haar face + eye detections and optional FER+ expression scores.

    Eye centers are approximate landmarks; when the eye cascade misses (glasses, glare, dim light)
    motion falls back to the face-box center instead of dropping the frame.
    """
    def __init__(self, emotion_model=EMOTION_MODEL):
        import cv2
        self.cv = cv2
        self.face = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eyes = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye_tree_eyeglasses.xml')
        if self.face.empty() or self.eyes.empty():
            raise RuntimeError('Классификаторы лица/глаз отсутствуют')
        self.previous = None
        self.previous_center = None
        self.emotion_net = None
        if emotion_model and Path(emotion_model).is_file():
            try:
                self.emotion_net = cv2.dnn.readNetFromONNX(str(emotion_model))
            except cv2.error:
                self.emotion_net = None

    def process(self, frame, dt):
        raw = self.cv.cvtColor(frame, self.cv.COLOR_BGR2GRAY)
        gray = self.cv.equalizeHist(raw)
        faces = self.face.detectMultiScale(gray, 1.15, 5, minSize=(70, 70))
        result = {'present': len(faces) == 1, 'reliable': False, 'motion': 0.0}
        if len(faces) != 1:
            self.previous = self.previous_center = None
            return result
        x, y, w, h = map(int, faces[0])
        center = (x + w / 2, y + h / 2)
        eyes = self.eyes.detectMultiScale(gray[y:y + int(h * .65), x:x + w], 1.1, 5, minSize=(12, 12))
        points = sorted([(x + ex + ew / 2, y + ey + eh / 2) for ex, ey, ew, eh in eyes])
        eyes_found = len(points) == 2 and points[1][0] - points[0][0] >= .18 * w
        result['reliable'] = self.previous_center is not None
        if eyes_found and self.previous:
            result['motion'] = sum(math.dist(a, b) for a, b in zip(points, self.previous)) / (2 * w * max(dt, .01))
        elif self.previous_center:
            result['motion'] = math.dist(center, self.previous_center) / (w * max(dt, .01))
        self.previous = points if eyes_found else None
        self.previous_center = center
        if self.emotion_net is not None:
            result['emotions'] = self.expression(raw, (x, y, w, h))
        return result

    def expression(self, gray, box):
        """FER+ scores for one face crop: 64×64 grayscale, raw 0–255 input, softmax over 8 classes."""
        import numpy as np
        x, y, w, h = box
        crop = gray[max(0, y):y + h, max(0, x):x + w]
        blob = self.cv.dnn.blobFromImage(self.cv.resize(crop, (64, 64)).astype(np.float32))
        self.emotion_net.setInput(blob)
        scores = self.emotion_net.forward().flatten()
        scores = np.exp(scores - scores.max())
        scores /= scores.sum()
        return {name: round(float(p), 3) for name, p in zip(EMOTIONS, scores)}
