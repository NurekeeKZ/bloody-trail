class EvidenceManager:
    def __init__(self, state, catalog, rules):
        self.state, self.catalog, self.rules = state, catalog, rules
        self.on_change = lambda kind, identifier: None

    def collect(self, evidence_id):
        if evidence_id not in self.catalog:
            raise ValueError('Unknown evidence: ' + evidence_id)
        if evidence_id in self.state.evidence_ids:
            return False
        self.state.evidence_ids.append(evidence_id)
        self.state.evidence_records[evidence_id] = {
            'day': self.state.current_day, 'slot': self.state.time_slot,
            'verified': False, 'source': self.catalog[evidence_id]['source'], 'related': []}
        self.state.statistics['inspections'] += 1
        self.on_change('collect', evidence_id)
        return True

    def confirm_rule(self, rule):
        if not set(rule['requires']).issubset(self.state.evidence_ids):
            return False
        if rule['id'] not in self.state.flags:
            self.state.flags.append(rule['id'])
            self.on_change('conclusion', rule['id'])
        for hypothesis in self.state.hypotheses.values():
            if hypothesis['rule'] == rule['id']:
                hypothesis.update(status='confirmed', reason=rule['text'] + ' Все необходимые источники собраны.')
        for eid in rule['requires']:
            record = self.state.evidence_records[eid]
            record['verified'] = True
            record['related'] = sorted(set(record.get('related', [])) | (set(rule['requires']) - {eid}))
        return True

    def propose(self, first, second):
        pair = sorted([first, second])
        if first == second or not set(pair).issubset(self.state.evidence_ids):
            raise ValueError('Выберите две разные найденные улики.')
        key = '|'.join(pair)
        if key not in self.state.hypotheses:
            rule = self.rule_for(pair)
            self.state.hypotheses[key] = {'evidence': pair, 'rule': rule['id'] if rule else None,
                                         'status': 'pending', 'reason': ('Преступления 2020 и 2035 годов могут быть связаны. Нужен независимый архивный протокол.' if rule and rule['id']=='blood_history' else 'Гипотеза ещё не проверена.')}
        return key

    def rule_for(self, pair):
        return next((r for r in self.rules if sorted(r.get('pair', [])) == sorted(pair)), None)

    def evaluate(self, key):
        hypothesis = self.state.hypotheses[key]
        rule = self.rule_for(hypothesis['evidence'])
        if rule is None:
            self.state.statistics['deduction_mistakes'] = self.state.statistics.get('deduction_mistakes', 0) + 1
            self.on_change('mistake', key)
            hypothesis.update(status='rejected', reason='В материалах дела нет основания для этой связи. Совместное наличие предметов не доказывает причинную связь.')
        else:
            missing = [eid for eid in rule['requires'] if eid not in self.state.evidence_ids]
            if missing:
                hypothesis.update(status='pending', reason='Недостаточно подтверждений. Нужны: ' + ', '.join(self.catalog[e]['title'] for e in missing) + '.')
            else:
                self.confirm_rule(rule)
                hypothesis.update(status='confirmed', reason=rule['text'] + f' Все необходимые источники собраны ({len(rule["requires"])}).')
        return hypothesis['reason']

    def check_deduction(self, rule_id, chosen):
        """Slot board: the player must name every source of one conclusion; returns (confirmed, message)."""
        rule = next(r for r in self.rules if r['id'] == rule_id)
        required, chosen = set(rule['requires']), set(chosen)
        if not chosen.issubset(self.state.evidence_ids):
            raise ValueError('Выберите только найденные улики.')
        if rule_id in self.state.flags:
            return True, rule['text']
        if chosen == required:
            return True, self.evaluate(self.propose(*rule['pair']))
        if not required.issubset(self.state.evidence_ids):
            return False, 'Для этого вывода найдены ещё не все материалы. Продолжайте осмотр; ошибка не засчитана.'
        self.state.statistics['deduction_mistakes'] = self.state.statistics.get('deduction_mistakes', 0) + 1
        self.on_change('mistake', rule_id)
        return False, (f'Не сходится: подходят {len(chosen & required)} из {len(required)}. '
                       'Совместное наличие предметов не доказывает связь.')

    def reject(self, key):
        hypothesis = self.state.hypotheses[key]
        if hypothesis['status'] == 'confirmed':
            return 'Связь подтверждена независимыми источниками. Отмена мнения не отменяет найденные факты.'
        hypothesis.update(status='rejected', reason='Игрок отклонил гипотезу: доказательств пока недостаточно. Её можно проверить повторно.')
        return hypothesis['reason']

    def analyze(self):
        unlocked = []
        for rule in self.rules:
            if set(rule['requires']).issubset(self.state.evidence_ids):
                if rule['id'] not in self.state.flags:
                    self.confirm_rule(rule)
                    unlocked.append(rule['text'])
        self.state.statistics['analyses'] += 1
        return unlocked

    def can_finalize(self):
        return all(r['id'] in self.state.flags and set(r['requires']).issubset(self.state.evidence_ids)
                   for r in self.rules if not r.get('optional', False))

    @property
    def score(self):
        """Derived from unique facts, never incremented by repeated UI actions."""
        correct = sum(r['id'] in self.state.flags and set(r['requires']).issubset(self.state.evidence_ids)
                      for r in self.rules)
        return 10 * len(set(self.state.evidence_ids)) + 20 * correct
