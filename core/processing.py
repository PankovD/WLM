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
from .constants import CONFIGURED_FILE, DEFAULT_FILE
from .network import get_token, is_blocked, random_sleep, wait_for_connection
from .config import OUTPUT_ID_CSV
import csv
import pandas as pd
import sys

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
            # Оновлюємо токен
            token = get_token()
            lines = 0

    # Закінчили — сповіщаємо споживачів


    # Закриваємо файли
    writer_file.close()
    if selected_file.lower().endswith('.csv'):
        infile.close()
        
    return

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
                print(f"\rTotal rows written: {total_rows_written}", end="", flush=True)
            logging.info(f"Row {upc} written to Excel.")
            
        excel_queue.task_done()
    
    if progress_queue:
        progress_queue.put(None)

# ------------------- Original consumer -------------------
def consumer_worker(id_queue, excel_queue, column_names, results_file, progress_queue=None, status=None):
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
                    except Exception:
                        return ''

                row_data = {
                    **{
                        col['header']: (
                            eval(col['expression'], {}, {
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
            progress_queue.put(1)
            id_queue.task_done()
#----------------------END NEW BLOCK--------------------
                # ↓ Зібрали всі потрібні поля, складаємо рядок і кидаємо його в excel_queue
    #             price_info = prod.get('priceInfo') or {}
    #             current = price_info.get('currentPrice') or {}
    #             row_data = {
    #                 'Store Page': product_url.replace("?redirect=false", ""),
    #                 'Catalog Page': f"https://seller.walmart.com/catalog/add-items?search={original.get('UPC','')}",
    #                 'Product Title': prod.get('name'),
    #                 'Product ID': prod.get('usItemId'),
    #                 'Selling Price': current.get('price'),
    #                 'Active Sellers': prod.get('transactableOfferCount'),
    #                 'Ratings': prod.get('numberOfReviews'),
    #                 'Average Rating': prod.get('averageRating'),
    #                 'Current Seller': prod.get('sellerName'),
    #                 'UPC': original.get('UPC',''),
    #                 'PRICE': original.get('Price',''),
    #                 **{col: original.get(col,'') for col in column_names}
    #             }
    #             row = [row_data.get(h, '') for h in RESULT_HEADER + column_names]
    #             excel_queue.put(row)

    #             success = True
    #             break  # вдалий парсинг, виходимо з attempts

    #         if blocked:
    #             # Якщо був блок, уже зробили task_done/put → просто продовжуємо
    #             continue

    #         if success:
    #             id_queue.task_done()
    #             continue

    #         # Якщо 3 спроби не дали результат (й ми не були заблоковані), фіксуємо помилку та закриваємо задачу
    #         logging.error(f"Failed to process item {product_id} after 3 attempts")
    #         id_queue.task_done()

    # logging.info(f"Consumer finished; total blocks: {blocks}")

