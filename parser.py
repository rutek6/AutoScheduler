from bs4 import BeautifulSoup
from models import TimeSlot, Group, Course
import re

DAY_MAP = {
    "poniedziałek": 0,
    "wtorek": 1,
    "środa": 2,
    "czwartek": 3,
    "piątek": 4,
    "sobota": 5,
    "niedziela": 6
}

def parse_html_plan(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    entries = soup.find_all("timetable-entry")

    # course_name → (group_name → list[TimeSlot])
    courses = {}

    for e in entries:

        # --- 1. NAZWA KURSU ---
        course_name = e.get("name", "").strip()
        if not course_name:
            continue
        
        # --- 2. NAZWA GRUPY ---
        info = e.find("div", {"slot": "info"})
        if not info:
            continue
        group_name = info.get_text(" ", strip=True)
        
        #2.1 --- TYP GRUPY (case-insensitive)
        uname = group_name.upper()
        if "CWW" in uname:
            group_type = "CWW"
        elif "CW" in uname:
            group_type = "CW"
        elif "WYK" in uname:
            group_type = "WYK"
        elif "LAB" in uname:
            group_type = "LAB"
        elif "LEK_NOW" in uname:
            group_type = "LEK_NOW"
        elif "KON" in uname:
            group_type = "KON"
        else:
            group_type = "UNK"

        #2.2 --- NR GRUPY (first number sequence)
        m_num = re.search(r"(\d+)", group_name)
        if m_num:
            group_number = m_num.group(1)
        else:
            group_number = "0"

        group_key = f"{group_type}-{group_number}"
        
        # --- 3. START TIME ---
        start_el = e.find("span", {"slot": "time"})
        style = e.get("style", "")
        # if not start_el:
        #     continue

        start_str = start_el.get_text(" ", strip=True)

        # wyciągamy pierwszą godzinę HH:MM z dowolnego śmietnika tekstowego
        m_time = re.search(r"(\d{1,2}):(\d{2})", start_str)
        if not m_time:
            continue
        h, m = map(int, m_time.groups())
        start_minutes = h * 60 + m
        
        # --- 4. END TIME + DAY
        dialog_event = e.find("span", {"slot": "dialog-event"})
        
        if not dialog_event:
            continue

        text = dialog_event.get_text(" ", strip=True).lower()
        # zakres godzin: HH:MM - HH:MM
        m_end = re.search(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", text) #UW
        if not m_end:
            m_end = re.search(r"(\d{1,2}):(\d{2})\s*\u2014\s*(\d{1,2}):(\d{2})", text) #UKSW
        if m_end:
            h1, m1, h2, m2 = map(int, m_end.groups())
            end_minutes = h2 * 60 + m2
    
        #DAY
        
        parent_day = e.find_parent("timetable-day")
        if parent_day:
            h4 = parent_day.find_previous("h4")
            if h4:
                dname = h4.get_text(" ", strip=True).lower()
                day = DAY_MAP.get(dname)
            
            
            
        
        
        # --- 5. SCALANIE GRUP ---
        if course_name not in courses:
            courses[course_name] = {}

        if group_key not in courses[course_name]:
            courses[course_name][group_key] = []

        # dodajemy slot do tej grupy (nawet jeśli jest wiele slotów tego samego dnia)
        courses[course_name][group_key].append(
            TimeSlot(day, start_minutes, end_minutes)
        )

    # --- 6. KONWERSJA DO OBIEKTÓW Course/Group ---
    result = []
    for cname, groups in courses.items():
        group_objs = [
            Group(gkey, slots)
            for gkey, slots in groups.items()
        ]
        result.append(Course(cname, group_objs))

    return result

