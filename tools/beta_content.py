"""Extend the existing six-node campaign, keeping evidence IDs and authoring data."""
import copy
import json
from pathlib import Path


def upgrade():
    folder = Path(__file__).resolve().parents[1] / 'src/data'
    def read(name):
        return json.loads((folder / (name + '.json')).read_text(encoding='utf-8'))
    def write(name, value):
        (folder / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    worlds, rooms = read('worlds'), read('investigations')
    worlds['archive']['requires_flags'] = ['pattern']
    worlds['metro']['requires_flags'] = ['history']
    worlds['helios']['title'] = 'Офис Helios Systems'
    worlds['helios']['requires_flags'] = ['history']
    worlds['helios']['neighbors'] = ['metro', 'port']
    worlds['port'] = copy.deepcopy(worlds['helios'])
    worlds['port'].update(title='Порт / последний след', neighbors=['helios'], requires=['pass'], requires_flags=['route'])
    for obj in worlds['port']['objects']:
        if obj['kind'] == 'investigation': obj['scene'] = 'port'
        if obj['kind'] == 'dialogue': obj.update(name='Сарсенов', dialogue='weir')
    # Individual obstacle arrangements within the established map format.
    layouts = {'apartment': [[160,160,180,110],[1050,280,160,230],[500,710,240,64]],
               'archive': [[100,180,220,90],[100,360,220,90],[1120,160,130,360]],
               'metro': [[170,190,140,200],[500,690,450,64],[1080,220,90,150]],
               'helios': [[140,150,210,100],[1050,230,150,120],[950,690,250,70]],
               'port': [[100,160,230,170],[600,710,220,100],[1100,230,100,250]]}
    for loc, walls in layouts.items(): worlds[loc]['walls'] = worlds[loc]['walls'][:4] + walls
    rooms['helios']['title'] = 'Helios / журнал доступа Сарсенова'
    all_spots = rooms['helios']['hotspots'] + rooms.get('port', {}).get('hotspots', [])
    server = copy.deepcopy(next(s for s in all_spots if s.get('evidence') == 'server'))
    rooms['helios']['hotspots'] = [s for s in rooms['helios']['hotspots'] if s.get('evidence') != 'server']
    rooms['port'] = {'title': 'Порт / независимая серверная копия', 'renderer': 'port', 'hotspots': [server,
        {'id': 'backup', 'label': 'Защищённая передача', 'rect': [120, 490, 260, 110], 'art': 'terminal',
         'description': 'Резервная копия обеспечивает законность задержания.',
         'actions': [{'id':'backup','label':'Передать копию Ермекову','type':'backup','requires':['server']}]},
        {'id': 'weir', 'label': 'Сарсенов / противостояние', 'rect':[880,440,260,150], 'art':'board',
         'description':'Сарсенов ждёт решения. Недоказанное обвинение завершит расследование поражением.',
         'actions':[{'id':'confront','label':'Начать разговор с Сарсеновым','type':'finale'}]}]}
    write('worlds', worlds); write('investigations', rooms)
    evidence = read('evidence')
    evidence['pass']['source'] = 'Офис Helios Systems'
    evidence['server']['source'] = 'Порт / независимая копия'
    write('evidence', evidence)
    dialogues = read('dialogues')
    choices = dialogues['anna']['choices']
    for c in choices:
        if c.get('evidence') == 'anna':
            c.update(effect_id='anna_respect', trust_npc='anna', trust_delta=15, reputation_delta=5)
    if not any(c.get('effect_id') == 'anna_threat' for c in choices):
        choices.insert(1, {'label':'Надавить на свидетеля', 'effect_id':'anna_threat', 'trust_npc':'anna',
                          'trust_delta':-25, 'reputation_delta':-15,
                          'reply':'Аружан отстраняется. Нажим разрушает доверие; лучше предъявить факты и выслушать её.'})
    write('dialogues', dialogues)
    write('chapters', {
      '1': {'title':'Первые следы', 'text':'Астера, 2035. Ермеков даёт Никите дело Нурланова. Примите поручение, исследуйте кабинет и квартиру. Сопоставьте снимок с кровавым следом — это завершит бесплатное дело Day 1.'},
      '2': {'title':'Архив «Сигма»', 'text':'След связан с гибелью родителей в 2020 году. Восстановите архив, подтвердите связь с «Сигмой», выслушайте Анну и получите журнал метро. Голос и камера добровольны.'},
      '3': {'title':'Правда или месть', 'text':'Журнал ведёт в Helios Systems. Получите пропуск Сарсенова, подтвердите маршрут и отправляйтесь в порт за независимой копией. Передайте резервную копию Ермекову, прежде чем решать судьбу Сарсенова.'}})

    from prologue_content import upgrade as upgrade_prologue
    upgrade_prologue()


if __name__ == '__main__': upgrade()
