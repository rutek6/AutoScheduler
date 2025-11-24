import os
import math
import tkinter as tk
from tkinter import filedialog, messagebox
from parser import parse_html_plan    # parses timetable entries from HTML. See parser.py. :contentReference[oaicite:6]{index=6}
from scheduler import Scheduler
from eval import Evaluate            # scoring & conflict detection. See eval.py. :contentReference[oaicite:7]{index=7}
from models import TimeSlot, Group, Course, Schedule  # datamodels. :contentReference[oaicite:8]{index=8}
from weights import Weights

# default sample path (uploaded file in your project)
SAMPLE_PATH = "/mnt/data/plan.html.html"  # bundled sample file. :contentReference[oaicite:9]{index=9}

DAY_NAMES = ["Pon", "Wto", "Śro", "Czw", "Pią", "Sob", "Ndz"]

# Visual parameters
CANVAS_WIDTH = 1000
CANVAS_HEIGHT = 700
LEFT_COL_WIDTH = 60      # width for hour labels
DAY_COL_GAP = 6
TOP_MARGIN = 20
BOTTOM_MARGIN = 20

START_HOUR = 7   # timetable start (most USOS exports use 7..20). You may override after parsing.
END_HOUR = 20

# color palette for groups (cycled)
COLORS = [
    "#cfe2f3", "#f9cb9c", "#d9ead3", "#f4cccc", "#d9d2e9",
    "#fff2cc", "#ead1dc", "#d0e0e3", "#fce5cd", "#b6d7a8"
]


class TimetableApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.profile = Weights()
        self.title("Generator planów — Siatka godzinowa")
        self.geometry(f"{CANVAS_WIDTH+40}x{CANVAS_HEIGHT+140}")

        # top controls
        ctrl = tk.Frame(self)
        ctrl.pack(padx=8, pady=6, anchor="w")
        w = self.load_profile
        if w is None:
            w = Weights()

        
        tk.Button(ctrl, text="Wczytaj plik HTML...", command=self.load_file).pack(side="left", padx=4)
        tk.Button(ctrl, text="Wczytaj profil JSON", command=self.load_profile).pack(side="left", padx=4)

        

        self.info_label = tk.Label(ctrl, text="Brak załadowanego planu")
        self.info_label.pack(side="left", padx=10)

        nav = tk.Frame(self)
        nav.pack(padx=8, pady=4, anchor="w")

        tk.Button(nav, text="<< Poprzedni", command=self.prev_plan).pack(side="left", padx=4)
        tk.Button(nav, text="Następny >>", command=self.next_plan).pack(side="left", padx=4)
        self.plan_index_label = tk.Label(nav, text="Plan 0 / 0")
        self.plan_index_label.pack(side="left", padx=8)

        # canvas where timetable is drawn
        self.canvas = tk.Canvas(self, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="white")
        self.canvas.pack(padx=10, pady=6)

        # bottom: textual details for selected tile
        self.details = tk.Text(self, height=6)
        self.details.pack(fill="x", padx=10, pady=(0,10))

        # internal state
        self.plans = []           # List[Schedule]
        self.sorted_plans = []
        self.current_index = 0
        self.start_hour = START_HOUR
        self.end_hour = END_HOUR
        self.days_to_show = list(range(5))  # show Mon-Fri by default

        # mapping of drawn rects to info
        self.rect_map = {}

        # bind click
        self.canvas.bind("<Button-1>", self.on_click)

    # ---------- Loading & scheduling ----------
    def load_file(self):
        path = filedialog.askopenfilename(title="Wybierz plik HTML", filetypes=[("HTML files", "*.html;*.htm")])
        if not path:
            return
        self._load_and_generate(path)

    def load_profile(self):
        path_json = filedialog.askopenfilename(title="Otwórz profil JSON", filetypes=[("JSON files", "*json")])
        if not path_json:
            return
        try:
            self.profile = Weights.load(path_json)
            messagebox.showinfo("Profil wczytany")
        except Exception as e:
            messagebox.showerror("Błąd")        

    def _load_and_generate(self, path):
        try:
            courses = parse_html_plan(path)   # parse_html_plan returns List[Course]. See parser.py. :contentReference[oaicite:10]{index=10}
        except Exception as e:
            messagebox.showerror("Błąd parsowania", str(e))
            return

        # create scheduler and generate plans (uses your Scheduler implementation)
        try:
            scheduler = Scheduler(courses)
            plans = scheduler.generate_plans()
        except Exception as e:
            messagebox.showerror("Błąd generowania planów", str(e))
            return

        # evaluate & sort using your Evaluate
        w = self.profile

        evaluator = Evaluate(plans)
        evaluator.sort_plans(plans, w)   # sorts in place. See eval.py. :contentReference[oaicite:11]{index=11}

        self.plans = plans
        self.current_index = 0

        # adjust timetable range (find min start and max end across first plan to better fit)
        if plans:
            min_start = min((slot.start for p in plans for g in p.selected_groups.values() for slot in g.slots), default=self.start_hour*60)
            max_end = max((slot.end for p in plans for g in p.selected_groups.values() for slot in g.slots), default=self.end_hour*60)
            # round to hours
            self.start_hour = max(0, min(self.start_hour, min_start // 60))
            self.end_hour = max(self.end_hour, (math.ceil(max_end / 60)))
        else:
            self.start_hour = START_HOUR
            self.end_hour = END_HOUR

        self.update_ui_after_load(path)

    def update_ui_after_load(self, path):
        pname = os.path.basename(path)
        self.info_label.config(text=f"Plik: {pname}")
        self.plan_index_label.config(text=f"Plan {self.current_index+1} / {len(self.plans)}")
        if not self.plans:
            self.canvas.delete("all")
            self.details.delete(1.0, tk.END)
            return
        self.draw_current_plan()

    # ---------- Navigation ----------
    def prev_plan(self):
        if not self.plans:
            return
        self.current_index = max(0, self.current_index - 1)
        self.plan_index_label.config(text=f"Plan {self.current_index+1} / {len(self.plans)}")
        self.draw_current_plan()

    def next_plan(self):
        if not self.plans:
            return
        self.current_index = min(len(self.plans)-1, self.current_index + 1)
        self.plan_index_label.config(text=f"Plan {self.current_index+1} / {len(self.plans)}")
        self.draw_current_plan()

    # ---------- Drawing ----------
    def draw_current_plan(self):
        self.canvas.delete("all")
        self.rect_map.clear()
        plan = self.plans[self.current_index]

        # layout calculations
        days = self.days_to_show
        num_days = len(days)
        avail_w = CANVAS_WIDTH - LEFT_COL_WIDTH - (num_days-1)*DAY_COL_GAP - 20
        day_w = avail_w / num_days
        hour_span = self.end_hour - self.start_hour
        pixels_per_minute = (CANVAS_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN) / (hour_span * 60)

        # draw hour lines & labels on left
        for h in range(self.start_hour, self.end_hour+1):
            y = TOP_MARGIN + (h - self.start_hour) * 60 * pixels_per_minute
            # horizontal line
            self.canvas.create_line(LEFT_COL_WIDTH, y, CANVAS_WIDTH-10, y, fill="#eee")
            # hour label
            self.canvas.create_text(LEFT_COL_WIDTH - 8, y+2, text=f"{h}:00", anchor="e")

        # draw day columns & headers
        for i, d in enumerate(days):
            x0 = LEFT_COL_WIDTH + i * (day_w + DAY_COL_GAP)
            x1 = x0 + day_w
            # header
            self.canvas.create_rectangle(x0, 0, x1, TOP_MARGIN, fill="#f0f0f0", outline="#ddd")
            self.canvas.create_text((x0+x1)/2, TOP_MARGIN/2, text=DAY_NAMES[d], font=("TkDefaultFont", 10, "bold"))
            # vertical separator
            self.canvas.create_line(x0, TOP_MARGIN, x0, CANVAS_HEIGHT-BOTTOM_MARGIN, fill="#eee")

        # draw group slots as rectangles
        # map group type -> color index for stable coloring within plan
        type_color = {}
        color_idx = 0

        for cname, group in plan.selected_groups.items():
            gtype = group.type
            if gtype not in type_color:
                type_color[gtype] = COLORS[color_idx % len(COLORS)]
                color_idx += 1
            color = type_color[gtype]

            for slot in group.slots:
                day = slot.day
                if day not in days:
                    continue
                x0 = LEFT_COL_WIDTH + days.index(day) * (day_w + DAY_COL_GAP)
                x1 = x0 + day_w
                # clamp to timetable range
                start_min = max(slot.start, self.start_hour*60)
                end_min = min(slot.end, self.end_hour*60)
                y0 = TOP_MARGIN + (start_min - self.start_hour*60) * pixels_per_minute
                y1 = TOP_MARGIN + (end_min - self.start_hour*60) * pixels_per_minute
                # small padding
                pad = 3
                rect = self.canvas.create_rectangle(x0+pad, y0+pad, x1-pad, y1-pad, fill=color, outline="#666")
                # label text inside
                label = f"{cname}\n{group.key}\n{self._time_str(slot.start)}-{self._time_str(slot.end)}"
                # create text (wrapped by width)
                self.canvas.create_text(x0+6, (y0+y1)/2, anchor="w", text=label, width=day_w-12, font=("TkDefaultFont", 9))
                # store mapping for clicks
                self.rect_map[rect] = {
                    "course": cname,
                    "group": group,
                    "slot": slot,
                    "label": label
                }

        # bounding box right border
        last_x = LEFT_COL_WIDTH + num_days * (day_w + DAY_COL_GAP)
        self.canvas.create_line(last_x, TOP_MARGIN, last_x, CANVAS_HEIGHT-BOTTOM_MARGIN, fill="#ddd")

        # summary in details
        self.details.delete(1.0, tk.END)
        self.details.insert(tk.END, f"Plan {self.current_index+1} / {len(self.plans)}\n")
        self.details.insert(tk.END, f"Kursy: {len(plan.selected_groups)}\n")
        self.details.insert(tk.END, "Kliknij kafelek, by zobaczyć szczegóły zajęć.\n")

    def _time_str(self, minutes:int) -> str:
        h = minutes // 60
        m = minutes % 60
        return f"{h:02d}:{m:02d}"

    # ---------- Interaction ----------
    def on_click(self, event):
        # determine which rect was clicked
        clicked = None
        # canvas.find_overlapping returns ids; pick topmost that is in rect_map
        ids = self.canvas.find_overlapping(event.x, event.y, event.x, event.y)
        for cid in reversed(ids):
            if cid in self.rect_map:
                clicked = self.rect_map[cid]
                break

        if not clicked:
            return

        self.details.delete(1.0, tk.END)
        grp: Group = clicked["group"]
        slot: TimeSlot = clicked["slot"]
        self.details.insert(tk.END, f"Kurs: {clicked['course']}\n")
        self.details.insert(tk.END, f"Grupa: {grp.key}\n")
        self.details.insert(tk.END, f"Dzień: {DAY_NAMES[slot.day]} ({slot.day})\n")
        self.details.insert(tk.END, f"Czas: {self._time_str(slot.start)} - {self._time_str(slot.end)}\n")
        # add all slots of the group
        self.details.insert(tk.END, "\nWszystkie sloty tej grupy:\n")
        for s in grp.slots:
            self.details.insert(tk.END, f" - {DAY_NAMES[s.day]} {self._time_str(s.start)}-{self._time_str(s.end)}\n")


if __name__ == "__main__":
    app = TimetableApp()
    app.mainloop()
