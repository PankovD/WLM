import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import time
import os
import ctypes
from queue import Empty
import json
import sys
import subprocess
from .auth import delete_account_rpc, change_password_rpc, load_credentials, SUPABASE_KEY, SUPABASE_URL, CREDENTIALS_FILE
from .constants import COLUMNS_FILE, CONFIGURED_FILE, DEFAULT_FILE, APP_NAME
import keyring
from PIL import Image, ImageTk
import threading

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # DPI-aware
except Exception:
    pass
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(__file__)


class ColumnConfigWindow:
    def __init__(self, master):
        self.master = master

        # дані
        self.available_columns = self._load_json(COLUMNS_FILE)
        if not os.path.exists(CONFIGURED_FILE):
            self.selected_columns = self._load_json(DEFAULT_FILE)
        else:
            self.selected_columns  = self._load_json(CONFIGURED_FILE)
        
        self.dragging_index = None

        # UI
        self._build_ui()
        self._refresh()

    def _load_json(self, fn):
        if not os.path.exists(fn): return []
        try:
            with open(fn, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    def _build_ui(self):
        frm = tk.Frame(self.master, bg='white', padx=10, pady=10)
        frm.pack(fill='both', expand=True)

        title_font = ("Arial", 12, "bold")

        # — Available Columns
        lf = tk.LabelFrame(frm, text="Available Columns", bg='white', font=title_font)
        lf.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        self.avail_sb = tk.Scrollbar(lf, orient='vertical')
        self.avail_lb = tk.Listbox(lf, yscrollcommand=self.avail_sb.set, width=30, height=20)
        self.avail_sb.config(command=self.avail_lb.yview)
        self.avail_lb.pack(side='left', fill='both', expand=True)
        self.avail_sb.pack(side='right', fill='y')

        # Центр: Add / Remove
        cf = tk.Frame(frm, bg='white')
        cf.pack(side='left', padx=5, pady=5)
        ttk.Button(cf, text="→", style='OtherConf.TButton', command=self._add).pack(pady=10)
        ttk.Button(cf, text="←", style='OtherConf.TButton', command=self._remove).pack(pady=10)

        # — Selected Columns
        rf = tk.LabelFrame(frm, text="Selected Columns", background='white', font=title_font)
        rf.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        self.sel_sb = tk.Scrollbar(rf, orient='vertical')
        self.sel_lb = tk.Listbox(rf, yscrollcommand=self.sel_sb.set, width=30, height=20)
        self.sel_sb.config(command=self.sel_lb.yview)
        self.sel_lb.pack(side='left', fill='both', expand=True)
        self.sel_sb.pack(side='right', fill='y')

        # drag & drop
        self.sel_lb.bind('<Button-1>',     self._on_drag_start)
        self.sel_lb.bind('<B1-Motion>',    self._on_drag_motion)
        self.sel_lb.bind('<ButtonRelease-1>', self._on_drag_drop)

        # Up/Down для Selected

        ttk.Button(cf, text="↑ Up",   style='OtherConf.TButton', command=self.move_up).pack(side='left', padx=3)
        ttk.Button(cf, text="↓ Down", style='OtherConf.TButton', command=self.move_down).pack(side='left', padx=3)

        # Bottom
        bf = tk.Frame(self.master, bg='white')
        bf.pack(fill='x', pady=10)
        ttk.Button(bf, text="Set to Default", style='Def.TButton',  command=self._set_default).pack(side='left', padx=5)
        ttk.Button(bf, text="Save",           style='Save.TButton', command=self._save).pack(side='left', padx=5)
        ttk.Button(bf, text="Cancel",         style='ExitConf.TButton', command=self.master.destroy).pack(side='right', padx=5)

    def _refresh(self):
        self.avail_lb.delete(0, tk.END)
        self.sel_lb.delete(0, tk.END)

        used = {c['header'] for c in self.selected_columns}
        for c in self.available_columns:
            if c['header'] not in used:
                self.avail_lb.insert(tk.END, c['header'])
        for c in self.selected_columns:
            self.sel_lb.insert(tk.END, c['header'])

    def _add(self):
        sel = self.avail_lb.curselection()
        if not sel: return
        hdr = self.avail_lb.get(sel[0])
        for c in self.available_columns:
            if c['header']==hdr:
                self.selected_columns.append(c)
                break
        self._refresh()

    def _remove(self):
        sel = self.sel_lb.curselection()
        if not sel: return
        self.selected_columns.pop(sel[0])
        self._refresh()

    def move_up(self):
        sel = self.sel_lb.curselection()
        if not sel or sel[0]==0: return
        i = sel[0]
        self.selected_columns[i-1], self.selected_columns[i] = self.selected_columns[i], self.selected_columns[i-1]
        self._refresh()
        self.sel_lb.select_set(i-1)

    def move_down(self):
        sel = self.sel_lb.curselection()
        if not sel or sel[0]>=len(self.selected_columns)-1: return
        i = sel[0]
        self.selected_columns[i], self.selected_columns[i+1] = self.selected_columns[i+1], self.selected_columns[i]
        self._refresh()
        self.sel_lb.select_set(i+1)

    def _set_default(self):
        if not os.path.exists(DEFAULT_FILE):
            messagebox.showerror("Error", "default_columns.json not found")
            return
        self.selected_columns = self._load_json(DEFAULT_FILE)
        self._refresh()

    def _save(self):
        try:
            with open(CONFIGURED_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.selected_columns, f, indent=2, ensure_ascii=False)
            self.master.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Save failed: {e}")

    # Drag & Drop реалізація
    def _on_drag_start(self, ev):
        self.dragging_index = self.sel_lb.nearest(ev.y)
    def _on_drag_motion(self, ev):
        tgt = self.sel_lb.nearest(ev.y)
        self.sel_lb.selection_clear(0, tk.END)
        self.sel_lb.selection_set(tgt)
    def _on_drag_drop(self, ev):
        tgt = self.sel_lb.nearest(ev.y)
        if self.dragging_index is None or tgt==self.dragging_index: return
        self.selected_columns.insert(tgt, self.selected_columns.pop(self.dragging_index))
        self._refresh()
        self.sel_lb.select_set(tgt)
        self.dragging_index = None

def restart_program():
    if getattr(sys, 'frozen', False):
        executable = sys.executable
        # Обгортаємо шлях до виконуваного файлу в лапки
        args = [f'"{executable}"']
    else:
        script = os.path.abspath(sys.argv[0])
        executable = sys.executable
        # Обгортаємо скрипт у лапки, також executable теж
        args = [f'"{executable}"', f'"{script}"'] + sys.argv[1:]

    os.execv(executable, args)

    
def clear_credentials(username):
    if os.path.exists(CREDENTIALS_FILE):
        os.remove(CREDENTIALS_FILE)
    try:
        keyring.delete_password(APP_NAME, username)
    except Exception:
        pass

def get_version():
    try:
        base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
        version_file = os.path.join(base_dir, 'version.json')
        with open(version_file, 'r') as f:
            return json.load(f).get('version', 'Unknown')
    except Exception:
        return 'Unknown'
    
def choose_mode(current_user=None):
    mode = {'value': None}

    info_win_ref = {'window': None}
    set_win_ref = {'window': None}
    pw_win_ref = {'window': None}
    columns_config_ref = {'window': None}

    win = tk.Tk()
    win.title("Walmart Parser")
    win.resizable(False, False)
    win.attributes('-topmost', True)
    if not current_user:
        user_from_file = load_credentials()
        current_user = user_from_file
    width, height = 500, 500
    win.update_idletasks()
    screen_width = win.winfo_screenwidth()
    screen_height = win.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    win.geometry(f"{width}x{height}+{x}+{y}")
    
    s = ttk.Style()
    s.theme_use('alt')

    # s.configure('Custom.TButton',
    #             font=('Cascadia Code', 10, 'bold'),
    #             background="#0069E1",
    #             foreground='white',
    #             relief='flat',
    #             padding=(10, 6))
    # s.map('Custom.TButton',
    #     background=[('active', "#0092E1")],  # при наведенні
    #     foreground=[('active', 'white')],
    #     relief=[('active', 'flat')])  # при наведенні
    
    s.configure('Custom.TButton',
                font=('Cascadia Code', 10, 'bold'),
                background="#00B460",
                foreground='white',
                relief='flat',
                padding=(10, 6))
    s.map('Custom.TButton',
        background=[('active', "#00C468")],  # при наведенні
        foreground=[('active', 'white')],
        relief=[('active', 'flat')])  # при наведенні
  

    s.configure('FlatInfo.TButton',
        font=('Calibri', 15, 'bold'),
        background='white',
        foreground='#0066CC',
        borderwidth=0,
        relief='flat',
        padding=2)
    s.map('FlatInfo.TButton',
        background=[('active', 'white')],
        foreground=[('active', '#004C99')],
        bordercolor=[('active', '#004C99')])

    s.configure('Exit.TButton',
                font=('Cascadia Code', 10, 'bold'),
                background="#FF3737",
                relief='flat',
                foreground='white',
                padding=(10, 0))
    s.map('Exit.TButton',
        background=[('active', "#FF4949")],  # при наведенні
        foreground=[('active', 'white')],
        relief=[('active','flat')])
    

    #------settings buttons style------

    s.configure('Other.TButton',
        font=('Cascadia Code', 10, 'bold'),
        background="#00B460",
        relief='flat',
        foreground='white',
        padding=(5, 0))
    s.map('Other.TButton',
        background=[('active', "#00C468")],  # при наведенні
        foreground=[('active', 'white')],
        relief=[('active', 'flat')])  # при наведенні
    
    s.configure('Delete.TButton',
        font=('Cascadia Code', 10, 'bold'),
        background='white',
        foreground='#FF3737',
        borderwidth=0,
        relief='flat',
        padding=(2, 0))
    s.map('Delete.TButton',
        background=[('active', 'white')],
        foreground=[('active', '#FF4949')],
        bordercolor=[('active', '#FF4949')])
    
    container = tk.Frame(win, bg='white', padx=20, pady=20)
    container.pack(expand=True, fill='both')

    
    logo_frame = tk.Frame(container, bg='white')
    logo_frame.pack(pady=(10, 20))

    inner = tk.Frame(logo_frame, bg='white')
    inner.pack()

    logo_image_path = os.path.join(base_dir, "walmart.ico")  # або абсолютний шлях
    img = Image.open(logo_image_path).resize((32, 32), Image.LANCZOS)
    logo_img = ImageTk.PhotoImage(img, master=win)

    logo_label = ttk.Label(inner, image=logo_img, font=("Segoe UI Emoji", 24), background='white')
    logo_label.image = logo_img
    logo_label.pack(side='left')


    title_label = ttk.Label(inner, text="Walmart Parser", font=("Segoe UI", 16, "bold"), background='white')
    title_label.pack(side='left', padx=10)

    tk.Frame(container, width=410, height=10, bg='white').pack(pady=(30, 0))

    head = ttk.Label(container, text="Choose search mode", font=("Segoe UI", 14, "bold"), background='white')
    head.pack(pady=(0, 15))
    lbl = ttk.Label(container, text="Search by:", font=("Segoe UI", 12), background='white')
    lbl.pack(pady=(0, 15))

    def set_and_close(selection):
        mode['value'] = selection
        win.destroy()

    # def app_exit():
    #     win.destroy()
    #     os._exit(0)

    def show_info_window():
        if info_win_ref['window'] and info_win_ref['window'].winfo_exists():
            info_win_ref['window'].lift()
            info_win_ref['window'].focus_force()
            return
        info_win = tk.Toplevel(win)
        info_win_ref['window'] = info_win
        info_win.title("Program Info")
        #info_win.geometry("400x250")
        info_win.resizable(False, False)
        info_win.attributes('-topmost', True)

        info_frame = tk.Frame(info_win, bg='white', padx=20, pady=20)
        info_frame.pack(expand=True, fill='both')
        version = get_version()
        label_text = (
            "This program is designed to search for products on Walmart using UPC/EAN or Item ID. \n"
            "To use the program, select the search mode, choose a file (Excel or CSV(UTF-8)) with the relevant data, and specify the columns containing the search key and price (optional).\n\n"
            "After finishing the search, you can view a summary of the results, including the number of items processed, not found items, and total time taken.\n"
        )
        ttk.Label(info_frame, text="Walmart Parser", font=("Segoe UI", 14, "bold"), background="white").pack(pady=(0, 10))
        ttk.Label(info_frame, text=f"Version: {version}", font=("Segoe UI", 11), background="white").pack()
        tk.Label(info_frame, text=label_text, wraplength=380, justify="left", bg="white", font=("Segoe UI", 10)).pack(pady=(10))
        
        def on_close():
            info_win_ref['window'] = None  # очищаємо посилання
            info_win.destroy()
        ttk.Button(info_frame, text="Close", style='Exit.TButton', command=on_close).pack(pady=20)

    button_row = tk.Frame(container, bg='white')
    button_row.pack(pady=10)

    def fixed_button(parent, text, command):
        frame = tk.Frame(parent, width=200, height=70, bg='white')
        frame.pack_propagate(False)  # не дозволяє вмісту змінювати розмір
        frame.pack(side='left', padx=5)

        btn = ttk.Button(frame, text=text, style='Custom.TButton', command=command)
        btn.pack(fill='both', expand=True, pady=5)

        return btn
    
    def app_exit():
        win.destroy()
        win.quit()
        os._exit(0)

    btn_upc = fixed_button(button_row, "UPC/EAN", lambda: set_and_close('upc'))
    btn_id  = fixed_button(button_row, "Item ID", lambda: set_and_close('id'))

    btn_info = ttk.Button(container, text="ℹ", width= 3, style='FlatInfo.TButton', command=show_info_window)
    btn_info.place(relx=1.0, x=-10, y=45, anchor='ne')
    
    tk.Frame(container, width=410, height=15, bg='white').pack(pady=(30, 5))  # Порожній відступ
    
    exit_frame = tk.Frame(container, width=410, height=50, bg='white')  # 200 + 200 + відступ
    exit_frame.pack_propagate(False)
    exit_frame.pack(pady=(30, 20))
      # Порожній відступ
    btn_exit = ttk.Button(exit_frame, text="Exit program", style='Exit.TButton', command=app_exit)
    btn_exit.pack(fill='both', expand=True)
    
    def open_column_configurator():
        if columns_config_ref['window'] and columns_config_ref['window'].winfo_exists():
            columns_config_ref['window'].lift()
            columns_config_ref['window'].focus_force()
            return

        # Відкриваємо нове вікно
        col_win = tk.Toplevel()
        columns_config_ref['window'] = col_win
        col_win.title("Configure Columns")
        col_win.geometry("800x700")
        col_win.attributes('-topmost', True)
        # col_win.grab_set()  # але блокує інші вікна поки відкрито це
        s = ttk.Style(col_win)
        s.theme_use('alt')
        s.configure(
            'Save.TButton',
            font=('Cascadia Code', 10, 'bold'),
            background="#00B460",
            foreground='white',
            relief='flat',
            padding=(8, 5)
        )
        s.map(
            'Save.TButton',
            background=[('active', "#00C468")],  # при наведенні
            foreground=[('active', 'white')],
            relief=[('active', 'flat')]
        )
        s.configure(
            'Def.TButton',
            font=('Cascadia Code', 10, 'bold'),
            background="#0068EF",
            foreground='white',
            relief='flat',
            padding=(8, 5)
        )
        s.map(
            'Def.TButton',
            background=[('active', "#2483FF")],  # при наведенні
            foreground=[('active', 'white')],
            relief=[('active', 'flat')]
        )
        s.configure(
            'ExitConf.TButton',
            font=('Cascadia Code', 10, 'bold'),
            background="#FF3737",
            relief='flat',
            foreground='white',
            padding=(8, 5)
        )
        s.map(
            'ExitConf.TButton',
            background=[('active', "#FF4949")],  # при наведенні
            foreground=[('active', 'white')],
            relief=[('active','flat')]
        )
        s.configure('OtherConf.TButton',
            font=('Cascadia Code', 8, 'bold'),
            background="#ECECEC",
            relief='flat',
            foreground='#333333',
            padding=(0, 0))
        s.map('OtherConf.TButton',
            background=[('active', "#CDECFF")],  # при наведенні
            foreground=[('active', '#333333')],
            relief=[('active', 'flat')])

        app = ColumnConfigWindow(col_win)

    def open_settings():

        if set_win_ref['window'] and set_win_ref['window'].winfo_exists():
            set_win_ref['window'].lift()
            set_win_ref['window'].focus_force()
            return
        set_win = tk.Toplevel(win)
        set_win_ref['window'] = set_win
        set_win.title("Settings")
        set_win.geometry("400x350")
        set_win.resizable(False, False)
        set_win.attributes('-topmost', True)

        set_frame = tk.Frame(set_win, bg='white', padx=20, pady=20)
        set_frame.pack(expand=True, fill='both')
        ttk.Button(set_frame, text="Configure Columns", style='Other.TButton', command=open_column_configurator).pack(pady=5, fill='x')
        tk.Frame(set_frame, height=30, bg='white').pack(pady=(5, 0))
        ttk.Button(set_frame, text="Change Password",  style='Other.TButton', command=change_password_dialog).pack(pady=5, fill='x')
        tk.Frame(set_frame, height=30, bg='white').pack(pady=(5, 0))  # Порожній відступ

        bottom_frame = tk.Frame(set_frame, bg='white')
        bottom_frame.pack(side='bottom', fill='x', pady=(5, 5))  # 5 пікселів від дна
        ttk.Button(bottom_frame, text="Delete Account", style='Delete.TButton', command=delete_account_dialog).pack(pady=5, fill='x')
        ttk.Button(bottom_frame, text="Close", style='Exit.TButton', command=set_win.destroy).pack(fill='x')

        # ttk.Button(set_frame, text="Delete Account",   style='Delete.TButton', command=delete_account_dialog).pack(pady=5, fill='x')
        # close_btn = ttk.Button(set_frame, text="Close",style='Exit.TButton', command=set_win.destroy)
        # close_btn.place(relx=0.5, rely=1.0, anchor='s', y=-2)
    
    settings_btn =ttk.Button(container, text="🛠", style='FlatInfo.TButton', width=3, command=open_settings)
    settings_btn.place(relx=1.0, x=-10, y=10, anchor='ne')

    def delete_account_dialog():
        if pw_win_ref['window'] and pw_win_ref['window'].winfo_exists():
            pw_win_ref['window'].lift()
            pw_win_ref['window'].focus_force()
            return
        dlg = tk.Toplevel(win)
        pw_win_ref['window'] = dlg
        dlg.title("Delete Account")
        dlg.geometry("350x200")
        dlg.resizable(False, False)
        dlg.attributes('-topmost', True)

        dlg_frame = tk.Frame(dlg, bg='white', padx=20, pady=20)
        dlg_frame.pack(expand=True, fill='both')

        tk.Label(dlg_frame, text="Confirm your password to delete account:", bg='white').pack(pady=(10,5))
        pwd_var = tk.StringVar()
        ttk.Entry(dlg_frame, textvariable=pwd_var, show="*").pack(pady=5)

        def on_confirm_delete():
            pwd = pwd_var.get()
            ok, msg = delete_account_rpc(current_user, pwd)
            if ok:
                clear_credentials(current_user)
                messagebox.showinfo("Deleted","Your account has been deleted.")
                dlg.destroy()
                win.destroy()
                restart_program()
            else:
                messagebox.showerror("Error", msg)

        ttk.Button(dlg_frame, text="Confirm Delete", style='Exit.TButton', command=on_confirm_delete).pack(pady=15)

    def change_password_dialog():
        if pw_win_ref['window'] and pw_win_ref['window'].winfo_exists():
            pw_win_ref['window'].lift()
            pw_win_ref['window'].focus_force()
            return
        dlg = tk.Toplevel(win)
        pw_win_ref['window'] = dlg
        dlg.title("Change Password")
        dlg.geometry("350x320")
        dlg.resizable(False, False)
        dlg.attributes('-topmost', True)

        dlg_frame = tk.Frame(dlg, bg='white', padx=20, pady=20)
        dlg_frame.pack(expand=True, fill='both')

        tk.Label(dlg_frame, text="Old Password:", bg='white').pack(pady=(10,0))
        old_var = tk.StringVar()
        ttk.Entry(dlg_frame, textvariable=old_var, show="*").pack(pady=5)

        tk.Label(dlg_frame, text="New Password:", bg='white').pack(pady=(10,0))
        new_var = tk.StringVar()
        ttk.Entry(dlg_frame, textvariable=new_var, show="*").pack(pady=5)

        tk.Label(dlg_frame, text="Confirm new Password:", bg='white').pack(pady=(10,0))
        conf_new_var = tk.StringVar()
        ttk.Entry(dlg_frame, textvariable=conf_new_var, show="*").pack(pady=5)

        def on_confirm_change():
            if new_var.get() == conf_new_var.get():
                ok, msg = change_password_rpc(current_user, old_var.get(), new_var.get())
                if ok:
                    # оновлюємо в keyring
                    keyring.set_password(APP_NAME, current_user, new_var.get())
                    messagebox.showinfo("Success","Password changed successfully.")
                    dlg.destroy()
                else:
                    messagebox.showerror("Error", msg)
            else:
                messagebox.showerror("Error", "New passwords do not match.")

        ttk.Button(dlg_frame, text="Confirm Change", style='Other.TButton', command=on_confirm_change).pack(pady=15)
        
    win.bind('<Return>', lambda e: set_and_close('upc'))
    win.bind('<Escape>', lambda e: win.destroy())

    win.mainloop()
    return mode['value']

def count_rows_in_file(file_path):
    ext = file_path.lower().split('.')[-1]
    if ext in ('csv', 'txt'):
        df = pd.read_csv(file_path)
    elif ext in ('xls', 'xlsx'):
        df = pd.read_excel(file_path)
    else:
        raise ValueError("Unsupported file format")
    return len(df)

# ------------------- Вікно вибору файлу та колонок -------------------
def choose_file_and_columns(id_mode=False):
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select a file",
        filetypes=[("Excel files", "*.xlsx;*.xls"), ("CSV files", "*.csv"), ("All files", "*.*")]
    )
    if not file_path:
        return None, None, None, None, None
        
    
    df = pd.read_csv(file_path, dtype=str) if file_path.endswith('.csv') else pd.read_excel(file_path, dtype=str)
    total_rows = count_rows_in_file(file_path)
    column_window = tk.Tk()
    column_window.title("Select Columns")
    column_window.resizable(False, False)
    column_window.attributes('-topmost', True)
    column_window.configure(bg='white')
    width, height = 500, 250
    column_window.update_idletasks()
    screen_width = column_window.winfo_screenwidth()
    screen_height = column_window.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    column_window.geometry(f"{width}x{height}+{x}+{y}")
    column_names = df.columns.tolist()
    
    s = ttk.Style(column_window)
    s.theme_use('clam')
    s.configure(
        'White.TLabel',
        background='white',
        font=('Segoe UI', 11)
    )
    s.configure(
        'WhiteBold.TLabel',
        background='white',
        font=('Segoe UI', 11, 'bold')
    )

    label_text = "Select the column that contains Item ID:" if id_mode else "Select the column that contains UPC/EAN:"
    ttk.Label(column_window, text=label_text,style=("WhiteBold.TLabel")).pack(pady=10)
    id_dropdown = ttk.Combobox(column_window, values=column_names)
    id_dropdown.pack(pady=5)
    id_dropdown.current(0)
    ttk.Label(column_window, text="Select the column that contains Price (optional):",style=("White.TLabel")).pack(pady=5)
    price_dropdown = ttk.Combobox(column_window, values=["<None>"] + column_names)
    price_dropdown.pack(pady=5)
    price_dropdown.current(0)
    selected_id = tk.StringVar()
    selected_price = tk.StringVar()
    def on_select():
        selected_id.set(id_dropdown.get())
        selected_price.set(price_dropdown.get() if price_dropdown.get() != "<None>" else None)
        column_window.quit()
        column_window.destroy()

    s.configure('Custom.TButton',
                font=('Cascadia Code', 10, 'bold'),
                background="#00B32A",
                foreground='white',
                padding=(10, 10))
    s.map('Custom.TButton',
        background=[('active', "#009723")],  # при наведенні
        foreground=[('active', 'white')])
    ttk.Button(column_window, text="Start", width = 20, style='Custom.TButton', command=on_select).pack(pady=10)
    
    def on_close():
        column_window.destroy()
        os._exit(0)
    column_window.protocol("WM_DELETE_WINDOW", on_close)
    column_window.bind('<Escape>', lambda e: on_close())
    column_window.bind('<Return>', lambda e: on_close())

    column_window.mainloop()
    return file_path, selected_id.get(), selected_price.get(), column_names, total_rows


