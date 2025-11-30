import os
import math
import tkinter as tk
from tkinter import ttk
from ttkbootstrap import Style
from tkinter import filedialog, messagebox
from parser import parse_html_plan    # parses timetable entries from HTML. See parser.py. :contentReference[oaicite:6]{index=6}
from scheduler import Scheduler
from eval import Evaluate            # scoring & conflict detection. See eval.py. :contentReference[oaicite:7]{index=7}
from models import TimeSlot, Group, Course, Schedule  # datamodels. :contentReference[oaicite:8]{index=8}
from weights import Weights, Preferences


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


# KOLORY DEFULT
COLORS = [
    "#2d4f73",  # ciemny niebieski / slate blue
    "#735d2d",  # brązowo-złoty, przygaszony
    "#2d7350",  # ciemna zieleń teal
    "#733f3f",  # ciemny, wypłowiały czerwony
    "#4b3f73",  # ciemny fiolet
    "#73662d",  # złoto-brązowy, nienachalny
    "#734963",  # śliwkowy, stonowany róż
    "#2d6b73",  # przygaszony cyjan / dark teal
    "#73502d",  # ciemny pomarańcz / rust
    "#3f7341",  # ciemna zieleń mech
]


#KOLORY RÓŻOWE (dodaj style "superhero")
# COLORS = [
#     "#6d3a5a",  # głęboka śliwka
#     "#814262",  # burgund z fioletem
#     "#9a4f70",  # malinowy, ale przygaszony
#     "#b1647d",  # ciepły róż z fioletem
#     "#c47a8c",  # brudny róż, pastelowy
#     "#d097a9",  # jasny, pudrowy róż-fiolet
#     "#b79acb",  # chłodny wrzos (dla zróżnicowania)
#     "#a07bbd",  # spokojna lawenda
#     "#8c63a8",  # ciemny pastelowy fiolet
#     "#734b8e",  # głęboki fiolet, elegancki
# ]





