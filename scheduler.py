from models import Course, Group, TimeSlot, Schedule
from typing import List, Dict

class Scheduler:
    def __init__(self, courses: List[Course]):
        self.courses = courses

    def generate_plans(self) -> List[Schedule]:
        results = []
        plan: Dict[str, Group] = {}

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

                for group in grouped[t]:
                    plan[f"{course.name}-{t}"] = group

                    dfs_group_type(type_index + 1)

                    del plan[f"{course.name}-{t}"]
            
            dfs_group_type(0)
        
        dfs_course(0)
        return results

    