def show_progress_bar(total_count, progress_queue, finish_callback):
    root = tk.Tk()
    root.title("Processing Progress")
    root.geometry("400x230")
    root.resizable(False, False)
    root.attributes('-topmost', True)

    s = ttk.Style(root)
    s.theme_use('clam')

    s.configure(
        'Exit.TButton',
        font=('Cascadia Code', 10, 'bold'),
        background="#FF3737",
        relief='flat',
        foreground='white',
        padding=(10, 0)
    )
    s.map(
        'Exit.TButton',
        background=[('active', "#FF4949")],  # при наведенні
        foreground=[('active', 'white')],
        relief=[('active','flat')]
    )
    s.configure(
        'Green.Horizontal.TProgressbar',      # ім’я нового стилю
        troughcolor='white',                  # колір фону (канавки)
        background='#4CAF50',                 # колір заповненого сегменту (зелений)
        thickness=20                          # висота смужки (за бажанням)
    )

    container = tk.Frame(root, bg='white', padx=20, pady=20)
    container.pack(expand=True, fill='both')


    label = ttk.Label(container, text="Processing items...", background='white', font=("Segoe UI", 12))
    label.pack(pady=10)

    progressbar = ttk.Progressbar(container, style='Green.Horizontal.TProgressbar', orient='horizontal', length=350, mode='determinate')
    progressbar.pack(pady=10)
    progressbar['maximum'] = total_count
    progressbar['value'] = 0

    progress_label = ttk.Label(container, text=f"0 / {total_count} items processed", background='white', font=("Segoe UI", 10))
    progress_label.pack()

    timer_label = ttk.Label(container, text="Total runtime: 00:00:00",background='white', font=("Segoe UI", 10))
    timer_label.pack(pady=(5, 5))
    start_time = time.time()

    def format_elapsed(seconds):
        h, rem = divmod(int(seconds), 3600)
        m, s = divmod(rem, 60)
        return f"{h:02}:{m:02}:{s:02}"

    processed_count = 0

    def check_queue():
        nonlocal processed_count
        try:
            while True:
                item = progress_queue.get_nowait()
                progress_queue.task_done()
                # Якщо отримали None — це фінальний сигнал
                if item is None:
                    root.destroy()
                    finish_callback()
                    return
                # Інакше item має бути 1 (крок прогресу)
                processed_count += item
        except Empty:
            pass

        progressbar['value'] = processed_count
        progress_label.config(text=f"{processed_count} / {total_count} items processed")

        elapsed_seconds = time.time() - start_time
        timer_label.config(text=f"Total runtime: {format_elapsed(elapsed_seconds)}")
        # Якщо вже досягли або перевищили total_count, завершити
        if processed_count >= total_count:
            root.destroy()
            finish_callback()
        else:
            root.after(100, check_queue)
    ttk.Button(container, text="Cancel", style='Exit.TButton', command=restart_program).pack(pady=(10, 0))
    def on_close():
        root.destroy()
        os._exit(0)
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.bind('<Escape>', lambda e: on_close())
    root.bind('<Return>', lambda e: on_close())

    root.after(100, check_queue)
    root.mainloop()