class PreferencesPanel(tk.LabelFrame):
    def __init__(self, master, weights: Weights, preferences: Preferences, courses, on_apply_callback):
        super().__init__(master, text="Preferencje oceny", padx=10, pady=10)
        self.weights = weights
        self.preferences = preferences
        self.on_apply_callback = on_apply_callback
        self.vars = {}
        self.style = Style(theme='solar')
        self.courses = courses

        fields = [
            ("Waga okienek", "weight_gaps"),
            ("Waga późnego końca", "weight_late_end"),
            ("Waga wolnych dni", "weight_days_free"),
            ("Waga pojedyńczych zajęć w ciągu dnia", "weight_single_object")
        ]

        row = 0
        tk.Label(self, text = "Bez kolizji z wykładami").grid(row=row, column=0, sticky="w")
        varBool = tk.IntVar()
        check = tk.Checkbutton(self, variable=varBool, onvalue=999999, offvalue=0)
        check.grid(row=row, column=1, sticky = "w")
        
        self.vars["weight_conflicts"] = varBool
        row = 1
        for label, attr in fields:
            tk.Label(self, text=label).grid(row=row, column=0, sticky="w")
            var = tk.IntVar(value=getattr(weights, attr))
            tk.Scale(self, 
                     variable=var, 
                     orient = tk.HORIZONTAL,
                     activebackground="#f9cb9c",
                     bd=3,

                     ).grid(row=row, column=1, sticky="w")
            self.vars[attr] = var
            row += 1

        tk.Label(self, text="Preferowane godziny początku i końca zajęć (Pon–Pią):").grid(row=row, column=0, columnspan=2, pady=(10,0))
        row += 1

        self.start_vars = []
        self.end_vars = []
        for d in range(5):
            vs = tk.IntVar(value=weights.start[d] if weights.start[d] is not None else 0)
            ve = tk.IntVar(value=weights.end[d] if weights.end[d] is not None else 0)
            tk.Label(self, text=["Pon","Wto","Śro","Czw","Pią"][d]).grid(row=row, column=0, sticky="w")
            tk.Entry(self, textvariable=vs, width=6).grid(row=row, column=1, sticky="w")
            tk.Entry(self, textvariable=ve, width=6).grid(row=row, column=2, sticky="w")
            self.start_vars.append(vs)
            self.end_vars.append(ve)
            row += 1
        
        self.free_days_vars = []
    
        tk.Label(self, text="Preferowane dni wolne:").grid(row=row, column=0, columnspan=2, pady=(10,0))
        row += 1
        for d in range(5):
            free_day = tk.IntVar()
            tk.Label(self, text=["Pon","Wto","Śro","Czw","Pią"][d]).grid(row=row, column=0, sticky="w")
            tk.Checkbutton(self, variable=free_day, onvalue=1, offvalue=0).grid(row = row, column = 1, sticky="w")
            self.free_days_vars.append(free_day)
            row += 1
        
        row += 1
        
        self.choices_by_course = {}
        
        if self.courses is not None:
            tk.Label(self, text="Preferowane grupy").grid(row=row, column=0, columnspan=2, pady=(10,0))
            row += 1
            for c in self.courses:
                c.groups.sort(key=lambda g: g.key.lower())
            for c in self.courses:
                tk.Label(self,text=c.name).grid(row=row, column=0, sticky="w")
                # row+=1
                menubutton = tk.Menubutton(self)
                menu = tk.Menu(menubutton, tearoff=False)
                menubutton.configure(menu=menu)
                menubutton.grid(row=row, column=2, pady=(10,0), sticky="w")
                self.choices = {}
                for group in c.groups:
                    self.choices[group.key] = tk.IntVar(value=0)
                    menu.add_checkbutton(label=group.key, variable=self.choices[group.key], onvalue=1, offvalue=0)
                row+=1
                self.choices_by_course[c.name] = self.choices
        
        #PROFILE JSON - DO PÓŹNIEJSZEJ IMPLEMENTACJI
        # tk.Button(self, text="Zapisz profil JSON", command=self.save_profile).grid(row=row, column=0, pady=10)
        # tk.Button(self, text="Wczytaj profil JSON", command=self.load_profile).grid(row=row, column=1)
        # row += 1

        tk.Button(self, text="Zastosuj", command=self.apply).grid(row=row, column=0, columnspan=2, pady=10)

    # === AKCJE ===
    def apply(self):
        for attr, var in self.vars.items():
            setattr(self.weights, attr, var.get())
        for d in range(5):
            self.weights.start[d] = int(self.start_vars[d].get()) or None
            self.weights.end[d] = int(self.end_vars[d].get()) or None
            self.preferences.free_days[d] = int(self.free_days_vars[d].get()) or None
        
        if self.preferences.required_groups is None:
            self.preferences.required_groups = {}

        for cname, groups in self.choices_by_course.items():
            self.preferences.required_groups.setdefault(cname, {})
            for key, value in groups.items():
                self.preferences.required_groups[cname][key] = int(value.get())

        if self.on_apply_callback:
            self.on_apply_callback()

    # PROFILE JSON - DO WDROŻENIA
    # def save_profile(self):
    #     path = filedialog.asksaveasfilename(defaultextension=".json")
    #     if not path:
    #         return
    #     self.apply()
    #     self.weights.save(path)
    #     messagebox.showinfo("OK", "Zapisano profil.")

    # def load_profile(self):
    #     path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
    #     if not path:
    #         return
    #     try:
    #         neww = Weights.load(path)
    #         self.weights.__dict__.update(neww.__dict__)
    #         self.refresh()
    #         messagebox.showinfo("OK", "Wczytano profil.")
    #     except Exception as e:
    #         messagebox.showerror("Błąd", str(e))

    def refresh(self):
        for attr, var in self.vars.items():
            var.set(getattr(self.weights, attr))
        for d in range(5):
            self.start_vars[d].set(self.weights.start[d] if self.weights.start[d] else 0)
            self.end_vars[d].set(self.weights.end[d] if self.weights.end[d] else 0)
            self.free_days_vars[d].set(self.preferences.free_days[d] if self.preferences.free_days[d] else None)



class TimetableApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.profile = Weights()
        self.preferences = Preferences()
        self.title("Generator planów — Siatka godzinowa")
        self.geometry(f"{CANVAS_WIDTH+40}x{CANVAS_HEIGHT+140}")
        self.style = Style(theme='solar')
        # top controls
        ctrl = tk.Frame(self)
        ctrl.pack(padx=8, pady=6, anchor="w")
        # panel preferencji – po prawej
        self.prefs_frame = tk.Frame(self)
        self.prefs_frame.pack(side="right", padx=10, pady=10, anchor="n")
        self.pref_panel = PreferencesPanel(
            self.prefs_frame,
            self.profile,
            self.preferences,
            None,
            on_apply_callback=self.regenerate_after_preferences
        )
        self.pref_panel.pack()
        # w = self.load_profile
        w = Weights()

        tk.Button(ctrl, text="Wczytaj plik HTML...", command=self.load_file).pack(side="left", padx=4)

        self.info_label = tk.Label(ctrl, text="Brak załadowanego planu")
        self.info_label.pack(side="left", padx=10)

        nav = tk.Frame(self)
        nav.pack(padx=8, pady=4, anchor="w")

        tk.Button(nav, text="<< Poprzedni", command=self.prev_plan).pack(side="left", padx=4)
        tk.Button(nav, text="Następny >>", command=self.next_plan).pack(side="left", padx=4)
        self.plan_index_label = tk.Label(nav, text="Plan 0 / 0")
        self.plan_index_label.pack(side="left", padx=8)

        
        self.canvas = tk.Canvas(self, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="white")
        self.canvas.pack(padx=10, pady=6)

       
        self.details = tk.Text(self, height=6)
        self.details.pack(fill="x", padx=10, pady=(0,10))

        self.plans = []           
        self.sorted_plans = []
        self.current_index = 0
        self.start_hour = START_HOUR
        self.end_hour = END_HOUR
        self.days_to_show = list(range(5))  

        self.rect_map = {}

        self.canvas.bind("<Button-1>", self.on_click)

    def regenerate_after_preferences(self):
        if not hasattr(self, "courses_loaded") or not self.courses_loaded:
            return

        scheduler = Scheduler(self.courses_loaded, self.preferences, self.profile)
        plans = scheduler.generate_plans()
        if not plans:
            messagebox.showerror("Brak planów", "Żaden plan nie spełnia nowych preferencji.")
            return

        evaluator = Evaluate(plans)
        evaluator.sort_plans(plans, self.profile)

        self.plans = plans
        self.current_index = 0
        self.draw_current_plan()
        self.plan_index_label.config(text=f"Plan {self.current_index+1} / {len(self.plans)}")

    def recompute_sorted_plans(self):
        if not self.plans:
            return
        evaluator = Evaluate(self.plans)
        evaluator.sort_plans(self.plans, self.profile)
        self.current_index = 0
        self.draw_current_plan()
        self.plan_index_label.config(text=f"Plan {self.current_index+1} / {len(self.plans)}")

    def load_file(self):
        path = filedialog.askopenfilename(title="Wybierz plik HTML", filetypes=[("HTML files", "*.html;*.htm")])
        if not path:
            return
        for d in range(5):
            self.preferences.free_days[d] = None
        self._load_and_generate(path)

    # PROFIL JSON DO PÓŹNIEJSZEJ IMPLEMENTACJI
    # def load_profile(self):
    #     path_json = filedialog.askopenfilename(title="Otwórz profil JSON", filetypes=[("JSON files", "*json")])
    #     if not path_json:
    #         return
    #     try:
    #         self.profile = Weights.load(path_json)
    #         messagebox.showinfo("Profil wczytany")
    #     except Exception as e:
    #         messagebox.showerror("Błąd")        

    def _load_and_generate(self, path):
        try:
            courses = parse_html_plan(path)  
            self.courses_loaded = courses
            self.pref_panel.destroy()
            self.pref_panel = PreferencesPanel(
            self.prefs_frame,
            self.profile,
            self.preferences,
            courses,
            on_apply_callback=self.regenerate_after_preferences
            )
            self.pref_panel.pack()
        except Exception as e:
            messagebox.showerror("Błąd parsowania", str(e))
            return
    
        try:
            scheduler = Scheduler(courses, self.preferences, self.profile)
            plans = scheduler.generate_plans()
            if len(plans) == 0:
                messagebox.showerror("Błąd", "Brak planów zgodnych z preferencjami")
                return
        except Exception as e:
            messagebox.showerror("Błąd generowania planów", str(e))
            return

        w = self.profile
        evaluator = Evaluate(plans)
        evaluator.sort_plans(plans, w)   

        self.plans = plans
        self.current_index = 0

        if plans:
            min_start = min((slot.start for p in plans for g in p.selected_groups.values() for slot in g.slots), default=self.start_hour*60)
            max_end = max((slot.end for p in plans for g in p.selected_groups.values() for slot in g.slots), default=self.end_hour*60)

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

    def _assign_columns(self, events):
        events.sort(key=lambda e: (e['slot'].start, e['slot'].end))
        columns = []  
        for ev in events:
            placed = False
            for ci, col in enumerate(columns):
                last = col[-1]['slot']
                if last.end <= ev['slot'].start:
                    col.append(ev)
                    ev['col'] = ci
                    placed = True
                    break
            if not placed:
                columns.append([ev])
                ev['col'] = len(columns) - 1

        col_count = len(columns) if columns else 1
        for col in columns:
            for ev in col:
                ev['col_count'] = col_count

        return events

    def draw_current_plan(self):
        self.canvas.delete("all")
        self.rect_map.clear()
        plan = self.plans[self.current_index]
        self.style = Style(theme='solar')

        days = self.days_to_show
        num_days = len(days)
        avail_w = CANVAS_WIDTH - LEFT_COL_WIDTH - (num_days-1)*DAY_COL_GAP - 20
        day_w = avail_w / num_days
        hour_span = self.end_hour - self.start_hour
        pixels_per_minute = (CANVAS_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN) / (hour_span * 60)

        for h in range(self.start_hour, self.end_hour+1):
            y = TOP_MARGIN + (h - self.start_hour) * 60 * pixels_per_minute
            self.canvas.create_line(
                LEFT_COL_WIDTH, y, 
                CANVAS_WIDTH-10, y,
                fill="white"
            )
            self.canvas.create_text(
                LEFT_COL_WIDTH - 8, y + 2, 
                text=f"{h}:00", anchor="e",
                fill="white"
            )

        day_x0 = {}
        for i, d in enumerate(days):
            x0 = LEFT_COL_WIDTH + i * (day_w + DAY_COL_GAP)
            x1 = x0 + day_w
            day_x0[d] = (x0, x1)

            # prostokąt nagłówka
            self.canvas.create_rectangle(x0, 0, x1, TOP_MARGIN, fill="white")
            # nazwa dnia
            self.canvas.create_text((x0+x1)/2, TOP_MARGIN/2, text=DAY_NAMES[d], fill="black")
            # pionowa linia oddzielająca kolumny
            self.canvas.create_line(
                x0, TOP_MARGIN,
                x0, CANVAS_HEIGHT - BOTTOM_MARGIN,
                fill="white"
            )


        slots_per_day = {d: [] for d in days}


        for cname, group in plan.selected_groups.items():
            for slot in group.slots:
                if slot.day in days:
                    slots_per_day[slot.day].append({
                        "course": cname,
                        "group": group,
                        "slot": slot
                    })

        # --- Kolory dla typów grup
        type_color = {}
        color_idx = 0

        # --- Rysowanie wydarzeń ---
        for d in days:
            events = slots_per_day[d]
            if not events:
                continue

            self._assign_columns(events)

            x0_day, x1_day = day_x0[d]
            full_width = x1_day - x0_day
            inner_gap = 6

            for ev in events:
                group = ev["group"]
                slot = ev["slot"]
                cname = ev["course"]
                gtype = group.type

                # przydzielenie koloru dla typu
                if gtype not in type_color:
                    type_color[gtype] = COLORS[color_idx % len(COLORS)]
                    color_idx += 1
                color = type_color[gtype]

                col_idx = ev.get("col", 0)
                col_count = ev.get("col_count", 1)

                col_w = (full_width - (col_count-1) * inner_gap) / col_count

                x0 = x0_day + col_idx * (col_w + inner_gap)
                x1 = x0 + col_w

                start_min = max(slot.start, self.start_hour * 60)
                end_min = min(slot.end, self.end_hour * 60)

                y0 = TOP_MARGIN + (start_min - self.start_hour*60) * pixels_per_minute
                y1 = TOP_MARGIN + (end_min - self.start_hour*60) * pixels_per_minute

    
                rect = self.canvas.create_rectangle(
                    x0 + 3, y0 + 3,
                    x1 - 3, y1 - 3,
                    fill=color
                )

                max_w = max(10, col_w - 12)
                max_h = max(6, (y1 - y0) - 8)
                
                # skracamy tylko nazwę kursu (cname)
                base_name = cname.split("-")[0].strip()
                short_name = self.shorten_text(base_name, max_w, max_h)

                raw_label = (
                    f"{short_name}\n"
                    f"{group.key}\n"
                    f"{self._time_str(slot.start)}-{self._time_str(slot.end)}"
                )

                # zmierz wysokość etykiety
                tid = self.canvas.create_text(0, 0, text=raw_label, anchor="nw", font=("TkDefaultFont", 9))
                bbox = self.canvas.bbox(tid)
                self.canvas.delete(tid)

                label = raw_label

                if bbox:
                    h = bbox[3] - bbox[1]
                    if h > max_h:
                        # usuń godzinę jeśli tekst za wysoki
                        label = f"{short_name}\n{group.key}"

                text_x = x0 + 6
                text_width = max(10, col_w - 12)

                self.canvas.create_text(
                    text_x, (y0+y1)/2,
                    anchor="w",
                    text=label,
                    width=text_width,
                    fill="white"
                )

                self.rect_map[rect] = {
                    "course": cname,
                    "group": group,
                    "slot": slot,
                    "label": label
                }

    def shorten_text(self, text, max_width, max_height, font=("TkDefaultFont", 9)):
            """Przycina tekst do max_width pikseli, dodając ... jeśli trzeba."""
            tid = self.canvas.create_text(0, 0, text=text, anchor="nw", font=font)
            bbox = self.canvas.bbox(tid)
            self.canvas.delete(tid)

            if not bbox:
                return text  # fallback

            x0, y0, x1, y1 = bbox
            width = x1 - x0
            height = y1 - y0

            if width <= max_width and height <= max_height:
                return text

            candidate = text

            # przycinamy od końca
            for i in range(len(text), 1, -1):
                candidate = text[:i] + "..."
                tid = self.canvas.create_text(0, 0, text=candidate, anchor="nw", font=font)
                bbox2 = self.canvas.bbox(tid)
                self.canvas.delete(tid)

                if not bbox2:
                    continue

                x0, y0, x1, y1 = bbox2
                width2 = x1 - x0
                height2 = y1 - y0

                if width2 <= max_width and height2 <= max_height:
                    return candidate
                    
                if height2 > max_height:
                    lines = candidate.split("\n")
                    if len(lines) > 1:
                        candidate = "\n".join(lines[:-1])
                        text = candidate
                        continue

            return candidate


    def _time_str(self, minutes:int) -> str:
        h = minutes // 60
        m = minutes % 60
        return f"{h:02d}:{m:02d}"

    def on_click(self, event):
        
        clicked = None
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
        self.details.insert(tk.END, "\nWszystkie sloty tej grupy:\n")
        for s in grp.slots:
            self.details.insert(tk.END, f" - {DAY_NAMES[s.day]} {self._time_str(s.start)}-{self._time_str(s.end)}\n")


if __name__ == "__main__":
    app = TimetableApp()
    app.mainloop()
