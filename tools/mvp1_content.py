"""Idempotent MVP 1 enrichment; preserves the existing JSON-based story architecture."""
import json
from pathlib import Path


def upgrade():
    folder = Path(__file__).resolve().parents[1] / 'src' / 'data'
    def read(name):
        return json.loads((folder / (name + '.json')).read_text(encoding='utf-8'))
    def write(name, value):
        (folder / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

    worlds = read('worlds')
    next(o for o in worlds['station']['objects'] if o['id'] == 'npc')['dialogue'] = 'sokolov'
    worlds['apartment']['requires'] = ['order', 'photo', 'metadata']
    worlds['apartment']['requires_flags'] = ['initial_anomaly']
    worlds['apartment']['requires_story'] = ['case_accepted']
    # Old saves could legally reach the apartment with just the photo. Preserve that
    # location when loading; new travel always uses the stronger requirements above.
    worlds['apartment']['load_requires'] = ['photo']
    write('worlds', worlds)
    dialogues = read('dialogues')
    choices = dialogues['sokolov']['choices']
    if not any(c.get('action') == 'accept_case' for c in choices):
        choices.insert(0, {'label': 'Принять дело Нурланова', 'action': 'accept_case',
                           'reply': 'Азамат Нурланов, архивист, найден мёртвым. Поручение у тебя. '
                                    'На столе осмотри снимок и терминал: сначала фото, затем удалённые метаданные. '
                                    'Подтверди связь на доске — получишь основание выехать в квартиру.'})
    write('dialogues', dialogues)
    rooms = read('investigations')
    computer = next(s for s in rooms['station']['hotspots'] if s['id'] == 'computer')
    computer['description'] = 'Дело Азамата Нурланова. В компьютере остались запись об архивисте и следы удаления метаданных.'
    computer['actions'][0].update(label='Изучить запись Нурланова',
        text='Азамат Нурланов — архивист, найденный мёртвым. Снимок из его дела повторяет след 2020 года. '
             'Зафиксируйте фотографию на столе, затем проверьте удалённые файлы здесь.')
    write('investigations', rooms)
    from lab12_content import upgrade as upgrade_lab12
    upgrade_lab12()


if __name__ == '__main__':
    upgrade()
