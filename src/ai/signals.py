"""Engine-independent signal scoring. No devices, files or game-state mutations."""
import math
from array import array


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

    def step(self, dt, present, reliable, motion):
        dt = max(0, min(dt, self.duration - self.elapsed))
        self.elapsed += dt
        if present and reliable and motion <= 0.65:
            self.good += dt
        return self.good / max(self.elapsed, .001) >= .8 if self.elapsed >= self.duration - 1e-8 else None


class FaceProcessor:
    """Haar face + eye detections; eye centers are approximate facial landmarks."""
    def __init__(self):
        import cv2
        self.cv = cv2
        self.face = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eyes = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye_tree_eyeglasses.xml')
        if self.face.empty() or self.eyes.empty():
            raise RuntimeError('Классификаторы лица/глаз отсутствуют')
        self.previous = None

    def process(self, frame, dt):
        gray = self.cv.equalizeHist(self.cv.cvtColor(frame, self.cv.COLOR_BGR2GRAY))
        faces = self.face.detectMultiScale(gray, 1.15, 5, minSize=(70, 70))
        result = {'present': len(faces) == 1, 'reliable': False, 'motion': 0.0}
        if len(faces) != 1:
            self.previous = None
            return result
        x, y, w, h = map(int, faces[0])
        eyes = self.eyes.detectMultiScale(gray[y:y + int(h * .65), x:x + w], 1.1, 5, minSize=(12, 12))
        points = sorted([(x + ex + ew / 2, y + ey + eh / 2) for ex, ey, ew, eh in eyes])
        if len(points) != 2 or points[1][0] - points[0][0] < .18 * w:
            self.previous = None
            return result
        result['reliable'] = self.previous is not None
        if self.previous:
            result['motion'] = sum(math.dist(a, b) for a, b in zip(points, self.previous)) / (2 * w * max(dt, .01))
        self.previous = points
        return result
