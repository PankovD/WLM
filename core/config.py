import os
import base64
import time
import logging

# Walmart Marketplace API credentials
# Зберігаються тут (в оновлюваному core), а не в launcher.exe
CLIENT_ID = "2f04b7d6-4f0e-42fd-9e3b-d8379611aa7f"
CLIENT_SECRET = "QMkI2QWJ4nN4jsXAJpigHmMl_UEWYGyqnlADVTOh_ppqpghObi21EI6nxgEKosdVfjw4hEPwVg0v2z5iWO-15A"
AUTH_BASE64 = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

TOKEN_URL = "https://marketplace.walmartapis.com/v3/token"

# Шляхи збереження
CURRENT_TIME = time.strftime("%Y-%m-%d_%H-%M-%S")
OUTPUT_FOLDER = "logging"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
LOG_FILE = os.path.join(OUTPUT_FOLDER, f"log_{CURRENT_TIME}.txt")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

OUTPUT_ID_CSV = os.path.join(OUTPUT_FOLDER, 'item_ids.csv')
