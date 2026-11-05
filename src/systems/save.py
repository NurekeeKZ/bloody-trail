import json
import math
from dataclasses import fields
from src.core.state import GameState


class SaveManager:
    VERSION = 8

    def __init__(self, path, worlds, catalog, rules):
        self.path, self.worlds, self.catalog, self.rules = path, worlds, catalog, rules

    def save(self, state):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'version': self.VERSION, 'state': state.to_dict()},
                                        ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(self.path)

    def load(self):
        try:
            payload = json.loads(self.path.read_text(encoding='utf-8'))
            if payload['version'] not in (1, 2, 3, 4, 5, 6, 7, self.VERSION):
                raise ValueError('Неподдерживаемая версия сохранения')
            values = payload['state']
            if payload['version'] == 1:
                values = dict(values)
                values.setdefault('play_seconds', 0.0)
            if payload['version'] < 3:
                values = dict(values)
                values.setdefault('hypotheses', {})
            if payload['version'] < 4:
                values = dict(values)
                values.setdefault('story', {'case_accepted': 'order' in values.get('evidence_ids', []),
                                            'anomaly_announced': 'metadata' in values.get('evidence_ids', []),
                                            'qte_complete': values.get('location') != 'station',
                                            'mvp_complete': False})
            if payload['version'] < 5:
                values = dict(values)
                defaults = GameState()
                for name in ('run_id', 'time_remaining', 'visited', 'achievements', 'campaign'):
                    values.setdefault(name, getattr(defaults, name))
                if values.get('location') != 'station' and values['location'] not in values['visited']:
                    values['visited'].append(values['location'])
                if values.get('ending') in ('arrest', 'revenge', 'release'):
                    values['location'] = 'port'
                    values['campaign'].update(weir_confronted=True, backup=True)
            if payload['version'] < 6:
                values = dict(values)
                values.setdefault('narrative', GameState().narrative)
                values['narrative']['prologue_complete'] = True
            if payload['version'] < 7:
                values = dict(values)
                for name in ('companion','discoveries','intuition'):
                    values.setdefault(name, getattr(GameState(), name))
            if payload['version'] < 8:
                values=dict(values);values.setdefault('thriller',GameState().thriller)
            if set(values) != {f.name for f in fields(GameState)}:
                raise ValueError('Неполное сохранение')
            state = GameState(**values)
            from src.systems.story_manager import validate_thriller, NEW_ENDINGS, ending_allowed as branch_allowed
            validate_thriller(state.thriller,self.catalog)
            if state.thriller['ending_id'] != (state.ending if state.ending in NEW_ENDINGS else ''):
                raise ValueError('Противоречивая концовка ветки')
            if state.ending in NEW_ENDINGS:
                from src.systems.evidence import EvidenceManager
                if not branch_allowed(state,EvidenceManager(state,self.catalog,self.rules),state.ending):raise ValueError('Нет оснований для развязки')
            c=state.companion;d=state.discoveries
            if not isinstance(c,dict) or set(c)!={'mode','location','position'} or c['mode'] not in ('follow','roam','stay','come') or c['location'] not in ('',*self.worlds) or not isinstance(c['position'],list) or len(c['position'])!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in c['position']):
                raise ValueError('Неверное состояние спутника')
            if not isinstance(d,dict) or set(d)!={'revealed','solved','hints','comments'} or any(not isinstance(d[k],list) or any(not isinstance(v,str) for v in d[k]) for k in ('revealed','solved','comments')) or not isinstance(d['hints'],dict) or any(not isinstance(k,str) or type(v) is not int or not 0<=v<=3 for k,v in d['hints'].items()):
                raise ValueError('Неверное состояние головоломок')
            if type(state.intuition) not in (int,float) or not math.isfinite(state.intuition) or not 0<=state.intuition<=100:
                raise ValueError('Неверный ресурс интуиции')
            n = state.narrative
            if not isinstance(n,dict) or set(n) != set(GameState().narrative) or any(type(n[k]) is not bool for k in ('started','prologue_complete','flashback_seen')) or not isinstance(n['objective'],str) or not isinstance(n['journal'],list) or any(not isinstance(x,str) for x in n['journal']):
                raise ValueError('Неверное состояние пролога')
            if type(state.play_seconds) not in (int, float) or not math.isfinite(state.play_seconds) or state.play_seconds < 0:
                raise ValueError('Неверное время прохождения')
            if state.location not in self.worlds:
                raise ValueError('Неизвестная локация')
            if not isinstance(state.position, list) or len(state.position) != 2:
                raise ValueError('Неверная позиция')
            if any(type(v) not in (int, float) or not math.isfinite(v) for v in state.position):
                raise ValueError('Неверные координаты')
            if any(not 32 <= state.position[i] <= self.worlds[state.location]['size'][i] - 32 for i in (0, 1)):
                raise ValueError('Позиция за границами мира')
            if not isinstance(state.evidence_ids, list) or any(e not in self.catalog for e in state.evidence_ids):
                raise ValueError('Неизвестная улика')
            if len(set(state.evidence_ids)) != len(state.evidence_ids):
                raise ValueError('Повторные улики')
            for name in ('trust', 'statistics', 'evidence_records'):
                if not isinstance(getattr(state, name), dict):
                    raise ValueError('Неверная структура данных')
            if set(state.evidence_records) != set(state.evidence_ids):
                raise ValueError('Отсутствует журнал улик')
            for record in state.evidence_records.values():
                if not isinstance(record, dict) or type(record.get('verified')) is not bool:
                    raise ValueError('Неверный статус улики')
                if not isinstance(record.get('source'), str) or not record['source'].strip():
                    raise ValueError('Отсутствует источник улики')
                if type(record.get('day')) is not int or not 1 <= record['day'] <= 3 or type(record.get('slot')) is not int or not 0 <= record['slot'] <= 5:
                    raise ValueError('Неверное время обнаружения')
                record.setdefault('related', [])
                if not isinstance(record['related'], list) or any(e not in state.evidence_ids for e in record['related']):
                    raise ValueError('Неверные связанные улики')
            if not isinstance(state.flags, list) or any(f not in {r['id'] for r in self.rules} for f in state.flags):
                raise ValueError('Неизвестный вывод')
            for rule in self.rules:
                if rule['id'] in state.flags and not set(rule['requires']).issubset(state.evidence_ids):
                    raise ValueError('Вывод без подтверждающих улик')
                if payload['version'] < 3 and rule['id'] in state.flags:
                    for eid in rule['requires']:
                        record = state.evidence_records[eid]
                        record['related'] = sorted(set(record['related']) | (set(rule['requires']) - {eid}))
            if not isinstance(state.hypotheses, dict) or len(state.hypotheses) > len(self.catalog) ** 2:
                raise ValueError('Неверный журнал гипотез')
            for key, hypothesis in state.hypotheses.items():
                pair = hypothesis['evidence']
                if not isinstance(pair, list) or len(pair) != 2 or any(e not in state.evidence_ids for e in pair) or pair[0] == pair[1] or key != '|'.join(sorted(pair)):
                    raise ValueError('Неверная связь')
                rule = next((r for r in self.rules if sorted(r.get('pair', [])) == sorted(pair)), None)
                if hypothesis['rule'] != (rule['id'] if rule else None) or hypothesis['status'] not in ('pending', 'confirmed', 'rejected') or not isinstance(hypothesis['reason'], str):
                    raise ValueError('Неверная гипотеза')
                if hypothesis['status'] == 'confirmed' and (rule is None or rule['id'] not in state.flags or not set(rule['requires']).issubset(state.evidence_ids)):
                    raise ValueError('Ложное подтверждение гипотезы')
            for name in ('health', 'reputation', 'current_day', 'time_slot'):
                if type(getattr(state, name)) is not int:
                    raise ValueError('Неверный показатель')
            if not 1 <= state.current_day <= 3 or not 0 <= state.time_slot <= 5:
                raise ValueError('Неверное время')
            if not 0 <= state.health <= 100 or not 0 <= state.reputation <= 100:
                raise ValueError('Неверное состояние')
            if not isinstance(state.story, dict) or set(state.story) != set(GameState().story) or any(type(v) is not bool for v in state.story.values()):
                raise ValueError('Неверный прогресс эпизода')
            if state.story['case_accepted'] and 'order' not in state.evidence_ids:
                raise ValueError('Дело не выдано')
            if state.story['mvp_complete'] and not (state.story['case_accepted'] and state.story['qte_complete'] and
                    'initial_anomaly' in state.flags and {'order', 'photo', 'metadata'}.issubset(state.evidence_ids)):
                raise ValueError('Эпизод завершён без оснований')
            if state.ending not in ('', 'arrest', 'revenge', 'release', 'withdraw', 'health', 'insufficient', *NEW_ENDINGS):
                raise ValueError('Неизвестный финал')
            if (state.ending == 'health') != (state.health == 0):
                raise ValueError('Несогласованное поражение по здоровью')
            if any(type(state.statistics.get(k)) is not int or state.statistics[k] < 0
                   for k in ('inspections', 'analyses')):
                raise ValueError('Неверная статистика')
            for key, value in state.statistics.items():
                if not isinstance(key, str) or type(value) is not int or value < 0:
                    raise ValueError('Неверная статистика')
            for key in ('anna_respect', 'anna_threat', 'perfect_interview'):
                if state.statistics.get(key, 0) not in (0, 1):
                    raise ValueError('Неверный результат диалога')
            for key in ('guard_shortcut', 'guard_access', 'guard_explained', 'stealth_quiet', 'guard_attempts', 'stealth_attempts'):
                if key in state.statistics and (type(state.statistics[key]) is not int or state.statistics[key] < 0):
                    raise ValueError('Неверный результат AI-эпизода')
                if key in ('guard_shortcut', 'guard_access', 'guard_explained', 'stealth_quiet') and state.statistics.get(key, 0) not in (0, 1):
                    raise ValueError('Неверный результат AI-эпизода')
            from src.systems.campaign import ACHIEVEMENTS, ending_allowed
            from src.systems.evidence import EvidenceManager
            if not isinstance(state.run_id, str) or len(state.run_id) != 32 or any(c not in '0123456789abcdef' for c in state.run_id):
                raise ValueError('Неверный ID расследования')
            if type(state.time_remaining) is not int or not 0 <= state.time_remaining <= 18:
                raise ValueError('Неверный запас времени')
            if state.time_remaining == 0 and state.ending != 'insufficient':
                raise ValueError('Истёкший срок без завершения дела')
            if not isinstance(state.visited, list) or any(x not in self.worlds for x in state.visited):
                raise ValueError('Неверный журнал локаций')
            if not isinstance(state.achievements, list) or any(x not in ACHIEVEMENTS for x in state.achievements):
                raise ValueError('Неверное достижение')
            if not isinstance(state.campaign, dict) or set(state.campaign) != set(GameState().campaign) or any(type(v) is not bool for v in state.campaign.values()):
                raise ValueError('Неверный прогресс кампании')
            if any(type(v) is not int or not 0 <= v <= 100 for v in state.trust.values()):
                raise ValueError('Неверное доверие NPC')
            if state.ending in ('arrest', 'revenge', 'release') and not ending_allowed(state, EvidenceManager(state, self.catalog, self.rules), state.ending):
                raise ValueError('Концовка не соответствует доказательствам и решениям')
            # Display strings in earlier saves keep their meaning, while stable IDs stay unchanged.
            replacements={'Левицкого':'Нурланова','Левицкий':'Нурланов','Соколова':'Ермекова','Соколову':'Ермекову','Соколов':'Ермеков','Вейра':'Сарсенова','Вейр':'Сарсенов','Волковых':'Сейтовых','Анны':'Аружан','Анна':'Аружан'}
            def current_names(text):
                for old,new in replacements.items():text=text.replace(old,new)
                return text
            state.narrative['objective']=current_names(state.narrative['objective'])
            state.narrative['journal']=[current_names(t) for t in state.narrative['journal']]
            for record in state.evidence_records.values():record['source']=current_names(record['source'])
            for hypothesis in state.hypotheses.values():hypothesis['reason']=current_names(hypothesis['reason'])
            return state
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError('Сохранение повреждено') from exc
