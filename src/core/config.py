from pathlib import Path
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[2]
# Assets are read-only in a packaged installation. Progress is outside the bundle.
def default_storage():
    if getattr(sys, 'frozen', False):
        return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'BloodyTrail' / 'saves'
    return ROOT / 'saves'

SIZE = (1280, 720)
BG = (9, 15, 27)
PANEL = (17, 28, 44)
CYAN = (90, 214, 226)
RED = (218, 69, 88)
INK = (222, 229, 230)
MUTED = (136, 157, 173)


def data(name):
    return json.loads((ROOT / 'src' / 'data' / (name + '.json')).read_text(encoding='utf-8'))
