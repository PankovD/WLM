import tkinter as tk
from tkinter import ttk, filedialog
import pandas as pd
import time
import os
import ctypes
from queue import Empty
import json
import sys
import subprocess

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # DPI-aware
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
    
def choose_mode():
    mode = {'value': None}
    info_win_ref = {'window': None}
    win = tk.Tk()
    win.title("Select Mode")
    win.resizable(False, False)
    win.attributes('-topmost', True)

    width, height = 500, 400
    win.update_idletasks()
    screen_width = win.winfo_screenwidth()
    screen_height = win.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    win.geometry(f"{width}x{height}+{x}+{y}")

    container = tk.Frame(win, bg='white', padx=20, pady=20)
    container.pack(expand=True, fill='both')

    head = ttk.Label(container, text="Choose search mode", font=("Segoe UI", 14, "bold"), background='white')
    head.pack(pady=(0, 15))
    lbl = ttk.Label(container, text="Search by:", font=("Segoe UI", 12), background='white')
    lbl.pack(pady=(0, 15))

    def set_and_close(selection):
        mode['value'] = selection
        win.destroy()
    
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
        ttk.Button(info_frame, text="Close", command=on_close).pack(pady=20)

    s = ttk.Style()
    s.theme_use('alt')
    s.configure('Custom.TButton',
                font=('Cascadia Code', 10, 'bold'),
                background="#0069E1",
                foreground='white',
                padding=(10, 10))
    s.map('Custom.TButton',
        background=[('active', "#0092E1")],  # при наведенні
        foreground=[('active', 'white')])
        
    s.configure('FlatInfo.TButton',
        font=('Segoe UI', 10, 'bold'),
        background='white',
        foreground='#0066CC',
        borderwidth=1,
        relief='solid',
        padding=(6, 4)
    )

    s.map('FlatInfo.TButton',
        background=[('active', 'white')],
        foreground=[('active', '#004C99')],
        bordercolor=[('active', '#004C99')]
    )
    
    btn_upc = ttk.Button(container, text="UPC/EAN", width = 20, style='Custom.TButton', command=lambda: set_and_close('upc'))
    btn_id = ttk.Button(container, text="Item ID", width = 20, style='Custom.TButton', command=lambda: set_and_close('id'))
    btn_info = ttk.Button(container, text="ℹ Info", width=20, style='FlatInfo.TButton', command=show_info_window)
    # btn_upc = tk.Button(container, text="UPC/EAN", bg="#4CAF50", fg="white", font=('Cascadia Code', 10, 'bold'), command=lambda: set_and_close('upc'))
    # btn_id = tk.Button(container, text="ID", bg="#2196F3", fg="white", font=('Cascadia Code', 10, 'bold'), command=lambda: set_and_close('id'))


    btn_upc.pack(pady=5, ipady=3)
    btn_id.pack(pady=5, ipady=3)
    btn_info.pack(pady=30)

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
        return None, None, None, None
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
    column_window.mainloop()
    return file_path, selected_id.get(), selected_price.get(), column_names, total_rows


def show_progress_bar(total_count, progress_queue, finish_callback):
    root = tk.Tk()
    root.title("Processing Progress")
    root.geometry("400x170")
    root.resizable(False, False)
    root.attributes('-topmost', True)

    label = ttk.Label(root, text="Processing items...", font=("Segoe UI", 12))
    label.pack(pady=10)

    progressbar = ttk.Progressbar(root, orient='horizontal', length=350, mode='determinate')
    progressbar.pack(pady=10)
    progressbar['maximum'] = total_count
    progressbar['value'] = 0

    progress_label = ttk.Label(root, text=f"0 / {total_count} items processed", font=("Segoe UI", 10))
    progress_label.pack()

    timer_label = ttk.Label(root, text="Total runtime: 00:00:00", font=("Segoe UI", 10))
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
    msg5 = ttk.Label(container, text=f"Total blocks: {blocks}", style='White.TLabel')
    
    msg1.pack(pady=(0, 10))
    msg2.pack()
    msg3.pack()
    msg4.pack()
    msg5.pack(pady=(0, 10))

    def restart_program():
        if getattr(sys, 'frozen', False):
            # Якщо запущено як .exe
            executable = os.path.abspath(sys.executable)
            args = [executable] + sys.argv[1:]
        else:
            # Якщо запущено як скрипт
            executable = os.path.abspath(sys.executable)
            script = os.path.abspath(sys.argv[0])
            args = [executable, script] + sys.argv[1:]
        
        # Використовуємо список аргументів: кожен елемент передається окремо
        subprocess.Popen(args, shell=False)
        sys.exit()





    def close():
        win.quit()
        win.after(10, os._exit, 0)
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
    ttk.Button(container, text="Finish", width = 20, style='Custom.TButton', command=restart_program).pack(pady=(10, 0))


    win.bind('<Return>', lambda e: close())
    win.bind('<Escape>', lambda e: close())

    win.mainloop()
