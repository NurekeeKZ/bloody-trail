"""Engine-independent consequences and deterministic ending predicates."""
from copy import deepcopy

THRILLER_DEFAULTS={
 'phase':'idle','branch':'main','noise_detected':False,'movement_detected':False,
 'was_captured':False,'leg_injured':False,'injured_history':False,'chase_success':False,
 'hide_success':False,'ally_lost':False,'ally_saved':False,'secret_hint':False,
 'surrendered':False,'hide_attempts':0,'hide_elapsed':0.0,'danger':0.0,
 'chase_step':0,'chase_results':[],'route':'','escape_attempts':0,'items':[],
 'position':[180.0,500.0],'events':[],'ending_id':''}
NEW_ENDINGS=('truth','false_accusation','prisoner','price','secret')

def new_thriller():return deepcopy(THRILLER_DEFAULTS)

class StoryManager:
    def __init__(self,state,evidence):self.state=state;self.evidence=evidence;self.t=state.thriller
    def log(self,key,text):
        if key not in self.t['events']:
            self.t['events'].append(key);self.state.narrative['journal'].append(text)
            return True
        return False
    def phase(self,phase,branch=None):
        self.t['phase']=phase
        goals={'warehouse':'Найти укрытие на складе 07','hiding':'Переждать обыск: тишина и неподвижность','quiet':'Подслушать встречу; обсудить запись с Нурсом','chase':'Уйти от преследователя','recovery':'Найти аптечку и выбраться из служебной комнаты','captive':'Найти проволоку и код; открыть камеру','alley':'Открыть служебный проход и помочь Аружан','street':'Вызвать помощь и вывести Аружан','resolved':'Сопоставить доказательства, передать копию и предъявить цепочку Сарсенову'}
        self.state.narrative['objective']=goals.get(phase,self.state.narrative['objective'])
        if branch:self.t['branch']=branch
        self.t['position']=[180.,500.]
    def start(self):
        if self.t['phase']=='idle':self.phase('warehouse');self.log('start','Нурс обнаружил следы ночной встречи на складе порта.')
    def injury(self):
        if not self.t['leg_injured']:
            self.t['leg_injured']=True;self.t['injured_history']=True
            self.state.health=max(1,self.state.health-20)
            self.log('injury','Травма ноги: скорость снижена. Перевязка доступна в служебной комнате.')
    def hide_result(self,cause):
        self.t['hide_attempts']+=1;self.t['hide_elapsed']=0.;self.t['danger']=0.
        if cause=='quiet':
            self.t['hide_success']=True;self.phase('quiet','quiet')
            self.log('quiet','Тишина позволила подслушать встречу. Найдите диктофон у окна.')
        elif cause=='motion':
            self.t['movement_detected']=True;self.injury();self.phase('recovery','motion')
            self.log('motion','Преследователь заметил движение. Никита ранен и заперт в служебной комнате.')
        else:
            self.t['noise_detected']=True
            if self.t['hide_attempts']>=2:self.capture()
            else:self.begin_chase('noise')
    def begin_chase(self,branch=None):
        if len(self.t['chase_results'])==5:
            self.phase('street');self.log('escape_after_search','После обыска Никита выбрался на улицу через служебную лестницу.');return
        if not self.t['chase_results']:self.t['chase_step']=0
        self.phase('chase',branch or self.t['branch'])
    def qte_result(self,key,success,route=''):
        if any(r['id']==key for r in self.t['chase_results']):return False
        self.t['chase_results'].append({'id':key,'success':bool(success),'route':route})
        self.t['chase_step']=len(self.t['chase_results'])
        if route:self.t['route']=route
        if not success:
            self.state.health=max(1,self.state.health-8)
            if key=='jump':self.injury()
        self.log('qte_'+key,('Пройдено: ' if success else 'Ошибка: ')+key+(' / '+route if route else ''))
        return True
    def finish_chase(self):
        results=self.t['chase_results'];errors=sum(not r['success'] for r in results)
        if errors>=3:self.capture()
        elif any(r['id']=='door' and not r['success'] for r in results):
            self.phase('hiding');self.t['hide_elapsed']=0.;self.t['danger']=0.
        else:
            self.t['chase_success']=True;self.phase('alley' if self.t['route']=='left' else 'street')
    def capture(self):
        self.t['was_captured']=True;self.phase('captive','captive')
        self.log('captured','Никита захвачен. В камере можно найти инструмент, код и журнал похитителей.')
    def rescue(self,save):
        self.t['ally_saved']=bool(save);self.t['ally_lost']=not save
        self.state.trust['anna']=90 if save else 0
        if save:self.state.health=max(1,self.state.health-10)
        self.log('ally_choice','Аружан спасена через служебный выход.' if save else 'Никита ушёл один. Аружан погибла при поджоге склада.')
        self.phase('resolved')
    def collect(self,key):
        if key not in self.t['items']:self.t['items'].append(key);return True
        return False
    def escape(self,code):
        if not {'wire','code'}.issubset(self.t['items']):return False
        if code!='4172':
            self.t['escape_attempts']+=1;return False
        self.log('escaped','Замок камеры вскрыт; Никита выбрался из плена с журналом похитителей.')
        self.phase('street');return True

