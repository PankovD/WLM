import threading
import time
import os
import json
import logging
import requests
import httpx
from urllib.parse import urljoin, urlparse
from parsel import Selector
from .constants import BASE_HEADERS
from requests.exceptions import RequestException
from queue import Queue
from openpyxl import Workbook
from .constants import CONFIGURED_FILE, DEFAULT_FILE
from .network import get_token, is_blocked, random_sleep, wait_for_connection
from .config import OUTPUT_ID_CSV
import csv
import pandas as pd
import sys

# Shared lock for thread-safe status dict updates across all worker threads
_status_lock = threading.Lock()

def get_column_defs():
    if not os.path.exists(CONFIGURED_FILE):
        with open(DEFAULT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        with open(CONFIGURED_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    

    

# Walmart API: оновлювати токен кожні ~200 запитів
TOKEN_REFRESH_LIMIT = 199
# Пауза після блокування Walmart (секунди)
BLOCK_WAIT_SEC = 180

def collect_ids(id_queue, excel_queue, selected_file, upc_col, price_col, column_names, status=None):
    lines = 0
    token = get_token()
    column_defs = get_column_defs()

    infile = None
    writer_file = open(OUTPUT_ID_CSV, 'w', newline='', encoding='utf-8')
    try:
        writer = csv.writer(writer_file)
        writer.writerow(['UPC', 'ItemID', 'Price'] + column_names)
        writer_file.flush()
        os.fsync(writer_file.fileno())

        # Відкриваємо файл з UPC або Excel залежно від розширення
        if selected_file.lower().endswith('.csv'):
            infile = open(selected_file, 'r', encoding='utf-8', errors='replace')
            iterator = csv.reader(infile)
            try:
                next(iterator)  # пропускаємо заголовок
            except StopIteration:
                pass
        else:
            df_upc = pd.read_excel(selected_file, dtype=str).fillna('')
            iterator = df_upc.itertuples(index=False, name=None)

        api_headers = {
            "Accept": "application/json",
            "WM_SVC.NAME": "Walmart Marketplace",
            "WM_QOS.CORRELATION_ID": "1234567890"
        }

        # Reuse TCP connections for all UPC API requests
        with requests.Session() as session:
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

                # Пошук через API з трьома спробами
                for attempt in range(3):
                    try:
                        url = f"https://marketplace.walmartapis.com/v3/items/walmart/search?query={trial_upc}"
                        h = {**api_headers, "WM_SEC.ACCESS_TOKEN": token}
                        r = session.get(url, headers=h, timeout=10)
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
                        h = {**api_headers, "WM_SEC.ACCESS_TOKEN": token}
                        r = session.get(url, headers=h, timeout=10)
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
                    if status is not None:
                        with _status_lock:
                            status['not_found'] += 1
                    logging.warning(f"UPC {original_upc} not found after 3 retries")

                    hdrs = [col['header'] for col in column_defs] + column_names
                    notfound_row_data = {}
                    for col in column_defs:
                        notfound_row_data[col['header']] = 'Not Found' if col['header'] == 'Product ID' else ''
                    for col in column_names:
                        notfound_row_data[col] = original.get(col, '')
                    excel_queue.put([notfound_row_data.get(h, '') for h in hdrs])

                writer_file.flush()
                os.fsync(writer_file.fileno())

                lines += 1
                if lines >= TOKEN_REFRESH_LIMIT:
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

EXCEL_SAVE_INTERVAL = 10  # зберігати файл кожні N рядків

def writer_worker(excel_queue, file_write_lock, results_file, column_names, progress_queue=None, status=None):
    wb = Workbook()
    ws = wb.active
    total_rows_written = 0
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
            total_rows_written += 1
            should_save = (total_rows_written % EXCEL_SAVE_INTERVAL == 0)
            if progress_queue:
                progress_queue.put(1)
            print(f"\rTotal rows written: {total_rows_written}", end="", flush=True)
            logging.info(f"Row {upc} written to Excel.")
        # Save outside lock to avoid blocking consumers during I/O
        if should_save:
            wb.save(results_file)
        if status is not None:
            with _status_lock:
                status['total_rows_written'] = total_rows_written
        excel_queue.task_done()

    wb.save(results_file)  # фінальний запис залишків
    if progress_queue:
        progress_queue.put(None)

# ------------------- Original consumer -------------------
def consumer_worker(id_queue, excel_queue, column_names, results_file, status=None):
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

            for attempt in range(3):
                try:
                    # ↓ Тепер беремо request саме по product_url (а не щодового формування f-string)
                    r = client.get(product_url,
                                   headers=BASE_HEADERS[h_index],
                                   follow_redirects=False)
                except httpx.RequestError:
                    wait_for_connection()
                    continue  # йдемо до наступної спроби із поточним product_url

                # Якщо побачили блокування — повертаємо в чергу і виходимо
                if is_blocked(r):
                    blocks += 1
                    if status is not None:
                        with _status_lock:
                            status['blocks'] = status.get('blocks', 0) + 1
                    logging.warning(
                        f"Blocked for UPC {original.get('UPC','')}, re-enqueueing once"
                    )
                    id_queue.task_done()
                    id_queue.put((product_id, original))
                    for remaining in range(BLOCK_WAIT_SEC, 0, -10):
                        logging.info(f"Block cooldown: {remaining}s remaining")
                        time.sleep(10)
                    blocked = True
                    break

                # Якщо статус 301/302/… — поновлюємо product_url на поточну Location та пробуємо ще раз
                if r.status_code in (301, 302, 303, 307, 308):
                    new_location = r.headers.get("Location")
                    if new_location:
                        parsed_loc = urlparse(new_location)
                        # Block open redirects to external domains
                        if parsed_loc.scheme and parsed_loc.netloc and parsed_loc.netloc != "www.walmart.com":
                            logging.warning("Redirect to external domain blocked: %s", new_location)
                            break
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
#----------------------NEW BLOCK--------------------
                data_sources = {
                    'product': prod,
                    'idml': idml,
                    'original': original,
                    'product_url': product_url.replace("?redirect=false", ""),
                    'current': prod.get('priceInfo', {}).get('currentPrice', {})
                }

                def get_by_path(data_sources, path):
                    try:
                        parts = path.split('.')
                        current = data_sources.get(parts[0])
                        for part in parts[1:]:
                            if isinstance(current, list):
                                # Претендуємо, що це список словників зі схемою name/value
                                name_map = {item.get("name"): item.get("value") for item in current if isinstance(item, dict)}
                                current = name_map.get(part, "")
                            elif isinstance(current, dict):
                                current = current.get(part)
                            else:
                                return ''
                        if isinstance(current, (list, dict)):
                            return json.dumps(current, ensure_ascii=False)
                        return current if current is not None else ''
                    except Exception as e:
                        logging.debug("get_by_path failed for '%s': %s", path, e)
                        return ''

                row_data = {
                    **{
                        col['header']: (
                            eval(col['expression'], {"__builtins__": {}}, {
                                'product_url': product_url,
                                'original': original,
                                'prod': prod,
                                'idml': idml,
                                'current': prod.get('priceInfo', {}).get('currentPrice', {})
                            }) if 'expression' in col else get_by_path(data_sources, col['json_path'])
                        )
                        for col in column_defs
                    },
                    **{col: original.get(col, '') for col in column_names}
                }

                headers = [col['header'] for col in column_defs] + column_names
                row = [
                    json.dumps(value) if isinstance(value, (list, dict)) else value
                    for value in [row_data.get(h, '') for h in headers]
                ]
                excel_queue.put(row)

                success = True
                break  # вдалий парсинг, виходимо з attempts

            if blocked:
                # Якщо був блок, уже зробили task_done/put → просто продовжуємо
                continue

            if success:
                id_queue.task_done()
                continue

            # Якщо 3 спроби не дали результат (й ми не були заблоковані), фіксуємо помилку та закриваємо задачу
            logging.error(f"Failed to process item {product_id} after 3 attempts")
            id_queue.task_done()

