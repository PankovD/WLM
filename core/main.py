from core import gui
import os
import time
import threading
import logging
from queue import Queue
from .gui import choose_mode, choose_file_and_columns, show_progress_bar, show_summary
from .processing import collect_ids, load_ids_from_file, writer_worker, consumer_worker

from .config import OUTPUT_FOLDER

status = {
    'total_rows_written': 0,
    'not_found': 0,
    'blocks': 0
}

def run_app():
    mode = choose_mode()
    if not mode:
        return

    selected_file, key_col, price_col, column_names, total_rows = \
        choose_file_and_columns(id_mode=(mode=='id'))
    if not selected_file:
        return

    start = time.time()
    dt_str = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(start))
    input_name = os.path.splitext(os.path.basename(selected_file))[0]
    input_folder = os.path.dirname(selected_file)
    results_file = os.path.join(input_folder, f"{input_name}_parsed_{dt_str}.xlsx")
    
    id_queue = Queue()
    excel_queue = Queue()
    progress_queue = Queue()
    file_lock = threading.Lock()

    # Writer
    t_writer = threading.Thread(target=writer_worker,
                                args=(excel_queue, file_lock, results_file, column_names, progress_queue, status))
    t_writer.start()

    # Producer
    if mode == 'upc':
        t_prod = threading.Thread(target=collect_ids,
                                  args=(id_queue, excel_queue, selected_file, key_col, price_col, column_names, status))
        t_prod.start()
    else:
        load_ids_from_file(id_queue, selected_file, key_col, price_col, column_names)

    # Consumers
    consumers = []
    for _ in range(3):
        t = threading.Thread(target=consumer_worker,
                              args=(id_queue, excel_queue, column_names, results_file, status))
        t.start()
        consumers.append(t)

    # Progress Bar
    def finish_cb():
        excel_queue.put(None)  # <--- тут, не в main потоці
        t_writer.join()
        elapsed = int(time.time() - start)
        hours, rem = divmod(elapsed, 3600)
        minutes, seconds = divmod(rem, 60)
        time_str = f"{hours:02}:{minutes:02}:{seconds:02}"

        logging.info("Total rows written: %d", status['total_rows_written'])
        logging.info("Not found items: %d", status['not_found'])
        logging.info("Total blocks: %d", status['blocks'])
        logging.info("Total time taken: %s", time_str)
        logging.info("Results saved in: %s", results_file)

        show_summary(
            total_rows_written=status['total_rows_written'],
            time_str=f"{hours:02}:{minutes:02}:{seconds:02}",
            results_file=results_file,
            blocks=status['blocks'],
            not_found=status['not_found']
        )


    t_progress = threading.Thread(target=show_progress_bar,
                                  args=(total_rows, progress_queue, finish_cb))
    t_progress.start()

    # Очікування завершення
    if mode == 'upc':
        t_prod.join()
    for _ in consumers:
        id_queue.put(None)
    for t in consumers:
        t.join()
    
    excel_queue.join()
    t_writer.join()


if __name__ == '__main__':
    run_app()
