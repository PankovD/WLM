import pandas as pd

def count_rows_in_file(file_path):
    # Повернути кількість рядків у CSV чи Excel
    ext = file_path.lower().split('.')[-1]
    if ext in ('csv', 'txt'):
        df = pd.read_csv(file_path)
    elif ext in ('xls', 'xlsx'):
        df = pd.read_excel(file_path)
    else:
        raise ValueError("Unsupported file format")
    return len(df)


# Можна додати допоміжні функції для запису CSV/Excel