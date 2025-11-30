from models import Course, Group, TimeSlot, Schedule
from typing import List, Dict
from weights import Weights, Preferences
from wrapper import groups_conflict_c


class Scheduler:
    def __init__(self, courses: List[Course], preferences: Preferences = None, weights: Weights = None):
        self.courses = courses
        self.preferences = preferences or Preferences()
        self.weights = weights or Weights()

        def course_complexity(course: Course):
            grouped = course.groups_by_type()

            # 1) MRV: liczba opcji (im mniej tym bardziej ograniczony)
            mrv_count = 1
            for groups in grouped.values():
                # jeśli typ ma 0 grup, nie wpływa
                mrv_count *= len(groups) if len(groups) > 0 else 1

            # 2) Degree heuristic — kurs koliduje z innymi kursami
            # używamy conflict_graph po jego stworzeniu, ale teraz jeszcze go nie ma
            # więc wstępnie liczymy potencjalne konflikty slotowe:
            degree = 0
            for g1 in course.groups:
                for other in self.courses:
                    if other is course:
                        continue
                    for g2 in other.groups:
                        # szybkie przybliżenie: czy sloty dzielą dzień?
                        for s1 in g1.slots:
                            for s2 in g2.slots:
                                if s1.day == s2.day:
                                    degree += 1

            # 3) Liczba typów zajęć (im więcej typów, tym trudniej)
            type_count = len(grouped)

            # Wynik heurystyki:
            # - im MNIEJSZY wynik, tym łatwiejszy kurs
            # - sortujemy rosnąco: trudne → łatwe
            return (
                mrv_count,        # MRV
                degree,           # stopień konfliktów
                type_count        # liczba typów
            )
        # sortujemy kursy wg heurystyki
        self.courses.sort(key=course_complexity)

        self.preferences = preferences or Preferences()
        
        # PRZYGOTOWANIE GRUP DO KODU W C
        from wrapper import prepare_group_c
        for course in self.courses:
            for group in course.groups:
                prepare_group_c(group)
        
        #GRAF KONFLIKTÓW - TWORZENIE
        self.all_groups = []
        self.group_to_id = {}
        gid = 0
        for course in self.courses:
            for group in course.groups:
                group._id = gid
                self.all_groups.append(group)
                gid += 1
        self.group_count = gid
        self.conflict_graph = None
        N = gid
        conflict = [bytearray(N) for _ in range(N)]
        for i in range(N):
            gi = self.all_groups[i]
            for j in range(i+1, N):
                gj = self.all_groups[j]
                collides = groups_conflict_c(gi, gj, wyklad=True)
                if collides:
                    conflict[i][j] = collides
                    conflict[j][i] = collides
        self.conflict_graph = conflict
        Scheduler.global_conflict_graph = conflict

    def generate_plans(self) -> List[Schedule]:
        results = []
        plan: Dict[str, Group] = {}

        def plan_has_conflict(new_group):
            #Konflikty ćwiczeń
            for g in plan.values():
                if self.conflict_graph[g._id][new_group._id] == 1:
                    return True
                if not self.weights.weight_conflicts == 0:  
                    if self.conflict_graph[g._id][new_group._id] == 2:
                        return True
            return False


        domains = []
        course_types_list = []
        for course in self.courses:
            grouped = course.groups_by_type()
            types = list(grouped.keys())
            course_types_list.append(types)
            per_type = {}
            for t in types:
                per_type[t] = set(g._id for g in grouped[t])
            domains.append(per_type)

        num_courses = len(self.courses)
        
        def apply_forward(chosen_gid, course_index):
            removed = []
            for ci in range(course_index + 1, num_courses):
                for t, s in domains[ci].items():
                    to_remove = []
                    for gid2 in s:
                        if self.conflict_graph[chosen_gid][gid2] == 1:
                            to_remove.append(gid2)
                    for gid2 in to_remove:
                        s.remove(gid2)
                        removed.append((ci, t, gid2))
            return removed
        
        def rollback(removed):
            for ci, t, gid2 in removed:
                domains[ci][t].add(gid2)

        def dfs_course(course_index: int):
            if course_index == len(self.courses):
                results.append(Schedule(plan.copy()))
                return    

            course = self.courses[course_index]
            grouped = course.groups_by_type()
            types_list = list(grouped.keys())

            def dfs_group_type(type_index: int):
                if type_index == len(types_list):
                    dfs_course(course_index+1)
                    return
                
                t = types_list[type_index]

                if len(grouped[t]) == 1:
                    group = grouped[t][0]
                    if not plan_has_conflict(group):
                        gid = group._id
                        removed = apply_forward(gid, course_index)

                        dead = False
                        for ci in range(course_index + 1, num_courses):
                            for tt in course_types_list[ci]:
                                if len(domains[ci][tt]) == 0:
                                    dead = True
                                    break
                            if dead:
                                break
                                
                        required = True
                        req = self.preferences.required_groups or {}
                        allowed = req.get(course.name, {})      # dict: { "CW-1": 1, "CW-2": 0, ... }
                        required_keys = [k for k, v in allowed.items() if int(v) == 1]
                        if required_keys:
                            if group.key not in required_keys:
                                required = False
                        fit = True
                        for slots in group.slots:
                                if self.weights.end[slots.day] is not None and slots.end > self.weights.end[slots.day]*60:
                                    fit = False
                                    break
                                if self.weights.start[slots.day] is not None and slots.start < self.weights.start[slots.day]*60:
                                    fit = False
                                    break
                                if self.preferences.free_days[slots.day] == 1:
                                    fit = False
                                    break

                        if fit and required and not dead:
                            plan[f"{course.name}-{t}"] = group
                            dfs_group_type(type_index + 1)
                            del plan[f"{course.name}-{t}"]
                        rollback(removed)
                    return

                for group in grouped[t]:
                    gid = group._id
                    if plan_has_conflict(group):
                        continue
                    removed = apply_forward(gid, course_index)
                    dead = False
                    for ci in range(course_index + 1, num_courses):
                        for tt in course_types_list[ci]:
                            if len(domains[ci][tt]) == 0:
                                dead = True
                        if dead:
                            break
                    if not dead:
                        required = True
                        req = self.preferences.required_groups or {}
                        allowed = req.get(course.name, {})      # dict: { "CW-1": 1, "CW-2": 0, ... }
                        required_keys = [k for k, v in allowed.items() if int(v) == 1]

                        if required_keys:
                            if group.key not in required_keys:
                                required = False
                        fit = True
                        for slots in group.slots:
                                if self.weights.end[slots.day] is not None and slots.end > self.weights.end[slots.day]*60:
                                    fit = False
                                    break
                                if self.weights.start[slots.day] is not None and slots.start < self.weights.start[slots.day]*60:
                                    fit = False
                                    break
                                if self.preferences.free_days[slots.day] == 1:
                                    fit = False
                                    break
                        if fit and required:
                            plan[f"{course.name}-{t}"] = group
                            dfs_group_type(type_index + 1)
                            del plan[f"{course.name}-{t}"]
                    rollback(removed)

            dfs_group_type(0)
        
        dfs_course(0)
        return results