def ending_allowed(state,evidence,ending):
    t=state.thriller
    if state.health<=0 or state.time_remaining<=0:return False
    if ending=='prisoner':return t['was_captured'] and t['phase']=='captive' and (t['escape_attempts']>=3 or t['surrendered'])
    if t['phase']!='resolved' or state.location!='port':return False
    if ending=='false_accusation':return not evidence.can_finalize() and 'false_charge' in t['events']
    ready=evidence.can_finalize() and state.campaign['weir_confronted'] and state.campaign['backup']
    if ending=='truth':return ready and not t['ally_lost']
    if ending=='price':return ready and t['ally_lost']
    if ending=='secret':
        return (ready and t['hide_success'] and t['chase_success'] and t['ally_saved'] and t['secret_hint']
                and len(t['chase_results'])==5 and all(r['success'] for r in t['chase_results'])
                and {'warehouse_record','book_drive','password_note'}.issubset(state.evidence_ids))
    return False

def validate_thriller(t,catalog):
    import math
    if not isinstance(t,dict) or set(t)!=set(THRILLER_DEFAULTS):raise ValueError('Неверная структура сюжетных последствий')
    for k,v in THRILLER_DEFAULTS.items():
        if type(v) is bool and type(t[k]) is not bool:raise ValueError('Неверный сюжетный флаг')
    if t['phase'] not in ('idle','warehouse','hiding','quiet','chase','recovery','captive','alley','street','resolved'):raise ValueError('Неизвестная ветка')
    if t['branch'] not in ('main','quiet','noise','motion','captive'):raise ValueError('Неизвестная история')
    if t['route'] not in ('','left','right') or t['ending_id'] not in ('',*NEW_ENDINGS):raise ValueError('Неверный выбор')
    for key,maximum in [('hide_attempts',100),('chase_step',5),('escape_attempts',3)]:
        if type(t[key]) is not int or not 0<=t[key]<=maximum:raise ValueError('Неверный счётчик ветки')
    for key,maximum in [('hide_elapsed',15),('danger',1)]:
        if type(t[key]) not in (int,float) or not math.isfinite(t[key]) or not 0<=t[key]<=maximum:raise ValueError('Неверное состояние пряток')
    if not isinstance(t['position'],list) or len(t['position'])!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in t['position']) or not 50<=t['position'][0]<=1230 or not 160<=t['position'][1]<=590:raise ValueError('Неверная позиция эпизода')
    for key in ('events','items'):
        if not isinstance(t[key],list) or len(t[key])>100 or any(not isinstance(v,str) for v in t[key]) or len(set(t[key]))!=len(t[key]):raise ValueError('Неверный журнал эпизода')
    if not isinstance(t['chase_results'],list) or len(t['chase_results'])!=t['chase_step']:raise ValueError('Неверная погоня')
    for r,expected in zip(t['chase_results'],('jump','direction','door','sprint','push')):
        if not isinstance(r,dict) or set(r)!={'id','success','route'} or r['id']!=expected or type(r['success']) is not bool or r['route'] not in ('','left','right'):raise ValueError('Неверный результат QTE')
    if t['chase_success'] and (len(t['chase_results'])!=5 or sum(not r['success'] for r in t['chase_results'])>=3 or not t['chase_results'][2]['success']):raise ValueError('Погоня не была пройдена')
    if t['ally_saved'] and t['ally_lost']:raise ValueError('Противоречивая судьба союзника')
