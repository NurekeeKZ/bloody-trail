"""Generate original code-native temporary art; replace PNGs without changing logic."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pygame
from src.ui.investigation_art import office, evidence_image
from src.core.config import data

pygame.init()
for directory in ('rooms', 'evidence'):
    (ROOT / 'assets' / directory).mkdir(parents=True, exist_ok=True)
pygame.image.save(office(), str(ROOT / 'assets' / 'rooms' / 'station.png'))
for eid in data('evidence'):
    pygame.image.save(evidence_image(eid), str(ROOT / 'assets' / 'evidence' / (eid + '.png')))
pygame.quit()
