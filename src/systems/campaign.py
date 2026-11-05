"""Beta progression, achievements and ending predicates, independent of UI."""
ACHIEVEMENTS = {
    'first': 'Первая улика', 'detective': 'Хороший детектив',
    'deduction': 'Мастер дедукции', 'interview': 'Безупречный допрос', 'truth': 'Правда раскрыта'}


def refresh_achievements(state, evidence):
    checks = {'first': bool(state.evidence_ids), 'detective': 'pattern' in state.flags,
              'deduction': evidence.can_finalize(),
              'interview': bool(state.statistics.get('perfect_interview', 0)),
              'truth': state.ending in ('arrest','truth','price','secret') and evidence.can_finalize()}
    new = []
    for key, earned in checks.items():
        if earned and key not in state.achievements:
            state.achievements.append(key)
            new.append(ACHIEVEMENTS[key])
    return new


def ending_allowed(state, evidence, ending):
    if ending not in ('arrest', 'revenge', 'release'):
        return False
    ready = (state.location == 'port' and state.health > 0 and state.time_remaining > 0
             and evidence.can_finalize() and state.campaign['weir_confronted'])
    if ending == 'arrest':
        ready = ready and state.campaign['backup'] and state.reputation >= 40 and state.trust.get('sokolov', 50) >= 40
    return bool(ready)
