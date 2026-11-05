"""Stateful puzzle logic independent of Pygame. UI cannot award unsolved rewards."""
class HiddenEvidenceSystem:
    def __init__(self,state):self.state=state
    def reveal(self,key):
        if key not in self.state.discoveries['revealed']:
            self.state.discoveries['revealed'].append(key);return True
        return False
    def known(self,key):return key in self.state.discoveries['revealed']

class PuzzleManager:
    def __init__(self,state,evidence,definitions):
        self.state=state;self.evidence=evidence;self.definitions=definitions
    def available(self,key):
        p=self.definitions[key]
        return set(p.get('requires',[])).issubset(self.state.evidence_ids) and set(p.get('revealed',[])).issubset(self.state.discoveries['revealed'])
    def solve(self,key,answer):
        p=self.definitions[key]
        if key in self.state.discoveries['solved']:return False,'Уже решено; повторных очков нет.'
        if not self.available(key):return False,p.get('locked','Недостаточно оснований. Осмотрите другие предметы и поговорите с сотрудниками.')
        if str(answer).strip()!=p['answer']:
            self.state.statistics['puzzle_errors']=self.state.statistics.get('puzzle_errors',0)+1
            return False,p['failure']
        self.state.discoveries['solved'].append(key)
        if p.get('reward'):self.evidence.collect(p['reward'])
        for marker in p.get('unlocks',[]):HiddenEvidenceSystem(self.state).reveal(marker)
        return True,p['success']

class HintManager:
    def __init__(self,state,definitions):self.state=state;self.definitions=definitions
    def next(self,location):
        candidates=[(key,p) for key,p in self.definitions.items() if p['location']==location and key not in self.state.discoveries['solved']]
        if not candidates:return 'Проверьте собранные материалы на доске. Вывод принимает детектив.'
        key,p=candidates[0];level=min(3,self.state.discoveries['hints'].get(key,0)+1)
        self.state.discoveries['hints'][key]=level
        return f'Подсказка {level}/3: '+p['hints'][level-1]
