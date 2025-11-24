from models import Course, Group, TimeSlot, Schedule
from typing import List, Dict
from weights import Weights

class Evaluate:
    def __init__(self, plans: List[Schedule]):
        self.plans = plans

    def conflict_slots(self, s1: TimeSlot, s2: TimeSlot) -> bool:
        if s1.day != s2.day:
            return False
        return not (s1.end <= s2.start or s2.end <= s1.start)
    
    def conflict_groups(self, g1: Group, g2: Group) -> bool:
        for a in g1.slots:
            for b in g2.slots:
                if self.conflict_slots(a,b):
                    return True
        return False
    
    def conflict_plan(self, plans: Dict[str, Group]) -> bool:
        groups = list(plans.values())
        for i in range(len(groups)):
            for j in range(i+1, len(groups)):
                if self.conflict_groups(groups[i], groups[j]):
                    return True
        return False
    
    def friday(self, schedule: Schedule) -> int:
        groups = list(schedule.selected_groups.values())
        minutes = 0 #minutes over 14:00

        for i in range(len(groups)):
            for j in groups[i].slots:
                if j.day == 4 and j.end > 13*60 and j.end - 13*60 > minutes:
                    minutes = j.end - 13*60
        return minutes
    
    def monday(self, schedule: Schedule) -> int:
        groups = list(schedule.selected_groups.values())
        minutes = 0
        for i in range(len(groups)):
            for j in groups[i].slots:
                if j.day == 0 and j.start < 10*60 and 10*60 - j.start > minutes:
                    minutes = 10*60 - j.start
        return minutes
    
    def gaps(self, schedule: Schedule) -> int:
        # dzień → lista slotów tego dnia
        slots_per_day = {d: [] for d in range(7)}
        # zbieramy wszystkie TimeSlot z planu
        for group in schedule.selected_groups.values():
            for slot in group.slots:
                slots_per_day[slot.day].append(slot)
        total_gap_minutes = 0

        for day in range(7):
            slots = slots_per_day[day]
            if not slots:
                continue
            # Sortujemy po czasie startu
            slots.sort(key=lambda s: s.start)
            # Liczymy gapy
            for i in range(len(slots) - 1):
                gap = slots[i+1].start - slots[i].end
                if gap > 30:           # faktyczne okienko
                    total_gap_minutes += gap

        return total_gap_minutes

    def late_end(self, schedule: Schedule):
        slots_per_day = {d: [] for d in range(7)}
        # zbieramy wszystkie TimeSlot z planu
        for group in schedule.selected_groups.values():
            for slot in group.slots:
                slots_per_day[slot.day].append(slot)
        
        late_minutes = 0
        for day in range(7):
            slots = slots_per_day[day]
            if not slots:
                continue
            # Sortujemy po czasie startu
            slots.sort(key=lambda s: s.start)
            last = slots[len(slots) - 1]
            if last.end > 16*60:
                late_minutes += last.end - 16*60
        return late_minutes


    def conflicts(self, schedule: Schedule):
        groups = list(schedule.selected_groups.values())
        conflicts = 0
        for i in range(len(groups)):
            for j in range(i+1, len(groups)):
                if self.conflict_groups(groups[i], groups[j]):
                    conflicts += 1
        return conflicts


    def mandatory_groups_conflict(self, schedule: Schedule) -> bool:
        groups = list(schedule.selected_groups.values())
        for i in range(len(groups)):
            for j in range(i+1, len(groups)):
                if self.conflict_groups(groups[i], groups[j]):
                    # jeśli kolidują obowiązkowe (czyli nie WYK)
                    if groups[i].type != "WYK" and groups[j].type != "WYK":
                        return True
        return False
    
    def days_free(self, schedule: Schedule) -> int:
        slots_per_day = {d: [] for d in range(7)}

        for group in schedule.selected_groups.values():
            for slot in group.slots:
                slots_per_day[slot.day].append(slot)
        days_free = 0
        for d in range(5):  # pon–pt
            if len(slots_per_day[d]) == 0:
                if d == 0 or d == 4:
                    days_free += 3
                else:
                    days_free += 1
        return days_free

            


    def score(self, schedule: Schedule, w: Weights = None) -> int:
        
        if w is None:
            w = Weights()

        conflicts = self.conflicts(schedule)
        friday_penalty = self.friday(schedule)
        monday_penalty = self.monday(schedule)
        gaps_penalty = self.gaps(schedule)
        late_penalty = self.late_end(schedule)
        days_free = self.days_free(schedule)

        if self.mandatory_groups_conflict(schedule):
            return 9999999

    # jeśli nie kolidują obowiązkowe, licz score normalnie
        penalty = (
            conflicts*w.weight_conflicts +
            friday_penalty * w.weight_friday_end +
            monday_penalty * w.weight_monday_start +
            gaps_penalty * w.weight_gaps +
            late_penalty * w.weight_late_end -
            days_free * w.weight_days_free
        )
        return penalty

        
    def sort_plans(self, plans: List[Schedule], w: Weights = None):
        if w is None:
            w = Weights()
        self.plans = plans
        # plans.sort(key=self.score(plans, w))
        plans.sort(key=lambda s: self.score(s, w))
