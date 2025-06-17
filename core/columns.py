import json
import os
import tkinter as tk
from tkinter import ttk
import sys
import ctypes

if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(__file__)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # DPI-aware
except Exception:
    pass

COLUMNS_CONFIG = os.path.join(base_dir, "columns.json")

def load_all_fields(sample_json):
    # отримуємо перелік всіх ключів з обʼєкта product
    return sorted(sample_json.keys())

def load_selected():
    if os.path.exists(COLUMNS_CONFIG):
        return json.load(open(COLUMNS_CONFIG))
    return []

def save_selected(cols):
    json.dump(cols, open(COLUMNS_CONFIG, "w"), indent=2)

def configure_columns(sample_json):
    all_fields = load_all_fields(sample_json)
    selected = load_selected()

    win = tk.Toplevel()
    win.title("Configure Columns")
    win.geometry("600x400")

    # Списки
    left_frame = ttk.Frame(win)
    right_frame = ttk.Frame(win)
    left_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
    right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

    ttk.Label(left_frame, text="Available Fields").pack()
    avail_lb = tk.Listbox(left_frame, selectmode="extended")
    avail_lb.pack(fill="both", expand=True)

    ttk.Label(right_frame, text="Selected Columns").pack()
    sel_lb = tk.Listbox(right_frame, selectmode="extended")
    sel_lb.pack(fill="both", expand=True)

    # Заповнюємо
    for f in all_fields:
        if f not in selected:
            avail_lb.insert("end", f)
    for f in selected:
        sel_lb.insert("end", f)

    # Кнопки між списками
    btn_frame = ttk.Frame(win)
    btn_frame.place(relx=0.45, rely=0.3)
    ttk.Button(btn_frame, text="▶", command=lambda: move(avail_lb, sel_lb)).pack(pady=5)
    ttk.Button(btn_frame, text="◀", command=lambda: move(sel_lb, avail_lb)).pack(pady=5)

    # Up/Down для правого Listbox
    nav_frame = ttk.Frame(right_frame)
    nav_frame.pack(pady=5)
    ttk.Button(nav_frame, text="Up", command=lambda: reorder(sel_lb, -1)).pack(side="left", padx=5)
    ttk.Button(nav_frame, text="Down", command=lambda: reorder(sel_lb, +1)).pack(side="left", padx=5)

    def on_save():
        cols = sel_lb.get(0, "end")
        save_selected(list(cols))
        win.destroy()

    ttk.Button(win, text="Save", command=on_save).pack(side="bottom", pady=10)

    win.grab_set()  # модальне вікно
    win.mainloop()

# допоміжні функції
def move(src: tk.Listbox, dst: tk.Listbox):
    for idx in reversed(src.curselection()):
        val = src.get(idx)
        dst.insert("end", val)
        src.delete(idx)

def reorder(lb: tk.Listbox, direction: int):
    sel = lb.curselection()
    if not sel: return
    idx = sel[0]
    new = idx + direction
    if 0 <= new < lb.size():
        txt = lb.get(idx)
        lb.delete(idx)
        lb.insert(new, txt)
        lb.selection_set(new)