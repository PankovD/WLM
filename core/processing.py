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
from .column_resolver import resolve_column
from requests.exceptions import RequestException
from openpyxl import Workbook
from .constants import CONFIGURED_FILE, DEFAULT_FILE
from .network import get_token, is_blocked, wait_for_connection
from .config import OUTPUT_ID_CSV
import csv
import pandas as pd

def get_column_defs():
    if not os.path.exists(CONFIGURED_FILE):
        with open(DEFAULT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        with open(CONFIGURED_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    

    

not_found = 0
def collect_ids(id_queue, excel_queue, selected_file, upc_col, price_col, column_names, status=None):
    token = None
    global not_found
    lines = 0

    # Отримання OAuth токена
    token = get_token()
    column_defs = get_column_defs()
    infile = None
    writer_file = open(OUTPUT_ID_CSV, 'w', newline='', encoding='utf-8')
    try:
        writer = csv.writer(writer_file)
        writer.writerow(['UPC', 'ItemID', 'Price'] + column_names)
        writer_file.flush()
        os.fsync(writer_file.fileno())

        if selected_file.lower().endswith('.csv'):
            infile = open(selected_file, 'r', encoding='utf-8', errors='replace')
            reader = csv.reader(infile)
            iterator = reader
            try:
                next(iterator)
            except StopIteration:
                pass
        else:
            df_upc = pd.read_excel(selected_file, dtype=str).fillna('')
            iterator = df_upc.itertuples(index=False, name=None)

        for row in iterator:
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

            for _ in range(3):
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

            if item_id:
                writer.writerow([trial_upc, item_id, price] + row)
                logging.info(f"Found ID {item_id} for UPC {original_upc}")
                id_queue.put((item_id, original))
            else:
                writer.writerow([original_upc, 'Not Found', price] + row)
                with total_rows_lock:
                    global not_found
                    not_found += 1
                if status:
                    status['not_found'] += 1
                logging.warning(f"UPC {original_upc} not found after 3 retries")

                headers = [col['header'] for col in column_defs] + column_names
                notfound_row_data = {}
                for col in column_defs:
                    if col['header'] == 'Product ID':
                        notfound_row_data[col['header']] = 'Not Found'
                    else:
                        notfound_row_data[col['header']] = ''
                for col in column_names:
                    notfound_row_data[col] = original.get(col, '')
                notfound_row = [notfound_row_data.get(h, '') for h in headers]
                excel_queue.put(notfound_row)

            writer_file.flush()
            os.fsync(writer_file.fileno())

            lines += 1
            if lines >= 199:
                token = get_token()
                lines = 0
    finally:
        writer_file.close()
        if infile is not None:
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
# result_header = [
#     'Store Page', 'Catalog Page', 'Product Title', 'Product ID',
#     'Selling Price', 'Active Sellers', 'Ratings', 'Average Rating',
#     'Current Seller', 'UPC', 'PRICE'
# ]

wb = Workbook()
ws = wb.active

total_rows_written = 0
blocks = 0
total_rows_lock = threading.Lock()

def writer_worker(excel_queue, file_write_lock, results_file, column_names, progress_queue=None, status=None):
    global total_rows_written
    column_defs = get_column_defs()
    headers = [col['header'] for col in column_defs] + column_names
    UPC_INDEX = headers.index("UPC")
    ws.append(headers)
    wb.save(results_file)
    while True:
        row = excel_queue.get()
        if row is None:
            excel_queue.task_done()
            break
        with file_write_lock:
            upc = row[UPC_INDEX] if len(row) > UPC_INDEX else "N/A"
            ws.append(row)
            wb.save(results_file)
            with total_rows_lock:
                total_rows_written += 1
                if status is not None:
                    status['total_rows_written'] = total_rows_written
                if progress_queue:
                    progress_queue.put(1)
                logging.info(f"Total rows written: {total_rows_written}")
            logging.info(f"Row {upc} written to Excel.")
            
        excel_queue.task_done()
    
    if progress_queue:
        progress_queue.put(None)

# ------------------- Original consumer -------------------
def consumer_worker(id_queue, excel_queue, column_names):
    h_index = 0
    blocks = 0
    column_defs = get_column_defs()
    with httpx.Client(http2=True, timeout=10) as client:
        while True:
            raw = id_queue.get()
            if raw is None:                   # Sentinel: завершуємо воркер
                id_queue.task_done()
                break

            product_id, original = raw
            success = False
            blocked = False

            # ↓ Винесемо product_url назовні, щоб можна було його перезаписати
            product_url = f'https://www.walmart.com/ip/{product_id}?redirect=false'

            for _ in range(3):
                try:
                    r = client.get(product_url,
                                   headers=BASE_HEADERS[h_index],
                                   follow_redirects=False)
                except httpx.RequestError:
                    wait_for_connection()
                    continue  # йдемо до наступної спроби із поточним product_url

                # Якщо побачили блокування — повертаємо в чергу і виходимо
                if is_blocked(r):
                    blocks += 1
                    logging.warning(
                        f"Blocked for UPC {original.get('UPC','')}, re-enqueueing once"
                    )
                    id_queue.task_done()
                    id_queue.put((product_id, original))
                    time.sleep(180)
                    blocked = True
                    break

                # Якщо статус 301/302/… — поновлюємо product_url на поточну Location та пробуємо ще раз
                if r.status_code in (301, 302, 303, 307, 308):
                    # ↓ тут беремо зворот URL із заголовка іще раз запитом
                    new_location = r.headers.get("Location")
                    if new_location:
                        # Якщо Location видається відносним, додаємо домен вручну
                        product_url = urljoin("https://www.walmart.com", new_location)
                    continue  # переходимо до наступного attempt уже з оновленим product_url

                if r.status_code != 200:
                    continue  # жодної дії, просто спроба неуспішна, але без редиректу

                # ↓ УСПІШНО отримали HTML, переходимо до парсингу
                sel = Selector(text=r.text)
                data_str = sel.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
                if not data_str:
                    continue
                data_json = json.loads(data_str)
                prod = (
                    data_json.get("props", {})
                              .get("pageProps", {})
                              .get("initialData", {})
                              .get("data", {})
                              .get("product", {})
                )
                if not prod:
                    continue

                idml = (
                    data_json.get("props", {})
                              .get("pageProps", {})
                              .get("initialData", {})
                              .get("data", {})
                              .get("idml", {})
                )
                if not idml:
                    continue
                data_sources = {
                    'product': prod,
                    'prod': prod,
                    'idml': idml,
                    'original': original,
                    'product_url': product_url.replace("?redirect=false", ""),
                    'current': prod.get('priceInfo', {}).get('currentPrice', {})
                }

                row_data = {
                    **{col['header']: resolve_column(col, data_sources) for col in column_defs},
                    **{col: original.get(col, '') for col in column_names}
                }

                headers = [col['header'] for col in column_defs] + column_names
                row = [
                    json.dumps(value) if isinstance(value, (list, dict)) else value
                    for value in [row_data.get(h, '') for h in headers]
                ]
                excel_queue.put(row)

                success = True
                break

            if blocked:
                continue

            if success:
                id_queue.task_done()
                continue

            logging.error(f"Failed to process item {product_id} after 3 attempts")
            id_queue.task_done()

