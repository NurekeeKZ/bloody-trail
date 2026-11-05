"""Local demo access and result journal. No payment or network integration."""
import json
from pathlib import Path


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


class ContentAccess:
    def __init__(self, path):
        self.path = Path(path)
        self.full_version_unlocked = False
        self.error = ''
        try:
            if self.path.exists():
                data = json.loads(self.path.read_text(encoding='utf-8'))
                if type(data.get('full_version_unlocked')) is not bool:
                    raise ValueError('Некорректный флаг доступа')
                self.full_version_unlocked = data['full_version_unlocked']
        except (OSError, ValueError, TypeError, AttributeError):
            self.error = 'Файл доступа повреждён; включён безопасный режим демо.'

    def allows(self, chapter):
        return chapter == 1 or self.full_version_unlocked

    def unlock(self):
        atomic_json(self.path, {'full_version_unlocked': True})
        self.full_version_unlocked = True


class ResultJournal:
    def __init__(self, path):
        self.path = Path(path)

    def read(self):
        if not self.path.exists():
            return []
        rows = json.loads(self.path.read_text(encoding='utf-8'))
        if not isinstance(rows, list) or len(rows) > 100:
            raise ValueError('Неверная таблица результатов')
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get('run_id'), str) or not isinstance(row.get('ending'), str):
                raise ValueError('Неверная запись результата')
            for key in ('score', 'health', 'reputation', 'seconds', 'evidence'):
                if type(row.get(key)) is not int or row[key] < 0:
                    raise ValueError('Неверная статистика результата')
        return rows

    def record(self, state, score):
        rows = [r for r in self.read() if r['run_id'] != state.run_id]
        rows.append({'run_id': state.run_id, 'ending': state.ending, 'score': score,
                     'health': state.health, 'reputation': state.reputation,
                     'seconds': int(state.play_seconds), 'evidence': len(state.evidence_ids),
                     'day': state.current_day, 'time_remaining': state.time_remaining, 'trust': dict(state.trust),
                     'achievements': state.achievements[:]})
        atomic_json(self.path, rows[-100:])
