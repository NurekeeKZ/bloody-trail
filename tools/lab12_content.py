"""Enrich existing game data; no replacement of maps or story architecture."""
import json
from pathlib import Path


def upgrade():
    folder = Path(__file__).resolve().parents[1] / 'src/data'
    path = folder / 'worlds.json'
    worlds = json.loads(path.read_text(encoding='utf-8'))
    objects = worlds['metro']['objects']
    if not any(o['id'] == 'guard' for o in objects):
        objects.append({'id': 'guard', 'name': 'Охранник метро', 'kind': 'dialogue',
                        'dialogue': 'guard', 'rect': [1280, 420, 28, 24]})
    path.write_text(json.dumps(worlds, ensure_ascii=False, indent=2), encoding='utf-8')
    # The journal hotspot offers the same conversation rather than bypassing the guard.
    path = folder / 'investigations.json'
    rooms = json.loads(path.read_text(encoding='utf-8'))
    spot = next(s for s in rooms['metro']['hotspots'] if s.get('evidence') == 'transit')
    spot['description'] = 'Журнал находится у охранника. Получите разрешение через разговор, спокойствие или тихий подход.'
    spot['actions'] = [{'id': 'guard', 'label': 'Поговорить с охранником', 'type': 'guard'}]
    path.write_text(json.dumps(rooms, ensure_ascii=False, indent=2), encoding='utf-8')
    from beta_content import upgrade as upgrade_beta
    upgrade_beta()


if __name__ == '__main__':
    upgrade()