#-------------------- Показати підсумок роботи програми -------------------

def show_summary(total_rows_written, time_str, results_file, blocks, not_found):
    win = tk.Tk()
    win.title("Process Completed")
    win.resizable(False, False)
    win.attributes('-topmost', True)

    width, height = 400, 300
    win.update_idletasks()
    screen_width = win.winfo_screenwidth()
    screen_height = win.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    win.geometry(f"{width}x{height}+{x}+{y}")

    container = tk.Frame(win, bg='white', padx=20, pady=20)
    container.pack(expand=True, fill='both')
    
    style = ttk.Style(win)
    style.theme_use('clam')
    style.configure(
        'White.TLabel',
        background='white',
        font=('Segoe UI', 12)
    )
    style.configure(
        'WhiteBold.TLabel',
        background='white',
        font=('Segoe UI', 12, 'bold')
    )

    msg1 = ttk.Label(container, text="Program finished.", style='WhiteBold.TLabel')
    msg2 = ttk.Label(container, text=f"{total_rows_written} items processed.", style='White.TLabel')
    msg3 = ttk.Label(container, text=f"Not found: {not_found} items.", style='White.TLabel')
    msg4 = ttk.Label(container, text=f"Total time taken: {time_str}", style='White.TLabel')
    # msg5 = ttk.Label(container, text=f"Total blocks: {blocks}", style='White.TLabel')
    
    msg1.pack(pady=(0, 10))
    msg2.pack()
    msg3.pack()
    msg4.pack(pady=(0, 10))
    # msg5.pack(pady=(0, 10))

    def close():
        win.quit()
        win.after(10, os._exit, 0)
    
    def on_restart():
        win.destroy()
        restart_program()

    s = ttk.Style(win)
    s.theme_use('clam')
    s.configure('Custom.TButton',
                font=('Cascadia Code', 10, 'bold'),
                background="#00B32A",
                foreground='white',
                padding=(10, 10))
    s.map('Custom.TButton',
        background=[('active', "#009723")],  # при наведенні
        foreground=[('active', 'white')])
    ttk.Button(container, text="Finish", width = 20, style='Custom.TButton', command=on_restart).pack(pady=(10, 0))


    win.bind('<Return>', lambda e: close())
    win.bind('<Escape>', lambda e: close())

    win.mainloop()
