from models import Course, Group, TimeSlot, Schedule
from typing import List, Dict
from weights import Weights
from scheduler import *

class Evaluate:
    def __init__(self, plans: List[Schedule]):
        self.plans = plans

    #Liczenie kary za kończenie po 13 w piątek - im dłużej tym większa kara
    def day_end(self, schedule: Schedule, w: Weights) -> int:
        groups = list(schedule.selected_groups.values())
        minutes = 0 #minutes over friday_end_hour

        for i in range(len(groups)):
            for j in groups[i].slots:
                for d in range(5):
                    if j.day == d and w.end[d] is not None and j.end > w.end[d]*60 and j.end - w.end[d]*60 > minutes:
                        minutes = j.end - w.end[d]*60
        return minutes
    
    def day_start(self, schedule: Schedule, w: Weights) -> int:
        groups = list(schedule.selected_groups.values())
        minutes = 0
        for i in range(len(groups)):
            for j in groups[i].slots:
                for d in range(5):
                    if j.day == d and w.start[d] is not None and j.start < w.start[d]*60 and w.start[d]*60 - j.start > minutes:
                        minutes = w.start[d]*60 - j.start
        return minutes
    
    def gaps(self, schedule: Schedule) -> int:
        slots_per_day = {d: [] for d in range(7)}
        for group in schedule.selected_groups.values():
            if not group.type == "WF":
                for slot in group.slots:
                    slots_per_day[slot.day].append(slot)
        total_gap_minutes = 0

        for day in range(7):
            slots = slots_per_day[day]
            if not slots:
                continue
            slots.sort(key=lambda s: s.start)
            for i in range(len(slots) - 1):
                gap = slots[i+1].start - slots[i].end
                if gap > 30:           
                    total_gap_minutes += gap

        return total_gap_minutes

    def late_end(self, schedule: Schedule):
        slots_per_day = {d: [] for d in range(7)}
        for group in schedule.selected_groups.values():
            for slot in group.slots:
                slots_per_day[slot.day].append(slot)
        
        late_minutes = 0
        for day in range(7):
            slots = slots_per_day[day]
            if not slots:
                continue
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
                if Scheduler.global_conflict_graph[groups[i]._id][groups[j]._id] == 2:
                    conflicts += 1
        return conflicts
    
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

    def single_object(self, schedule: Schedule):
        slots_per_day = {d: [] for d in range(5)}
        for group in schedule.selected_groups.values():
            for slot in group.slots:
                slots_per_day[slot.day].append(slot)
        single_penalty = 0
        for d in range(5):  # pon–pt
            if len(slots_per_day[d]) == 1:
                single_penalty += 1
        return single_penalty


    def score(self, schedule: Schedule, w: Weights = None) -> int:
        
        if w is None:
            w = Weights()

        conflicts = self.conflicts(schedule)
        gaps_penalty = self.gaps(schedule)
        late_penalty = self.late_end(schedule)
        days_free = self.days_free(schedule)
        single_penalty = self.single_object(schedule)

        penalty = (
            conflicts*w.weight_conflicts_always + 
            gaps_penalty * w.weight_gaps +
            late_penalty * w.weight_late_end -
            days_free * w.weight_days_free +
            single_penalty * w.weight_single_object
        )
        return penalty
            
    def sort_plans(self, plans: List[Schedule], w: Weights = None):
        if w is None:
            w = Weights()
        self.plans = plans
        plans.sort(key=lambda s: self.score(s, w))
        
