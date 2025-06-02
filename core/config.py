import os
import base64
import time
import logging

# API credentials та шляхи
AUTH_BASE64 = os.environ.get("AUTH_BASE64", "")
TOKEN_URL = "https://marketplace.walmartapis.com/v3/token"

# Шляхи збереження
CURRENT_TIME = time.strftime("%Y-%m-%d_%H-%M-%S")
OUTPUT_FOLDER = "results"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
LOG_FILE = os.path.join(OUTPUT_FOLDER, f"log_{CURRENT_TIME}.txt")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

OUTPUT_ID_CSV = os.path.join(OUTPUT_FOLDER, 'item_ids.csv')