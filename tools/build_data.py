"""Rebuild the starter content. Runtime reads JSON, never this script."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'src' / 'data'
OUT.mkdir(parents=True, exist_ok=True)


def write(name, value):
    (OUT / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


entries = [
    ('photo', 'Фотография трёх капель', 'station', 'На снимке из квартиры Нурланова — три капли, как на семейной фотографии 2020 года.'),
    ('metadata', 'Удалённые метаданные', 'station', 'В журнале терминала остались следы удаления полей. N.U.R.S. рекомендует сравнение с исходным делом.'),
    ('order', 'Поручение Ермекова', 'station', 'Три дня до передачи дела комиссии. Любое обвинение требует независимых подтверждений.'),
    ('blood', 'След на стене', 'apartment', 'Рисунок повторяет фотографию. Само сходство ещё не устанавливает личность убийцы.'),
    ('key', 'Ключ 2/2', 'apartment', 'В сейфе Нурланова найдена вторая часть ключа к архивным материалам.'),
    ('note', 'Записка у радиатора', 'apartment', 'Нурланов оставил ссылку на архив 2020 года и имя источника — Аружан.'),
    ('archive', 'Дело Сейтовых, 2020', 'archive', 'Айгуль и Ерлан собирали материалы о системе слежения «Сигма». Версия ограбления не объясняет пропажу архива.'),
    ('sigma', 'Реестр «Сигмы»', 'archive', 'В исходном реестре сохранилась связь проекта с Helios Systems. Требуется независимый журнал доступа.'),
    ('anna', 'Показания Аружан', 'metro', 'Аружан указывает на маршрут перевозки материалов к порту. Показания нужно проверить по пропускам.'),
    ('transit', 'Журнал охраны метро', 'metro', 'Запись подтверждает время движения груза к порту; номер совпадает с указанным Аружан.'),
    ('pass', 'Пропуск Сарсенова', 'helios', 'Пропуск связывает Сарсенова с маршрутом груза. Одна запись доступа не доказывает всё дело.'),
    ('server', 'Независимая серверная копия', 'helios', 'Копия журнала связывает операции Сарсенова с удалением материалов «Сигмы». Вместе с исходным архивом замыкает цепочку.')]
names = {'station': 'Полицейский участок', 'apartment': 'Квартира Нурланова', 'archive': 'Городской архив',
         'metro': 'Переход метро', 'helios': 'Helios Systems / порт'}
write('evidence', {eid: {'title': title, 'source': names[loc], 'text': description, 'reliability': 'Требует сопоставления'}
                   for eid, title, loc, description in entries})
write('rules', [
    {'id': 'pattern', 'requires': ['photo', 'blood'], 'text': 'Совпадение следов подтверждено двумя источниками.'},
    {'id': 'history', 'requires': ['metadata', 'archive', 'sigma'], 'text': 'Удаление материалов связано с делом 2020 года и «Сигмой».'},
    {'id': 'route', 'requires': ['anna', 'transit', 'pass'], 'text': 'Маршрут из показаний подтверждён журналом и пропуском Сарсенова.'},
    {'id': 'identity', 'requires': ['archive', 'sigma', 'pass', 'server'], 'text': 'Архив и независимая копия подтверждают цепочку действий Сарсенова.'}])
worlds = {}
locations = list(names)
for index, loc in enumerate(locations):
    objects = [
        {'id': 'desk', 'name': 'Рабочее место / материалы дела', 'rect': [440, 300, 192, 96], 'kind': 'investigation', 'scene': loc},
        {'id': 'board', 'name': 'Доска доказательств', 'rect': [900, 160, 180, 64], 'kind': 'board'},
        {'id': 'npc', 'name': ['Капитан Ермеков', 'N.U.R.S.', 'N.U.R.S.', 'Аружан', 'N.U.R.S.'][index],
         'rect': [770, 420, 28, 24], 'kind': 'dialogue', 'dialogue': 'anna' if loc == 'metro' else 'briefing'},
        {'id': 'exit', 'name': 'Выход на карту Астеры', 'rect': [1320, 600, 70, 100], 'kind': 'map'}]
    worlds[loc] = {'title': names[loc], 'size': [1536, 960], 'spawn': [350, 520],
                   'chapter': 1 if index < 2 else 2 if index < 4 else 3,
                   'requires': [[], ['photo'], ['key', 'note'], ['archive'], ['anna', 'transit']][index],
                   'neighbors': [locations[j] for j in (index - 1, index + 1) if 0 <= j < len(locations)],
                   'walls': [[0, 0, 1536, 112], [0, 928, 1536, 32], [0, 0, 32, 960], [1504, 0, 32, 960],
                             [160, 160, 180, 110], [1100, 310, 96, 210], [480, 690, 300, 72]], 'objects': objects}
write('worlds', worlds)
investigations = {}
rects = [[150, 275, 260, 190], [500, 380, 240, 116], [790, 240, 235, 200]]
for loc in locations:
    selected = [row for row in entries if row[2] == loc]
    investigations[loc] = {'title': names[loc], 'hotspots': [
        {'id': row[0], 'label': row[1], 'rect': rects[i], 'evidence': row[0],
         'art': ['terminal', 'papers', 'board'][i]} for i, row in enumerate(selected)]}
write('investigations', investigations)
write('dialogues', {
    'briefing': {'speaker': 'N.U.R.S.', 'text': 'Нурланов мёртв. Снимок повторяет след из дела ваших родителей. Начните с терминала, Никита. Совпадение — ещё не доказательство.',
                 'choices': [{'label': 'Как вести расследование?', 'reply': 'Осмотрите все материалы. Введите «сравни следы» в панели N.U.R.S. или проверьте цепочку на доске.'},
                             {'label': 'Что показал архив?', 'requires': ['archive'], 'reply': 'Ваши родители изучали «Сигму». Найдите независимое подтверждение журнала доступа.'},
                             {'label': 'Завершить разговор', 'close': True}]},
    'anna': {'speaker': 'Аружан', 'text': 'Нурланов боялся, что архив снова исчезнет. Я видела груз, направлявшийся к порту. Проверьте журнал охраны.',
             'choices': [{'label': 'Записать показания', 'evidence': 'anna', 'reply': 'Показания записаны. Сверьте время с журналом охраны.'},
                         {'label': 'Уточнить по журналу', 'requires': ['transit'], 'reply': 'Да, это то время. Пропуск в порту даст вам следующий независимый источник.'},
                         {'label': 'Завершить разговор', 'close': True}]}})
write('intents', {
    'evidence': ['покажи улики', 'открой улики', 'показать инвентарь', 'список улик', 'что найдено', 'открой инвентарь', 'улики'],
    'analyze': ['анализируй запись', 'сравни следы', 'сопоставь улики', 'проверь доказательства', 'анализ следов', 'анализируй материалы', 'проверить связь', 'сравни материалы'],
    'map': ['покажи карту', 'открой карту', 'карта города', 'где локации', 'маршрут города', 'карта'],
    'help': ['какие есть версии', 'помоги расследованию', 'нужна подсказка', 'что делать дальше', 'помощь', 'какой следующий шаг', 'покажи подсказку']})

from investigation_content import upgrade
upgrade()
