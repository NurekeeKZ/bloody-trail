"""Recreate only the original temporary portrait PNGs; does not change game data."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from src.core.config import ROOT
from src.ui.portraits import PortraitManager,CHARACTERS,EMOTIONS
if __name__=='__main__':
    for key in CHARACTERS:
        folder=ROOT/'assets/portraits'/key
        folder.mkdir(parents=True,exist_ok=True)
        for emotion in EMOTIONS:
            pygame.image.save(PortraitManager.paint(key,emotion),str(folder/(emotion+'.png')))
