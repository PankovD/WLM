import tkinter as tk
from tkinter import ttk, filedialog
import pandas as pd
import time
import os
import ctypes
from queue import Empty

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # DPI-aware
except Exception:
    pass


def choose_mode():
    mode = {'value': None}
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

    s = ttk.Style()
    s.theme_use('alt')
    s.configure('Custom.TButton',
                font=('Cascadia Code', 10, 'bold'),
                background="#4BAE00",
                foreground='white',
                padding=(10, 10))
    s.map('Custom.TButton',
        background=[('active', "#0D3D8A")],  # при наведенні
        foreground=[('active', 'white')])
    
    btn_upc = ttk.Button(container, text="UPC/EAN", width = 20, style='Custom.TButton', command=lambda: set_and_close('upc'))
    btn_id = ttk.Button(container, text="ID", width = 20, style='Custom.TButton', command=lambda: set_and_close('id'))

    # btn_upc = tk.Button(container, text="UPC/EAN", bg="#4CAF50", fg="white", font=('Cascadia Code', 10, 'bold'), command=lambda: set_and_close('upc'))
    # btn_id = tk.Button(container, text="ID", bg="#2196F3", fg="white", font=('Cascadia Code', 10, 'bold'), command=lambda: set_and_close('id'))


    btn_upc.pack(pady=5, ipady=3)
    btn_id.pack(pady=5, ipady=3)

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
    width, height = 500, 250
    column_window.update_idletasks()
    screen_width = column_window.winfo_screenwidth()
    screen_height = column_window.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    column_window.geometry(f"{width}x{height}+{x}+{y}")
    column_names = df.columns.tolist()
    label_text = "Select the column that contains Item ID:" if id_mode else "Select the column that contains UPC/EAN:"
    tk.Label(column_window, text=label_text,font=("Segoe UI", 11, "bold")).pack(pady=10)
    id_dropdown = ttk.Combobox(column_window, values=column_names)
    id_dropdown.pack(pady=5)
    id_dropdown.current(0)
    tk.Label(column_window, text="Select the column that contains Price (optional):",font=("Segoe UI", 11)).pack(pady=5)
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

    s = ttk.Style(column_window)
    s.theme_use('clam')
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
                progress_queue.get_nowait()
                processed_count += 1
        except Empty:
            pass

        progressbar['value'] = processed_count
        progress_label.config(text=f"{processed_count} / {total_count} items processed")
        
        elapsed_seconds = time.time() - start_time
        timer_label.config(text=f"Total runtime: {format_elapsed(elapsed_seconds)}")

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
    ttk.Button(container, text="Finish", width = 20, style='Custom.TButton', command=close).pack(pady=(10, 0))


    win.bind('<Return>', lambda e: close())
    win.bind('<Escape>', lambda e: close())

    win.mainloop()
