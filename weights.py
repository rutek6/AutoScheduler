import json
from dataclasses import dataclass, asdict

@dataclass
class Weights:
    weight_conflicts: int = 10000
    weight_friday_end: int = 15
    weight_monday_start: int = 3
    weight_gaps: int = 10
    weight_late_end: int = 25
    weight_days_free: int = 25

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=4, ensure_ascii=False)

    @staticmethod
    def load(path: str):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return Weights(**data)