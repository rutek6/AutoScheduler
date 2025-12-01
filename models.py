from dataclasses import dataclass
from typing import List, Dict

@dataclass
class TimeSlot:
    day: int #0 - Pon, 6 - Niedz
    start: int
    end: int
    week: int #0 - każdy tydzień, 1 - nieparzyste, 2 - parzyste

@dataclass
class Group:
    key: str
    slots: List[TimeSlot]
    person: str

    @property
    def type(self):
        return self.key.split("-")[0]

    @property
    def number(self):
        return int(self.key.split("-")[1])
    
  

@dataclass
class Course:
    name: str
    groups: List[Group]

    def get_groups_by_type(self, group_type: str) -> List[Group]:
       return [g for g in self.groups if g.type == group_type]
    
    def groups_by_type(self) -> Dict[str, List[Group]]:
        result = {}
        for g in self.groups:
            result.setdefault(g.type, []).append(g)
        return result

@dataclass
class Schedule:
    selected_groups: Dict[str, Group]
