"""Bloody Trail entry point. All paths are relative to this file, not cwd."""
import argparse
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true', help='Render scenes without a display')
    parser.add_argument('--save-dir', type=Path, help='Optional isolated save directory for QA')
    parser.add_argument('--release-check', type=Path, help='Hardware-free packaged runtime verification, JSON output')
    args = parser.parse_args()
    if args.release_check:
        from src.core.release_check import run
        run(args.release_check)
        return
    if args.smoke:
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        os.environ['SDL_AUDIODRIVER'] = 'dummy'
    from src.core.game import Game
    game = Game(storage_dir=args.save_dir)
    game.smoke() if args.smoke else game.run()


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
