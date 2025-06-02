import threading
import time
import os
import json
import logging
import requests
import httpx
from urllib.parse import urljoin
from scrapy.selector import Selector
from .constants import BASE_HEADERS
from requests.exceptions import RequestException
from queue import Queue
from openpyxl import Workbook
from .constants import RESULT_HEADER
from .network import get_token, is_blocked, random_sleep, wait_for_connection
from .config import OUTPUT_ID_CSV
import csv
import pandas as pd

not_found = 0
def collect_ids(id_queue, excel_queue, selected_file, upc_col, price_col, column_names, status=None):
    token = None
    global not_found
    lines = 0

    # Отримання OAuth токена
    token = get_token()

    # Підготовка writer для результатів
    writer_file = open(OUTPUT_ID_CSV, 'w', newline='', encoding='utf-8')
    writer = csv.writer(writer_file)
    writer.writerow(['UPC', 'ItemID', 'Price'] + column_names)
    writer_file.flush()
    os.fsync(writer_file.fileno())

    # Відкриваємо файл з UPC або Excel залежно від розширення
    if selected_file.lower().endswith('.csv'):
        infile = open(selected_file, 'r', encoding='utf-8', errors='replace')
        reader = csv.reader(infile)
        iterator = reader
        # Пропускаємо заголовок CSV
        try:
            next(iterator)
        except StopIteration:
            pass
    else:
        # Для .xlsx/.xls читаємо через pandas, приводимо всі значення до рядків
        df_upc = pd.read_excel(selected_file, dtype=str).fillna('')
        iterator = df_upc.itertuples(index=False, name=None)

    # Обробка кожного рядка
    for row in iterator:
        # Перетворюємо всі елементи рядка у рядки, щоб уникнути float
        row = [str(cell) for cell in row]
        original_upc = row[column_names.index(upc_col)].strip()
        if original_upc.startswith('0'):
            trial_upc = original_upc
            _trial_upc = original_upc.lstrip('0')
        else:
            trial_upc = '0' + original_upc
            _trial_upc = original_upc

        price = row[column_names.index(price_col)] if price_col else ''
        item_id = None

        # Пошук через API з трьома спробами
        for attempt in range(3):
            try:
                url = f"https://marketplace.walmartapis.com/v3/items/walmart/search?query={trial_upc}"
                h = {
                    "WM_SEC.ACCESS_TOKEN": token,
                    "Accept": "application/json",
                    "WM_SVC.NAME": "Walmart Marketplace",
                    "WM_QOS.CORRELATION_ID": "1234567890"
                }
                r = requests.get(url, headers=h, timeout=10)
            except RequestException as e:
                logging.error(f"Network error for UPC {original_upc}: {e}")
                wait_for_connection()
                continue
            if r.status_code == 200:
                data = r.json()
                if data.get('items'):
                    item_id = data['items'][0]['itemId']
            if item_id:
                break
            else:
                trial_upc = '0' + trial_upc

        # Додаткова спроба без ведучого нуля
        if not item_id:
            try:
                url = f"https://marketplace.walmartapis.com/v3/items/walmart/search?query={_trial_upc}"
                h = {
                    "WM_SEC.ACCESS_TOKEN": token,
                    "Accept": "application/json",
                    "WM_SVC.NAME": "Walmart Marketplace",
                    "WM_QOS.CORRELATION_ID": "1234567890"
                }
                r = requests.get(url, headers=h, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    if data.get('items'):
                        item_id = data['items'][0]['itemId']
            except RequestException as e:
                logging.error(f"Network error for UPC {original_upc}: {e}")
                wait_for_connection()

        original = dict(zip(column_names, row))
        original['UPC'], original['Price'] = original_upc, price

        # Запис результату
        if item_id:
            writer.writerow([trial_upc, item_id, price] + row)
            logging.info(f"Found ID {item_id} for UPC {original_upc}")
            id_queue.put((item_id, original))
        else:
            writer.writerow([original_upc, 'Not Found', price] + row)
            not_found += 1
            status['not_found'] += 1 if status else 0
            logging.warning(f"UPC {original_upc} not found after 3 retries")
            notfound_row = [
                '', '', '', 'Not Found', '', '', '', '', '', original_upc, price
            ] + [original.get(col, '') for col in column_names]
            excel_queue.put(notfound_row)

        writer_file.flush()
        os.fsync(writer_file.fileno())

        lines += 1
        if lines >= 199:
            # Оновлюємо токен
            token = get_token()
            lines = 0

    # Закінчили — сповіщаємо споживачів

    id_queue.put(None)

    # Закриваємо файли
    writer_file.close()
    if selected_file.lower().endswith('.csv'):
        infile.close()


# ------------------- Producer: Збір із файлу по ID -------------------
def load_ids_from_file(id_queue, selected_file, id_col, price_col, column_names):
    df_local = pd.read_csv(selected_file, dtype=str) if selected_file.endswith('.csv') else pd.read_excel(selected_file, dtype=str)
    for _, row in df_local.iterrows():
        product_id = row[id_col]
        price = row[price_col] if price_col else ""
        original = dict(zip(column_names, row.tolist()))
        original['Price'] = price
        id_queue.put((product_id, original))
    
    id_queue.put(None)

# ------------------- Writer: Запис рядків у Excel -------------------
result_header = [
    'Store Page', 'Catalog Page', 'Product Title', 'Product ID',
    'Selling Price', 'Active Sellers', 'Ratings', 'Average Rating',
    'Current Seller', 'UPC', 'PRICE'
]
wb = Workbook()
ws = wb.active

total_rows_written = 0
blocks = 0
total_rows_lock = threading.Lock()

def writer_worker(excel_queue, file_write_lock, results_file, column_names, progress_queue=None, status=None):
    global total_rows_written
    ws.append(RESULT_HEADER + column_names)
    wb.save(results_file)
    while True:
        row = excel_queue.get()
        if row is None:
            excel_queue.task_done()
            break
        with file_write_lock:
            ws.append(row)
            wb.save(results_file)
            with total_rows_lock:
                total_rows_written += 1
                if status is not None:
                    status['total_rows_written'] = total_rows_written
                if progress_queue:
                    progress_queue.put(1)
                print(f"\rTotal rows written: {total_rows_written}", end="", flush=True)
            logging.info("Row written to Excel.")
            
        excel_queue.task_done()

# ------------------- Consumer: Парсинг сторінок -------------------
def consumer_worker(id_queue, excel_queue, column_names, results_file, status=None):
    h_index = 0
    blocks = 0

    with httpx.Client(http2=True, timeout=10) as client:
        while True:
            raw = id_queue.get()
            if raw is None:                   # Sentinel: завершуємо воркер
                id_queue.task_done()
                break

            product_id, original = raw
            product_url = f'https://www.walmart.com/ip/{product_id}?redirect=false'
            success = False

            for attempt in range(3):
                try:
                    r = client.get(product_url,
                                   headers=BASE_HEADERS[h_index],
                                   follow_redirects=False)
                except httpx.RequestError:
                    wait_for_connection()
                    continue

                # Якщо побачили блокування — перекидаємо назад в чергу й йдемо до наступного
                if is_blocked(r):
                    blocks += 1
                    logging.warning(
                        f"Blocked for UPC {original.get('UPC','')}, re-enqueueing once"
                    )
                    id_queue.put((product_id, original))
                    id_queue.task_done()
                    time.sleep(180)    # “охолоджування”
                    break             # вихід із for — повернемося до while, щоб взяти наступний item

                # Обробка редиректів
                if r.status_code in (301, 302, 303, 307, 308):
                    product_url = urljoin("https://www.walmart.com",
                                          r.headers.get("Location"))
                    continue

                if r.status_code != 200:
                    continue

                # Якщо дійшли сюди — успішно завантажили і можемо парсити
                sel = Selector(text=r.text)
                data_str = sel.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
                if not data_str:
                    continue
                data_json = json.loads(data_str)
                prod = (data_json.get("props", {})
                             .get("pageProps", {})
                             .get("initialData", {})
                             .get("data", {})
                             .get("product", {}))
                if not prod:
                    continue

                # Формуємо рядок у excel_queue
                price_info = prod.get('priceInfo') or {}
                current = price_info.get('currentPrice') or {}
                row_data = {
                    'Store Page': product_url,
                    'Catalog Page': f"https://seller.walmart.com/catalog/add-items?search={original.get('UPC','')}",
                    'Product Title': prod.get('name'),
                    'Product ID': prod.get('usItemId'),
                    'Selling Price': current.get('price'),
                    'Active Sellers': prod.get('transactableOfferCount'),
                    'Ratings': prod.get('numberOfReviews'),
                    'Average Rating': prod.get('averageRating'),
                    'Current Seller': prod.get('sellerName'),
                    'UPC': original.get('UPC',''),
                    'PRICE': original.get('Price',''),
                    **{col: original.get(col,'') for col in column_names}
                }
                row = [row_data.get(h, '') for h in result_header + column_names]
                excel_queue.put(row)

                success = True
                break  # вийшли з attempts

            # Якщо вдалося — відзначаємо виконання task_done і йдемо далі
            if success:
                id_queue.task_done()
                continue

            # Якщо не успішно (після 3 спроб без блокування) — лог і task_done
            logging.error(f"Failed to process item {product_id} after 3 attempts")
            id_queue.task_done()

    logging.info(f"Consumer finished; total blocks: {blocks}")