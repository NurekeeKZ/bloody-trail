"""Idempotent enrichment of the starter JSON for Investigation Mode v0.3."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def upgrade():
    folder = ROOT / 'src' / 'data'
    def read(name):
        return json.loads((folder / (name + '.json')).read_text(encoding='utf-8'))
    def write(name, value):
        (folder / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    scenes = read('investigations')
    scenes['station'] = {
        'title': 'Кабинет особого отдела', 'case': 'Дело Нурланова / Кровавый след',
        'background': 'assets/rooms/station.png', 'renderer': 'office',
        'hotspots': [
            {'id': 'computer', 'label': 'Компьютер N.U.R.S.', 'rect': [365, 300, 235, 170], 'art': 'terminal',
             'evidence': 'metadata', 'description': 'Полицейский терминал. В журнале дела остались следы удаления метаданных.',
             'actions': [
                 {'id': 'archive', 'label': 'Изучить архив', 'type': 'read', 'text': 'Запись Нурланова доступна. Исходное дело Сейтовых хранится в городском архиве; этот терминал не заменяет оригинал.'},
                 {'id': 'deleted', 'label': 'Проверить удалённые файлы', 'type': 'collect', 'evidence': 'metadata', 'requires': ['photo']},
                 {'id': 'nurs', 'label': 'Попросить N.U.R.S. проанализировать', 'type': 'assistant', 'requires': ['metadata']}]},
            {'id': 'documents', 'label': 'Фотоматериалы Нурланова', 'rect': [655, 440, 190, 100], 'art': 'papers',
             'evidence': 'photo', 'description': 'Снимок трёх капель крови. Никита узнаёт композицию следа из семейной папки 2020 года.',
             'actions': [{'id': 'photo', 'label': 'Зафиксировать фотографию', 'type': 'collect', 'evidence': 'photo'}]},
            {'id': 'folders', 'label': 'Папки дел / поручение', 'rect': [1130, 150, 110, 200], 'art': 'folders',
             'evidence': 'order', 'description': 'Капитан Ермеков выделил три дня до передачи дела внешней комиссии.',
             'actions': [{'id': 'order', 'label': 'Сохранить поручение Ермекова', 'type': 'collect', 'evidence': 'order'}]},
            {'id': 'board', 'label': 'Доска расследования', 'rect': [765, 140, 310, 210], 'art': 'board',
             'description': 'Выберите две найденные улики, создайте гипотезу и проверьте её по независимым источникам.',
             'actions': [{'id': 'board', 'label': 'Открыть доску', 'type': 'board'}]},
            {'id': 'phone', 'label': 'Телефон / капитан Ермеков', 'rect': [1020, 420, 160, 90], 'art': 'phone',
             'description': 'Внутренняя линия отдела. Новые подтверждённые выводы открывают вопросы капитану.',
             'actions': [{'id': 'call', 'label': 'Связаться с Ермековым', 'type': 'dialogue', 'dialogue': 'sokolov'}]},
            {'id': 'window', 'label': 'Окно / Астера', 'rect': [65, 140, 245, 220], 'art': 'window',
             'description': 'Дождь смывает следы с улиц. В кабинете остаются фотографии, документы и три дня на проверку.',
             'actions': [{'id': 'look', 'label': 'Осмотреть город', 'type': 'read', 'text': 'Ночной центр Астеры. Это атмосферная деталь, а не улика и не подтверждение какой-либо версии.'}]},
            {'id': 'desk', 'label': 'Стол Никиты', 'rect': [320, 545, 700, 64], 'art': 'desk',
             'description': 'Личная рабочая зона детектива. Вещи здесь помогают организовать расследование.',
             'actions': [{'id': 'inventory', 'label': 'Открыть материалы дела', 'type': 'inventory'}]}
        ]}
    write('investigations', scenes)
    rules = read('rules')
    pairs = {'pattern': ['photo', 'blood'], 'history': ['metadata', 'archive'],
             'route': ['anna', 'transit'], 'identity': ['pass', 'server']}
    for rule in rules:
        if rule['id'] in pairs:
            rule['pair'] = pairs[rule['id']]
    if not any(r['id'] == 'initial_anomaly' for r in rules):
        rules.append({'id': 'initial_anomaly', 'requires': ['photo', 'metadata'], 'pair': ['photo', 'metadata'],
                      'optional': True, 'text': 'Снимок связан с записью, в которой удалены метаданные. Нужна проверка исходного дела 2020 года; личность убийцы этим не установлена.'})
    write('rules', rules)
    evidence = read('evidence')
    for eid, entry in evidence.items():
        entry['id'] = eid
        entry['image'] = 'assets/evidence/' + eid + '.png'
        entry['media_note'] = 'Схематичная реконструкция для прототипа; подпись и описание являются игровыми данными.'
    write('evidence', evidence)
    conversations = read('dialogues')
    conversations['sokolov'] = {
        'speaker': 'Капитан Нурсултан Ермеков',
        'text': 'У тебя три дня, Волков. Не путай знакомый след с доказанной версией. Сначала собери основания.',
        'choices': [
            {'label': 'Уточнить порядок расследования', 'reply': 'Зафиксируй материалы, затем проверь связи. Ни одно имя не должно появиться в обвинении без подтверждения.'},
            {'label': 'Обсудить связь снимка и удаления', 'requires_flags': ['initial_anomaly'],
             'reply': 'Связь записи со снимком подтверждена. Теперь я понимаю, почему ты просишь сверку с исходным делом. Найди материалы Нурланова и независимый оригинал 2020 года.'},
            {'label': 'Завершить разговор', 'close': True}]}
    write('dialogues', conversations)
    from mvp1_content import upgrade as upgrade_mvp1
    upgrade_mvp1()


if __name__ == '__main__':
    upgrade()
