import json
from dataclasses import dataclass, asdict, field
from typing import List, Optional
from models import Group

@dataclass
class Weights:
    weight_conflicts: int = 0
    weight_conflicts_always: int = 10000 
    weight_gaps: int = 10 #Waga okienek
    weight_late_end: int = 25 #Waga późnego końca zajęć
    weight_days_free: int = 25 #Ujemna, waga wolnych dni
    weight_single_object: int = 15 #Waga pojedyńczych zajęć
    #Godziny startu i końca w poszczególne dni (0 - pon.)
    start: List[Optional[int]] = field(default_factory=lambda: [None, None, None, None, None])
    end: List[Optional[int]] = field(default_factory=lambda: [None, None, None, None, None])

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=4, ensure_ascii=False)

    @staticmethod
    def load(path: str):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return Weights(**data)
@dataclass
class Preferences:
    required_groups: dict[str, dict[str, int]] = field(default_factory=dict)
    free_days: List[int] = field(default_factory=lambda: [None, None, None, None, None])
