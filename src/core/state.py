from dataclasses import dataclass, field, asdict
from uuid import uuid4
from src.systems.story_manager import new_thriller


@dataclass
class GameState:
    location: str = 'station'
    position: list = field(default_factory=lambda: [350.0, 520.0])
    evidence_ids: list = field(default_factory=list)
    evidence_records: dict = field(default_factory=dict)
    flags: list = field(default_factory=list)
    trust: dict = field(default_factory=dict)
    reputation: int = 100
    health: int = 100
    current_day: int = 1
    time_slot: int = 0
    ending: str = ''
    play_seconds: float = 0.0
    hypotheses: dict = field(default_factory=dict)
    story: dict = field(default_factory=lambda: {'case_accepted': False, 'anomaly_announced': False,
                                                'qte_complete': False, 'mvp_complete': False})
    statistics: dict = field(default_factory=lambda: {'inspections': 0, 'analyses': 0})
    narrative: dict = field(default_factory=lambda: {'started': False, 'prologue_complete': False, 'flashback_seen': False, 'objective': 'Принять дело Нурланова', 'journal': []})
    run_id: str = field(default_factory=lambda: uuid4().hex)
    time_remaining: int = 18
    visited: list = field(default_factory=lambda: ['station'])
    achievements: list = field(default_factory=list)
    campaign: dict = field(default_factory=lambda: {'archive_qte': False, 'backup': False,
                                                   'weir_confronted': False})

    companion: dict = field(default_factory=lambda: {'mode': 'follow', 'location': '', 'position': [350.0, 590.0]})
    discoveries: dict = field(default_factory=lambda: {'revealed': [], 'solved': [], 'hints': {}, 'comments': []})
    intuition: float = 100.0

    thriller: dict = field(default_factory=new_thriller)

    def to_dict(self):
        return asdict(self)
