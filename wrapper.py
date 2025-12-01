from models import TimeSlot, Group, Schedule, Course
from typing import List, Dict
import os, sys, ctypes as ct

class CTimeSlot(ct.Structure):
    _fields_ = [
        ("day", ct.c_int),
        ("start", ct.c_int),
        ("end", ct.c_int),
        ("week", ct.c_int)
    ]

if hasattr(sys, "_MEIPASS"):
    # onefile / standalone mode
    base = sys._MEIPASS
else:
    # development mode
    base = os.path.dirname(__file__)

import platform

# detect which OS we are on
system = platform.system()

if hasattr(sys, "_MEIPASS"):
    base = sys._MEIPASS     
else:
    base = os.path.dirname(__file__)

if system == "Windows":
    libname = "scheduler_core.dll"
elif system == "Linux":
    libname = "scheduler_core.so"
elif system == "Darwin":      
    libname = "scheduler_core.dylib"
else:
    raise RuntimeError(f"Unsupported OS: {system}")

dll_path = os.path.join(base, libname)


lib = ct.CDLL(dll_path)

lib.groups_conflict.argtypes = [ct.POINTER(CTimeSlot), ct.POINTER(CTimeSlot), ct.c_int, ct.c_int, ct.c_char_p, ct.c_char_p, ct.c_int]
lib.groups_conflict.restype = ct.c_int

def prepare_group_c(group: Group):
        group.c_slots = (CTimeSlot * len(group.slots))(
            *[CTimeSlot(s.day, s.start, s.end, s.week) for s in group.slots]
        )
        group.c_slot_count = len(group.slots)
        group.c_type = group.type.encode("ascii")

def groups_conflict_c(g1: Group, g2: Group, wyklad: bool):
    return lib.groups_conflict(
        g1.c_slots,
        g2.c_slots,
        g1.c_slot_count,
        g2.c_slot_count,
        g1.c_type,
        g2.c_type,
        wyklad
    )
